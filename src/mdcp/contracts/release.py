from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    StringConstraints,
    model_validator,
)

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import EvidenceClass

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]


class OnnxMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sha256: Sha256
    size_bytes: PositiveInt = Field(le=64 * 1024 * 1024)
    opset: PositiveInt
    operators: tuple[str, ...]
    input_names: tuple[str, ...]
    output_name: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_inventory(self) -> OnnxMetadata:
        if not self.operators or tuple(sorted(set(self.operators))) != self.operators:
            raise ValueError("operators must be non-empty, unique, and sorted")
        if not self.input_names or len(set(self.input_names)) != len(self.input_names):
            raise ValueError("input names must be non-empty and unique")
        return self


class InventoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1, max_length=256)
    sha256: Sha256


class ServingInventory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entry_point: Literal["mdcp.predictor.app:app"]
    environment: tuple[str, ...]
    entries: tuple[InventoryEntry, ...]

    @model_validator(mode="after")
    def validate_ordering(self) -> ServingInventory:
        if tuple(sorted(set(self.environment))) != self.environment:
            raise ValueError("environment inventory must be unique and sorted")
        paths = tuple(entry.path for entry in self.entries)
        if tuple(sorted(set(paths))) != paths:
            raise ValueError("serving paths must be unique and sorted")
        return self


class ArtifactDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["artifact-descriptor/v1"]
    model_name: Literal["stable", "candidate"]
    evidence_class: EvidenceClass
    training_data_kind: Literal["deterministic_generated", "uci_bike_sharing_2011"]
    git_source_sha: GitSha
    model_sha256: Sha256
    schema_digest: Sha256
    serving_code_config_id: Sha256
    feature_manifest_sha256: Sha256
    dependency_lock_sha256: Sha256
    split_manifest_sha256: Sha256
    training_receipt_sha256: Sha256
    h1_report_sha256: Sha256
    onnx: OnnxMetadata

    @model_validator(mode="after")
    def bind_model_digest(self) -> ArtifactDescriptor:
        if self.model_sha256 != self.onnx.sha256:
            raise ValueError("model_sha256 must match onnx.sha256")
        return self


SERVING_PATHS = (
    "docker/predictor.Dockerfile",
    "pyproject.toml",
    "schemas/v1/bike-request.schema.json",
    "schemas/v1/prediction-response.schema.json",
    "src/mdcp/contracts/workload.py",
    "src/mdcp/predictor/app.py",
    "src/mdcp/predictor/runtime.py",
    "uv.lock",
)
SERVING_ENVIRONMENT = (
    "MDCP_DESCRIPTOR_PATH",
    "MDCP_ONNX_PATH",
    "MDCP_RELEASE_ID",
    "MDCP_ROUTE_REVISION",
)


def artifact_descriptor_digest(descriptor: ArtifactDescriptor) -> str:
    return sha256_hex(canonicalize_json(descriptor.model_dump(mode="json")))


def serving_inventory_digest(inventory: ServingInventory) -> str:
    return sha256_hex(canonicalize_json(inventory.model_dump(mode="json")))


def serving_inventory_from_root(repository_root: Path) -> ServingInventory:
    entries = tuple(
        InventoryEntry(path=path, sha256=sha256_hex((repository_root / path).read_bytes()))
        for path in SERVING_PATHS
    )
    return ServingInventory(
        entry_point="mdcp.predictor.app:app",
        environment=SERVING_ENVIRONMENT,
        entries=entries,
    )
