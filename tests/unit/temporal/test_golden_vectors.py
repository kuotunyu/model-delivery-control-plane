from __future__ import annotations

import copy
import hashlib
import json
import struct
from pathlib import Path

import pytest

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.contracts.workload_v2 import BikeRequestV2
from mdcp.temporal.adapter import adapt_v2
from mdcp.temporal.golden_vectors import (
    GOLDEN_CASE_IDS,
    GoldenVectorManifestError,
    verify_golden_vector_manifest,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
GOLDEN_VECTORS = REPOSITORY_ROOT / "tests/fixtures/temporal/adapter-golden-vectors.json"
APPROVED_MANIFEST_SHA256 = "ddeb4c7d52223589828b927ce744f53c5ca6981ce303b853230976fb88dc9eae"
EXPECTED_CASE_IDS = (
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


def _load_manifest() -> dict[str, object]:
    return json.loads(GOLDEN_VECTORS.read_text(encoding="utf-8"))


def _write_manifest(tmp_path: Path, manifest: dict[str, object]) -> Path:
    path = tmp_path / "mutated-golden-vectors.json"
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_manifest_is_exact_ordered_inventory() -> None:
    result = verify_golden_vector_manifest(GOLDEN_VECTORS)

    assert GOLDEN_CASE_IDS == EXPECTED_CASE_IDS
    assert result.verdict == "PASS"
    assert result.case_ids == EXPECTED_CASE_IDS
    assert result.case_count == 14
    assert len(result.case_inventory_sha256) == 64
    assert result.manifest_sha256 == APPROVED_MANIFEST_SHA256


def test_coordinated_manifest_rewrite_cannot_replace_approved_identity(
    tmp_path: Path,
) -> None:
    manifest = copy.deepcopy(_load_manifest())
    vectors = manifest["vectors"]
    assert isinstance(vectors, list)
    case = vectors[0]
    case["payload"]["temp"] = 0.25

    request = BikeRequestV2.model_validate(case["payload"])
    expected_float64 = list(adapt_v2(request).values)
    case["expected_float64"] = expected_float64
    case["float64_sha256"] = hashlib.sha256(
        struct.pack(f"<{len(expected_float64)}d", *expected_float64)
    ).hexdigest()
    case["float32_sha256"] = hashlib.sha256(
        struct.pack(f"<{len(expected_float64)}f", *expected_float64)
    ).hexdigest()
    case["case_sha256"] = sha256_hex(
        canonicalize_json({key: value for key, value in case.items() if key != "case_sha256"})
    )
    manifest["case_inventory"] = [
        {"id": vector["id"], "case_sha256": vector["case_sha256"]} for vector in vectors
    ]
    manifest["case_inventory_sha256"] = sha256_hex(canonicalize_json(manifest["case_inventory"]))

    with pytest.raises(
        GoldenVectorManifestError,
        match="^GOLDEN_VECTOR_MANIFEST_INVALID$",
    ):
        verify_golden_vector_manifest(_write_manifest(tmp_path, manifest))


@pytest.mark.parametrize(
    "mutation",
    (
        "missing",
        "extra",
        "duplicate",
        "renamed",
        "reordered",
        "payload",
        "expected_reason",
        "float64",
        "float32_digest",
        "case_sha256",
        "aggregate_digest",
    ),
)
def test_manifest_mutations_fail_closed(
    tmp_path: Path,
    mutation: str,
) -> None:
    manifest = copy.deepcopy(_load_manifest())
    vectors = manifest["vectors"]
    assert isinstance(vectors, list)

    if mutation == "missing":
        vectors.pop()
    elif mutation == "extra":
        extra = copy.deepcopy(vectors[-1])
        extra["id"] = "unexpected_case"
        vectors.append(extra)
    elif mutation == "duplicate":
        vectors[1]["id"] = vectors[0]["id"]
    elif mutation == "renamed":
        vectors[0]["id"] = "renamed_origin"
    elif mutation == "reordered":
        vectors[0], vectors[1] = vectors[1], vectors[0]
    elif mutation == "payload":
        vectors[0]["payload"]["temp"] = 0.25
    elif mutation == "expected_reason":
        vectors[7]["expected_reason"] = "TEMPORAL_FIELD_MISMATCH"
    elif mutation == "float64":
        vectors[0]["expected_float64"][0] = 2.0
    elif mutation == "float32_digest":
        vectors[0]["float32_sha256"] = "0" * 64
    elif mutation == "case_sha256":
        vectors[0]["case_sha256"] = "0" * 64
    elif mutation == "aggregate_digest":
        manifest["case_inventory_sha256"] = "0" * 64

    with pytest.raises(
        GoldenVectorManifestError,
        match="^GOLDEN_VECTOR_MANIFEST_INVALID$",
    ):
        verify_golden_vector_manifest(_write_manifest(tmp_path, manifest))


def test_case_shapes_are_closed_by_outcome() -> None:
    manifest = _load_manifest()
    vectors = manifest["vectors"]
    assert isinstance(vectors, list)

    for case in vectors:
        if "expected_reason" in case:
            assert set(case) == {"id", "payload", "expected_reason", "case_sha256"}
        else:
            assert set(case) == {
                "id",
                "payload",
                "expected_float64",
                "float64_sha256",
                "float32_sha256",
                "case_sha256",
            }


def test_accepted_vectors_cover_every_categorical_boundary() -> None:
    accepted = [
        case["payload"] for case in _load_manifest()["vectors"] if "expected_float64" in case
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
