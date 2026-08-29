from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

from mdcp.common.canonical import canonicalize_json

REPOSITORY_ROOT = Path(__file__).parents[3]
ZERO = "0" * 64
FREEZE = "1" * 40
REQUEST_FIELDS = (
    "schema_version",
    "canonicalization_version",
    "expected_freeze_head",
    "repository_root",
    "search_receipt_path",
    "evidence_index_path",
    "authorization_path",
    "consumption_root",
    "archive_path",
    "private_container_path",
    "search_receipt_sha256",
    "evidence_index_sha256",
    "authorization_sha256",
    "source_inventory_sha256",
    "repository_inventory_sha256",
    "formal_worker_inventory_sha256",
    "launch_profile_sha256",
)
RESPONSE_FIELDS = (
    "schema_version",
    "canonicalization_version",
    "verdict",
    "reason_codes",
    "private_identity",
    "seal_record_sha256",
    "repository_inventory_sha256",
    "authorization_sha256",
    "consumption_marker_sha256",
    "fit_count",
    "h2_status",
    "h2_loaded_rows",
    "worker_request_sha256",
    "formal_worker_inventory_sha256",
    "launch_profile_sha256",
)


def _protocol() -> ModuleType:
    module_path = REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker_protocol.py"
    assert module_path.is_file(), "formal worker protocol module is absent"
    return importlib.import_module("mdcp.temporal.formal_worker_protocol")


def _request_document() -> dict[str, object]:
    return {
        "schema_version": "mdcp.formal-worker-request.v1",
        "canonicalization_version": "RFC8785",
        "expected_freeze_head": FREEZE,
        "repository_root": "C:/repository",
        "search_receipt_path": "C:/repository/evidence/public/v02/search/search-receipt.json",
        "evidence_index_path": "C:/repository/evidence/public/v02/search/evidence-index.json",
        "authorization_path": "C:/authorization.json",
        "consumption_root": "C:/consumption",
        "archive_path": "C:/archive.zip",
        "private_container_path": "C:/private/container.json",
        "search_receipt_sha256": "a" * 64,
        "evidence_index_sha256": "b" * 64,
        "authorization_sha256": "c" * 64,
        "source_inventory_sha256": "d" * 64,
        "repository_inventory_sha256": "e" * 64,
        "formal_worker_inventory_sha256": "f" * 64,
        "launch_profile_sha256": "2" * 64,
    }


def _response_document(
    *, verdict: str = "PASS", reasons: tuple[str, ...] = ()
) -> dict[str, object]:
    return {
        "schema_version": "mdcp.formal-worker-response.v1",
        "canonicalization_version": "RFC8785",
        "verdict": verdict,
        "reason_codes": reasons,
        "private_identity": {
            "file_count": 5,
            "total_bytes": 10,
            "inventory_sha256": "3" * 64,
            "manifest_sha256": "4" * 64,
        }
        if verdict == "PASS"
        else None,
        "seal_record_sha256": "5" * 64 if verdict == "PASS" else None,
        "repository_inventory_sha256": "e" * 64 if verdict == "PASS" else None,
        "authorization_sha256": "c" * 64 if verdict == "PASS" else ZERO,
        "consumption_marker_sha256": "6" * 64 if verdict == "PASS" else None,
        "fit_count": 84 if verdict == "PASS" else 0,
        "h2_status": "SEALED_NOT_LOADED",
        "h2_loaded_rows": 0,
        "worker_request_sha256": "7" * 64,
        "formal_worker_inventory_sha256": "f" * 64,
        "launch_profile_sha256": "2" * 64,
    }


def test_protocol_module_and_exact_schema_files_exist() -> None:
    assert (REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker_protocol.py").is_file()
    for relative_path in (
        "schemas/v2/formal-worker-request.schema.json",
        "schemas/v2/formal-worker-response.schema.json",
    ):
        assert (REPOSITORY_ROOT / relative_path).is_file()


def test_protocol_locks_fixed_transport_and_inventory_constants() -> None:
    protocol = _protocol()
    assert protocol.MAX_WORKER_MESSAGE_BYTES == 65_536
    assert protocol.WORKER_STDOUT_PROBE_BYTES == 65_537
    assert protocol.FORMAL_WORKER_TIMEOUT_SECONDS == 21_600
    assert protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS == 30
    assert protocol.FORMAL_WORKER_SOURCE_PATHS == (
        "schemas/v2/formal-worker-request.schema.json",
        "schemas/v2/formal-worker-response.schema.json",
        "src/mdcp/temporal/formal_worker.py",
        "src/mdcp/temporal/formal_worker_protocol.py",
    )
    assert protocol.FORMAL_WORKER_SOURCE_INVENTORY_SCHEMA_VERSION == (
        "mdcp.formal-worker-source-inventory.v1"
    )


def test_protocol_owns_the_exact_ascii_ordered_47_dedicated_worker_source_paths() -> None:
    protocol = _protocol()
    current_documents = {
        "docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-dedicated-formal-worker-corrective.md",
        "docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md",
    }
    obsolete_documents = {
        "docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-final-review-corrective.md",
        "docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md",
    }
    excluded_paths = {
        "evidence/public/v02/search/evidence-index.json",
        "evidence/public/v02/search/search-receipt.json",
        "tests/integration/temporal/test_formal_worker_process.py",
        "tests/unit/temporal/test_formal_worker_protocol.py",
    }

    assert len(protocol.SEARCH_SOURCE_PATHS) == 47
    assert len(set(protocol.SEARCH_SOURCE_PATHS)) == 47
    assert tuple(sorted(protocol.SEARCH_SOURCE_PATHS, key=str.encode)) == (
        protocol.SEARCH_SOURCE_PATHS
    )
    assert current_documents.issubset(protocol.SEARCH_SOURCE_PATHS)
    assert obsolete_documents.isdisjoint(protocol.SEARCH_SOURCE_PATHS)
    assert excluded_paths.isdisjoint(protocol.SEARCH_SOURCE_PATHS)
    assert all(
        protocol.SEARCH_SOURCE_PATHS.count(path) == 1
        for path in protocol.FORMAL_WORKER_SOURCE_PATHS
    )


def test_protocol_models_are_closed() -> None:
    protocol = _protocol()
    assert tuple(protocol.FormalWorkerRequest.model_fields) == REQUEST_FIELDS
    assert tuple(protocol.FormalWorkerResponse.model_fields) == RESPONSE_FIELDS
    assert tuple(protocol.FormalWorkerSourceEntry.model_fields) == ("logical_path", "sha256")
    for model in (
        protocol.FormalWorkerRequest,
        protocol.FormalWorkerResponse,
        protocol.FormalWorkerSourceEntry,
        protocol.FormalRunAuthorization,
        protocol.SearchReceipt,
        protocol.SearchSourceEntry,
        protocol.SearchEvidenceIndex,
    ):
        assert model.model_config["extra"] == "forbid"
        assert model.model_config["frozen"] is True


def _physical_schema(relative_path: str) -> dict[str, object]:
    return json.loads((REPOSITORY_ROOT / relative_path).read_text("utf-8"))


def _json_document(document: dict[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(document))


def _physical_schema_matches(schema: object, value: object, root: dict[str, object]) -> bool:
    assert isinstance(schema, dict)
    if "$ref" in schema:
        reference = schema["$ref"]
        assert isinstance(reference, str) and reference.startswith("#/")
        resolved: object = root
        for part in reference[2:].split("/"):
            assert isinstance(resolved, dict)
            resolved = resolved[part]
        return _physical_schema_matches(resolved, value, root)
    if "allOf" in schema and not all(
        _physical_schema_matches(item, value, root) for item in schema["allOf"]
    ):
        return False
    if "anyOf" in schema and not any(
        _physical_schema_matches(item, value, root) for item in schema["anyOf"]
    ):
        return False
    if (
        "oneOf" in schema
        and sum(_physical_schema_matches(item, value, root) for item in schema["oneOf"]) != 1
    ):
        return False
    if "not" in schema and _physical_schema_matches(schema["not"], value, root):
        return False
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    expected_type = schema.get("type")
    if expected_type == "object" or "properties" in schema:
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return False
        required = schema.get("required", [])
        if any(field not in value for field in required):
            return False
        if schema.get("additionalProperties") is False and any(
            field not in properties for field in value
        ):
            return False
        if any(
            field in value and not _physical_schema_matches(field_schema, value[field], root)
            for field, field_schema in properties.items()
        ):
            return False
    elif expected_type == "array":
        if not isinstance(value, list):
            return False
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get(
            "maxItems", len(value)
        ):
            return False
        if "items" in schema and any(
            not _physical_schema_matches(schema["items"], item, root) for item in value
        ):
            return False
    elif expected_type == "integer":
        if type(value) is not int:
            return False
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            return False
    elif expected_type == "string":
        if type(value) is not str:
            return False
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            return False
    elif expected_type == "null" and value is not None:
        return False
    return True


def _assert_physical_schema_accepts(relative_path: str, document: dict[str, object]) -> None:
    schema = _physical_schema(relative_path)
    assert _physical_schema_matches(schema, document, schema)


def _assert_physical_schema_rejects(relative_path: str, document: dict[str, object]) -> None:
    schema = _physical_schema(relative_path)
    assert not _physical_schema_matches(schema, document, schema)


def test_physical_schemas_declare_the_closed_protocol_constraints() -> None:
    request_schema = _physical_schema("schemas/v2/formal-worker-request.schema.json")
    request_defs = request_schema["$defs"]
    assert isinstance(request_defs, dict)
    assert request_defs["absolute_windows_path"]["pattern"]
    assert request_defs["git_commit"]["allOf"][1]["not"]["const"] == "0" * 40
    assert request_defs["sha256"]["allOf"][1]["not"]["const"] == ZERO

    response_schema = _physical_schema("schemas/v2/formal-worker-response.schema.json")
    response_defs = response_schema["$defs"]
    response_properties = response_schema["properties"]
    assert isinstance(response_defs, dict) and isinstance(response_properties, dict)
    assert response_defs["nonzero_sha256"]["allOf"][1]["not"]["const"] == ZERO
    assert response_defs["private_identity"]["properties"]["file_count"]["minimum"] == 0
    assert response_defs["private_identity"]["properties"]["total_bytes"]["minimum"] == 0
    assert set(response_properties["reason_codes"]["items"]["enum"]) == {
        "FORMAL_RUN_REQUEST_INVALID",
        "SEARCH_FREEZE_INVALID",
        "FORMAL_RUN_AUTHORIZATION_INVALID",
        "FORMAL_RUN_AUTHORIZATION_MISMATCH",
        "FORMAL_RUN_REPOSITORY_INVALID",
        "FORMAL_RUN_CONSUMPTION_ROOT_INVALID",
        "FORMAL_RUN_DESTINATION_INVALID",
        "FORMAL_RUN_AUTHORIZATION_CONSUMED",
        "FORMAL_RUN_CONSUMPTION_FAILED",
        "PUBLICATION_UNSUPPORTED",
        "FORMAL_RUN_CONSUMPTION_UNKNOWN",
        "FORMAL_RUN_EXECUTION_UNKNOWN",
        "FORMAL_RUN_SEAL_UNKNOWN",
    }
    assert response_properties["fit_count"] == {"type": "integer", "minimum": 0, "maximum": 84}
    assert len(response_schema["oneOf"]) == 6


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("repository_root", "repository"),
        ("search_receipt_path", "C:/repository/../receipt.json"),
        ("authorization_sha256", ZERO),
        ("expected_freeze_head", "0" * 40),
    ),
)
def test_request_physical_schema_rejects_noncanonical_paths_and_zero_identities(
    field: str, value: str
) -> None:
    document = _request_document()
    document[field] = value
    _assert_physical_schema_rejects(
        "schemas/v2/formal-worker-request.schema.json", _json_document(document)
    )


@pytest.mark.parametrize(
    "field",
    (
        "repository_root",
        "search_receipt_path",
        "evidence_index_path",
        "authorization_path",
        "consumption_root",
        "archive_path",
        "private_container_path",
    ),
)
@pytest.mark.parametrize("leading_segment", (".", ".."))
def test_request_physical_schema_rejects_drive_root_dot_segments(
    field: str, leading_segment: str
) -> None:
    document = _request_document()
    document[field] = f"C:/{leading_segment}/receipt.json"
    _assert_physical_schema_rejects(
        "schemas/v2/formal-worker-request.schema.json", _json_document(document)
    )


def test_request_physical_schema_accepts_the_closed_valid_document() -> None:
    _assert_physical_schema_accepts(
        "schemas/v2/formal-worker-request.schema.json", _json_document(_request_document())
    )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda document: document.update(reason_codes=["UNKNOWN_REASON"]),
        lambda document: document.update(fit_count=85),
        lambda document: document.update(
            private_identity={
                "file_count": -1,
                "total_bytes": 10,
                "inventory_sha256": "3" * 64,
                "manifest_sha256": "4" * 64,
            }
        ),
        lambda document: document.update(authorization_sha256=ZERO),
        lambda document: document.update(
            verdict="FAIL",
            reason_codes=["FORMAL_RUN_AUTHORIZATION_MISMATCH"],
            private_identity=None,
            seal_record_sha256=None,
            repository_inventory_sha256=None,
            consumption_marker_sha256=None,
            authorization_sha256="c" * 64,
            fit_count=1,
        ),
    ),
)
def test_response_physical_schema_rejects_adversarial_outcomes(mutation) -> None:
    document = _json_document(_response_document())
    mutation(document)
    _assert_physical_schema_rejects("schemas/v2/formal-worker-response.schema.json", document)


def test_response_physical_schema_accepts_exact_lifecycle_outcomes() -> None:
    for verdict, reason, authorization, marker, fit_count in _response_lifecycle_cases():
        document = _json_document(_response_document(verdict=verdict, reasons=(reason,)))
        document.update(
            authorization_sha256=authorization,
            consumption_marker_sha256=marker,
            fit_count=fit_count,
        )
        _assert_physical_schema_accepts("schemas/v2/formal-worker-response.schema.json", document)


def test_request_round_trip_is_canonical_and_has_no_self_hash() -> None:
    protocol = _protocol()
    raw = canonicalize_json(_request_document())
    parsed = protocol.parse_formal_worker_request(raw)
    assert parsed.model_dump(mode="json") == _request_document()
    assert protocol.encode_formal_worker_request(parsed) == raw
    assert protocol.worker_request_sha256(parsed) == protocol.sha256_hex(raw)
    assert "worker_request_sha256" not in type(parsed).model_fields


def test_response_round_trip_is_canonical_and_pass_has_no_reason() -> None:
    protocol = _protocol()
    raw = canonicalize_json(_response_document())
    parsed = protocol.parse_formal_worker_response(raw)
    assert parsed.reason_codes == ()
    assert protocol.encode_formal_worker_response(parsed) == raw


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("expected_freeze_head", "0" * 40),
        ("repository_root", "SENTINEL_RELATIVE_PATH"),
        ("search_receipt_path", "C:/repository/../receipt.json"),
        ("authorization_sha256", "A" * 64),
        ("repository_inventory_sha256", ZERO),
        ("launch_profile_sha256", ZERO),
    ),
)
def test_request_rejects_invalid_identity_or_noncanonical_path(field: str, value: str) -> None:
    protocol = _protocol()
    document = _request_document()
    document[field] = value
    with pytest.raises(ValueError) as caught:
        protocol.FormalWorkerRequest.model_validate(document)
    assert value not in str(caught.value)


@pytest.mark.parametrize(
    ("mutation", "raw"),
    (
        (
            "missing",
            lambda: canonicalize_json(
                {key: value for key, value in _request_document().items() if key != "archive_path"}
            ),
        ),
        (
            "callback",
            lambda: canonicalize_json(_request_document() | {"callback": "SENTINEL_CALLBACK"}),
        ),
        ("pickle", lambda: canonicalize_json(_request_document() | {"pickle": "SENTINEL_BASE64"})),
        ("code", lambda: canonicalize_json(_request_document() | {"code": "SENTINEL_CODE"})),
        ("module", lambda: canonicalize_json(_request_document() | {"module": "SENTINEL_MODULE"})),
        (
            "environment",
            lambda: canonicalize_json(_request_document() | {"environment": {"SENTINEL": "1"}}),
        ),
        ("opaque", lambda: canonicalize_json(_request_document() | {"opaque": {"nested": []}})),
        (
            "self-hash",
            lambda: canonicalize_json(_request_document() | {"worker_request_sha256": "9" * 64}),
        ),
        (
            "duplicate",
            lambda: (
                b'{"schema_version":"mdcp.formal-worker-request.v1",'
                b'"schema_version":"mdcp.formal-worker-request.v1"}'
            ),
        ),
        ("reordered", lambda: json.dumps(_request_document(), separators=(",", ":")).encode()),
        ("nonfinite", lambda: b'{"value":NaN}'),
        ("oversized", lambda: b" " * 65_537),
        ("bom", lambda: b"\xef\xbb\xbf" + canonicalize_json(_request_document())),
        ("newline", lambda: canonicalize_json(_request_document()) + b"\n"),
        ("trailing", lambda: canonicalize_json(_request_document()) + b" "),
        ("invalid-utf8", lambda: b"\xff"),
    ),
)
def test_request_parser_rejects_noncanonical_or_oversized_bytes(mutation: str, raw: object) -> None:
    protocol = _protocol()
    payload = raw()  # type: ignore[operator]
    with pytest.raises(ValueError) as caught:
        protocol.parse_formal_worker_request(payload)
    assert "SENTINEL" not in str(caught.value), mutation


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("fit_count", True),
        ("fit_count", 85),
        ("fit_count", -1),
        ("h2_loaded_rows", True),
        ("authorization_sha256", "C" * 64),
    ),
)
def test_response_rejects_bool_for_int_and_invalid_digest(field: str, value: object) -> None:
    protocol = _protocol()
    document = _response_document()
    document[field] = value
    with pytest.raises(ValueError) as caught:
        protocol.FormalWorkerResponse.model_validate(document)
    assert str(value) not in str(caught.value)


def _response_lifecycle_cases() -> tuple[tuple[str, str, str, str | None, int], ...]:
    return (
        ("FAIL", "FORMAL_RUN_REQUEST_INVALID", ZERO, None, 0),
        ("FAIL", "SEARCH_FREEZE_INVALID", ZERO, None, 0),
        ("FAIL", "FORMAL_RUN_AUTHORIZATION_INVALID", ZERO, None, 0),
        ("FAIL", "FORMAL_RUN_REPOSITORY_INVALID", ZERO, None, 0),
        ("FAIL", "PUBLICATION_UNSUPPORTED", ZERO, None, 0),
        ("FAIL", "FORMAL_RUN_AUTHORIZATION_MISMATCH", "c" * 64, None, 0),
        ("FAIL", "FORMAL_RUN_CONSUMPTION_ROOT_INVALID", "c" * 64, None, 0),
        ("FAIL", "FORMAL_RUN_DESTINATION_INVALID", "c" * 64, None, 0),
        ("FAIL", "FORMAL_RUN_AUTHORIZATION_CONSUMED", "c" * 64, None, 0),
        ("FAIL", "FORMAL_RUN_CONSUMPTION_FAILED", "c" * 64, None, 0),
        ("UNKNOWN", "FORMAL_RUN_CONSUMPTION_UNKNOWN", "c" * 64, None, 0),
        ("UNKNOWN", "FORMAL_RUN_EXECUTION_UNKNOWN", "c" * 64, "6" * 64, 40),
        ("UNKNOWN", "FORMAL_RUN_SEAL_UNKNOWN", "c" * 64, "6" * 64, 80),
    )


@pytest.mark.parametrize(
    ("verdict", "reason", "authorization", "marker", "fit_count"),
    _response_lifecycle_cases(),
)
def test_worker_response_reason_matrix_is_closed(
    verdict: str, reason: str, authorization: str, marker: str | None, fit_count: int
) -> None:
    protocol = _protocol()
    document = _response_document(verdict=verdict, reasons=(reason,))
    document.update(
        authorization_sha256=authorization,
        consumption_marker_sha256=marker,
        fit_count=fit_count,
    )
    response = protocol.FormalWorkerResponse.model_validate(document)
    assert (
        response.verdict,
        response.reason_codes,
        response.authorization_sha256,
        response.consumption_marker_sha256,
        response.fit_count,
    ) == (verdict, (reason,), authorization, marker, fit_count)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda document: document.update(fit_count=79),
        lambda document: document.update(authorization_sha256=ZERO),
        lambda document: document.update(consumption_marker_sha256=None),
    ),
)
def test_pass_response_requires_all_identities_and_completion_fit_count(mutation) -> None:
    protocol = _protocol()
    document = _response_document()
    mutation(document)
    with pytest.raises(ValueError):
        protocol.FormalWorkerResponse.model_validate(document)


@pytest.mark.parametrize(
    ("reason", "fit_count"),
    (
        ("FORMAL_RUN_EXECUTION_UNKNOWN", 40),
        ("FORMAL_RUN_SEAL_UNKNOWN", 80),
    ),
)
def test_unknown_execution_and_seal_reject_zero_consumption_marker(
    reason: str, fit_count: int
) -> None:
    protocol = _protocol()
    document = _response_document(verdict="UNKNOWN", reasons=(reason,))
    document.update(
        authorization_sha256="c" * 64,
        consumption_marker_sha256=ZERO,
        fit_count=fit_count,
    )
    with pytest.raises(ValueError):
        protocol.FormalWorkerResponse.model_validate(document)


@pytest.mark.parametrize(
    ("parser", "raw"),
    (
        ("parse_formal_worker_request", b"[" * 1200 + b"0" + b"]" * 1200),
        ("parse_formal_worker_response", b"[" * 1200 + b"0" + b"]" * 1200),
    ),
)
def test_worker_parsers_sanitize_bounded_deep_nesting(parser: str, raw: bytes) -> None:
    protocol = _protocol()
    assert len(raw) < protocol.MAX_WORKER_MESSAGE_BYTES
    with pytest.raises(ValueError, match="^FORMAL_WORKER_PROTOCOL_INVALID$"):
        getattr(protocol, parser)(raw)


@pytest.mark.parametrize(
    "reason",
    ("FORMAL_WORKER_LAUNCH_FAILED", "FORMAL_WORKER_PROCESS_UNKNOWN", "UNKNOWN_REASON"),
)
def test_worker_response_cannot_emit_supervisor_or_unknown_reason(reason: str) -> None:
    protocol = _protocol()
    with pytest.raises(ValueError) as caught:
        protocol.FormalWorkerResponse.model_validate(
            _response_document(verdict="FAIL", reasons=(reason,))
        )
    assert reason not in str(caught.value)


def test_worker_inventory_digest_has_exact_closed_shape() -> None:
    protocol = _protocol()
    entries = tuple(
        protocol.FormalWorkerSourceEntry(logical_path=path, sha256=str(index) * 64)
        for index, path in enumerate(protocol.FORMAL_WORKER_SOURCE_PATHS, start=1)
    )
    expected = protocol.sha256_hex(
        canonicalize_json(
            {
                "schema_version": "mdcp.formal-worker-source-inventory.v1",
                "entries": [entry.model_dump(mode="json") for entry in entries],
            }
        )
    )
    assert protocol.formal_worker_inventory_sha256(entries) == expected
    with pytest.raises(ValueError):
        protocol.FormalWorkerSourceEntry(
            logical_path=protocol.FORMAL_WORKER_SOURCE_PATHS[0], sha256=ZERO
        )


def test_launch_profile_digest_is_canonical_and_symbolic() -> None:
    protocol = _protocol()
    assert protocol.launch_profile_sha256() == protocol.sha256_hex(
        canonicalize_json(protocol.LAUNCH_PROFILE)
    )
    assert protocol.LAUNCH_PROFILE == {
        "platform": "windows",
        "executable": "ABSOLUTE_CURRENT_PYTHON_3_12_INTERPRETER",
        "target": "ABSOLUTE_VERIFIED_FORMAL_WORKER_SCRIPT",
        "arguments": ("-I", "-B", "-S", "ABSOLUTE_VERIFIED_FORMAL_WORKER_SCRIPT"),
        "shell": False,
        "cwd": "VERIFIED_REPOSITORY_ROOT",
        "close_fds": True,
        "stdin": "pipe",
        "stdout": "pipe",
        "stderr": "devnull",
        "environment_keys": ("SYSTEMROOT", "WINDIR"),
        "site_processing": False,
        "project_source_bootstrap": "SCRIPT_DERIVED_REPOSITORY_ROOT/src",
        "dependency_bootstrap": "INTERPRETER_DERIVED_LIB_SITE_PACKAGES_DIRECT_SYS_PATH_ONLY",
        "response_limit": 65_536,
        "wall_timeout": 21_600,
        "post_termination_wait": 30,
        "automatic_retry": False,
        "worker_launches_per_request": 1,
        "worker_child_processes": 0,
    }
