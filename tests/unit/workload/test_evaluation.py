from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from mdcp.common.enums import EvidenceClass, GateVerdict
from mdcp.policy.cluster_bootstrap import PairedQualityRow
from mdcp.workload.evaluation import QualityPolicy, evaluate_h1, paired_rows_from_frame

GROUPS = (
    "weather_clear",
    "weather_mist",
    "weather_adverse",
    "day_non_working",
    "day_working",
    "demand_peak",
    "demand_off_peak",
)


def _rows(count: int, *, candidate_error: float) -> tuple[PairedQualityRow, ...]:
    start = date(2012, 1, 1)
    return tuple(
        PairedQualityRow(
            request_id=f"r-{index}",
            calendar_day=(start + timedelta(days=index // 24)).isoformat(),
            stable_prediction=90.0,
            candidate_prediction=100.0 - candidate_error,
            label=100.0,
            groups=GROUPS,
        )
        for index in range(count)
    )


def _policy() -> QualityPolicy:
    return QualityPolicy(
        schema_version="mdcp.quality-policy.v1",
        overall_max_ratio=0.97,
        subgroup_max_ratio=1.05,
        minimum_subgroup_rows=100,
        resamples=2000,
        seed=2026,
        subgroup_names=GROUPS,
    )


def test_h1_synthetic_pass_is_separate_evidence_class() -> None:
    report = evaluate_h1(
        _rows(240, candidate_error=9.0),
        _policy(),
        evidence_class=EvidenceClass.SYNTHETIC_TEST,
    )

    assert report.verdict is GateVerdict.PASS
    assert report.evidence_class is EvidenceClass.SYNTHETIC_TEST
    assert report.bootstrap.overall.point_ratio == 0.9


def test_h1_threshold_failure_remains_fail() -> None:
    report = evaluate_h1(_rows(240, candidate_error=10.1), _policy())

    assert report.verdict is GateVerdict.FAIL
    assert "OVERALL_RATIO" in report.reason_codes


def test_h1_subgroup_below_100_makes_whole_report_unknown() -> None:
    rows = list(_rows(240, candidate_error=9.0))
    for index, row in enumerate(rows):
        groups = tuple(group for group in row.groups if group != "weather_adverse")
        if index < 99:
            groups = (*groups, "weather_adverse")
        rows[index] = row.model_copy(update={"groups": groups})

    report = evaluate_h1(rows, _policy())

    assert report.verdict is GateVerdict.UNKNOWN
    assert report.reason_codes == ("INSUFFICIENT_SUBGROUP_ROWS:weather_adverse",)


def test_evaluator_assigns_only_prespecified_groups() -> None:
    frame = pd.DataFrame(
        {
            "weathersit": [1, 2, 4],
            "workingday": [0, 1, 1],
            "hr": [8, 10, 18],
            "cnt": [100, 100, 100],
        },
        index=pd.DatetimeIndex(
            ["2012-01-01 08:00", "2012-01-02 10:00", "2012-01-03 18:00"],
            name="observed_at",
        ),
    )

    rows = paired_rows_from_frame(frame, [90, 90, 90], [91, 91, 91])

    assert rows[0].groups == ("weather_clear", "day_non_working", "demand_peak")
    assert rows[1].groups == ("weather_mist", "day_working", "demand_off_peak")
    assert rows[2].groups == ("weather_adverse", "day_working", "demand_peak")
    assert rows[0].calendar_day.isoformat() == "2012-01-01"
