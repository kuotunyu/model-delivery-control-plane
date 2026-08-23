from __future__ import annotations

import numpy as np
import pandas as pd

from mdcp.workload.training import (
    ModelFixtureConfig,
    create_training_receipt,
    train_fixture,
)


def _rows() -> pd.DataFrame:
    rng = np.random.default_rng(2026)
    count = 256
    return pd.DataFrame(
        {
            "season": rng.integers(1, 5, count),
            "mnth": rng.integers(1, 13, count),
            "hr": rng.integers(0, 24, count),
            "holiday": rng.integers(0, 2, count),
            "weekday": rng.integers(0, 7, count),
            "workingday": rng.integers(0, 2, count),
            "weathersit": rng.integers(1, 5, count),
            "temp": rng.random(count),
            "atemp": rng.random(count),
            "hum": rng.random(count),
            "windspeed": rng.random(count),
            "cnt": rng.integers(0, 400, count),
        },
        index=pd.date_range("2011-01-01", periods=count, freq="h", name="observed_at"),
    )


def test_candidate_fit_is_reproducible_across_fresh_pipelines() -> None:
    config = ModelFixtureConfig(
        schema_version="mdcp.model-fixture.v1",
        name="candidate-v1",
        n_estimators=48,
        max_depth=10,
        min_samples_leaf=2,
        random_state=2026,
        n_jobs=1,
    )
    rows = _rows()

    first = train_fixture(config, rows)
    second = train_fixture(config, rows)
    first_receipt = create_training_receipt(config, rows)
    second_receipt = create_training_receipt(config, rows)

    assert np.array_equal(first.predict(rows), second.predict(rows))
    assert first_receipt.config_sha256 == second_receipt.config_sha256
    assert first_receipt.training_rows_sha256 == second_receipt.training_rows_sha256
