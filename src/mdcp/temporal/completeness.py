"""Identity-first completeness accounting for temporal development quality rows."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import TypeVar

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import PairedQualityRow
from mdcp.temporal.folds import SourceRowIdentity

_ACCOUNTING_REASON_CODES = (
    "MISSING_IDENTITY",
    "DUPLICATE_IDENTITY",
    "UNEXPECTED_IDENTITY",
    "INVALID_OUTPUT",
    "INVALID_REASON_CODE",
)
ADAPTER_REASON_CODES = _ACCOUNTING_REASON_CODES + (
    "ADAPTER_REJECTED",
    "TIMESTAMP_MISMATCH",
    "SCHEMA_FAILURE",
)
PREDICTION_REASON_CODES = _ACCOUNTING_REASON_CODES + (
    "INFERENCE_ERROR",
    "INVALID_RESPONSE",
    "PREDICTION_REJECTED",
)
LABEL_REASON_CODES = _ACCOUNTING_REASON_CODES + (
    "MISSING_LABEL",
    "LABEL_READ_ERROR",
)
_ADAPTER_FAILURE_REASON_CODES = ADAPTER_REASON_CODES[len(_ACCOUNTING_REASON_CODES) :]
_PREDICTION_FAILURE_REASON_CODES = PREDICTION_REASON_CODES[len(_ACCOUNTING_REASON_CODES) :]
_LABEL_FAILURE_REASON_CODES = LABEL_REASON_CODES[len(_ACCOUNTING_REASON_CODES) :]

_WEATHER_GROUPS = frozenset(("weather_clear", "weather_mist", "weather_adverse"))
_DAY_GROUPS = frozenset(("day_non_working", "day_working"))
_DEMAND_GROUPS = frozenset(("demand_peak", "demand_off_peak"))


@dataclass(frozen=True, slots=True)
class AdapterOutcome:
    """One adapter terminal outcome bound to an authoritative source identity."""

    identity: SourceRowIdentity
    succeeded: bool
    calendar_day: date | None = None
    groups: tuple[str, ...] = ()
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class PredictionOutcome:
    """One stable or candidate prediction terminal outcome."""

    identity: SourceRowIdentity
    succeeded: bool
    value: float | None = None
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class LabelOutcome:
    """One development-label terminal outcome, separate from inference."""

    identity: SourceRowIdentity
    succeeded: bool
    value: float | None = None
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class LayerAccounting:
    """Closed accounting for one stream against the fixed source denominator."""

    expected_count: int
    observed_count: int
    success_count: int
    failure_count: int
    missing_count: int
    duplicate_count: int
    unexpected_count: int
    invalid_count: int
    reason_counts: tuple[tuple[str, int], ...]

    @property
    def success_rate(self) -> float:
        return self.success_count / self.expected_count if self.expected_count else 1.0

    @property
    def complete(self) -> bool:
        return (
            self.observed_count == self.expected_count
            and self.success_count == self.expected_count
            and self.failure_count == 0
            and self.missing_count == 0
            and self.duplicate_count == 0
            and self.unexpected_count == 0
            and self.invalid_count == 0
            and self.success_rate == 1.0
        )

    def reason_count(self, reason_code: str) -> int:
        """Return a fixed reason count without accepting open-ended receipt keys."""
        return dict(self.reason_counts).get(reason_code, 0)


@dataclass(frozen=True, slots=True)
class CompletenessReceipt:
    """Development completeness verdict and independent layer accounting."""

    verdict: GateVerdict
    reason_codes: tuple[str, ...]
    source_count: int
    adapter: LayerAccounting
    stable: LayerAccounting
    candidate: LayerAccounting
    label: LayerAccounting

    @property
    def adapter_success_count(self) -> int:
        return self.adapter.success_count

    @property
    def adapter_failure_count(self) -> int:
        return self.adapter.failure_count

    @property
    def adapter_success_rate(self) -> float:
        return self.adapter.success_rate

    @property
    def stable_success_count(self) -> int:
        return self.stable.success_count

    @property
    def stable_failure_count(self) -> int:
        return self.stable.failure_count

    @property
    def stable_success_rate(self) -> float:
        return self.stable.success_rate

    @property
    def candidate_success_count(self) -> int:
        return self.candidate.success_count

    @property
    def candidate_failure_count(self) -> int:
        return self.candidate.failure_count

    @property
    def candidate_success_rate(self) -> float:
        return self.candidate.success_rate

    @property
    def label_success_count(self) -> int:
        return self.label.success_count

    @property
    def label_failure_count(self) -> int:
        return self.label.failure_count

    @property
    def label_missing_count(self) -> int:
        return self.label.reason_count("MISSING_LABEL")

    @property
    def label_success_rate(self) -> float:
        return self.label.success_rate


_OutcomeT = TypeVar("_OutcomeT", AdapterOutcome, PredictionOutcome, LabelOutcome)


def _identity_material(identity: SourceRowIdentity) -> dict[str, object]:
    return {
        "fold_id": identity.fold_id,
        "request_id": identity.request_id,
        "local_timestamp": identity.local_timestamp,
        "source_position": identity.source_position,
    }


def _valid_identity(identity: object) -> bool:
    if type(identity) is not SourceRowIdentity:
        return False
    if (
        type(identity.fold_id) is not str
        or not identity.fold_id
        or type(identity.request_id) is not str
        or not identity.request_id
        or type(identity.local_timestamp) is not str
        or not identity.local_timestamp
        or type(identity.source_position) is not int
        or identity.source_position < 0
        or type(identity.identity_sha256) is not str
        or len(identity.identity_sha256) != 64
        or any(character not in "0123456789abcdef" for character in identity.identity_sha256)
    ):
        return False
    try:
        timestamp = datetime.fromisoformat(identity.local_timestamp)
    except ValueError:
        return False
    if (
        timestamp.tzinfo is not None
        or timestamp.isoformat(timespec="seconds") != identity.local_timestamp
    ):
        return False
    return identity.identity_sha256 == sha256_hex(canonicalize_json(_identity_material(identity)))


def _valid_source_inventory(inventory: tuple[SourceRowIdentity, ...]) -> bool:
    if not inventory or any(not _valid_identity(identity) for identity in inventory):
        return False
    digests = [identity.identity_sha256 for identity in inventory]
    request_ids = [identity.request_id for identity in inventory]
    local_timestamps = [identity.local_timestamp for identity in inventory]
    source_positions = [(identity.fold_id, identity.source_position) for identity in inventory]
    return (
        len(digests) == len(set(digests))
        and len(request_ids) == len(set(request_ids))
        and len(local_timestamps) == len(set(local_timestamps))
        and len(source_positions) == len(set(source_positions))
    )


def _valid_number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _adapter_classification(outcome: AdapterOutcome) -> tuple[str, str | None]:
    if type(outcome.succeeded) is not bool:
        return "invalid", "INVALID_OUTPUT"
    if outcome.succeeded:
        if outcome.reason_code is not None or type(outcome.calendar_day) is not date:
            return "invalid", "INVALID_OUTPUT"
        try:
            authoritative_day = datetime.fromisoformat(outcome.identity.local_timestamp).date()
        except ValueError:
            return "invalid", "INVALID_OUTPUT"
        groups = outcome.groups
        if (
            type(groups) is not tuple
            or len(groups) != 3
            or any(type(group) is not str or not group for group in groups)
            or groups[0] not in _WEATHER_GROUPS
            or groups[1] not in _DAY_GROUPS
            or groups[2] not in _DEMAND_GROUPS
            or outcome.calendar_day != authoritative_day
        ):
            return "invalid", "INVALID_OUTPUT"
        return "success", None
    if (
        outcome.calendar_day is not None
        or outcome.groups
        or (
            type(outcome.reason_code) is not str
            or outcome.reason_code not in _ADAPTER_FAILURE_REASON_CODES
        )
    ):
        reason = (
            "INVALID_REASON_CODE"
            if type(outcome.reason_code) is not str
            or outcome.reason_code not in ADAPTER_REASON_CODES
            else "INVALID_OUTPUT"
        )
        return "invalid", reason
    return "failure", outcome.reason_code


def _prediction_classification(outcome: PredictionOutcome) -> tuple[str, str | None]:
    if type(outcome.succeeded) is not bool:
        return "invalid", "INVALID_OUTPUT"
    if outcome.succeeded:
        if outcome.reason_code is not None or not _valid_number(outcome.value):
            return "invalid", "INVALID_OUTPUT"
        return "success", None
    if outcome.value is not None or (
        type(outcome.reason_code) is not str
        or outcome.reason_code not in _PREDICTION_FAILURE_REASON_CODES
    ):
        reason = (
            "INVALID_REASON_CODE"
            if type(outcome.reason_code) is not str
            or outcome.reason_code not in PREDICTION_REASON_CODES
            else "INVALID_OUTPUT"
        )
        return "invalid", reason
    return "failure", outcome.reason_code


def _label_classification(outcome: LabelOutcome) -> tuple[str, str | None]:
    if type(outcome.succeeded) is not bool:
        return "invalid", "INVALID_OUTPUT"
    if outcome.succeeded:
        if outcome.reason_code is not None or not _valid_number(outcome.value):
            return "invalid", "INVALID_OUTPUT"
        return "success", None
    if outcome.value is not None or (
        type(outcome.reason_code) is not str
        or outcome.reason_code not in _LABEL_FAILURE_REASON_CODES
    ):
        reason = (
            "INVALID_REASON_CODE"
            if type(outcome.reason_code) is not str or outcome.reason_code not in LABEL_REASON_CODES
            else "INVALID_OUTPUT"
        )
        return "invalid", reason
    if outcome.reason_code == "MISSING_LABEL":
        return "missing", outcome.reason_code
    return "failure", outcome.reason_code


def _fixed_reason_counts(
    reason_codes: tuple[str, ...], counts: Counter[str]
) -> tuple[tuple[str, int], ...]:
    return tuple((reason_code, counts[reason_code]) for reason_code in reason_codes)


def _account_stream(
    expected: dict[str, SourceRowIdentity],
    outcomes: tuple[_OutcomeT, ...],
    *,
    outcome_type: type[_OutcomeT],
    classify: Callable[[_OutcomeT], tuple[str, str | None]],
    reason_codes: tuple[str, ...],
) -> tuple[LayerAccounting, dict[str, _OutcomeT]]:
    observed: defaultdict[str, list[_OutcomeT]] = defaultdict(list)
    reasons: Counter[str] = Counter()
    unexpected_count = 0
    invalid_count = 0

    for outcome in outcomes:
        if type(outcome) is not outcome_type or not _valid_identity(outcome.identity):
            unexpected_count += 1
            invalid_count += 1
            reasons["INVALID_OUTPUT"] += 1
            continue
        expected_identity = expected.get(outcome.identity.identity_sha256)
        if expected_identity is None or outcome.identity != expected_identity:
            unexpected_count += 1
            reasons["UNEXPECTED_IDENTITY"] += 1
            continue
        observed[outcome.identity.identity_sha256].append(outcome)

    accepted: dict[str, _OutcomeT] = {}
    missing_count = 0
    duplicate_count = 0
    success_count = 0
    for identity_sha256 in expected:
        matches = observed.get(identity_sha256, [])
        if not matches:
            missing_count += 1
            reasons["MISSING_IDENTITY"] += 1
            continue
        if len(matches) != 1:
            duplicate_count += 1
            reasons["DUPLICATE_IDENTITY"] += 1
            for outcome in matches:
                classification, reason_code = classify(outcome)
                if classification == "missing":
                    missing_count += 1
                    reasons[reason_code or "MISSING_IDENTITY"] += 1
                elif classification == "invalid":
                    invalid_count += 1
                    reasons[reason_code or "INVALID_OUTPUT"] += 1
                elif classification == "failure":
                    reasons[reason_code or "INVALID_OUTPUT"] += 1
            continue
        outcome = matches[0]
        classification, reason_code = classify(outcome)
        if classification == "success":
            success_count += 1
            accepted[identity_sha256] = outcome
        elif classification == "missing":
            missing_count += 1
            reasons[reason_code or "MISSING_IDENTITY"] += 1
        elif classification == "invalid":
            invalid_count += 1
            reasons[reason_code or "INVALID_OUTPUT"] += 1
        else:
            reasons[reason_code or "INVALID_OUTPUT"] += 1

    expected_count = len(expected)
    accounting = LayerAccounting(
        expected_count=expected_count,
        observed_count=len(outcomes),
        success_count=success_count,
        failure_count=expected_count - success_count,
        missing_count=missing_count,
        duplicate_count=duplicate_count,
        unexpected_count=unexpected_count,
        invalid_count=invalid_count,
        reason_counts=_fixed_reason_counts(reason_codes, reasons),
    )
    return accounting, accepted


def _invalid_inventory_layer(
    expected_count: int, observed_count: int, reason_codes: tuple[str, ...]
) -> LayerAccounting:
    reasons: Counter[str] = Counter({"INVALID_OUTPUT": expected_count})
    return LayerAccounting(
        expected_count=expected_count,
        observed_count=observed_count,
        success_count=0,
        failure_count=expected_count,
        missing_count=0,
        duplicate_count=0,
        unexpected_count=0,
        invalid_count=expected_count,
        reason_counts=_fixed_reason_counts(reason_codes, reasons),
    )


def assemble_development_pairs(
    inventory: Iterable[SourceRowIdentity],
    adapters: Iterable[AdapterOutcome],
    stable: Iterable[PredictionOutcome],
    candidate: Iterable[PredictionOutcome],
    labels: Iterable[LabelOutcome],
) -> tuple[CompletenessReceipt, tuple[PairedQualityRow, ...]]:
    """Account every development identity before producing any quality pair."""
    inventory_tuple = tuple(inventory)
    adapter_tuple = tuple(adapters)
    stable_tuple = tuple(stable)
    candidate_tuple = tuple(candidate)
    label_tuple = tuple(labels)
    source_count = len(inventory_tuple)

    if not _valid_source_inventory(inventory_tuple):
        receipt = CompletenessReceipt(
            verdict=GateVerdict.UNKNOWN,
            reason_codes=("SOURCE_INVENTORY_INVALID",),
            source_count=source_count,
            adapter=_invalid_inventory_layer(
                source_count, len(adapter_tuple), ADAPTER_REASON_CODES
            ),
            stable=_invalid_inventory_layer(
                source_count, len(stable_tuple), PREDICTION_REASON_CODES
            ),
            candidate=_invalid_inventory_layer(
                source_count, len(candidate_tuple), PREDICTION_REASON_CODES
            ),
            label=_invalid_inventory_layer(source_count, len(label_tuple), LABEL_REASON_CODES),
        )
        return receipt, ()

    expected = {identity.identity_sha256: identity for identity in inventory_tuple}
    adapter_accounting, accepted_adapters = _account_stream(
        expected,
        adapter_tuple,
        outcome_type=AdapterOutcome,
        classify=_adapter_classification,
        reason_codes=ADAPTER_REASON_CODES,
    )
    prediction_expected = {
        identity_sha256: expected[identity_sha256]
        for identity_sha256 in expected
        if identity_sha256 in accepted_adapters
    }
    stable_accounting, accepted_stable = _account_stream(
        prediction_expected,
        stable_tuple,
        outcome_type=PredictionOutcome,
        classify=_prediction_classification,
        reason_codes=PREDICTION_REASON_CODES,
    )
    candidate_accounting, accepted_candidate = _account_stream(
        prediction_expected,
        candidate_tuple,
        outcome_type=PredictionOutcome,
        classify=_prediction_classification,
        reason_codes=PREDICTION_REASON_CODES,
    )
    label_expected = {
        identity_sha256: expected[identity_sha256]
        for identity_sha256 in expected
        if identity_sha256 in accepted_stable and identity_sha256 in accepted_candidate
    }
    label_accounting, accepted_labels = _account_stream(
        label_expected,
        label_tuple,
        outcome_type=LabelOutcome,
        classify=_label_classification,
        reason_codes=LABEL_REASON_CODES,
    )
    layers = (
        ("ADAPTER_INCOMPLETE", adapter_accounting),
        ("STABLE_PREDICTION_INCOMPLETE", stable_accounting),
        ("CANDIDATE_PREDICTION_INCOMPLETE", candidate_accounting),
        ("LABEL_INCOMPLETE", label_accounting),
    )
    reason_codes = tuple(reason for reason, layer in layers if not layer.complete)
    verdict = GateVerdict.PASS if not reason_codes else GateVerdict.UNKNOWN
    receipt = CompletenessReceipt(
        verdict=verdict,
        reason_codes=reason_codes,
        source_count=source_count,
        adapter=adapter_accounting,
        stable=stable_accounting,
        candidate=candidate_accounting,
        label=label_accounting,
    )
    if verdict is not GateVerdict.PASS:
        return receipt, ()

    pairs = tuple(
        PairedQualityRow(
            request_id=identity.request_id,
            calendar_day=accepted_adapters[identity.identity_sha256].calendar_day,
            stable_prediction=accepted_stable[identity.identity_sha256].value,
            candidate_prediction=accepted_candidate[identity.identity_sha256].value,
            label=accepted_labels[identity.identity_sha256].value,
            groups=accepted_adapters[identity.identity_sha256].groups,
        )
        for identity in inventory_tuple
    )
    return receipt, pairs
