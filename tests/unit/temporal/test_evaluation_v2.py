from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from types import MappingProxyType

import pytest

from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import BootstrapResult, PairedQualityRow, RatioMetric
from mdcp.temporal.completeness import (
    ADAPTER_REASON_CODES,
    LABEL_REASON_CODES,
    PREDICTION_REASON_CODES,
    CompletenessReceipt,
    LayerAccounting,
)
from mdcp.temporal.evaluation import (
    FIXED_SUBGROUPS,
    FOLD_IDS,
    DevelopmentQualityReport,
    FoldQualityReport,
    NamedQualityMetric,
    QualificationEvidence,
    QualityMetricReport,
    evaluate_fold,
    evaluate_pooled,
    qualify_trial,
)


def _layer(count: int, reason_codes: tuple[str, ...]) -> LayerAccounting:
    return LayerAccounting(
        expected_count=count,
        observed_count=count,
        success_count=count,
        failure_count=0,
        missing_count=0,
        duplicate_count=0,
        unexpected_count=0,
        invalid_count=0,
        reason_counts=tuple((reason, 0) for reason in reason_codes),
    )


def _complete_receipt(count: int) -> CompletenessReceipt:
    return CompletenessReceipt(
        verdict=GateVerdict.PASS,
        reason_codes=(),
        source_count=count,
        adapter=_layer(count, ADAPTER_REASON_CODES),
        stable=_layer(count, PREDICTION_REASON_CODES),
        candidate=_layer(count, PREDICTION_REASON_CODES),
        label=_layer(count, LABEL_REASON_CODES),
    )


def _rows(fold_id: str, *, ratio: float = 0.90) -> tuple[PairedQualityRow, ...]:
    start = date(2011, 7, 1) + timedelta(days=100 * (int(fold_id[1]) - 1))
    rows: list[PairedQualityRow] = []
    weather_groups = ("weather_clear", "weather_mist", "weather_adverse")
    for position in range(300):
        rows.append(
            PairedQualityRow(
                request_id=f"{fold_id}-{position:04d}",
                calendar_day=start + timedelta(days=position // 30),
                stable_prediction=20.0,
                candidate_prediction=10.0 + 10.0 * ratio,
                label=10.0,
                groups=(
                    weather_groups[position % 3],
                    "day_working" if position % 2 else "day_non_working",
                    "demand_peak" if position % 2 else "demand_off_peak",
                ),
            )
        )
    return tuple(rows)


def _quality_metric(
    *, point_ratio: float = 0.90, ucb95: float = 0.90, row_count: int = 300
) -> QualityMetricReport:
    return QualityMetricReport(
        row_count=row_count,
        stable_mae=10.0,
        candidate_mae=10.0 * point_ratio,
        point_ratio=point_ratio,
        ucb95=ucb95,
    )


def _bootstrap(
    *, point_ratio: float = 0.90, ucb95: float = 0.90, row_count: int = 300
) -> BootstrapResult:
    overall = RatioMetric(
        row_count=row_count,
        stable_mae=10.0,
        candidate_mae=10.0 * point_ratio,
        point_ratio=point_ratio,
        ucb95=ucb95,
    )
    return BootstrapResult(
        valid=True,
        overall=overall,
        subgroups={
            group: RatioMetric(
                row_count=100 if group.startswith("weather_") else 150,
                stable_mae=10.0,
                candidate_mae=9.0,
                point_ratio=0.90,
                ucb95=0.90,
            )
            for group in FIXED_SUBGROUPS
        },
        resamples=2000,
        seed=2026,
        replicate_index=1899,
    )


def _fold_report(fold_id: str, *, point: float = 0.90) -> FoldQualityReport:
    return FoldQualityReport(
        fold_id=fold_id,
        completeness=_complete_receipt(300),
        paired_row_count=300,
        overall=_quality_metric(point_ratio=point, ucb95=point),
        subgroups=tuple(
            NamedQualityMetric(
                name=group,
                metric=_quality_metric(row_count=100 if group.startswith("weather_") else 150),
            )
            for group in FIXED_SUBGROUPS
        ),
        bootstrap=_bootstrap(point_ratio=point, ucb95=point),
        reason_codes=(),
    )


def _report_with(
    *,
    pooled_point: float = 0.90,
    pooled_ucb: float = 0.90,
    subgroup_points: tuple[float, ...] | None = None,
    subgroup_ucbs: tuple[float, ...] | None = None,
    subgroup_counts: tuple[int, ...] | None = None,
    fold_points: tuple[float, ...] = (0.90, 0.90, 0.90, 0.90),
    evidence: QualificationEvidence | None = None,
) -> DevelopmentQualityReport:
    subgroup_points = subgroup_points or (0.90,) * len(FIXED_SUBGROUPS)
    subgroup_ucbs = subgroup_ucbs or (0.90,) * len(FIXED_SUBGROUPS)
    subgroup_counts = subgroup_counts or (400, 400, 400, 600, 600, 600, 600)
    pooled_subgroups = tuple(
        NamedQualityMetric(
            name=group,
            metric=_quality_metric(
                point_ratio=point,
                ucb95=ucb,
                row_count=count,
            ),
        )
        for group, point, ucb, count in zip(
            FIXED_SUBGROUPS,
            subgroup_points,
            subgroup_ucbs,
            subgroup_counts,
            strict=True,
        )
    )
    pooled_bootstrap = BootstrapResult(
        valid=True,
        overall=RatioMetric(
            row_count=1200,
            stable_mae=10.0,
            candidate_mae=10.0 * pooled_point,
            point_ratio=pooled_point,
            ucb95=pooled_ucb,
        ),
        subgroups={
            entry.name: RatioMetric(
                row_count=entry.metric.row_count,
                stable_mae=entry.metric.stable_mae or 0.0,
                candidate_mae=entry.metric.candidate_mae or 0.0,
                point_ratio=entry.metric.point_ratio or 0.0,
                ucb95=entry.metric.ucb95 or 0.0,
            )
            for entry in pooled_subgroups
        },
        resamples=2000,
        seed=2026,
        replicate_index=1899,
    )
    return DevelopmentQualityReport(
        folds=tuple(
            _fold_report(fold_id, point=point)
            for fold_id, point in zip(FOLD_IDS, fold_points, strict=True)
        ),
        pooled_row_count=1200,
        pooled_overall=_quality_metric(
            point_ratio=pooled_point,
            ucb95=pooled_ucb,
            row_count=1200,
        ),
        pooled_subgroups=pooled_subgroups,
        pooled_bootstrap=pooled_bootstrap,
        qualification_evidence=evidence
        or QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
        reason_codes=(),
    )


def test_fold_evaluation_uses_frozen_bootstrap_and_reports_all_groups() -> None:
    rows = _rows("F1")

    report = evaluate_fold("F1", rows, _complete_receipt(len(rows)))

    assert report.reason_codes == ()
    assert report.bootstrap.valid is True
    assert report.bootstrap.resamples == 2000
    assert report.bootstrap.seed == 2026
    assert report.bootstrap.replicate_index == 1899
    assert report.overall.point_ratio == pytest.approx(0.90)
    assert tuple(entry.name for entry in report.subgroups) == FIXED_SUBGROUPS
    assert tuple(entry.metric.row_count for entry in report.subgroups) == (
        100,
        100,
        100,
        150,
        150,
        150,
        150,
    )


def test_pooled_evaluation_is_the_disjoint_union_of_exactly_four_folds() -> None:
    fold_rows = {fold_id: _rows(fold_id) for fold_id in FOLD_IDS}
    receipts = {fold_id: _complete_receipt(len(rows)) for fold_id, rows in fold_rows.items()}

    report = evaluate_pooled(
        fold_rows,
        receipts,
        QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
    )

    assert tuple(fold.fold_id for fold in report.folds) == FOLD_IDS
    assert report.pooled_row_count == 1200
    assert report.pooled_bootstrap.valid is True
    assert report.pooled_overall.point_ratio == pytest.approx(0.90)
    assert tuple(entry.name for entry in report.pooled_subgroups) == FIXED_SUBGROUPS


def test_pooled_evaluation_normalizes_mapping_order_without_changing_fold_order() -> None:
    fold_rows = {fold_id: _rows(fold_id) for fold_id in reversed(FOLD_IDS)}
    receipts = {
        fold_id: _complete_receipt(len(fold_rows[fold_id])) for fold_id in reversed(FOLD_IDS)
    }

    report = evaluate_pooled(
        MappingProxyType(fold_rows),
        MappingProxyType(receipts),
        QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
    )

    assert report.reason_codes == ()
    assert tuple(fold.fold_id for fold in report.folds) == FOLD_IDS


def test_pooled_evaluation_rejects_calendar_day_overlap_between_folds() -> None:
    fold_rows = {fold_id: _rows(fold_id) for fold_id in FOLD_IDS}
    fold_rows["F2"] = tuple(
        row.model_copy(update={"calendar_day": fold_rows["F1"][position].calendar_day})
        for position, row in enumerate(fold_rows["F2"])
    )
    receipts = {fold_id: _complete_receipt(len(rows)) for fold_id, rows in fold_rows.items()}

    report = evaluate_pooled(
        fold_rows,
        receipts,
        QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
    )

    assert report.pooled_bootstrap.valid is False
    assert "OVERLAPPING_FOLD_CALENDAR_DAY" in report.reason_codes
    assert qualify_trial(report).verdict is GateVerdict.UNKNOWN


def test_qualification_accepts_every_frozen_threshold_at_its_boundary() -> None:
    result = qualify_trial(
        _report_with(
            pooled_point=0.97,
            pooled_ucb=0.97,
            subgroup_points=(1.05,) * len(FIXED_SUBGROUPS),
            subgroup_ucbs=(1.05,) * len(FIXED_SUBGROUPS),
            fold_points=(0.99, 1.00, 0.98, 1.04),
        )
    )

    assert result.qualified is True
    assert result.verdict is GateVerdict.PASS
    assert result.reason_codes == ()


def test_qualification_result_carries_the_exact_selection_key_inputs() -> None:
    result = qualify_trial(
        _report_with(
            pooled_ucb=0.96,
            subgroup_ucbs=(1.01, 1.02, 1.03, 1.04, 1.05, 1.00, 0.99),
            fold_points=(0.91, 0.92, 0.93, 1.04),
        ),
        trial_id="STAT-A1",
        family_id="STAT",
    )

    assert result.trial_id == "STAT-A1"
    assert result.family_id == "STAT"
    assert result.pooled_ucb95 == 0.96
    assert result.worst_fold_point == 1.04
    assert result.worst_subgroup_ucb95 == 1.05


def test_one_fold_only_win_does_not_qualify() -> None:
    result = qualify_trial(_report_with(fold_points=(0.80, 1.01, 1.02, 1.03)))

    assert result.qualified is False
    assert result.verdict is GateVerdict.FAIL
    assert "FOLD_STABILITY" in result.reason_codes


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"pooled_point": 0.9700001}, "POOLED_OVERALL_POINT_RATIO"),
        ({"pooled_ucb": 0.9700001}, "POOLED_OVERALL_UCB95"),
        (
            {"subgroup_points": (1.0500001,) + (0.90,) * 6},
            "POOLED_SUBGROUP_POINT_RATIO:weather_clear",
        ),
        (
            {"subgroup_ucbs": (1.0500001,) + (0.90,) * 6},
            "POOLED_SUBGROUP_UCB95:weather_clear",
        ),
        (
            {"fold_points": (1.0500001, 0.90, 0.90, 0.90)},
            "FOLD_OVERALL_POINT_RATIO:F1",
        ),
    ],
)
def test_threshold_violations_are_fail_not_unknown(
    override: dict[str, object], reason: str
) -> None:
    result = qualify_trial(_report_with(**override))  # type: ignore[arg-type]

    assert result.verdict is GateVerdict.FAIL
    assert result.qualified is False
    assert reason in result.reason_codes


def test_insufficient_group_in_any_fold_is_unknown_even_when_pooled_is_large() -> None:
    report = _report_with()
    first_fold = report.folds[0]
    deficient = replace(
        first_fold,
        subgroups=(
            NamedQualityMetric(
                name=FIXED_SUBGROUPS[0],
                metric=replace(first_fold.subgroups[0].metric, row_count=99),
            ),
            *first_fold.subgroups[1:],
        ),
    )

    result = qualify_trial(replace(report, folds=(deficient, *report.folds[1:])))

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert "INSUFFICIENT_SUBGROUP_ROWS:F1:weather_clear" in result.reason_codes


@pytest.mark.parametrize("field", ["lineage", "converter", "evidence", "budget"])
def test_non_pass_qualification_evidence_is_unknown(field: str) -> None:
    evidence = QualificationEvidence(
        lineage=GateVerdict.PASS,
        converter=GateVerdict.PASS,
        evidence=GateVerdict.PASS,
        budget=GateVerdict.PASS,
    )
    evidence = replace(evidence, **{field: GateVerdict.FAIL})

    result = qualify_trial(_report_with(evidence=evidence))

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert f"{field.upper()}_NOT_PASS" in result.reason_codes


def test_incomplete_accounting_is_unknown_before_bootstrap_or_thresholds() -> None:
    report = _report_with()
    incomplete_receipt = replace(
        report.folds[0].completeness,
        verdict=GateVerdict.UNKNOWN,
        reason_codes=("CANDIDATE_PREDICTION_INCOMPLETE",),
    )
    incomplete_fold = replace(report.folds[0], completeness=incomplete_receipt)

    result = qualify_trial(replace(report, folds=(incomplete_fold, *report.folds[1:])))

    assert result.verdict is GateVerdict.UNKNOWN
    assert "INCOMPLETE_ACCOUNTING:F1" in result.reason_codes


def test_omitted_subgroup_is_unknown_and_cannot_be_silently_ignored() -> None:
    report = _report_with()
    malformed = replace(report, pooled_subgroups=report.pooled_subgroups[:-1])

    result = qualify_trial(malformed)

    assert result.verdict is GateVerdict.UNKNOWN
    assert "INVALID_SUBGROUP_INVENTORY:POOLED" in result.reason_codes


def test_non_positive_stable_denominator_is_unknown() -> None:
    rows = tuple(
        row.model_copy(
            update={
                "stable_prediction": row.label,
                "candidate_prediction": row.label,
            }
        )
        for row in _rows("F1")
    )

    report = evaluate_fold("F1", rows, _complete_receipt(len(rows)))

    assert report.bootstrap.valid is False
    assert report.reason_codes == ("NONPOSITIVE_STABLE_MAE",)


def test_coordinated_invalid_metric_values_cannot_bypass_denominator_checks() -> None:
    report = _report_with()
    invalid_overall = replace(
        report.pooled_overall,
        stable_mae=0.0,
        candidate_mae=0.0,
        point_ratio=0.0,
    )
    invalid_bootstrap = report.pooled_bootstrap.model_copy(
        update={
            "overall": report.pooled_bootstrap.overall.model_copy(
                update={
                    "stable_mae": 0.0,
                    "candidate_mae": 0.0,
                    "point_ratio": 0.0,
                }
            )
        }
    )

    result = qualify_trial(
        replace(
            report,
            pooled_overall=invalid_overall,
            pooled_bootstrap=invalid_bootstrap,
        )
    )

    assert result.verdict is GateVerdict.UNKNOWN
    assert "INVALID_OVERALL_METRIC:POOLED" in result.reason_codes


def test_coordinated_point_ratio_must_still_match_reported_maes() -> None:
    report = _report_with()
    invalid_overall = replace(
        report.pooled_overall,
        candidate_mae=8.0,
        point_ratio=0.90,
    )
    invalid_bootstrap = report.pooled_bootstrap.model_copy(
        update={
            "overall": report.pooled_bootstrap.overall.model_copy(
                update={"candidate_mae": 8.0, "point_ratio": 0.90}
            )
        }
    )

    result = qualify_trial(
        replace(
            report,
            pooled_overall=invalid_overall,
            pooled_bootstrap=invalid_bootstrap,
        )
    )

    assert result.verdict is GateVerdict.UNKNOWN
    assert "INVALID_OVERALL_METRIC:POOLED" in result.reason_codes


def test_missing_fold_is_unknown_not_a_three_fold_gate() -> None:
    report = _report_with()

    result = qualify_trial(replace(report, folds=report.folds[:3]))

    assert result.verdict is GateVerdict.UNKNOWN
    assert "INVALID_FOLD_INVENTORY" in result.reason_codes


def test_malformed_fold_entry_fails_closed_without_evaluator_exception() -> None:
    report = _report_with()
    malformed = replace(report, folds=(*report.folds, object()))

    result = qualify_trial(malformed)  # type: ignore[arg-type]

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.reason_codes == ("INVALID_FOLD_INVENTORY",)
