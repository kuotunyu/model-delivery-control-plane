from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.constants import (
    BOOTSTRAP_INDEX,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    MAX_FORMAL_FITS,
    SUBGROUP_NAMES,
    TEMPORAL_FEATURE_COLUMNS,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = REPOSITORY_ROOT / "configs" / "workload" / "temporal-development-v2.json"
SCHEMA_PATH = REPOSITORY_ROOT / "schemas" / "v2" / "temporal-development.schema.json"

TRIAL_IDS = [
    "CTRL-01",
    "REC-180-L4",
    "REC-180-L12",
    "REC-270-L4",
    "REC-270-L12",
    "REC-365-L4",
    "REC-365-L12",
    "STAT-A0.1",
    "STAT-A1",
    "STAT-A10",
    "STAT-A100",
    "STAT-A1000",
    "NL-E64-R0.03-D2",
    "NL-E64-R0.03-D3",
    "NL-E64-R0.07-D2",
    "NL-E64-R0.07-D3",
    "NL-E128-R0.03-D2",
    "NL-E128-R0.03-D3",
    "NL-E128-R0.07-D2",
    "NL-E128-R0.07-D3",
]


def _load_object(path: Path) -> dict[str, Any]:
    value = parse_json_bytes(path.read_bytes())
    assert isinstance(value, dict)
    return value


def _assert_schema_accepts(value: object, schema: dict[str, Any], location: str = "$") -> None:
    if "oneOf" in schema:
        accepted = 0
        for candidate in schema["oneOf"]:
            try:
                _assert_schema_accepts(value, candidate, location)
            except AssertionError:
                continue
            accepted += 1
        assert accepted == 1, location
        return

    if "enum" in schema:
        assert value in schema["enum"], location

    expected_type = schema.get("type")
    if expected_type == "object":
        assert isinstance(value, dict), location
        properties = schema["properties"]
        assert set(schema["required"]) == set(properties), location
        assert schema["additionalProperties"] is False, location
        assert set(value) == set(properties), location
        for key, child in properties.items():
            _assert_schema_accepts(value[key], child, f"{location}.{key}")
    elif expected_type == "array":
        assert isinstance(value, list), location
        assert len(value) >= schema.get("minItems", 0), location
        assert len(value) <= schema.get("maxItems", len(value)), location
        if schema.get("uniqueItems"):
            assert len({canonicalize_json(item) for item in value}) == len(value), location
        for index, item in enumerate(value):
            _assert_schema_accepts(item, schema["items"], f"{location}[{index}]")
    elif expected_type == "string":
        assert isinstance(value, str), location
    elif expected_type == "integer":
        assert isinstance(value, int) and not isinstance(value, bool), location
    elif expected_type == "number":
        assert isinstance(value, int | float) and not isinstance(value, bool), location
    elif expected_type == "boolean":
        assert isinstance(value, bool), location
    elif expected_type == "null":
        assert value is None, location

    if isinstance(value, int | float) and not isinstance(value, bool):
        assert value >= schema.get("minimum", value), location
        assert value <= schema.get("maximum", value), location
    if "const" in schema:
        assert value == schema["const"], location


def _assert_all_object_schemas_are_closed(value: object) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False
            assert set(value["required"]) == set(value["properties"])
        for child in value.values():
            _assert_all_object_schemas_are_closed(child)
    elif isinstance(value, list):
        for child in value:
            _assert_all_object_schemas_are_closed(child)


def test_protocol_has_exact_inventory() -> None:
    protocol = _load_object(PROTOCOL_PATH)

    assert protocol["schema_version"] == "mdcp.temporal-development.v0.2"
    assert [fold["id"] for fold in protocol["folds"]] == ["F1", "F2", "F3", "F4"]
    assert protocol["trial_ids"] == TRIAL_IDS
    assert len(set(protocol["trial_ids"])) == 20
    assert sum(family["eligible_count"] for family in protocol["families"]) == 19
    assert protocol["execution"] == {
        "seed": 2026,
        "estimator_threads": 1,
        "selection_fits": 80,
        "replay_fits": 4,
        "final_fits": 1,
        "maximum_fits": 85,
        "peak_resident_memory_bytes": 4_294_967_296,
        "wall_clock_seconds": 21_600,
    }
    assert protocol["execution"]["maximum_fits"] == MAX_FORMAL_FITS


def test_protocol_freezes_folds_features_families_and_quality() -> None:
    protocol = _load_object(PROTOCOL_PATH)

    assert protocol["folds"] == [
        {
            "id": "F1",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2011-07-01T00:00:00",
            "validation_start": "2011-07-01T00:00:00",
            "validation_end": "2011-10-01T00:00:00",
        },
        {
            "id": "F2",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2011-10-01T00:00:00",
            "validation_start": "2011-10-01T00:00:00",
            "validation_end": "2012-01-01T00:00:00",
        },
        {
            "id": "F3",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2012-01-01T00:00:00",
            "validation_start": "2012-01-01T00:00:00",
            "validation_end": "2012-04-01T00:00:00",
        },
        {
            "id": "F4",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2012-04-01T00:00:00",
            "validation_start": "2012-04-01T00:00:00",
            "validation_end": "2012-07-01T00:00:00",
        },
    ]
    assert protocol["model_feature_schema"] == list(TEMPORAL_FEATURE_COLUMNS)
    assert [(family["family_id"], family["trial_count"]) for family in protocol["families"]] == [
        ("CTRL", 1),
        ("REC", 6),
        ("STAT", 5),
        ("NL", 8),
    ]
    assert protocol["families"][0]["parameters"] == {
        "bootstrap": [True],
        "max_depth": [8],
        "max_features": [1.0],
        "min_samples_leaf": [4],
        "n_estimators": [32],
        "n_jobs": [1],
        "random_state": [2026],
    }
    assert protocol["families"][1]["recency_days"] == [180, 270, 365]
    assert protocol["families"][1]["parameters"]["min_samples_leaf"] == [4, 12]
    assert protocol["families"][2]["parameters"]["alpha"] == [0.1, 1, 10, 100, 1000]
    assert protocol["families"][2]["preprocessing"] == {
        "categorical_positions": [1, 2, 3, 4, 5, 6, 7],
        "fixed_categorical_domains": [
            [1, 2, 3, 4],
            list(range(1, 13)),
            list(range(24)),
            [0, 1],
            list(range(7)),
            [0, 1],
            [1, 2, 3, 4],
        ],
        "standardization_ddof": 0,
        "standardized_positions": list(range(8, 19)),
        "zero_variance_policy": "invalid",
    }
    assert protocol["families"][3]["parameters"] == {
        "learning_rate": [0.03, 0.07],
        "loss": ["squared_error"],
        "max_depth": [2, 3],
        "max_features": [None],
        "min_samples_leaf": [8],
        "n_estimators": [64, 128],
        "random_state": [2026],
        "subsample": [1.0],
    }
    quality = protocol["quality"]
    assert quality["overall_max_ratio"] == 0.97
    assert quality["subgroup_max_ratio"] == 1.05
    assert quality["subgroup_names"] == list(SUBGROUP_NAMES)
    assert quality["min_subgroup_rows"] == 100
    assert quality["bootstrap"] == {
        "cluster": "calendar_day",
        "index": BOOTSTRAP_INDEX,
        "paired": True,
        "resamples": BOOTSTRAP_RESAMPLES,
        "rng": "PCG64",
        "seed": BOOTSTRAP_SEED,
    }
    assert quality["completeness"] == {
        "adapter": 1.0,
        "candidate_prediction": 1.0,
        "development_label": 1.0,
        "stable_prediction": 1.0,
    }
    assert quality["cross_fold"] == {
        "fold_overall_max_ratio": 1.05,
        "minimum_folds_at_or_below_one": 3,
    }


def test_checked_in_schema_accepts_protocol_and_is_recursively_closed() -> None:
    protocol = _load_object(PROTOCOL_PATH)
    schema = _load_object(SCHEMA_PATH)

    _assert_schema_accepts(protocol, schema)
    _assert_all_object_schemas_are_closed(schema)

    tampered = deepcopy(protocol)
    tampered["quality"]["bootstrap"]["resamples"] = 2100
    with pytest.raises(AssertionError, match=r"\$\.quality\.bootstrap\.resamples"):
        _assert_schema_accepts(tampered, schema)

    extra = deepcopy(protocol)
    extra["families"][0]["parameters"]["unapproved"] = [1]
    with pytest.raises(AssertionError, match=r"\$\.families\[0\]\.parameters"):
        _assert_schema_accepts(extra, schema)


@pytest.mark.parametrize(
    "mutation",
    [
        "feature_order",
        "fold_boundary",
        "family_model_kind",
        "family_parameters",
        "family_preprocessing",
        "family_eligibility",
        "family_feature_set",
        "trial_order",
    ],
)
def test_schema_rejects_semantically_reassigned_protocol_content(mutation: str) -> None:
    protocol = _load_object(PROTOCOL_PATH)
    schema = _load_object(SCHEMA_PATH)
    tampered = deepcopy(protocol)

    if mutation == "feature_order":
        tampered["model_feature_schema"][0:2] = reversed(tampered["model_feature_schema"][0:2])
    elif mutation == "fold_boundary":
        tampered["folds"][0]["train_end"] = "2011-10-01T00:00:00"
    elif mutation == "family_model_kind":
        tampered["families"][0]["model_kind"] = "ridge_regressor"
    elif mutation == "family_parameters":
        tampered["families"][0]["parameters"] = tampered["families"][1]["parameters"]
    elif mutation == "family_preprocessing":
        tampered["families"][0]["preprocessing"] = tampered["families"][2]["preprocessing"]
    elif mutation == "family_eligibility":
        tampered["families"][0]["eligible_count"] = 1
    elif mutation == "family_feature_set":
        tampered["families"][0]["feature_positions"] = tampered["families"][1]["feature_positions"]
    elif mutation == "trial_order":
        tampered["trial_ids"][1:3] = reversed(tampered["trial_ids"][1:3])
    else:  # pragma: no cover - the parametrization is the closed mutation inventory
        raise AssertionError("unknown semantic mutation")

    with pytest.raises(AssertionError):
        _assert_schema_accepts(tampered, schema)


def test_protocol_canonical_digest_is_stable() -> None:
    protocol = _load_object(PROTOCOL_PATH)
    first = canonicalize_json(protocol)
    second = canonicalize_json(parse_json_bytes(first))

    assert first == second
    assert len(sha256_hex(first)) == 64
