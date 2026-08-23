from __future__ import annotations

import warnings
from pathlib import Path
from typing import Literal

import onnx
from pydantic import BaseModel, ConfigDict
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.pipeline import Pipeline

from mdcp.common.digests import sha256_hex
from mdcp.workload.features import approved_feature_columns

ONNX_TARGET_OPSET = 18


class OnnxReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.onnx-receipt.v1"] = "mdcp.onnx-receipt.v1"
    onnx_sha256: str
    byte_size: int
    target_opset: int
    input_names: tuple[str, ...]
    input_shapes: tuple[tuple[int | None, ...], ...]
    output_name: str
    output_shape: tuple[int | None, ...]
    operators: tuple[str, ...]


def _shape(value_info: onnx.ValueInfoProto) -> tuple[int | None, ...]:
    dimensions = value_info.type.tensor_type.shape.dim
    return tuple(dimension.dim_value or None for dimension in dimensions)


def export_pipeline_onnx(pipeline: Pipeline, path: Path) -> OnnxReceipt:
    """Export the reviewed pipeline to one bounded, local ONNX artifact."""

    inputs = [
        (name, FloatTensorType([None, 1]))
        for name in approved_feature_columns()
    ]
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Field onnx.AttributeProto.ints: Expected an int, got a boolean.*",
            category=DeprecationWarning,
        )
        model = convert_sklearn(
            pipeline,
            initial_types=inputs,
            target_opset=ONNX_TARGET_OPSET,
        )
    model.producer_name = "mdcp-skl2onnx"
    model.doc_string = ""
    for node in model.graph.node:
        node.doc_string = ""
    onnx.checker.check_model(model)
    content = model.SerializeToString()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    return OnnxReceipt(
        onnx_sha256=sha256_hex(content),
        byte_size=len(content),
        target_opset=ONNX_TARGET_OPSET,
        input_names=tuple(value.name for value in model.graph.input),
        input_shapes=tuple(_shape(value) for value in model.graph.input),
        output_name=model.graph.output[0].name,
        output_shape=_shape(model.graph.output[0]),
        operators=tuple(sorted({node.op_type for node in model.graph.node})),
    )
