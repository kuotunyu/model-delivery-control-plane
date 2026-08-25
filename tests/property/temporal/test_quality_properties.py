from __future__ import annotations

from dataclasses import replace

from hypothesis import given
from hypothesis import strategies as st

from mdcp.common.enums import GateVerdict
from mdcp.policy.cluster_bootstrap import BootstrapResult, RatioMetric
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


def _receipt() -> CompletenessReceipt:
    return CompletenessReceipt(
        verdict=GateVerdict.PASS,
        reason_codes=(),
        source_count=300,
        adapter=_layer(300, ADAPTER_REASON_CODES),
        stable=_layer(300, PREDICTION_REASON_CODES),
        candidate=_layer(300, PREDICTION_REASON_CODES),
        label=_layer(300, LABEL_REASON_CODES),
    )


def _metric(point: float, ucb: float, count: int) -> QualityMetricReport:
    return QualityMetricReport(
        row_count=count,
        stable_mae=10.0,
        candidate_mae=10.0 * point,
        point_ratio=point,
        ucb95=ucb,
    )


def _bootstrap(point: float, ucb: float, count: int, subgroup_count: int) -> BootstrapResult:
    return BootstrapResult(
        valid=True,
        overall=RatioMetric(
            row_count=count,
            stable_mae=10.0,
            candidate_mae=10.0 * point,
            point_ratio=point,
            ucb95=ucb,
        ),
        subgroups={
            group: RatioMetric(
                row_count=subgroup_count,
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


def _report(
    *,
    pooled_point: float = 0.90,
    pooled_ucb: float = 0.90,
    fold_points: tuple[float, float, float, float] = (0.90, 0.90, 0.90, 0.90),
) -> DevelopmentQualityReport:
    folds = tuple(
        FoldQualityReport(
            fold_id=fold_id,
            completeness=_receipt(),
            paired_row_count=300,
            overall=_metric(point, point, 300),
            subgroups=tuple(
                NamedQualityMetric(group, _metric(0.90, 0.90, 100)) for group in FIXED_SUBGROUPS
            ),
            bootstrap=_bootstrap(point, point, 300, 100),
            reason_codes=(),
        )
        for fold_id, point in zip(FOLD_IDS, fold_points, strict=True)
    )
    return DevelopmentQualityReport(
        folds=folds,
        pooled_row_count=1200,
        pooled_overall=_metric(pooled_point, pooled_ucb, 1200),
        pooled_subgroups=tuple(
            NamedQualityMetric(group, _metric(0.90, 0.90, 400)) for group in FIXED_SUBGROUPS
        ),
        pooled_bootstrap=_bootstrap(pooled_point, pooled_ucb, 1200, 400),
        qualification_evidence=QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
        reason_codes=(),
    )


@given(excess=st.floats(min_value=1e-9, max_value=0.1, allow_nan=False))
def test_any_overall_threshold_excess_is_a_fail_not_unknown(excess: float) -> None:
    point_result = qualify_trial(_report(pooled_point=0.97 + excess))
    ucb_result = qualify_trial(_report(pooled_ucb=0.97 + excess))

    assert point_result.verdict is GateVerdict.FAIL
    assert ucb_result.verdict is GateVerdict.FAIL
    assert point_result.qualified is False
    assert ucb_result.qualified is False


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


@given(missing=st.sampled_from(FIXED_SUBGROUPS))
def test_any_missing_fixed_subgroup_makes_evidence_unknown(missing: str) -> None:
    report = _report()
    filtered = tuple(entry for entry in report.pooled_subgroups if entry.name != missing)

    result = qualify_trial(replace(report, pooled_subgroups=filtered))

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert "INVALID_SUBGROUP_INVENTORY:POOLED" in result.reason_codes


@given(count=st.integers(min_value=0, max_value=99), group=st.sampled_from(FIXED_SUBGROUPS))
def test_any_subgroup_below_100_is_statistically_unknown(count: int, group: str) -> None:
    report = _report()
    pooled = tuple(
        replace(entry, metric=replace(entry.metric, row_count=count))
        if entry.name == group
        else entry
        for entry in report.pooled_subgroups
    )

    result = qualify_trial(replace(report, pooled_subgroups=pooled))

    assert result.verdict is GateVerdict.UNKNOWN
    assert result.qualified is False
    assert f"INSUFFICIENT_SUBGROUP_ROWS:POOLED:{group}" in result.reason_codes
