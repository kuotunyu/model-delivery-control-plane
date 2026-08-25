from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

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
    QualificationEvidence,
    evaluate_pooled,
    qualify_trial,
)


def _layer(count: int, reasons: tuple[str, ...]) -> LayerAccounting:
    return LayerAccounting(
        expected_count=count,
        observed_count=count,
        success_count=count,
        failure_count=0,
        missing_count=0,
        duplicate_count=0,
        unexpected_count=0,
        invalid_count=0,
        reason_counts=tuple((reason, 0) for reason in reasons),
    )


def _receipt(count: int = 300) -> CompletenessReceipt:
    return CompletenessReceipt(
        verdict=GateVerdict.PASS,
        reason_codes=(),
        source_count=count,
        adapter=_layer(count, ADAPTER_REASON_CODES),
        stable=_layer(count, PREDICTION_REASON_CODES),
        candidate=_layer(count, PREDICTION_REASON_CODES),
        label=_layer(count, LABEL_REASON_CODES),
    )


def _distributed_inventory(counts: dict[str, int], order: tuple[str, ...]) -> tuple[str, ...]:
    inventory: list[str] = []
    remaining = dict(counts)
    while any(remaining.values()):
        for value in order:
            if remaining[value]:
                inventory.append(value)
                remaining[value] -= 1
    return tuple(inventory)


def _rows(
    fold_id: str,
    ratio: float,
    *,
    target_group: str | None = None,
    target_count: int = 0,
) -> tuple[PairedQualityRow, ...]:
    weather = ("weather_clear", "weather_mist", "weather_adverse")
    days = ("day_non_working", "day_working")
    demand = ("demand_peak", "demand_off_peak")
    weather_counts = {group: 100 for group in weather}
    day_counts = {group: 150 for group in days}
    demand_counts = {group: 150 for group in demand}
    for groups, counts in (
        (weather, weather_counts),
        (days, day_counts),
        (demand, demand_counts),
    ):
        if target_group in groups:
            counts[target_group] = target_count
            remainder = 300 - target_count
            others = [group for group in groups if group != target_group]
            for position, group in enumerate(others):
                counts[group] = remainder // len(others) + (
                    1 if position < remainder % len(others) else 0
                )

    inventories = (
        _distributed_inventory(weather_counts, weather),
        _distributed_inventory(day_counts, days),
        _distributed_inventory(demand_counts, demand),
    )
    start = date(2011, 7, 1) + timedelta(days=100 * (int(fold_id[1]) - 1))
    return tuple(
        PairedQualityRow(
            request_id=f"{fold_id}-property-{position:04d}",
            calendar_day=start + timedelta(days=position // 30),
            stable_prediction=20.0,
            candidate_prediction=10.0 + 10.0 * ratio,
            label=10.0,
            groups=tuple(inventory[position] for inventory in inventories),
        )
        for position in range(300)
    )


def _report(
    *,
    fold_points: tuple[float, float, float, float] = (0.90, 0.90, 0.90, 0.90),
    target_group: str | None = None,
    pooled_target_count: int = 0,
) -> DevelopmentQualityReport:
    per_fold_counts = tuple(
        pooled_target_count // 4 + (1 if position < pooled_target_count % 4 else 0)
        for position in range(4)
    )
    fold_rows = {
        fold_id: _rows(
            fold_id,
            point,
            target_group=target_group,
            target_count=per_fold_counts[position],
        )
        for position, (fold_id, point) in enumerate(zip(FOLD_IDS, fold_points, strict=True))
    }
    return evaluate_pooled(
        fold_rows,
        {fold_id: _receipt(len(rows)) for fold_id, rows in fold_rows.items()},
        QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
    )


@settings(max_examples=12, deadline=None)
@given(excess=st.floats(min_value=1e-9, max_value=0.1, allow_nan=False))
def test_any_overall_threshold_excess_is_a_fail_not_unknown(excess: float) -> None:
    result = qualify_trial(_report(fold_points=(0.97 + excess,) * 4))

    assert result.verdict is GateVerdict.FAIL
    assert result.qualified is False
    assert "POOLED_OVERALL_POINT_RATIO" in result.reason_codes


@settings(max_examples=12, deadline=None)
@given(
    winning_fold=st.integers(min_value=0, max_value=3),
    winner=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    losers=st.tuples(
        *(st.floats(min_value=1.0000001, max_value=1.05, allow_nan=False) for _ in range(3))
    ),
)
def test_one_fold_only_win_never_satisfies_stability(
    winning_fold: int, winner: float, losers: tuple[float, float, float]
) -> None:
    points = list(losers)
    points.insert(winning_fold, winner)

    result = qualify_trial(_report(fold_points=tuple(points)))  # type: ignore[arg-type]

    assert result.verdict is GateVerdict.FAIL
    assert result.qualified is False
    assert "FOLD_STABILITY" in result.reason_codes


@settings(max_examples=12, deadline=None)
@given(missing=st.sampled_from(FIXED_SUBGROUPS))
def test_any_missing_fixed_subgroup_makes_evidence_unknown(missing: str) -> None:
    report = _report()
    filtered = tuple(entry for entry in report.pooled_subgroups if entry.name != missing)

    result = qualify_trial(replace(report, pooled_subgroups=filtered))

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert "INVALID_SUBGROUP_INVENTORY:POOLED" in result.reason_codes


@settings(max_examples=12, deadline=None)
@given(count=st.integers(min_value=0, max_value=99), group=st.sampled_from(FIXED_SUBGROUPS))
def test_any_subgroup_below_100_is_statistically_unknown(count: int, group: str) -> None:
    report = _report(target_group=group, pooled_target_count=count)

    result = qualify_trial(report)

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert f"INSUFFICIENT_SUBGROUP_ROWS:POOLED:{group}" in result.reason_codes
