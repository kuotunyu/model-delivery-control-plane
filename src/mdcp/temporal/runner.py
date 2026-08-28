"""One-shot serial orchestration for bounded temporal development."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from mdcp.common.canonical import canonicalize_json
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
class DevelopmentFitRequest:
    """One exact immutable fit operation issued by the state machine."""

    sequence: int
    phase: FitPhase
    trial_id: str
    fold_id: str


@dataclass(frozen=True, slots=True)
class DevelopmentFoldResult:
    """Exact typed output of one worker-owned fold execution."""

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


@dataclass(frozen=True, slots=True)
class DevelopmentRunBundle:
    public_result: PublicDevelopmentResult
    private_bundle: PrivateRunBundle
    fit_ledger: FitLedger
    qualifications: tuple[QualificationResult, ...]
    replay: ReplayResult | None
    selection: SelectionDecision


@dataclass(frozen=True, slots=True)
class _ProcessedFold:
    result: DevelopmentFoldResult
    completeness: CompletenessReceipt
    context: FoldQualificationContext
    digest: QualificationFoldDigests


def _valid_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and set(value).issubset(_SHA256_ALPHABET)


def _valid_fold_result(result: object, trial_id: str, fold_id: str) -> bool:
    return (
        type(result) is DevelopmentFoldResult
        and result.trial_id == trial_id
        and result.fold_id == fold_id
        and type(result.inventory) is tuple
        and all(type(item) is SourceRowIdentity for item in result.inventory)
        and type(result.adapters) is tuple
        and all(type(item) is AdapterOutcome for item in result.adapters)
        and type(result.predictions) is tuple
        and all(type(item) is PredictionOutcome for item in result.predictions)
        and all(
            item.value is None or (type(item.value) is float and math.isfinite(item.value))
            for item in result.predictions
        )
        and type(result.labels) is tuple
        and all(type(item) is LabelOutcome for item in result.labels)
        and all(
            item.value is None or (type(item.value) is float and math.isfinite(item.value))
            for item in result.labels
        )
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
    result: DevelopmentFoldResult,
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
    result: DevelopmentFoldResult,
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
    result: DevelopmentFoldResult,
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
    result: DevelopmentFoldResult,
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
    result: DevelopmentFoldResult,
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


class DevelopmentStateMachine:
    """Pure one-shot sequencing, qualification, ranking, and replay state."""

    __slots__ = (
        "_baseline",
        "_finalized",
        "_ledger",
        "_outstanding",
        "_private_folds",
        "_processed_selection",
        "_provisional",
        "_qualifications",
        "_replay",
        "_replay_digests",
        "_reports",
        "_selection",
        "_session",
    )

    def __init__(self) -> None:
        self._ledger = FitLedger()
        self._outstanding: DevelopmentFitRequest | None = None
        self._baseline: dict[str, tuple[PredictionOutcome, ...]] = {}
        self._processed_selection: list[_ProcessedFold] = []
        self._reports: list[DevelopmentQualityReport] = []
        self._qualifications: list[QualificationResult] = []
        self._private_folds: list[PrivateFoldEvidence] = []
        self._session: ReplaySelectionSession | None = None
        self._provisional: ProvisionalWinner | None = None
        self._replay_digests: list[ReplayFoldDigests] = []
        self._replay: ReplayResult | None = None
        self._selection: SelectionDecision | None = None
        self._finalized = False

    def next_fit_request(self) -> DevelopmentFitRequest | None:
        """Reserve and issue the next exact selection or sole-winner replay fit."""
        self._require_active()
        if self._outstanding is not None:
            raise FitBudgetError("FIT_REQUEST_OUTSTANDING")

        if self._ledger.selection_count < _SELECTION_LIMIT:
            index = self._ledger.selection_count
            trial_index, fold_index = divmod(index, len(EXACT_FOLD_IDS))
            trial_id = EXACT_TRIAL_IDS[trial_index]
            fold_id = EXACT_FOLD_IDS[fold_index]
            self._ledger.record_selection(trial_id, fold_id)
            request = DevelopmentFitRequest(
                sequence=self._ledger.total_count,
                phase=FitPhase.SELECTION,
                trial_id=trial_id,
                fold_id=fold_id,
            )
            self._outstanding = request
            return request

        if self._session is None or self._selection is not None:
            return None
        if self._provisional is None:
            return None
        if self._ledger.replay_count >= _REPLAY_LIMIT:
            return None

        fold_id = EXACT_FOLD_IDS[self._ledger.replay_count]
        self._ledger.record_replay(self._provisional.trial_id, fold_id)
        request = DevelopmentFitRequest(
            sequence=self._ledger.total_count,
            phase=FitPhase.REPLAY,
            trial_id=self._provisional.trial_id,
            fold_id=fold_id,
        )
        self._outstanding = request
        return request

    def record_fit_result(
        self,
        request: DevelopmentFitRequest,
        result: DevelopmentFoldResult,
    ) -> None:
        """Accept only the exact result for the one outstanding immutable request."""
        self._require_active()
        if self._outstanding is None:
            raise DevelopmentRunError("FIT_REQUEST_NOT_ISSUED")
        if type(request) is not DevelopmentFitRequest or request != self._outstanding:
            raise DevelopmentRunError("FIT_REQUEST_MISMATCH")
        if not _valid_fold_result(result, request.trial_id, request.fold_id):
            raise DevelopmentRunError("FOLD_RESULT_INVALID")

        if request.phase is FitPhase.SELECTION:
            self._record_selection_result(request, result)
        elif request.phase is FitPhase.REPLAY:
            self._record_replay_result(request, result)
        else:  # pragma: no cover - exact request equality makes this unreachable
            raise DevelopmentRunError("FIT_REQUEST_MISMATCH")
        self._outstanding = None

    def finalize(self) -> DevelopmentRunBundle:
        """Seal and return the completed deterministic run exactly once."""
        self._require_active()
        if self._outstanding is not None:
            raise DevelopmentRunError("FIT_REQUEST_OUTSTANDING")
        if (
            self._ledger.selection_count != _SELECTION_LIMIT
            or self._selection is None
            or len(self._reports) != len(EXACT_TRIAL_IDS)
            or len(self._qualifications) != len(EXACT_TRIAL_IDS) - 1
        ):
            raise DevelopmentRunError("DEVELOPMENT_RUN_INCOMPLETE")
        if self._provisional is None:
            if self._ledger.replay_count != 0 or self._replay is not None:
                raise DevelopmentRunError("DEVELOPMENT_RUN_INVALID")
        elif self._ledger.replay_count != _REPLAY_LIMIT or self._replay is None:
            raise DevelopmentRunError("DEVELOPMENT_RUN_INCOMPLETE")

        private_bundle = PrivateRunBundle(
            evidence_class="synthetic_test",
            files=tuple(
                sorted(self._private_folds, key=lambda item: item.logical_path.encode("ascii"))
            ),
        )
        qualifications = tuple(self._qualifications)
        bundle = DevelopmentRunBundle(
            public_result=_public_result(
                tuple(self._reports),
                qualifications,
                self._selection,
                self._ledger,
            ),
            private_bundle=private_bundle,
            fit_ledger=self._ledger,
            qualifications=qualifications,
            replay=self._replay,
            selection=self._selection,
        )
        self._finalized = True
        return bundle

    def _record_selection_result(
        self,
        request: DevelopmentFitRequest,
        result: DevelopmentFoldResult,
    ) -> None:
        if request.trial_id == EXACT_TRIAL_IDS[0]:
            self._baseline[request.fold_id] = result.predictions
        stable = self._baseline.get(request.fold_id)
        if stable is None:
            raise DevelopmentRunError("STABLE_BASELINE_MISSING")
        try:
            processed = _process_fold(result, stable)
        except Exception as error:
            raise DevelopmentRunError("FOLD_RESULT_INVALID") from error
        self._private_folds.append(
            _private_fold_evidence(request.sequence - 1, request.phase, result)
        )
        self._processed_selection.append(processed)
        if request.fold_id != EXACT_FOLD_IDS[-1]:
            return

        folds = tuple(self._processed_selection)
        if len(folds) != len(EXACT_FOLD_IDS):
            raise DevelopmentRunError("SELECTION_ORDER_INVALID")
        self._processed_selection.clear()
        try:
            report, context = _evaluate_trial(request.trial_id, folds)
        except Exception as error:
            raise DevelopmentRunError("FOLD_RESULT_INVALID") from error
        self._reports.append(report)
        if request.trial_id != EXACT_TRIAL_IDS[0]:
            self._qualifications.append(qualify_trial(report, context))

        if request.trial_id == EXACT_TRIAL_IDS[-1]:
            qualifications = tuple(self._qualifications)
            try:
                session = ReplaySelectionSession(qualifications)
                provisional = self._ledger.bind_session(session)
            except (FitBudgetError, ValueError) as error:
                raise DevelopmentRunError("SELECTION_SESSION_INVALID") from error
            self._session = session
            self._provisional = provisional
            if provisional is None:
                selection = finalize_selection(session, None, None)
                if any(item.verdict is GateVerdict.UNKNOWN for item in qualifications):
                    selection = SelectionDecision(
                        status="UNKNOWN/NO_ELIGIBLE_CANDIDATE",
                        provisional_winner=None,
                        final_winner=None,
                        retry_allowed=False,
                        reason_codes=("QUALIFICATION_UNKNOWN",),
                    )
                self._selection = selection

    def _record_replay_result(
        self,
        request: DevelopmentFitRequest,
        result: DevelopmentFoldResult,
    ) -> None:
        if self._session is None or self._provisional is None:
            raise DevelopmentRunError("PROVISIONAL_WINNER_REQUIRED")
        stable = self._baseline.get(request.fold_id)
        if stable is None:
            raise DevelopmentRunError("STABLE_BASELINE_MISSING")
        self._private_folds.append(
            _private_fold_evidence(request.sequence - 1, request.phase, result)
        )
        self._replay_digests.append(_replay_digest(result, stable))
        if request.fold_id != EXACT_FOLD_IDS[-1]:
            return
        replay = ReplayResult(
            trial_id=self._provisional.trial_id,
            family_id=self._provisional.family_id,
            ranking_key=self._provisional.ranking_key,
            qualification_inventory_sha256=self._provisional.qualification_inventory_sha256,
            session_sha256=self._session.session_sha256,
            verdict=(
                GateVerdict.PASS
                if all(item.verdict is GateVerdict.PASS for item in self._replay_digests)
                else GateVerdict.UNKNOWN
            ),
            digests=tuple(self._replay_digests),
        )
        self._replay = replay
        self._selection = finalize_selection(self._session, self._provisional, replay)

    def _require_active(self) -> None:
        if self._finalized:
            raise DevelopmentRunError("RUN_ALREADY_FINALIZED")


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
