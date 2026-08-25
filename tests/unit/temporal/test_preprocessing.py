from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS
from mdcp.temporal.trials import TrialSpec, build_estimator, load_trial_specs

REPOSITORY_ROOT = Path(__file__).parents[3]
PROTOCOL = json.loads(
    (REPOSITORY_ROOT / "configs" / "workload" / "temporal-development-v2.json").read_text(
        encoding="utf-8"
    )
)


def _stat_spec() -> TrialSpec:
    return next(spec for spec in load_trial_specs(PROTOCOL) if spec.trial_id == "STAT-A1")


def _stat_rows() -> pd.DataFrame:
    positions = np.arange(8, dtype=float)
    frame = pd.DataFrame(
        {
            "season": [1, 2, 3, 4, 1, 2, 3, 4],
            "mnth": np.arange(1, 9),
            "hr": np.arange(8),
            "holiday": [0, 1] * 4,
            "weekday": np.arange(8) % 7,
            "workingday": [1, 0] * 4,
            "weathersit": [1, 2, 3, 4, 1, 2, 3, 4],
            **{
                column: positions + offset
                for offset, column in enumerate(TEMPORAL_FEATURE_COLUMNS[7:], start=1)
            },
        }
    )
    frame["cnt"] = 20 + positions
    return frame


def test_stat_uses_fixed_full_category_domains_not_observed_values() -> None:
    rows = _stat_rows()
    pipeline = build_estimator(_stat_spec()).fit(rows, rows["cnt"])
    categorical = pipeline.named_steps["preprocess"].named_transformers_["categorical"]

    assert [values.tolist() for values in categorical.categories_] == [
        [1, 2, 3, 4],
        list(range(1, 13)),
        list(range(24)),
        [0, 1],
        list(range(7)),
        [0, 1],
        [1, 2, 3, 4],
    ]


def test_stat_standardizes_from_training_mean_and_population_standard_deviation() -> None:
    rows = _stat_rows()
    pipeline = build_estimator(_stat_spec()).fit(rows, rows["cnt"])
    scaler = pipeline.named_steps["preprocess"].named_transformers_["continuous"]

    expected_mean = np.arange(8, dtype=float).mean() + np.arange(1, 12, dtype=float)
    expected_scale = np.full(11, np.arange(8, dtype=float).std(ddof=0))
    np.testing.assert_allclose(scaler.mean_, expected_mean)
    np.testing.assert_allclose(scaler.scale_, expected_scale)


def test_stat_rejects_zero_variance_continuous_feature() -> None:
    rows = _stat_rows()
    rows["annual_cos"] = 1.0

    with pytest.raises(ValueError, match="zero-variance STAT continuous feature"):
        build_estimator(_stat_spec()).fit(rows, rows["cnt"])
