from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from mdcp.feasibility.load_probe import (
    ErrorClass,
    RequestOutcome,
    build_load_document,
    classify_http_error,
    nearest_rank_us,
    response_outcome,
    run_load,
)
from mdcp.feasibility.synthetic_predictor import app

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_synthetic_predictor_returns_stable_schema() -> None:
    response = TestClient(app).post(
        "/predict",
        json={"row": {"temp": 0.4, "humidity": 0.7, "hour": 8}},
    )

    assert response.status_code == 200
    assert response.json() == {"prediction": 8.66, "schema_version": "synthetic-v1"}


def test_nearest_rank_has_no_interpolation() -> None:
    assert nearest_rank_us(list(range(1, 101)), 0.95) == 95


@pytest.mark.asyncio
async def test_absolute_clock_scheduler_respects_in_flight_limit() -> None:
    active = 0
    observed_max = 0

    async def send() -> RequestOutcome:
        nonlocal active, observed_max
        active += 1
        observed_max = max(observed_max, active)
        await asyncio.sleep(0.003)
        active -= 1
        return RequestOutcome(ok=True, status_code=200)

    result = await run_load(send, count=40, rate_rps=1_000, max_in_flight=4)

    assert result.admitted == 40
    assert result.completed == 40
    assert result.errors == 0
    assert result.max_in_flight == 4
    assert observed_max == 4


@pytest.mark.asyncio
async def test_load_probe_accounts_only_sanitized_error_classes() -> None:
    outcomes = iter(
        [
            RequestOutcome(ok=False, error_class=ErrorClass.CONNECT_ERROR),
            RequestOutcome(ok=False, error_class=ErrorClass.INVALID_RESPONSE),
            RequestOutcome(ok=True, status_code=200),
        ]
    )

    async def send() -> RequestOutcome:
        return next(outcomes)

    result = await run_load(send, count=3, rate_rps=1_000, max_in_flight=2)

    assert result.errors == 2
    assert result.error_class_counts == {
        "ConnectError": 1,
        "ConnectTimeout": 0,
        "ReadTimeout": 0,
        "ProtocolError": 0,
        "InvalidResponse": 1,
        "Other": 0,
    }


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (httpx.ConnectError("secret host"), ErrorClass.CONNECT_ERROR),
        (httpx.ConnectTimeout("secret host"), ErrorClass.CONNECT_TIMEOUT),
        (httpx.ReadTimeout("secret host"), ErrorClass.READ_TIMEOUT),
        (httpx.RemoteProtocolError("secret host"), ErrorClass.PROTOCOL_ERROR),
        (RuntimeError("secret host"), ErrorClass.OTHER),
    ],
)
def test_transport_errors_map_to_fixed_public_classes(
    error: Exception, expected: ErrorClass
) -> None:
    assert classify_http_error(error) is expected
    assert "secret" not in classify_http_error(error).value


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"prediction": 1.0}),
    ],
)
def test_invalid_http_responses_have_one_sanitized_class(response: httpx.Response) -> None:
    assert response_outcome(response) == RequestOutcome(
        ok=False,
        status_code=response.status_code,
        error_class=ErrorClass.INVALID_RESPONSE,
    )


def test_load_document_has_feasibility_claim_ceiling() -> None:
    document = build_load_document(
        admitted=2_000,
        completed=2_000,
        errors=0,
        achieved_rps=80.0,
        max_in_flight=8,
        p95_us=2_000,
        wall_time_ms=25_000,
    )

    assert document["evidence_class"] == "FEASIBILITY"
    assert document["claim_boundary"] == "load harness feasibility; not predictor performance"
    assert document["gate"]["name"] == "load_harness"
    assert document["gate"]["verdict"] == "PASS"
    assert len(document["gate"]["evidence_digest"]) == 64
    assert document["result"]["error_class_counts"] == {
        "ConnectError": 0,
        "ConnectTimeout": 0,
        "ReadTimeout": 0,
        "ProtocolError": 0,
        "InvalidResponse": 0,
        "Other": 0,
    }


def test_load_document_rejects_nonzero_error_class_even_if_error_total_is_zero() -> None:
    counts = {error_class: 0 for error_class in ErrorClass}
    counts[ErrorClass.OTHER] = 1

    document = build_load_document(
        admitted=2_000,
        completed=2_000,
        errors=0,
        achieved_rps=80.0,
        max_in_flight=8,
        p95_us=2_000,
        wall_time_ms=25_000,
        error_class_counts=counts,
    )

    assert document["gate"]["verdict"] == "FAIL"


def test_compose_load_generator_is_internal_bounded_and_evidence_scoped(
    tmp_path: Path,
) -> None:
    versions = dict(
        line.split("=", 1)
        for line in (REPOSITORY_ROOT / "constraints" / "versions.env").read_text(
            encoding="utf-8"
        ).splitlines()
        if line and not line.startswith("#")
    )
    environment = os.environ.copy()
    environment["MDCP_PYTHON_IMAGE"] = versions["PYTHON_IMAGE"]
    environment["MDCP_LOAD_EVIDENCE_DIR"] = str(tmp_path)
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "--file",
            str(REPOSITORY_ROOT / "compose.feasibility.yaml"),
            "--profile",
            "load",
            "config",
            "--format",
            "json",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    configuration = json.loads(completed.stdout)
    generator = configuration["services"]["load-generator"]
    predictor = configuration["services"]["load-predictor"]

    assert configuration["networks"]["load"]["internal"] is True
    for service in (generator, predictor):
        assert service["networks"] == {"load": None}
        assert "ports" not in service
    assert generator["user"] == "65534:65534"
    assert generator["read_only"] is True
    assert generator["cap_drop"] == ["ALL"]
    assert generator["security_opt"] == ["no-new-privileges:true"]
    assert generator["cpus"] == 0.5
    assert generator["mem_limit"] == str(128 * 1024 * 1024)
    assert generator["pids_limit"] == 64
    assert generator["tmpfs"] == ["/tmp:rw,noexec,nosuid,size=16m,mode=1777"]
    assert generator["depends_on"] == {
        "load-predictor": {"condition": "service_healthy", "required": True}
    }
    assert generator["volumes"] == [
        {
            "type": "bind",
            "source": str(tmp_path),
            "target": "/evidence",
            "bind": {"create_host_path": False},
        }
    ]
    assert generator.get("network_mode") is None
    assert generator["entrypoint"] == ["python", "-m", "mdcp.feasibility.load_probe"]
    assert generator["command"] == [
        "--url",
        "http://load-predictor:8080/predict",
        "--count",
        "2000",
        "--rate",
        "80",
        "--max-in-flight",
        "32",
        "--out",
        "/evidence/load-harness.json",
    ]
    assert all("docker.sock" not in volume["target"] for volume in generator["volumes"])
