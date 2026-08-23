from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from numpy.testing import assert_allclose

from mdcp.contracts.workload import BikeRequest
from mdcp.predictor.runtime import OnnxPredictor
from mdcp.workload.features import approved_feature_columns
from mdcp.workload.onnx_export import export_pipeline_onnx
from mdcp.workload.training import ModelFixtureConfig, train_fixture


def _rows() -> pd.DataFrame:
    rng = np.random.default_rng(2026)
    count = 512
    rows = pd.DataFrame(
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
            "cnt": rng.integers(0, 500, count),
        },
        index=pd.date_range("2011-01-01", periods=count, freq="h", name="observed_at"),
    )
    return rows


def test_onnx_prediction_matches_sklearn(tmp_path: Path) -> None:
    rows = _rows()
    config = ModelFixtureConfig(
        schema_version="mdcp.model-fixture.v1",
        name="candidate-v1",
        n_estimators=16,
        max_depth=8,
        min_samples_leaf=2,
        random_state=2026,
        n_jobs=1,
    )
    native = train_fixture(config, rows)
    path = tmp_path / "model.onnx"
    receipt = export_pipeline_onnx(native, path)
    runtime = OnnxPredictor(
        onnx_path=path,
        expected_sha256=receipt.onnx_sha256,
        release_id="sha256:" + "a" * 64,
        route_revision=1,
    )

    native_values = native.predict(rows.loc[:, approved_feature_columns()].head(32))
    onnx_values = []
    for index, row in rows.head(32).iterrows():
        request = BikeRequest(request_id=str(index), **row.loc[list(approved_feature_columns())])
        onnx_values.append(runtime.predict(request))

    assert_allclose(onnx_values, native_values, rtol=1e-5, atol=1e-5)
