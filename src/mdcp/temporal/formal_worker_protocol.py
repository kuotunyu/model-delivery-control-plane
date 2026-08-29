"""Closed, process-free byte protocol for the dedicated formal worker."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitCommit = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
AuthorizationId = Annotated[
    str,
    StringConstraints(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    ),
]

MAX_WORKER_MESSAGE_BYTES = 65_536
WORKER_STDOUT_PROBE_BYTES = 65_537
FORMAL_WORKER_TIMEOUT_SECONDS = 21_600
FORMAL_WORKER_TERMINATION_WAIT_SECONDS = 30
FORMAL_WORKER_SOURCE_INVENTORY_SCHEMA_VERSION = "mdcp.formal-worker-source-inventory.v1"
FORMAL_WORKER_SOURCE_PATHS = (
    "schemas/v2/formal-worker-request.schema.json",
    "schemas/v2/formal-worker-response.schema.json",
    "src/mdcp/temporal/formal_worker.py",
    "src/mdcp/temporal/formal_worker_protocol.py",
)
SEARCH_SOURCE_PATHS = (
    "configs/workload/temporal-development-v2.json",
    "configs/workload/uci-bike-sharing-v1.json",
    "docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md",
    "docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md",
    "docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-dedicated-formal-worker-corrective.md",
    "docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md",
    "docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md",
    "docs/superpowers/specs/2026-08-26-mdcp-v02-private-evidence-container-design.md",
    "docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md",
    "docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md",
    "pyproject.toml",
    "schemas/v2/bike-request.schema.json",
    "schemas/v2/development-result-index.schema.json",
    "schemas/v2/formal-run-authorization.schema.json",
    "schemas/v2/formal-worker-request.schema.json",
    "schemas/v2/formal-worker-response.schema.json",
    "schemas/v2/search-receipt.schema.json",
    "schemas/v2/temporal-contract-receipt.schema.json",
    "schemas/v2/temporal-development.schema.json",
    "src/mdcp/common/canonical.py",
    "src/mdcp/common/digests.py",
    "src/mdcp/common/enums.py",
    "src/mdcp/contracts/workload.py",
    "src/mdcp/contracts/workload_v2.py",
    "src/mdcp/policy/cluster_bootstrap.py",
    "src/mdcp/temporal/adapter.py",
    "src/mdcp/temporal/cli.py",
    "src/mdcp/temporal/completeness.py",
    "src/mdcp/temporal/constants.py",
    "src/mdcp/temporal/contract_gate.py",
    "src/mdcp/temporal/evaluation.py",
    "src/mdcp/temporal/evidence.py",
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/folds.py",
    "src/mdcp/temporal/formal_worker.py",
    "src/mdcp/temporal/formal_worker_protocol.py",
    "src/mdcp/temporal/golden_vectors.py",
    "src/mdcp/temporal/run_evidence.py",
    "src/mdcp/temporal/runner.py",
    "src/mdcp/temporal/runtime_guards.py",
    "src/mdcp/temporal/search_identity.py",
    "src/mdcp/temporal/selection.py",
    "src/mdcp/temporal/trials.py",
    "src/mdcp/workload/dataset.py",
    "src/mdcp/workload/splits.py",
    "tests/fixtures/temporal/adapter-golden-vectors.json",
    "uv.lock",
)
PRIVATE_LOGICAL_OUTPUTS = (
    "provisional-winner.json",
    "qualification-report.json",
    "ranking-report.json",
    "replay-report.json",
    "trial-summary.json",
)
PRE_CONSUMPTION_FAILURE_REASONS = frozenset(
    {
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
    }
)
POST_CONSUMPTION_UNKNOWN_REASONS = frozenset(
    {
        "FORMAL_RUN_CONSUMPTION_UNKNOWN",
        "FORMAL_RUN_EXECUTION_UNKNOWN",
        "FORMAL_RUN_SEAL_UNKNOWN",
    }
)
ZERO_AUTHORIZATION_FAILURE_REASONS = frozenset(
    {
        "FORMAL_RUN_REQUEST_INVALID",
        "SEARCH_FREEZE_INVALID",
        "FORMAL_RUN_AUTHORIZATION_INVALID",
        "FORMAL_RUN_REPOSITORY_INVALID",
        "PUBLICATION_UNSUPPORTED",
    }
)
IDENTIFIED_AUTHORIZATION_FAILURE_REASONS = (
    PRE_CONSUMPTION_FAILURE_REASONS - ZERO_AUTHORIZATION_FAILURE_REASONS
)
LAUNCH_PROFILE = {
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
    "response_limit": MAX_WORKER_MESSAGE_BYTES,
    "wall_timeout": FORMAL_WORKER_TIMEOUT_SECONDS,
    "post_termination_wait": FORMAL_WORKER_TERMINATION_WAIT_SECONDS,
    "automatic_retry": False,
    "worker_launches_per_request": 1,
    "worker_child_processes": 0,
}


def _invalid() -> ValueError:
    return ValueError("FORMAL_WORKER_PROTOCOL_INVALID")


def _require_string(value: object) -> str:
    if type(value) is not str:
        raise _invalid()
    return value


def _require_nonzero_digest(value: str) -> str:
    if value == "0" * 64:
        raise _invalid()
    return value


def _require_absolute_windows_path(value: object) -> str:
    value = _require_string(value)
    if (
        len(value) < 4
        or not ("A" <= value[0] <= "Z")
        or value[1:3] != ":/"
        or "\\" in value
        or any(part in ("", ".", "..") for part in value[3:].split("/"))
    ):
        raise _invalid()
    return value


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class SearchReceipt(_ClosedModel):
    """The canonical, public, deliberately acyclic search identity."""

    schema_version: Literal["mdcp.search-receipt.v1"]
    canonicalization_version: Literal["RFC8785"]
    search_source_commit: GitCommit
    approved_spec_sha256: Sha256
    dependency_lock_sha256: Sha256
    dataset_contract_sha256: Sha256
    dataset_archive_sha256: Sha256
    development_rows_sha256: Sha256
    temporal_schema_sha256: Sha256
    temporal_adapter_sha256: Sha256
    golden_vector_sha256: Sha256
    fold_table_sha256: Sha256
    trial_table_sha256: Sha256
    ranking_rule_sha256: Sha256
    quality_policy_sha256: Sha256
    statistical_code_sha256: Sha256
    execution_seed: Literal[2026]
    estimator_threads: Literal[1]
    selection_fit_limit: Literal[80]
    replay_fit_limit: Literal[4]
    final_fit_limit: Literal[1]
    maximum_fit_limit: Literal[85]
    h1_role: Literal["OBSERVED_DEVELOPMENT_ONLY"]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    created_at_utc: datetime

    @field_validator("created_at_utc")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at_utc must be UTC")
        return value


class FormalRunAuthorization(_ClosedModel):
    """One external owner authorization bound to one exact frozen search."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        json_schema_extra={
            "allOf": [
                {
                    "not": {
                        "properties": {field: {"const": zero}},
                        "required": [field],
                    }
                }
                for field, zero in (
                    ("search_freeze_commit", "0" * 40),
                    ("search_receipt_sha256", "0" * 64),
                    ("protocol_sha256", "0" * 64),
                )
            ]
        },
    )

    schema_version: Literal["mdcp.formal-run-authorization.v1"]
    canonicalization_version: Literal["RFC8785"]
    search_freeze_commit: GitCommit
    search_receipt_sha256: Sha256
    protocol_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]
    authorization_id: AuthorizationId
    authorized_action: Literal["ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN"]
    authorized_at_utc: datetime
    consumed: Literal[False]

    @field_validator(
        "schema_version",
        "canonicalization_version",
        "search_freeze_commit",
        "search_receipt_sha256",
        "protocol_sha256",
        "dataset_archive_sha256",
        "authorization_id",
        "authorized_action",
        "authorized_at_utc",
        mode="before",
    )
    @classmethod
    def _require_string_input(cls, value: object) -> object:
        if type(value) is not str:
            raise ValueError("FORMAL_RUN_AUTHORIZATION_INVALID")
        return value

    @field_validator("consumed", mode="before")
    @classmethod
    def _require_false_boolean(cls, value: object) -> object:
        if type(value) is not bool or value is not False:
            raise ValueError("FORMAL_RUN_AUTHORIZATION_INVALID")
        return value

    @field_validator("authorized_at_utc")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("FORMAL_RUN_AUTHORIZATION_INVALID")
        return value

    @model_validator(mode="after")
    def _reject_zero_identities(self) -> FormalRunAuthorization:
        if (
            self.search_freeze_commit == "0" * 40
            or self.search_receipt_sha256 == "0" * 64
            or self.protocol_sha256 == "0" * 64
        ):
            raise ValueError("FORMAL_RUN_AUTHORIZATION_INVALID")
        return self


class SearchSourceEntry(_ClosedModel):
    logical_path: str
    git_mode: Literal["100644"]
    byte_size: int
    sha256: Sha256

    @field_validator("logical_path", mode="before")
    @classmethod
    def _known_logical_path(cls, value: object) -> str:
        value = _require_string(value)
        if value not in SEARCH_SOURCE_PATHS:
            raise ValueError("SEARCH_SOURCE_PATH_INVALID")
        return value

    @field_validator("byte_size", mode="before")
    @classmethod
    def _nonnegative_size(cls, value: object) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("SEARCH_SOURCE_SIZE_INVALID")
        return value


def search_source_inventory_sha256(entries: tuple[SearchSourceEntry, ...]) -> str:
    return sha256_hex(canonicalize_json([entry.model_dump(mode="json") for entry in entries]))


class SearchEvidenceIndex(_ClosedModel):
    schema_version: Literal["mdcp.search-evidence-index.v1"]
    canonicalization_version: Literal["RFC8785"]
    source_entries: tuple[SearchSourceEntry, ...]
    source_inventory_sha256: Sha256
    private_logical_outputs: tuple[str, ...]
    search_receipt_sha256: Sha256
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]

    @model_validator(mode="after")
    def _closed_structure(self) -> SearchEvidenceIndex:
        if (
            tuple(item.logical_path for item in self.source_entries) != SEARCH_SOURCE_PATHS
            or self.private_logical_outputs != PRIVATE_LOGICAL_OUTPUTS
            or self.source_inventory_sha256 != search_source_inventory_sha256(self.source_entries)
        ):
            raise ValueError("SEARCH_SOURCE_INDEX_INVALID")
        return self


class FormalWorkerSourceEntry(_ClosedModel):
    logical_path: str
    sha256: Sha256

    @field_validator("logical_path", mode="before")
    @classmethod
    def _known_logical_path(cls, value: object) -> str:
        value = _require_string(value)
        if value not in FORMAL_WORKER_SOURCE_PATHS:
            raise _invalid()
        return value

    @field_validator("sha256")
    @classmethod
    def _nonzero_digest(cls, value: str) -> str:
        return _require_nonzero_digest(value)


def formal_worker_inventory_sha256(entries: tuple[FormalWorkerSourceEntry, ...]) -> str:
    if tuple(entry.logical_path for entry in entries) != FORMAL_WORKER_SOURCE_PATHS:
        raise _invalid()
    return sha256_hex(
        canonicalize_json(
            {
                "schema_version": FORMAL_WORKER_SOURCE_INVENTORY_SCHEMA_VERSION,
                "entries": [entry.model_dump(mode="json") for entry in entries],
            }
        )
    )


def launch_profile_sha256() -> str:
    return sha256_hex(canonicalize_json(LAUNCH_PROFILE))


class FormalWorkerRequest(_ClosedModel):
    schema_version: Literal["mdcp.formal-worker-request.v1"]
    canonicalization_version: Literal["RFC8785"]
    expected_freeze_head: GitCommit
    repository_root: str
    search_receipt_path: str
    evidence_index_path: str
    authorization_path: str
    consumption_root: str
    archive_path: str
    private_container_path: str
    search_receipt_sha256: Sha256
    evidence_index_sha256: Sha256
    authorization_sha256: Sha256
    source_inventory_sha256: Sha256
    repository_inventory_sha256: Sha256
    formal_worker_inventory_sha256: Sha256
    launch_profile_sha256: Sha256

    @field_validator(
        "schema_version",
        "canonicalization_version",
        "expected_freeze_head",
        "search_receipt_sha256",
        "evidence_index_sha256",
        "authorization_sha256",
        "source_inventory_sha256",
        "repository_inventory_sha256",
        "formal_worker_inventory_sha256",
        "launch_profile_sha256",
        mode="before",
    )
    @classmethod
    def _require_string_values(cls, value: object) -> str:
        return _require_string(value)

    @field_validator(
        "repository_root",
        "search_receipt_path",
        "evidence_index_path",
        "authorization_path",
        "consumption_root",
        "archive_path",
        "private_container_path",
        mode="before",
    )
    @classmethod
    def _require_paths(cls, value: object) -> str:
        return _require_absolute_windows_path(value)

    @model_validator(mode="after")
    def _require_nonzero_identities(self) -> FormalWorkerRequest:
        if self.expected_freeze_head == "0" * 40 or any(
            value == "0" * 64
            for value in (
                self.search_receipt_sha256,
                self.evidence_index_sha256,
                self.authorization_sha256,
                self.source_inventory_sha256,
                self.repository_inventory_sha256,
                self.formal_worker_inventory_sha256,
                self.launch_profile_sha256,
            )
        ):
            raise _invalid()
        return self


class FormalWorkerPrivateIdentity(_ClosedModel):
    file_count: int
    total_bytes: int
    inventory_sha256: Sha256
    manifest_sha256: Sha256

    @field_validator("file_count", "total_bytes", mode="before")
    @classmethod
    def _nonnegative_integer(cls, value: object) -> int:
        if type(value) is not int or value < 0:
            raise _invalid()
        return value

    @model_validator(mode="after")
    def _require_nonzero_digests(self) -> FormalWorkerPrivateIdentity:
        _require_nonzero_digest(self.inventory_sha256)
        _require_nonzero_digest(self.manifest_sha256)
        return self


class FormalWorkerResponse(_ClosedModel):
    schema_version: Literal["mdcp.formal-worker-response.v1"]
    canonicalization_version: Literal["RFC8785"]
    verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    private_identity: FormalWorkerPrivateIdentity | None
    seal_record_sha256: Sha256 | None
    repository_inventory_sha256: Sha256 | None
    authorization_sha256: Sha256
    consumption_marker_sha256: Sha256 | None
    fit_count: int
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    worker_request_sha256: Sha256
    formal_worker_inventory_sha256: Sha256
    launch_profile_sha256: Sha256

    @field_validator("reason_codes", mode="before")
    @classmethod
    def _require_reason_tuple(cls, value: object) -> object:
        if type(value) not in (tuple, list) or any(type(item) is not str for item in value):
            raise _invalid()
        return tuple(value)

    @field_validator("fit_count", "h2_loaded_rows", mode="before")
    @classmethod
    def _require_integer(cls, value: object) -> int:
        if type(value) is not int:
            raise _invalid()
        return value

    @field_validator(
        "schema_version",
        "canonicalization_version",
        "verdict",
        "authorization_sha256",
        "worker_request_sha256",
        "formal_worker_inventory_sha256",
        "launch_profile_sha256",
        mode="before",
    )
    @classmethod
    def _require_string_values(cls, value: object) -> str:
        return _require_string(value)

    @model_validator(mode="after")
    def _closed_outcome(self) -> FormalWorkerResponse:
        if not 0 <= self.fit_count <= 84:
            raise _invalid()
        if any(
            value == "0" * 64
            for value in (
                self.worker_request_sha256,
                self.formal_worker_inventory_sha256,
                self.launch_profile_sha256,
            )
        ):
            raise _invalid()
        if self.verdict == "PASS":
            if (
                self.reason_codes
                or self.fit_count not in (80, 84)
                or self.private_identity is None
                or self.seal_record_sha256 is None
                or self.repository_inventory_sha256 is None
                or self.consumption_marker_sha256 is None
                or self.authorization_sha256 == "0" * 64
                or self.seal_record_sha256 == "0" * 64
                or self.repository_inventory_sha256 == "0" * 64
                or self.consumption_marker_sha256 == "0" * 64
            ):
                raise _invalid()
            return self
        if (
            len(self.reason_codes) != 1
            or self.private_identity is not None
            or self.seal_record_sha256 is not None
            or self.repository_inventory_sha256 is not None
        ):
            raise _invalid()
        reason = self.reason_codes[0]
        if self.verdict == "FAIL":
            if (
                reason not in PRE_CONSUMPTION_FAILURE_REASONS
                or self.consumption_marker_sha256 is not None
                or self.fit_count != 0
            ):
                raise _invalid()
            if reason in ZERO_AUTHORIZATION_FAILURE_REASONS:
                if self.authorization_sha256 != "0" * 64:
                    raise _invalid()
            elif (
                reason not in IDENTIFIED_AUTHORIZATION_FAILURE_REASONS
                or self.authorization_sha256 == "0" * 64
            ):
                raise _invalid()
            return self
        if self.authorization_sha256 == "0" * 64:
            raise _invalid()
        if reason == "FORMAL_RUN_CONSUMPTION_UNKNOWN":
            if self.consumption_marker_sha256 is not None or self.fit_count != 0:
                raise _invalid()
            return self
        if reason == "FORMAL_RUN_EXECUTION_UNKNOWN":
            if self.consumption_marker_sha256 in (None, "0" * 64):
                raise _invalid()
            return self
        if reason == "FORMAL_RUN_SEAL_UNKNOWN":
            if self.consumption_marker_sha256 in (None, "0" * 64) or self.fit_count not in (80, 84):
                raise _invalid()
            return self
        raise _invalid()


def _parse_worker_message(
    raw: bytes, model: type[FormalWorkerRequest] | type[FormalWorkerResponse]
):
    if type(raw) is not bytes or len(raw) > MAX_WORKER_MESSAGE_BYTES:
        raise _invalid()
    try:
        value = model.model_validate(parse_json_bytes(raw))
        if canonicalize_json(value.model_dump(mode="json")) != raw:
            raise _invalid()
    except Exception:
        raise _invalid() from None
    return value


def parse_formal_worker_request(raw: bytes) -> FormalWorkerRequest:
    return _parse_worker_message(raw, FormalWorkerRequest)


def parse_formal_worker_response(raw: bytes) -> FormalWorkerResponse:
    return _parse_worker_message(raw, FormalWorkerResponse)


def encode_formal_worker_request(request: FormalWorkerRequest) -> bytes:
    if type(request) is not FormalWorkerRequest:
        raise _invalid()
    raw = canonicalize_json(request.model_dump(mode="json"))
    if len(raw) > MAX_WORKER_MESSAGE_BYTES:
        raise _invalid()
    return raw


def encode_formal_worker_response(response: FormalWorkerResponse) -> bytes:
    if type(response) is not FormalWorkerResponse:
        raise _invalid()
    raw = canonicalize_json(response.model_dump(mode="json"))
    if len(raw) > MAX_WORKER_MESSAGE_BYTES:
        raise _invalid()
    return raw


def worker_request_sha256(request: FormalWorkerRequest) -> str:
    return sha256_hex(encode_formal_worker_request(request))
