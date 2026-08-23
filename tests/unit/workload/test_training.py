from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from mdcp.workload.features import approved_feature_columns
from mdcp.workload.training import (
    ModelFixtureConfig,
    create_training_receipt,
    train_fixture,
)

REPOSITORY_ROOT = Path(__file__).parents[3]


def _train_rows() -> pd.DataFrame:
    index = pd.date_range("2011-01-01", periods=96, freq="h", name="observed_at")
    hour = np.arange(96) % 24
    frame = pd.DataFrame(
        {
            "season": 1,
            "mnth": 1,
            "hr": hour,
            "holiday": 0,
            "weekday": np.arange(96) // 24,
            "workingday": 1,
            "weathersit": 1,
            "temp": 0.2 + hour / 100,
            "atemp": 0.25 + hour / 100,
            "hum": 0.8 - hour / 100,
            "windspeed": 0.1,
            "cnt": 20 + 3 * hour,
        },
        index=index,
    )
    return frame


@pytest.fixture
def stable_config() -> ModelFixtureConfig:
    return ModelFixtureConfig(
        schema_version="mdcp.model-fixture.v1",
        name="stable-v1",
        n_estimators=32,
        max_depth=8,
        min_samples_leaf=4,
        random_state=2026,
        n_jobs=1,
    )


def test_training_is_deterministic(stable_config: ModelFixtureConfig) -> None:
    rows = _train_rows()

    left = train_fixture(stable_config, rows)
    right = train_fixture(stable_config, rows)
    left_receipt = create_training_receipt(stable_config, rows)
    right_receipt = create_training_receipt(stable_config, rows)

    features = rows.loc[:, approved_feature_columns()].head(32)
    assert left.predict(features).tobytes() == right.predict(features).tobytes()
    assert left_receipt == right_receipt


def test_pipeline_fit_receipt_contains_only_2011(stable_config: ModelFixtureConfig) -> None:
    receipt = create_training_receipt(stable_config, _train_rows())

    assert receipt.fit_min_timestamp == "2011-01-01T00:00:00Z"
    assert receipt.fit_max_timestamp < "2012-01-01T00:00:00Z"
    assert receipt.row_count == 96
    assert len(receipt.training_rows_sha256) == 64


def test_training_rejects_non_2011_or_unordered_rows(
    stable_config: ModelFixtureConfig,
) -> None:
    rows = _train_rows()
    h1 = rows.head(1).copy()
    h1.index = pd.DatetimeIndex(["2012-01-01"], name="observed_at")
    with pytest.raises(ValueError, match="2011 training partition"):
        train_fixture(stable_config, pd.concat([rows, h1]))
    with pytest.raises(ValueError, match="chronological order"):
        train_fixture(stable_config, rows.sort_index(ascending=False))


def test_model_config_is_strict_and_freezes_execution() -> None:
    with pytest.raises(ValidationError):
        ModelFixtureConfig.model_validate(
            {
                "schema_version": "mdcp.model-fixture.v1",
                "name": "unsafe",
                "n_estimators": 1,
                "max_depth": 1,
                "min_samples_leaf": 1,
                "random_state": 7,
                "n_jobs": -1,
                "extra": True,
            }
        )


def test_reviewed_model_configs_are_bounded() -> None:
    for name in ("stable-v1", "candidate-v1"):
        config = ModelFixtureConfig.model_validate_json(
            (REPOSITORY_ROOT / "configs" / "models" / f"{name}.yaml").read_text(
                encoding="utf-8"
            )
        )
        assert config.name == name
        assert config.random_state == 2026
        assert config.n_jobs == 1
        assert config.n_estimators <= 128
        assert json.loads(config.model_dump_json())["schema_version"] == "mdcp.model-fixture.v1"
