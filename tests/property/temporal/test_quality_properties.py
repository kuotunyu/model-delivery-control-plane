from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
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
    FoldQualificationContext,
    QualificationContext,
    QualificationEvidence,
    evaluate_pooled,
    qualify_trial,
)
from mdcp.temporal.folds import SourceRowIdentity
from mdcp.temporal.trials import canonical_trial_identity


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


def _identity(fold_id: str, position: int, row: PairedQualityRow) -> SourceRowIdentity:
    local_timestamp = f"{row.calendar_day.isoformat()}T{position % 24:02d}:{position % 60:02d}:00"
    material = {
        "fold_id": fold_id,
        "request_id": row.request_id,
        "local_timestamp": local_timestamp,
        "source_position": position,
    }
    return SourceRowIdentity(
        **material,
        identity_sha256=sha256_hex(canonicalize_json(material)),
    )


def _context(fold_rows: dict[str, tuple[PairedQualityRow, ...]]) -> QualificationContext:
    return QualificationContext(
        folds=tuple(
            FoldQualificationContext(
                fold_id=fold_id,
                inventory=tuple(
                    _identity(fold_id, position, row)
                    for position, row in enumerate(fold_rows[fold_id])
                ),
                paired_rows=fold_rows[fold_id],
            )
            for fold_id in FOLD_IDS
        ),
        trial_identity=canonical_trial_identity("STAT-A1"),
    )


def _report(
    *,
    fold_points: tuple[float, float, float, float] = (0.90, 0.90, 0.90, 0.90),
    target_group: str | None = None,
    pooled_target_count: int = 0,
) -> tuple[DevelopmentQualityReport, QualificationContext]:
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
    context = _context(fold_rows)
    report = evaluate_pooled(
        context,
        {fold_id: _receipt(len(rows)) for fold_id, rows in fold_rows.items()},
        QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
    )
    return report, context


@settings(max_examples=12, deadline=None)
@given(excess=st.floats(min_value=1e-9, max_value=0.1, allow_nan=False))
def test_any_overall_threshold_excess_is_a_fail_not_unknown(excess: float) -> None:
    report, context = _report(fold_points=(0.97 + excess,) * 4)
    result = qualify_trial(report, context)

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

    report, context = _report(fold_points=tuple(points))  # type: ignore[arg-type]
    result = qualify_trial(report, context)

    assert result.verdict is GateVerdict.FAIL
    assert result.qualified is False
    assert "FOLD_STABILITY" in result.reason_codes


@settings(max_examples=12, deadline=None)
@given(missing=st.sampled_from(FIXED_SUBGROUPS))
def test_any_missing_fixed_subgroup_makes_evidence_unknown(missing: str) -> None:
    report, context = _report()
    filtered = tuple(entry for entry in report.pooled_subgroups if entry.name != missing)

    result = qualify_trial(replace(report, pooled_subgroups=filtered), context)

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert "INVALID_SUBGROUP_INVENTORY:POOLED" in result.reason_codes


@settings(max_examples=12, deadline=None)
@given(count=st.integers(min_value=0, max_value=99), group=st.sampled_from(FIXED_SUBGROUPS))
def test_any_subgroup_below_100_is_statistically_unknown(count: int, group: str) -> None:
    report, context = _report(target_group=group, pooled_target_count=count)

    result = qualify_trial(report, context)

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert f"INSUFFICIENT_SUBGROUP_ROWS:POOLED:{group}" in result.reason_codes
