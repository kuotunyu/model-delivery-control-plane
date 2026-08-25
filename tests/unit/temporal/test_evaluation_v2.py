from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from types import MappingProxyType

import pytest

from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import PairedQualityRow
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
    NamedQualityMetric,
    QualificationEvidence,
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


def _rows(
    fold_id: str,
    *,
    ratio: float = 0.90,
    weather_ratios: tuple[float, float, float] | None = None,
    day_ratios: tuple[float, ...] | None = None,
    weather_counts: tuple[int, int, int] = (100, 100, 100),
) -> tuple[PairedQualityRow, ...]:
    assert sum(weather_counts) == 300
    assert day_ratios is None or len(day_ratios) == 10
    start = date(2011, 7, 1) + timedelta(days=100 * (int(fold_id[1]) - 1))
    rows: list[PairedQualityRow] = []
    weather_groups = ("weather_clear", "weather_mist", "weather_adverse")
    remaining = dict(zip(weather_groups, weather_counts, strict=True))
    weather_inventory_list: list[str] = []
    while any(remaining.values()):
        for group in weather_groups:
            if remaining[group]:
                weather_inventory_list.append(group)
                remaining[group] -= 1
    weather_inventory = tuple(weather_inventory_list)
    for position in range(300):
        weather_group = weather_inventory[position]
        candidate_ratio = ratio
        if weather_ratios is not None:
            candidate_ratio = weather_ratios[weather_groups.index(weather_group)]
        if day_ratios is not None:
            candidate_ratio = day_ratios[position // 30]
        rows.append(
            PairedQualityRow(
                request_id=f"{fold_id}-{position:04d}",
                calendar_day=start + timedelta(days=position // 30),
                stable_prediction=20.0,
                candidate_prediction=10.0 + 10.0 * candidate_ratio,
                label=10.0,
                groups=(
                    weather_group,
                    "day_working" if position % 2 else "day_non_working",
                    "demand_peak" if position % 2 else "demand_off_peak",
                ),
            )
        )
    return tuple(rows)


def _report_with(
    *,
    fold_points: tuple[float, ...] = (0.90, 0.90, 0.90, 0.90),
    weather_ratios: tuple[float, float, float] | None = None,
    day_ratios: tuple[float, ...] | None = None,
    weather_counts: dict[str, tuple[int, int, int]] | None = None,
    evidence: QualificationEvidence | None = None,
) -> DevelopmentQualityReport:
    fold_rows = {
        fold_id: _rows(
            fold_id,
            ratio=point,
            weather_ratios=weather_ratios,
            day_ratios=day_ratios,
            weather_counts=(weather_counts or {}).get(fold_id, (100, 100, 100)),
        )
        for fold_id, point in zip(FOLD_IDS, fold_points, strict=True)
    }
    receipts = {fold_id: _complete_receipt(len(rows)) for fold_id, rows in fold_rows.items()}
    return evaluate_pooled(
        fold_rows,
        receipts,
        evidence
        or QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
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
    assert qualify_trial(report).verdict is GateVerdict.PASS
    assert "_paired_rows" not in repr(report)
    assert "F1-0000" not in repr(report)


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
    result = qualify_trial(_report_with(fold_points=(0.97, 0.97, 0.97, 0.97)))

    assert result.qualified is True
    assert result.verdict is GateVerdict.PASS
    assert result.reason_codes == ()


def test_qualification_accepts_subgroup_point_and_ucb_at_exact_boundary() -> None:
    report = _report_with(weather_ratios=(1.05, 0.80, 0.80))

    result = qualify_trial(report)

    weather_clear = report.pooled_bootstrap.subgroups["weather_clear"]
    assert weather_clear.point_ratio == pytest.approx(1.05)
    assert weather_clear.ucb95 == pytest.approx(1.05)
    assert result.verdict is GateVerdict.PASS


def test_qualification_result_carries_the_exact_selection_key_inputs() -> None:
    result = qualify_trial(
        _report_with(fold_points=(0.96, 0.96, 0.96, 0.96)),
        trial_id="STAT-A1",
        family_id="STAT",
    )

    assert result.trial_id == "STAT-A1"
    assert result.family_id == "STAT"
    assert result.pooled_ucb95 == pytest.approx(0.96)
    assert result.worst_fold_point == pytest.approx(0.96)
    assert result.worst_subgroup_ucb95 == pytest.approx(0.96)


def test_one_fold_only_win_does_not_qualify() -> None:
    result = qualify_trial(_report_with(fold_points=(0.80, 1.01, 1.02, 1.03)))

    assert result.qualified is False
    assert result.verdict is GateVerdict.FAIL
    assert "FOLD_STABILITY" in result.reason_codes


def test_pooled_overall_point_threshold_violation_is_fail_not_unknown() -> None:
    result = qualify_trial(_report_with(fold_points=(0.9700001,) * 4))

    assert result.verdict is GateVerdict.FAIL
    assert "POOLED_OVERALL_POINT_RATIO" in result.reason_codes


def test_real_bootstrap_ucb_threshold_violation_is_fail_not_unknown() -> None:
    report = _report_with(day_ratios=(0.75,) * 5 + (1.15,) * 5)

    result = qualify_trial(report)

    assert report.pooled_overall.point_ratio <= 0.97
    assert report.pooled_overall.ucb95 > 0.97
    assert result.verdict is GateVerdict.FAIL
    assert "POOLED_OVERALL_UCB95" in result.reason_codes


def test_pooled_subgroup_point_threshold_violation_is_fail_not_unknown() -> None:
    result = qualify_trial(_report_with(weather_ratios=(1.0500001, 0.80, 0.80)))

    assert result.verdict is GateVerdict.FAIL
    assert "POOLED_SUBGROUP_POINT_RATIO:weather_clear" in result.reason_codes


def test_real_subgroup_bootstrap_ucb_threshold_violation_is_fail_not_unknown() -> None:
    report = _report_with(day_ratios=(0.70,) * 5 + (1.30,) * 5)

    result = qualify_trial(report)

    weather_clear = report.pooled_bootstrap.subgroups["weather_clear"]
    assert weather_clear.point_ratio <= 1.05
    assert weather_clear.ucb95 > 1.05
    assert result.verdict is GateVerdict.FAIL
    assert "POOLED_SUBGROUP_UCB95:weather_clear" in result.reason_codes


def test_fold_point_threshold_violation_is_fail_not_unknown() -> None:
    result = qualify_trial(_report_with(fold_points=(1.0500001, 0.80, 0.80, 0.80)))

    assert result.verdict is GateVerdict.FAIL
    assert "FOLD_OVERALL_POINT_RATIO:F1" in result.reason_codes


def test_insufficient_group_in_any_fold_is_unknown_even_when_pooled_is_large() -> None:
    report = _report_with(
        weather_counts={"F1": (99, 100, 101)},
    )

    result = qualify_trial(report)

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
    fold_rows = {fold_id: _rows(fold_id) for fold_id in FOLD_IDS}
    receipts = {fold_id: _complete_receipt(len(rows)) for fold_id, rows in fold_rows.items()}
    incomplete_receipt = replace(
        receipts["F1"],
        verdict=GateVerdict.UNKNOWN,
        reason_codes=("CANDIDATE_PREDICTION_INCOMPLETE",),
    )
    receipts["F1"] = incomplete_receipt
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

    result = qualify_trial(report)

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
    assert "REPORT_RECOMPUTATION_MISMATCH" in result.reason_codes


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
    assert "REPORT_RECOMPUTATION_MISMATCH" in result.reason_codes


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


@pytest.mark.parametrize(
    "mutation",
    ("missing", "extra", "duplicate", "reordered", "non_tuple", "malformed"),
)
def test_malformed_fold_subgroup_inventory_is_unknown_without_exception(
    mutation: str,
) -> None:
    report = _report_with()
    entries: object = report.folds[0].subgroups
    if mutation == "missing":
        entries = report.folds[0].subgroups[:-1]
    elif mutation == "extra":
        entries = (*report.folds[0].subgroups, report.folds[0].subgroups[0])
    elif mutation == "duplicate":
        entries = (
            report.folds[0].subgroups[0],
            report.folds[0].subgroups[0],
            *report.folds[0].subgroups[2:],
        )
    elif mutation == "reordered":
        entries = tuple(reversed(report.folds[0].subgroups))
    elif mutation == "non_tuple":
        entries = list(report.folds[0].subgroups)
    elif mutation == "malformed":
        entries = (*report.folds[0].subgroups[:-1], object())
    malformed_fold = replace(report.folds[0], subgroups=entries)  # type: ignore[arg-type]

    result = qualify_trial(replace(report, folds=(malformed_fold, *report.folds[1:])))

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.reason_codes == ("INVALID_SUBGROUP_INVENTORY:F1",)


@pytest.mark.parametrize(
    "mutation",
    ("missing", "extra", "duplicate", "reordered", "non_tuple", "malformed"),
)
def test_malformed_pooled_subgroup_inventory_is_unknown_without_exception(
    mutation: str,
) -> None:
    report = _report_with()
    entries: object = report.pooled_subgroups
    if mutation == "missing":
        entries = report.pooled_subgroups[:-1]
    elif mutation == "extra":
        entries = (*report.pooled_subgroups, report.pooled_subgroups[0])
    elif mutation == "duplicate":
        entries = (
            report.pooled_subgroups[0],
            report.pooled_subgroups[0],
            *report.pooled_subgroups[2:],
        )
    elif mutation == "reordered":
        entries = tuple(reversed(report.pooled_subgroups))
    elif mutation == "non_tuple":
        entries = list(report.pooled_subgroups)
    elif mutation == "malformed":
        entries = (*report.pooled_subgroups[:-1], object())

    result = qualify_trial(replace(report, pooled_subgroups=entries))  # type: ignore[arg-type]

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.reason_codes == ("INVALID_SUBGROUP_INVENTORY:POOLED",)


def test_coordinated_pooled_metric_tamper_is_unknown() -> None:
    report = _report_with()
    changed_metric = replace(
        report.pooled_overall,
        candidate_mae=8.0,
        point_ratio=0.80,
        ucb95=0.80,
    )
    changed_bootstrap = report.pooled_bootstrap.model_copy(
        update={
            "overall": report.pooled_bootstrap.overall.model_copy(
                update={"candidate_mae": 8.0, "point_ratio": 0.80, "ucb95": 0.80}
            )
        }
    )

    result = qualify_trial(
        replace(
            report,
            pooled_overall=changed_metric,
            pooled_bootstrap=changed_bootstrap,
        )
    )

    assert result.verdict is GateVerdict.UNKNOWN
    assert "REPORT_RECOMPUTATION_MISMATCH" in result.reason_codes


def test_coordinated_fold_metric_tamper_is_unknown() -> None:
    report = _report_with()
    first = report.folds[0]
    changed_fold = replace(
        first,
        overall=replace(first.overall, candidate_mae=8.0, point_ratio=0.80, ucb95=0.80),
        bootstrap=first.bootstrap.model_copy(
            update={
                "overall": first.bootstrap.overall.model_copy(
                    update={"candidate_mae": 8.0, "point_ratio": 0.80, "ucb95": 0.80}
                )
            }
        ),
    )

    result = qualify_trial(replace(report, folds=(changed_fold, *report.folds[1:])))

    assert result.verdict is GateVerdict.UNKNOWN
    assert "REPORT_RECOMPUTATION_MISMATCH" in result.reason_codes


def test_coordinated_ucb_only_tamper_is_unknown() -> None:
    report = _report_with()
    changed_metric = replace(report.pooled_overall, ucb95=0.10)
    changed_bootstrap = report.pooled_bootstrap.model_copy(
        update={"overall": report.pooled_bootstrap.overall.model_copy(update={"ucb95": 0.10})}
    )

    result = qualify_trial(
        replace(
            report,
            pooled_overall=changed_metric,
            pooled_bootstrap=changed_bootstrap,
        )
    )

    assert result.verdict is GateVerdict.UNKNOWN
    assert "REPORT_RECOMPUTATION_MISMATCH" in result.reason_codes


def test_coordinated_partition_counts_cannot_change_the_row_denominator() -> None:
    report = _report_with()

    def changed_entries(
        entries: tuple[NamedQualityMetric, ...], count: int
    ) -> tuple[NamedQualityMetric, ...]:
        return tuple(
            replace(entry, metric=replace(entry.metric, row_count=count)) for entry in entries
        )

    changed_folds = tuple(
        replace(
            fold,
            subgroups=changed_entries(fold.subgroups, 100),
            bootstrap=fold.bootstrap.model_copy(
                update={
                    "subgroups": {
                        name: metric.model_copy(update={"row_count": 100})
                        for name, metric in fold.bootstrap.subgroups.items()
                    }
                }
            ),
        )
        for fold in report.folds
    )
    changed_pooled = changed_entries(report.pooled_subgroups, 400)
    changed_pooled_bootstrap = report.pooled_bootstrap.model_copy(
        update={
            "subgroups": {
                name: metric.model_copy(update={"row_count": 400})
                for name, metric in report.pooled_bootstrap.subgroups.items()
            }
        }
    )

    result = qualify_trial(
        replace(
            report,
            folds=changed_folds,
            pooled_subgroups=changed_pooled,
            pooled_bootstrap=changed_pooled_bootstrap,
        )
    )

    assert result.verdict is GateVerdict.UNKNOWN
    assert "REPORT_RECOMPUTATION_MISMATCH" in result.reason_codes


@pytest.mark.parametrize("mutation", ("reason_count", "reason_order", "boolean_counter"))
def test_contradictory_pass_completeness_receipt_is_unknown(mutation: str) -> None:
    report = _report_with()
    layer = report.folds[0].completeness.adapter
    if mutation == "reason_count":
        layer = replace(
            layer,
            reason_counts=((layer.reason_counts[0][0], 1), *layer.reason_counts[1:]),
        )
    elif mutation == "reason_order":
        layer = replace(layer, reason_counts=tuple(reversed(layer.reason_counts)))
    else:
        layer = replace(layer, failure_count=False)  # type: ignore[arg-type]
    receipt = replace(report.folds[0].completeness, adapter=layer)
    changed_fold = replace(report.folds[0], completeness=receipt)

    result = qualify_trial(replace(report, folds=(changed_fold, *report.folds[1:])))

    assert result.verdict is GateVerdict.UNKNOWN
    assert "INCOMPLETE_ACCOUNTING:F1" in result.reason_codes


def test_pass_receipt_with_all_accounting_counters_changed_to_one_is_unknown() -> None:
    report = _report_with()
    layer = report.folds[0].completeness.adapter
    layer = replace(
        layer,
        expected_count=1,
        observed_count=1,
        success_count=1,
        failure_count=1,
        missing_count=1,
        duplicate_count=1,
        unexpected_count=1,
        invalid_count=1,
    )
    receipt = replace(report.folds[0].completeness, adapter=layer)
    changed_fold = replace(report.folds[0], completeness=receipt)

    result = qualify_trial(replace(report, folds=(changed_fold, *report.folds[1:])))

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.reason_codes == ("INCOMPLETE_ACCOUNTING:F1",)
