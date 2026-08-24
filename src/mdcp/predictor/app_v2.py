from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from mdcp.common.enums import ExecutionRole
from mdcp.contracts.workload import PredictionResponse, SafeErrorResponse
from mdcp.predictor.runtime import OnnxPredictor, PredictionContractError
from mdcp.temporal.routing import AdmissionKind, classify_envelope


class PredictorRuntime(Protocol):
    release_id: str
    route_revision: int

    def predict(self, request: object) -> float: ...


def _error(
    status_code: int,
    error_code: str,
    request_id: str | None = None,
) -> JSONResponse:
    body = SafeErrorResponse(request_id=request_id, error_code=error_code)
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def create_app(
    runtime: PredictorRuntime,
    *,
    admission_role: ExecutionRole = ExecutionRole.STABLE,
) -> FastAPI:
    application = FastAPI(title="MDCP v2 immutable ONNX predictor", docs_url=None, redoc_url=None)
    application.state.admission_counts = {kind: 0 for kind in AdmissionKind}

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        del request, error
        return _error(422, "INVALID_REQUEST")

    @application.exception_handler(Exception)
    async def internal_error(request: Request, error: Exception) -> JSONResponse:
        del request, error
        return _error(500, "INTERNAL_ERROR")

    @application.get("/health/ready")
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @application.post(
        "/v1/predict",
        response_model=PredictionResponse,
        responses={422: {"model": SafeErrorResponse}, 500: {"model": SafeErrorResponse}},
    )
    async def predict(payload: dict[str, object]) -> PredictionResponse | JSONResponse:
        try:
            decision = classify_envelope(payload)
        except ValidationError:
            return _error(422, "INVALID_REQUEST")

        application.state.admission_counts[decision.kind] += 1
        if decision.kind is AdmissionKind.INVALID_V2:
            return _error(422, decision.reason_code or "INVALID_V2_ENVELOPE")

        if decision.kind is AdmissionKind.LEGACY_STABLE_ONLY:
            if admission_role is not ExecutionRole.STABLE:
                return _error(422, AdmissionKind.LEGACY_STABLE_ONLY.value)
            if decision.legacy_request is None:
                return _error(422, "INVALID_REQUEST")
            runtime_request = decision.legacy_request
            request_id = decision.legacy_request.request_id
        else:
            if decision.v2_request is None:
                return _error(422, "INVALID_V2_ENVELOPE")
            request_id = decision.v2_request.request_id
            if admission_role is ExecutionRole.STABLE:
                runtime_request = decision.v2_request.to_legacy()
            else:
                if decision.feature_vector is None:
                    return _error(422, "INVALID_V2_ENVELOPE")
                runtime_request = decision.feature_vector

        try:
            value = runtime.predict(runtime_request)
            if not math.isfinite(value) or value < 0:
                raise PredictionContractError("invalid model output")
        except PredictionContractError:
            return _error(500, "INVALID_MODEL_OUTPUT", request_id)
        return PredictionResponse(
            request_id=request_id,
            release_id=runtime.release_id,
            prediction=value,
            route_revision=runtime.route_revision,
        )

    return application


def runtime_from_environment() -> OnnxPredictor:
    descriptor_path = Path(os.environ["MDCP_DESCRIPTOR_PATH"])
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    onnx_metadata = descriptor.get("onnx", descriptor)
    expected_sha256 = onnx_metadata.get("sha256") or onnx_metadata["onnx_sha256"]
    return OnnxPredictor(
        onnx_path=Path(os.environ["MDCP_ONNX_PATH"]),
        expected_sha256=expected_sha256,
        release_id=os.environ["MDCP_RELEASE_ID"],
        route_revision=int(os.environ["MDCP_ROUTE_REVISION"]),
    )


app = create_app(runtime_from_environment()) if os.getenv("MDCP_ONNX_PATH") else FastAPI()
