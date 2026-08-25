from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from mdcp.common.canonical import canonicalize_json
from mdcp.temporal.search_identity import SearchIdentityInputs, SearchReceipt, build_search_receipt

REPOSITORY_ROOT = Path(__file__).parents[3]
RECEIPT_SCHEMA = REPOSITORY_ROOT / "schemas/v2/search-receipt.schema.json"


def _inputs(**updates: object) -> SearchIdentityInputs:
    material: dict[str, object] = {
        "search_source_commit": "a" * 40,
        "approved_spec_sha256": "1" * 64,
        "dependency_lock_sha256": "2" * 64,
        "dataset_contract_sha256": "3" * 64,
        "dataset_archive_sha256": "4" * 64,
        "development_rows_sha256": "5" * 64,
        "temporal_schema_sha256": "6" * 64,
        "temporal_adapter_sha256": "7" * 64,
        "golden_vector_sha256": "8" * 64,
        "fold_table_sha256": "9" * 64,
        "trial_table_sha256": "a" * 64,
        "ranking_rule_sha256": "b" * 64,
        "quality_policy_sha256": "c" * 64,
        "statistical_code_sha256": "d" * 64,
        "created_at_utc": datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
    }
    material.update(updates)
    return SearchIdentityInputs.model_validate(material)


def test_receipt_has_source_but_no_freeze_sha() -> None:
    fields = set(SearchReceipt.model_fields)

    assert "search_source_commit" in fields
    assert "search_freeze_commit" not in fields


def test_receipt_has_only_the_canonical_identity_and_limit_fields() -> None:
    receipt = build_search_receipt(_inputs())

    assert set(SearchReceipt.model_fields) == {
        "schema_version",
        "canonicalization_version",
        "search_source_commit",
        "approved_spec_sha256",
        "dependency_lock_sha256",
        "dataset_contract_sha256",
        "dataset_archive_sha256",
        "development_rows_sha256",
        "temporal_schema_sha256",
        "temporal_adapter_sha256",
        "golden_vector_sha256",
        "fold_table_sha256",
        "trial_table_sha256",
        "ranking_rule_sha256",
        "quality_policy_sha256",
        "statistical_code_sha256",
        "execution_seed",
        "estimator_threads",
        "selection_fit_limit",
        "replay_fit_limit",
        "final_fit_limit",
        "maximum_fit_limit",
        "h1_role",
        "h2_status",
        "h2_loaded_rows",
        "created_at_utc",
    }
    assert receipt.execution_seed == 2026
    assert receipt.estimator_threads == 1
    assert (
        receipt.selection_fit_limit,
        receipt.replay_fit_limit,
        receipt.final_fit_limit,
        receipt.maximum_fit_limit,
    ) == (80, 4, 1, 85)
    assert receipt.h1_role == "OBSERVED_DEVELOPMENT_ONLY"
    assert (receipt.h2_status, receipt.h2_loaded_rows) == ("SEALED_NOT_LOADED", 0)
    assert receipt.created_at_utc == datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def test_receipt_is_rfc8785_canonicalizable_without_private_paths() -> None:
    receipt = build_search_receipt(_inputs())
    serialized = canonicalize_json(receipt.model_dump(mode="json")).decode("utf-8")

    assert "search_freeze_commit" not in serialized
    assert "path" not in serialized
    assert "C:\\" not in serialized


def test_receipt_rejects_non_utc_creation_time() -> None:
    with pytest.raises(ValidationError):
        build_search_receipt(_inputs(created_at_utc=datetime(2026, 8, 25, 20, 0)))


def test_checked_in_receipt_schema_matches_the_closed_model() -> None:
    checked_in = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))

    assert checked_in == SearchReceipt.model_json_schema()
    assert checked_in["additionalProperties"] is False
    assert set(checked_in["required"]) == set(checked_in["properties"])
