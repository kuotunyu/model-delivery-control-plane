from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

import numpy as np
import onnx
import onnxruntime as ort
from pydantic import BaseModel, ConfigDict

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import ValidationVerdict
from mdcp.validator.policy import ValidationPolicy
from mdcp.validator.service import ReasonCode, ValidationCheck, make_check


class OnnxValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: ValidationVerdict
    reason_codes: tuple[ReasonCode, ...]
    checks: tuple[ValidationCheck, ...]
    operators: tuple[str, ...] = ()
    opset: int | None = None
    smoke_prediction: float | None = None


def _result(
    content: bytes,
    code: ReasonCode,
    verdict: ValidationVerdict,
    *,
    operators: tuple[str, ...] = (),
    opset: int | None = None,
    smoke_prediction: float | None = None,
) -> OnnxValidationResult:
    facts = {
        "artifact_sha256": sha256_hex(content),
        "code": code.value,
        "operators": operators,
        "opset": opset,
    }
    check = make_check(
        code,
        verdict,
        evidence_digest=sha256_hex(canonicalize_json(facts)),
    )
    return OnnxValidationResult(
        verdict=verdict,
        reason_codes=() if verdict is ValidationVerdict.PASS else (code,),
        checks=(check,),
        operators=operators,
        opset=opset,
        smoke_prediction=smoke_prediction,
    )


def _external_location_is_unsafe(model: onnx.ModelProto) -> bool:
    for tensor in model.graph.initializer:
        if tensor.data_location != onnx.TensorProto.EXTERNAL:
            continue
        locations = [
            item.value.replace("\\", "/") for item in tensor.external_data if item.key == "location"
        ]
        for location in locations:
            path = PurePosixPath(location)
            if path.is_absolute() or ".." in path.parts:
                return True
        return True
    return False


def _shape_is_bounded(value_info: onnx.ValueInfoProto) -> bool:
    dimensions = value_info.type.tensor_type.shape.dim
    if len(dimensions) > 2:
        return False
    return all(
        not dimension.dim_value or dimension.dim_value <= 1_000_000 for dimension in dimensions
    )


def _input_inventory(
    model: onnx.ModelProto,
) -> tuple[tuple[str, tuple[int | None, ...]], ...]:
    return tuple(
        (
            value.name,
            tuple(dimension.dim_value or None for dimension in value.type.tensor_type.shape.dim),
        )
        for value in model.graph.input
    )


def validate_onnx(
    path: Path,
    policy: ValidationPolicy,
    expected_inputs: Sequence[tuple[str, Sequence[int | None]]] | None = None,
) -> OnnxValidationResult:
    if path.stat().st_size > policy.max_onnx_bytes:
        return _result(b"", ReasonCode.VAL_RESOURCE_LIMIT, ValidationVerdict.FAIL)
    content = path.read_bytes()
    try:
        model = onnx.load_model_from_string(content)
    except Exception:
        return _result(content, ReasonCode.VAL_ONNX_INVALID, ValidationVerdict.FAIL)

    operators = tuple(sorted({node.op_type for node in model.graph.node}))
    opset = next(
        (item.version for item in model.opset_import if item.domain in {"", "ai.onnx"}),
        None,
    )
    if _external_location_is_unsafe(model):
        return _result(
            content,
            ReasonCode.VAL_PATH_ESCAPE,
            ValidationVerdict.QUARANTINE,
            operators=operators,
            opset=opset,
        )
    if (
        opset is None
        or not policy.minimum_opset <= opset <= policy.maximum_opset
        or len(model.graph.node) > policy.max_graph_nodes
        or any(operator not in policy.allowed_operators for operator in operators)
    ):
        return _result(
            content,
            ReasonCode.VAL_ONNX_OPERATOR,
            ValidationVerdict.FAIL,
            operators=operators,
            opset=opset,
        )
    if not all(
        _shape_is_bounded(value)
        for value in (*model.graph.input, *model.graph.output, *model.graph.value_info)
    ):
        return _result(
            content,
            ReasonCode.VAL_RESOURCE_LIMIT,
            ValidationVerdict.FAIL,
            operators=operators,
            opset=opset,
        )
    if expected_inputs is not None and _input_inventory(model) != tuple(
        (name, tuple(shape)) for name, shape in expected_inputs
    ):
        return _result(
            content,
            ReasonCode.VAL_ONNX_INVALID,
            ValidationVerdict.FAIL,
            operators=operators,
            opset=opset,
        )
    try:
        onnx.checker.check_model(model)
        session = ort.InferenceSession(content, providers=["CPUExecutionProvider"])
        feed = {
            item.name: np.asarray(
                [[policy.smoke_input.get(item.name, 0.5)]],
                dtype=np.float32,
            )
            for item in session.get_inputs()
        }
        output = session.run(None, feed)[0]
        smoke_prediction = float(np.asarray(output).reshape(-1)[0])
    except Exception:
        return _result(
            content,
            ReasonCode.VAL_ONNX_INVALID,
            ValidationVerdict.FAIL,
            operators=operators,
            opset=opset,
        )
    if not math.isfinite(smoke_prediction) or smoke_prediction < 0:
        return _result(
            content,
            ReasonCode.VAL_ONNX_INVALID,
            ValidationVerdict.FAIL,
            operators=operators,
            opset=opset,
        )
    return _result(
        content,
        ReasonCode.VAL_OK,
        ValidationVerdict.PASS,
        operators=operators,
        opset=opset,
        smoke_prediction=smoke_prediction,
    )
