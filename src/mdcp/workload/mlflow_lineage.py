from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from pydantic import BaseModel, ConfigDict

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_DIGEST_TAGS = {
    "onnx_sha256": "mdcp.onnx_sha256",
    "training_rows_sha256": "mdcp.training_rows_sha256",
    "config_sha256": "mdcp.config_sha256",
    "h1_report_sha256": "mdcp.h1_report_sha256",
}


class MLflowVersionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str
    version: int
    run_id: str
    artifact_uri: str
    onnx_sha256: str
    training_rows_sha256: str
    config_sha256: str
    h1_report_sha256: str


def _validate_digest_tags(tags: Mapping[str, str]) -> None:
    for tag in REQUIRED_DIGEST_TAGS.values():
        if not SHA256_PATTERN.fullmatch(tags.get(tag, "")):
            raise ValueError(f"model version lacks valid {tag}")


def record_mlflow_version(
    *,
    model_name: str,
    onnx_path: Path,
    evidence_paths: Sequence[Path],
    digest_tags: Mapping[str, str],
    tracking_uri: str,
    experiment_name: str,
) -> MLflowVersionSnapshot:
    """Record local artifacts and return the numeric immutable registry snapshot."""

    _validate_digest_tags(digest_tags)
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    experiment_id = (
        experiment.experiment_id
        if experiment is not None
        else client.create_experiment(experiment_name)
    )
    run = client.create_run(
        experiment_id,
        tags={"mlflow.runName": f"{model_name}-numeric-lineage"},
    )
    try:
        client.log_artifact(run.info.run_id, str(onnx_path), artifact_path="model")
        for path in evidence_paths:
            client.log_artifact(run.info.run_id, str(path), artifact_path="evidence")
        client.set_terminated(run.info.run_id, status="FINISHED")
    except Exception:
        client.set_terminated(run.info.run_id, status="FAILED")
        raise

    try:
        client.get_registered_model(model_name)
    except MlflowException as error:
        if error.error_code != "RESOURCE_DOES_NOT_EXIST":
            raise
        client.create_registered_model(model_name)

    artifact_uri = f"{run.info.artifact_uri}/model/{onnx_path.name}"
    model_version = client.create_model_version(
        name=model_name,
        source=artifact_uri,
        run_id=run.info.run_id,
        tags=dict(digest_tags),
    )
    return snapshot_mlflow_version(
        model_name,
        int(model_version.version),
        tracking_uri=tracking_uri,
    )


def snapshot_mlflow_version(
    model_name: str,
    version: int,
    *,
    tracking_uri: str | None = None,
) -> MLflowVersionSnapshot:
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        raise ValueError("numeric model version required")
    client = MlflowClient(tracking_uri=tracking_uri)
    model_version = client.get_model_version(model_name, str(version))
    if not model_version.run_id or not model_version.source:
        raise ValueError("model version lacks immutable run lineage")
    if model_version.run_id not in model_version.source:
        raise ValueError("model version source is not bound to its run")

    values: dict[str, str] = {}
    tags = model_version.tags or {}
    _validate_digest_tags(tags)
    for field, tag in REQUIRED_DIGEST_TAGS.items():
        values[field] = tags[tag]

    return MLflowVersionSnapshot(
        model_name=model_name,
        version=version,
        run_id=model_version.run_id,
        artifact_uri=model_version.source,
        **values,
    )
