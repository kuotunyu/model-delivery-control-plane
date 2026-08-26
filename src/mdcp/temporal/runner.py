"""One-shot serial orchestration for bounded temporal development."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from threading import Lock

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.temporal.completeness import (
    AdapterOutcome,
    CompletenessReceipt,
    LabelOutcome,
    PredictionOutcome,
    assemble_development_pairs,
)
from mdcp.temporal.evaluation import (
    DevelopmentQualityReport,
    FoldQualificationContext,
    QualificationContext,
    QualificationEvidence,
    QualificationFoldDigests,
    QualificationResult,
    evaluate_pooled,
    qualify_trial,
)
from mdcp.temporal.folds import SourceRowIdentity
from mdcp.temporal.run_evidence import (
    ClosedMetrics,
    PrivateFoldEvidence,
    PrivateRunBundle,
    PublicDevelopmentResult,
    PublicFoldReceipt,
    PublicTrialReceipt,
)
from mdcp.temporal.runtime_guards import RuntimeGuard, RuntimeObservation, RuntimeStage
from mdcp.temporal.selection import (
    ProvisionalWinner,
    ReplayFoldDigests,
    ReplayResult,
    ReplaySelectionSession,
    SelectionDecision,
    finalize_selection,
)
from mdcp.temporal.trials import canonical_trial_identity

EXACT_FOLD_IDS = ("F1", "F2", "F3", "F4")
EXACT_TRIAL_IDS = (
    "CTRL-01",
    "REC-180-L4",
    "REC-180-L12",
    "REC-270-L4",
    "REC-270-L12",
    "REC-365-L4",
    "REC-365-L12",
    "STAT-A0.1",
    "STAT-A1",
    "STAT-A10",
    "STAT-A100",
    "STAT-A1000",
    "NL-E64-R0.03-D2",
    "NL-E64-R0.03-D3",
    "NL-E64-R0.07-D2",
    "NL-E64-R0.07-D3",
    "NL-E128-R0.03-D2",
    "NL-E128-R0.03-D3",
    "NL-E128-R0.07-D2",
    "NL-E128-R0.07-D3",
)
_SELECTION_LIMIT = len(EXACT_TRIAL_IDS) * len(EXACT_FOLD_IDS)
_REPLAY_LIMIT = len(EXACT_FOLD_IDS)
_SHA256_ALPHABET = frozenset("0123456789abcdef")


class FitPhase(StrEnum):
    SELECTION = "SELECTION"
    REPLAY = "REPLAY"


class FitBudgetError(RuntimeError):
    """Raised before an attempt can violate the frozen Wave 3 fit plan."""


class DevelopmentRunError(RuntimeError):
    """Fixed-code terminal result for an unsealable synthetic run."""

    def __init__(self, *reason_codes: str) -> None:
        self.reason_codes = reason_codes or ("DEVELOPMENT_RUN_UNKNOWN",)
        super().__init__(self.reason_codes[0])


@dataclass(frozen=True, slots=True)
class FitRecord:
    phase: FitPhase
    trial_id: str
    fold_id: str


@dataclass(slots=True)
class FitLedger:
    """Append-only exact-order accounting for 80 selection and at most four replay fits."""

    _records: list[FitRecord] = field(default_factory=list, init=False, repr=False)
    _selection_bound: bool = field(default=False, init=False, repr=False)
    _provisional: ProvisionalWinner | None = field(default=None, init=False, repr=False)

    @property
    def records(self) -> tuple[FitRecord, ...]:
        return tuple(self._records)

    @property
    def selection_count(self) -> int:
        return sum(record.phase is FitPhase.SELECTION for record in self._records)

    @property
    def replay_count(self) -> int:
        return sum(record.phase is FitPhase.REPLAY for record in self._records)

    @property
    def final_count(self) -> int:
        return 0

    @property
    def total_count(self) -> int:
        return len(self._records)

    def record_selection(self, trial_id: str, fold_id: str) -> None:
        """Reserve the next exact trial/fold selection fit."""
        if self._selection_bound or self.selection_count >= _SELECTION_LIMIT:
            raise FitBudgetError("SELECTION_ALREADY_CONSUMED")
        trial_index, fold_index = divmod(self.selection_count, len(EXACT_FOLD_IDS))
        if (trial_id, fold_id) != (
            EXACT_TRIAL_IDS[trial_index],
            EXACT_FOLD_IDS[fold_index],
        ):
            raise FitBudgetError("SELECTION_ORDER_INVALID")
        self._records.append(FitRecord(FitPhase.SELECTION, trial_id, fold_id))

    def bind_session(self, session: ReplaySelectionSession) -> ProvisionalWinner | None:
        """Seal one exact session and return only its internally derived rank one."""
        if self._selection_bound:
            raise FitBudgetError("SELECTION_AUTHORITY_ALREADY_BOUND")
        if self.selection_count != _SELECTION_LIMIT:
            raise FitBudgetError("SELECTION_INCOMPLETE")
        if type(session) is not ReplaySelectionSession:
            raise FitBudgetError("SELECTION_SESSION_INVALID")
        provisional = session.ranked_provisional()
        self._selection_bound = True
        self._provisional = provisional
        return provisional

    def record_replay(self, trial_id: str, fold_id: str) -> None:
        """Reserve the next exact replay fold for the sole bound provisional winner."""
        if not self._selection_bound:
            raise FitBudgetError("PROVISIONAL_WINNER_REQUIRED")
        if self._provisional is None:
            raise FitBudgetError("NO_PROVISIONAL_WINNER")
        if self.replay_count >= _REPLAY_LIMIT:
            raise FitBudgetError("REPLAY_ALREADY_CONSUMED")
        if trial_id != self._provisional.trial_id:
            raise FitBudgetError("REPLAY_TARGET_INVALID")
        if fold_id != EXACT_FOLD_IDS[self.replay_count]:
            raise FitBudgetError("REPLAY_FOLD_INVALID")
        self._records.append(FitRecord(FitPhase.REPLAY, trial_id, fold_id))


@dataclass(frozen=True, slots=True)
class _DevelopmentFoldResult:
    """Exact private typed output of one synthetic fold execution."""

    trial_id: str
    fold_id: str
    inventory: tuple[SourceRowIdentity, ...]
    adapters: tuple[AdapterOutcome, ...]
    predictions: tuple[PredictionOutcome, ...]
    labels: tuple[LabelOutcome, ...]
    contract_verdict: GateVerdict
    preprocessing_state_sha256: str
    feature_vector_sha256: str
    prediction_vector_sha256: str
    metric_sha256: str
    receipt_sha256: str


@dataclass(slots=True)
class _DevelopmentRunState:
    lock: Lock = field(default_factory=Lock)
    consumed: bool = False


@dataclass(frozen=True, slots=True)
class _DevelopmentExecutionPlan:
    """Private synthetic seam; Task 4 supplies the permit-bearing natural composition."""

    fit_fold: Callable[[FitPhase, str, str], object]
    _state: _DevelopmentRunState = field(default_factory=_DevelopmentRunState, init=False)


@dataclass(frozen=True, slots=True)
class DevelopmentRunBundle:
    public_result: PublicDevelopmentResult
    private_bundle: PrivateRunBundle
    fit_ledger: FitLedger
    qualifications: tuple[QualificationResult, ...]
    replay: ReplayResult | None
    selection: SelectionDecision


@dataclass(frozen=True, slots=True)
class _FormalDevelopmentInputs:
    repository_root: Path
    expected_freeze_head: str
    archive_path: Path
    archive_sha256: str
    private_container_path: Path
    search_receipt_sha256: str
    protocol_sha256: str


@dataclass(frozen=True, slots=True)
class _ProcessedFold:
    result: _DevelopmentFoldResult
    completeness: CompletenessReceipt
    context: FoldQualificationContext
    digest: QualificationFoldDigests


def _valid_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and set(value).issubset(_SHA256_ALPHABET)


def _valid_fold_result(result: object, trial_id: str, fold_id: str) -> bool:
    return (
        type(result) is _DevelopmentFoldResult
        and result.trial_id == trial_id
        and result.fold_id == fold_id
        and type(result.inventory) is tuple
        and all(type(item) is SourceRowIdentity for item in result.inventory)
        and type(result.adapters) is tuple
        and all(type(item) is AdapterOutcome for item in result.adapters)
        and type(result.predictions) is tuple
        and all(type(item) is PredictionOutcome for item in result.predictions)
        and type(result.labels) is tuple
        and all(type(item) is LabelOutcome for item in result.labels)
        and type(result.contract_verdict) is GateVerdict
        and all(
            _valid_sha256(value)
            for value in (
                result.preprocessing_state_sha256,
                result.feature_vector_sha256,
                result.prediction_vector_sha256,
                result.metric_sha256,
                result.receipt_sha256,
            )
        )
    )


def _checkpoint(guard: RuntimeGuard, stage: RuntimeStage) -> None:
    try:
        observation = guard.checkpoint(stage)
    except Exception as error:
        raise DevelopmentRunError("RUNTIME_GUARD_INVALID") from error
    if type(observation) is not RuntimeObservation or observation.verdict not in (
        "PASS",
        "UNKNOWN",
    ):
        raise DevelopmentRunError("RUNTIME_GUARD_INVALID")
    if observation.verdict != "PASS":
        if type(observation.reason_codes) is not tuple or not observation.reason_codes:
            raise DevelopmentRunError("RUNTIME_GUARD_INVALID")
        raise DevelopmentRunError(*observation.reason_codes)


def _execute_fit(
    plan: _DevelopmentExecutionPlan,
    guard: RuntimeGuard,
    ledger: FitLedger,
    phase: FitPhase,
    trial_id: str,
    fold_id: str,
) -> _DevelopmentFoldResult:
    _checkpoint(guard, RuntimeStage.PRE_FIT)
    if phase is FitPhase.SELECTION:
        ledger.record_selection(trial_id, fold_id)
    else:
        ledger.record_replay(trial_id, fold_id)
    callback_error: Exception | None = None
    result: object = None
    try:
        result = plan.fit_fold(phase, trial_id, fold_id)
    except Exception as error:
        callback_error = error
    _checkpoint(guard, RuntimeStage.POST_FIT)
    if callback_error is not None:
        raise DevelopmentRunError("FOLD_EXECUTION_FAILED") from callback_error
    if not _valid_fold_result(result, trial_id, fold_id):
        raise DevelopmentRunError("FOLD_RESULT_INVALID")
    return result


def _prediction_material(
    outcomes: tuple[PredictionOutcome, ...],
) -> list[dict[str, object]]:
    return [
        {
            "identity": asdict(outcome.identity),
            "succeeded": outcome.succeeded,
            "value": outcome.value,
            "reason_code": outcome.reason_code,
        }
        for outcome in outcomes
    ]


def _fold_evidence_sha256(
    result: _DevelopmentFoldResult,
    stable: tuple[PredictionOutcome, ...],
) -> str:
    return sha256_hex(
        canonicalize_json(
            {
                "trial_id": result.trial_id,
                "fold_id": result.fold_id,
                "contract_verdict": result.contract_verdict.value,
                "inventory": [asdict(identity) for identity in result.inventory],
                "adapters": [
                    {
                        "identity": asdict(outcome.identity),
                        "succeeded": outcome.succeeded,
                        "calendar_day": (
                            outcome.calendar_day.isoformat()
                            if outcome.calendar_day is not None
                            else None
                        ),
                        "groups": list(outcome.groups),
                        "reason_code": outcome.reason_code,
                    }
                    for outcome in result.adapters
                ],
                "stable_predictions": _prediction_material(stable),
                "candidate_predictions": _prediction_material(result.predictions),
                "labels": [
                    {
                        "identity": asdict(outcome.identity),
                        "succeeded": outcome.succeeded,
                        "value": outcome.value,
                        "reason_code": outcome.reason_code,
                    }
                    for outcome in result.labels
                ],
                "declared_digests": {
                    "preprocessing_state_sha256": result.preprocessing_state_sha256,
                    "feature_vector_sha256": result.feature_vector_sha256,
                    "prediction_vector_sha256": result.prediction_vector_sha256,
                    "metric_sha256": result.metric_sha256,
                    "receipt_sha256": result.receipt_sha256,
                },
            }
        )
    )


def _qualification_digest(
    result: _DevelopmentFoldResult,
    stable: tuple[PredictionOutcome, ...],
) -> QualificationFoldDigests:
    identity = canonical_trial_identity(result.trial_id)
    return QualificationFoldDigests(
        fold_id=result.fold_id,
        configuration_sha256=identity.configuration_sha256,
        preprocessing_state_sha256=result.preprocessing_state_sha256,
        feature_vector_sha256=result.feature_vector_sha256,
        prediction_vector_sha256=result.prediction_vector_sha256,
        metric_sha256=result.metric_sha256,
        receipt_sha256=_fold_evidence_sha256(result, stable),
    )


def _process_fold(
    result: _DevelopmentFoldResult,
    stable: tuple[PredictionOutcome, ...],
) -> _ProcessedFold:
    completeness, pairs = assemble_development_pairs(
        result.inventory,
        result.adapters,
        stable,
        result.predictions,
        result.labels,
    )
    return _ProcessedFold(
        result=result,
        completeness=completeness,
        context=FoldQualificationContext(
            fold_id=result.fold_id,
            inventory=result.inventory,
            paired_rows=pairs,
        ),
        digest=_qualification_digest(result, stable),
    )


def _qualification_evidence(folds: tuple[_ProcessedFold, ...]) -> QualificationEvidence:
    evidence_verdict = (
        GateVerdict.PASS
        if all(fold.result.contract_verdict is GateVerdict.PASS for fold in folds)
        else GateVerdict.UNKNOWN
    )
    return QualificationEvidence(
        lineage=GateVerdict.PASS,
        converter=GateVerdict.PASS,
        evidence=evidence_verdict,
        budget=GateVerdict.PASS,
    )


def _evaluate_trial(
    trial_id: str,
    folds: tuple[_ProcessedFold, ...],
) -> tuple[DevelopmentQualityReport, QualificationContext]:
    identity = canonical_trial_identity(trial_id)
    context = QualificationContext(
        folds=tuple(fold.context for fold in folds),
        trial_identity=identity,
        fold_digests=tuple(fold.digest for fold in folds),
    )
    report = evaluate_pooled(
        context,
        {fold.result.fold_id: fold.completeness for fold in folds},
        _qualification_evidence(folds),
    )
    return report, context


def _replay_digest(
    result: _DevelopmentFoldResult,
    stable: tuple[PredictionOutcome, ...],
) -> ReplayFoldDigests:
    qualification = _qualification_digest(result, stable)
    return ReplayFoldDigests(
        fold_id=qualification.fold_id,
        verdict=result.contract_verdict,
        configuration_sha256=qualification.configuration_sha256,
        preprocessing_state_sha256=qualification.preprocessing_state_sha256,
        feature_vector_sha256=qualification.feature_vector_sha256,
        prediction_vector_sha256=qualification.prediction_vector_sha256,
        metric_sha256=qualification.metric_sha256,
        receipt_sha256=qualification.receipt_sha256,
    )


def _private_fold_evidence(
    sequence: int,
    phase: FitPhase,
    result: _DevelopmentFoldResult,
) -> PrivateFoldEvidence:
    document = {
        "phase": phase.value,
        "trial_id": result.trial_id,
        "fold_id": result.fold_id,
        "contract_verdict": result.contract_verdict.value,
        "inventory": [asdict(identity) for identity in result.inventory],
        "adapters": [
            {
                "identity": asdict(outcome.identity),
                "succeeded": outcome.succeeded,
                "calendar_day": (
                    outcome.calendar_day.isoformat() if outcome.calendar_day is not None else None
                ),
                "groups": list(outcome.groups),
                "reason_code": outcome.reason_code,
            }
            for outcome in result.adapters
        ],
        "predictions": [
            {
                "identity": asdict(outcome.identity),
                "succeeded": outcome.succeeded,
                "value": outcome.value,
                "reason_code": outcome.reason_code,
            }
            for outcome in result.predictions
        ],
        "labels": [
            {
                "identity": asdict(outcome.identity),
                "succeeded": outcome.succeeded,
                "value": outcome.value,
                "reason_code": outcome.reason_code,
            }
            for outcome in result.labels
        ],
        "preprocessing_state_sha256": result.preprocessing_state_sha256,
        "feature_vector_sha256": result.feature_vector_sha256,
        "prediction_vector_sha256": result.prediction_vector_sha256,
        "metric_sha256": result.metric_sha256,
        "receipt_sha256": result.receipt_sha256,
    }
    return PrivateFoldEvidence(
        logical_path=(
            f"{phase.value.lower()}/{sequence:03d}-{result.trial_id}-{result.fold_id}.json"
        ),
        canonical_bytes=canonicalize_json(document),
    )


def _closed_metrics(report: object) -> ClosedMetrics:
    if report is None:
        return ClosedMetrics(
            row_count=None,
            stable_mae=None,
            candidate_mae=None,
            point_ratio=None,
            ucb95=None,
        )
    return ClosedMetrics(
        row_count=float(report.row_count),
        stable_mae=float(report.stable_mae),
        candidate_mae=float(report.candidate_mae),
        point_ratio=float(report.point_ratio),
        ucb95=float(report.ucb95),
    )


def _public_trial_receipt(
    index: int,
    report: DevelopmentQualityReport,
    qualification: QualificationResult | None,
) -> PublicTrialReceipt:
    status = "PASS" if qualification is None else qualification.verdict.value
    folds: list[PublicFoldReceipt] = []
    for fold in report.folds:
        if status == "UNKNOWN":
            metrics = _closed_metrics(None)
            reasons = ("METRICS_UNAVAILABLE",)
        else:
            metrics = _closed_metrics(fold.overall)
            reasons = ("QUALITY_THRESHOLD_EXCEEDED",) if status == "FAIL" else ()
        folds.append(
            PublicFoldReceipt(
                fold_id=fold.fold_id,
                status=status,
                metrics=metrics,
                reason_codes=reasons,
            )
        )
    return PublicTrialReceipt(
        trial_id=f"TRIAL-{index:02d}",
        selection_fit_count=4,
        folds=tuple(folds),
    )


def _public_result(
    reports: tuple[DevelopmentQualityReport, ...],
    qualifications: tuple[QualificationResult, ...],
    selection: SelectionDecision,
    ledger: FitLedger,
) -> PublicDevelopmentResult:
    qualification_by_trial = {item.trial_id: item for item in qualifications}
    trials = tuple(
        _public_trial_receipt(
            index,
            report,
            qualification_by_trial.get(EXACT_TRIAL_IDS[index - 1]),
        )
        for index, report in enumerate(reports, start=1)
    )
    status = (
        "PASS"
        if selection.status == "PASS"
        else "FAIL"
        if selection.status == "NO_ELIGIBLE_CANDIDATE"
        else "UNKNOWN"
    )
    result_sha256 = sha256_hex(
        canonicalize_json(
            {
                "status": status,
                "selection": {
                    "status": selection.status,
                    "reason_codes": list(selection.reason_codes),
                },
                "fits": [asdict(record) for record in ledger.records],
                "qualification_reports": [item.report_sha256 for item in qualifications],
            }
        )
    )
    return PublicDevelopmentResult(
        schema_version="mdcp.development-result-index.v1",
        canonicalization_version="RFC8785",
        evidence_class="synthetic_test",
        status=status,
        h1_role="OBSERVED_DEVELOPMENT_ONLY",
        h2_state="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
        selection_fit_count=80,
        result_sha256=result_sha256,
        trials=trials,
    )


def _run_development_core(
    plan: _DevelopmentExecutionPlan,
    guard: RuntimeGuard,
    *,
    defer_final_checkpoints: bool = False,
) -> DevelopmentRunBundle:
    """Execute the exact synthetic 80+4 state machine once with one replay session."""
    if type(plan) is not _DevelopmentExecutionPlan or not callable(plan.fit_fold):
        raise DevelopmentRunError("DEVELOPMENT_PLAN_INVALID")
    with plan._state.lock:
        if plan._state.consumed:
            raise DevelopmentRunError("RUN_ALREADY_CONSUMED")
        plan._state.consumed = True

    pre_seal_checked = False
    exit_checked = False
    try:
        _checkpoint(guard, RuntimeStage.PRE_LOAD)
        ledger = FitLedger()
        private_files: list[PrivateFoldEvidence] = []
        baseline: dict[str, tuple[PredictionOutcome, ...]] = {}
        reports: list[DevelopmentQualityReport] = []
        qualifications: list[QualificationResult] = []

        for trial_id in EXACT_TRIAL_IDS:
            processed: list[_ProcessedFold] = []
            for fold_id in EXACT_FOLD_IDS:
                result = _execute_fit(
                    plan,
                    guard,
                    ledger,
                    FitPhase.SELECTION,
                    trial_id,
                    fold_id,
                )
                private_files.append(
                    _private_fold_evidence(
                        len(private_files),
                        FitPhase.SELECTION,
                        result,
                    )
                )
                if trial_id == EXACT_TRIAL_IDS[0]:
                    baseline[fold_id] = result.predictions
                stable = baseline.get(fold_id)
                if stable is None:
                    raise DevelopmentRunError("STABLE_BASELINE_MISSING")
                processed.append(_process_fold(result, stable))
            fold_tuple = tuple(processed)
            report, context = _evaluate_trial(trial_id, fold_tuple)
            reports.append(report)
            if trial_id != EXACT_TRIAL_IDS[0]:
                qualifications.append(qualify_trial(report, context))

        qualification_tuple = tuple(qualifications)
        session = ReplaySelectionSession(qualification_tuple)
        provisional = ledger.bind_session(session)
        replay: ReplayResult | None = None
        if provisional is None:
            selection = finalize_selection(session, None, None)
        else:
            replay_digests: list[ReplayFoldDigests] = []
            for fold_id in EXACT_FOLD_IDS:
                result = _execute_fit(
                    plan,
                    guard,
                    ledger,
                    FitPhase.REPLAY,
                    provisional.trial_id,
                    fold_id,
                )
                private_files.append(
                    _private_fold_evidence(
                        len(private_files),
                        FitPhase.REPLAY,
                        result,
                    )
                )
                replay_digests.append(_replay_digest(result, baseline[fold_id]))
            replay = ReplayResult(
                trial_id=provisional.trial_id,
                family_id=provisional.family_id,
                ranking_key=provisional.ranking_key,
                qualification_inventory_sha256=provisional.qualification_inventory_sha256,
                session_sha256=session.session_sha256,
                verdict=(
                    GateVerdict.PASS
                    if all(digest.verdict is GateVerdict.PASS for digest in replay_digests)
                    else GateVerdict.UNKNOWN
                ),
                digests=tuple(replay_digests),
            )
            selection = finalize_selection(session, provisional, replay)

        private_bundle = PrivateRunBundle(
            evidence_class="synthetic_test",
            files=tuple(sorted(private_files, key=lambda item: item.logical_path.encode("ascii"))),
        )
        public_result = _public_result(
            tuple(reports),
            qualification_tuple,
            selection,
            ledger,
        )
        if not defer_final_checkpoints:
            pre_seal_checked = True
            _checkpoint(guard, RuntimeStage.PRE_SEAL)
            exit_checked = True
            _checkpoint(guard, RuntimeStage.EXIT)
        return DevelopmentRunBundle(
            public_result=public_result,
            private_bundle=private_bundle,
            fit_ledger=ledger,
            qualifications=qualification_tuple,
            replay=replay,
            selection=selection,
        )
    except DevelopmentRunError as original:
        if not defer_final_checkpoints and not pre_seal_checked:
            with suppress(DevelopmentRunError):
                _checkpoint(guard, RuntimeStage.PRE_SEAL)
        if not defer_final_checkpoints and not exit_checked:
            with suppress(DevelopmentRunError):
                _checkpoint(guard, RuntimeStage.EXIT)
        raise original
    except Exception as error:
        if not defer_final_checkpoints and not pre_seal_checked:
            with suppress(DevelopmentRunError):
                _checkpoint(guard, RuntimeStage.PRE_SEAL)
        if not defer_final_checkpoints and not exit_checked:
            with suppress(DevelopmentRunError):
                _checkpoint(guard, RuntimeStage.EXIT)
        raise DevelopmentRunError("DEVELOPMENT_RUN_UNKNOWN") from error


def _build_formal_execution_plan(
    inputs: _FormalDevelopmentInputs,
) -> _DevelopmentExecutionPlan:
    """Build a lazy natural fold executor; no archive byte is opened here."""
    protocol_path = inputs.repository_root / "configs/workload/temporal-development-v2.json"
    try:
        protocol_bytes = protocol_path.read_bytes()
        if sha256_hex(protocol_bytes) != inputs.protocol_sha256:
            raise DevelopmentRunError("PROTOCOL_IDENTITY_MISMATCH")
        protocol = parse_json_bytes(protocol_bytes)
    except DevelopmentRunError:
        raise
    except Exception as error:
        raise DevelopmentRunError("PROTOCOL_INVALID") from error
    loaded: dict[str, object] = {}

    def fit_fold(phase: FitPhase, trial_id: str, fold_id: str) -> object:
        if not loaded:
            _load_formal_execution_state(inputs, protocol, loaded)
        return _fit_formal_fold(loaded, phase, trial_id, fold_id)

    return _DevelopmentExecutionPlan(fit_fold=fit_fold)


def _load_formal_execution_state(
    inputs: _FormalDevelopmentInputs,
    protocol: object,
    state: dict[str, object],
) -> None:
    from mdcp.temporal.folds import load_fold_specs, materialize_folds
    from mdcp.temporal.trials import load_trial_specs
    from mdcp.workload.dataset import load_uci_development_archive
    from mdcp.workload.splits import split_development_rows

    if not isinstance(protocol, dict):
        raise DevelopmentRunError("PROTOCOL_INVALID")
    rows = load_uci_development_archive(inputs.archive_path, inputs.archive_sha256)
    partitions = split_development_rows(rows)
    folds = materialize_folds(partitions, load_fold_specs(protocol))
    trials = load_trial_specs(protocol)
    if (
        tuple(fold.spec.fold_id for fold in folds) != EXACT_FOLD_IDS
        or tuple(trial.trial_id for trial in trials) != EXACT_TRIAL_IDS
    ):
        raise DevelopmentRunError("FORMAL_INVENTORY_INVALID")
    state.update(
        {
            "folds": {fold.spec.fold_id: fold for fold in folds},
            "trials": {trial.trial_id: trial for trial in trials},
        }
    )


def _fit_formal_fold(
    state: dict[str, object],
    phase: FitPhase,
    trial_id: str,
    fold_id: str,
) -> _DevelopmentFoldResult:
    from mdcp.temporal.trials import (
        _feature_names,
        _materialize_features,
        build_estimator,
        training_rows_for_trial,
    )

    folds = state["folds"]
    trials = state["trials"]
    del phase
    if not isinstance(folds, dict) or not isinstance(trials, dict):
        raise DevelopmentRunError("FORMAL_INVENTORY_INVALID")
    fold = folds[fold_id]
    trial = trials[trial_id]
    training = training_rows_for_trial(trial, fold)
    features = _feature_names(trial)
    validation = _materialize_features(fold.validation).loc[:, (*features, "cnt")]
    estimator = build_estimator(trial)
    estimator.fit(training.loc[:, features], training["cnt"])
    prediction_values = tuple(
        float(value) for value in estimator.predict(validation.loc[:, features])
    )
    label_values = tuple(float(value) for value in validation["cnt"])
    adapters = tuple(
        AdapterOutcome(
            identity=identity,
            succeeded=True,
            calendar_day=datetime.fromisoformat(identity.local_timestamp).date(),
            groups=_formal_groups(fold.validation.iloc[position]),
        )
        for position, identity in enumerate(fold.inventory)
    )
    predictions = tuple(
        PredictionOutcome(identity=identity, succeeded=True, value=value)
        for identity, value in zip(fold.inventory, prediction_values, strict=True)
    )
    labels = tuple(
        LabelOutcome(identity=identity, succeeded=True, value=value)
        for identity, value in zip(fold.inventory, label_values, strict=True)
    )
    feature_material = [
        [float(value) for value in row]
        for row in validation.loc[:, features].itertuples(index=False, name=None)
    ]
    training_material = [
        [float(value) for value in row]
        for row in training.loc[:, features].itertuples(index=False, name=None)
    ]
    declared = {
        "trial_id": trial_id,
        "fold_id": fold_id,
        "preprocessing_state_sha256": sha256_hex(
            canonicalize_json(
                {
                    "configuration_sha256": canonical_trial_identity(trial_id).configuration_sha256,
                    "training_features": training_material,
                    "training_labels": tuple(float(value) for value in training["cnt"]),
                }
            )
        ),
        "feature_vector_sha256": sha256_hex(canonicalize_json(feature_material)),
        "prediction_vector_sha256": sha256_hex(canonicalize_json(prediction_values)),
        "metric_sha256": sha256_hex(
            canonicalize_json(
                {
                    "labels": label_values,
                    "predictions": prediction_values,
                }
            )
        ),
    }
    return _DevelopmentFoldResult(
        trial_id=trial_id,
        fold_id=fold_id,
        inventory=fold.inventory,
        adapters=adapters,
        predictions=predictions,
        labels=labels,
        contract_verdict=GateVerdict.PASS,
        preprocessing_state_sha256=declared["preprocessing_state_sha256"],
        feature_vector_sha256=declared["feature_vector_sha256"],
        prediction_vector_sha256=declared["prediction_vector_sha256"],
        metric_sha256=declared["metric_sha256"],
        receipt_sha256=sha256_hex(canonicalize_json(declared)),
    )


def _formal_groups(row: object) -> tuple[str, str, str]:
    weather = int(row["weathersit"])
    hour = int(row["hr"])
    return (
        (
            "weather_clear"
            if weather == 1
            else "weather_mist"
            if weather == 2
            else "weather_adverse"
        ),
        "day_working" if int(row["workingday"]) == 1 else "day_non_working",
        "demand_peak" if hour in {7, 8, 9, 16, 17, 18} else "demand_off_peak",
    )
