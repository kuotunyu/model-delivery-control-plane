from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from mdcp.contracts import workload as workload_v1
from mdcp.contracts.workload import BikeRequest
from mdcp.contracts.workload_v2 import BikeRequestEnvelope, BikeRequestV2

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_PATH = REPOSITORY_ROOT / "schemas" / "v2" / "bike-request.schema.json"

VALID_V2 = {
    "schema_version": "mdcp.bike-request.v2",
    "request_id": "v2-origin",
    "event_timestamp": "2011-01-01T00:00:00-05:00",
    "season": 1,
    "mnth": 1,
    "hr": 0,
    "holiday": 0,
    "weekday": 6,
    "workingday": 0,
    "weathersit": 1,
    "temp": 0.24,
    "atemp": 0.2879,
    "hum": 0.81,
    "windspeed": 0.0,
}


def test_v1_and_v2_request_modules_are_disjoint() -> None:
    assert BikeRequest.__module__ == "mdcp.contracts.workload"
    assert BikeRequestV2.__module__ == "mdcp.contracts.workload_v2"
    assert not hasattr(workload_v1, "BikeRequestV2")
    assert not hasattr(workload_v1, "BikeRequestEnvelope")


def test_v2_envelope_is_strict_and_reduces_to_v1() -> None:
    request = BikeRequestV2.model_validate(VALID_V2)
    legacy = request.to_legacy()

    assert request.schema_version == "mdcp.bike-request.v2"
    assert isinstance(legacy, BikeRequest)
    assert legacy.model_dump() == {
        key: value
        for key, value in VALID_V2.items()
        if key not in {"schema_version", "event_timestamp"}
    }
    assert set(get_args(BikeRequestEnvelope)) == {BikeRequest, BikeRequestV2}


@pytest.mark.parametrize("name", ["yr", "dteday", "instant", "casual", "registered", "cnt"])
def test_v2_rejects_forbidden_fields(name: str) -> None:
    with pytest.raises(ValidationError):
        BikeRequestV2.model_validate({**VALID_V2, name: 1})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "mdcp.bike-request.v3"),
        ("event_timestamp", "2011-01-01T00:00:00Z"),
        ("request_id", ""),
    ],
)
def test_v2_rejects_invalid_envelope_identity(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        BikeRequestV2.model_validate({**VALID_V2, field: value})


def test_checked_in_v2_schema_is_exact_pydantic_output() -> None:
    expected = (
        json.dumps(BikeRequestV2.model_json_schema(), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    assert SCHEMA_PATH.read_bytes() == expected
