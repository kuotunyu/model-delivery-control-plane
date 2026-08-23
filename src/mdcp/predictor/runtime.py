from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import onnxruntime as ort

from mdcp.common.digests import sha256_hex
from mdcp.contracts.workload import BikeRequest
from mdcp.workload.features import approved_feature_columns


class ModelBindingError(ValueError):
    """Raised before readiness when local model bytes do not match the descriptor."""


class PredictionContractError(RuntimeError):
    """Raised when a runtime output cannot satisfy the public response contract."""


class OnnxPredictor:
    def __init__(
        self,
        *,
        onnx_path: Path,
        expected_sha256: str,
        release_id: str,
        route_revision: int,
    ) -> None:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", release_id) or route_revision <= 0:
            raise ModelBindingError("invalid deployment identity")
        content = onnx_path.read_bytes()
        if sha256_hex(content) != expected_sha256:
            raise ModelBindingError("ONNX digest does not match descriptor")
        self.release_id = release_id
        self.route_revision = route_revision
        self.session = ort.InferenceSession(content, providers=["CPUExecutionProvider"])
        self.output_name = self.session.get_outputs()[0].name
        actual_inputs = tuple(value.name for value in self.session.get_inputs())
        if actual_inputs != approved_feature_columns():
            raise ModelBindingError("ONNX input contract differs from workload contract")

    @staticmethod
    def tensor(request: BikeRequest) -> dict[str, np.ndarray]:
        values = request.model_dump()
        return {
            name: np.asarray([[values[name]]], dtype=np.float32)
            for name in approved_feature_columns()
        }

    def predict(self, request: BikeRequest) -> float:
        raw = self.session.run([self.output_name], self.tensor(request))[0]
        value = float(np.asarray(raw).reshape(-1)[0])
        if not math.isfinite(value) or value < 0:
            raise PredictionContractError("invalid model output")
        return value
