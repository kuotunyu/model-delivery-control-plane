from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import mdcp.temporal.contract_gate as contract_gate
from mdcp.common.canonical import canonicalize_json
from mdcp.contracts.serving_identity_v2 import V2_SERVING_PATHS
from mdcp.temporal.contract_gate import (
    CHECK_IDS,
    DevelopmentIdentity,
    TemporalContractGateError,
    TemporalContractReceipt,
    build_temporal_contract_receipt,
)
from mdcp.temporal.evidence import public_evidence_violations
from mdcp.temporal.firewall import run_development_boundary
from mdcp.temporal.golden_vectors import GOLDEN_CASE_IDS

REPOSITORY_ROOT = Path(__file__).parents[3]
RECEIPT_SCHEMA = REPOSITORY_ROOT / "schemas" / "v2" / "temporal-contract-receipt.schema.json"
REQUEST_SCHEMA = REPOSITORY_ROOT / "schemas" / "v2" / "bike-request.schema.json"
NATURAL_ARCHIVE_SHA256 = "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
NATURAL_ARCHIVE_SIZE = 279_992
NATURAL_DEVELOPMENT_IDENTITY = DevelopmentIdentity(
    archive_sha256=NATURAL_ARCHIVE_SHA256,
    development_row_count=13_003,
    development_rows_sha256=("b6d1bf9218354b112c2b74344283822fc83be678ff08f96f42199cb18076b3cc"),
    train_row_count=8_645,
    train_rows_sha256=("8ea404e03805f46b8ec66e6fc5a9fc25751837548c047e359e5b0212542469a5"),
    h1_row_count=4_358,
    h1_rows_sha256=("35a421a0eb8b3565523f6e3798f64b4b336e719771b4d1a167139803a0120b80"),
)
EXPECTED_CHECK_IDS = (
    "V1_SERVING_IDENTITY",
    "V2_REQUEST_SCHEMA",
    "V2_ENTRY_POINT",
    "V2_SERVING_INVENTORY",
    "ROUTING_TRUTH_TABLE",
    "DEVELOPMENT_BOUNDARY",
    "FEATURE_LINEAGE",
    "STATIC_H2_FIREWALL",
    "BEHAVIORAL_H2_FIREWALL",
    "GOLDEN_VECTOR_INVENTORY",
    "PUBLIC_EVIDENCE",
)
CHECKER_NAMES = (
    "_check_v1_serving_identity",
    "_check_v2_schemas",
    "_check_v2_entry_point",
    "_check_v2_serving_inventory",
    "_check_routing_truth_table",
    "_check_development_boundary",
    "_check_feature_lineage",
    "_check_static_h2_firewall",
    "_check_behavioral_h2_firewall",
    "_check_golden_vector_inventory",
    "_check_public_evidence",
)

_TESTS_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_TESTS_ROOT))
try:
    _archive_fixtures = importlib.import_module("temporal_archive_fixtures")
finally:
    sys.path.pop(0)

ArchiveFixture = _archive_fixtures.ArchiveFixture
build_synthetic_archive = _archive_fixtures.build_synthetic_archive
synthetic_archive = _archive_fixtures.synthetic_archive


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _identity_for_archive(archive: ArchiveFixture) -> DevelopmentIdentity:
    boundary = run_development_boundary(archive.path, archive.sha256)
    return DevelopmentIdentity(
        archive_sha256=boundary.archive_sha256,
        development_row_count=boundary.development_row_count,
        development_rows_sha256=boundary.development_rows_sha256,
        train_row_count=boundary.train_row_count,
        train_rows_sha256=boundary.train_rows_sha256,
        h1_row_count=boundary.h1_row_count,
        h1_rows_sha256=boundary.h1_rows_sha256,
    )


def _build_reviewer_receipt(archive: ArchiveFixture) -> TemporalContractReceipt:
    return build_temporal_contract_receipt(
        REPOSITORY_ROOT,
        reviewer_archive_path=archive.path,
        reviewer_archive_sha256=archive.sha256,
        reviewer_recipe_sha256=archive.recipe_sha256,
        development_archive_path=archive.path,
        development_archive_sha256=archive.sha256,
        expected_development_identity=_identity_for_archive(archive),
    )


def test_contract_receipt_binds_all_executed_wave_one_identities(
    synthetic_archive: ArchiveFixture,
) -> None:
    receipt = _build_reviewer_receipt(synthetic_archive)
    document = receipt.model_dump(mode="json")

    assert CHECK_IDS == EXPECTED_CHECK_IDS
    assert receipt.check_ids == EXPECTED_CHECK_IDS
    assert receipt.schema_version == "mdcp.temporal-contract-receipt.v1"
    assert receipt.verdict == "PASS"
    assert receipt.v1_serving_identity == (
        "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"
    )
    assert receipt.v1_entry_point == "mdcp.predictor.app:app"
    assert receipt.v2_entry_point == "mdcp.predictor.app_v2:app"
    assert tuple(entry.path for entry in receipt.v2_serving_inventory.entries) == (V2_SERVING_PATHS)
    assert receipt.v2_serving_inventory_sha256
    assert receipt.request_schema_sha256 == _sha256(REQUEST_SCHEMA)
    assert receipt.receipt_schema_sha256 == _sha256(RECEIPT_SCHEMA)
    assert receipt.temporal_schema_id == "mdcp.temporal-features.v0.2"
    assert receipt.feature_count == 18
    assert receipt.development_row_count == 13_003
    assert receipt.train_row_count == 8_645
    assert receipt.h1_row_count == 4_358
    assert receipt.behavioral_firewall.development_boundary.read_csv_nrows == (13_003,)
    assert receipt.behavioral_firewall.development_boundary.forbidden_call_counts == {
        "load_uci_archive": 0,
        "split_rows": 0,
        "DatasetPartitions.open_h2": 0,
    }
    assert receipt.behavioral_firewall.development_boundary.h2_loaded_rows == 0
    assert receipt.golden_case_ids == GOLDEN_CASE_IDS
    assert receipt.golden_case_count == 14
    assert receipt.h2_status == "SEALED_NOT_LOADED"
    assert receipt.h2_loaded_rows == 0
    assert public_evidence_violations(document) == ()


def test_receipt_assembly_is_repeatable_and_acyclic(
    synthetic_archive: ArchiveFixture,
) -> None:
    first = _build_reviewer_receipt(synthetic_archive)
    second = _build_reviewer_receipt(synthetic_archive)
    first_bytes = canonicalize_json(first.model_dump(mode="json"))
    second_bytes = canonicalize_json(second.model_dump(mode="json"))

    assert first_bytes == second_bytes
    serialized = first_bytes.decode("utf-8")
    assert "receipt_sha256" not in serialized
    assert "commit_sha" not in serialized
    assert "git_source_sha" not in serialized
    for forbidden in (
        str(synthetic_archive.path),
        "event_timestamp",
        "raw_rows",
        "exception",
        "environment",
        "sentinel",
        "credential",
    ):
        assert forbidden not in serialized


def test_checked_in_receipt_schema_matches_model_and_closes_inventory() -> None:
    checked_in = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))

    assert checked_in == TemporalContractReceipt.model_json_schema()
    assert checked_in["additionalProperties"] is False
    assert set(checked_in["required"]) == set(checked_in["properties"])
    inventory_schema = checked_in["properties"]["v2_serving_inventory"]
    entries_schema = inventory_schema["properties"]["entries"]
    assert entries_schema["minItems"] == 23
    assert entries_schema["maxItems"] == 23
    assert (
        tuple(item["properties"]["path"]["const"] for item in entries_schema["prefixItems"])
        == V2_SERVING_PATHS
    )

    behavioral_schema = checked_in["$defs"]["BehavioralFirewallBody"]
    boundary_schema = checked_in["$defs"]["DevelopmentBoundaryResult"]
    counter_schema = checked_in["$defs"]["ForbiddenCallCounts"]
    assert behavioral_schema["additionalProperties"] is False
    assert boundary_schema["additionalProperties"] is False
    assert counter_schema["additionalProperties"] is False
    assert set(counter_schema["properties"]) == {
        "load_uci_archive",
        "split_rows",
        "DatasetPartitions.open_h2",
    }
    assert set(counter_schema["required"]) == set(counter_schema["properties"])
    assert all(counter["const"] == 0 for counter in counter_schema["properties"].values())


@pytest.mark.parametrize(
    ("object_path", "extra_key"),
    (
        (("behavioral_firewall",), "unexpected_behavioral_field"),
        (
            ("behavioral_firewall", "development_boundary"),
            "unexpected_boundary_field",
        ),
    ),
)
def test_receipt_model_rejects_extra_behavioral_object_fields(
    synthetic_archive: ArchiveFixture,
    object_path: tuple[str, ...],
    extra_key: str,
) -> None:
    document = _build_reviewer_receipt(synthetic_archive).model_dump(mode="json")
    target = document
    for component in object_path:
        target = target[component]
    target[extra_key] = "not-allowed"

    with pytest.raises(ValidationError):
        TemporalContractReceipt.model_validate(document)


def test_receipt_model_rejects_unknown_forbidden_call_counter(
    synthetic_archive: ArchiveFixture,
) -> None:
    document = _build_reviewer_receipt(synthetic_archive).model_dump(mode="json")
    counters = document["behavioral_firewall"]["development_boundary"]["forbidden_call_counts"]
    counters["unknown_capability"] = 0

    with pytest.raises(ValidationError):
        TemporalContractReceipt.model_validate(document)


@pytest.mark.parametrize(
    "counter_name",
    ("load_uci_archive", "split_rows", "DatasetPartitions.open_h2"),
)
def test_receipt_model_rejects_nonzero_forbidden_call_counter(
    synthetic_archive: ArchiveFixture,
    counter_name: str,
) -> None:
    document = _build_reviewer_receipt(synthetic_archive).model_dump(mode="json")
    counters = document["behavioral_firewall"]["development_boundary"]["forbidden_call_counts"]
    counters[counter_name] = 1

    with pytest.raises(ValidationError):
        TemporalContractReceipt.model_validate(document)


@pytest.mark.parametrize(
    "digest_path",
    (
        ("behavioral_firewall", "fixture_recipe_sha256"),
        (
            "behavioral_firewall",
            "development_boundary",
            "archive_sha256",
        ),
        (
            "behavioral_firewall",
            "development_boundary",
            "development_rows_sha256",
        ),
        (
            "behavioral_firewall",
            "development_boundary",
            "train_rows_sha256",
        ),
        (
            "behavioral_firewall",
            "development_boundary",
            "h1_rows_sha256",
        ),
        ("behavioral_firewall", "static_firewall_implementation_sha256"),
        ("behavioral_firewall", "behavioral_firewall_implementation_sha256"),
        ("behavioral_firewall", "bounded_loader_implementation_sha256"),
        ("behavioral_firewall", "development_split_implementation_sha256"),
    ),
)
def test_receipt_model_rejects_invalid_nested_digest(
    synthetic_archive: ArchiveFixture,
    digest_path: tuple[str, ...],
) -> None:
    document = _build_reviewer_receipt(synthetic_archive).model_dump(mode="json")
    target = document
    for component in digest_path[:-1]:
        target = target[component]
    target[digest_path[-1]] = "A" * 64

    with pytest.raises(ValidationError):
        TemporalContractReceipt.model_validate(document)


@pytest.mark.parametrize(
    "mutation",
    ("missing", "extra", "duplicate", "reordered", "unknown"),
)
def test_receipt_model_rejects_inventory_mutations(
    synthetic_archive: ArchiveFixture,
    mutation: str,
) -> None:
    document = _build_reviewer_receipt(synthetic_archive).model_dump(mode="json")
    entries = document["v2_serving_inventory"]["entries"]
    if mutation == "missing":
        entries.pop()
    elif mutation == "extra":
        extra = copy.deepcopy(entries[-1])
        extra["path"] = "src/mdcp/extra.py"
        entries.append(extra)
    elif mutation == "duplicate":
        entries[-1] = copy.deepcopy(entries[0])
    elif mutation == "reordered":
        entries[0], entries[1] = entries[1], entries[0]
    else:
        entries[-1]["path"] = "src/mdcp/unknown.py"

    with pytest.raises(ValidationError):
        TemporalContractReceipt.model_validate(document)


def test_every_named_checker_executes_exactly_once(
    synthetic_archive: ArchiveFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_identity = _identity_for_archive(synthetic_archive)
    counts = {name: 0 for name in CHECKER_NAMES}
    for name in CHECKER_NAMES:
        original = getattr(contract_gate, name)

        def recording_checker(
            *args: object,
            __name: str = name,
            __original: Any = original,
            **kwargs: object,
        ) -> object:
            counts[__name] += 1
            return __original(*args, **kwargs)

        monkeypatch.setattr(contract_gate, name, recording_checker)

    receipt = build_temporal_contract_receipt(
        REPOSITORY_ROOT,
        reviewer_archive_path=synthetic_archive.path,
        reviewer_archive_sha256=synthetic_archive.sha256,
        reviewer_recipe_sha256=synthetic_archive.recipe_sha256,
        development_archive_path=synthetic_archive.path,
        development_archive_sha256=synthetic_archive.sha256,
        expected_development_identity=expected_identity,
    )

    assert receipt.verdict == "PASS"
    assert counts == {name: 1 for name in CHECKER_NAMES}


@pytest.mark.parametrize("checker_name", CHECKER_NAMES)
def test_any_checker_failure_prevents_pass(
    synthetic_archive: ArchiveFixture,
    monkeypatch: pytest.MonkeyPatch,
    checker_name: str,
) -> None:
    expected_identity = _identity_for_archive(synthetic_archive)

    def fail_checker(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(contract_gate, checker_name, fail_checker)
    with pytest.raises(
        TemporalContractGateError,
        match="^TEMPORAL_CONTRACT_GATE_FAILED$",
    ) as caught:
        build_temporal_contract_receipt(
            REPOSITORY_ROOT,
            reviewer_archive_path=synthetic_archive.path,
            reviewer_archive_sha256=synthetic_archive.sha256,
            reviewer_recipe_sha256=synthetic_archive.recipe_sha256,
            development_archive_path=synthetic_archive.path,
            development_archive_sha256=synthetic_archive.sha256,
            expected_development_identity=expected_identity,
        )
    assert "sensitive internal detail" not in str(caught.value)


def test_expected_development_identity_is_only_an_equality_assertion(
    synthetic_archive: ArchiveFixture,
) -> None:
    wrong = _identity_for_archive(synthetic_archive).model_copy(
        update={"development_rows_sha256": "0" * 64}
    )

    with pytest.raises(
        TemporalContractGateError,
        match="^TEMPORAL_CONTRACT_GATE_FAILED$",
    ):
        build_temporal_contract_receipt(
            REPOSITORY_ROOT,
            reviewer_archive_path=synthetic_archive.path,
            reviewer_archive_sha256=synthetic_archive.sha256,
            reviewer_recipe_sha256=synthetic_archive.recipe_sha256,
            development_archive_path=synthetic_archive.path,
            development_archive_sha256=synthetic_archive.sha256,
            expected_development_identity=wrong,
        )


def test_approved_development_prefix_receipt_recomputes(tmp_path: Path) -> None:
    if os.environ.get("MDCP_REQUIRE_NATURAL_GATE") != "1":
        pytest.skip("natural development-prefix gate requires explicit local authorization")
    archive_value = os.environ.get("MDCP_UCI_ARCHIVE")
    assert archive_value is not None
    development_archive = Path(archive_value)
    assert development_archive.stat().st_size == NATURAL_ARCHIVE_SIZE
    assert _sha256(development_archive) == NATURAL_ARCHIVE_SHA256
    reviewer_archive = build_synthetic_archive(tmp_path / "reviewer-synthetic.zip")

    receipt = build_temporal_contract_receipt(
        REPOSITORY_ROOT,
        reviewer_archive_path=reviewer_archive.path,
        reviewer_archive_sha256=reviewer_archive.sha256,
        reviewer_recipe_sha256=reviewer_archive.recipe_sha256,
        development_archive_path=development_archive,
        development_archive_sha256=NATURAL_ARCHIVE_SHA256,
        expected_development_identity=NATURAL_DEVELOPMENT_IDENTITY,
    )

    assert receipt.archive_sha256 == NATURAL_ARCHIVE_SHA256
    assert receipt.development_row_count == 13_003
    assert receipt.train_row_count == 8_645
    assert receipt.h1_row_count == 4_358
    assert receipt.h2_status == "SEALED_NOT_LOADED"
    assert receipt.h2_loaded_rows == 0
    assert public_evidence_violations(receipt.model_dump(mode="json")) == ()
