from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from mdcp.common.enums import (
    EvidenceClass,
    ExecutionRole,
    FaultProfile,
    GateVerdict,
    ReleaseState,
    ValidationVerdict,
)
from mdcp.contracts.workload import BikeRequest, PredictionResponse, SafeErrorResponse

FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures" / "workload"
FORBIDDEN_FEATURES = {"casual", "registered", "cnt", "instant", "dteday", "yr"}


@pytest.fixture
def valid_request() -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / "single-row.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(FORBIDDEN_FEATURES))
def test_bike_request_rejects_forbidden_fields(
    valid_request: dict[str, object], name: str
) -> None:
    with pytest.raises(ValidationError):
        BikeRequest.model_validate({**valid_request, name: 1})


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -0.01, 1.01])
def test_bike_request_rejects_invalid_normalized_values(
    valid_request: dict[str, object], value: float
) -> None:
    with pytest.raises(ValidationError):
        BikeRequest.model_validate({**valid_request, "temp": value})


def test_prediction_requires_runtime_identity() -> None:
    value = PredictionResponse(
        request_id="r-1",
        release_id="sha256:" + "a" * 64,
        prediction=42.0,
        route_revision=7,
    )

    assert value.prediction == 42.0
    with pytest.raises(ValidationError):
        PredictionResponse(
            request_id="r-1",
            release_id="candidate",
            prediction=42.0,
            route_revision=7,
        )


def test_safe_error_response_has_no_raw_exception_field() -> None:
    response = SafeErrorResponse(request_id="r-1", error_code="INVALID_MODEL_OUTPUT")

    assert response.model_dump() == {
        "request_id": "r-1",
        "error_code": "INVALID_MODEL_OUTPUT",
        "retryable": False,
    }
    with pytest.raises(ValidationError):
        SafeErrorResponse(
            request_id="r-1",
            error_code="INVALID_MODEL_OUTPUT",
            exception="raw",
        )


def test_common_enums_freeze_cross_wave_values() -> None:
    assert {value.value for value in GateVerdict} == {"PASS", "FAIL", "UNKNOWN"}
    assert "QUARANTINE" in {value.value for value in ValidationVerdict}
    assert ExecutionRole.SHADOW.value == "shadow"
    assert EvidenceClass.REVIEWER_LOCALLY_RECOMPUTED.value == "reviewer_locally_recomputed"
    assert FaultProfile.SUBGROUP_CORRUPTION.value == "subgroup_corruption"
    assert ReleaseState.ROLLED_BACK.value == "ROLLED_BACK"
