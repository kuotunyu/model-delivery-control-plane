from __future__ import annotations

import math

from fastapi.testclient import TestClient

from mdcp.predictor.app import create_app

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


class FakeRuntime:
    release_id = "sha256:" + "b" * 64
    route_revision = 4
    value = 42.5

    def __init__(self) -> None:
        self.calls: list[object] = []

    def predict(self, request: object) -> float:
        self.calls.append(request)
        return self.value


def test_predictor_echoes_immutable_runtime_identity() -> None:
    client = TestClient(create_app(FakeRuntime()))

    response = client.post("/v1/predict", json=VALID_REQUEST)

    assert response.status_code == 200
    assert response.json() == {
        "request_id": "api-1",
        "release_id": "sha256:" + "b" * 64,
        "prediction": 42.5,
        "route_revision": 4,
        "traceparent": None,
    }
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_predictor_rejects_nonfinite_output_with_sanitized_error() -> None:
    runtime = FakeRuntime()
    runtime.value = math.nan
    client = TestClient(create_app(runtime), raise_server_exceptions=False)

    response = client.post("/v1/predict", json=VALID_REQUEST)

    assert response.status_code == 500
    assert response.json() == {
        "request_id": "api-1",
        "error_code": "INVALID_MODEL_OUTPUT",
        "retryable": False,
    }
    assert "nan" not in response.text.lower()


def test_predictor_validation_error_does_not_echo_invalid_input() -> None:
    client = TestClient(create_app(FakeRuntime()), raise_server_exceptions=False)
    invalid = {**VALID_REQUEST, "request_id": "sensitive", "cnt": 99}

    response = client.post("/v1/predict", json=invalid)

    assert response.status_code == 422
    assert response.json() == {
        "request_id": None,
        "error_code": "INVALID_REQUEST",
        "retryable": False,
    }
    assert "sensitive" not in response.text
    assert "cnt" not in response.text
