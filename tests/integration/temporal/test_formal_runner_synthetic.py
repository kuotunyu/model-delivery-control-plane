from __future__ import annotations

import inspect
import os
import sys
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

import mdcp.temporal.cli as cli
import mdcp.temporal.evaluation as evaluation_module
import mdcp.temporal.run_evidence as run_evidence
import mdcp.temporal.runner as runner
from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import BootstrapResult, PairedQualityRow, RatioMetric
from mdcp.temporal.completeness import AdapterOutcome, LabelOutcome, PredictionOutcome
from mdcp.temporal.evidence import public_evidence_violations
from mdcp.temporal.folds import SourceRowIdentity
from mdcp.temporal.runtime_guards import RuntimeObservation, RuntimeStage

_FORBIDDEN_BEHAVIORAL_CALLS = {
    "mdcp.workload.dataset.load_uci_archive",
    "mdcp.workload.splits.split_rows",
    "mdcp.workload.splits.DatasetPartitions.open_h2",
    ("mdcp.temporal.run_evidence._make_evidence_mutation_surface.<locals>.consume_marker"),
    ("mdcp.temporal.run_evidence._make_evidence_mutation_surface.<locals>.publish_private"),
    ("mdcp.temporal.run_evidence._make_evidence_mutation_surface.<locals>.publish_terminal"),
    "mdcp.temporal.runner._fit_formal_fold",
}


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
    return runner.DevelopmentFoldResult(
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


def _checkpoint(guard: _StageGuard | None, stage: RuntimeStage) -> None:
    if guard is None:
        return
    observation = guard.checkpoint(stage)
    if observation.verdict != "PASS":
        raise runner.DevelopmentRunError(*observation.reason_codes)


def _drive_state_machine(
    *,
    one_qualified_trial: str | None = "STAT-A1",
    contract_invalid_trial: str | None = None,
    changed_replay_digest: bool = False,
    changed_replay_evidence: str | None = None,
    changed_replay_predictions: bool = False,
    invalid_typed_verdict: bool = False,
    replay_contract_verdict: GateVerdict | None = None,
    guard: _StageGuard | None = None,
    calls: list[tuple[runner.FitPhase, str, str]] | None = None,
    defer_final_checkpoints: bool = False,
) -> tuple[
    runner.DevelopmentStateMachine,
    tuple[runner.DevelopmentFitRequest, ...],
    runner.DevelopmentRunBundle,
]:
    machine = runner.DevelopmentStateMachine()
    requests: list[runner.DevelopmentFitRequest] = []
    pre_seal_started = False
    exit_started = False
    try:
        _checkpoint(guard, RuntimeStage.PRE_LOAD)
        while (request := machine.next_fit_request()) is not None:
            _checkpoint(guard, RuntimeStage.PRE_FIT)
            requests.append(request)
            if calls is not None:
                calls.append((request.phase, request.trial_id, request.fold_id))
            result = _fold_result(
                request.phase,
                request.trial_id,
                request.fold_id,
                one_qualified_trial=one_qualified_trial,
                contract_invalid_trial=contract_invalid_trial,
                changed_replay_digest=changed_replay_digest,
                changed_replay_evidence=changed_replay_evidence,
                changed_replay_predictions=changed_replay_predictions,
                invalid_typed_verdict=invalid_typed_verdict,
            )
            assert type(result) is runner.DevelopmentFoldResult
            if request.phase is runner.FitPhase.REPLAY and replay_contract_verdict is not None:
                result = replace(result, contract_verdict=replay_contract_verdict)
            machine.record_fit_result(request, result)
            _checkpoint(guard, RuntimeStage.POST_FIT)
        bundle = machine.finalize()
        if not defer_final_checkpoints:
            pre_seal_started = True
            _checkpoint(guard, RuntimeStage.PRE_SEAL)
            exit_started = True
            _checkpoint(guard, RuntimeStage.EXIT)
        return machine, tuple(requests), bundle
    except Exception:
        if not defer_final_checkpoints and not pre_seal_started:
            pre_seal_started = True
            with suppress(runner.DevelopmentRunError):
                _checkpoint(guard, RuntimeStage.PRE_SEAL)
        if not defer_final_checkpoints and not exit_started:
            exit_started = True
            with suppress(runner.DevelopmentRunError):
                _checkpoint(guard, RuntimeStage.EXIT)
        raise


@dataclass(slots=True)
class _SyntheticOperation:
    one_qualified_trial: str | None = "STAT-A1"
    contract_invalid_trial: str | None = None
    changed_replay_digest: bool = False
    changed_replay_evidence: str | None = None
    changed_replay_predictions: bool = False
    invalid_typed_verdict: bool = False
    replay_contract_verdict: GateVerdict | None = None
    calls: list[tuple[runner.FitPhase, str, str]] = field(default_factory=list, init=False)
    _consumed: bool = field(default=False, init=False, repr=False)
    _lock: object = field(default_factory=threading.Lock, init=False, repr=False)

    def run(
        self,
        guard: _StageGuard,
        *,
        defer_final_checkpoints: bool = False,
    ) -> runner.DevelopmentRunBundle:
        with self._lock:
            if self._consumed:
                raise runner.DevelopmentRunError("RUN_ALREADY_CONSUMED")
            self._consumed = True
        return _drive_state_machine(
            one_qualified_trial=self.one_qualified_trial,
            contract_invalid_trial=self.contract_invalid_trial,
            changed_replay_digest=self.changed_replay_digest,
            changed_replay_evidence=self.changed_replay_evidence,
            changed_replay_predictions=self.changed_replay_predictions,
            invalid_typed_verdict=self.invalid_typed_verdict,
            replay_contract_verdict=self.replay_contract_verdict,
            guard=guard,
            calls=self.calls,
            defer_final_checkpoints=defer_final_checkpoints,
        )[2]


def _synthetic_plan(
    *,
    one_qualified_trial: str | None = "STAT-A1",
    contract_invalid_trial: str | None = None,
    changed_replay_digest: bool = False,
    changed_replay_evidence: str | None = None,
    changed_replay_predictions: bool = False,
    invalid_typed_verdict: bool = False,
) -> _SyntheticOperation:
    return _SyntheticOperation(
        one_qualified_trial=one_qualified_trial,
        contract_invalid_trial=contract_invalid_trial,
        changed_replay_digest=changed_replay_digest,
        changed_replay_evidence=changed_replay_evidence,
        changed_replay_predictions=changed_replay_predictions,
        invalid_typed_verdict=invalid_typed_verdict,
    )


def synthetic_run(*, one_qualified_trial: str | None = "STAT-A1") -> runner.DevelopmentRunBundle:
    return _synthetic_plan(one_qualified_trial=one_qualified_trial).run(_StageGuard())


def test_direct_state_machine_executes_exact_synthetic_80_plus_4() -> None:
    operation = _synthetic_plan()

    result = operation.run(_StageGuard())

    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 4
    assert result.fit_ledger.total_count == 84
    assert len(operation.calls) == 84


def test_fail_only_replay_is_terminal_unknown_without_losing_84_fit_result() -> None:
    operation = _SyntheticOperation(replay_contract_verdict=GateVerdict.FAIL)

    result = operation.run(_StageGuard())

    assert result.fit_ledger.total_count == 84
    assert result.replay is not None
    assert result.replay.verdict is GateVerdict.UNKNOWN
    assert result.selection.status == "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
    assert result.selection.reason_codes == ("REPLAY_UNKNOWN",)
    assert len(operation.calls) == 84


@contextmanager
def _count_forbidden_calls():
    counts = {name: 0 for name in _FORBIDDEN_BEHAVIORAL_CALLS}
    lock = threading.Lock()

    def profile(frame: object, event: str, _argument: object) -> None:
        if event != "call":
            return
        code = frame.f_code
        identity = f"{frame.f_globals.get('__name__')}.{code.co_qualname}"
        if identity in counts:
            with lock:
                counts[identity] += 1

    previous_thread = threading.getprofile()
    previous_process = sys.getprofile()
    threading.setprofile(profile)
    sys.setprofile(profile)
    try:
        yield counts
    finally:
        sys.setprofile(previous_process)
        threading.setprofile(previous_thread)


def _invoke_same_plan_concurrently(
    operation: _SyntheticOperation, *, callers: int
) -> tuple[tuple[str, int, int, tuple[str, ...]], ...]:
    barrier = threading.Barrier(callers)

    def invoke() -> tuple[str, int, int, tuple[str, ...]]:
        barrier.wait()
        try:
            result = operation.run(_StageGuard())
        except runner.DevelopmentRunError as error:
            return "FAIL", 0, os.getpid(), error.reason_codes
        return "PASS", result.fit_ledger.total_count, os.getpid(), ()

    with ThreadPoolExecutor(max_workers=callers) as executor:
        return tuple(executor.map(lambda _index: invoke(), range(callers)))


def test_concurrent_synthetic_plan_has_one_ledger_and_at_most_84_fits() -> None:
    operation = _synthetic_plan()

    with _count_forbidden_calls() as forbidden_calls:
        outcomes = _invoke_same_plan_concurrently(operation, callers=8)

    passes = [outcome for outcome in outcomes if outcome[0] == "PASS"]
    failures = [outcome for outcome in outcomes if outcome[0] == "FAIL"]
    assert len(passes) == 1
    assert passes[0][1] == 84
    assert len(failures) == 7
    assert {outcome[3] for outcome in failures} == {("RUN_ALREADY_CONSUMED",)}
    assert len(operation.calls) == 84
    assert max(outcome[1] for outcome in outcomes) <= 84
    assert {outcome[2] for outcome in outcomes} == {os.getpid()}
    assert forbidden_calls == dict.fromkeys(_FORBIDDEN_BEHAVIORAL_CALLS, 0)


def test_behavioral_profiler_observes_every_forbidden_probe() -> None:
    evidence_namespace: dict[str, object] = {"__name__": "mdcp.temporal.run_evidence"}
    exec(
        "def _make_evidence_mutation_surface():\n"
        "    def consume_marker():\n"
        "        return None\n"
        "    def publish_private():\n"
        "        return None\n"
        "    def publish_terminal():\n"
        "        return None\n"
        "    return consume_marker, publish_private, publish_terminal\n",
        evidence_namespace,
    )
    evidence_factory = evidence_namespace["_make_evidence_mutation_surface"]
    assert callable(evidence_factory)
    evidence_probes = evidence_factory()
    assert isinstance(evidence_probes, tuple)

    dataset_namespace: dict[str, object] = {"__name__": "mdcp.workload.dataset"}
    exec("def load_uci_archive():\n    return None\n", dataset_namespace)
    splits_namespace: dict[str, object] = {"__name__": "mdcp.workload.splits"}
    exec(
        "def split_rows():\n"
        "    return None\n"
        "class DatasetPartitions:\n"
        "    def open_h2(self):\n"
        "        return None\n",
        splits_namespace,
    )
    runner_namespace: dict[str, object] = {"__name__": "mdcp.temporal.runner"}
    exec("def _fit_formal_fold():\n    return None\n", runner_namespace)
    partition_type = splits_namespace["DatasetPartitions"]
    assert isinstance(partition_type, type)
    probes = (
        dataset_namespace["load_uci_archive"],
        splits_namespace["split_rows"],
        partition_type().open_h2,
        *evidence_probes,
        runner_namespace["_fit_formal_fold"],
    )
    assert all(callable(probe) for probe in probes)

    with _count_forbidden_calls() as forbidden_calls:
        for probe in probes:
            probe()

    assert forbidden_calls == dict.fromkeys(_FORBIDDEN_BEHAVIORAL_CALLS, 1)


@pytest.mark.parametrize(
    (
        "one_qualified_trial",
        "contract_invalid_trial",
        "changed_replay_digest",
        "expected_status",
        "expected_selection",
        "expected_fits",
    ),
    (
        ("STAT-A1", None, False, "PASS", "PASS", 84),
        (None, None, False, "FAIL", "NO_ELIGIBLE_CANDIDATE", 80),
        (
            "STAT-A1",
            "STAT-A1",
            False,
            "UNKNOWN",
            "UNKNOWN/NO_ELIGIBLE_CANDIDATE",
            80,
        ),
        (
            "STAT-A1",
            None,
            True,
            "UNKNOWN",
            "UNKNOWN/NO_ELIGIBLE_CANDIDATE",
            84,
        ),
    ),
)
def test_synthetic_terminal_matrix_has_no_fallback_or_85th_fit(
    one_qualified_trial: str | None,
    contract_invalid_trial: str | None,
    changed_replay_digest: bool,
    expected_status: str,
    expected_selection: str,
    expected_fits: int,
) -> None:
    operation = _synthetic_plan(
        one_qualified_trial=one_qualified_trial,
        contract_invalid_trial=contract_invalid_trial,
        changed_replay_digest=changed_replay_digest,
    )

    with _count_forbidden_calls() as forbidden_calls:
        result = operation.run(_StageGuard())

    assert result.public_result.status == expected_status
    assert result.selection.status == expected_selection
    assert result.fit_ledger.total_count == expected_fits
    assert len(operation.calls) == expected_fits
    assert expected_fits <= 84
    assert result.fit_ledger.final_count == 0
    assert forbidden_calls == dict.fromkeys(_FORBIDDEN_BEHAVIORAL_CALLS, 0)
    if expected_selection == "UNKNOWN/NO_ELIGIBLE_CANDIDATE" and expected_fits == 80:
        assert result.selection.reason_codes == ("QUALIFICATION_UNKNOWN",)
    if result.replay is not None:
        replay_trial = result.replay.trial_id
        assert {call[1] for call in operation.calls[80:]} == {replay_trial}


def test_synthetic_harness_has_no_formal_authority_or_natural_output_surface() -> None:
    parameters = set(inspect.signature(_synthetic_plan).parameters)
    assert parameters == {
        "one_qualified_trial",
        "contract_invalid_trial",
        "changed_replay_digest",
        "changed_replay_evidence",
        "changed_replay_predictions",
        "invalid_typed_verdict",
    }
    assert parameters.isdisjoint(
        {
            "archive",
            "authorization",
            "destination",
            "formal_seal",
            "natural_bundle",
            "writer",
        }
    )
    result = synthetic_run()
    assert result.private_bundle.evidence_class == "synthetic_test"
    assert result.public_result.evidence_class == "synthetic_test"
    assert not isinstance(result, run_evidence.FormalDevelopmentSeal)
    assert public_evidence_violations(result.public_result.model_dump(mode="json")) == ()


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_public_synthetic_writer_returns_identity_without_raw_authority(tmp_path: Path) -> None:
    result = synthetic_run()
    destination = tmp_path / "synthetic-private.container.json"

    identity = run_evidence.write_synthetic_bundle_no_clobber(destination, result.private_bundle)

    assert type(identity) is run_evidence.PrivateBundleIdentity
    assert run_evidence.verify_private_container(destination, identity).verdict == "PASS"
    assert public_evidence_violations(identity.model_dump(mode="json")) == ()


def test_invalid_cli_calls_are_concurrently_denied_before_formal_behavior(
    capfd: pytest.CaptureFixture[str],
) -> None:
    callers = 8
    with (
        _count_forbidden_calls() as forbidden_calls,
        ThreadPoolExecutor(max_workers=callers) as executor,
    ):
        outcomes = tuple(executor.map(lambda _index: cli.main(()), range(callers)))

    assert outcomes == (2,) * callers
    expected = (
        '{"reason_code":"FORMAL_RUN_REQUEST_INVALID",'
        '"schema_version":"mdcp.formal-run-cli-result.v1","verdict":"FAIL"}'
    )
    assert capfd.readouterr().out.splitlines() == [expected] * callers
    assert forbidden_calls == dict.fromkeys(_FORBIDDEN_BEHAVIORAL_CALLS, 0)


def test_state_machine_uses_existing_rank_one_and_same_session_for_replay() -> None:
    result = synthetic_run(one_qualified_trial="STAT-A1")

    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 4
    assert result.selection.final_winner is not None
    assert result.selection.final_winner.trial_id == "STAT-A1"
    assert result.selection.reason_codes == ()
    assert result.public_result.status == "PASS"
    assert result.private_bundle.evidence_class == "synthetic_test"


def test_state_machine_changed_replay_digest_fails_closed_without_another_target() -> None:
    operation = _synthetic_plan(changed_replay_digest=True)

    result = operation.run(_StageGuard())

    assert result.fit_ledger.total_count == 84
    assert result.selection.final_winner is None
    assert result.selection.reason_codes == ("REPLAY_DIGEST_MISMATCH",)
    assert operation.calls[-4:] == [
        (runner.FitPhase.REPLAY, "STAT-A1", fold_id) for fold_id in runner.EXACT_FOLD_IDS
    ]


def test_state_machine_changed_replay_predictions_cannot_reuse_selection_digest() -> None:
    operation = _synthetic_plan(changed_replay_predictions=True)

    result = operation.run(_StageGuard())

    assert result.selection.final_winner is None
    assert result.selection.reason_codes == ("REPLAY_DIGEST_MISMATCH",)


@pytest.mark.parametrize("mutation", ("labels", "adapters", "inventory"))
def test_state_machine_changed_typed_replay_evidence_cannot_reuse_declared_digests(
    mutation: str,
) -> None:
    operation = _synthetic_plan(changed_replay_evidence=mutation)

    result = operation.run(_StageGuard())

    assert result.selection.final_winner is None
    assert result.selection.reason_codes == ("REPLAY_DIGEST_MISMATCH",)


def test_state_machine_poor_quality_trial_still_completes_all_four_folds() -> None:
    operation = _synthetic_plan(one_qualified_trial=None)

    result = operation.run(_StageGuard())

    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 0
    assert result.selection.status == "NO_ELIGIBLE_CANDIDATE"
    for trial_id in runner.EXACT_TRIAL_IDS:
        assert [call[2] for call in operation.calls if call[1] == trial_id] == list(
            runner.EXACT_FOLD_IDS
        )


def test_state_machine_contract_invalid_trial_gets_no_replacement_fit() -> None:
    operation = _synthetic_plan(
        one_qualified_trial=None,
        contract_invalid_trial="STAT-A1",
    )

    result = operation.run(_StageGuard())

    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 0
    assert len([call for call in operation.calls if call[1] == "STAT-A1"]) == 4
    assert result.selection.final_winner is None


def test_state_machine_rejects_non_enum_fold_verdict_without_replacement() -> None:
    operation = _synthetic_plan(invalid_typed_verdict=True)

    with pytest.raises(runner.DevelopmentRunError, match="^FOLD_RESULT_INVALID$"):
        operation.run(_StageGuard())

    assert operation.calls == [(runner.FitPhase.SELECTION, "CTRL-01", "F1")]


def test_runtime_failure_stops_before_the_next_fit_and_checkpoints_exit() -> None:
    operation = _synthetic_plan()
    guard = _StageGuard(
        lambda stages: stages[-1] is RuntimeStage.PRE_FIT
        and stages.count(RuntimeStage.PRE_FIT) == 2
    )

    with pytest.raises(runner.DevelopmentRunError, match="^COMPUTE_MEMORY_EXCEEDED$"):
        operation.run(guard)

    assert operation.calls == [(runner.FitPhase.SELECTION, "CTRL-01", "F1")]
    assert guard.stages == [
        RuntimeStage.PRE_LOAD,
        RuntimeStage.PRE_FIT,
        RuntimeStage.POST_FIT,
        RuntimeStage.PRE_FIT,
        RuntimeStage.PRE_SEAL,
        RuntimeStage.EXIT,
    ]


def test_success_checkpoints_every_started_fit_before_seal_and_exit() -> None:
    operation = _synthetic_plan()
    guard = _StageGuard()

    result = operation.run(guard)

    assert len(operation.calls) == 84
    assert guard.stages[0] is RuntimeStage.PRE_LOAD
    assert guard.stages[-2:] == [RuntimeStage.PRE_SEAL, RuntimeStage.EXIT]
    assert guard.stages.count(RuntimeStage.PRE_FIT) == 84
    assert guard.stages.count(RuntimeStage.POST_FIT) == 84
    assert result.fit_ledger.final_count == 0


@pytest.mark.parametrize("failed_stage", (RuntimeStage.PRE_SEAL, RuntimeStage.EXIT))
def test_terminal_seal_or_exit_checkpoint_is_not_retried(
    failed_stage: RuntimeStage,
) -> None:
    operation = _synthetic_plan()
    guard = _StageGuard(lambda stages: stages[-1] is failed_stage)

    with pytest.raises(runner.DevelopmentRunError, match="^COMPUTE_MEMORY_EXCEEDED$"):
        operation.run(guard)

    assert guard.stages.count(failed_stage) == 1


def test_second_invocation_with_same_plan_is_terminal_without_another_fit() -> None:
    operation = _synthetic_plan()
    first = operation.run(_StageGuard())
    first_call_count = len(operation.calls)

    with pytest.raises(runner.DevelopmentRunError, match="^RUN_ALREADY_CONSUMED$"):
        operation.run(_StageGuard())

    assert first.fit_ledger.total_count == 84
    assert len(operation.calls) == first_call_count


def test_runner_has_no_public_replay_target_or_reconstructed_session_surface() -> None:
    assert not hasattr(runner, "replay_provisional")
    assert not hasattr(runner, "run_selection")
    assert not hasattr(runner, "FormalRunContext")
    assert not hasattr(runner, "_run_development_core")
    assert not hasattr(runner, "_DevelopmentExecutionPlan")


def test_private_rows_and_predictions_never_enter_closed_public_result() -> None:
    result = synthetic_run()

    public = result.public_result.model_dump(mode="json")
    assert public["h2_state"] == "SEALED_NOT_LOADED"
    assert public["h2_loaded_rows"] == 0
    assert "request_id" not in repr(public)
    assert "prediction" not in repr(public)
    assert "F1-0000" in repr(result.private_bundle)


def test_internal_formal_inputs_have_no_module_reachable_dependency_injection_surface() -> None:
    assert not hasattr(runner, "_FormalDevelopmentInputs")
    assert not hasattr(runner, "run_formal_development")


def test_state_machine_issues_exact_synthetic_80_plus_four_in_order() -> None:
    _machine, requests, bundle = _drive_state_machine()

    expected_selection = tuple(
        (runner.FitPhase.SELECTION, trial_id, fold_id)
        for trial_id in runner.EXACT_TRIAL_IDS
        for fold_id in runner.EXACT_FOLD_IDS
    )
    assert tuple((item.phase, item.trial_id, item.fold_id) for item in requests[:80]) == (
        expected_selection
    )
    assert tuple(item.sequence for item in requests) == tuple(range(1, 85))
    assert tuple((item.phase, item.trial_id, item.fold_id) for item in requests[80:]) == tuple(
        (runner.FitPhase.REPLAY, "STAT-A1", fold_id) for fold_id in runner.EXACT_FOLD_IDS
    )
    assert bundle.fit_ledger.selection_count == 80
    assert bundle.fit_ledger.replay_count == 4
    assert bundle.selection.status == "PASS"


def test_state_machine_has_zero_replay_without_a_qualified_candidate() -> None:
    _machine, requests, bundle = _drive_state_machine(one_qualified_trial=None)

    assert len(requests) == 80
    assert bundle.fit_ledger.selection_count == 80
    assert bundle.fit_ledger.replay_count == 0
    assert bundle.selection.status == "NO_ELIGIBLE_CANDIDATE"


def test_state_machine_rejects_result_before_issue_and_duplicate_result() -> None:
    machine = runner.DevelopmentStateMachine()
    result = _fold_result(
        runner.FitPhase.SELECTION,
        "CTRL-01",
        "F1",
        one_qualified_trial="STAT-A1",
        contract_invalid_trial=None,
        changed_replay_digest=False,
        changed_replay_evidence=None,
        changed_replay_predictions=False,
        invalid_typed_verdict=False,
    )
    request = runner.DevelopmentFitRequest(1, runner.FitPhase.SELECTION, "CTRL-01", "F1")

    with pytest.raises(runner.DevelopmentRunError, match="^FIT_REQUEST_NOT_ISSUED$"):
        machine.record_fit_result(request, result)
    issued = machine.next_fit_request()
    assert issued == request
    machine.record_fit_result(issued, result)
    with pytest.raises(runner.DevelopmentRunError, match="^FIT_REQUEST_NOT_ISSUED$"):
        machine.record_fit_result(issued, result)


@pytest.mark.parametrize(
    "mutation",
    (
        {"sequence": 2},
        {"phase": runner.FitPhase.REPLAY},
        {"trial_id": "REC-180-L4"},
        {"fold_id": "F2"},
    ),
)
def test_state_machine_rejects_stale_reordered_or_wrong_request(
    mutation: dict[str, object],
) -> None:
    machine = runner.DevelopmentStateMachine()
    issued = machine.next_fit_request()
    assert issued is not None
    forged = replace(issued, **mutation)
    result = _fold_result(
        issued.phase,
        issued.trial_id,
        issued.fold_id,
        one_qualified_trial="STAT-A1",
        contract_invalid_trial=None,
        changed_replay_digest=False,
        changed_replay_evidence=None,
        changed_replay_predictions=False,
        invalid_typed_verdict=False,
    )

    with pytest.raises(runner.DevelopmentRunError, match="^FIT_REQUEST_MISMATCH$"):
        machine.record_fit_result(forged, result)


@pytest.mark.parametrize("field", ("trial_id", "fold_id"))
def test_state_machine_rejects_result_for_the_wrong_trial_or_fold(field: str) -> None:
    machine = runner.DevelopmentStateMachine()
    request = machine.next_fit_request()
    assert request is not None
    result = _fold_result(
        request.phase,
        request.trial_id,
        request.fold_id,
        one_qualified_trial="STAT-A1",
        contract_invalid_trial=None,
        changed_replay_digest=False,
        changed_replay_evidence=None,
        changed_replay_predictions=False,
        invalid_typed_verdict=False,
    )
    assert type(result) is runner.DevelopmentFoldResult
    forged = replace(result, **{field: "F2" if field == "fold_id" else "REC-180-L4"})

    with pytest.raises(runner.DevelopmentRunError, match="^FOLD_RESULT_INVALID$"):
        machine.record_fit_result(request, forged)


@pytest.mark.parametrize("field", ("predictions", "labels"))
@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf"), 10**400))
def test_state_machine_normalizes_invalid_numeric_values(
    field: str,
    value: float | int,
) -> None:
    machine = runner.DevelopmentStateMachine()
    request = machine.next_fit_request()
    assert request is not None
    result = _fold_result(
        request.phase,
        request.trial_id,
        request.fold_id,
        one_qualified_trial="STAT-A1",
        contract_invalid_trial=None,
        changed_replay_digest=False,
        changed_replay_evidence=None,
        changed_replay_predictions=False,
        invalid_typed_verdict=False,
    )
    assert type(result) is runner.DevelopmentFoldResult
    outcomes = getattr(result, field)
    invalid_outcomes = (replace(outcomes[0], value=value), *outcomes[1:])

    with pytest.raises(runner.DevelopmentRunError, match="^FOLD_RESULT_INVALID$"):
        machine.record_fit_result(request, replace(result, **{field: invalid_outcomes}))


def test_state_machine_rejects_rank_two_fallback_and_a_fifth_replay() -> None:
    machine = runner.DevelopmentStateMachine()
    requests: list[runner.DevelopmentFitRequest] = []
    while (request := machine.next_fit_request()) is not None:
        requests.append(request)
        if request.phase is runner.FitPhase.REPLAY and request.fold_id == "F1":
            forged = replace(request, trial_id="REC-180-L4")
            result = _fold_result(
                request.phase,
                request.trial_id,
                request.fold_id,
                one_qualified_trial="STAT-A1",
                contract_invalid_trial=None,
                changed_replay_digest=False,
                changed_replay_evidence=None,
                changed_replay_predictions=False,
                invalid_typed_verdict=False,
            )
            with pytest.raises(runner.DevelopmentRunError, match="^FIT_REQUEST_MISMATCH$"):
                machine.record_fit_result(forged, result)
        result = _fold_result(
            request.phase,
            request.trial_id,
            request.fold_id,
            one_qualified_trial="STAT-A1",
            contract_invalid_trial=None,
            changed_replay_digest=False,
            changed_replay_evidence=None,
            changed_replay_predictions=False,
            invalid_typed_verdict=False,
        )
        machine.record_fit_result(request, result)

    assert len(requests) == 84
    assert machine.next_fit_request() is None
    bundle = machine.finalize()
    assert bundle.fit_ledger.replay_count == 4
    assert bundle.selection.final_winner is not None
    assert bundle.selection.final_winner.trial_id == "STAT-A1"


def test_state_machine_finalize_is_one_shot_and_rejects_late_results() -> None:
    machine, requests, _bundle = _drive_state_machine(one_qualified_trial=None)

    with pytest.raises(runner.DevelopmentRunError, match="^RUN_ALREADY_FINALIZED$"):
        machine.finalize()
    with pytest.raises(runner.DevelopmentRunError, match="^RUN_ALREADY_FINALIZED$"):
        machine.next_fit_request()
    last = requests[-1]
    late = _fold_result(
        last.phase,
        last.trial_id,
        last.fold_id,
        one_qualified_trial=None,
        contract_invalid_trial=None,
        changed_replay_digest=False,
        changed_replay_evidence=None,
        changed_replay_predictions=False,
        invalid_typed_verdict=False,
    )
    with pytest.raises(runner.DevelopmentRunError, match="^RUN_ALREADY_FINALIZED$"):
        machine.record_fit_result(last, late)
