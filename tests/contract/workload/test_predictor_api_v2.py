from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from mdcp.common.enums import ExecutionRole
from mdcp.contracts.workload import BikeRequest
from mdcp.predictor.app import app as v1_app
from mdcp.predictor.app import create_app as create_v1_app
from mdcp.predictor.app_v2 import app as v2_app
from mdcp.predictor.app_v2 import create_app as create_v2_app
from mdcp.temporal.adapter import TemporalFeatureVector
from mdcp.temporal.routing import AdmissionKind

VALID_REQUEST = {
    "request_id": "api-1",
    "season": 1,
    "mnth": 1,
    "hr": 8,
    "holiday": 0,
    "weekday": 1,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.24,
    "atemp": 0.2879,
    "hum": 0.81,
    "windspeed": 0.0,
}
VALID_V2_REQUEST = {
    **VALID_REQUEST,
    "request_id": "api-v2",
    "schema_version": "mdcp.bike-request.v2",
    "event_timestamp": "2011-01-03T08:00:00-05:00",
}


class FakeRuntime:
    release_id = "sha256:" + "b" * 64
    route_revision = 4
    value = 42.5

    def __init__(self) -> None:
        self.calls: list[object] = []

    def predict(self, request: object) -> float:
        self.calls.append(request)
        return self.value


def test_entry_points_are_explicit_and_distinct() -> None:
    assert v1_app is not v2_app
    assert create_v1_app.__module__ == "mdcp.predictor.app"
    assert create_v2_app.__module__ == "mdcp.predictor.app_v2"


@pytest.mark.parametrize(
    ("payload", "error_code"),
    [
        ({**VALID_REQUEST, "schema_version": "mdcp.bike-request.v2"}, "MISSING_EVENT_TIMESTAMP"),
        (
            {**VALID_REQUEST, "event_timestamp": VALID_V2_REQUEST["event_timestamp"]},
            "INVALID_V2_ENVELOPE",
        ),
        (
            {**VALID_V2_REQUEST, "schema_version": "mdcp.bike-request.v3"},
            "INVALID_V2_ENVELOPE",
        ),
    ],
)
def test_partial_or_invalid_v2_never_calls_runtime(
    payload: dict[str, object], error_code: str
) -> None:
    runtime = FakeRuntime()
    client = TestClient(create_v2_app(runtime), raise_server_exceptions=False)

    response = client.post("/v1/predict", json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "request_id": None,
        "error_code": error_code,
        "retryable": False,
    }
    assert runtime.calls == []


def test_stable_role_accepts_legacy_and_reduces_valid_v2_to_v1() -> None:
    runtime = FakeRuntime()
    app = create_v2_app(runtime, admission_role=ExecutionRole.STABLE)
    client = TestClient(app)

    assert client.post("/v1/predict", json=VALID_REQUEST).status_code == 200
    assert client.post("/v1/predict", json=VALID_V2_REQUEST).status_code == 200

    assert len(runtime.calls) == 2
    assert all(isinstance(request, BikeRequest) for request in runtime.calls)
    assert app.state.admission_counts == {
        AdmissionKind.LEGACY_STABLE_ONLY: 1,
        AdmissionKind.V2_CANDIDATE_ELIGIBLE: 1,
        AdmissionKind.INVALID_V2: 0,
    }


def test_candidate_role_rejects_legacy_and_receives_only_temporal_vector() -> None:
    runtime = FakeRuntime()
    app = create_v2_app(runtime, admission_role=ExecutionRole.CANDIDATE)
    client = TestClient(app)

    legacy_response = client.post("/v1/predict", json=VALID_REQUEST)
    candidate_response = client.post("/v1/predict", json=VALID_V2_REQUEST)

    assert legacy_response.status_code == 422
    assert legacy_response.json()["error_code"] == "LEGACY_STABLE_ONLY"
    assert candidate_response.status_code == 200
    assert len(runtime.calls) == 1
    assert isinstance(runtime.calls[0], TemporalFeatureVector)


def test_v2_predictor_rejects_nonfinite_output_with_sanitized_error() -> None:
    runtime = FakeRuntime()
    runtime.value = math.nan
    client = TestClient(create_v2_app(runtime), raise_server_exceptions=False)

    response = client.post("/v1/predict", json=VALID_V2_REQUEST)

    assert response.status_code == 500
    assert response.json() == {
        "request_id": "api-v2",
        "error_code": "INVALID_MODEL_OUTPUT",
        "retryable": False,
    }
    assert "nan" not in response.text.lower()
