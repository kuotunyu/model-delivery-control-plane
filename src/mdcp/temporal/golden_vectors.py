from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.contracts.workload_v2 import BikeRequestV2
from mdcp.temporal.adapter import TemporalContractError, adapt_v2
from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS, TEMPORAL_SCHEMA_ID

GOLDEN_CASE_IDS = (
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
)
APPROVED_GOLDEN_MANIFEST_SHA256 = "ddeb4c7d52223589828b927ce744f53c5ca6981ce303b853230976fb88dc9eae"

_MANIFEST_KEYS = {
    "schema_version",
    "temporal_schema_id",
    "feature_columns",
    "float_contract",
    "vectors",
    "case_inventory",
    "case_inventory_sha256",
}
_ACCEPTED_CASE_KEYS = {
    "id",
    "payload",
    "expected_float64",
    "float64_sha256",
    "float32_sha256",
    "case_sha256",
}
_REJECTED_CASE_KEYS = {"id", "payload", "expected_reason", "case_sha256"}
_FLOAT_CONTRACT = {
    "adapter_arithmetic": "float64",
    "boundary_cast": "float32_once",
    "digest_byte_order": "little",
}
_FAILURE_REASON = "GOLDEN_VECTOR_MANIFEST_INVALID"


class GoldenVectorManifestError(ValueError):
    def __init__(self) -> None:
        self.reason_code = _FAILURE_REASON
        super().__init__(_FAILURE_REASON)


@dataclass(frozen=True)
class GoldenInventoryResult:
    schema_version: Literal["mdcp.golden-vector-inventory.v1"]
    verdict: Literal["PASS"]
    case_ids: tuple[str, ...]
    case_count: Literal[14]
    case_inventory_sha256: str
    manifest_sha256: str


def _fail() -> None:
    raise GoldenVectorManifestError()


def _float_digest(format_code: str, values: list[float]) -> str:
    try:
        payload = struct.pack(f"<{len(values)}{format_code}", *values)
    except (OverflowError, struct.error):
        _fail()
    return hashlib.sha256(payload).hexdigest()


def _case_body(case: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in case.items() if key != "case_sha256"}


def _verify_case(case: object, expected_id: str) -> dict[str, str]:
    if not isinstance(case, dict) or case.get("id") != expected_id:
        _fail()
    is_rejected = "expected_reason" in case
    expected_keys = _REJECTED_CASE_KEYS if is_rejected else _ACCEPTED_CASE_KEYS
    if set(case) != expected_keys:
        _fail()

    payload = case.get("payload")
    if not isinstance(payload, dict):
        _fail()
    try:
        request = BikeRequestV2.model_validate(payload)
    except ValidationError:
        _fail()

    if is_rejected:
        try:
            adapt_v2(request)
        except TemporalContractError as error:
            if error.reason_code.value != case.get("expected_reason"):
                _fail()
        else:
            _fail()
    else:
        expected = case.get("expected_float64")
        if (
            not isinstance(expected, list)
            or len(expected) != len(TEMPORAL_FEATURE_COLUMNS)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(float(value))
                for value in expected
            )
        ):
            _fail()
        expected_values = [float(value) for value in expected]
        try:
            actual = adapt_v2(request)
        except TemporalContractError:
            _fail()
        if actual.names != TEMPORAL_FEATURE_COLUMNS or list(actual.values) != expected_values:
            _fail()
        if _float_digest("d", expected_values) != case.get("float64_sha256"):
            _fail()
        if _float_digest("f", expected_values) != case.get("float32_sha256"):
            _fail()

    calculated_case_sha256 = sha256_hex(canonicalize_json(_case_body(case)))
    if case.get("case_sha256") != calculated_case_sha256:
        _fail()
    return {"id": expected_id, "case_sha256": calculated_case_sha256}


def _verify_manifest(raw: bytes) -> GoldenInventoryResult:
    manifest = parse_json_bytes(raw)
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        _fail()
    if (
        manifest.get("schema_version") != "mdcp.adapter-golden-vectors.v1"
        or manifest.get("temporal_schema_id") != TEMPORAL_SCHEMA_ID
        or manifest.get("feature_columns") != list(TEMPORAL_FEATURE_COLUMNS)
        or manifest.get("float_contract") != _FLOAT_CONTRACT
    ):
        _fail()

    vectors = manifest.get("vectors")
    if not isinstance(vectors, list) or len(vectors) != len(GOLDEN_CASE_IDS):
        _fail()
    inventory = [
        _verify_case(case, expected_id)
        for case, expected_id in zip(vectors, GOLDEN_CASE_IDS, strict=True)
    ]
    if manifest.get("case_inventory") != inventory:
        _fail()
    inventory_sha256 = sha256_hex(canonicalize_json(inventory))
    if manifest.get("case_inventory_sha256") != inventory_sha256:
        _fail()

    return GoldenInventoryResult(
        schema_version="mdcp.golden-vector-inventory.v1",
        verdict="PASS",
        case_ids=GOLDEN_CASE_IDS,
        case_count=14,
        case_inventory_sha256=inventory_sha256,
        manifest_sha256=sha256_hex(raw),
    )


def verify_golden_vector_manifest(path: Path) -> GoldenInventoryResult:
    try:
        raw = path.read_bytes()
        if sha256_hex(raw) != APPROVED_GOLDEN_MANIFEST_SHA256:
            _fail()
        return _verify_manifest(raw)
    except GoldenVectorManifestError:
        raise
    except Exception as error:
        raise GoldenVectorManifestError() from error
