"""Closed public development receipts and synthetic private evidence publication."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.evidence import public_evidence_violations

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
_FOLD_IDS = ("F1", "F2", "F3", "F4")
_TRIAL_IDS = tuple(f"TRIAL-{number:02d}" for number in range(1, 21))


class ClosedMetrics(BaseModel):
    """The only public aggregate metrics permitted in a fold receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    row_count: float | None
    stable_mae: float | None
    candidate_mae: float | None
    point_ratio: float | None
    ucb95: float | None

    @field_validator("row_count", "stable_mae", "candidate_mae", "point_ratio", "ucb95")
    @classmethod
    def _finite_non_negative(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("CLOSED_METRIC_INVALID")
        return value


class PublicFoldReceipt(BaseModel):
    """One closed four-fold public receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fold_id: Literal["F1", "F2", "F3", "F4"]
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    metrics: ClosedMetrics
    reason_codes: tuple[Literal["METRICS_UNAVAILABLE", "QUALITY_THRESHOLD_EXCEEDED"], ...]

    @model_validator(mode="after")
    def _unknown_metrics_are_explicit(self) -> PublicFoldReceipt:
        values = tuple(self.metrics.model_dump().values())
        if self.status == "UNKNOWN":
            if any(value is not None for value in values) or self.reason_codes != (
                "METRICS_UNAVAILABLE",
            ):
                raise ValueError("UNKNOWN_RECEIPT_INVALID")
        elif any(value is None for value in values):
            raise ValueError("KNOWN_RECEIPT_METRICS_REQUIRED")
        return self


class PublicTrialReceipt(BaseModel):
    """A trial has exactly one fit per closed fold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: Literal[
        "TRIAL-01",
        "TRIAL-02",
        "TRIAL-03",
        "TRIAL-04",
        "TRIAL-05",
        "TRIAL-06",
        "TRIAL-07",
        "TRIAL-08",
        "TRIAL-09",
        "TRIAL-10",
        "TRIAL-11",
        "TRIAL-12",
        "TRIAL-13",
        "TRIAL-14",
        "TRIAL-15",
        "TRIAL-16",
        "TRIAL-17",
        "TRIAL-18",
        "TRIAL-19",
        "TRIAL-20",
    ]
    selection_fit_count: Literal[4]
    folds: tuple[PublicFoldReceipt, PublicFoldReceipt, PublicFoldReceipt, PublicFoldReceipt]

    @model_validator(mode="after")
    def _exact_fold_inventory(self) -> PublicTrialReceipt:
        if tuple(fold.fold_id for fold in self.folds) != _FOLD_IDS:
            raise ValueError("FOLD_INVENTORY_INVALID")
        return self


class PublicDevelopmentResult(BaseModel):
    """Public-only, schema-closed receipt for one development inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.development-result-index.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["synthetic_test", "natural_development"]
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    h1_role: Literal["OBSERVED_DEVELOPMENT_ONLY"]
    h2_state: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    selection_fit_count: Literal[80]
    result_sha256: Sha256
    trials: tuple[
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
        PublicTrialReceipt,
    ]

    @model_validator(mode="after")
    def _exact_trial_inventory(self) -> PublicDevelopmentResult:
        if tuple(trial.trial_id for trial in self.trials) != _TRIAL_IDS:
            raise ValueError("TRIAL_INVENTORY_INVALID")
        return self


class PrivateFoldEvidence(BaseModel):
    """A canonical private logical file; it is never part of a public receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    logical_path: str
    canonical_bytes: bytes

    @field_validator("logical_path")
    @classmethod
    def _canonical_logical_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or path.is_absolute()
            or any(part in ("", ".", "..") for part in path.parts)
            or path.as_posix() != value
        ):
            raise ValueError("LOGICAL_PATH_INVALID")
        return value


class PrivateRunBundle(BaseModel):
    """Private logical files for a synthetic run only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_class: Literal["synthetic_test", "natural_development"]
    files: tuple[PrivateFoldEvidence, ...]


class PrivateBundleIdentity(BaseModel):
    """The deliberately narrow public identity of private published files."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file_count: int
    total_bytes: int
    inventory_sha256: Sha256
    manifest_sha256: Sha256

    @field_validator("file_count", "total_bytes")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("IDENTITY_COUNT_INVALID")
        return value


class DevelopmentResultCheck(BaseModel):
    """A sanitized verifier result that never includes untrusted material."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: Literal["PASS", "FAIL"]
    reason_codes: tuple[
        Literal["DEVELOPMENT_RESULT_INVALID", "DEVELOPMENT_RESULT_SCHEMA_INVALID"], ...
    ]


class _PublicationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)


def canonical_public_result_bytes(result: PublicDevelopmentResult) -> bytes:
    """Validate the public result and produce its sole RFC-8785 representation."""
    if type(result) is not PublicDevelopmentResult:
        raise _PublicationError("DEVELOPMENT_RESULT_INVALID")
    document = result.model_dump(mode="json")
    if _checked_in_schema() != PublicDevelopmentResult.model_json_schema():
        raise _PublicationError("DEVELOPMENT_RESULT_SCHEMA_INVALID")
    if public_evidence_violations(document):
        raise _PublicationError("DEVELOPMENT_RESULT_INVALID")
    return canonicalize_json(document)


def verify_development_result(path: Path) -> DevelopmentResultCheck:
    """Fail closed for malformed, noncanonical, private, or schema-drifted public evidence."""
    try:
        raw = path.read_bytes()
        document = parse_json_bytes(raw)
        result = PublicDevelopmentResult.model_validate(document)
        if canonical_public_result_bytes(result) != raw:
            return _failed_result("DEVELOPMENT_RESULT_INVALID")
    except _PublicationError as error:
        return _failed_result(str(error))
    except Exception:
        return _failed_result("DEVELOPMENT_RESULT_INVALID")
    return DevelopmentResultCheck(verdict="PASS", reason_codes=())


def write_synthetic_bundle_no_clobber(
    root: Path, bundle: PrivateRunBundle
) -> PrivateBundleIdentity:
    """Atomically publish a private synthetic bundle under an already trusted parent."""
    if type(bundle) is not PrivateRunBundle:
        raise _PublicationError("PRIVATE_BUNDLE_INVALID")
    if bundle.evidence_class != "synthetic_test":
        raise _PublicationError("FORMAL_RUN_PERMIT_REQUIRED")
    _require_new_child_of_trusted_parent(root)
    files = _validated_private_files(bundle.files)
    inventory = [
        {
            "logical_path": item.logical_path,
            "sha256": sha256_hex(item.canonical_bytes),
            "bytes": len(item.canonical_bytes),
        }
        for item in files
    ]
    inventory_sha256 = sha256_hex(canonicalize_json(inventory))
    manifest = canonicalize_json(
        {
            "evidence_class": "synthetic_test",
            "files": inventory,
            "inventory_sha256": inventory_sha256,
        }
    )
    manifest_sha256 = sha256_hex(manifest)
    staging = root.parent / f".{root.name}.staging"
    if staging.exists() or staging.is_symlink():
        raise _PublicationError("STAGING_EXISTS")
    try:
        staging.mkdir()
        for item in files:
            destination = staging.joinpath(*PurePosixPath(item.logical_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            _write_exclusive_canonical_file(destination, item.canonical_bytes)
        _write_exclusive_canonical_file(staging / "manifest.json", manifest)
        os.rename(staging, root)
    except FileExistsError as error:
        raise _PublicationError("DESTINATION_EXISTS") from error
    except OSError as error:
        raise _PublicationError("PUBLICATION_FAILED") from error
    return PrivateBundleIdentity(
        file_count=len(files),
        total_bytes=sum(len(item.canonical_bytes) for item in files),
        inventory_sha256=inventory_sha256,
        manifest_sha256=manifest_sha256,
    )


def _checked_in_schema() -> object:
    try:
        return json.loads(
            Path("schemas/v2/development-result-index.schema.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise _PublicationError("DEVELOPMENT_RESULT_SCHEMA_INVALID") from error


def _failed_result(code: str) -> DevelopmentResultCheck:
    if code not in {"DEVELOPMENT_RESULT_INVALID", "DEVELOPMENT_RESULT_SCHEMA_INVALID"}:
        code = "DEVELOPMENT_RESULT_INVALID"
    return DevelopmentResultCheck(verdict="FAIL", reason_codes=(code,))


def _require_new_child_of_trusted_parent(root: Path) -> None:
    parent = root.parent
    if root.name in ("", ".") or not parent.is_dir() or _is_link(parent):
        raise _PublicationError("TRUSTED_PARENT_REQUIRED")
    if root.exists() or _is_link(root):
        raise _PublicationError("DESTINATION_EXISTS")


def _validated_private_files(
    files: tuple[PrivateFoldEvidence, ...],
) -> tuple[PrivateFoldEvidence, ...]:
    if not files:
        raise _PublicationError("PRIVATE_BUNDLE_EMPTY")
    paths = tuple(item.logical_path for item in files)
    if len(set(paths)) != len(paths):
        raise _PublicationError("DUPLICATE_LOGICAL_PATH")
    if paths != tuple(sorted(paths)):
        raise _PublicationError("LOGICAL_PATH_ORDER_INVALID")
    for item in files:
        try:
            if canonicalize_json(parse_json_bytes(item.canonical_bytes)) != item.canonical_bytes:
                raise _PublicationError("NONCANONICAL_PRIVATE_BYTES")
        except _PublicationError:
            raise
        except Exception as error:
            raise _PublicationError("NONCANONICAL_PRIVATE_BYTES") from error
    return files


def _write_exclusive_canonical_file(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_BINARY, 0o600)
    try:
        offset = 0
        while offset < len(content):
            written = os.write(descriptor, content[offset:])
            if written <= 0:
                raise OSError("PRIVATE_WRITE_FAILED")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _is_link(path: Path) -> bool:
    return path.is_symlink() or os.path.isjunction(path)
