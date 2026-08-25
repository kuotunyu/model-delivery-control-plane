"""Frozen fold and pooled temporal-development quality qualification."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import (
    BootstrapResult,
    PairedQualityRow,
    RatioMetric,
    cluster_bootstrap_ratios,
)
from mdcp.temporal.completeness import CompletenessReceipt

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
class FoldQualityReport:
    """Completeness and frozen quality statistics for one development fold."""

    fold_id: str
    completeness: CompletenessReceipt
    paired_row_count: int
    overall: QualityMetricReport
    subgroups: tuple[NamedQualityMetric, ...]
    bootstrap: BootstrapResult
    reason_codes: tuple[str, ...]


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


def _row_inventory(
    rows: tuple[PairedQualityRow, ...],
) -> tuple[dict[str, int], tuple[str, ...]]:
    counts = {group: 0 for group in FIXED_SUBGROUPS}
    reasons: list[str] = []
    if any(type(row) is not PairedQualityRow for row in rows):
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


def _complete_receipt(receipt: object, row_count: int) -> bool:
    if type(receipt) is not CompletenessReceipt:
        return False
    if (
        receipt.verdict is not GateVerdict.PASS
        or receipt.reason_codes
        or receipt.source_count != row_count
    ):
        return False
    return all(
        layer.complete
        and layer.expected_count == row_count
        and layer.observed_count == row_count
        and layer.success_count == row_count
        for layer in (receipt.adapter, receipt.stable, receipt.candidate, receipt.label)
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
    fold_id: str,
    rows: Sequence[PairedQualityRow],
    completeness: CompletenessReceipt,
) -> FoldQualityReport:
    """Evaluate one fold with the unchanged paired calendar-day bootstrap."""
    row_tuple = tuple(rows)
    counts, row_reasons = _row_inventory(row_tuple)
    reasons: list[str] = list(row_reasons)
    if type(fold_id) is not str or fold_id not in FOLD_IDS:
        reasons.append("INVALID_FOLD_ID")
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
    )


def evaluate_pooled(
    fold_rows: Mapping[str, Sequence[PairedQualityRow]],
    completeness_by_fold: Mapping[str, CompletenessReceipt],
    qualification_evidence: QualificationEvidence,
) -> DevelopmentQualityReport:
    """Evaluate the exact four folds and their disjoint pooled out-of-fold union."""
    reasons: list[str] = []
    if (
        not isinstance(fold_rows, Mapping)
        or not isinstance(completeness_by_fold, Mapping)
        or set(fold_rows) != set(FOLD_IDS)
        or set(completeness_by_fold) != set(FOLD_IDS)
    ):
        reasons.append("INVALID_FOLD_INVENTORY")

    reports = tuple(
        evaluate_fold(fold_id, fold_rows[fold_id], completeness_by_fold[fold_id])
        for fold_id in FOLD_IDS
        if fold_id in fold_rows and fold_id in completeness_by_fold
    )
    pooled_rows = tuple(
        row for fold_id in FOLD_IDS if fold_id in fold_rows for row in fold_rows[fold_id]
    )
    counts, row_reasons = _row_inventory(pooled_rows)
    reasons.extend(row_reasons)
    seen_days: set[object] = set()
    for fold_id in FOLD_IDS:
        fold_days = (
            {row.calendar_day for row in fold_rows[fold_id]}
            if fold_id in fold_rows
            and all(type(row) is PairedQualityRow for row in fold_rows[fold_id])
            else set()
        )
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
        and bootstrap.valid
        and bootstrap.reason_code is None
        and bootstrap.overall is not None
        and bootstrap.resamples == _BOOTSTRAP_RESAMPLES
        and bootstrap.seed == _BOOTSTRAP_SEED
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


def _fold_unknown_reasons(report: DevelopmentQualityReport) -> list[str]:
    unknown: list[str] = []
    if (
        type(report.folds) is not tuple
        or tuple(fold.fold_id for fold in report.folds if type(fold) is FoldQualityReport)
        != FOLD_IDS
        or any(type(fold) is not FoldQualityReport for fold in report.folds)
    ):
        return ["INVALID_FOLD_INVENTORY"]

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
        _subgroups_are_valid(fold.fold_id, fold.subgroups, fold.bootstrap, unknown)
    return unknown


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
    if _subgroups_are_valid("POOLED", report.pooled_subgroups, report.pooled_bootstrap, unknown):
        fold_counts = {
            group: sum(
                next(entry.metric.row_count for entry in fold.subgroups if entry.name == group)
                for fold in report.folds
            )
            for group in FIXED_SUBGROUPS
        }
        for entry in report.pooled_subgroups:
            if entry.metric.row_count != fold_counts[entry.name]:
                unknown.append(f"INVALID_POOLED_SUBGROUP_COUNT:{entry.name}")
    return unknown


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

    unknown = _fold_unknown_reasons(report)
    if "INVALID_FOLD_INVENTORY" in unknown:
        return _qualification_result(
            report,
            trial_id=trial_id,
            family_id=family_id,
            verdict=GateVerdict.UNKNOWN,
            qualified=False,
            reason_codes=tuple(dict.fromkeys(unknown)),
        )
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
