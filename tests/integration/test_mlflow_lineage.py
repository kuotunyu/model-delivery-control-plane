from __future__ import annotations

from pathlib import Path

import pytest

from mdcp.workload.mlflow_lineage import record_mlflow_version, snapshot_mlflow_version


def test_mlflow_snapshot_requires_numeric_version_and_immutable_source(
    tmp_path: Path,
) -> None:
    tracking_uri = (tmp_path / "mlruns").as_uri()
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"synthetic-onnx")

    recorded = record_mlflow_version(
        model_name="bike-demand",
        onnx_path=artifact,
        evidence_paths=(),
        digest_tags={
            "mdcp.onnx_sha256": "a" * 64,
            "mdcp.training_rows_sha256": "b" * 64,
            "mdcp.config_sha256": "c" * 64,
            "mdcp.h1_report_sha256": "d" * 64,
        },
        tracking_uri=tracking_uri,
        experiment_name="wave1-lineage",
    )

    snapshot = snapshot_mlflow_version(
        "bike-demand",
        recorded.version,
        tracking_uri=tracking_uri,
    )

    assert snapshot == recorded
    assert recorded.version == 1
    assert recorded.run_id in recorded.artifact_uri
    assert snapshot.onnx_sha256 == "a" * 64


def test_mlflow_snapshot_rejects_alias_before_client_access() -> None:
    with pytest.raises(ValueError, match="numeric model version required"):
        snapshot_mlflow_version("bike-demand", "champion")  # type: ignore[arg-type]
