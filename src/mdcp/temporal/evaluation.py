"""Frozen fold and pooled temporal-development quality qualification."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import (
    BootstrapResult,
    PairedQualityRow,
    RatioMetric,
    cluster_bootstrap_ratios,
)
from mdcp.temporal.completeness import (
    ADAPTER_REASON_CODES,
    LABEL_REASON_CODES,
    PREDICTION_REASON_CODES,
    CompletenessReceipt,
    LayerAccounting,
)
from mdcp.temporal.folds import SourceRowIdentity

FOLD_IDS = ("F1", "F2", "F3", "F4")
FIXED_SUBGROUPS = (
    "weather_clear",
    "weather_mist",
    "weather_adverse",
    "day_non_working",
    "day_working",
    "demand_peak",
    "demand_off_peak",
)
_WEATHER_GROUPS = frozenset(FIXED_SUBGROUPS[:3])
_DAY_GROUPS = frozenset(FIXED_SUBGROUPS[3:5])
_DEMAND_GROUPS = frozenset(FIXED_SUBGROUPS[5:])
_BOOTSTRAP_RESAMPLES = 2000
_BOOTSTRAP_SEED = 2026
_BOOTSTRAP_INDEX = 1899
_MIN_SUBGROUP_ROWS = 100
_POOLED_OVERALL_MAX_RATIO = 0.97
_POOLED_SUBGROUP_MAX_RATIO = 1.05
_FOLD_OVERALL_MAX_RATIO = 1.05
_MIN_FOLDS_AT_OR_BELOW_ONE = 3


@dataclass(frozen=True, slots=True)
class QualityMetricReport:
    """One reported quality metric; values are absent only for invalid evidence."""

    row_count: int
    stable_mae: float | None
    candidate_mae: float | None
    point_ratio: float | None
    ucb95: float | None


@dataclass(frozen=True, slots=True)
class NamedQualityMetric:
    """A metric bound to one fixed subgroup name."""

    name: str
    metric: QualityMetricReport


@dataclass(frozen=True, slots=True)
class FoldQualificationContext:
    """Transient raw fold inputs; never nested in a report or public evidence."""

    fold_id: str
    inventory: tuple[SourceRowIdentity, ...]
    paired_rows: tuple[PairedQualityRow, ...]


@dataclass(frozen=True, slots=True)
class QualificationContext:
    """Transient exact four-fold source inventory and paired-row binding."""

    folds: tuple[FoldQualificationContext, ...]


@dataclass(frozen=True, slots=True)
class FoldQualityReport:
    """Completeness and frozen quality statistics for one development fold."""

    fold_id: str
    completeness: CompletenessReceipt
    paired_row_count: int
    overall: QualityMetricReport
    subgroups: tuple[NamedQualityMetric, ...]
    bootstrap: BootstrapResult
    reason_codes: tuple[str, ...]
    inventory_sha256: str
    pairing_sha256: str


@dataclass(frozen=True, slots=True)
class QualificationEvidence:
    """Non-metric qualification evidence required before ranking."""

    lineage: GateVerdict
    converter: GateVerdict
    evidence: GateVerdict
    budget: GateVerdict


@dataclass(frozen=True, slots=True)
class DevelopmentQualityReport:
    """Four fold reports plus the pooled out-of-fold report."""

    folds: tuple[FoldQualityReport, ...]
    pooled_row_count: int
    pooled_overall: QualityMetricReport
    pooled_subgroups: tuple[NamedQualityMetric, ...]
    pooled_bootstrap: BootstrapResult
    qualification_evidence: QualificationEvidence
    reason_codes: tuple[str, ...]
    pooled_inventory_sha256: str
    pooled_pairing_sha256: str


@dataclass(frozen=True, slots=True)
class QualificationResult:
    """Fail-closed qualification decision produced before ranking."""

    trial_id: str
    family_id: str
    verdict: GateVerdict
    qualified: bool
    reason_codes: tuple[str, ...]
    pooled_ucb95: float | None
    worst_fold_point: float | None
    worst_subgroup_ucb95: float | None


def _invalid_bootstrap(reason_code: str) -> BootstrapResult:
    return BootstrapResult(
        valid=False,
        reason_code=reason_code,
        resamples=_BOOTSTRAP_RESAMPLES,
        seed=_BOOTSTRAP_SEED,
        replicate_index=_BOOTSTRAP_INDEX,
    )


def _empty_metric(row_count: int) -> QualityMetricReport:
    return QualityMetricReport(
        row_count=row_count,
        stable_mae=None,
        candidate_mae=None,
        point_ratio=None,
        ucb95=None,
    )


def _metric_report(metric: RatioMetric) -> QualityMetricReport:
    return QualityMetricReport(
        row_count=metric.row_count,
        stable_mae=metric.stable_mae,
        candidate_mae=metric.candidate_mae,
        point_ratio=metric.point_ratio,
        ucb95=metric.ucb95,
    )


def _canonical_group_membership(groups: object) -> bool:
    return (
        type(groups) is tuple
        and len(groups) == 3
        and type(groups[0]) is str
        and groups[0] in _WEATHER_GROUPS
        and type(groups[1]) is str
        and groups[1] in _DAY_GROUPS
        and type(groups[2]) is str
        and groups[2] in _DEMAND_GROUPS
    )


def _valid_paired_row(row: object) -> bool:
    if (
        type(row) is not PairedQualityRow
        or type(row.request_id) is not str
        or not 1 <= len(row.request_id) <= 128
        or type(row.calendar_day) is not date
        or not _canonical_group_membership(row.groups)
    ):
        return False
    values = (row.stable_prediction, row.candidate_prediction, row.label)
    return all(
        type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in values
    )


def _row_inventory(
    rows: tuple[PairedQualityRow, ...],
) -> tuple[dict[str, int], tuple[str, ...]]:
    counts = {group: 0 for group in FIXED_SUBGROUPS}
    reasons: list[str] = []
    if any(not _valid_paired_row(row) for row in rows):
        reasons.append("INVALID_PAIRED_ROW")
        return counts, tuple(reasons)
    request_ids = [row.request_id for row in rows]
    if len(request_ids) != len(set(request_ids)):
        reasons.append("DUPLICATE_REQUEST_ID")
    for row in rows:
        if not _canonical_group_membership(row.groups):
            reasons.append("INVALID_SUBGROUP_MEMBERSHIP")
            continue
        for group in row.groups:
            counts[group] += 1
    return counts, tuple(dict.fromkeys(reasons))


def _valid_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _identity_material(identity: SourceRowIdentity) -> dict[str, object]:
    return {
        "fold_id": identity.fold_id,
        "request_id": identity.request_id,
        "local_timestamp": identity.local_timestamp,
        "source_position": identity.source_position,
    }


def _valid_source_identity(identity: object, fold_id: str) -> bool:
    if type(identity) is not SourceRowIdentity:
        return False
    if (
        type(identity.fold_id) is not str
        or identity.fold_id != fold_id
        or type(identity.request_id) is not str
        or not identity.request_id
        or type(identity.local_timestamp) is not str
        or not identity.local_timestamp
        or type(identity.source_position) is not int
        or identity.source_position < 0
        or not _valid_sha256(identity.identity_sha256)
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


def _valid_fold_context(context: object) -> bool:
    if (
        type(context) is not FoldQualificationContext
        or type(context.fold_id) is not str
        or context.fold_id not in FOLD_IDS
        or type(context.inventory) is not tuple
        or type(context.paired_rows) is not tuple
        or not context.inventory
        or len(context.inventory) != len(context.paired_rows)
    ):
        return False
    if any(not _valid_source_identity(identity, context.fold_id) for identity in context.inventory):
        return False
    counts, row_reasons = _row_inventory(context.paired_rows)
    if row_reasons or not counts:
        return False
    request_ids = [identity.request_id for identity in context.inventory]
    identity_digests = [identity.identity_sha256 for identity in context.inventory]
    local_timestamps = [identity.local_timestamp for identity in context.inventory]
    source_positions = [identity.source_position for identity in context.inventory]
    if (
        len(request_ids) != len(set(request_ids))
        or len(identity_digests) != len(set(identity_digests))
        or len(local_timestamps) != len(set(local_timestamps))
        or len(source_positions) != len(set(source_positions))
        or request_ids != [row.request_id for row in context.paired_rows]
    ):
        return False
    return all(
        datetime.fromisoformat(identity.local_timestamp).date() == row.calendar_day
        for identity, row in zip(context.inventory, context.paired_rows, strict=True)
    )


def _valid_qualification_context(context: object) -> bool:
    if (
        type(context) is not QualificationContext
        or type(context.folds) is not tuple
        or len(context.folds) != len(FOLD_IDS)
        or any(not _valid_fold_context(fold) for fold in context.folds)
        or tuple(fold.fold_id for fold in context.folds) != FOLD_IDS
    ):
        return False
    request_ids = [row.request_id for fold in context.folds for row in fold.paired_rows]
    identity_digests = [
        identity.identity_sha256 for fold in context.folds for identity in fold.inventory
    ]
    return len(request_ids) == len(set(request_ids)) and len(identity_digests) == len(
        set(identity_digests)
    )


def _inventory_digest(inventory: tuple[SourceRowIdentity, ...]) -> str:
    return sha256_hex(canonicalize_json([identity.identity_sha256 for identity in inventory]))


def _pairing_digest(context: FoldQualificationContext) -> str:
    pair_digests = []
    for identity, row in zip(context.inventory, context.paired_rows, strict=True):
        pair_digests.append(
            sha256_hex(
                canonicalize_json(
                    {
                        "identity_sha256": identity.identity_sha256,
                        "request_id": row.request_id,
                        "calendar_day": row.calendar_day.isoformat(),
                        "stable_prediction": row.stable_prediction,
                        "candidate_prediction": row.candidate_prediction,
                        "label": row.label,
                        "groups": list(row.groups),
                    }
                )
            )
        )
    return sha256_hex(canonicalize_json(pair_digests))


def _pooled_digest(fold_digests: Sequence[str]) -> str:
    return sha256_hex(canonicalize_json(list(fold_digests)))


def _valid_pass_layer(
    layer: object,
    row_count: int,
    reason_inventory: tuple[str, ...],
) -> bool:
    if type(layer) is not LayerAccounting:
        return False
    counters = (
        layer.expected_count,
        layer.observed_count,
        layer.success_count,
        layer.failure_count,
        layer.missing_count,
        layer.duplicate_count,
        layer.unexpected_count,
        layer.invalid_count,
    )
    if any(type(value) is not int or value < 0 for value in counters):
        return False
    if (
        layer.expected_count != row_count
        or layer.observed_count != row_count
        or layer.success_count != row_count
        or any(value != 0 for value in counters[3:])
    ):
        return False
    if type(layer.reason_counts) is not tuple or len(layer.reason_counts) != len(reason_inventory):
        return False
    for entry, expected_reason in zip(layer.reason_counts, reason_inventory, strict=True):
        if (
            type(entry) is not tuple
            or len(entry) != 2
            or type(entry[0]) is not str
            or entry[0] != expected_reason
            or type(entry[1]) is not int
            or entry[1] != 0
        ):
            return False
    return True


def _complete_receipt(receipt: object, row_count: int) -> bool:
    if type(receipt) is not CompletenessReceipt:
        return False
    if (
        receipt.verdict is not GateVerdict.PASS
        or type(receipt.reason_codes) is not tuple
        or receipt.reason_codes != ()
        or type(receipt.source_count) is not int
        or receipt.source_count != row_count
    ):
        return False
    return (
        _valid_pass_layer(receipt.adapter, row_count, ADAPTER_REASON_CODES)
        and _valid_pass_layer(receipt.stable, row_count, PREDICTION_REASON_CODES)
        and _valid_pass_layer(receipt.candidate, row_count, PREDICTION_REASON_CODES)
        and _valid_pass_layer(receipt.label, row_count, LABEL_REASON_CODES)
    )


def _reports_from_bootstrap(
    result: BootstrapResult, counts: Mapping[str, int], row_count: int
) -> tuple[QualityMetricReport, tuple[NamedQualityMetric, ...]]:
    overall = (
        _metric_report(result.overall)
        if result.valid and result.overall
        else _empty_metric(row_count)
    )
    subgroups = tuple(
        NamedQualityMetric(
            name=group,
            metric=(
                _metric_report(result.subgroups[group])
                if result.valid and group in result.subgroups
                else _empty_metric(counts[group])
            ),
        )
        for group in FIXED_SUBGROUPS
    )
    return overall, subgroups


def evaluate_fold(
    context: FoldQualificationContext,
    completeness: CompletenessReceipt,
) -> FoldQualityReport:
    """Evaluate one fold with the unchanged paired calendar-day bootstrap."""
    if not _valid_fold_context(context):
        raise ValueError("fold qualification context is invalid")
    fold_id = context.fold_id
    row_tuple = context.paired_rows
    counts, row_reasons = _row_inventory(row_tuple)
    reasons: list[str] = list(row_reasons)
    if not _complete_receipt(completeness, len(row_tuple)):
        reasons.append(f"INCOMPLETE_ACCOUNTING:{fold_id}")

    if reasons:
        bootstrap = _invalid_bootstrap(reasons[0])
    else:
        bootstrap = cluster_bootstrap_ratios(
            row_tuple,
            FIXED_SUBGROUPS,
            _BOOTSTRAP_RESAMPLES,
            _BOOTSTRAP_SEED,
        )
        if not bootstrap.valid:
            reasons.append(bootstrap.reason_code or "INVALID_BOOTSTRAP")

    for group in FIXED_SUBGROUPS:
        if counts[group] < _MIN_SUBGROUP_ROWS:
            reasons.append(f"INSUFFICIENT_SUBGROUP_ROWS:{fold_id}:{group}")
    overall, subgroups = _reports_from_bootstrap(bootstrap, counts, len(row_tuple))
    return FoldQualityReport(
        fold_id=fold_id,
        completeness=completeness,
        paired_row_count=len(row_tuple),
        overall=overall,
        subgroups=subgroups,
        bootstrap=bootstrap,
        reason_codes=tuple(dict.fromkeys(reasons)),
        inventory_sha256=_inventory_digest(context.inventory),
        pairing_sha256=_pairing_digest(context),
    )


def evaluate_pooled(
    context: QualificationContext,
    completeness_by_fold: Mapping[str, CompletenessReceipt],
    qualification_evidence: QualificationEvidence,
) -> DevelopmentQualityReport:
    """Evaluate the exact four folds and their disjoint pooled out-of-fold union."""
    if not _valid_qualification_context(context):
        raise ValueError("qualification context is invalid")
    if not isinstance(completeness_by_fold, Mapping) or set(completeness_by_fold) != set(FOLD_IDS):
        raise ValueError("completeness inventory is invalid")

    reports = tuple(
        evaluate_fold(fold, completeness_by_fold[fold.fold_id]) for fold in context.folds
    )
    pooled_rows = tuple(row for fold in context.folds for row in fold.paired_rows)
    counts, row_reasons = _row_inventory(pooled_rows)
    reasons: list[str] = list(row_reasons)
    seen_days: set[object] = set()
    for fold in context.folds:
        fold_days = {row.calendar_day for row in fold.paired_rows}
        if seen_days.intersection(fold_days):
            reasons.append("OVERLAPPING_FOLD_CALENDAR_DAY")
        seen_days.update(fold_days)

    can_evaluate = (
        not reasons
        and len(reports) == len(FOLD_IDS)
        and all(
            _complete_receipt(report.completeness, report.paired_row_count)
            and report.bootstrap.valid
            for report in reports
        )
    )
    if can_evaluate:
        bootstrap = cluster_bootstrap_ratios(
            pooled_rows,
            FIXED_SUBGROUPS,
            _BOOTSTRAP_RESAMPLES,
            _BOOTSTRAP_SEED,
        )
        if not bootstrap.valid:
            reasons.append(bootstrap.reason_code or "INVALID_BOOTSTRAP")
    else:
        bootstrap = _invalid_bootstrap(reasons[0] if reasons else "INVALID_FOLD_EVIDENCE")

    for group in FIXED_SUBGROUPS:
        if counts[group] < _MIN_SUBGROUP_ROWS:
            reasons.append(f"INSUFFICIENT_SUBGROUP_ROWS:POOLED:{group}")
    overall, subgroups = _reports_from_bootstrap(bootstrap, counts, len(pooled_rows))
    return DevelopmentQualityReport(
        folds=reports,
        pooled_row_count=len(pooled_rows),
        pooled_overall=overall,
        pooled_subgroups=subgroups,
        pooled_bootstrap=bootstrap,
        qualification_evidence=qualification_evidence,
        reason_codes=tuple(dict.fromkeys(reasons)),
        pooled_inventory_sha256=_pooled_digest([report.inventory_sha256 for report in reports]),
        pooled_pairing_sha256=_pooled_digest([report.pairing_sha256 for report in reports]),
    )


def _valid_metric(metric: object) -> bool:
    if type(metric) is not QualityMetricReport or type(metric.row_count) is not int:
        return False
    if metric.row_count <= 0:
        return False
    values = (metric.stable_mae, metric.candidate_mae, metric.point_ratio, metric.ucb95)
    if not all(
        type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in values
    ):
        return False
    stable_mae, candidate_mae, point_ratio, _ = values
    return stable_mae > 0 and math.isclose(
        candidate_mae / stable_mae,
        point_ratio,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def _metric_matches_bootstrap(metric: QualityMetricReport, bootstrap: RatioMetric) -> bool:
    return (
        metric.row_count == bootstrap.row_count
        and metric.stable_mae == bootstrap.stable_mae
        and metric.candidate_mae == bootstrap.candidate_mae
        and metric.point_ratio == bootstrap.point_ratio
        and metric.ucb95 == bootstrap.ucb95
    )


def _bootstrap_is_frozen(bootstrap: object) -> bool:
    return (
        type(bootstrap) is BootstrapResult
        and bootstrap.valid is True
        and bootstrap.reason_code is None
        and bootstrap.overall is not None
        and type(bootstrap.resamples) is int
        and bootstrap.resamples == _BOOTSTRAP_RESAMPLES
        and type(bootstrap.seed) is int
        and bootstrap.seed == _BOOTSTRAP_SEED
        and type(bootstrap.replicate_index) is int
        and bootstrap.replicate_index == _BOOTSTRAP_INDEX
        and tuple(bootstrap.subgroups) == FIXED_SUBGROUPS
    )


def _subgroups_are_valid(
    scope: str,
    entries: object,
    bootstrap: BootstrapResult,
    unknown: list[str],
) -> bool:
    if (
        type(entries) is not tuple
        or tuple(entry.name for entry in entries if type(entry) is NamedQualityMetric)
        != FIXED_SUBGROUPS
        or any(type(entry) is not NamedQualityMetric for entry in entries)
    ):
        unknown.append(f"INVALID_SUBGROUP_INVENTORY:{scope}")
        return False
    valid = True
    for entry in entries:
        if (
            type(entry.metric) is QualityMetricReport
            and type(entry.metric.row_count) is int
            and entry.metric.row_count < _MIN_SUBGROUP_ROWS
        ):
            unknown.append(f"INSUFFICIENT_SUBGROUP_ROWS:{scope}:{entry.name}")
            valid = False
        if not _valid_metric(entry.metric):
            unknown.append(f"INVALID_SUBGROUP_METRIC:{scope}:{entry.name}")
            valid = False
            continue
        bootstrap_metric = bootstrap.subgroups.get(entry.name)
        if bootstrap_metric is None or not _metric_matches_bootstrap(
            entry.metric, bootstrap_metric
        ):
            unknown.append(f"INVALID_SUBGROUP_METRIC:{scope}:{entry.name}")
            valid = False
    return valid


def _exact_subgroup_inventory(entries: object) -> bool:
    return (
        type(entries) is tuple
        and len(entries) == len(FIXED_SUBGROUPS)
        and all(type(entry) is NamedQualityMetric for entry in entries)
        and tuple(entry.name for entry in entries) == FIXED_SUBGROUPS
    )


def _report_shape_reasons(report: DevelopmentQualityReport) -> list[str]:
    if (
        type(report.folds) is not tuple
        or len(report.folds) != len(FOLD_IDS)
        or any(type(fold) is not FoldQualityReport for fold in report.folds)
        or tuple(fold.fold_id for fold in report.folds) != FOLD_IDS
    ):
        return ["INVALID_FOLD_INVENTORY"]
    for fold in report.folds:
        if type(fold.paired_row_count) is not int or fold.paired_row_count < 0:
            return ["INVALID_REPORT_SHAPE"]
        if not _valid_sha256(fold.inventory_sha256) or not _valid_sha256(fold.pairing_sha256):
            return ["INVALID_REPORT_SHAPE"]
        if not _exact_subgroup_inventory(fold.subgroups):
            return [f"INVALID_SUBGROUP_INVENTORY:{fold.fold_id}"]
    if type(report.pooled_row_count) is not int or report.pooled_row_count < 0:
        return ["INVALID_REPORT_SHAPE"]
    if not _valid_sha256(report.pooled_inventory_sha256) or not _valid_sha256(
        report.pooled_pairing_sha256
    ):
        return ["INVALID_REPORT_SHAPE"]
    if not _exact_subgroup_inventory(report.pooled_subgroups):
        return ["INVALID_SUBGROUP_INVENTORY:POOLED"]
    if (
        type(report.reason_codes) is not tuple
        or any(type(reason) is not str for reason in report.reason_codes)
        or any(
            type(fold.reason_codes) is not tuple
            or any(type(reason) is not str for reason in fold.reason_codes)
            for fold in report.folds
        )
    ):
        return ["INVALID_REPORT_SHAPE"]
    return []


def _partition_reasons(
    scope: str,
    entries: tuple[NamedQualityMetric, ...],
    denominator: int,
) -> list[str]:
    counts = {entry.name: entry.metric.row_count for entry in entries}
    partitions = (
        ("weather", FIXED_SUBGROUPS[:3]),
        ("day", FIXED_SUBGROUPS[3:5]),
        ("demand", FIXED_SUBGROUPS[5:]),
    )
    return [
        f"INVALID_PARTITION_TOTAL:{scope}:{name}"
        for name, groups in partitions
        if sum(counts[group] for group in groups) != denominator
    ]


def _fold_unknown_reasons(report: DevelopmentQualityReport) -> list[str]:
    unknown: list[str] = []
    for fold in report.folds:
        if not _complete_receipt(fold.completeness, fold.paired_row_count):
            unknown.append(f"INCOMPLETE_ACCOUNTING:{fold.fold_id}")
        unknown.extend(fold.reason_codes)
        if not _bootstrap_is_frozen(fold.bootstrap):
            unknown.append(f"INVALID_BOOTSTRAP:{fold.fold_id}")
            continue
        if not _valid_metric(fold.overall) or not _metric_matches_bootstrap(
            fold.overall, fold.bootstrap.overall
        ):
            unknown.append(f"INVALID_OVERALL_METRIC:{fold.fold_id}")
        elif fold.overall.row_count != fold.paired_row_count:
            unknown.append(f"INVALID_OVERALL_ROW_COUNT:{fold.fold_id}")
        if _subgroups_are_valid(fold.fold_id, fold.subgroups, fold.bootstrap, unknown):
            unknown.extend(_partition_reasons(fold.fold_id, fold.subgroups, fold.paired_row_count))
    return unknown


def _weighted_sum(metric: QualityMetricReport, row_count: int, attribute: str) -> float:
    return float(getattr(metric, attribute)) * row_count


def _pooled_aggregate_reasons(report: DevelopmentQualityReport) -> list[str]:
    reasons: list[str] = []
    for attribute in ("stable_mae", "candidate_mae"):
        pooled_sum = _weighted_sum(report.pooled_overall, report.pooled_row_count, attribute)
        fold_sum = sum(
            _weighted_sum(fold.overall, fold.paired_row_count, attribute) for fold in report.folds
        )
        if not math.isclose(pooled_sum, fold_sum, rel_tol=1e-12, abs_tol=1e-12):
            reasons.append("INVALID_POOLED_AGGREGATE:overall")
            break

    fold_subgroups = [
        {entry.name: entry.metric for entry in fold.subgroups} for fold in report.folds
    ]
    pooled_subgroups = {entry.name: entry.metric for entry in report.pooled_subgroups}
    for group in FIXED_SUBGROUPS:
        pooled_metric = pooled_subgroups[group]
        for attribute in ("stable_mae", "candidate_mae"):
            pooled_sum = _weighted_sum(pooled_metric, pooled_metric.row_count, attribute)
            fold_sum = sum(
                _weighted_sum(metrics[group], metrics[group].row_count, attribute)
                for metrics in fold_subgroups
            )
            if not math.isclose(pooled_sum, fold_sum, rel_tol=1e-12, abs_tol=1e-12):
                reasons.append(f"INVALID_POOLED_AGGREGATE:{group}")
                break
    return reasons


def _pooled_unknown_reasons(report: DevelopmentQualityReport) -> list[str]:
    unknown: list[str] = list(report.reason_codes)
    if report.pooled_row_count != sum(fold.paired_row_count for fold in report.folds):
        unknown.append("INVALID_POOLED_ROW_COUNT")
    if not _bootstrap_is_frozen(report.pooled_bootstrap):
        unknown.append("INVALID_BOOTSTRAP:POOLED")
        return unknown
    if not _valid_metric(report.pooled_overall) or not _metric_matches_bootstrap(
        report.pooled_overall, report.pooled_bootstrap.overall
    ):
        unknown.append("INVALID_OVERALL_METRIC:POOLED")
    elif report.pooled_overall.row_count != report.pooled_row_count:
        unknown.append("INVALID_OVERALL_ROW_COUNT:POOLED")
    if _subgroups_are_valid("POOLED", report.pooled_subgroups, report.pooled_bootstrap, unknown):
        fold_subgroups = [
            {entry.name: entry.metric for entry in fold.subgroups} for fold in report.folds
        ]
        fold_counts = {
            group: sum(metrics[group].row_count for metrics in fold_subgroups)
            for group in FIXED_SUBGROUPS
        }
        for entry in report.pooled_subgroups:
            if entry.metric.row_count != fold_counts[entry.name]:
                unknown.append(f"INVALID_POOLED_SUBGROUP_COUNT:{entry.name}")
        unknown.extend(
            _partition_reasons("POOLED", report.pooled_subgroups, report.pooled_row_count)
        )
        unknown.extend(_pooled_aggregate_reasons(report))
    return unknown


def _report_matches_context(
    report: DevelopmentQualityReport,
    context: QualificationContext,
) -> bool:
    receipts: dict[str, CompletenessReceipt] = {}
    for fold in report.folds:
        receipts[fold.fold_id] = fold.completeness
    recomputed = evaluate_pooled(
        context,
        receipts,
        report.qualification_evidence,
    )
    return report == recomputed


def _evidence_unknown_reasons(evidence: object) -> list[str]:
    if type(evidence) is not QualificationEvidence:
        return ["INVALID_QUALIFICATION_EVIDENCE"]
    reasons: list[str] = []
    for field in ("lineage", "converter", "evidence", "budget"):
        if getattr(evidence, field) is not GateVerdict.PASS:
            reasons.append(f"{field.upper()}_NOT_PASS")
    return reasons


def _qualification_result(
    report: DevelopmentQualityReport | None,
    *,
    trial_id: str,
    family_id: str,
    verdict: GateVerdict,
    qualified: bool,
    reason_codes: tuple[str, ...],
) -> QualificationResult:
    metrics_available = (
        report is not None
        and _valid_metric(report.pooled_overall)
        and type(report.folds) is tuple
        and len(report.folds) == len(FOLD_IDS)
        and all(
            type(fold) is FoldQualityReport and _valid_metric(fold.overall) for fold in report.folds
        )
        and type(report.pooled_subgroups) is tuple
        and len(report.pooled_subgroups) == len(FIXED_SUBGROUPS)
        and all(
            type(entry) is NamedQualityMetric and _valid_metric(entry.metric)
            for entry in report.pooled_subgroups
        )
    )
    return QualificationResult(
        trial_id=trial_id,
        family_id=family_id,
        verdict=verdict,
        qualified=qualified,
        reason_codes=reason_codes,
        pooled_ucb95=report.pooled_overall.ucb95 if metrics_available else None,
        worst_fold_point=(
            max(fold.overall.point_ratio for fold in report.folds) if metrics_available else None
        ),
        worst_subgroup_ucb95=(
            max(entry.metric.ucb95 for entry in report.pooled_subgroups)
            if metrics_available
            else None
        ),
    )


def qualify_trial(
    report: DevelopmentQualityReport,
    context: QualificationContext | None = None,
    *,
    trial_id: str = "",
    family_id: str = "",
) -> QualificationResult:
    """Qualify one final-eligible trial before ranking, preserving FAIL/UNKNOWN."""
    if type(report) is not DevelopmentQualityReport:
        return _qualification_result(
            None,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=("INVALID_DEVELOPMENT_REPORT",),
        )

    shape_reasons = _report_shape_reasons(report)
    if shape_reasons:
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=tuple(shape_reasons),
        )

    if context is None:
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=("QUALIFICATION_CONTEXT_REQUIRED",),
        )
    if not _valid_qualification_context(context):
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=("QUALIFICATION_CONTEXT_INVALID",),
        )

    completeness_reasons = [
        f"INCOMPLETE_ACCOUNTING:{fold.fold_id}"
        for fold in report.folds
        if not _complete_receipt(fold.completeness, fold.paired_row_count)
    ]
    if completeness_reasons:
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=tuple(completeness_reasons),
        )

    if not _report_matches_context(report, context):
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=("QUALIFICATION_CONTEXT_MISMATCH",),
        )

    unknown = _fold_unknown_reasons(report)
    unknown.extend(_pooled_unknown_reasons(report))
    unknown.extend(_evidence_unknown_reasons(report.qualification_evidence))
    unknown = list(dict.fromkeys(unknown))
    if unknown:
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=tuple(unknown),
        )

    failures: list[str] = []
    if report.pooled_overall.point_ratio > _POOLED_OVERALL_MAX_RATIO:
        failures.append("POOLED_OVERALL_POINT_RATIO")
    if report.pooled_overall.ucb95 > _POOLED_OVERALL_MAX_RATIO:
        failures.append("POOLED_OVERALL_UCB95")
    for entry in report.pooled_subgroups:
        if entry.metric.point_ratio > _POOLED_SUBGROUP_MAX_RATIO:
            failures.append(f"POOLED_SUBGROUP_POINT_RATIO:{entry.name}")
        if entry.metric.ucb95 > _POOLED_SUBGROUP_MAX_RATIO:
            failures.append(f"POOLED_SUBGROUP_UCB95:{entry.name}")
    fold_points = tuple(fold.overall.point_ratio for fold in report.folds)
    for fold, point_ratio in zip(report.folds, fold_points, strict=True):
        if point_ratio > _FOLD_OVERALL_MAX_RATIO:
            failures.append(f"FOLD_OVERALL_POINT_RATIO:{fold.fold_id}")
    if sum(point <= 1.0 for point in fold_points) < _MIN_FOLDS_AT_OR_BELOW_ONE:
        failures.append("FOLD_STABILITY")

    if failures:
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.FAIL,
            qualified=False,
            reason_codes=tuple(failures),
        )
    return _qualification_result(
        report,
        trial_id=trial_id,
        family_id=family_id,
        verdict=GateVerdict.PASS,
        qualified=True,
        reason_codes=(),
    )
