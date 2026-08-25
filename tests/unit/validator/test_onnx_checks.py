from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper, numpy_helper

from mdcp.common.enums import ValidationVerdict
from mdcp.validator.onnx_checks import validate_onnx
from mdcp.validator.policy import ValidationPolicy
from mdcp.validator.service import ReasonCode

REPOSITORY_ROOT = Path(__file__).parents[3]


@pytest.fixture
def policy() -> ValidationPolicy:
    return ValidationPolicy.model_validate_json(
        (REPOSITORY_ROOT / "configs" / "policy" / "validation-v1.json").read_text(encoding="utf-8")
    )


def _single_input_model(
    operator: str,
    *,
    output_value: float | None = None,
    inputs: tuple[tuple[str, tuple[int | None, ...]], ...] = (("season", (None, 1)),),
) -> bytes:
    input_infos = [
        helper.make_tensor_value_info(name, TensorProto.FLOAT, list(shape))
        for name, shape in inputs
    ]
    output_info = helper.make_tensor_value_info("prediction", TensorProto.FLOAT, [None, 1])
    if output_value is None:
        nodes = [helper.make_node(operator, ["season"], ["prediction"])]
        initializers: list[onnx.TensorProto] = []
    else:
        value = numpy_helper.from_array(
            np.asarray([[output_value]], dtype=np.float32),
            name="constant_value",
        )
        nodes = [helper.make_node("Identity", ["constant_value"], ["prediction"])]
        initializers = [value]
    graph = helper.make_graph(nodes, "adversarial", input_infos, [output_info], initializers)
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", 18)],
        ir_version=10,
    )
    return model.SerializeToString()


@pytest.mark.parametrize("role", ["stable", "candidate"])
def test_reviewer_onnx_passes_static_and_smoke_checks(
    role: str,
    policy: ValidationPolicy,
) -> None:
    path = REPOSITORY_ROOT / "tests" / "fixtures" / "artifacts" / role / "model.onnx"

    result = validate_onnx(path, policy)

    assert result.verdict is ValidationVerdict.PASS
    assert result.reason_codes == ()
    assert result.smoke_prediction is not None
    assert result.smoke_prediction >= 0


def test_unsupported_operator_fails_with_fixed_code(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    path = tmp_path / "unsupported-op.onnx"
    path.write_bytes(_single_input_model("Abs"))

    result = validate_onnx(path, policy)

    assert result.verdict is ValidationVerdict.FAIL
    assert result.reason_codes == (ReasonCode.VAL_ONNX_OPERATOR,)


@pytest.mark.parametrize("value", [float("nan"), -1.0])
def test_nonfinite_or_negative_smoke_output_fails(
    tmp_path: Path,
    policy: ValidationPolicy,
    value: float,
) -> None:
    path = tmp_path / "invalid-output.onnx"
    path.write_bytes(_single_input_model("Identity", output_value=value))

    result = validate_onnx(path, policy)

    assert result.verdict is ValidationVerdict.FAIL
    assert result.reason_codes == (ReasonCode.VAL_ONNX_INVALID,)


def test_external_data_parent_escape_is_quarantined(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    path = tmp_path / "external-parent.onnx"
    model = onnx.load_model_from_string(_single_input_model("Identity", output_value=1.0))
    tensor = model.graph.initializer[0]
    tensor.ClearField("raw_data")
    tensor.data_location = onnx.TensorProto.EXTERNAL
    tensor.external_data.add(key="location", value="../secret.bin")
    path.write_bytes(model.SerializeToString())

    result = validate_onnx(path, policy)

    assert result.verdict is ValidationVerdict.QUARANTINE
    assert result.reason_codes == (ReasonCode.VAL_PATH_ESCAPE,)


def test_expected_input_inventory_accepts_exact_names_order_and_shapes(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    path = tmp_path / "exact-inputs.onnx"
    expected_inputs = (("season", (None, 1)), ("temp", (None, 1)))
    path.write_bytes(_single_input_model("Identity", output_value=1.0, inputs=expected_inputs))

    result = validate_onnx(path, policy, expected_inputs=expected_inputs)

    assert result.verdict is ValidationVerdict.PASS


@pytest.mark.parametrize(
    "expected_inputs",
    [
        (("season", (None, 1)), ("hum", (None, 1))),
        (("temp", (None, 1)), ("season", (None, 1))),
        (("season", (None, 1)),),
        (("season", (None, 1)), ("temp", (None, 1)), ("hum", (None, 1))),
        (("season", (None, 1)), ("temp", (None, 2))),
    ],
    ids=["unknown", "reordered", "missing", "extra", "wrong-shaped"],
)
def test_expected_input_inventory_rejects_any_contract_mismatch(
    tmp_path: Path,
    policy: ValidationPolicy,
    expected_inputs: tuple[tuple[str, tuple[int | None, ...]], ...],
) -> None:
    path = tmp_path / "invalid-inputs.onnx"
    actual_inputs = (("season", (None, 1)), ("temp", (None, 1)))
    path.write_bytes(_single_input_model("Identity", output_value=1.0, inputs=actual_inputs))

    result = validate_onnx(path, policy, expected_inputs=expected_inputs)

    assert result.verdict is ValidationVerdict.FAIL
    assert result.reason_codes == (ReasonCode.VAL_ONNX_INVALID,)
