from __future__ import annotations

import json
from pathlib import Path

from mdcp.contracts.workload import BikeRequest, PredictionResponse

REPOSITORY_ROOT = Path(__file__).parents[3]


def test_checked_in_workload_schemas_match_pydantic_source() -> None:
    expected = {
        "bike-request.schema.json": BikeRequest.model_json_schema(),
        "prediction-response.schema.json": PredictionResponse.model_json_schema(),
    }

    for filename, schema in expected.items():
        checked_in = json.loads(
            (REPOSITORY_ROOT / "schemas" / "v1" / filename).read_text(encoding="utf-8")
        )
        assert checked_in == schema


def test_bike_schema_is_strict_and_has_only_approved_request_fields() -> None:
    schema = BikeRequest.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "request_id",
        "season",
        "mnth",
        "hr",
        "holiday",
        "weekday",
        "workingday",
        "weathersit",
        "temp",
        "atemp",
        "hum",
        "windspeed",
    }
