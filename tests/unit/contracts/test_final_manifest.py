from __future__ import annotations

import pytest
from pydantic import ValidationError

from mdcp.contracts.release import (
    ArtifactDescriptor,
    BundleMember,
    FinalReleaseManifest,
    OciSubject,
    OnnxMetadata,
    release_id,
)


def _manifest() -> FinalReleaseManifest:
    return FinalReleaseManifest(
        schema_version="mdcp.final-release-manifest.v1",
        canonicalization="RFC8785",
        image_descriptor_digest="1" * 64,
        image_descriptor_schema_version="artifact-descriptor/v1",
        registered_model_name="mdcp-bike-demand",
        mlflow_numeric_version=2,
        mlflow_run_id="2" * 32,
        onnx=OnnxMetadata(
            sha256="3" * 64,
            size_bytes=707,
            opset=18,
            operators=("Add", "Concat", "MatMul", "Relu"),
            input_names=("season",),
            output_name="prediction",
        ),
        input_schema_digest="4" * 64,
        output_schema_digest="5" * 64,
        git_source_sha="6" * 40,
        serving_code_config_id="7" * 64,
        training_config_sha256="8" * 64,
        uci_doi="10.24432/C5W894",
        uci_source_sha256="9" * 64,
        uci_attribution_sha256="a" * 64,
        dataset_manifest_sha256="b" * 64,
        split_manifest_sha256="c" * 64,
        preprocessing_receipt_sha256="d" * 64,
        leakage_receipt_sha256="e" * 64,
        h1_evaluation_report_sha256="f" * 64,
        oci=OciSubject(
            repository="ghcr.io/kuotunyu/model-delivery-control-plane",
            digest="sha256:" + "1" * 64,
        ),
        sbom_sha256="2" * 64,
        provenance_sha256="3" * 64,
        attestation_sha256="4" * 64,
        scan_receipt_sha256="5" * 64,
        rollout_policy_sha256="6" * 64,
    )


def test_release_id_is_acyclic_and_not_baked_into_descriptor() -> None:
    manifest = _manifest()
    computed = release_id(manifest)

    assert manifest.oci.reference.startswith(
        "ghcr.io/kuotunyu/model-delivery-control-plane@sha256:"
    )
    assert "release_id" not in manifest.identity_material()
    assert "oci" not in ArtifactDescriptor.model_fields
    assert "release_id" not in ArtifactDescriptor.model_fields
    assert computed.startswith("sha256:")
    assert manifest.model_copy(update={"release_id": computed}).release_id == computed


def test_release_id_changes_when_oci_subject_changes() -> None:
    manifest = _manifest()
    changed = manifest.model_copy(
        update={"oci": manifest.oci.model_copy(update={"digest": "sha256:" + "0" * 64})}
    )

    assert release_id(manifest) != release_id(changed)


def test_parsed_release_id_must_match_canonical_body() -> None:
    manifest = _manifest()
    document = manifest.model_dump(mode="json")
    document["release_id"] = "sha256:" + "0" * 64

    with pytest.raises(ValidationError, match="release_id"):
        FinalReleaseManifest.model_validate(document)


@pytest.mark.parametrize(
    "value",
    [
        "ghcr.io/kuotunyu/model-delivery-control-plane:latest",
        "docker.io/library/model:tag",
    ],
)
def test_oci_subject_rejects_mutable_reference(value: str) -> None:
    repository, _, digest = value.partition("@")
    with pytest.raises(ValidationError):
        OciSubject(repository=repository, digest=digest or "latest")


@pytest.mark.parametrize("path", ["../secret", "/absolute", "C:/host/file", "a/../../b"])
def test_bundle_member_rejects_unsafe_relative_path(path: str) -> None:
    with pytest.raises(ValidationError, match="safe relative path"):
        BundleMember(
            path=path,
            media_type="application/json",
            size_bytes=1,
            sha256="a" * 64,
        )
