"""Acyclic identity and exact-parent preflight for the formal development search."""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.evidence import public_evidence_violations

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitCommit = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
AuthorizationId = Annotated[
    str,
    StringConstraints(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    ),
]

SEARCH_RECEIPT_RELATIVE_PATH = Path("evidence/public/v02/search/search-receipt.json")
EVIDENCE_INDEX_RELATIVE_PATH = Path("evidence/public/v02/search/evidence-index.json")
SEARCH_SOURCE_PATHS = (
    "configs/workload/temporal-development-v2.json",
    "configs/workload/uci-bike-sharing-v1.json",
    "docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md",
    "docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md",
    "docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-formal-seal-closure-corrective.md",
    "docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md",
    "docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md",
    "docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md",
    "docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-closure-design.md",
    "docs/superpowers/specs/2026-08-26-mdcp-v02-private-evidence-container-design.md",
    "pyproject.toml",
    "schemas/v2/bike-request.schema.json",
    "schemas/v2/development-result-index.schema.json",
    "schemas/v2/formal-run-authorization.schema.json",
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
_ALLOWLISTED_FREEZE_ADDITIONS = frozenset(
    {
        SEARCH_RECEIPT_RELATIVE_PATH.as_posix(),
        EVIDENCE_INDEX_RELATIVE_PATH.as_posix(),
    }
)
_BOUND_DIGEST_PATHS = {
    "approved_spec_sha256": Path(
        "docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md"
    ),
    "dependency_lock_sha256": Path("uv.lock"),
    "dataset_contract_sha256": Path("configs/workload/temporal-development-v2.json"),
    "temporal_schema_sha256": Path("schemas/v2/temporal-development.schema.json"),
    "temporal_adapter_sha256": Path("src/mdcp/temporal/adapter.py"),
    "golden_vector_sha256": Path("tests/fixtures/temporal/adapter-golden-vectors.json"),
    "fold_table_sha256": Path("configs/workload/temporal-development-v2.json"),
    "trial_table_sha256": Path("configs/workload/temporal-development-v2.json"),
    "ranking_rule_sha256": Path("src/mdcp/temporal/selection.py"),
    "quality_policy_sha256": Path("configs/workload/temporal-development-v2.json"),
    "statistical_code_sha256": Path("src/mdcp/temporal/evaluation.py"),
}
_FROZEN_DATASET_ARCHIVE_SHA256 = "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
_FROZEN_DEVELOPMENT_ROWS_SHA256 = "b6d1bf9218354b112c2b74344283822fc83be678ff08f96f42199cb18076b3cc"


class SearchIdentityInputs(BaseModel):
    """Source-commit inputs whose values become the public search receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    created_at_utc: datetime

    @field_validator("created_at_utc")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at_utc must be UTC")
        return value


class SearchReceipt(BaseModel):
    """The canonical, public, deliberately acyclic search identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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


class FormalRunAuthorization(BaseModel):
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


class SearchSourceEntry(BaseModel):
    """One immutable source file in the closure-owned search identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    logical_path: str
    git_mode: Literal["100644"]
    byte_size: int
    sha256: Sha256

    @field_validator("logical_path")
    @classmethod
    def _known_logical_path(cls, value: str) -> str:
        if value not in SEARCH_SOURCE_PATHS:
            raise ValueError("SEARCH_SOURCE_PATH_INVALID")
        return value

    @field_validator("byte_size")
    @classmethod
    def _nonnegative_size(cls, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("SEARCH_SOURCE_SIZE_INVALID")
        return value


class SearchEvidenceIndex(BaseModel):
    """The public index whose authenticity is supplied by an external digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
        if tuple(item.logical_path for item in self.source_entries) != SEARCH_SOURCE_PATHS:
            raise ValueError("SEARCH_SOURCE_INDEX_INVALID")
        if self.private_logical_outputs != PRIVATE_LOGICAL_OUTPUTS:
            raise ValueError("SEARCH_SOURCE_INDEX_INVALID")
        if self.source_inventory_sha256 != _inventory_sha256(self.source_entries):
            raise ValueError("SEARCH_SOURCE_INDEX_INVALID")
        return self


@dataclass(frozen=True)
class SearchFreezeCheck:
    verdict: Literal["PASS", "FAIL"]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class SearchSourceCheck:
    verdict: Literal["PASS", "FAIL"]
    reason_codes: tuple[str, ...]


def build_search_source_inventory(root: Path) -> tuple[SearchSourceEntry, ...]:
    """Build the closed 43-entry inventory from regular, non-link source files."""
    root = root.resolve()
    entries: list[SearchSourceEntry] = []
    for logical_path in SEARCH_SOURCE_PATHS:
        source_path = root / logical_path
        raw = _read_regular_nonlink_file(source_path)
        if raw is None:
            raise ValueError("SEARCH_SOURCE_FILE_INVALID")
        entries.append(
            SearchSourceEntry(
                logical_path=logical_path,
                git_mode="100644",
                byte_size=len(raw),
                sha256=sha256_hex(raw),
            )
        )
    return tuple(entries)


def verify_search_source_inventory(
    root: Path, index_path: Path, expected_index_sha256: str
) -> SearchSourceCheck:
    """Verify an extracted source archive only after authenticating its index externally."""
    if not _valid_sha256(expected_index_sha256, nonzero=True):
        return _source_fail("SEARCH_SOURCE_INDEX_ANCHOR_INVALID")
    raw = _read_regular_nonlink_file(index_path)
    if raw is None or sha256_hex(raw) != expected_index_sha256:
        return _source_fail("SEARCH_SOURCE_INDEX_ANCHOR_MISMATCH")
    try:
        index = SearchEvidenceIndex.model_validate(parse_json_bytes(raw))
        if canonicalize_json(index.model_dump(mode="json")) != raw:
            raise ValueError
    except Exception:
        return _source_fail("SEARCH_SOURCE_INDEX_INVALID")
    try:
        actual = build_search_source_inventory(root)
    except ValueError:
        return _source_fail("SEARCH_SOURCE_FILE_INVALID")
    if actual != index.source_entries:
        return _source_fail("SEARCH_SOURCE_INVENTORY_MISMATCH")
    return SearchSourceCheck(verdict="PASS", reason_codes=("SEARCH_SOURCE_INVENTORY_PASS",))


def prepare_search_freeze(root: Path, created_at_utc: datetime) -> SearchEvidenceIndex:
    """Create only the receipt/index pair, refusing a dirty source or existing outputs."""
    root = root.resolve()
    if not _is_clean_checkout(root):
        raise ValueError("SEARCH_FREEZE_DIRTY")
    if not _has_exact_search_source_modes(root):
        raise ValueError("SEARCH_SOURCE_MODE_INVALID")
    if any((root / relative).exists() for relative in _ALLOWLISTED_FREEZE_ADDITIONS):
        raise ValueError("SEARCH_FREEZE_OUTPUT_EXISTS")
    source_commit = _git(root, "rev-parse", "HEAD")
    if source_commit is None or _is_placeholder_commit(source_commit):
        raise ValueError("SEARCH_SOURCE_COMMIT_INVALID")
    fields = {
        name: sha256_hex((root / path).read_bytes()) for name, path in _BOUND_DIGEST_PATHS.items()
    }
    receipt = build_search_receipt(
        SearchIdentityInputs(
            search_source_commit=source_commit,
            dataset_archive_sha256=_FROZEN_DATASET_ARCHIVE_SHA256,
            development_rows_sha256=_FROZEN_DEVELOPMENT_ROWS_SHA256,
            created_at_utc=created_at_utc,
            **fields,
        )
    )
    receipt_bytes = canonicalize_json(receipt.model_dump(mode="json"))
    entries = build_search_source_inventory(root)
    index = SearchEvidenceIndex(
        schema_version="mdcp.search-evidence-index.v1",
        canonicalization_version="RFC8785",
        source_entries=entries,
        source_inventory_sha256=_inventory_sha256(entries),
        private_logical_outputs=PRIVATE_LOGICAL_OUTPUTS,
        search_receipt_sha256=sha256_hex(receipt_bytes),
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )
    _publish_no_clobber(root / SEARCH_RECEIPT_RELATIVE_PATH, receipt_bytes)
    try:
        _publish_no_clobber(
            root / EVIDENCE_INDEX_RELATIVE_PATH, canonicalize_json(index.model_dump(mode="json"))
        )
    except Exception:
        # A partial publication is never accepted; the caller must resolve it manually.
        raise ValueError("SEARCH_FREEZE_PUBLICATION_FAILED") from None
    return index


def build_search_receipt(inputs: SearchIdentityInputs) -> SearchReceipt:
    """Build the receipt without accepting a freeze SHA or private path."""
    if _is_placeholder_commit(inputs.search_source_commit):
        raise ValueError("search_source_commit must be a non-placeholder Git SHA")
    receipt = SearchReceipt(
        schema_version="mdcp.search-receipt.v1",
        canonicalization_version="RFC8785",
        search_source_commit=inputs.search_source_commit,
        approved_spec_sha256=inputs.approved_spec_sha256,
        dependency_lock_sha256=inputs.dependency_lock_sha256,
        dataset_contract_sha256=inputs.dataset_contract_sha256,
        dataset_archive_sha256=inputs.dataset_archive_sha256,
        development_rows_sha256=inputs.development_rows_sha256,
        temporal_schema_sha256=inputs.temporal_schema_sha256,
        temporal_adapter_sha256=inputs.temporal_adapter_sha256,
        golden_vector_sha256=inputs.golden_vector_sha256,
        fold_table_sha256=inputs.fold_table_sha256,
        trial_table_sha256=inputs.trial_table_sha256,
        ranking_rule_sha256=inputs.ranking_rule_sha256,
        quality_policy_sha256=inputs.quality_policy_sha256,
        statistical_code_sha256=inputs.statistical_code_sha256,
        execution_seed=2026,
        estimator_threads=1,
        selection_fit_limit=80,
        replay_fit_limit=4,
        final_fit_limit=1,
        maximum_fit_limit=85,
        h1_role="OBSERVED_DEVELOPMENT_ONLY",
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
        created_at_utc=inputs.created_at_utc,
    )
    if public_evidence_violations(receipt.model_dump(mode="json")):
        raise ValueError("search receipt contains non-public evidence")
    return receipt


def verify_search_freeze(
    repository_root: Path,
    receipt_path: Path,
    evidence_index_path: Path,
    *,
    expected_head: str | None = None,
) -> SearchFreezeCheck:
    """Fail closed unless HEAD is the exact receipt-only child of its source commit."""
    root = repository_root.resolve()
    if not _is_clean_checkout(root):
        return _fail("SEARCH_FREEZE_DIRTY")
    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return _fail("SEARCH_FREEZE_HEAD_INVALID")
    if expected_head is not None and head != expected_head:
        return _fail("SEARCH_FREEZE_HEAD_MISMATCH")
    if not _has_exact_search_source_head_modes(root, head):
        return _fail("SEARCH_SOURCE_MODE_INVALID")
    remotes = _git(root, "remote")
    if remotes is None or remotes:
        return _fail("SEARCH_FREEZE_REMOTE_INVALID")
    tags = _git(root, "tag", "--points-at", "HEAD")
    if tags is None or tags:
        return _fail("SEARCH_FREEZE_HEAD_TAGGED")
    public_evidence_error = _has_regular_public_evidence(root, head)
    if public_evidence_error is not None:
        return _fail(public_evidence_error)
    receipt_bytes = _read_expected_public_file(root, receipt_path, SEARCH_RECEIPT_RELATIVE_PATH)
    if receipt_bytes is None:
        return _fail("SEARCH_RECEIPT_MISSING")
    index_bytes = _read_expected_public_file(
        root, evidence_index_path, EVIDENCE_INDEX_RELATIVE_PATH
    )
    if index_bytes is None:
        return _fail("SEARCH_EVIDENCE_INDEX_MISSING")
    receipt = _parse_receipt(receipt_bytes)
    if receipt is None:
        return _fail("SEARCH_RECEIPT_INVALID")
    index = _parse_index(index_bytes)
    if index is None:
        return _fail("SEARCH_EVIDENCE_INDEX_INVALID")
    if sha256_hex(receipt_bytes) != index.search_receipt_sha256:
        return _fail("SEARCH_RECEIPT_DIGEST_MISMATCH")
    try:
        if build_search_source_inventory(root) != index.source_entries:
            return _fail("SEARCH_SOURCE_INVENTORY_MISMATCH")
    except ValueError:
        return _fail("SEARCH_SOURCE_FILE_INVALID")
    if head == receipt.search_source_commit:
        return _fail("SEARCH_FREEZE_SELF_REFERENCE")
    if _is_placeholder_commit(receipt.search_source_commit):
        return _fail("SEARCH_RECEIPT_INVALID")
    parents = _git(root, "show", "-s", "--format=%P", "HEAD")
    if parents is None or len(parents.split()) != 1:
        return _fail("SEARCH_FREEZE_PARENT_COUNT_INVALID")
    if parents != receipt.search_source_commit:
        return _fail("SEARCH_FREEZE_PARENT_MISMATCH")
    if not _has_exact_allowlisted_additions(root):
        return _fail("SEARCH_FREEZE_DIFF_NOT_ALLOWLISTED")
    if not _bound_digests_recompute(root, receipt):
        return _fail("SEARCH_RECEIPT_BOUND_DIGEST_MISMATCH")
    if receipt.h2_status != "SEALED_NOT_LOADED" or receipt.h2_loaded_rows != 0:
        return _fail("SEARCH_H2_STATE_INVALID")
    return SearchFreezeCheck(verdict="PASS", reason_codes=("SEARCH_FREEZE_PASS",))


def _fail(reason_code: str) -> SearchFreezeCheck:
    return SearchFreezeCheck(verdict="FAIL", reason_codes=(reason_code,))


def _source_fail(reason_code: str) -> SearchSourceCheck:
    return SearchSourceCheck(verdict="FAIL", reason_codes=(reason_code,))


def _valid_sha256(value: object, *, nonzero: bool = False) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
        and (not nonzero or value != "0" * 64)
    )


def _inventory_sha256(entries: tuple[SearchSourceEntry, ...]) -> str:
    return sha256_hex(canonicalize_json([entry.model_dump(mode="json") for entry in entries]))


def _read_regular_nonlink_file(path: Path) -> bytes | None:
    """Read a leaf only when it is a plain regular file, including on Windows."""
    try:
        information = os.lstat(path)
        if (
            path.is_symlink()
            or not stat.S_ISREG(information.st_mode)
            or (
                os.name == "nt"
                and information.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
            )
        ):
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) != information.st_size:
        return None
    return raw


def _publish_no_clobber(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        written = os.write(descriptor, raw)
        if written != len(raw):
            raise OSError("short write")
    finally:
        os.close(descriptor)


def _is_placeholder_commit(value: str) -> bool:
    return value == "0" * 40


def _git(root: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _is_clean_checkout(root: Path) -> bool:
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    return status == ""


def _has_exact_search_source_modes(root: Path) -> bool:
    entries = _git(root, "ls-files", "-s", "--", *SEARCH_SOURCE_PATHS)
    if entries is None:
        return False
    indexed = tuple(line.split("\t", 1) for line in entries.splitlines() if line)
    return (
        len(indexed) == len(SEARCH_SOURCE_PATHS)
        and tuple(item[1] for item in indexed if len(item) == 2) == SEARCH_SOURCE_PATHS
        and all(len(item) == 2 and item[0].split()[0] == "100644" for item in indexed)
    )


def _has_exact_search_source_head_modes(root: Path, head: str) -> bool:
    entries = _git(root, "ls-tree", head, "--", *SEARCH_SOURCE_PATHS)
    if entries is None:
        return False
    parsed = tuple(line.partition("\t") for line in entries.splitlines() if line)
    return (
        len(parsed) == len(SEARCH_SOURCE_PATHS)
        and tuple(item[2] for item in parsed) == SEARCH_SOURCE_PATHS
        and all(
            item[1] == "\t"
            and len(item[0].split()) == 3
            and item[0].split()[0] == "100644"
            and item[0].split()[1] == "blob"
            for item in parsed
        )
    )


def _read_expected_public_file(root: Path, supplied: Path, expected: Path) -> bytes | None:
    try:
        supplied_absolute = supplied.absolute()
        expected_path = root / expected
        expected_absolute = expected_path.absolute()
    except OSError:
        return None
    if supplied_absolute != expected_absolute or expected_path.is_symlink():
        return None
    try:
        return expected_path.read_bytes()
    except OSError:
        return None


def _parse_receipt(raw: bytes) -> SearchReceipt | None:
    try:
        document = parse_json_bytes(raw)
        receipt = SearchReceipt.model_validate(document)
        if canonicalize_json(receipt.model_dump(mode="json")) != raw:
            return None
        if public_evidence_violations(receipt.model_dump(mode="json")):
            return None
    except Exception:
        return None
    return receipt


def _parse_index(raw: bytes) -> SearchEvidenceIndex | None:
    try:
        document = parse_json_bytes(raw)
        index = SearchEvidenceIndex.model_validate(document)
        if canonicalize_json(index.model_dump(mode="json")) != raw:
            return None
        if public_evidence_violations(index.model_dump(mode="json")):
            return None
    except Exception:
        return None
    return index


def _has_exact_allowlisted_additions(root: Path) -> bool:
    diff = _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD")
    if diff is None:
        return False
    entries = [line.split("\t", 1) for line in diff.splitlines() if line]
    return (
        len(entries) == len(_ALLOWLISTED_FREEZE_ADDITIONS)
        and all(len(entry) == 2 and entry[0] == "A" for entry in entries)
        and {entry[1] for entry in entries} == _ALLOWLISTED_FREEZE_ADDITIONS
    )


def _has_regular_public_evidence(root: Path, head: str) -> str | None:
    expected_entries = (
        (SEARCH_RECEIPT_RELATIVE_PATH.as_posix(), "SEARCH_RECEIPT_MISSING"),
        (EVIDENCE_INDEX_RELATIVE_PATH.as_posix(), "SEARCH_EVIDENCE_INDEX_MISSING"),
    )
    for relative_path, missing_error in expected_entries:
        entry = _git(root, "ls-tree", head, "--", relative_path)
        if entry == "":
            return missing_error
        if entry is None:
            return "SEARCH_FREEZE_PUBLIC_EVIDENCE_NOT_REGULAR"
        metadata, separator, path = entry.partition("\t")
        fields = metadata.split()
        if (
            not separator
            or path != relative_path
            or len(fields) != 3
            or fields[0] != "100644"
            or fields[1] != "blob"
        ):
            return "SEARCH_FREEZE_PUBLIC_EVIDENCE_NOT_REGULAR"
    return None


def _bound_digests_recompute(root: Path, receipt: SearchReceipt) -> bool:
    if (
        receipt.dataset_archive_sha256 != _FROZEN_DATASET_ARCHIVE_SHA256
        or receipt.development_rows_sha256 != _FROZEN_DEVELOPMENT_ROWS_SHA256
    ):
        return False
    for field_name, relative_path in _BOUND_DIGEST_PATHS.items():
        try:
            actual = sha256_hex((root / relative_path).read_bytes())
        except OSError:
            return False
        if actual != getattr(receipt, field_name):
            return False
    return True
