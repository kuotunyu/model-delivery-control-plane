from __future__ import annotations

from pathlib import Path

import pytest

from mdcp.contracts.release import ArtifactDescriptor
from mdcp.validator.mlflow_snapshot import (
    compare_mlflow_snapshots,
    validate_snapshot_against_descriptor,
)
from mdcp.workload.mlflow_lineage import MLflowVersionSnapshot

REPOSITORY_ROOT = Path(__file__).parents[3]


def _snapshot() -> MLflowVersionSnapshot:
    return MLflowVersionSnapshot.model_validate_json(
        (
            REPOSITORY_ROOT
            / "tests"
            / "fixtures"
            / "validator"
            / "mlflow-version-snapshot.json"
        ).read_text(encoding="utf-8")
    )


def _descriptor() -> ArtifactDescriptor:
    return ArtifactDescriptor.model_validate_json(
        (
            REPOSITORY_ROOT
            / "tests"
            / "fixtures"
            / "artifacts"
            / "stable"
            / "artifact-descriptor.json"
        ).read_text(encoding="utf-8")
    )


def test_numeric_snapshot_matches_staged_descriptor() -> None:
    check = validate_snapshot_against_descriptor(_snapshot(), _descriptor())

    assert check.verdict.value == "PASS"


def test_alias_input_is_rejected_before_registry_access() -> None:
    with pytest.raises(ValueError, match="numeric model version required"):
        MLflowVersionSnapshot.model_validate(
            {**_snapshot().model_dump(mode="json"), "version": "champion"}
        )


@pytest.mark.parametrize(
    "update",
    [
        {"artifact_uri": "file:///changed/model/model.onnx"},
        {"onnx_sha256": "0" * 64},
    ],
)
def test_changed_uri_or_digest_fails_snapshot_comparison(update: dict[str, str]) -> None:
    observed = _snapshot().model_copy(update=update)

    with pytest.raises(ValueError, match="snapshot identity mismatch"):
        compare_mlflow_snapshots(_snapshot(), observed)


def test_descriptor_digest_mismatch_fails_closed() -> None:
    snapshot = _snapshot().model_copy(update={"onnx_sha256": "0" * 64})

    check = validate_snapshot_against_descriptor(snapshot, _descriptor())

    assert check.verdict.value == "FAIL"
