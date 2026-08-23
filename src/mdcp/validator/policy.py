from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OnnxOperatorPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.onnx-operator-policy.v1"]
    minimum_opset: int = Field(ge=1)
    maximum_opset: int = Field(ge=1)
    operators: tuple[str, ...]

    @model_validator(mode="after")
    def validate_policy(self) -> OnnxOperatorPolicy:
        if self.minimum_opset > self.maximum_opset:
            raise ValueError("minimum opset exceeds maximum opset")
        if tuple(sorted(set(self.operators))) != self.operators:
            raise ValueError("operator allowlist must be unique and sorted")
        return self


class ValidationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.validation-policy.v1"]
    max_file_count: int = Field(ge=1, le=1024)
    max_total_bytes: int = Field(ge=1, le=256 * 1024 * 1024)
    max_single_file_bytes: int = Field(ge=1, le=128 * 1024 * 1024)
    max_onnx_bytes: int = Field(ge=1, le=64 * 1024 * 1024)
    max_graph_nodes: int = Field(ge=1, le=16384)
    minimum_opset: int = Field(ge=1)
    maximum_opset: int = Field(ge=1)
    allowed_operators: tuple[str, ...]
    forbidden_suffixes: tuple[str, ...]
    smoke_input: dict[str, float]

    @model_validator(mode="after")
    def validate_policy(self) -> ValidationPolicy:
        if self.minimum_opset > self.maximum_opset:
            raise ValueError("minimum opset exceeds maximum opset")
        if tuple(sorted(set(self.allowed_operators))) != self.allowed_operators:
            raise ValueError("operator allowlist must be unique and sorted")
        if tuple(sorted(set(self.forbidden_suffixes))) != self.forbidden_suffixes:
            raise ValueError("forbidden suffixes must be unique and sorted")
        if not self.smoke_input:
            raise ValueError("smoke input must not be empty")
        return self


def load_validation_policy(
    validation_path: Path,
    operator_path: Path,
) -> ValidationPolicy:
    validation = ValidationPolicy.model_validate_json(
        validation_path.read_text(encoding="utf-8")
    )
    operators = OnnxOperatorPolicy.model_validate_json(
        operator_path.read_text(encoding="utf-8")
    )
    if (
        validation.minimum_opset != operators.minimum_opset
        or validation.maximum_opset != operators.maximum_opset
        or validation.allowed_operators != operators.operators
    ):
        raise ValueError("validation policy does not match frozen operator policy")
    return validation
