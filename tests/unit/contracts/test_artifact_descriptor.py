from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from mdcp.contracts.release import (
    ArtifactDescriptor,
    InventoryEntry,
    OnnxMetadata,
    ServingInventory,
    artifact_descriptor_digest,
    serving_inventory_digest,
)

REPOSITORY_ROOT = Path(__file__).parents[3]


def _descriptor() -> ArtifactDescriptor:
    return ArtifactDescriptor(
        schema_version="artifact-descriptor/v1",
        model_name="stable",
        evidence_class="synthetic_test",
        training_data_kind="deterministic_generated",
        git_source_sha="1" * 40,
        model_sha256="a" * 64,
        schema_digest="b" * 64,
        serving_code_config_id="c" * 64,
        feature_manifest_sha256="d" * 64,
        dependency_lock_sha256="e" * 64,
        split_manifest_sha256="f" * 64,
        training_receipt_sha256="0" * 64,
        h1_report_sha256="1" * 64,
        onnx=OnnxMetadata(
            sha256="a" * 64,
            size_bytes=128,
            opset=18,
            operators=("Add", "Concat"),
            input_names=("season",),
            output_name="prediction",
        ),
    )


def test_descriptor_has_only_prebuild_identity() -> None:
    descriptor = _descriptor()

    assert descriptor.git_source_sha
    assert descriptor.onnx.sha256
    assert descriptor.schema_digest
    assert descriptor.serving_code_config_id
    assert "oci" not in ArtifactDescriptor.model_fields
    assert "release_id" not in ArtifactDescriptor.model_fields


def test_descriptor_digest_detects_tampering() -> None:
    descriptor = _descriptor()
    changed = descriptor.model_copy(
        update={"onnx": descriptor.onnx.model_copy(update={"sha256": "2" * 64})}
    )

    assert artifact_descriptor_digest(descriptor) != artifact_descriptor_digest(changed)


def test_model_and_onnx_digests_must_match() -> None:
    with pytest.raises(ValidationError, match="model_sha256"):
        ArtifactDescriptor.model_validate(
            {**_descriptor().model_dump(mode="json"), "model_sha256": "2" * 64}
        )


def test_serving_inventory_digest_covers_path_and_content() -> None:
    inventory = ServingInventory(
        entry_point="mdcp.predictor.app:app",
        environment=("MDCP_DESCRIPTOR_PATH", "MDCP_ONNX_PATH"),
        entries=(InventoryEntry(path="src/a.py", sha256="a" * 64),),
    )
    changed = inventory.model_copy(
        update={"entries": (InventoryEntry(path="src/a.py", sha256="b" * 64),)}
    )

    assert serving_inventory_digest(inventory) != serving_inventory_digest(changed)


@pytest.mark.parametrize("role", ["stable", "candidate"])
def test_checked_in_reviewer_descriptor_binds_model(role: str) -> None:
    root = REPOSITORY_ROOT / "tests" / "fixtures" / "artifacts" / role
    descriptor = ArtifactDescriptor.model_validate_json(
        (root / "artifact-descriptor.json").read_text(encoding="utf-8")
    )

    assert descriptor.model_name == role
    assert descriptor.model_sha256 == descriptor.onnx.sha256
    assert descriptor.evidence_class.value == "synthetic_test"
    assert descriptor.training_data_kind == "deterministic_generated"
    assert json.loads((root / "artifact-descriptor.json").read_text())["schema_version"]
