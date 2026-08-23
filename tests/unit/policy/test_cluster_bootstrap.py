from __future__ import annotations

import json
from pathlib import Path

from mdcp.policy.cluster_bootstrap import PairedQualityRow, cluster_bootstrap_ratios

VECTOR = Path(__file__).parents[2] / "fixtures" / "workload" / "bootstrap-vector.json"


def test_cluster_bootstrap_vector_is_exact_and_reproducible() -> None:
    vector = json.loads(VECTOR.read_text(encoding="utf-8"))
    rows = tuple(PairedQualityRow.model_validate(row) for row in vector["rows"])

    first = cluster_bootstrap_ratios(rows, vector["groups"], 2000, 2026)
    second = cluster_bootstrap_ratios(rows, vector["groups"], 2000, 2026)

    assert first == second
    assert first.valid is True
    assert first.overall.ucb95 == vector["expected_overall_ucb95"]
    assert first.subgroups["weather_clear"].ucb95 == vector["expected_subgroup_ucb95"]
    assert first.replicate_index == 1899


def test_cluster_bootstrap_zero_stable_error_is_unknown() -> None:
    rows = (
        PairedQualityRow(
            request_id="zero",
            calendar_day="2012-01-01",
            stable_prediction=10,
            candidate_prediction=10,
            label=10,
            groups=("g",),
        ),
    )

    result = cluster_bootstrap_ratios(rows, ("g",), 2000, 2026)

    assert result.valid is False
    assert result.reason_code == "NONPOSITIVE_STABLE_MAE"
