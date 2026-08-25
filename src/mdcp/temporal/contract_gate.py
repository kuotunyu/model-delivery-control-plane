from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.contracts.release import serving_inventory_digest, serving_inventory_from_root
from mdcp.contracts.serving_identity_v2 import (
    V2_SERVING_PATHS,
    V2ServingInventoryBody,
    V2ServingInventoryResult,
    build_v2_serving_inventory,
    verify_v2_serving_inventory,
)
from mdcp.contracts.workload_v2 import BikeRequestV2
from mdcp.predictor.app import create_app as create_v1_app
from mdcp.predictor.app_v2 import create_app as create_v2_app
from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS, TEMPORAL_SCHEMA_ID
from mdcp.temporal.evidence import public_evidence_violations
from mdcp.temporal.firewall import (
    BehavioralFirewallBody,
    BehavioralFirewallResult,
    DevelopmentBoundaryResult,
    audit_static_h2_firewall,
    run_behavioral_h2_firewall,
    run_development_boundary,
)
from mdcp.temporal.golden_vectors import (
    GoldenInventoryResult,
    verify_golden_vector_manifest,
)
from mdcp.temporal.routing import AdmissionKind, classify_envelope
from mdcp.workload.features import audit_temporal_feature_lineage

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

FROZEN_V1_SERVING_IDENTITY = "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"
CHECK_IDS = (
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

ExactCheckIds = tuple[
    Literal["V1_SERVING_IDENTITY"],
    Literal["V2_REQUEST_SCHEMA"],
    Literal["V2_ENTRY_POINT"],
    Literal["V2_SERVING_INVENTORY"],
    Literal["ROUTING_TRUTH_TABLE"],
    Literal["DEVELOPMENT_BOUNDARY"],
    Literal["FEATURE_LINEAGE"],
    Literal["STATIC_H2_FIREWALL"],
    Literal["BEHAVIORAL_H2_FIREWALL"],
    Literal["GOLDEN_VECTOR_INVENTORY"],
    Literal["PUBLIC_EVIDENCE"],
]
ExactGoldenCaseIds = tuple[
    Literal["origin"],
    Literal["year_end_category_maxima"],
    Literal["leap_day"],
    Literal["spring_before"],
    Literal["spring_after"],
    Literal["fall_edt"],
    Literal["fall_est"],
    Literal["malformed_timestamp"],
    Literal["nonexistent_local_time"],
    Literal["wrong_ambiguous_offset"],
    Literal["cross_field_mismatch"],
    Literal["before_lower_bound"],
    Literal["last_accepted_hour"],
    Literal["exact_upper_bound"],
]

_EXACT_V2_INVENTORY_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "schema_version": {
            "const": "mdcp.v2-serving-inventory.v1",
            "type": "string",
        },
        "entry_point": {
            "const": "mdcp.predictor.app_v2:app",
            "type": "string",
        },
        "entries": {
            "type": "array",
            "minItems": len(V2_SERVING_PATHS),
            "maxItems": len(V2_SERVING_PATHS),
            "prefixItems": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"const": path, "type": "string"},
                        "sha256": {
                            "pattern": "^[0-9a-f]{64}$",
                            "type": "string",
                        },
                    },
                    "required": ["path", "sha256"],
                }
                for path in V2_SERVING_PATHS
            ],
        },
    },
    "required": ["schema_version", "entry_point", "entries"],
}


class TemporalContractGateError(RuntimeError):
    def __init__(self) -> None:
        self.reason_code = "TEMPORAL_CONTRACT_GATE_FAILED"
        super().__init__(self.reason_code)


class _FeatureLineageColumns:
    columns = TEMPORAL_FEATURE_COLUMNS


class DevelopmentIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    archive_sha256: Sha256
    development_row_count: Literal[13_003]
    development_rows_sha256: Sha256
    train_row_count: Literal[8_645]
    train_rows_sha256: Sha256
    h1_row_count: Literal[4_358]
    h1_rows_sha256: Sha256


class TemporalContractReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.temporal-contract-receipt.v1"]
    verdict: Literal["PASS"]
    check_ids: ExactCheckIds
    v1_serving_identity: Literal["d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"]
    v1_entry_point: Literal["mdcp.predictor.app:app"]
    v2_entry_point: Literal["mdcp.predictor.app_v2:app"]
    v2_serving_inventory: V2ServingInventoryBody = Field(
        json_schema_extra=_EXACT_V2_INVENTORY_JSON_SCHEMA
    )
    v2_serving_inventory_sha256: Sha256
    request_schema_sha256: Sha256
    receipt_schema_sha256: Sha256
    temporal_schema_id: Literal["mdcp.temporal-features.v0.2"]
    feature_count: Literal[18]
    archive_sha256: Sha256
    development_row_count: Literal[13_003]
    development_rows_sha256: Sha256
    train_row_count: Literal[8_645]
    train_rows_sha256: Sha256
    h1_row_count: Literal[4_358]
    h1_rows_sha256: Sha256
    development_identity_sha256: Sha256
    routing_truth_table_sha256: Sha256
    feature_lineage_sha256: Sha256
    static_firewall_result_sha256: Sha256
    golden_case_ids: ExactGoldenCaseIds
    golden_case_count: Literal[14]
    golden_case_inventory_sha256: Sha256
    golden_manifest_sha256: Sha256
    behavioral_firewall: BehavioralFirewallBody
    behavioral_result_sha256: Sha256
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]


def _path_digest(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _checked_json(path: Path) -> object:
    return parse_json_bytes(path.read_bytes())


def _check_v1_serving_identity(repository_root: Path) -> str:
    identity = serving_inventory_digest(serving_inventory_from_root(repository_root))
    if identity != FROZEN_V1_SERVING_IDENTITY:
        raise TemporalContractGateError()
    return identity


def _check_v2_schemas(repository_root: Path) -> tuple[str, str]:
    request_schema_path = repository_root / "schemas/v2/bike-request.schema.json"
    receipt_schema_path = repository_root / "schemas/v2/temporal-contract-receipt.schema.json"
    if _checked_json(request_schema_path) != BikeRequestV2.model_json_schema():
        raise TemporalContractGateError()
    if _checked_json(receipt_schema_path) != TemporalContractReceipt.model_json_schema():
        raise TemporalContractGateError()
    return _path_digest(request_schema_path), _path_digest(receipt_schema_path)


def _check_v2_entry_point() -> tuple[str, str]:
    if (
        create_v1_app.__module__ != "mdcp.predictor.app"
        or create_v2_app.__module__ != "mdcp.predictor.app_v2"
        or create_v1_app is create_v2_app
    ):
        raise TemporalContractGateError()
    return "mdcp.predictor.app:app", "mdcp.predictor.app_v2:app"


def _check_v2_serving_inventory(repository_root: Path) -> V2ServingInventoryResult:
    result = build_v2_serving_inventory(repository_root, V2_SERVING_PATHS)
    return verify_v2_serving_inventory(repository_root, result)


def _check_routing_truth_table() -> str:
    legacy = {
        "request_id": "contract-route",
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
    v2 = {
        **legacy,
        "schema_version": "mdcp.bike-request.v2",
        "event_timestamp": "2011-01-01T00:00:00-05:00",
    }
    cases = (
        ("legacy", legacy),
        ("v2", v2),
        ("missing_timestamp", {**legacy, "schema_version": "mdcp.bike-request.v2"}),
        ("missing_schema", {**legacy, "event_timestamp": v2["event_timestamp"]}),
        (
            "invalid_timestamp",
            {
                **v2,
                "event_timestamp": "2011-03-13T02:00:00-05:00",
                "mnth": 3,
                "hr": 2,
                "weekday": 0,
            },
        ),
    )
    observed = [
        {
            "case_id": case_id,
            "kind": decision.kind.value,
            "reason_code": decision.reason_code,
        }
        for case_id, payload in cases
        for decision in (classify_envelope(payload),)
    ]
    expected = [
        {
            "case_id": "legacy",
            "kind": AdmissionKind.LEGACY_STABLE_ONLY.value,
            "reason_code": None,
        },
        {
            "case_id": "v2",
            "kind": AdmissionKind.V2_CANDIDATE_ELIGIBLE.value,
            "reason_code": None,
        },
        {
            "case_id": "missing_timestamp",
            "kind": AdmissionKind.INVALID_V2.value,
            "reason_code": "MISSING_EVENT_TIMESTAMP",
        },
        {
            "case_id": "missing_schema",
            "kind": AdmissionKind.INVALID_V2.value,
            "reason_code": "INVALID_V2_ENVELOPE",
        },
        {
            "case_id": "invalid_timestamp",
            "kind": AdmissionKind.INVALID_V2.value,
            "reason_code": "INVALID_EVENT_TIMESTAMP",
        },
    ]
    if observed != expected:
        raise TemporalContractGateError()
    return sha256_hex(canonicalize_json(observed))


def _identity_from_boundary(boundary: DevelopmentBoundaryResult) -> DevelopmentIdentity:
    return DevelopmentIdentity(
        archive_sha256=boundary.archive_sha256,
        development_row_count=boundary.development_row_count,
        development_rows_sha256=boundary.development_rows_sha256,
        train_row_count=boundary.train_row_count,
        train_rows_sha256=boundary.train_rows_sha256,
        h1_row_count=boundary.h1_row_count,
        h1_rows_sha256=boundary.h1_rows_sha256,
    )


def _check_development_boundary(
    archive_path: Path,
    archive_sha256: str,
    expected_identity: DevelopmentIdentity | Mapping[str, object],
) -> DevelopmentIdentity:
    expected = DevelopmentIdentity.model_validate(expected_identity)
    boundary = run_development_boundary(archive_path, archive_sha256)
    actual = _identity_from_boundary(boundary)
    if actual != expected:
        raise TemporalContractGateError()
    return actual


def _check_feature_lineage() -> str:
    lineage = audit_temporal_feature_lineage(_FeatureLineageColumns())
    if lineage.columns != TEMPORAL_FEATURE_COLUMNS:
        raise TemporalContractGateError()
    return lineage.lineage_sha256


def _check_static_h2_firewall(repository_root: Path) -> str:
    result = audit_static_h2_firewall(repository_root)
    document = {
        "schema_version": result.schema_version,
        "verdict": result.verdict,
        "checked_paths": list(result.checked_paths),
        "implementation_sha256": result.implementation_sha256,
    }
    return sha256_hex(canonicalize_json(document))


def _check_behavioral_h2_firewall(
    archive_path: Path,
    archive_sha256: str,
    recipe_sha256: str,
) -> BehavioralFirewallResult:
    return run_behavioral_h2_firewall(
        archive_path,
        archive_sha256,
        fixture_recipe_sha256=recipe_sha256,
    )


def _check_golden_vector_inventory(repository_root: Path) -> GoldenInventoryResult:
    return verify_golden_vector_manifest(
        repository_root / "tests/fixtures/temporal/adapter-golden-vectors.json"
    )


def _check_public_evidence(receipt: TemporalContractReceipt) -> None:
    if public_evidence_violations(receipt.model_dump(mode="json")):
        raise TemporalContractGateError()


def build_temporal_contract_receipt(
    repository_root: Path,
    *,
    reviewer_archive_path: Path,
    reviewer_archive_sha256: str,
    reviewer_recipe_sha256: str,
    development_archive_path: Path,
    development_archive_sha256: str,
    expected_development_identity: DevelopmentIdentity | Mapping[str, object],
) -> TemporalContractReceipt:
    try:
        v1_identity = _check_v1_serving_identity(repository_root)
        request_schema_sha256, receipt_schema_sha256 = _check_v2_schemas(repository_root)
        v1_entry_point, v2_entry_point = _check_v2_entry_point()
        v2_inventory = _check_v2_serving_inventory(repository_root)
        routing_truth_table_sha256 = _check_routing_truth_table()
        development_identity = _check_development_boundary(
            development_archive_path,
            development_archive_sha256,
            expected_development_identity,
        )
        feature_lineage_sha256 = _check_feature_lineage()
        static_firewall_result_sha256 = _check_static_h2_firewall(repository_root)
        behavioral_result = _check_behavioral_h2_firewall(
            reviewer_archive_path,
            reviewer_archive_sha256,
            reviewer_recipe_sha256,
        )
        golden_result = _check_golden_vector_inventory(repository_root)

        receipt = TemporalContractReceipt(
            schema_version="mdcp.temporal-contract-receipt.v1",
            verdict="PASS",
            check_ids=CHECK_IDS,
            v1_serving_identity=v1_identity,
            v1_entry_point=v1_entry_point,
            v2_entry_point=v2_entry_point,
            v2_serving_inventory=v2_inventory.body,
            v2_serving_inventory_sha256=v2_inventory.inventory_sha256,
            request_schema_sha256=request_schema_sha256,
            receipt_schema_sha256=receipt_schema_sha256,
            temporal_schema_id=TEMPORAL_SCHEMA_ID,
            feature_count=len(TEMPORAL_FEATURE_COLUMNS),
            archive_sha256=development_identity.archive_sha256,
            development_row_count=development_identity.development_row_count,
            development_rows_sha256=development_identity.development_rows_sha256,
            train_row_count=development_identity.train_row_count,
            train_rows_sha256=development_identity.train_rows_sha256,
            h1_row_count=development_identity.h1_row_count,
            h1_rows_sha256=development_identity.h1_rows_sha256,
            development_identity_sha256=sha256_hex(
                canonicalize_json(development_identity.model_dump(mode="json"))
            ),
            routing_truth_table_sha256=routing_truth_table_sha256,
            feature_lineage_sha256=feature_lineage_sha256,
            static_firewall_result_sha256=static_firewall_result_sha256,
            golden_case_ids=golden_result.case_ids,
            golden_case_count=golden_result.case_count,
            golden_case_inventory_sha256=golden_result.case_inventory_sha256,
            golden_manifest_sha256=golden_result.manifest_sha256,
            behavioral_firewall=behavioral_result.body,
            behavioral_result_sha256=behavioral_result.behavioral_result_sha256,
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
        )
        _check_public_evidence(receipt)
        return receipt
    except TemporalContractGateError:
        raise
    except Exception:
        raise TemporalContractGateError() from None
