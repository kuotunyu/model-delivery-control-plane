from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import onnx
import pandas as pd

from mdcp.workload.onnx_export import export_pipeline_onnx
from mdcp.workload.training import ModelFixtureConfig, train_fixture

REPOSITORY_ROOT = Path(__file__).parents[3]


def _model():
    count = 96
    hour = np.arange(count) % 24
    rows = pd.DataFrame(
        {
            "season": 1,
            "mnth": 1,
            "hr": hour,
            "holiday": 0,
            "weekday": (np.arange(count) // 24) % 7,
            "workingday": 1,
            "weathersit": 1,
            "temp": 0.2 + hour / 100,
            "atemp": 0.25 + hour / 100,
            "hum": 0.8 - hour / 100,
            "windspeed": 0.1,
            "cnt": 20 + 3 * hour,
        },
        index=pd.date_range("2011-01-01", periods=count, freq="h", name="observed_at"),
    )
    config = ModelFixtureConfig(
        schema_version="mdcp.model-fixture.v1",
        name="stable-v1",
        n_estimators=8,
        max_depth=4,
        min_samples_leaf=2,
        random_state=2026,
        n_jobs=1,
    )
    return train_fixture(config, rows)


def test_export_receipt_binds_onnx_bytes_and_contract(tmp_path: Path) -> None:
    output = tmp_path / "model.onnx"

    receipt = export_pipeline_onnx(_model(), output)

    content = output.read_bytes()
    model = onnx.load_model_from_string(content)
    assert receipt.onnx_sha256 == hashlib.sha256(content).hexdigest()
    assert receipt.byte_size == len(content)
    assert receipt.input_names == (
        "season",
        "mnth",
        "hr",
        "holiday",
        "weekday",
        "workingday",
        "weathersit",
        "temp",
        "atemp",
        "hum",
        "windspeed",
    )
    assert receipt.output_name in {output.name for output in model.graph.output}
    assert "TreeEnsembleRegressor" in receipt.operators


def test_predictor_dockerfile_is_local_non_root_contract() -> None:
    content = (REPOSITORY_ROOT / "docker" / "predictor.Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "USER mdcp" in content
    assert "MDCP_ONNX_PATH=/model/model.onnx" in content
    assert "MDCP_DESCRIPTOR_PATH=/model/artifact-descriptor.json" in content
    assert all(token not in content.lower() for token in ("curl ", "wget ", "http://", "https://"))
