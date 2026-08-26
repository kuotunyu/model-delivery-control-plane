from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

import mdcp.temporal.evaluation as evaluation_module
import mdcp.temporal.runner as runner
from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import BootstrapResult, PairedQualityRow, RatioMetric
from mdcp.temporal.completeness import AdapterOutcome, LabelOutcome, PredictionOutcome
from mdcp.temporal.folds import SourceRowIdentity
from mdcp.temporal.runtime_guards import RuntimeObservation, RuntimeStage


class _StageGuard:
    def __init__(self, fail: Callable[[tuple[RuntimeStage, ...]], bool] | None = None) -> None:
        self.stages: list[RuntimeStage] = []
        self._fail = fail or (lambda _stages: False)

    def checkpoint(self, stage: RuntimeStage) -> RuntimeObservation:
        self.stages.append(stage)
        failed = self._fail(tuple(self.stages))
        return RuntimeObservation(
            verdict="UNKNOWN" if failed else "PASS",
            reason_codes=("COMPUTE_MEMORY_EXCEEDED",) if failed else (),
            elapsed_ns=0,
            peak_process_bytes=1024,
            repository_inventory_sha256="f" * 64,
        )


def _fast_bootstrap(
    rows: Sequence[PairedQualityRow],
    groups: Sequence[str],
    resamples: int,
    seed: int,
) -> BootstrapResult:
    def metric(selected: tuple[PairedQualityRow, ...]) -> RatioMetric:
        stable_mae = sum(abs(row.stable_prediction - row.label) for row in selected) / len(selected)
        candidate_mae = sum(abs(row.candidate_prediction - row.label) for row in selected) / len(
            selected
        )
        ratio = candidate_mae / stable_mae
        return RatioMetric(
            row_count=len(selected),
            stable_mae=stable_mae,
            candidate_mae=candidate_mae,
            point_ratio=ratio,
            ucb95=ratio,
        )

    row_tuple = tuple(rows)
    return BootstrapResult(
        valid=True,
        overall=metric(row_tuple),
        subgroups={
            group: metric(tuple(row for row in row_tuple if group in row.groups))
            for group in groups
        },
        resamples=resamples,
        seed=seed,
        replicate_index=1899,
    )


@pytest.fixture(autouse=True)
def _deterministic_fast_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluation_module, "cluster_bootstrap_ratios", _fast_bootstrap)


def _identity(fold_id: str, position: int) -> SourceRowIdentity:
    starts = {
        "F1": date(2011, 7, 1),
        "F2": date(2011, 10, 1),
        "F3": date(2012, 1, 1),
        "F4": date(2012, 4, 1),
    }
    timestamp = datetime.combine(
        starts[fold_id] + timedelta(days=position // 24),
        datetime.min.time(),
    ) + timedelta(hours=position % 24)
    material = {
        "fold_id": fold_id,
        "request_id": f"{fold_id}-{position:04d}",
        "local_timestamp": timestamp.isoformat(timespec="seconds"),
        "source_position": position,
    }
    return SourceRowIdentity(
        **material,
        identity_sha256=sha256_hex(canonicalize_json(material)),
    )


_FOLD_INPUTS = {
    fold_id: tuple(_identity(fold_id, position) for position in range(300))
    for fold_id in runner.EXACT_FOLD_IDS
}


def _fold_result(
    phase: runner.FitPhase,
    trial_id: str,
    fold_id: str,
    *,
    one_qualified_trial: str | None,
    contract_invalid_trial: str | None,
    changed_replay_digest: bool,
    changed_replay_evidence: str | None,
    changed_replay_predictions: bool,
    invalid_typed_verdict: bool,
) -> object:
    inventory = _FOLD_INPUTS[fold_id]
    candidate_ratio = 0.9 if trial_id == one_qualified_trial else 1.2
    if phase is runner.FitPhase.REPLAY and changed_replay_predictions:
        candidate_ratio = 0.8
    adapters = tuple(
        AdapterOutcome(
            identity=identity,
            succeeded=True,
            calendar_day=datetime.fromisoformat(identity.local_timestamp).date(),
            groups=(
                ("weather_clear", "weather_mist", "weather_adverse")[position % 3],
                "day_working" if position % 2 else "day_non_working",
                "demand_peak" if position % 2 else "demand_off_peak",
            ),
        )
        for position, identity in enumerate(inventory)
    )
    predictions = tuple(
        PredictionOutcome(
            identity=identity,
            succeeded=True,
            value=20.0 if trial_id == "CTRL-01" else 10.0 + 10.0 * candidate_ratio,
        )
        for identity in inventory
    )
    labels = tuple(
        LabelOutcome(identity=identity, succeeded=True, value=10.0) for identity in inventory
    )
    if phase is runner.FitPhase.REPLAY and changed_replay_evidence == "labels":
        labels = (replace(labels[0], value=11.0), *labels[1:])
    if phase is runner.FitPhase.REPLAY and changed_replay_evidence == "adapters":
        adapters = (
            replace(
                adapters[0],
                groups=("weather_mist", "day_non_working", "demand_off_peak"),
            ),
            *adapters[1:],
        )
    if phase is runner.FitPhase.REPLAY and changed_replay_evidence == "inventory":
        inventory = (replace(inventory[0], source_position=999), *inventory[1:])
    digest_phase = "changed" if phase is runner.FitPhase.REPLAY and changed_replay_digest else "fit"
    contract_verdict: object = (
        "PASS"
        if invalid_typed_verdict and trial_id == "CTRL-01" and fold_id == "F1"
        else (
            GateVerdict.UNKNOWN
            if phase is runner.FitPhase.SELECTION and trial_id == contract_invalid_trial
            else GateVerdict.PASS
        )
    )
    return runner._DevelopmentFoldResult(
        trial_id=trial_id,
        fold_id=fold_id,
        inventory=inventory,
        adapters=adapters,
        predictions=predictions,
        labels=labels,
        contract_verdict=contract_verdict,
        preprocessing_state_sha256=sha256_hex(f"{trial_id}:{fold_id}:pre".encode()),
        feature_vector_sha256=sha256_hex(f"{trial_id}:{fold_id}:features".encode()),
        prediction_vector_sha256=sha256_hex(
            f"{trial_id}:{fold_id}:{digest_phase}:predictions".encode()
        ),
        metric_sha256=sha256_hex(f"{trial_id}:{fold_id}:metrics".encode()),
        receipt_sha256=sha256_hex(f"{trial_id}:{fold_id}:receipt".encode()),
    )


def _synthetic_plan(
    *,
    one_qualified_trial: str | None = "STAT-A1",
    contract_invalid_trial: str | None = None,
    changed_replay_digest: bool = False,
    changed_replay_evidence: str | None = None,
    changed_replay_predictions: bool = False,
    invalid_typed_verdict: bool = False,
) -> tuple[object, list[tuple[runner.FitPhase, str, str]]]:
    calls: list[tuple[runner.FitPhase, str, str]] = []

    def fit_fold(phase: runner.FitPhase, trial_id: str, fold_id: str) -> object:
        calls.append((phase, trial_id, fold_id))
        return _fold_result(
            phase,
            trial_id,
            fold_id,
            one_qualified_trial=one_qualified_trial,
            contract_invalid_trial=contract_invalid_trial,
            changed_replay_digest=changed_replay_digest,
            changed_replay_evidence=changed_replay_evidence,
            changed_replay_predictions=changed_replay_predictions,
            invalid_typed_verdict=invalid_typed_verdict,
        )

    return runner._DevelopmentExecutionPlan(fit_fold=fit_fold), calls


def synthetic_run(*, one_qualified_trial: str | None = "STAT-A1") -> runner.DevelopmentRunBundle:
    plan, _ = _synthetic_plan(one_qualified_trial=one_qualified_trial)
    return runner._run_development_core(plan, _StageGuard())


def test_core_uses_existing_rank_one_and_same_session_for_replay() -> None:
    result = synthetic_run(one_qualified_trial="STAT-A1")

    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 4
    assert result.selection.final_winner is not None
    assert result.selection.final_winner.trial_id == "STAT-A1"
    assert result.selection.reason_codes == ()
    assert result.public_result.status == "PASS"
    assert result.private_bundle.evidence_class == "synthetic_test"


def test_core_changed_replay_digest_fails_closed_without_another_target() -> None:
    plan, calls = _synthetic_plan(changed_replay_digest=True)

    result = runner._run_development_core(plan, _StageGuard())

    assert result.fit_ledger.total_count == 84
    assert result.selection.final_winner is None
    assert result.selection.reason_codes == ("REPLAY_DIGEST_MISMATCH",)
    assert calls[-4:] == [
        (runner.FitPhase.REPLAY, "STAT-A1", fold_id) for fold_id in runner.EXACT_FOLD_IDS
    ]


def test_core_changed_replay_predictions_cannot_reuse_selection_digest() -> None:
    plan, _ = _synthetic_plan(changed_replay_predictions=True)

    result = runner._run_development_core(plan, _StageGuard())

    assert result.selection.final_winner is None
    assert result.selection.reason_codes == ("REPLAY_DIGEST_MISMATCH",)


@pytest.mark.parametrize("mutation", ("labels", "adapters", "inventory"))
def test_core_changed_typed_replay_evidence_cannot_reuse_declared_digests(
    mutation: str,
) -> None:
    plan, _ = _synthetic_plan(changed_replay_evidence=mutation)

    result = runner._run_development_core(plan, _StageGuard())

    assert result.selection.final_winner is None
    assert result.selection.reason_codes == ("REPLAY_DIGEST_MISMATCH",)


def test_core_poor_quality_trial_still_completes_all_four_folds() -> None:
    plan, calls = _synthetic_plan(one_qualified_trial=None)

    result = runner._run_development_core(plan, _StageGuard())

    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 0
    assert result.selection.status == "NO_ELIGIBLE_CANDIDATE"
    for trial_id in runner.EXACT_TRIAL_IDS:
        assert [call[2] for call in calls if call[1] == trial_id] == list(runner.EXACT_FOLD_IDS)


def test_core_contract_invalid_trial_gets_no_replacement_fit() -> None:
    plan, calls = _synthetic_plan(
        one_qualified_trial=None,
        contract_invalid_trial="STAT-A1",
    )

    result = runner._run_development_core(plan, _StageGuard())

    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 0
    assert len([call for call in calls if call[1] == "STAT-A1"]) == 4
    assert result.selection.final_winner is None


def test_core_rejects_non_enum_fold_verdict_without_replacement() -> None:
    plan, calls = _synthetic_plan(invalid_typed_verdict=True)

    with pytest.raises(runner.DevelopmentRunError, match="^FOLD_RESULT_INVALID$"):
        runner._run_development_core(plan, _StageGuard())

    assert calls == [(runner.FitPhase.SELECTION, "CTRL-01", "F1")]


def test_runtime_failure_stops_before_the_next_fit_and_checkpoints_exit() -> None:
    plan, calls = _synthetic_plan()
    guard = _StageGuard(
        lambda stages: stages[-1] is RuntimeStage.PRE_FIT
        and stages.count(RuntimeStage.PRE_FIT) == 2
    )

    with pytest.raises(runner.DevelopmentRunError, match="^COMPUTE_MEMORY_EXCEEDED$"):
        runner._run_development_core(plan, guard)

    assert calls == [(runner.FitPhase.SELECTION, "CTRL-01", "F1")]
    assert guard.stages == [
        RuntimeStage.PRE_LOAD,
        RuntimeStage.PRE_FIT,
        RuntimeStage.POST_FIT,
        RuntimeStage.PRE_FIT,
        RuntimeStage.PRE_SEAL,
        RuntimeStage.EXIT,
    ]


def test_success_checkpoints_every_started_fit_before_seal_and_exit() -> None:
    plan, calls = _synthetic_plan()
    guard = _StageGuard()

    result = runner._run_development_core(plan, guard)

    assert len(calls) == 84
    assert guard.stages[0] is RuntimeStage.PRE_LOAD
    assert guard.stages[-2:] == [RuntimeStage.PRE_SEAL, RuntimeStage.EXIT]
    assert guard.stages.count(RuntimeStage.PRE_FIT) == 84
    assert guard.stages.count(RuntimeStage.POST_FIT) == 84
    assert result.fit_ledger.final_count == 0


@pytest.mark.parametrize("failed_stage", (RuntimeStage.PRE_SEAL, RuntimeStage.EXIT))
def test_terminal_seal_or_exit_checkpoint_is_not_retried(
    failed_stage: RuntimeStage,
) -> None:
    plan, _ = _synthetic_plan()
    guard = _StageGuard(lambda stages: stages[-1] is failed_stage)

    with pytest.raises(runner.DevelopmentRunError, match="^COMPUTE_MEMORY_EXCEEDED$"):
        runner._run_development_core(plan, guard)

    assert guard.stages.count(failed_stage) == 1


def test_second_invocation_with_same_plan_is_terminal_without_another_fit() -> None:
    plan, calls = _synthetic_plan()
    first = runner._run_development_core(plan, _StageGuard())
    first_call_count = len(calls)

    with pytest.raises(runner.DevelopmentRunError, match="^RUN_ALREADY_CONSUMED$"):
        runner._run_development_core(plan, _StageGuard())

    assert first.fit_ledger.total_count == 84
    assert len(calls) == first_call_count


def test_runner_has_no_public_replay_target_or_reconstructed_session_surface() -> None:
    plan, _ = _synthetic_plan()

    assert tuple(plan.__dataclass_fields__) == ("fit_fold", "_state")
    assert not hasattr(runner, "replay_provisional")
    assert not hasattr(runner, "run_selection")
    assert not hasattr(runner, "FormalRunContext")


def test_private_rows_and_predictions_never_enter_closed_public_result() -> None:
    result = synthetic_run()

    public = result.public_result.model_dump(mode="json")
    assert public["h2_state"] == "SEALED_NOT_LOADED"
    assert public["h2_loaded_rows"] == 0
    assert "request_id" not in repr(public)
    assert "prediction" not in repr(public)
    assert "F1-0000" in repr(result.private_bundle)


def test_internal_formal_inputs_have_no_dependency_injection_surface() -> None:
    assert tuple(runner._FormalDevelopmentInputs.__dataclass_fields__) == (
        "repository_root",
        "expected_freeze_head",
        "archive_path",
        "archive_sha256",
        "private_container_path",
        "search_receipt_sha256",
        "protocol_sha256",
    )
    assert not hasattr(runner, "run_formal_development")
