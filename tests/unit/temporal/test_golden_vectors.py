from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

from mdcp.contracts.workload_v2 import BikeRequestV2
from mdcp.temporal.adapter import TemporalContractError, adapt_v2
from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS, TEMPORAL_SCHEMA_ID

REPOSITORY_ROOT = Path(__file__).parents[3]
GOLDEN_VECTORS = REPOSITORY_ROOT / "tests" / "fixtures" / "temporal" / "adapter-golden-vectors.json"
EXPECTED_VECTOR_IDS = {
    "origin",
    "year_end_category_maxima",
    "leap_day",
    "spring_before",
    "spring_after",
    "fall_edt",
    "fall_est",
    "malformed_timestamp",
    "nonexistent_local_time",
    "wrong_ambiguous_offset",
    "cross_field_mismatch",
    "before_lower_bound",
    "last_accepted_hour",
    "exact_upper_bound",
}


def _digest(format_code: str, values: list[float]) -> str:
    return hashlib.sha256(struct.pack(f"<{len(values)}{format_code}", *values)).hexdigest()


def _load_vectors() -> dict[str, object]:
    return json.loads(GOLDEN_VECTORS.read_text(encoding="utf-8"))


def test_golden_vector_manifest_is_complete_and_frozen() -> None:
    manifest = _load_vectors()
    vectors = manifest["vectors"]

    assert manifest["schema_version"] == "mdcp.adapter-golden-vectors.v1"
    assert manifest["temporal_schema_id"] == TEMPORAL_SCHEMA_ID
    assert manifest["feature_columns"] == list(TEMPORAL_FEATURE_COLUMNS)
    assert manifest["float_contract"] == {
        "adapter_arithmetic": "float64",
        "boundary_cast": "float32_once",
        "digest_byte_order": "little",
    }
    assert {case["id"] for case in vectors} == EXPECTED_VECTOR_IDS


def test_golden_vectors_recompute_without_rewriting_fixture() -> None:
    manifest = _load_vectors()

    for case in manifest["vectors"]:
        request = BikeRequestV2.model_validate(case["payload"])
        if "expected_reason" in case:
            with pytest.raises(TemporalContractError) as caught:
                adapt_v2(request)
            assert caught.value.reason_code.value == case["expected_reason"]
            assert "expected_float64" not in case
            continue

        vector = adapt_v2(request)
        expected = case["expected_float64"]
        assert vector.names == TEMPORAL_FEATURE_COLUMNS
        assert list(vector.values) == expected
        assert _digest("d", expected) == case["float64_sha256"]
        assert _digest("f", expected) == case["float32_sha256"]


def test_accepted_vectors_cover_every_categorical_boundary() -> None:
    accepted = [
        case["payload"] for case in _load_vectors()["vectors"] if "expected_float64" in case
    ]
    expected_domains = {
        "season": {1, 4},
        "mnth": {1, 12},
        "hr": {0, 23},
        "holiday": {0, 1},
        "weekday": {0, 6},
        "workingday": {0, 1},
        "weathersit": {1, 4},
    }

    for name, boundaries in expected_domains.items():
        assert boundaries.issubset({payload[name] for payload in accepted})
