from __future__ import annotations

import hashlib
import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import pandas as pd
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from skl2onnx import convert_sklearn, update_registered_converter
from skl2onnx.common.data_types import FloatTensorType
from skl2onnx.shape_calculators.scaler import calculate_sklearn_scaler_output_shapes
from sklearn.pipeline import Pipeline

from mdcp.common.enums import ValidationVerdict
from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS
from mdcp.temporal.trials import build_estimator, load_trial_specs
from mdcp.validator.onnx_checks import validate_onnx
from mdcp.validator.policy import ValidationPolicy
from mdcp.validator.service import ReasonCode

REPOSITORY_ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = REPOSITORY_ROOT / "configs" / "workload" / "temporal-development-v2.json"
OPERATOR_POLICY_PATH = REPOSITORY_ROOT / "configs" / "policy" / "onnx-operators-v2.json"
VALIDATION_POLICY_PATH = REPOSITORY_ROOT / "configs" / "policy" / "validation-v2.json"

V2_OPERATOR_ALLOWLIST = (
    "Add",
    "ArrayFeatureExtractor",
    "Cast",
    "Concat",
    "Identity",
    "LinearRegressor",
    "MatMul",
    "OneHotEncoder",
    "Relu",
    "Reshape",
    "Scaler",
    "TreeEnsembleRegressor",
)
REPRESENTATIVE_TRIALS = (
    "CTRL-01",
    "REC-180-L4",
    "STAT-A1",
    "NL-E64-R0.03-D2",
)
EXPECTED_OPERATORS = {
    "CTRL-01": ("Concat", "Relu", "TreeEnsembleRegressor"),
    "REC-180-L4": ("Concat", "Relu", "TreeEnsembleRegressor"),
    "STAT-A1": (
        "Cast",
        "Concat",
        "LinearRegressor",
        "OneHotEncoder",
        "Relu",
        "Reshape",
        "Scaler",
    ),
    "NL-E64-R0.03-D2": ("Concat", "Relu", "TreeEnsembleRegressor"),
}


@dataclass(frozen=True)
class ConversionEvidence:
    onnx_sha256: str
    input_names: tuple[str, ...]
    input_shapes: tuple[tuple[int | None, ...], ...]
    operators: tuple[str, ...]
    opset: int
    native_predictions: np.ndarray
    onnx_predictions: np.ndarray
    negative_raw_predictions: np.ndarray
    negative_native_predictions: np.ndarray
    negative_onnx_predictions: np.ndarray

    @property
    def parity_allclose(self) -> bool:
        return bool(
            np.allclose(
                self.onnx_predictions,
                self.native_predictions,
                rtol=1e-5,
                atol=1e-5,
            )
        )


def _synthetic_rows() -> pd.DataFrame:
    count = 28 * 24
    position = np.arange(count, dtype=float)
    hour = (position % 24).astype(int)
    day = (position // 24).astype(int)
    weekday = day % 7
    elapsed_days = position / 24
    rows = pd.DataFrame(
        {
            "season": day % 4 + 1,
            "mnth": day % 12 + 1,
            "hr": hour,
            "holiday": (day % 11 == 0).astype(int),
            "weekday": weekday,
            "workingday": ((weekday != 0) & (weekday != 6)).astype(int),
            "weathersit": (day + hour) % 4 + 1,
            "temp": 0.2 + 0.001 * position,
            "atemp": 0.25 + 0.0009 * position,
            "hum": 0.8 - 0.0005 * position,
            "windspeed": (day * 7 + hour * 17) % 101 / 100,
            "elapsed_days": elapsed_days,
            "hour_sin": np.sin(2 * math.pi * hour / 24),
            "hour_cos": np.cos(2 * math.pi * hour / 24),
            "weekday_sin": np.sin(2 * math.pi * weekday / 7),
            "weekday_cos": np.cos(2 * math.pi * weekday / 7),
            "annual_sin": np.sin(2 * math.pi * elapsed_days / 365.2425),
            "annual_cos": np.cos(2 * math.pi * elapsed_days / 365.2425),
        },
        index=pd.date_range("2011-01-01", periods=count, freq="h", name="event_timestamp"),
    )
    rows["cnt"] = 20 + 0.05 * position + 8 * np.sin(2 * math.pi * hour / 24)
    rows.attrs = {
        "evidence_class": "synthetic_test",
        "source_kind": "deterministic_generated",
        "uci_rows": 0,
    }
    return rows


def _shape(value: onnx.ValueInfoProto) -> tuple[int | None, ...]:
    return tuple(dimension.dim_value or None for dimension in value.type.tensor_type.shape.dim)


def _convert_population_scaler(scope, operator, container) -> None:
    scaler = operator.raw_operator
    container.add_node(
        "Scaler",
        operator.inputs[0].full_name,
        operator.outputs[0].full_name,
        op_domain="ai.onnx.ml",
        name=scope.get_unique_operator_name("Scaler"),
        offset=scaler.mean_.astype(np.float32),
        scale=(1.0 / scaler.scale_).astype(np.float32),
    )


def _feed(frame: pd.DataFrame, input_names: tuple[str, ...]) -> dict[str, np.ndarray]:
    return {name: frame.loc[:, [name]].to_numpy(dtype=np.float32) for name in input_names}


def convert_synthetic_trial(trial_id: str, path: Path) -> ConversionEvidence:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    spec = next(spec for spec in load_trial_specs(protocol) if spec.trial_id == trial_id)
    input_names = tuple(
        TEMPORAL_FEATURE_COLUMNS[position - 1] for position in spec.feature_positions
    )
    rows = _synthetic_rows()
    features = rows.loc[:, input_names]
    estimator = build_estimator(spec).fit(features, rows["cnt"])

    if trial_id == "STAT-A1":
        population_scaler = type(estimator.named_steps["preprocess"].transformers_[1][1])
        update_registered_converter(
            population_scaler,
            "MdcpPopulationStandardScaler",
            calculate_sklearn_scaler_output_shapes,
            _convert_population_scaler,
        )

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Field onnx.AttributeProto.ints: Expected an int, got a boolean.*",
            category=DeprecationWarning,
        )
        model = convert_sklearn(
            Pipeline(estimator.steps),
            initial_types=[(name, FloatTensorType([None, 1])) for name in input_names],
            target_opset=18,
        )

    raw_output_name = model.graph.output[0].name
    model.graph.output[0].name = "clipped_prediction"
    model.graph.node.append(
        onnx.helper.make_node(
            "Relu",
            [raw_output_name],
            ["clipped_prediction"],
            name="MDCPNonNegativeClip",
        )
    )
    model.graph.name = f"mdcp-{trial_id}"
    for opset_import in model.opset_import:
        if opset_import.domain in {"", "ai.onnx"}:
            opset_import.version = 18
    model.producer_name = "mdcp-skl2onnx"
    model.doc_string = ""
    for node in model.graph.node:
        node.doc_string = ""
    onnx.checker.check_model(model)
    content = model.SerializeToString()
    path.write_bytes(content)

    session = ort.InferenceSession(content, providers=["CPUExecutionProvider"])
    probe = features.tail(16).copy()
    native_predictions = np.asarray(estimator.predict(probe), dtype=float).reshape(-1)
    onnx_predictions = np.asarray(session.run(None, _feed(probe, input_names))[0]).reshape(-1)

    negative_raw_predictions = np.asarray([], dtype=float)
    negative_native_predictions = np.asarray([], dtype=float)
    negative_onnx_predictions = np.asarray([], dtype=float)
    if trial_id == "STAT-A1":
        negative_probe = probe.head(1).copy()
        negative_probe.loc[:, TEMPORAL_FEATURE_COLUMNS[7:]] = -1_000_000.0
        negative_raw_predictions = estimator.predict_raw(negative_probe)
        negative_native_predictions = estimator.predict(negative_probe)
        negative_onnx_predictions = np.asarray(
            session.run(None, _feed(negative_probe, input_names))[0]
        ).reshape(-1)

    operators = tuple(sorted({node.op_type for node in model.graph.node}))
    opset = next(item.version for item in model.opset_import if item.domain in {"", "ai.onnx"})
    policy = ValidationPolicy.model_validate_json(
        VALIDATION_POLICY_PATH.read_text(encoding="utf-8")
    )
    expected_inputs = tuple((name, (None, 1)) for name in input_names)
    validation = validate_onnx(path, policy, expected_inputs=expected_inputs)
    assert validation.verdict is ValidationVerdict.PASS

    return ConversionEvidence(
        onnx_sha256=hashlib.sha256(content).hexdigest(),
        input_names=tuple(value.name for value in model.graph.input),
        input_shapes=tuple(_shape(value) for value in model.graph.input),
        operators=operators,
        opset=opset,
        native_predictions=native_predictions,
        onnx_predictions=onnx_predictions,
        negative_raw_predictions=negative_raw_predictions,
        negative_native_predictions=negative_native_predictions,
        negative_onnx_predictions=negative_onnx_predictions,
    )


def test_v2_policies_are_exact_and_retain_validator_limits() -> None:
    operator_policy = json.loads(OPERATOR_POLICY_PATH.read_text(encoding="utf-8"))
    validation_policy = ValidationPolicy.model_validate_json(
        VALIDATION_POLICY_PATH.read_text(encoding="utf-8")
    )

    assert tuple(operator_policy["operators"]) == V2_OPERATOR_ALLOWLIST
    assert validation_policy.allowed_operators == V2_OPERATOR_ALLOWLIST
    assert validation_policy.max_onnx_bytes == 64 * 1024 * 1024
    assert validation_policy.max_graph_nodes == 4096
    assert (validation_policy.minimum_opset, validation_policy.maximum_opset) == (13, 18)
    assert tuple(validation_policy.smoke_input) == TEMPORAL_FEATURE_COLUMNS


@pytest.mark.parametrize("trial_id", REPRESENTATIVE_TRIALS)
def test_family_converter_is_deterministic_and_allowlisted(
    trial_id: str,
    tmp_path: Path,
) -> None:
    first_path = tmp_path / f"{trial_id}-first.onnx"
    second_path = tmp_path / f"{trial_id}-second.onnx"

    first = convert_synthetic_trial(trial_id, first_path)
    second = convert_synthetic_trial(trial_id, second_path)

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    spec = next(spec for spec in load_trial_specs(protocol) if spec.trial_id == trial_id)
    expected_names = tuple(
        TEMPORAL_FEATURE_COLUMNS[position - 1] for position in spec.feature_positions
    )
    assert first_path.read_bytes() == second_path.read_bytes()
    assert first.onnx_sha256 == second.onnx_sha256
    assert first.input_names == expected_names
    assert first.input_shapes == ((None, 1),) * len(expected_names)
    assert first.operators == EXPECTED_OPERATORS[trial_id]
    assert set(first.operators) <= set(V2_OPERATOR_ALLOWLIST)
    assert "Relu" in first.operators
    assert first.opset == 18
    assert np.isfinite(first.onnx_predictions).all()
    assert (first.onnx_predictions >= 0).all()
    assert first.parity_allclose is True
    assert_allclose(
        first.onnx_predictions,
        first.native_predictions,
        rtol=1e-5,
        atol=1e-5,
    )

    if trial_id == "STAT-A1":
        assert first.negative_raw_predictions[0] < 0
        assert_array_equal(
            first.negative_native_predictions,
            np.maximum(0.0, first.negative_raw_predictions),
        )
        assert_allclose(
            first.negative_onnx_predictions,
            first.negative_native_predictions,
            rtol=0,
            atol=0,
        )
        assert first.negative_onnx_predictions[0] == 0


def test_family_converter_rejects_reordered_expected_inputs(tmp_path: Path) -> None:
    trial_id = "STAT-A1"
    path = tmp_path / "reordered-inputs.onnx"
    evidence = convert_synthetic_trial(trial_id, path)
    policy = ValidationPolicy.model_validate_json(
        VALIDATION_POLICY_PATH.read_text(encoding="utf-8")
    )
    reordered = tuple(
        (name, shape)
        for name, shape in reversed(
            tuple(zip(evidence.input_names, evidence.input_shapes, strict=True))
        )
    )

    result = validate_onnx(path, policy, expected_inputs=reordered)

    assert result.verdict is ValidationVerdict.FAIL
    assert result.reason_codes == (ReasonCode.VAL_ONNX_INVALID,)
