"""Closed public development receipts and synthetic private evidence publication."""

from __future__ import annotations

import base64
import ctypes
import json
import math
import os
import stat
import unicodedata
from ctypes import wintypes
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictFloat,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.evidence import public_evidence_violations

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
_FOLD_IDS = ("F1", "F2", "F3", "F4")
_TRIAL_IDS = tuple(f"TRIAL-{number:02d}" for number in range(1, 21))
_PRIVATE_CONTAINER_SCHEMA = "mdcp.private-evidence-container.v1"
_MAX_PRIVATE_ENTRIES = 128
_MAX_PRIVATE_PAYLOAD_BYTES = 128 * 1024**2
_MAX_PRIVATE_TOTAL_BYTES = 384 * 1024**2
_MAX_PRIVATE_CONTAINER_BYTES = 512 * 1024**2
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }
)
_WINDOWS_DELETE = 0x00010000
_WINDOWS_SYNCHRONIZE = 0x00100000
_WINDOWS_FILE_LIST_DIRECTORY = 0x00000001
_WINDOWS_FILE_READ_DATA = 0x00000001
_WINDOWS_FILE_WRITE_DATA = 0x00000002
_WINDOWS_FILE_ADD_FILE = 0x00000002
_WINDOWS_FILE_TRAVERSE = 0x00000020
_WINDOWS_FILE_READ_ATTRIBUTES = 0x00000080
_WINDOWS_FILE_SHARE_READ_WRITE = 0x00000003
_WINDOWS_FILE_SHARE_READ = 0x00000001
_WINDOWS_OPEN_EXISTING = 3
_WINDOWS_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_WINDOWS_FILE_ATTRIBUTE_NORMAL = 0x00000080
_WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_WINDOWS_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_WINDOWS_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_WINDOWS_FILE_DISPOSITION_INFO = 4
_WINDOWS_OBJECT_CASE_INSENSITIVE = 0x00000040
_WINDOWS_FILE_OPEN = 1
_WINDOWS_FILE_CREATE = 2
_WINDOWS_FILE_DIRECTORY_FILE = 0x00000001
_WINDOWS_FILE_OPEN_REPARSE_POINT = 0x00200000
_WINDOWS_FILE_WRITE_THROUGH = 0x00000002
_WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
_WINDOWS_FILE_NON_DIRECTORY_FILE = 0x00000040
_WINDOWS_STATUS_OBJECT_NAME_COLLISION = -1073741771
_WINDOWS_STATUS_FILE_IS_A_DIRECTORY = -1073741638


class _WindowsFileInformation(ctypes.Structure):
    _fields_ = (
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    )


class _WindowsDispositionInformation(ctypes.Structure):
    _fields_ = (("DeleteFile", wintypes.BOOL),)


class _WindowsUnicodeString(ctypes.Structure):
    _fields_ = (
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", wintypes.LPWSTR),
    )


class _WindowsObjectAttributes(ctypes.Structure):
    _fields_ = (
        ("Length", wintypes.ULONG),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(_WindowsUnicodeString)),
        ("Attributes", wintypes.ULONG),
        ("SecurityDescriptor", ctypes.c_void_p),
        ("SecurityQualityOfService", ctypes.c_void_p),
    )


class _WindowsIoStatusValue(ctypes.Union):
    _fields_ = (("Status", wintypes.LONG), ("Pointer", ctypes.c_void_p))


class _WindowsIoStatusBlock(ctypes.Structure):
    _fields_ = (
        ("StatusOrPointer", _WindowsIoStatusValue),
        ("Information", ctypes.c_size_t),
    )


def _is_windows_alias_component(value: str) -> bool:
    return (
        ":" in value
        or value.endswith((".", " "))
        or value.split(".", 1)[0].rstrip(" .").upper() in _WINDOWS_RESERVED_NAMES
    )


def _is_canonical_logical_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(
        value
        and len(value) <= 240
        and value.isascii()
        and "\\" not in value
        and not path.is_absolute()
        and path.as_posix() == value
        and all(
            part not in ("", ".", "..")
            and len(part) <= 64
            and all(
                character.isascii() and (character.isalnum() or character in "._-")
                for character in part
            )
            and not _is_windows_alias_component(part)
            for part in path.parts
        )
    )


class ClosedMetrics(BaseModel):
    """The only public aggregate metrics permitted in a fold receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    row_count: StrictFloat | None
    stable_mae: StrictFloat | None
    candidate_mae: StrictFloat | None
    point_ratio: StrictFloat | None
    ucb95: StrictFloat | None

    @field_validator("row_count", "stable_mae", "candidate_mae", "point_ratio", "ucb95")
    @classmethod
    def _finite_non_negative(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("CLOSED_METRIC_INVALID")
        return value


class PublicFoldReceipt(BaseModel):
    """One closed four-fold public receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

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

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

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

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

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

    @field_validator("h2_loaded_rows", mode="before")
    @classmethod
    def _reject_boolean_h2_count(cls, value: object) -> object:
        if type(value) is bool:
            raise ValueError("H2_LOADED_ROWS_INVALID")
        return value

    @model_validator(mode="after")
    def _exact_trial_inventory(self) -> PublicDevelopmentResult:
        if tuple(trial.trial_id for trial in self.trials) != _TRIAL_IDS:
            raise ValueError("TRIAL_INVENTORY_INVALID")
        return self


class PrivateFoldEvidence(BaseModel):
    """A canonical private logical file; it is never part of a public receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    logical_path: str
    canonical_bytes: bytes

    @field_validator("logical_path", mode="before")
    @classmethod
    def _exact_logical_path_type(cls, value: object) -> object:
        if type(value) is not str:
            raise ValueError("LOGICAL_PATH_INVALID")
        return value

    @field_validator("logical_path")
    @classmethod
    def _canonical_logical_path(cls, value: str) -> str:
        if not _is_canonical_logical_path(value):
            raise ValueError("LOGICAL_PATH_INVALID")
        return value

    @field_validator("canonical_bytes", mode="before")
    @classmethod
    def _exact_canonical_bytes_type(cls, value: object) -> object:
        if type(value) is not bytes:
            raise ValueError("CANONICAL_BYTES_INVALID")
        return value


class PrivateRunBundle(BaseModel):
    """Private logical files for a synthetic run only."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    evidence_class: Literal["synthetic_test", "natural_development"]
    files: tuple[PrivateFoldEvidence, ...]

    @field_validator("evidence_class", mode="before")
    @classmethod
    def _exact_evidence_class_type(cls, value: object) -> object:
        if type(value) is not str:
            raise ValueError("EVIDENCE_CLASS_INVALID")
        return value

    @field_validator("files", mode="before")
    @classmethod
    def _exact_files_type(cls, value: object) -> object:
        if type(value) is not tuple:
            raise ValueError("PRIVATE_FILES_INVALID")
        return value


class PrivateBundleIdentity(BaseModel):
    """The deliberately narrow public identity of private published files."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    file_count: StrictInt
    total_bytes: StrictInt
    inventory_sha256: Sha256
    manifest_sha256: Sha256

    @field_validator("file_count", "total_bytes", mode="before")
    @classmethod
    def _exact_integer_type(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("IDENTITY_COUNT_INVALID")
        return value

    @field_validator("inventory_sha256", "manifest_sha256", mode="before")
    @classmethod
    def _exact_digest_type(cls, value: object) -> object:
        if type(value) is not str:
            raise ValueError("IDENTITY_DIGEST_INVALID")
        return value

    @field_validator("file_count", "total_bytes")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("IDENTITY_COUNT_INVALID")
        return value


@dataclass(frozen=True, slots=True)
class FormalDevelopmentRequest:
    repository_root: Path
    expected_freeze_head: str
    search_receipt_path: Path
    evidence_index_path: Path
    authorization_path: Path
    consumption_root: Path
    archive_path: Path
    private_container_path: Path


@dataclass(frozen=True, slots=True)
class FormalDevelopmentOutcome:
    verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    private_identity: PrivateBundleIdentity | None
    seal_record_sha256: str | None
    repository_inventory_sha256: str | None
    authorization_sha256: str
    consumption_marker_sha256: str | None
    fit_count: int
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]

    def __post_init__(self) -> None:
        fail_reasons = {
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
        unknown_reasons = {
            "FORMAL_RUN_CONSUMPTION_UNKNOWN",
            "FORMAL_RUN_EXECUTION_UNKNOWN",
            "FORMAL_RUN_SEAL_UNKNOWN",
        }

        def valid_digest(value: object) -> bool:
            return (
                type(value) is str
                and len(value) == 64
                and all(character in "0123456789abcdef" for character in value)
            )

        zero = "0" * 64
        valid_common = (
            type(self.reason_codes) is tuple
            and type(self.fit_count) is int
            and self.h2_status == "SEALED_NOT_LOADED"
            and type(self.h2_loaded_rows) is int
            and self.h2_loaded_rows == 0
            and valid_digest(self.authorization_sha256)
        )
        if not valid_common:
            raise ValueError("FORMAL_DEVELOPMENT_OUTCOME_INVALID")
        if self.verdict == "PASS":
            valid = (
                self.reason_codes == ()
                and type(self.private_identity) is PrivateBundleIdentity
                and valid_digest(self.seal_record_sha256)
                and self.seal_record_sha256 != zero
                and valid_digest(self.repository_inventory_sha256)
                and self.repository_inventory_sha256 != zero
                and self.authorization_sha256 != zero
                and valid_digest(self.consumption_marker_sha256)
                and self.consumption_marker_sha256 != zero
                and self.fit_count in (80, 84)
            )
        elif self.verdict == "FAIL":
            valid = (
                len(self.reason_codes) == 1
                and self.reason_codes[0] in fail_reasons
                and self.private_identity is None
                and self.seal_record_sha256 is None
                and self.repository_inventory_sha256 is None
                and self.consumption_marker_sha256 is None
                and self.fit_count == 0
                and (
                    self.authorization_sha256 == zero
                    if self.reason_codes[0]
                    in {
                        "FORMAL_RUN_REQUEST_INVALID",
                        "SEARCH_FREEZE_INVALID",
                        "FORMAL_RUN_AUTHORIZATION_INVALID",
                        "FORMAL_RUN_REPOSITORY_INVALID",
                        "PUBLICATION_UNSUPPORTED",
                    }
                    else self.authorization_sha256 != zero
                )
            )
        elif self.verdict == "UNKNOWN":
            reason = self.reason_codes[0] if len(self.reason_codes) == 1 else ""
            valid = (
                reason in unknown_reasons
                and self.private_identity is None
                and self.seal_record_sha256 is None
                and self.repository_inventory_sha256 is None
                and self.authorization_sha256 != zero
                and (
                    self.consumption_marker_sha256 is None
                    if reason == "FORMAL_RUN_CONSUMPTION_UNKNOWN"
                    else valid_digest(self.consumption_marker_sha256)
                    and self.consumption_marker_sha256 != zero
                )
                and (
                    self.fit_count == 0
                    if reason == "FORMAL_RUN_CONSUMPTION_UNKNOWN"
                    else 0 <= self.fit_count <= 84
                    if reason == "FORMAL_RUN_EXECUTION_UNKNOWN"
                    else self.fit_count in (80, 84)
                )
            )
        else:
            valid = False
        if not valid:
            raise ValueError("FORMAL_DEVELOPMENT_OUTCOME_INVALID")


class FormalRunConsumptionMarker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal["mdcp.formal-run-consumption.v1"]
    canonicalization_version: Literal["RFC8785"]
    consumed: Literal[True]
    authorization_sha256: Sha256
    search_freeze_commit: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
    search_receipt_sha256: Sha256
    protocol_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]

    @model_validator(mode="after")
    def _nonzero_chain(self) -> FormalRunConsumptionMarker:
        if (
            self.authorization_sha256 == "0" * 64
            or self.search_freeze_commit == "0" * 40
            or self.search_receipt_sha256 == "0" * 64
            or self.protocol_sha256 == "0" * 64
        ):
            raise ValueError("FORMAL_RUN_CONSUMPTION_INVALID")
        return self


class FormalDevelopmentSeal(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        json_schema_extra={
            "allOf": [
                *(
                    {
                        "not": {
                            "properties": {field: {"const": "0" * 64}},
                            "required": [field],
                        }
                    }
                    for field in (
                        "authorization_sha256",
                        "consumption_marker_sha256",
                        "search_receipt_sha256",
                        "source_inventory_sha256",
                        "protocol_sha256",
                        "repository_inventory_sha256",
                        "exit_observation_sha256",
                    )
                ),
                {
                    "properties": {
                        "private_identity": {
                            "properties": {
                                "file_count": {"const": 5},
                                "total_bytes": {"exclusiveMinimum": 0},
                                "inventory_sha256": {"not": {"const": "0" * 64}},
                                "manifest_sha256": {"not": {"const": "0" * 64}},
                            }
                        },
                        "development_result": {
                            "properties": {"evidence_class": {"const": "natural_development"}}
                        },
                    }
                },
                {
                    "if": {
                        "properties": {"selection_status": {"const": "PASS"}},
                        "required": ["selection_status"],
                    },
                    "then": {
                        "properties": {
                            "fit_count": {"const": 84},
                            "development_result": {"properties": {"status": {"const": "PASS"}}},
                        }
                    },
                },
                {
                    "if": {
                        "properties": {"selection_status": {"const": "NO_ELIGIBLE_CANDIDATE"}},
                        "required": ["selection_status"],
                    },
                    "then": {
                        "properties": {
                            "fit_count": {"const": 80},
                            "development_result": {"properties": {"status": {"const": "FAIL"}}},
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "selection_status": {"const": "UNKNOWN/NO_ELIGIBLE_CANDIDATE"}
                        },
                        "required": ["selection_status"],
                    },
                    "then": {
                        "properties": {
                            "fit_count": {"enum": [80, 84]},
                            "development_result": {"properties": {"status": {"const": "UNKNOWN"}}},
                        }
                    },
                },
            ]
        },
    )

    schema_version: Literal["mdcp.formal-development-seal.v1"]
    canonicalization_version: Literal["RFC8785"]
    terminal_state: Literal["SEALED"]
    authorization_sha256: Sha256
    consumption_marker_sha256: Sha256
    search_freeze_commit: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
    search_receipt_sha256: Sha256
    source_inventory_sha256: Sha256
    protocol_sha256: Sha256
    repository_inventory_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]
    private_identity: PrivateBundleIdentity
    exit_observation_sha256: Sha256
    fit_count: Literal[80, 84]
    selection_status: Literal["PASS", "NO_ELIGIBLE_CANDIDATE", "UNKNOWN/NO_ELIGIBLE_CANDIDATE"]
    h1_role: Literal["OBSERVED_DEVELOPMENT_ONLY"]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    development_result: PublicDevelopmentResult

    @model_validator(mode="after")
    def _closed_chain(self) -> FormalDevelopmentSeal:
        nonzero = (
            self.authorization_sha256,
            self.consumption_marker_sha256,
            self.search_receipt_sha256,
            self.source_inventory_sha256,
            self.protocol_sha256,
            self.repository_inventory_sha256,
            self.exit_observation_sha256,
            self.private_identity.inventory_sha256,
            self.private_identity.manifest_sha256,
        )
        status_pairs = {
            "PASS": "PASS",
            "NO_ELIGIBLE_CANDIDATE": "FAIL",
            "UNKNOWN/NO_ELIGIBLE_CANDIDATE": "UNKNOWN",
        }
        if (
            any(value == "0" * 64 for value in nonzero)
            or self.private_identity.file_count != 5
            or self.private_identity.total_bytes <= 0
            or self.development_result.evidence_class != "natural_development"
            or self.development_result.status != status_pairs[self.selection_status]
            or (self.selection_status == "PASS" and self.fit_count != 84)
            or (self.selection_status == "NO_ELIGIBLE_CANDIDATE" and self.fit_count != 80)
        ):
            raise ValueError("FORMAL_DEVELOPMENT_SEAL_INVALID")
        return self


@dataclass(frozen=True, slots=True)
class FormalSealCheck:
    verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    private_identity: PrivateBundleIdentity | None
    seal_record_sha256: str | None
    repository_inventory_sha256: str | None
    fit_count: Literal[0, 80, 84]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]

    def __post_init__(self) -> None:
        fail = {
            "FORMAL_SEAL_REQUEST_INVALID",
            "FORMAL_SEAL_CHAIN_ABSENT",
            "FORMAL_SEAL_CHAIN_INVALID",
            "FORMAL_SEAL_TRUST_MISMATCH",
        }
        unknown = {
            "FORMAL_SEAL_INSPECTION_UNKNOWN",
            "FORMAL_SEAL_CONSUMPTION_UNKNOWN",
            "FORMAL_SEAL_INCOMPLETE",
            "FORMAL_SEAL_UNANCHORED",
        }
        if self.verdict == "PASS":
            valid = (
                self.reason_codes == ()
                and type(self.private_identity) is PrivateBundleIdentity
                and _valid_sha256(self.seal_record_sha256, nonzero=True)
                and _valid_sha256(self.repository_inventory_sha256, nonzero=True)
                and self.fit_count in (80, 84)
            )
        else:
            allowed = (
                fail if self.verdict == "FAIL" else unknown if self.verdict == "UNKNOWN" else set()
            )
            valid = (
                len(self.reason_codes) == 1
                and self.reason_codes[0] in allowed
                and self.private_identity is None
                and self.seal_record_sha256 is None
                and self.repository_inventory_sha256 is None
                and self.fit_count == 0
            )
        if self.h2_status != "SEALED_NOT_LOADED" or self.h2_loaded_rows != 0 or not valid:
            raise ValueError("FORMAL_SEAL_CHECK_INVALID")


class PrivateContainerCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    verdict: Literal["PASS", "FAIL"]
    reason_codes: tuple[
        Literal[
            "PRIVATE_CONTAINER_INVALID",
            "PRIVATE_CONTAINER_NONCANONICAL",
            "PRIVATE_CONTAINER_IDENTITY_MISMATCH",
            "PRIVATE_CONTAINER_SIZE_EXCEEDED",
        ],
        ...,
    ]
    identity: PrivateBundleIdentity | None = None


class _PrivateContainerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    logical_path: str
    byte_size: StrictInt
    sha256: Sha256
    payload_base64: str

    @field_validator("logical_path")
    @classmethod
    def _closed_logical_path(cls, value: str) -> str:
        if not _is_canonical_logical_path(value):
            raise ValueError("LOGICAL_PATH_INVALID")
        return value

    @field_validator("byte_size")
    @classmethod
    def _non_negative_size(cls, value: int) -> int:
        if value < 0:
            raise ValueError("BYTE_SIZE_INVALID")
        return value


class _PrivateContainer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal["mdcp.private-evidence-container.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["synthetic_test", "natural_development"]
    file_count: StrictInt
    total_bytes: StrictInt
    entries: tuple[_PrivateContainerEntry, ...]
    inventory_sha256: Sha256
    manifest_sha256: Sha256

    @field_validator("file_count", "total_bytes")
    @classmethod
    def _non_negative_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("COUNT_INVALID")
        return value


class DevelopmentResultCheck(BaseModel):
    """A sanitized verifier result that never includes untrusted material."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    verdict: Literal["PASS", "FAIL"]
    reason_codes: tuple[
        Literal["DEVELOPMENT_RESULT_INVALID", "DEVELOPMENT_RESULT_SCHEMA_INVALID"], ...
    ]


class _PublicationError(ValueError):
    pass


def _valid_sha256(value: object, *, nonzero: bool = False) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
        and (not nonzero or value != "0" * 64)
    )


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


def _checked_in_schema() -> object:
    try:
        schema = json.loads(
            Path("schemas/v2/development-result-index.schema.json").read_text(encoding="utf-8")
        )
        definitions = schema["$defs"]
        public = dict(definitions["PublicDevelopmentResult"])
        public["$defs"] = {
            name: definitions[name]
            for name in ("ClosedMetrics", "PublicFoldReceipt", "PublicTrialReceipt")
        }
        return public
    except (OSError, json.JSONDecodeError):
        raise _PublicationError("DEVELOPMENT_RESULT_SCHEMA_INVALID") from None


def _failed_result(code: str) -> DevelopmentResultCheck:
    if code not in {"DEVELOPMENT_RESULT_INVALID", "DEVELOPMENT_RESULT_SCHEMA_INVALID"}:
        code = "DEVELOPMENT_RESULT_INVALID"
    return DevelopmentResultCheck(verdict="FAIL", reason_codes=(code,))


def _private_container_failure(code: str) -> PrivateContainerCheck:
    allowed = {
        "PRIVATE_CONTAINER_INVALID",
        "PRIVATE_CONTAINER_NONCANONICAL",
        "PRIVATE_CONTAINER_IDENTITY_MISMATCH",
        "PRIVATE_CONTAINER_SIZE_EXCEEDED",
    }
    if code not in allowed:
        code = "PRIVATE_CONTAINER_INVALID"
    return PrivateContainerCheck(verdict="FAIL", reason_codes=(code,))


def _canonical_base64_decoded_size(value: str) -> int | None:
    if not value.isascii() or len(value) % 4:
        return None
    padding = 2 if value.endswith("==") else 1 if value.endswith("=") else 0
    data_end = len(value) - padding
    if value.find("=") not in (-1, data_end):
        return None
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    if any(value[index] not in alphabet for index in range(data_end)):
        return None
    if padding and len(value) < 4:
        return None
    decoded_size = (len(value) // 4) * 3 - padding
    if decoded_size == 0 and value:
        return None
    return decoded_size


def _inventory_core(entries: tuple[_PrivateContainerEntry, ...]) -> list[dict[str, object]]:
    return [
        {
            "logical_path": entry.logical_path,
            "byte_size": entry.byte_size,
            "sha256": entry.sha256,
        }
        for entry in entries
    ]


def _manifest_core(
    evidence_class: str,
    file_count: int,
    total_bytes: int,
    inventory_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": _PRIVATE_CONTAINER_SCHEMA,
        "canonicalization_version": "RFC8785",
        "evidence_class": evidence_class,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "inventory_sha256": inventory_sha256,
    }


def _validated_private_files(
    files: tuple[PrivateFoldEvidence, ...],
) -> tuple[PrivateFoldEvidence, ...]:
    if type(files) is not tuple or not files:
        raise _PublicationError("PRIVATE_BUNDLE_EMPTY")
    if len(files) > _MAX_PRIVATE_ENTRIES:
        raise _PublicationError("PRIVATE_CONTAINER_SIZE_EXCEEDED")
    if any(type(item) is not PrivateFoldEvidence for item in files):
        raise _PublicationError("PRIVATE_BUNDLE_INVALID")
    paths = tuple(item.logical_path for item in files)
    if len(set(paths)) != len(paths):
        raise _PublicationError("DUPLICATE_LOGICAL_PATH")
    if paths != tuple(sorted(paths, key=lambda value: value.encode("ascii"))):
        raise _PublicationError("LOGICAL_PATH_ORDER_INVALID")
    total_bytes = 0
    for item in files:
        if type(item.logical_path) is not str or type(item.canonical_bytes) is not bytes:
            raise _PublicationError("PRIVATE_BUNDLE_INVALID")
        if len(item.canonical_bytes) > _MAX_PRIVATE_PAYLOAD_BYTES:
            raise _PublicationError("PRIVATE_CONTAINER_SIZE_EXCEEDED")
        total_bytes += len(item.canonical_bytes)
        if total_bytes > _MAX_PRIVATE_TOTAL_BYTES:
            raise _PublicationError("PRIVATE_CONTAINER_SIZE_EXCEEDED")
        try:
            if canonicalize_json(parse_json_bytes(item.canonical_bytes)) != item.canonical_bytes:
                raise _PublicationError("NONCANONICAL_PRIVATE_BYTES")
        except _PublicationError:
            raise
        except Exception:
            raise _PublicationError("NONCANONICAL_PRIVATE_BYTES") from None
    return files


def _canonical_private_container(
    bundle: PrivateRunBundle,
    *forbidden_authority: object,
) -> tuple[bytes, PrivateBundleIdentity]:
    """Build the deterministic synthetic artifact; natural content is never accepted here."""
    if type(bundle) is not PrivateRunBundle:
        raise _PublicationError("PRIVATE_BUNDLE_INVALID")
    if bundle.evidence_class != "synthetic_test":
        raise _PublicationError("FORMAL_RUN_SEAL_AUTHORITY_REQUIRED")
    if forbidden_authority:
        raise _PublicationError("PRIVATE_BUNDLE_INVALID")
    files = _validated_private_files(bundle.files)
    entries = tuple(
        _PrivateContainerEntry(
            logical_path=item.logical_path,
            byte_size=len(item.canonical_bytes),
            sha256=sha256_hex(item.canonical_bytes),
            payload_base64=base64.b64encode(item.canonical_bytes).decode("ascii"),
        )
        for item in files
    )
    total_bytes = sum(entry.byte_size for entry in entries)
    inventory_sha256 = sha256_hex(canonicalize_json(_inventory_core(entries)))
    manifest = _manifest_core(
        bundle.evidence_class,
        len(entries),
        total_bytes,
        inventory_sha256,
    )
    manifest_sha256 = sha256_hex(canonicalize_json(manifest))
    container = _PrivateContainer(
        **manifest,
        entries=entries,
        manifest_sha256=manifest_sha256,
    )
    container_bytes = canonicalize_json(container.model_dump(mode="json"))
    if len(container_bytes) > _MAX_PRIVATE_CONTAINER_BYTES:
        raise _PublicationError("PRIVATE_CONTAINER_SIZE_EXCEEDED")
    identity = PrivateBundleIdentity(
        file_count=len(entries),
        total_bytes=total_bytes,
        inventory_sha256=inventory_sha256,
        manifest_sha256=manifest_sha256,
    )
    return container_bytes, identity


def _verify_private_container_raw(
    raw: bytes, expected_identity: PrivateBundleIdentity
) -> PrivateContainerCheck:
    """Verify already-read canonical bytes against the narrow public identity."""
    if type(raw) is not bytes or type(expected_identity) is not PrivateBundleIdentity:
        return _private_container_failure("PRIVATE_CONTAINER_INVALID")
    try:
        document = parse_json_bytes(raw)
        container = _PrivateContainer.model_validate(document)
        if canonicalize_json(container.model_dump(mode="json")) != raw:
            return _private_container_failure("PRIVATE_CONTAINER_NONCANONICAL")
        entries = container.entries
        if not entries:
            return _private_container_failure("PRIVATE_CONTAINER_INVALID")
        if len(entries) > _MAX_PRIVATE_ENTRIES:
            return _private_container_failure("PRIVATE_CONTAINER_SIZE_EXCEEDED")
        paths = tuple(entry.logical_path for entry in entries)
        if paths != tuple(sorted(set(paths), key=lambda value: value.encode("ascii"))):
            return _private_container_failure("PRIVATE_CONTAINER_INVALID")
        total_bytes = 0
        for entry in entries:
            decoded_size = _canonical_base64_decoded_size(entry.payload_base64)
            if decoded_size is None:
                return _private_container_failure("PRIVATE_CONTAINER_INVALID")
            if decoded_size > _MAX_PRIVATE_PAYLOAD_BYTES:
                return _private_container_failure("PRIVATE_CONTAINER_SIZE_EXCEEDED")
            try:
                payload = base64.b64decode(entry.payload_base64, validate=True)
            except Exception:
                return _private_container_failure("PRIVATE_CONTAINER_INVALID")
            if base64.b64encode(payload).decode("ascii") != entry.payload_base64:
                return _private_container_failure("PRIVATE_CONTAINER_INVALID")
            if len(payload) != decoded_size:
                return _private_container_failure("PRIVATE_CONTAINER_INVALID")
            total_bytes += len(payload)
            if total_bytes > _MAX_PRIVATE_TOTAL_BYTES:
                return _private_container_failure("PRIVATE_CONTAINER_SIZE_EXCEEDED")
            try:
                if canonicalize_json(parse_json_bytes(payload)) != payload:
                    return _private_container_failure("PRIVATE_CONTAINER_NONCANONICAL")
            except Exception:
                return _private_container_failure("PRIVATE_CONTAINER_NONCANONICAL")
            if entry.byte_size != len(payload) or entry.sha256 != sha256_hex(payload):
                return _private_container_failure("PRIVATE_CONTAINER_INVALID")
        if container.file_count != len(entries) or container.total_bytes != total_bytes:
            return _private_container_failure("PRIVATE_CONTAINER_INVALID")
        inventory_sha256 = sha256_hex(canonicalize_json(_inventory_core(entries)))
        if container.inventory_sha256 != inventory_sha256:
            return _private_container_failure("PRIVATE_CONTAINER_INVALID")
        manifest_sha256 = sha256_hex(
            canonicalize_json(
                _manifest_core(
                    container.evidence_class,
                    container.file_count,
                    container.total_bytes,
                    inventory_sha256,
                )
            )
        )
        if container.manifest_sha256 != manifest_sha256:
            return _private_container_failure("PRIVATE_CONTAINER_INVALID")
        identity = PrivateBundleIdentity(
            file_count=container.file_count,
            total_bytes=container.total_bytes,
            inventory_sha256=inventory_sha256,
            manifest_sha256=manifest_sha256,
        )
        if identity != expected_identity:
            return _private_container_failure("PRIVATE_CONTAINER_IDENTITY_MISMATCH")
    except _PublicationError as error:
        return _private_container_failure(str(error))
    except Exception:
        return _private_container_failure("PRIVATE_CONTAINER_INVALID")
    return PrivateContainerCheck(verdict="PASS", reason_codes=(), identity=identity)


def verify_private_container(
    path: Path, expected_identity: PrivateBundleIdentity
) -> PrivateContainerCheck:
    """Single-read one regular canonical container and verify its public identity."""
    if not isinstance(path, Path) or type(expected_identity) is not PrivateBundleIdentity:
        return _private_container_failure("PRIVATE_CONTAINER_INVALID")
    try:
        raw = _read_private_container_once(path)
    except _PublicationError as error:
        return _private_container_failure(str(error))
    except Exception:
        return _private_container_failure("PRIVATE_CONTAINER_INVALID")
    return _verify_private_container_raw(raw, expected_identity)


_MUTATION_BINDINGS = (
    dataclass,
    dataclass_field,
    asdict,
    Lock,
    Path,
    FormalDevelopmentRequest,
    FormalDevelopmentOutcome,
    FormalDevelopmentSeal,
    FormalRunConsumptionMarker,
    PrivateBundleIdentity,
    PrivateRunBundle,
    PublicDevelopmentResult,
    _PrivateContainer,
    _PrivateContainerEntry,
    _PublicationError,
    _valid_sha256,
    _validated_private_files,
    _inventory_core,
    _manifest_core,
    canonicalize_json,
    parse_json_bytes,
    sha256_hex,
    _MAX_PRIVATE_CONTAINER_BYTES,
    _WINDOWS_DELETE,
    _WINDOWS_FILE_ADD_FILE,
    _WINDOWS_FILE_ATTRIBUTE_DIRECTORY,
    _WINDOWS_FILE_ATTRIBUTE_NORMAL,
    _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT,
    _WINDOWS_FILE_CREATE,
    _WINDOWS_FILE_DIRECTORY_FILE,
    _WINDOWS_FILE_DISPOSITION_INFO,
    _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS,
    _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT,
    _WINDOWS_FILE_LIST_DIRECTORY,
    _WINDOWS_FILE_NON_DIRECTORY_FILE,
    _WINDOWS_FILE_OPEN,
    _WINDOWS_FILE_OPEN_REPARSE_POINT,
    _WINDOWS_FILE_READ_ATTRIBUTES,
    _WINDOWS_FILE_SHARE_READ_WRITE,
    _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT,
    _WINDOWS_FILE_TRAVERSE,
    _WINDOWS_FILE_WRITE_DATA,
    _WINDOWS_FILE_WRITE_THROUGH,
    _WINDOWS_INVALID_HANDLE_VALUE,
    _WINDOWS_OBJECT_CASE_INSENSITIVE,
    _WINDOWS_OPEN_EXISTING,
    _WINDOWS_RESERVED_NAMES,
    _WINDOWS_STATUS_FILE_IS_A_DIRECTORY,
    _WINDOWS_STATUS_OBJECT_NAME_COLLISION,
    _WINDOWS_SYNCHRONIZE,
    _WindowsDispositionInformation,
    _WindowsFileInformation,
    _WindowsIoStatusBlock,
    _WindowsObjectAttributes,
    _WindowsUnicodeString,
)


def _make_evidence_mutation_surface():
    """Bind the complete mutation authority inside one consumed lexical scope."""
    (
        closure_dataclass,
        closure_field,
        closure_asdict,
        ClosureLock,
        ClosurePath,
        FormalDevelopmentRequest,
        FormalDevelopmentOutcome,
        FormalDevelopmentSeal,
        FormalRunConsumptionMarker,
        PrivateBundleIdentity,
        PrivateRunBundle,
        PublicDevelopmentResult,
        _PrivateContainer,
        _PrivateContainerEntry,
        _PublicationError,
        _valid_sha256,
        _validated_private_files,
        _inventory_core,
        _manifest_core,
        closure_canonicalize_json,
        closure_parse_json_bytes,
        closure_sha256_hex,
        _MAX_PRIVATE_CONTAINER_BYTES,
        _WINDOWS_DELETE,
        _WINDOWS_FILE_ADD_FILE,
        _WINDOWS_FILE_ATTRIBUTE_DIRECTORY,
        _WINDOWS_FILE_ATTRIBUTE_NORMAL,
        _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT,
        _WINDOWS_FILE_CREATE,
        _WINDOWS_FILE_DIRECTORY_FILE,
        _WINDOWS_FILE_DISPOSITION_INFO,
        _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS,
        _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT,
        _WINDOWS_FILE_LIST_DIRECTORY,
        _WINDOWS_FILE_NON_DIRECTORY_FILE,
        _WINDOWS_FILE_OPEN,
        _WINDOWS_FILE_OPEN_REPARSE_POINT,
        _WINDOWS_FILE_READ_ATTRIBUTES,
        _WINDOWS_FILE_SHARE_READ_WRITE,
        _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT,
        _WINDOWS_FILE_TRAVERSE,
        _WINDOWS_FILE_WRITE_DATA,
        _WINDOWS_FILE_WRITE_THROUGH,
        _WINDOWS_INVALID_HANDLE_VALUE,
        _WINDOWS_OBJECT_CASE_INSENSITIVE,
        _WINDOWS_OPEN_EXISTING,
        _WINDOWS_RESERVED_NAMES,
        _WINDOWS_STATUS_FILE_IS_A_DIRECTORY,
        _WINDOWS_STATUS_OBJECT_NAME_COLLISION,
        _WINDOWS_SYNCHRONIZE,
        _WindowsDispositionInformation,
        _WindowsFileInformation,
        _WindowsIoStatusBlock,
        _WindowsObjectAttributes,
        _WindowsUnicodeString,
    ) = _MUTATION_BINDINGS  # noqa: F821 - consumed before the bootstrap alias is deleted
    b64encode = base64.b64encode
    POINTER = ctypes.POINTER
    byref = ctypes.byref
    c_int = ctypes.c_int
    c_void_p = ctypes.c_void_p
    cast = ctypes.cast
    create_string_buffer = ctypes.create_string_buffer
    create_unicode_buffer = ctypes.create_unicode_buffer
    pointer = ctypes.pointer
    sizeof = ctypes.sizeof
    BOOL = wintypes.BOOL
    DWORD = wintypes.DWORD
    HANDLE = wintypes.HANDLE
    LONG = wintypes.LONG
    LPCWSTR = wintypes.LPCWSTR
    LPWSTR = wintypes.LPWSTR
    ULONG = wintypes.ULONG
    platform = os.name
    S_ISDIR = stat.S_ISDIR
    S_ISREG = stat.S_ISREG
    normalize = unicodedata.normalize
    windll = ctypes.windll if platform == "nt" else None
    attempt_lock = ClosureLock()
    attempt_states: dict[str, str] = {}

    @closure_dataclass(frozen=True, slots=True)
    class FormalInputs:
        repository_root: ClosurePath
        expected_freeze_head: str
        archive_path: ClosurePath
        archive_sha256: str
        search_receipt_sha256: str
        protocol_sha256: str

    @closure_dataclass(frozen=True, slots=True)
    class _DevelopmentExecutionPlan:
        fit_fold: object
        _state: dict[str, object] = closure_field(default_factory=dict, init=False)

        def __post_init__(self) -> None:
            self._state.update({"lock": ClosureLock(), "consumed": False})

    def _checkpoint(guard: object, stage: object) -> None:
        from mdcp.temporal.runner import DevelopmentRunError as CheckpointRunError
        from mdcp.temporal.runtime_guards import RuntimeObservation

        try:
            observation = guard.checkpoint(stage)
        except Exception as error:
            raise CheckpointRunError("RUNTIME_GUARD_INVALID") from error
        if type(observation) is not RuntimeObservation or observation.verdict not in (
            "PASS",
            "UNKNOWN",
        ):
            raise CheckpointRunError("RUNTIME_GUARD_INVALID")
        if observation.verdict != "PASS":
            if type(observation.reason_codes) is not tuple or not observation.reason_codes:
                raise CheckpointRunError("RUNTIME_GUARD_INVALID")
            raise CheckpointRunError(*observation.reason_codes)

    def _execute_fit(
        plan: _DevelopmentExecutionPlan,
        guard: object,
        ledger: object,
        phase: object,
        trial_id: str,
        fold_id: str,
    ) -> object:
        from mdcp.temporal.runner import (
            DevelopmentRunError as FitRunError,
        )
        from mdcp.temporal.runner import (
            FitPhase as ExecutionFitPhase,
        )
        from mdcp.temporal.runner import (
            _valid_fold_result,
        )
        from mdcp.temporal.runtime_guards import RuntimeStage as ExecutionRuntimeStage

        _checkpoint(guard, ExecutionRuntimeStage.PRE_FIT)
        if phase is ExecutionFitPhase.SELECTION:
            ledger.record_selection(trial_id, fold_id)
        else:
            ledger.record_replay(trial_id, fold_id)
        callback_error: Exception | None = None
        result: object = None
        try:
            result = plan.fit_fold(phase, trial_id, fold_id)
        except Exception as error:
            callback_error = error
        _checkpoint(guard, ExecutionRuntimeStage.POST_FIT)
        if callback_error is not None:
            raise FitRunError("FOLD_EXECUTION_FAILED") from callback_error
        if not _valid_fold_result(result, trial_id, fold_id):
            raise FitRunError("FOLD_RESULT_INVALID")
        return result

    def _run_development_core(
        plan: _DevelopmentExecutionPlan,
        guard: object,
        *,
        defer_final_checkpoints: bool = False,
    ) -> object:
        from contextlib import suppress

        from mdcp.common.enums import GateVerdict as CoreGateVerdict
        from mdcp.temporal.runner import (
            EXACT_FOLD_IDS as CORE_FOLD_IDS,
        )
        from mdcp.temporal.runner import (
            EXACT_TRIAL_IDS as CORE_TRIAL_IDS,
        )
        from mdcp.temporal.runner import (
            DevelopmentRunBundle as CoreRunBundle,
        )
        from mdcp.temporal.runner import (
            DevelopmentRunError as CoreRunError,
        )
        from mdcp.temporal.runner import (
            FitLedger,
            _evaluate_trial,
            _private_fold_evidence,
            _process_fold,
            _public_result,
            _replay_digest,
        )
        from mdcp.temporal.runner import (
            FitPhase as CoreFitPhase,
        )
        from mdcp.temporal.runtime_guards import RuntimeStage as CoreRuntimeStage
        from mdcp.temporal.selection import (
            ReplayFoldDigests,
            ReplayResult,
            ReplaySelectionSession,
            SelectionDecision,
            finalize_selection,
        )

        if type(plan) is not _DevelopmentExecutionPlan or not callable(plan.fit_fold):
            raise CoreRunError("DEVELOPMENT_PLAN_INVALID")
        state = plan._state
        lock = state.get("lock")
        if lock is None:
            raise CoreRunError("DEVELOPMENT_PLAN_INVALID")
        with lock:
            if state.get("consumed") is not False:
                raise CoreRunError("RUN_ALREADY_CONSUMED")
            state["consumed"] = True

        pre_seal_checked = False
        exit_checked = False
        try:
            _checkpoint(guard, CoreRuntimeStage.PRE_LOAD)
            ledger = FitLedger()
            private_files: list[PrivateFoldEvidence] = []
            baseline: dict[str, tuple[object, ...]] = {}
            reports: list[object] = []
            qualifications: list[object] = []

            for trial_id in CORE_TRIAL_IDS:
                processed: list[object] = []
                for fold_id in CORE_FOLD_IDS:
                    result = _execute_fit(
                        plan,
                        guard,
                        ledger,
                        CoreFitPhase.SELECTION,
                        trial_id,
                        fold_id,
                    )
                    private_files.append(
                        _private_fold_evidence(
                            len(private_files),
                            CoreFitPhase.SELECTION,
                            result,
                        )
                    )
                    if trial_id == CORE_TRIAL_IDS[0]:
                        baseline[fold_id] = result.predictions
                    stable = baseline.get(fold_id)
                    if stable is None:
                        raise CoreRunError("STABLE_BASELINE_MISSING")
                    processed.append(_process_fold(result, stable))
                fold_tuple = tuple(processed)
                report, context = _evaluate_trial(trial_id, fold_tuple)
                reports.append(report)
                if trial_id != CORE_TRIAL_IDS[0]:
                    from mdcp.temporal.evaluation import qualify_trial

                    qualifications.append(qualify_trial(report, context))

            qualification_tuple = tuple(qualifications)
            session = ReplaySelectionSession(qualification_tuple)
            provisional = ledger.bind_session(session)
            replay: ReplayResult | None = None
            if provisional is None:
                selection = finalize_selection(session, None, None)
                if any(result.verdict.value == "UNKNOWN" for result in qualification_tuple):
                    selection = SelectionDecision(
                        status="UNKNOWN/NO_ELIGIBLE_CANDIDATE",
                        provisional_winner=None,
                        final_winner=None,
                        retry_allowed=False,
                        reason_codes=("QUALIFICATION_UNKNOWN",),
                    )
            else:
                replay_digests: list[ReplayFoldDigests] = []
                for fold_id in CORE_FOLD_IDS:
                    result = _execute_fit(
                        plan,
                        guard,
                        ledger,
                        CoreFitPhase.REPLAY,
                        provisional.trial_id,
                        fold_id,
                    )
                    private_files.append(
                        _private_fold_evidence(
                            len(private_files),
                            CoreFitPhase.REPLAY,
                            result,
                        )
                    )
                    replay_digests.append(_replay_digest(result, baseline[fold_id]))
                replay = ReplayResult(
                    trial_id=provisional.trial_id,
                    family_id=provisional.family_id,
                    ranking_key=provisional.ranking_key,
                    qualification_inventory_sha256=provisional.qualification_inventory_sha256,
                    session_sha256=session.session_sha256,
                    verdict=(
                        CoreGateVerdict.PASS
                        if all(digest.verdict is CoreGateVerdict.PASS for digest in replay_digests)
                        else CoreGateVerdict.UNKNOWN
                    ),
                    digests=tuple(replay_digests),
                )
                selection = finalize_selection(session, provisional, replay)

            private_bundle = PrivateRunBundle(
                evidence_class="synthetic_test",
                files=tuple(
                    sorted(private_files, key=lambda item: item.logical_path.encode("ascii"))
                ),
            )
            public_result = _public_result(
                tuple(reports),
                qualification_tuple,
                selection,
                ledger,
            )
            if not defer_final_checkpoints:
                pre_seal_checked = True
                _checkpoint(guard, CoreRuntimeStage.PRE_SEAL)
                exit_checked = True
                _checkpoint(guard, CoreRuntimeStage.EXIT)
            return CoreRunBundle(
                public_result=public_result,
                private_bundle=private_bundle,
                fit_ledger=ledger,
                qualifications=qualification_tuple,
                replay=replay,
                selection=selection,
            )
        except CoreRunError as original:
            if not defer_final_checkpoints and not pre_seal_checked:
                with suppress(CoreRunError):
                    _checkpoint(guard, CoreRuntimeStage.PRE_SEAL)
            if not defer_final_checkpoints and not exit_checked:
                with suppress(CoreRunError):
                    _checkpoint(guard, CoreRuntimeStage.EXIT)
            raise original
        except Exception as error:
            if not defer_final_checkpoints and not pre_seal_checked:
                with suppress(CoreRunError):
                    _checkpoint(guard, CoreRuntimeStage.PRE_SEAL)
            if not defer_final_checkpoints and not exit_checked:
                with suppress(CoreRunError):
                    _checkpoint(guard, CoreRuntimeStage.EXIT)
            raise CoreRunError("DEVELOPMENT_RUN_UNKNOWN") from error

    def _build_formal_execution_plan(inputs: FormalInputs) -> _DevelopmentExecutionPlan:
        from mdcp.temporal.runner import DevelopmentRunError as PlanRunError

        protocol_path = inputs.repository_root / "configs/workload/temporal-development-v2.json"
        try:
            protocol_bytes = protocol_path.read_bytes()
            if closure_sha256_hex(protocol_bytes) != inputs.protocol_sha256:
                raise PlanRunError("PROTOCOL_IDENTITY_MISMATCH")
            protocol = closure_parse_json_bytes(protocol_bytes)
        except PlanRunError:
            raise
        except Exception as error:
            raise PlanRunError("PROTOCOL_INVALID") from error
        loaded: dict[str, object] = {}

        def fit_fold(phase: object, trial_id: str, fold_id: str) -> object:
            if not loaded:
                _load_formal_execution_state(inputs, protocol, loaded)
            return _fit_formal_fold(loaded, phase, trial_id, fold_id)

        return _DevelopmentExecutionPlan(fit_fold=fit_fold)

    def _load_formal_execution_state(
        inputs: FormalInputs,
        protocol: object,
        state: dict[str, object],
    ) -> None:
        from mdcp.temporal.folds import load_fold_specs, materialize_folds
        from mdcp.temporal.runner import (
            EXACT_FOLD_IDS as INVENTORY_FOLD_IDS,
        )
        from mdcp.temporal.runner import (
            EXACT_TRIAL_IDS as INVENTORY_TRIAL_IDS,
        )
        from mdcp.temporal.runner import (
            DevelopmentRunError as InventoryRunError,
        )
        from mdcp.temporal.trials import load_trial_specs
        from mdcp.workload.dataset import load_uci_development_archive
        from mdcp.workload.splits import split_development_rows

        if not isinstance(protocol, dict):
            raise InventoryRunError("PROTOCOL_INVALID")
        rows = load_uci_development_archive(inputs.archive_path, inputs.archive_sha256)
        partitions = split_development_rows(rows)
        folds = materialize_folds(partitions, load_fold_specs(protocol))
        trials = load_trial_specs(protocol)
        if (
            tuple(fold.spec.fold_id for fold in folds) != INVENTORY_FOLD_IDS
            or tuple(trial.trial_id for trial in trials) != INVENTORY_TRIAL_IDS
        ):
            raise InventoryRunError("FORMAL_INVENTORY_INVALID")
        state.update(
            {
                "folds": {fold.spec.fold_id: fold for fold in folds},
                "trials": {trial.trial_id: trial for trial in trials},
            }
        )

    def _fit_formal_fold(
        state: dict[str, object],
        phase: object,
        trial_id: str,
        fold_id: str,
    ) -> object:
        from datetime import datetime

        from mdcp.common.enums import GateVerdict
        from mdcp.temporal.completeness import AdapterOutcome, LabelOutcome, PredictionOutcome
        from mdcp.temporal.runner import (
            DevelopmentRunError as NaturalFitRunError,
        )
        from mdcp.temporal.runner import (
            _DevelopmentFoldResult,
            _formal_groups,
        )
        from mdcp.temporal.trials import (
            _feature_names,
            _materialize_features,
            build_estimator,
            canonical_trial_identity,
            training_rows_for_trial,
        )

        folds = state["folds"]
        trials = state["trials"]
        del phase
        if not isinstance(folds, dict) or not isinstance(trials, dict):
            raise NaturalFitRunError("FORMAL_INVENTORY_INVALID")
        fold = folds[fold_id]
        trial = trials[trial_id]
        training = training_rows_for_trial(trial, fold)
        features = _feature_names(trial)
        validation = _materialize_features(fold.validation).loc[:, (*features, "cnt")]
        estimator = build_estimator(trial)
        estimator.fit(training.loc[:, features], training["cnt"])
        prediction_values = tuple(
            float(value) for value in estimator.predict(validation.loc[:, features])
        )
        label_values = tuple(float(value) for value in validation["cnt"])
        adapters = tuple(
            AdapterOutcome(
                identity=identity,
                succeeded=True,
                calendar_day=datetime.fromisoformat(identity.local_timestamp).date(),
                groups=_formal_groups(fold.validation.iloc[position]),
            )
            for position, identity in enumerate(fold.inventory)
        )
        predictions = tuple(
            PredictionOutcome(identity=identity, succeeded=True, value=value)
            for identity, value in zip(fold.inventory, prediction_values, strict=True)
        )
        labels = tuple(
            LabelOutcome(identity=identity, succeeded=True, value=value)
            for identity, value in zip(fold.inventory, label_values, strict=True)
        )
        feature_material = [
            [float(value) for value in row]
            for row in validation.loc[:, features].itertuples(index=False, name=None)
        ]
        training_material = [
            [float(value) for value in row]
            for row in training.loc[:, features].itertuples(index=False, name=None)
        ]
        declared = {
            "trial_id": trial_id,
            "fold_id": fold_id,
            "preprocessing_state_sha256": closure_sha256_hex(
                closure_canonicalize_json(
                    {
                        "configuration_sha256": canonical_trial_identity(
                            trial_id
                        ).configuration_sha256,
                        "training_features": training_material,
                        "training_labels": tuple(float(value) for value in training["cnt"]),
                    }
                )
            ),
            "feature_vector_sha256": closure_sha256_hex(
                closure_canonicalize_json(feature_material)
            ),
            "prediction_vector_sha256": closure_sha256_hex(
                closure_canonicalize_json(prediction_values)
            ),
            "metric_sha256": closure_sha256_hex(
                closure_canonicalize_json(
                    {"labels": label_values, "predictions": prediction_values}
                )
            ),
        }
        return _DevelopmentFoldResult(
            trial_id=trial_id,
            fold_id=fold_id,
            inventory=fold.inventory,
            adapters=adapters,
            predictions=predictions,
            labels=labels,
            contract_verdict=GateVerdict.PASS,
            preprocessing_state_sha256=declared["preprocessing_state_sha256"],
            feature_vector_sha256=declared["feature_vector_sha256"],
            prediction_vector_sha256=declared["prediction_vector_sha256"],
            metric_sha256=declared["metric_sha256"],
            receipt_sha256=closure_sha256_hex(closure_canonicalize_json(declared)),
        )

    @closure_dataclass(frozen=True, slots=True)
    class RetainedAncestor:
        handle: int
        volume_serial_number: int
        file_index: int

    @closure_dataclass(slots=True)
    class RetainedDestination:
        absolute_path: ClosurePath
        leaf_name: str
        ancestors: tuple[RetainedAncestor, ...]
        parent_handle: int
        created: bool = False
        closed: bool = False

    @closure_dataclass(slots=True)
    class RetainedPublicationPair:
        private: RetainedDestination
        terminal: RetainedDestination
        private_published: bool = False
        terminal_published: bool = False
        closed: bool = False

    @closure_dataclass(frozen=True, slots=True)
    class MarkerAttempt:
        create_entered: bool
        ntstatus: int | None
        iosb_status: int | None
        iosb_information: int | None
        owned_handle_value: int | None
        leaf_state: Literal["ABSENT", "PRESENT", "INDETERMINATE"]
        result: Literal["CREATED", "COLLISION", "PRECALL_FAILED", "INDETERMINATE"]
        marker_sha256: str | None

    def _absolute_destination(destination: ClosurePath) -> ClosurePath:
        if not isinstance(destination, ClosurePath):
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        try:
            raw_paths = destination._raw_paths
        except Exception:
            raise _PublicationError("TRUSTED_PARENT_REQUIRED") from None
        if (
            type(raw_paths) is not list
            or not raw_paths
            or any(type(raw_path) is not str or not raw_path for raw_path in raw_paths)
        ):
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        first_raw = raw_paths[0]
        ascii_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        if (
            len(first_raw) < 3
            or first_raw[0] not in ascii_letters
            or first_raw[1:3] != ":\\"
            or any("/" in raw_path for raw_path in raw_paths)
        ):
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        raw_fragments = [first_raw[3:], *raw_paths[1:]]
        for index, raw_fragment in enumerate(raw_fragments):
            if not raw_fragment:
                if index == 0:
                    continue
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
            if index > 0 and (
                raw_fragment.startswith("\\") or (len(raw_fragment) >= 2 and raw_fragment[1] == ":")
            ):
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
            if any(component in ("", ".", "..") for component in raw_fragment.split("\\")):
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        value = str(destination)
        if (
            not value
            or normalize("NFC", value) != value
            or value.startswith("\\\\")
            or not destination.is_absolute()
            or len(destination.drive) != 2
            or destination.drive[1:] != ":"
            or destination.drive[0] not in ascii_letters
            or destination.anchor != destination.drive + "\\"
        ):
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        components = destination.parts[1:]
        if not components:
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        for component in components:
            base = component.split(".", 1)[0].rstrip(" .").upper()
            if (
                component in ("", ".", "..")
                or component.endswith((".", " "))
                or "~" in component
                or any(ord(character) < 32 for character in component)
                or any(character in '<>:"|?*' for character in component)
                or base in _WINDOWS_RESERVED_NAMES
                or normalize("NFC", component) != component
            ):
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        return destination

    def _preflight_windows_destination(destination: ClosurePath) -> ClosurePath:
        """Validate every existing ancestor and require one absent regular-file leaf."""
        if platform != "nt":
            raise _PublicationError("PUBLICATION_UNSUPPORTED")
        checked_destination = _absolute_destination(destination)
        ancestors = _windows_open_trusted_ancestors(checked_destination)
        try:
            try:
                checked_destination.lstat()
            except FileNotFoundError:
                pass
            except OSError:
                raise _PublicationError("TRUSTED_PARENT_REQUIRED") from None
            else:
                raise _PublicationError("DESTINATION_EXISTS")
        finally:
            if not _windows_close_all([handle for handle, _, _ in reversed(ancestors)]):
                raise _PublicationError("PUBLICATION_FAILED") from None
        return checked_destination

    def _windows_last_error() -> int:
        get_last_error = windll.kernel32.GetLastError
        get_last_error.argtypes = ()
        get_last_error.restype = DWORD
        return int(get_last_error())

    def _windows_close(handle: int) -> bool:
        close_handle = windll.kernel32.CloseHandle
        close_handle.argtypes = (HANDLE,)
        close_handle.restype = BOOL
        return bool(close_handle(handle))

    def _windows_close_all(handles: list[int]) -> bool:
        all_closed = True
        for handle in handles:
            try:
                if not _windows_close(handle):
                    all_closed = False
            except Exception:
                all_closed = False
        return all_closed

    def _windows_create_file(
        path: ClosurePath,
        desired_access: int,
        creation_disposition: int,
        flags: int,
    ) -> tuple[int | None, int]:
        create_file = windll.kernel32.CreateFileW
        create_file.argtypes = (
            LPCWSTR,
            DWORD,
            DWORD,
            c_void_p,
            DWORD,
            DWORD,
            HANDLE,
        )
        create_file.restype = HANDLE
        handle = create_file(
            str(path),
            desired_access,
            _WINDOWS_FILE_SHARE_READ_WRITE,
            None,
            creation_disposition,
            flags,
            None,
        )
        if handle == _WINDOWS_INVALID_HANDLE_VALUE:
            return None, _windows_last_error()
        return int(handle), 0

    def _windows_file_information(handle: int) -> tuple[int, tuple[int, int, int]]:
        get_information = windll.kernel32.GetFileInformationByHandle
        get_information.argtypes = (
            HANDLE,
            POINTER(_WindowsFileInformation),
        )
        get_information.restype = BOOL
        information = _WindowsFileInformation()
        if not get_information(handle, byref(information)):
            raise _PublicationError("PUBLICATION_FAILED")
        return information.dwFileAttributes, (
            information.dwVolumeSerialNumber,
            information.nFileIndexHigh,
            information.nFileIndexLow,
        )

    def _windows_normalized_handle_name(handle: int) -> str:
        get_name = windll.kernel32.GetFinalPathNameByHandleW
        get_name.argtypes = (
            HANDLE,
            LPWSTR,
            DWORD,
            DWORD,
        )
        get_name.restype = DWORD
        buffer = create_unicode_buffer(32768)
        length = int(get_name(handle, buffer, len(buffer), 0))
        if length == 0 or length >= len(buffer):
            raise _PublicationError("PUBLICATION_FAILED")
        value = buffer.value
        if value.startswith("\\\\?\\"):
            value = value[4:]
        return normalize("NFC", value)

    def _windows_names_equal(left: str, right: str) -> bool:
        compare = windll.kernel32.CompareStringOrdinal
        compare.argtypes = (
            LPCWSTR,
            c_int,
            LPCWSTR,
            c_int,
            BOOL,
        )
        compare.restype = c_int
        return int(compare(left, -1, right, -1, True)) == 2

    def _windows_nt_relative_file(
        parent_handle: int,
        name: str,
        is_directory: bool,
        desired_access: int,
        share_mode: int,
        create_disposition: int,
        create_options: int,
    ) -> tuple[bool, int | None, int | None, int | None, int | None]:
        del is_directory
        entered = False
        status: int | None = None
        iosb_status: int | None = None
        information: int | None = None
        output_handle = None
        try:
            output_handle = HANDLE(_WINDOWS_INVALID_HANDLE_VALUE)
            name_buffer = create_unicode_buffer(name)
            name_length = len(name.encode("utf-16-le"))
            unicode_name = _WindowsUnicodeString(
                Length=name_length,
                MaximumLength=name_length + 2,
                Buffer=cast(name_buffer, LPWSTR),
            )
            attributes = _WindowsObjectAttributes(
                Length=sizeof(_WindowsObjectAttributes),
                RootDirectory=parent_handle,
                ObjectName=pointer(unicode_name),
                Attributes=_WINDOWS_OBJECT_CASE_INSENSITIVE,
                SecurityDescriptor=None,
                SecurityQualityOfService=None,
            )
            io_status = _WindowsIoStatusBlock()
            nt_create_file = windll.ntdll.NtCreateFile
            nt_create_file.argtypes = (
                POINTER(HANDLE),
                ULONG,
                POINTER(_WindowsObjectAttributes),
                POINTER(_WindowsIoStatusBlock),
                c_void_p,
                ULONG,
                ULONG,
                ULONG,
                ULONG,
                c_void_p,
                ULONG,
            )
            nt_create_file.restype = LONG
            entered = True
            status = int(
                nt_create_file(
                    byref(output_handle),
                    desired_access,
                    byref(attributes),
                    byref(io_status),
                    None,
                    _WINDOWS_FILE_ATTRIBUTE_NORMAL,
                    share_mode,
                    create_disposition,
                    create_options,
                    None,
                    0,
                )
            )
            iosb_status = int(io_status.StatusOrPointer.Status)
            information = int(io_status.Information)
        except Exception:
            pass
        owned = None
        try:
            value = output_handle.value if output_handle is not None else None
            if value not in (None, 0, _WINDOWS_INVALID_HANDLE_VALUE):
                owned = int(value)
        except Exception:
            owned = None
        return entered, status, iosb_status, information, owned

    def _windows_open_trusted_ancestors(
        destination: ClosurePath,
    ) -> list[tuple[int, tuple[int, int, int], str]]:
        records: list[tuple[int, tuple[int, int, int], str]] = []
        owned_handles: list[int] = []
        ancestor_access = (
            _WINDOWS_SYNCHRONIZE
            | _WINDOWS_FILE_READ_ATTRIBUTES
            | _WINDOWS_FILE_LIST_DIRECTORY
            | _WINDOWS_FILE_TRAVERSE
        )
        directory_options = (
            _WINDOWS_FILE_DIRECTORY_FILE
            | _WINDOWS_FILE_OPEN_REPARSE_POINT
            | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT
        )
        try:
            expected = destination.anchor
            root_handle, _ = _windows_create_file(
                ClosurePath(expected),
                ancestor_access | (_WINDOWS_FILE_ADD_FILE if len(destination.parts) == 2 else 0),
                _WINDOWS_OPEN_EXISTING,
                _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT | _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS,
            )
            if root_handle is None:
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
            owned_handles.append(root_handle)
            try:
                attributes, root_identity = _windows_file_information(root_handle)
            except _PublicationError:
                raise _PublicationError("TRUSTED_PARENT_REQUIRED") from None
            records.append((root_handle, root_identity, expected))
            if (
                not attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or not _windows_names_equal(_windows_normalized_handle_name(root_handle), expected)
            ):
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
            parent_handle = root_handle
            parent_components = destination.parts[1:-1]
            for index, component in enumerate(parent_components):
                expected = str(ClosurePath(expected) / component)
                try:
                    entered, status, iosb_status, _, handle = _windows_nt_relative_file(
                        parent_handle,
                        component,
                        True,
                        ancestor_access
                        | (_WINDOWS_FILE_ADD_FILE if index == len(parent_components) - 1 else 0),
                        _WINDOWS_FILE_SHARE_READ_WRITE,
                        _WINDOWS_FILE_OPEN,
                        directory_options,
                    )
                except _PublicationError:
                    raise _PublicationError("TRUSTED_PARENT_REQUIRED") from None
                if handle is not None:
                    owned_handles.append(handle)
                if not entered or status != 0 or iosb_status != 0 or handle is None:
                    raise _PublicationError("TRUSTED_PARENT_REQUIRED")
                try:
                    attributes, identity = _windows_file_information(handle)
                except _PublicationError:
                    raise _PublicationError("TRUSTED_PARENT_REQUIRED") from None
                records.append((handle, identity, expected))
                if (
                    not attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                    or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                    or identity[0] != root_identity[0]
                    or not _windows_names_equal(_windows_normalized_handle_name(handle), expected)
                ):
                    raise _PublicationError("TRUSTED_PARENT_REQUIRED")
                parent_handle = handle
            return records
        except Exception as caught:
            close_failed = not _windows_close_all(list(reversed(owned_handles)))
            if close_failed or (
                isinstance(caught, _PublicationError) and str(caught) == "PUBLICATION_FAILED"
            ):
                raise _PublicationError("PUBLICATION_FAILED") from None
            raise _PublicationError("TRUSTED_PARENT_REQUIRED") from None

    def _windows_revalidate_handles(
        records: list[tuple[int, tuple[int, int, int], str]],
    ) -> None:
        root_volume = records[0][1][0]
        for handle, expected_identity, expected_name in records:
            attributes, identity = _windows_file_information(handle)
            if (
                identity != expected_identity
                or identity[0] != root_volume
                or not attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or not _windows_names_equal(_windows_normalized_handle_name(handle), expected_name)
            ):
                raise _PublicationError("PUBLICATION_FAILED")

    def _revalidate_retained_ancestors(destination: RetainedDestination) -> None:
        root_volume = destination.ancestors[0].volume_serial_number
        expected_names = [destination.absolute_path.anchor]
        expected_name = destination.absolute_path.anchor
        for component in destination.absolute_path.parts[1:-1]:
            expected_name = str(ClosurePath(expected_name) / component)
            expected_names.append(expected_name)
        if len(expected_names) != len(destination.ancestors):
            raise _PublicationError("PUBLICATION_FAILED")
        for ancestor, expected_name in zip(destination.ancestors, expected_names, strict=True):
            attributes, identity = _windows_file_information(ancestor.handle)
            expected_identity = (
                ancestor.volume_serial_number,
                ancestor.file_index >> 32,
                ancestor.file_index & 0xFFFFFFFF,
            )
            if (
                identity != expected_identity
                or identity[0] != root_volume
                or not attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or not _windows_names_equal(
                    _windows_normalized_handle_name(ancestor.handle),
                    expected_name,
                )
            ):
                raise _PublicationError("PUBLICATION_FAILED")

    def _revalidate_final_handle(
        destination: RetainedDestination,
        final_handle: int,
        expected_identity: tuple[int, int, int],
    ) -> None:
        attributes, identity = _windows_file_information(final_handle)
        if (
            identity != expected_identity
            or identity[0] != destination.ancestors[0].volume_serial_number
            or attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
            or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
            or not _windows_names_equal(
                _windows_normalized_handle_name(final_handle),
                str(destination.absolute_path),
            )
        ):
            raise _PublicationError("PUBLICATION_FAILED")

    def _windows_flush(handle: int) -> None:
        flush_file_buffers = windll.kernel32.FlushFileBuffers
        flush_file_buffers.argtypes = (HANDLE,)
        flush_file_buffers.restype = BOOL
        if not flush_file_buffers(handle):
            raise _PublicationError("PUBLICATION_FAILED")

    def _windows_write_chunk(handle: int, content: bytes) -> int:
        write_file = windll.kernel32.WriteFile
        write_file.argtypes = (
            HANDLE,
            c_void_p,
            DWORD,
            POINTER(DWORD),
            c_void_p,
        )
        write_file.restype = BOOL
        buffer = create_string_buffer(content, len(content))
        written = DWORD()
        if not write_file(
            handle,
            byref(buffer),
            len(content),
            byref(written),
            None,
        ):
            raise _PublicationError("PUBLICATION_FAILED")
        return int(written.value)

    def _windows_write_all(handle: int, content: bytes) -> None:
        offset = 0
        while offset < len(content):
            chunk = content[offset : offset + 1_048_576]
            written = _windows_write_chunk(handle, chunk)
            if written != len(chunk):
                raise _PublicationError("PUBLICATION_FAILED")
            offset += written

    def _windows_set_delete_disposition(handle: int) -> bool:
        information = _WindowsDispositionInformation(DeleteFile=True)
        set_information = windll.kernel32.SetFileInformationByHandle
        set_information.argtypes = (
            HANDLE,
            c_int,
            c_void_p,
            DWORD,
        )
        set_information.restype = BOOL
        return bool(
            set_information(
                handle,
                _WINDOWS_FILE_DISPOSITION_INFO,
                byref(information),
                sizeof(information),
            )
        )

    def _publish_windows_container(destination: ClosurePath, content: bytes) -> None:
        ancestors = _windows_open_trusted_ancestors(destination)
        parent_handle = ancestors[-1][0]
        final_handle: int | None = None
        published = False
        cleanup_failed = False
        close_failed = False
        error: _PublicationError | None = None
        final_options = (
            _WINDOWS_FILE_NON_DIRECTORY_FILE
            | _WINDOWS_FILE_WRITE_THROUGH
            | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT
        )
        final_access = (
            _WINDOWS_FILE_WRITE_DATA
            | _WINDOWS_DELETE
            | _WINDOWS_SYNCHRONIZE
            | _WINDOWS_FILE_READ_ATTRIBUTES
        )
        try:
            entered, status, iosb_status, information, final_handle = _windows_nt_relative_file(
                parent_handle,
                destination.name,
                False,
                final_access,
                0,
                _WINDOWS_FILE_CREATE,
                final_options,
            )
            if (
                not entered
                or status != 0
                or iosb_status != 0
                or information != 2
                or final_handle is None
            ):
                if status in (
                    _WINDOWS_STATUS_OBJECT_NAME_COLLISION,
                    _WINDOWS_STATUS_FILE_IS_A_DIRECTORY,
                ):
                    raise _PublicationError("DESTINATION_EXISTS")
                raise _PublicationError("PUBLICATION_FAILED")
            attributes, final_identity = _windows_file_information(final_handle)
            if (
                attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or final_identity[0] != ancestors[0][1][0]
                or not _windows_names_equal(
                    _windows_normalized_handle_name(final_handle), str(destination)
                )
            ):
                raise _PublicationError("PUBLICATION_FAILED")
            _windows_write_all(final_handle, content)
            _windows_flush(final_handle)
            attributes, current_identity = _windows_file_information(final_handle)
            if (
                current_identity != final_identity
                or attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or not _windows_names_equal(
                    _windows_normalized_handle_name(final_handle), str(destination)
                )
            ):
                raise _PublicationError("PUBLICATION_FAILED")
            _windows_revalidate_handles(ancestors)
            published = True
        except _PublicationError as caught:
            error = caught
        except Exception:
            error = _PublicationError("PUBLICATION_FAILED")
        finally:
            if final_handle is not None:
                if not published:
                    try:
                        if not _windows_set_delete_disposition(final_handle):
                            cleanup_failed = True
                    except Exception:
                        cleanup_failed = True
                try:
                    if not _windows_close(final_handle):
                        close_failed = True
                except Exception:
                    close_failed = True
            if not _windows_close_all([handle for handle, _, _ in reversed(ancestors)]):
                close_failed = True
        if cleanup_failed or close_failed:
            raise _PublicationError("PUBLICATION_FAILED") from None
        if error is not None:
            raise error

    def _retained_destination(destination: ClosurePath) -> RetainedDestination:
        checked = _absolute_destination(destination)
        ancestors = _windows_open_trusted_ancestors(checked)
        entered, status, iosb_status, _, handle = _windows_nt_relative_file(
            ancestors[-1][0],
            checked.name,
            False,
            _WINDOWS_FILE_READ_ATTRIBUTES | _WINDOWS_SYNCHRONIZE,
            _WINDOWS_FILE_SHARE_READ_WRITE,
            _WINDOWS_FILE_OPEN,
            _WINDOWS_FILE_NON_DIRECTORY_FILE | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT,
        )
        exists = entered and status == 0 and iosb_status == 0 and handle is not None
        absent = status in (-1073741772, -1073741766) and handle is None
        if exists or not absent:
            close_failed = False
            if handle is not None:
                try:
                    if not _windows_close(handle):
                        close_failed = True
                except Exception:
                    close_failed = True
            if not _windows_close_all([item[0] for item in reversed(ancestors)]):
                close_failed = True
            if close_failed:
                raise _PublicationError("PUBLICATION_FAILED") from None
            raise _PublicationError("DESTINATION_EXISTS" if exists else "TRUSTED_PARENT_REQUIRED")
        retained = tuple(
            RetainedAncestor(
                handle=item[0],
                volume_serial_number=item[1][0],
                file_index=(item[1][1] << 32) | item[1][2],
            )
            for item in ancestors
        )
        return RetainedDestination(
            absolute_path=checked,
            leaf_name=checked.name,
            ancestors=retained,
            parent_handle=ancestors[-1][0],
        )

    def close_destination(destination: RetainedDestination) -> bool:
        if destination.closed:
            return True
        destination.closed = True
        return _windows_close_all([item.handle for item in reversed(destination.ancestors)])

    def close_pair(pair: RetainedPublicationPair) -> bool:
        if pair.closed:
            return True
        pair.closed = True
        terminal_closed = close_destination(pair.terminal)
        private_closed = close_destination(pair.private)
        return terminal_closed and private_closed

    def preflight_pair(private_path: ClosurePath) -> RetainedPublicationPair:
        checked_private = _absolute_destination(private_path)
        terminal_path = checked_private.with_name(f"{checked_private.name}.public.json")
        if checked_private == terminal_path:
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        private = _retained_destination(checked_private)
        try:
            terminal = _retained_destination(terminal_path)
        except Exception:
            if not close_destination(private):
                raise _PublicationError("PUBLICATION_FAILED") from None
            raise
        return RetainedPublicationPair(private=private, terminal=terminal)

    def _publish_retained(
        destination: RetainedDestination,
        content: bytes,
        *,
        cleanup_partial: bool,
    ) -> None:
        final_handle: int | None = None
        published = False
        try:
            entered, status, iosb_status, information, final_handle = _windows_nt_relative_file(
                destination.parent_handle,
                destination.leaf_name,
                False,
                _WINDOWS_FILE_WRITE_DATA
                | _WINDOWS_DELETE
                | _WINDOWS_SYNCHRONIZE
                | _WINDOWS_FILE_READ_ATTRIBUTES,
                0,
                _WINDOWS_FILE_CREATE,
                _WINDOWS_FILE_NON_DIRECTORY_FILE
                | _WINDOWS_FILE_WRITE_THROUGH
                | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT,
            )
            if (
                not entered
                or status != 0
                or iosb_status != 0
                or information != 2
                or final_handle is None
            ):
                if status in (
                    _WINDOWS_STATUS_OBJECT_NAME_COLLISION,
                    _WINDOWS_STATUS_FILE_IS_A_DIRECTORY,
                ):
                    raise _PublicationError("DESTINATION_EXISTS")
                raise _PublicationError("PUBLICATION_FAILED")
            attributes, identity = _windows_file_information(final_handle)
            if (
                attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or identity[0] != destination.ancestors[0].volume_serial_number
                or not _windows_names_equal(
                    _windows_normalized_handle_name(final_handle),
                    str(destination.absolute_path),
                )
            ):
                raise _PublicationError("PUBLICATION_FAILED")
            _windows_write_all(final_handle, content)
            _windows_flush(final_handle)
            _revalidate_retained_ancestors(destination)
            _revalidate_final_handle(destination, final_handle, identity)
            published = True
            destination.created = True
        finally:
            if final_handle is not None:
                if cleanup_partial and not published:
                    _windows_set_delete_disposition(final_handle)
                if not _windows_close(final_handle):
                    raise _PublicationError("PUBLICATION_FAILED") from None

    def publish_private(pair: RetainedPublicationPair, content: bytes) -> None:
        if pair.closed or pair.private_published:
            raise _PublicationError("PUBLICATION_FAILED")
        _publish_retained(pair.private, content, cleanup_partial=False)
        pair.private_published = True

    def publish_terminal(pair: RetainedPublicationPair, content: bytes) -> None:
        if pair.closed or not pair.private_published or pair.terminal_published:
            raise _PublicationError("PUBLICATION_FAILED")
        _publish_retained(pair.terminal, content, cleanup_partial=False)
        pair.terminal_published = True

    def _encode_container(
        evidence_class: Literal["synthetic_test", "natural_development"],
        files: tuple[PrivateFoldEvidence, ...],
    ) -> tuple[bytes, PrivateBundleIdentity]:
        bundle = PrivateRunBundle(evidence_class=evidence_class, files=files)
        validated = _validated_private_files(bundle.files)
        entries = tuple(
            _PrivateContainerEntry(
                logical_path=item.logical_path,
                byte_size=len(item.canonical_bytes),
                sha256=closure_sha256_hex(item.canonical_bytes),
                payload_base64=b64encode(item.canonical_bytes).decode("ascii"),
            )
            for item in validated
        )
        total_bytes = sum(item.byte_size for item in entries)
        inventory_sha256 = closure_sha256_hex(closure_canonicalize_json(_inventory_core(entries)))
        manifest = _manifest_core(
            evidence_class,
            len(entries),
            total_bytes,
            inventory_sha256,
        )
        manifest_sha256 = closure_sha256_hex(closure_canonicalize_json(manifest))
        content = closure_canonicalize_json(
            _PrivateContainer(
                **manifest,
                entries=entries,
                manifest_sha256=manifest_sha256,
            ).model_dump(mode="json")
        )
        if len(content) > _MAX_PRIVATE_CONTAINER_BYTES:
            raise _PublicationError("PRIVATE_CONTAINER_SIZE_EXCEEDED")
        return content, PrivateBundleIdentity(
            file_count=len(entries),
            total_bytes=total_bytes,
            inventory_sha256=inventory_sha256,
            manifest_sha256=manifest_sha256,
        )

    def encode_natural(
        files: tuple[PrivateFoldEvidence, ...],
    ) -> tuple[bytes, PrivateBundleIdentity]:
        expected = (
            "provisional-winner.json",
            "qualification-report.json",
            "ranking-report.json",
            "replay-report.json",
            "trial-summary.json",
        )
        if type(files) is not tuple or tuple(item.logical_path for item in files) != expected:
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        return _encode_container("natural_development", files)

    def _json_value(value: object) -> object:
        if hasattr(value, "value") and type(value.value) is str:
            return value.value
        if isinstance(value, tuple):
            return [_json_value(item) for item in value]
        if isinstance(value, list):
            return [_json_value(item) for item in value]
        if isinstance(value, dict):
            return {key: _json_value(item) for key, item in value.items()}
        return value

    def _winner_document(
        winner: object,
        qualification_sha256: str,
        trial_labels: dict[str, str],
    ) -> object:
        if winner is None:
            return None
        document = _json_value(closure_asdict(winner))
        if not isinstance(document, dict):
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        trial_id = document.get("trial_id")
        ranking_key = document.get("ranking_key")
        if (
            type(trial_id) is not str
            or trial_id not in trial_labels
            or not isinstance(ranking_key, list)
            or len(ranking_key) != 5
            or ranking_key[-1] != trial_id
        ):
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        document["trial_id"] = trial_labels[trial_id]
        ranking_key[-1] = trial_labels[trial_id]
        document["qualification_inventory_sha256"] = qualification_sha256
        return document

    def formalize(
        result: object,
    ) -> tuple[tuple[PrivateFoldEvidence, ...], PublicDevelopmentResult, str]:
        from mdcp.temporal.runner import (
            EXACT_FOLD_IDS,
            EXACT_TRIAL_IDS,
            DevelopmentRunBundle,
            FitPhase,
        )

        if type(result) is not DevelopmentRunBundle:
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        trial_labels = {
            trial_id: f"TRIAL-{index:02d}"
            for index, trial_id in enumerate(EXACT_TRIAL_IDS, start=1)
        }
        selection_folds: list[dict[str, object]] = []
        replay_folds: list[dict[str, object]] = []
        for item in result.private_bundle.files:
            document = closure_parse_json_bytes(item.canonical_bytes)
            if not isinstance(document, dict):
                raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
            trial_id = document.get("trial_id")
            if type(trial_id) is not str or trial_id not in trial_labels:
                raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
            document["trial_id"] = trial_labels[trial_id]
            if document.get("phase") == FitPhase.SELECTION.value:
                selection_folds.append(document)
            elif document.get("phase") == FitPhase.REPLAY.value:
                replay_folds.append(document)
            else:
                raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        expected_selection_order = tuple(
            (trial_labels[trial_id], fold_id)
            for trial_id in EXACT_TRIAL_IDS
            for fold_id in EXACT_FOLD_IDS
        )
        selection_order = tuple(
            (document.get("trial_id"), document.get("fold_id")) for document in selection_folds
        )
        if selection_order != expected_selection_order or len(replay_folds) not in (0, 4):
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        raw_qualifications = [_json_value(closure_asdict(item)) for item in result.qualifications]
        if len(raw_qualifications) != 19:
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        raw_qualification_sha256 = closure_sha256_hex(closure_canonicalize_json(raw_qualifications))
        if (
            result.selection.provisional_winner is not None
            and result.selection.provisional_winner.qualification_inventory_sha256
            != raw_qualification_sha256
        ) or (
            result.replay is not None
            and result.replay.qualification_inventory_sha256 != raw_qualification_sha256
        ):
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        qualifications: list[dict[str, object]] = []
        for expected_trial_id, item in zip(EXACT_TRIAL_IDS[1:], raw_qualifications, strict=True):
            if not isinstance(item, dict) or item.get("trial_id") != expected_trial_id:
                raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
            item["trial_id"] = trial_labels[expected_trial_id]
            qualifications.append(item)
        qualification_sha256 = closure_sha256_hex(closure_canonicalize_json(qualifications))
        expected_replay_order = (
            ()
            if result.selection.provisional_winner is None
            else tuple(
                (trial_labels[result.selection.provisional_winner.trial_id], fold_id)
                for fold_id in EXACT_FOLD_IDS
            )
        )
        replay_order = tuple(
            (document.get("trial_id"), document.get("fold_id")) for document in replay_folds
        )
        if replay_order != expected_replay_order:
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        replay_digests = (
            [_json_value(closure_asdict(item)) for item in result.replay.digests]
            if result.replay is not None
            else []
        )
        if tuple(item.get("fold_id") for item in replay_digests) != (
            EXACT_FOLD_IDS if result.replay is not None else ()
        ):
            raise _PublicationError("FORMAL_RUN_OUTPUT_INVALID")
        common = {
            "canonicalization_version": "RFC8785",
            "evidence_class": "natural_development",
        }
        documents = {
            "provisional-winner.json": {
                "schema_version": "mdcp.natural-provisional-winner.v1",
                **common,
                "provisional_winner": _winner_document(
                    result.selection.provisional_winner,
                    qualification_sha256,
                    trial_labels,
                ),
                "final_winner": _winner_document(
                    result.selection.final_winner,
                    qualification_sha256,
                    trial_labels,
                ),
            },
            "qualification-report.json": {
                "schema_version": "mdcp.natural-qualification-report.v1",
                **common,
                "qualification_inventory_sha256": qualification_sha256,
                "qualifications": qualifications,
            },
            "ranking-report.json": {
                "schema_version": "mdcp.natural-ranking-report.v1",
                **common,
                "selection_status": result.selection.status,
                "reason_codes": list(result.selection.reason_codes),
                "retry_allowed": False,
                "qualification_inventory_sha256": qualification_sha256,
                "provisional_ranking_key": (
                    [
                        *result.selection.provisional_winner.ranking_key[:-1],
                        trial_labels[result.selection.provisional_winner.trial_id],
                    ]
                    if result.selection.provisional_winner is not None
                    else None
                ),
            },
            "replay-report.json": {
                "schema_version": "mdcp.natural-replay-report.v1",
                **common,
                "selection_status": result.selection.status,
                "reason_codes": list(result.selection.reason_codes),
                "replay_trial_id": (
                    trial_labels[result.replay.trial_id] if result.replay is not None else None
                ),
                "replay_folds": replay_folds,
                "replay_digests": replay_digests,
            },
            "trial-summary.json": {
                "schema_version": "mdcp.natural-trial-summary.v1",
                **common,
                "selection_fit_count": 80,
                "selection_folds": selection_folds,
                "public_trials": result.public_result.model_dump(mode="json")["trials"],
            },
        }
        files = tuple(
            PrivateFoldEvidence(
                logical_path=logical_path,
                canonical_bytes=closure_canonicalize_json(documents[logical_path]),
            )
            for logical_path in (
                "provisional-winner.json",
                "qualification-report.json",
                "ranking-report.json",
                "replay-report.json",
                "trial-summary.json",
            )
        )
        public = result.public_result.model_dump(mode="json")
        public["evidence_class"] = "natural_development"
        return files, PublicDevelopmentResult.model_validate(public), result.selection.status

    encode_synthetic = _canonical_private_container

    def _outcome(
        verdict: Literal["PASS", "FAIL", "UNKNOWN"],
        reason: str | None,
        *,
        authorization_sha256: str = "0" * 64,
        marker_sha256: str | None = None,
        private_identity: PrivateBundleIdentity | None = None,
        seal_sha256: str | None = None,
        repository_sha256: str | None = None,
        fit_count: int = 0,
    ) -> FormalDevelopmentOutcome:
        return FormalDevelopmentOutcome(
            verdict=verdict,
            reason_codes=() if reason is None else (reason,),
            private_identity=private_identity,
            seal_record_sha256=seal_sha256,
            repository_inventory_sha256=repository_sha256,
            authorization_sha256=authorization_sha256,
            consumption_marker_sha256=marker_sha256,
            fit_count=fit_count,
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
        )

    def _safe_external_directory(path: ClosurePath, repository_root: ClosurePath) -> bool:
        try:
            metadata = path.lstat()
            attributes = metadata.st_file_attributes
            absolute = _absolute_destination(path)
            repository = _absolute_destination(repository_root)
        except Exception:
            return False
        return (
            S_ISDIR(metadata.st_mode)
            and not path.is_symlink()
            and not attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
            and absolute != repository
            and not absolute.is_relative_to(repository)
        )

    def _read_bounded_regular(path: ClosurePath, maximum: int) -> bytes | None:
        try:
            metadata = path.lstat()
            if (
                not S_ISREG(metadata.st_mode)
                or path.is_symlink()
                or metadata.st_file_attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or metadata.st_size <= 0
                or metadata.st_size > maximum
            ):
                return None
            raw = _read_private_container_once(path)
        except Exception:
            return None
        return raw if len(raw) == metadata.st_size else None

    def _marker_leaf_state(
        destination: RetainedDestination,
    ) -> Literal["ABSENT", "PRESENT", "INDETERMINATE"]:
        try:
            entered, status, iosb_status, _, handle = _windows_nt_relative_file(
                destination.parent_handle,
                destination.leaf_name,
                False,
                _WINDOWS_FILE_READ_ATTRIBUTES | _WINDOWS_SYNCHRONIZE,
                _WINDOWS_FILE_SHARE_READ_WRITE,
                _WINDOWS_FILE_OPEN,
                _WINDOWS_FILE_NON_DIRECTORY_FILE | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT,
            )
            if handle is not None:
                try:
                    closed = _windows_close(handle)
                except Exception:
                    return "INDETERMINATE"
                if not closed:
                    return "INDETERMINATE"
                if entered and status == 0 and iosb_status == 0:
                    return "PRESENT"
                return "INDETERMINATE"
            if status in (-1073741772, -1073741766):
                return "ABSENT"
        except Exception:
            pass
        return "INDETERMINATE"

    def _classify_marker_observation(
        entered: bool,
        status: int | None,
        iosb_status: int | None,
        information: int | None,
        owned: int | None,
        leaf_state: Literal["ABSENT", "PRESENT", "INDETERMINATE"],
    ) -> Literal["CREATED", "COLLISION", "PRECALL_FAILED", "INDETERMINATE"]:
        if entered and status == 0 and iosb_status == 0 and information == 2 and owned is not None:
            return "CREATED"
        if entered and status == _WINDOWS_STATUS_OBJECT_NAME_COLLISION and owned is None:
            return "COLLISION"
        if not entered and owned is None and leaf_state == "ABSENT":
            return "PRECALL_FAILED"
        if not entered and owned is None and leaf_state == "PRESENT":
            return "COLLISION"
        return "INDETERMINATE"

    def consume_marker(
        consumption_root: ClosurePath,
        authorization_sha256: str,
        marker_bytes: bytes,
        *,
        preflight_owned: bool = False,
    ) -> MarkerAttempt:
        marker_path = consumption_root / f"{authorization_sha256}.consumed.json"
        with attempt_lock:
            state = attempt_states.get(authorization_sha256)
            if preflight_owned:
                if state != "PREFLIGHT":
                    return MarkerAttempt(
                        False,
                        None,
                        None,
                        None,
                        None,
                        "INDETERMINATE",
                        "INDETERMINATE",
                        None,
                    )
            elif state == "CONSUMED":
                return MarkerAttempt(False, None, None, None, None, "PRESENT", "COLLISION", None)
            elif state in ("PREFLIGHT", "IN_PROGRESS", "UNKNOWN"):
                return MarkerAttempt(
                    False,
                    None,
                    None,
                    None,
                    None,
                    "INDETERMINATE",
                    "INDETERMINATE",
                    None,
                )
        try:
            destination = _retained_destination(marker_path)
        except _PublicationError as error:
            if str(error) == "DESTINATION_EXISTS":
                with attempt_lock:
                    attempt_states[authorization_sha256] = "CONSUMED"
                return MarkerAttempt(False, None, None, None, None, "PRESENT", "COLLISION", None)
            with attempt_lock:
                attempt_states[authorization_sha256] = "UNKNOWN"
            return MarkerAttempt(
                False,
                None,
                None,
                None,
                None,
                "INDETERMINATE",
                "INDETERMINATE",
                None,
            )
        with attempt_lock:
            state = attempt_states.get(authorization_sha256)
            if preflight_owned:
                if state != "PREFLIGHT":
                    if not close_destination(destination):
                        attempt_states[authorization_sha256] = "UNKNOWN"
                    return MarkerAttempt(
                        False,
                        None,
                        None,
                        None,
                        None,
                        "INDETERMINATE",
                        "INDETERMINATE",
                        None,
                    )
                attempt_states[authorization_sha256] = "IN_PROGRESS"
            elif state is not None:
                if not close_destination(destination):
                    attempt_states[authorization_sha256] = "UNKNOWN"
                    return MarkerAttempt(
                        False,
                        None,
                        None,
                        None,
                        None,
                        "INDETERMINATE",
                        "INDETERMINATE",
                        None,
                    )
                return MarkerAttempt(
                    False,
                    None,
                    None,
                    None,
                    None,
                    "PRESENT" if state == "CONSUMED" else "INDETERMINATE",
                    "COLLISION" if state == "CONSUMED" else "INDETERMINATE",
                    None,
                )
            else:
                attempt_states[authorization_sha256] = "IN_PROGRESS"
        entered, status, iosb_status, information, owned = _windows_nt_relative_file(
            destination.parent_handle,
            destination.leaf_name,
            False,
            _WINDOWS_FILE_WRITE_DATA | _WINDOWS_SYNCHRONIZE | _WINDOWS_FILE_READ_ATTRIBUTES,
            0,
            _WINDOWS_FILE_CREATE,
            _WINDOWS_FILE_NON_DIRECTORY_FILE
            | _WINDOWS_FILE_WRITE_THROUGH
            | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT,
        )
        exact_creation = (
            entered and status == 0 and iosb_status == 0 and information == 2 and owned is not None
        )
        leaf_state: Literal["ABSENT", "PRESENT", "INDETERMINATE"] = (
            "PRESENT" if exact_creation else _marker_leaf_state(destination)
        )
        result = _classify_marker_observation(
            entered,
            status,
            iosb_status,
            information,
            owned,
            leaf_state,
        )
        observed_owned = owned
        if result == "CREATED":
            work_failed = False
            close_failed = False
            try:
                marker_attributes, marker_identity = _windows_file_information(owned)
                if (
                    marker_attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                    or marker_attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                    or marker_identity[0] != destination.ancestors[0].volume_serial_number
                    or not _windows_names_equal(
                        _windows_normalized_handle_name(owned),
                        str(destination.absolute_path),
                    )
                ):
                    raise _PublicationError("PUBLICATION_FAILED")
                _windows_write_all(owned, marker_bytes)
                _windows_flush(owned)
                _revalidate_retained_ancestors(destination)
                _revalidate_final_handle(destination, owned, marker_identity)
            except Exception:
                work_failed = True
            finally:
                if owned is not None:
                    try:
                        if not _windows_close(owned):
                            close_failed = True
                    except Exception:
                        close_failed = True
                    owned = None
                try:
                    if not close_destination(destination):
                        close_failed = True
                except Exception:
                    close_failed = True
            if work_failed or close_failed:
                with attempt_lock:
                    attempt_states[authorization_sha256] = "UNKNOWN"
                return MarkerAttempt(
                    entered,
                    status,
                    iosb_status,
                    information,
                    observed_owned,
                    leaf_state,
                    "INDETERMINATE",
                    None,
                )
            digest = closure_sha256_hex(marker_bytes)
            with attempt_lock:
                attempt_states[authorization_sha256] = "CONSUMED"
            return MarkerAttempt(
                entered,
                status,
                iosb_status,
                information,
                observed_owned,
                leaf_state,
                "CREATED",
                digest,
            )
        close_failed = False
        if owned is not None:
            try:
                if not _windows_close(owned):
                    close_failed = True
            except Exception:
                close_failed = True
        if not close_destination(destination):
            close_failed = True
        if close_failed:
            with attempt_lock:
                attempt_states[authorization_sha256] = "UNKNOWN"
            return MarkerAttempt(
                entered,
                status,
                iosb_status,
                information,
                observed_owned,
                "INDETERMINATE",
                "INDETERMINATE",
                None,
            )
        if result == "COLLISION":
            with attempt_lock:
                attempt_states[authorization_sha256] = "CONSUMED"
            return MarkerAttempt(
                entered,
                status,
                iosb_status,
                information,
                observed_owned,
                leaf_state,
                "COLLISION",
                None,
            )
        if result == "PRECALL_FAILED":
            return MarkerAttempt(
                False,
                status,
                iosb_status,
                information,
                observed_owned,
                leaf_state,
                "PRECALL_FAILED",
                None,
            )
        with attempt_lock:
            attempt_states[authorization_sha256] = "UNKNOWN"
        return MarkerAttempt(
            entered,
            status,
            iosb_status,
            information,
            observed_owned,
            leaf_state,
            "INDETERMINATE",
            None,
        )

    def publish_synthetic(destination: ClosurePath, content: bytes) -> None:
        _publish_windows_container(_absolute_destination(destination), content)

    def write_synthetic(
        destination: ClosurePath, bundle: PrivateRunBundle
    ) -> PrivateBundleIdentity:
        if platform != "nt":
            raise _PublicationError("PUBLICATION_UNSUPPORTED")
        content, identity = encode_synthetic(bundle)
        publish_synthetic(destination, content)
        return identity

    def formal_operation(request: FormalDevelopmentRequest) -> FormalDevelopmentOutcome:
        if type(request) is not FormalDevelopmentRequest or not (
            all(
                isinstance(value, ClosurePath)
                for value in (
                    request.repository_root,
                    request.search_receipt_path,
                    request.evidence_index_path,
                    request.authorization_path,
                    request.consumption_root,
                    request.archive_path,
                    request.private_container_path,
                )
            )
            and type(request.expected_freeze_head) is str
            and len(request.expected_freeze_head) == 40
            and request.expected_freeze_head != "0" * 40
            and all(character in "0123456789abcdef" for character in request.expected_freeze_head)
        ):
            return _outcome("FAIL", "FORMAL_RUN_REQUEST_INVALID")
        if platform != "nt":
            return _outcome("FAIL", "PUBLICATION_UNSUPPORTED")

        from mdcp.temporal.search_identity import (
            FormalRunAuthorization,
            SearchReceipt,
            verify_search_freeze,
        )

        try:
            repository = _absolute_destination(request.repository_root)
            if repository != _absolute_destination(ClosurePath.cwd()):
                return _outcome("FAIL", "FORMAL_RUN_REPOSITORY_INVALID")
            freeze = verify_search_freeze(
                repository,
                request.search_receipt_path,
                request.evidence_index_path,
                expected_head=request.expected_freeze_head,
            )
            if freeze.verdict != "PASS":
                return _outcome("FAIL", "SEARCH_FREEZE_INVALID")
            receipt_raw = _read_bounded_regular(request.search_receipt_path, 1_048_576)
            index_raw = _read_bounded_regular(request.evidence_index_path, 4_194_304)
            if receipt_raw is None or index_raw is None:
                return _outcome("FAIL", "SEARCH_FREEZE_INVALID")
            receipt = SearchReceipt.model_validate(closure_parse_json_bytes(receipt_raw))
            if closure_canonicalize_json(receipt.model_dump(mode="json")) != receipt_raw:
                return _outcome("FAIL", "SEARCH_FREEZE_INVALID")
            authorization_raw = _read_bounded_regular(request.authorization_path, 65_536)
            if authorization_raw is None:
                return _outcome("FAIL", "FORMAL_RUN_AUTHORIZATION_INVALID")
            authorization = FormalRunAuthorization.model_validate(
                closure_parse_json_bytes(authorization_raw)
            )
            if (
                closure_canonicalize_json(authorization.model_dump(mode="json"))
                != authorization_raw
            ):
                return _outcome("FAIL", "FORMAL_RUN_AUTHORIZATION_INVALID")
        except Exception:
            return _outcome("FAIL", "FORMAL_RUN_AUTHORIZATION_INVALID")
        authorization_sha256 = closure_sha256_hex(authorization_raw)
        receipt_sha256 = closure_sha256_hex(receipt_raw)
        if (
            authorization.search_freeze_commit != request.expected_freeze_head
            or authorization.search_receipt_sha256 != receipt_sha256
            or authorization.protocol_sha256 != receipt.dataset_contract_sha256
            or authorization.dataset_archive_sha256 != receipt.dataset_archive_sha256
        ):
            return _outcome(
                "FAIL",
                "FORMAL_RUN_AUTHORIZATION_MISMATCH",
                authorization_sha256=authorization_sha256,
            )
        if not _safe_external_directory(request.consumption_root, repository):
            return _outcome(
                "FAIL",
                "FORMAL_RUN_CONSUMPTION_ROOT_INVALID",
                authorization_sha256=authorization_sha256,
            )
        if not _safe_external_directory(request.private_container_path.parent, repository):
            return _outcome(
                "FAIL",
                "FORMAL_RUN_DESTINATION_INVALID",
                authorization_sha256=authorization_sha256,
            )
        with attempt_lock:
            state = attempt_states.get(authorization_sha256)
            if state == "CONSUMED":
                return _outcome(
                    "FAIL",
                    "FORMAL_RUN_AUTHORIZATION_CONSUMED",
                    authorization_sha256=authorization_sha256,
                )
            if state is not None:
                return _outcome(
                    "UNKNOWN",
                    "FORMAL_RUN_CONSUMPTION_UNKNOWN",
                    authorization_sha256=authorization_sha256,
                )
            attempt_states[authorization_sha256] = "PREFLIGHT"
        try:
            pair = preflight_pair(request.private_container_path)
        except Exception:
            with attempt_lock:
                attempt_states[authorization_sha256] = "UNKNOWN"
            return _outcome(
                "FAIL",
                "FORMAL_RUN_DESTINATION_INVALID",
                authorization_sha256=authorization_sha256,
            )
        marker = FormalRunConsumptionMarker(
            schema_version="mdcp.formal-run-consumption.v1",
            canonicalization_version="RFC8785",
            consumed=True,
            authorization_sha256=authorization_sha256,
            search_freeze_commit=request.expected_freeze_head,
            search_receipt_sha256=receipt_sha256,
            protocol_sha256=receipt.dataset_contract_sha256,
            dataset_archive_sha256=receipt.dataset_archive_sha256,
        )
        marker_bytes = closure_canonicalize_json(marker.model_dump(mode="json"))
        marker_attempt = consume_marker(
            request.consumption_root,
            authorization_sha256,
            marker_bytes,
            preflight_owned=True,
        )
        if marker_attempt.result == "COLLISION":
            if not close_pair(pair):
                return _outcome(
                    "UNKNOWN",
                    "FORMAL_RUN_CONSUMPTION_UNKNOWN",
                    authorization_sha256=authorization_sha256,
                )
            return _outcome(
                "FAIL",
                "FORMAL_RUN_AUTHORIZATION_CONSUMED",
                authorization_sha256=authorization_sha256,
            )
        if marker_attempt.result == "PRECALL_FAILED":
            if not close_pair(pair):
                with attempt_lock:
                    attempt_states[authorization_sha256] = "UNKNOWN"
                return _outcome(
                    "UNKNOWN",
                    "FORMAL_RUN_CONSUMPTION_UNKNOWN",
                    authorization_sha256=authorization_sha256,
                )
            with attempt_lock:
                if attempt_states.get(authorization_sha256) != "IN_PROGRESS":
                    attempt_states[authorization_sha256] = "UNKNOWN"
                    return _outcome(
                        "UNKNOWN",
                        "FORMAL_RUN_CONSUMPTION_UNKNOWN",
                        authorization_sha256=authorization_sha256,
                    )
                attempt_states.pop(authorization_sha256)
            return _outcome(
                "FAIL",
                "FORMAL_RUN_CONSUMPTION_FAILED",
                authorization_sha256=authorization_sha256,
            )
        if marker_attempt.result != "CREATED" or marker_attempt.marker_sha256 is None:
            if not close_pair(pair):
                return _outcome(
                    "UNKNOWN",
                    "FORMAL_RUN_CONSUMPTION_UNKNOWN",
                    authorization_sha256=authorization_sha256,
                )
            return _outcome(
                "UNKNOWN",
                "FORMAL_RUN_CONSUMPTION_UNKNOWN",
                authorization_sha256=authorization_sha256,
            )
        marker_sha256 = marker_attempt.marker_sha256
        fit_count = 0
        phase = "EXECUTION"
        guard = None
        pre_seal_attempted = False
        exit_attempted = False

        def _attempt_pre_seal() -> None:
            nonlocal pre_seal_attempted
            if guard is None or pre_seal_attempted:
                return
            pre_seal_attempted = True
            _checkpoint(guard, RuntimeStage.PRE_SEAL)

        def _attempt_exit():
            nonlocal exit_attempted
            if guard is None or exit_attempted:
                return None
            exit_attempted = True
            return guard.checkpoint(RuntimeStage.EXIT)

        def _finish_terminal_guards() -> None:
            if guard is None:
                return
            try:
                _attempt_pre_seal()
            except Exception as error:
                del error
            try:
                _attempt_exit()
            except Exception as error:
                del error

        try:
            from mdcp.temporal.runtime_guards import (
                RuntimeStage,
                build_production_runtime_guard,
            )

            inputs = FormalInputs(
                repository_root=repository,
                expected_freeze_head=request.expected_freeze_head,
                archive_path=request.archive_path,
                archive_sha256=receipt.dataset_archive_sha256,
                search_receipt_sha256=receipt_sha256,
                protocol_sha256=receipt.dataset_contract_sha256,
            )
            guard = build_production_runtime_guard(repository, request.expected_freeze_head)
            result = _run_development_core(
                _build_formal_execution_plan(inputs),
                guard,
                defer_final_checkpoints=True,
            )
            fit_count = result.fit_ledger.total_count
            files, public_result, selection_status = formalize(result)
            private_bytes, private_identity = encode_natural(files)
            _attempt_pre_seal()
            publish_private(pair, private_bytes)
            phase = "SEAL"
            exit_observation = _attempt_exit()
            if (
                exit_observation is None
                or exit_observation.verdict != "PASS"
                or exit_observation.reason_codes != ()
                or not _valid_sha256(
                    exit_observation.repository_inventory_sha256,
                    nonzero=True,
                )
                or type(exit_observation.elapsed_ns) is not int
                or not 0 <= exit_observation.elapsed_ns <= 21_600_000_000_000
                or type(exit_observation.peak_process_bytes) is not int
                or not 0 <= exit_observation.peak_process_bytes <= 4_294_967_296
            ):
                raise _PublicationError("FORMAL_RUN_SEAL_UNKNOWN")
            repository_sha256 = exit_observation.repository_inventory_sha256
            exit_sha256 = closure_sha256_hex(
                closure_canonicalize_json(
                    {
                        "elapsed_within_budget": True,
                        "max_elapsed_ns": 21_600_000_000_000,
                        "max_peak_process_bytes": 4_294_967_296,
                        "memory_within_budget": True,
                        "reason_codes": [],
                        "repository_inventory_sha256": repository_sha256,
                        "schema_version": "mdcp.formal-exit-observation.v1",
                        "search_freeze_commit": request.expected_freeze_head,
                        "stage": "EXIT",
                        "verdict": "PASS",
                    }
                )
            )
            seal = FormalDevelopmentSeal(
                schema_version="mdcp.formal-development-seal.v1",
                canonicalization_version="RFC8785",
                terminal_state="SEALED",
                authorization_sha256=authorization_sha256,
                consumption_marker_sha256=marker_sha256,
                search_freeze_commit=request.expected_freeze_head,
                search_receipt_sha256=receipt_sha256,
                source_inventory_sha256=closure_sha256_hex(index_raw),
                protocol_sha256=receipt.dataset_contract_sha256,
                repository_inventory_sha256=repository_sha256,
                dataset_archive_sha256=receipt.dataset_archive_sha256,
                private_identity=private_identity,
                exit_observation_sha256=exit_sha256,
                fit_count=fit_count,
                selection_status=selection_status,
                h1_role="OBSERVED_DEVELOPMENT_ONLY",
                h2_status="SEALED_NOT_LOADED",
                h2_loaded_rows=0,
                development_result=public_result,
            )
            seal_bytes = closure_canonicalize_json(seal.model_dump(mode="json"))
            seal_sha256 = closure_sha256_hex(seal_bytes)
            publish_terminal(pair, seal_bytes)
            if not close_pair(pair):
                raise _PublicationError("FORMAL_RUN_SEAL_UNKNOWN")
            return _outcome(
                "PASS",
                None,
                authorization_sha256=authorization_sha256,
                marker_sha256=marker_sha256,
                private_identity=private_identity,
                seal_sha256=seal_sha256,
                repository_sha256=repository_sha256,
                fit_count=fit_count,
            )
        except Exception:
            _finish_terminal_guards()
            reason = (
                "FORMAL_RUN_SEAL_UNKNOWN" if phase == "SEAL" else "FORMAL_RUN_EXECUTION_UNKNOWN"
            )
            if not close_pair(pair):
                return _outcome(
                    "UNKNOWN",
                    reason,
                    authorization_sha256=authorization_sha256,
                    marker_sha256=marker_sha256,
                    fit_count=fit_count if phase == "EXECUTION" else fit_count or 80,
                )
            return _outcome(
                "UNKNOWN",
                reason,
                authorization_sha256=authorization_sha256,
                marker_sha256=marker_sha256,
                fit_count=fit_count if phase == "EXECUTION" else fit_count or 80,
            )

    def execute(request: FormalDevelopmentRequest) -> FormalDevelopmentOutcome:
        return formal_operation(request)

    return write_synthetic, execute


write_synthetic_bundle_no_clobber, execute_authorized_formal_development = (
    _make_evidence_mutation_surface()
)
del _make_evidence_mutation_surface
del _MUTATION_BINDINGS


def _seal_check(
    verdict: Literal["PASS", "FAIL", "UNKNOWN"],
    reason: str | None,
    *,
    private_identity: PrivateBundleIdentity | None = None,
    seal_sha256: str | None = None,
    repository_sha256: str | None = None,
    fit_count: Literal[0, 80, 84] = 0,
) -> FormalSealCheck:
    return FormalSealCheck(
        verdict=verdict,
        reason_codes=() if reason is None else (reason,),
        private_identity=private_identity,
        seal_record_sha256=seal_sha256,
        repository_inventory_sha256=repository_sha256,
        fit_count=fit_count,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )


def _recovery_leaf(path: Path, maximum: int) -> tuple[str, bytes | None]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return "ABSENT", None
    except OSError:
        return "UNKNOWN", None
    try:
        if (
            not stat.S_ISREG(metadata.st_mode)
            or path.is_symlink()
            or metadata.st_size <= 0
            or metadata.st_size > maximum
            or (
                os.name == "nt"
                and metadata.st_file_attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
            )
        ):
            return "PRESENT", None
        raw = _read_private_container_once(path)
    except Exception:
        return "UNKNOWN", None
    return ("PRESENT", raw) if len(raw) == metadata.st_size else ("UNKNOWN", None)


def _exact_keys(value: object, expected: frozenset[str]) -> bool:
    return isinstance(value, dict) and frozenset(value) == expected


def _valid_source_identity(value: object, fold_id: str) -> bool:
    return bool(
        _exact_keys(
            value,
            frozenset(
                {
                    "fold_id",
                    "request_id",
                    "local_timestamp",
                    "source_position",
                    "identity_sha256",
                }
            ),
        )
        and value["fold_id"] == fold_id
        and type(value["request_id"]) is str
        and bool(value["request_id"])
        and type(value["local_timestamp"]) is str
        and bool(value["local_timestamp"])
        and type(value["source_position"]) is int
        and value["source_position"] >= 0
        and _valid_sha256(value["identity_sha256"], nonzero=True)
    )


def _valid_fold_document(
    value: object,
    *,
    phase: str,
    trial_id: str,
    fold_id: str,
) -> bool:
    expected_keys = frozenset(
        {
            "phase",
            "trial_id",
            "fold_id",
            "contract_verdict",
            "inventory",
            "adapters",
            "predictions",
            "labels",
            "preprocessing_state_sha256",
            "feature_vector_sha256",
            "prediction_vector_sha256",
            "metric_sha256",
            "receipt_sha256",
        }
    )
    if (
        not _exact_keys(value, expected_keys)
        or value["phase"] != phase
        or value["trial_id"] != trial_id
        or value["fold_id"] != fold_id
        or value["contract_verdict"] not in {"PASS", "FAIL", "UNKNOWN"}
        or any(
            not _valid_sha256(value[field], nonzero=True)
            for field in (
                "preprocessing_state_sha256",
                "feature_vector_sha256",
                "prediction_vector_sha256",
                "metric_sha256",
                "receipt_sha256",
            )
        )
    ):
        return False
    inventory = value["inventory"]
    adapters = value["adapters"]
    predictions = value["predictions"]
    labels = value["labels"]
    if (
        not isinstance(inventory, list)
        or not inventory
        or not all(isinstance(items, list) for items in (adapters, predictions, labels))
        or len(adapters) != len(inventory)
        or len(predictions) != len(inventory)
        or len(labels) != len(inventory)
    ):
        return False
    adapter_keys = frozenset({"identity", "succeeded", "calendar_day", "groups", "reason_code"})
    value_keys = frozenset({"identity", "succeeded", "value", "reason_code"})
    for index, identity in enumerate(inventory):
        if not _valid_source_identity(identity, fold_id):
            return False
        adapter = adapters[index]
        if (
            not _exact_keys(adapter, adapter_keys)
            or adapter["identity"] != identity
            or type(adapter["succeeded"]) is not bool
            or not (adapter["calendar_day"] is None or type(adapter["calendar_day"]) is str)
            or not isinstance(adapter["groups"], list)
            or not all(type(group) is str for group in adapter["groups"])
            or not (adapter["reason_code"] is None or type(adapter["reason_code"]) is str)
        ):
            return False
        for outcome in (predictions[index], labels[index]):
            if (
                not _exact_keys(outcome, value_keys)
                or outcome["identity"] != identity
                or type(outcome["succeeded"]) is not bool
                or not (
                    outcome["value"] is None
                    or type(outcome["value"]) in (int, float)
                    and math.isfinite(outcome["value"])
                )
                or not (outcome["reason_code"] is None or type(outcome["reason_code"]) is str)
            ):
                return False
    return True


def _valid_fold_digest(value: object, fold_id: str, *, replay: bool) -> bool:
    keys = {
        "fold_id",
        "configuration_sha256",
        "preprocessing_state_sha256",
        "feature_vector_sha256",
        "prediction_vector_sha256",
        "metric_sha256",
        "receipt_sha256",
    }
    if replay:
        keys.add("verdict")
    return bool(
        _exact_keys(value, frozenset(keys))
        and value["fold_id"] == fold_id
        and (not replay or value["verdict"] in {"PASS", "FAIL", "UNKNOWN"})
        and all(
            _valid_sha256(value[field], nonzero=True)
            for field in keys
            if field not in {"fold_id", "verdict"}
        )
    )


def _valid_ranking_key(value: object, trial_id: str) -> bool:
    return bool(
        isinstance(value, list)
        and len(value) == 5
        and all(type(item) in (int, float) and math.isfinite(item) for item in value[:3])
        and type(value[3]) is int
        and value[4] == trial_id
    )


def _valid_winner(value: object, qualification_sha256: str) -> bool:
    keys = frozenset(
        {
            "trial_id",
            "family_id",
            "configuration_sha256",
            "report_sha256",
            "pooled_ucb95",
            "worst_fold_point",
            "worst_subgroup_ucb95",
            "ranking_key",
            "fold_digests",
            "qualification_inventory_sha256",
        }
    )
    if not _exact_keys(value, keys):
        return False
    trial_id = value["trial_id"]
    return bool(
        trial_id in _TRIAL_IDS[1:]
        and type(value["family_id"]) is str
        and bool(value["family_id"])
        and all(
            _valid_sha256(value[field], nonzero=True)
            for field in ("configuration_sha256", "report_sha256")
        )
        and all(
            type(value[field]) in (int, float)
            and math.isfinite(value[field])
            and value[field] >= 0.0
            for field in ("pooled_ucb95", "worst_fold_point", "worst_subgroup_ucb95")
        )
        and _valid_ranking_key(value["ranking_key"], trial_id)
        and isinstance(value["fold_digests"], list)
        and len(value["fold_digests"]) == 4
        and all(
            _valid_fold_digest(digest, fold_id, replay=False)
            for digest, fold_id in zip(value["fold_digests"], _FOLD_IDS, strict=True)
        )
        and value["qualification_inventory_sha256"] == qualification_sha256
    )


def _valid_natural_container(raw: bytes, seal: FormalDevelopmentSeal) -> bool:
    try:
        container = _PrivateContainer.model_validate(parse_json_bytes(raw))
        if (
            canonicalize_json(container.model_dump(mode="json")) != raw
            or container.evidence_class != "natural_development"
            or container.file_count != 5
        ):
            return False
        expected_paths = (
            "provisional-winner.json",
            "qualification-report.json",
            "ranking-report.json",
            "replay-report.json",
            "trial-summary.json",
        )
        if tuple(entry.logical_path for entry in container.entries) != expected_paths:
            return False
        documents: dict[str, object] = {}
        for entry in container.entries:
            payload = base64.b64decode(entry.payload_base64, validate=True)
            document = parse_json_bytes(payload)
            if canonicalize_json(document) != payload:
                return False
            documents[entry.logical_path] = document
        common = {
            "canonicalization_version": "RFC8785",
            "evidence_class": "natural_development",
        }
        summary = documents["trial-summary.json"]
        if (
            not _exact_keys(
                summary,
                frozenset(
                    {
                        "schema_version",
                        *common,
                        "selection_fit_count",
                        "selection_folds",
                        "public_trials",
                    }
                ),
            )
            or summary["schema_version"] != "mdcp.natural-trial-summary.v1"
            or any(summary[key] != value for key, value in common.items())
            or summary["selection_fit_count"] != 80
            or not isinstance(summary["selection_folds"], list)
            or len(summary["selection_folds"]) != 80
            or not all(
                _valid_fold_document(
                    document,
                    phase="SELECTION",
                    trial_id=trial_id,
                    fold_id=fold_id,
                )
                for document, (trial_id, fold_id) in zip(
                    summary["selection_folds"],
                    ((trial, fold) for trial in _TRIAL_IDS for fold in _FOLD_IDS),
                    strict=True,
                )
            )
            or summary["public_trials"] != seal.development_result.model_dump(mode="json")["trials"]
        ):
            return False
        qualification = documents["qualification-report.json"]
        if (
            not _exact_keys(
                qualification,
                frozenset(
                    {
                        "schema_version",
                        *common,
                        "qualification_inventory_sha256",
                        "qualifications",
                    }
                ),
            )
            or qualification["schema_version"] != "mdcp.natural-qualification-report.v1"
            or any(qualification[key] != value for key, value in common.items())
            or not isinstance(qualification["qualifications"], list)
            or len(qualification["qualifications"]) != 19
            or qualification["qualification_inventory_sha256"]
            != sha256_hex(canonicalize_json(qualification["qualifications"]))
        ):
            return False
        qualification_sha256 = qualification["qualification_inventory_sha256"]
        qualification_keys = frozenset(
            {
                "trial_id",
                "family_id",
                "configuration_sha256",
                "report_sha256",
                "verdict",
                "qualified",
                "reason_codes",
                "pooled_ucb95",
                "worst_fold_point",
                "worst_subgroup_ucb95",
                "fold_digests",
            }
        )
        for item, trial_id in zip(qualification["qualifications"], _TRIAL_IDS[1:], strict=True):
            if (
                not _exact_keys(item, qualification_keys)
                or item["trial_id"] != trial_id
                or type(item["family_id"]) is not str
                or item["verdict"] not in {"PASS", "FAIL", "UNKNOWN"}
                or type(item["qualified"]) is not bool
                or not isinstance(item["reason_codes"], list)
                or not all(type(reason) is str for reason in item["reason_codes"])
                or not all(
                    value is None or _valid_sha256(value, nonzero=True)
                    for value in (item["configuration_sha256"], item["report_sha256"])
                )
                or not all(
                    value is None
                    or type(value) in (int, float)
                    and math.isfinite(value)
                    and value >= 0.0
                    for value in (
                        item["pooled_ucb95"],
                        item["worst_fold_point"],
                        item["worst_subgroup_ucb95"],
                    )
                )
                or not (
                    item["fold_digests"] is None
                    or isinstance(item["fold_digests"], list)
                    and len(item["fold_digests"]) == 4
                    and all(
                        _valid_fold_digest(digest, fold_id, replay=False)
                        for digest, fold_id in zip(item["fold_digests"], _FOLD_IDS, strict=True)
                    )
                )
            ):
                return False
        ranking = documents["ranking-report.json"]
        ranking_keys = frozenset(
            {
                "schema_version",
                *common,
                "selection_status",
                "reason_codes",
                "retry_allowed",
                "qualification_inventory_sha256",
                "provisional_ranking_key",
            }
        )
        if (
            not _exact_keys(ranking, ranking_keys)
            or ranking["schema_version"] != "mdcp.natural-ranking-report.v1"
            or any(ranking[key] != value for key, value in common.items())
            or ranking["selection_status"] != seal.selection_status
            or not isinstance(ranking["reason_codes"], list)
            or not all(type(reason) is str for reason in ranking["reason_codes"])
            or ranking["retry_allowed"] is not False
            or ranking["qualification_inventory_sha256"] != qualification_sha256
        ):
            return False
        winners = documents["provisional-winner.json"]
        if (
            not _exact_keys(
                winners,
                frozenset(
                    {
                        "schema_version",
                        *common,
                        "provisional_winner",
                        "final_winner",
                    }
                ),
            )
            or winners["schema_version"] != "mdcp.natural-provisional-winner.v1"
            or any(winners[key] != value for key, value in common.items())
        ):
            return False
        provisional = winners["provisional_winner"]
        final = winners["final_winner"]
        if provisional is None:
            if ranking["provisional_ranking_key"] is not None or final is not None:
                return False
        elif (
            not _valid_winner(provisional, qualification_sha256)
            or ranking["provisional_ranking_key"] != provisional["ranking_key"]
            or not (
                final is None or _valid_winner(final, qualification_sha256) and final == provisional
            )
        ):
            return False
        if (seal.selection_status == "PASS") != (final is not None):
            return False
        replay = documents["replay-report.json"]
        if (
            not _exact_keys(
                replay,
                frozenset(
                    {
                        "schema_version",
                        *common,
                        "selection_status",
                        "reason_codes",
                        "replay_trial_id",
                        "replay_folds",
                        "replay_digests",
                    }
                ),
            )
            or replay["schema_version"] != "mdcp.natural-replay-report.v1"
            or any(replay[key] != value for key, value in common.items())
            or replay["selection_status"] != seal.selection_status
            or replay["reason_codes"] != ranking["reason_codes"]
            or not isinstance(replay["replay_folds"], list)
            or not isinstance(replay["replay_digests"], list)
        ):
            return False
        if provisional is None:
            return (
                replay["replay_trial_id"] is None
                and replay["replay_folds"] == []
                and replay["replay_digests"] == []
            )
        trial_id = provisional["trial_id"]
        return bool(
            replay["replay_trial_id"] == trial_id
            and len(replay["replay_folds"]) == 4
            and len(replay["replay_digests"]) == 4
            and all(
                _valid_fold_document(
                    document,
                    phase="REPLAY",
                    trial_id=trial_id,
                    fold_id=fold_id,
                )
                for document, fold_id in zip(replay["replay_folds"], _FOLD_IDS, strict=True)
            )
            and all(
                _valid_fold_digest(digest, fold_id, replay=True)
                for digest, fold_id in zip(replay["replay_digests"], _FOLD_IDS, strict=True)
            )
        )
    except Exception:
        return False


def verify_formal_development_seal(
    consumption_marker_path: Path,
    private_container_path: Path,
    terminal_seal_path: Path,
    *,
    expected_authorization_sha256: str,
    expected_search_receipt_sha256: str,
    expected_source_inventory_sha256: str,
    expected_repository_inventory_sha256: str,
    expected_seal_record_sha256: str,
) -> FormalSealCheck:
    """Read and verify one fully anchored terminal chain without mutation or resume."""
    paths = (consumption_marker_path, private_container_path, terminal_seal_path)
    expectations = (
        expected_authorization_sha256,
        expected_search_receipt_sha256,
        expected_source_inventory_sha256,
        expected_repository_inventory_sha256,
        expected_seal_record_sha256,
    )
    if (
        any(not isinstance(path, Path) or not path.is_absolute() for path in paths)
        or len({str(path) for path in paths}) != 3
        or any(not _valid_sha256(value) for value in expectations)
        or any(value == "0" * 64 for value in expectations[:4])
    ):
        return _seal_check("FAIL", "FORMAL_SEAL_REQUEST_INVALID")
    marker_state, marker_raw = _recovery_leaf(consumption_marker_path, 65_536)
    private_state, private_raw = _recovery_leaf(
        private_container_path, _MAX_PRIVATE_CONTAINER_BYTES
    )
    terminal_state, terminal_raw = _recovery_leaf(terminal_seal_path, 4_194_304)
    if "UNKNOWN" in (marker_state, private_state, terminal_state):
        return _seal_check("UNKNOWN", "FORMAL_SEAL_INSPECTION_UNKNOWN")
    if marker_state == private_state == terminal_state == "ABSENT":
        return _seal_check("FAIL", "FORMAL_SEAL_CHAIN_ABSENT")
    if marker_state == "ABSENT":
        return _seal_check("FAIL", "FORMAL_SEAL_CHAIN_INVALID")
    if marker_raw is None:
        return _seal_check("UNKNOWN", "FORMAL_SEAL_CONSUMPTION_UNKNOWN")
    try:
        marker = FormalRunConsumptionMarker.model_validate(parse_json_bytes(marker_raw))
        if canonicalize_json(marker.model_dump(mode="json")) != marker_raw:
            raise ValueError
    except Exception:
        return _seal_check("UNKNOWN", "FORMAL_SEAL_CONSUMPTION_UNKNOWN")
    if (
        private_state != "PRESENT"
        or private_raw is None
        or terminal_state != "PRESENT"
        or terminal_raw is None
    ):
        return _seal_check("UNKNOWN", "FORMAL_SEAL_INCOMPLETE")
    try:
        seal = FormalDevelopmentSeal.model_validate(parse_json_bytes(terminal_raw))
        if canonicalize_json(seal.model_dump(mode="json")) != terminal_raw:
            raise ValueError
    except Exception:
        return _seal_check("UNKNOWN", "FORMAL_SEAL_INCOMPLETE")
    private_check = _verify_private_container_raw(private_raw, seal.private_identity)
    if (
        private_check.verdict != "PASS"
        or private_check.identity is None
        or not _valid_natural_container(private_raw, seal)
    ):
        return _seal_check("UNKNOWN", "FORMAL_SEAL_INCOMPLETE")
    marker_sha256 = sha256_hex(marker_raw)
    seal_sha256 = sha256_hex(terminal_raw)
    exit_sha256 = sha256_hex(
        canonicalize_json(
            {
                "elapsed_within_budget": True,
                "max_elapsed_ns": 21_600_000_000_000,
                "max_peak_process_bytes": 4_294_967_296,
                "memory_within_budget": True,
                "reason_codes": [],
                "repository_inventory_sha256": seal.repository_inventory_sha256,
                "schema_version": "mdcp.formal-exit-observation.v1",
                "search_freeze_commit": seal.search_freeze_commit,
                "stage": "EXIT",
                "verdict": "PASS",
            }
        )
    )
    if (
        marker.authorization_sha256 != seal.authorization_sha256
        or marker.search_freeze_commit != seal.search_freeze_commit
        or marker.search_receipt_sha256 != seal.search_receipt_sha256
        or marker.protocol_sha256 != seal.protocol_sha256
        or marker.dataset_archive_sha256 != seal.dataset_archive_sha256
        or marker_sha256 != seal.consumption_marker_sha256
        or exit_sha256 != seal.exit_observation_sha256
        or seal.h2_status != "SEALED_NOT_LOADED"
        or seal.h2_loaded_rows != 0
    ):
        return _seal_check("FAIL", "FORMAL_SEAL_CHAIN_INVALID")
    if (
        seal.authorization_sha256 != expected_authorization_sha256
        or seal.search_receipt_sha256 != expected_search_receipt_sha256
        or seal.source_inventory_sha256 != expected_source_inventory_sha256
        or seal.repository_inventory_sha256 != expected_repository_inventory_sha256
        or (expected_seal_record_sha256 != "0" * 64 and seal_sha256 != expected_seal_record_sha256)
    ):
        return _seal_check("FAIL", "FORMAL_SEAL_TRUST_MISMATCH")
    if expected_seal_record_sha256 == "0" * 64:
        return _seal_check("UNKNOWN", "FORMAL_SEAL_UNANCHORED")
    return _seal_check(
        "PASS",
        None,
        private_identity=private_check.identity,
        seal_sha256=seal_sha256,
        repository_sha256=seal.repository_inventory_sha256,
        fit_count=seal.fit_count,
    )


def _windows_private_file_information(
    handle: int,
) -> tuple[int, tuple[int, int, int], int]:
    get_information = ctypes.windll.kernel32.GetFileInformationByHandle
    get_information.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_WindowsFileInformation),
    )
    get_information.restype = wintypes.BOOL
    information = _WindowsFileInformation()
    if not get_information(handle, ctypes.byref(information)):
        raise _PublicationError("PRIVATE_CONTAINER_INVALID")
    return (
        information.dwFileAttributes,
        (
            information.dwVolumeSerialNumber,
            information.nFileIndexHigh,
            information.nFileIndexLow,
        ),
        (int(information.nFileSizeHigh) << 32) | int(information.nFileSizeLow),
    )


def _windows_read_private_file(handle: int, size: int) -> bytes:
    read_file = ctypes.windll.kernel32.ReadFile
    read_file.argtypes = (
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    )
    read_file.restype = wintypes.BOOL
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk_size = min(remaining, 1_048_576)
        buffer = ctypes.create_string_buffer(chunk_size)
        read = wintypes.DWORD()
        if not read_file(
            handle,
            ctypes.byref(buffer),
            chunk_size,
            ctypes.byref(read),
            None,
        ):
            raise _PublicationError("PRIVATE_CONTAINER_INVALID")
        count = int(read.value)
        if count <= 0 or count > chunk_size:
            raise _PublicationError("PRIVATE_CONTAINER_INVALID")
        chunks.append(buffer.raw[:count])
        remaining -= count
    return b"".join(chunks)


def _read_private_container_windows(path: Path) -> bytes:
    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        str(path),
        _WINDOWS_FILE_READ_DATA | _WINDOWS_FILE_READ_ATTRIBUTES,
        _WINDOWS_FILE_SHARE_READ,
        None,
        _WINDOWS_OPEN_EXISTING,
        _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _WINDOWS_INVALID_HANDLE_VALUE:
        raise _PublicationError("PRIVATE_CONTAINER_INVALID")
    owned_handle = int(handle)
    raw: bytes | None = None
    try:
        attributes, identity, size = _windows_private_file_information(owned_handle)
        if (
            attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
            or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise _PublicationError("PRIVATE_CONTAINER_INVALID")
        if size > _MAX_PRIVATE_CONTAINER_BYTES:
            raise _PublicationError("PRIVATE_CONTAINER_SIZE_EXCEEDED")
        raw = _windows_read_private_file(owned_handle, size)
        current_attributes, current_identity, current_size = _windows_private_file_information(
            owned_handle
        )
        if (
            current_attributes != attributes
            or current_identity != identity
            or current_size != size
            or len(raw) != size
        ):
            raise _PublicationError("PRIVATE_CONTAINER_INVALID")
    finally:
        if not _windows_close_read_handle(owned_handle):
            raise _PublicationError("PRIVATE_CONTAINER_INVALID") from None
    if raw is None:
        raise _PublicationError("PRIVATE_CONTAINER_INVALID")
    return raw


def _read_private_container_posix(path: Path) -> bytes:
    no_follow = os.O_NOFOLLOW
    descriptor = os.open(str(path), os.O_RDONLY | no_follow | os.O_NONBLOCK)
    try:
        information = os.fstat(descriptor)
        if not stat.S_ISREG(information.st_mode):
            raise _PublicationError("PRIVATE_CONTAINER_INVALID")
        if information.st_size > _MAX_PRIVATE_CONTAINER_BYTES:
            raise _PublicationError("PRIVATE_CONTAINER_SIZE_EXCEEDED")
        remaining = information.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1_048_576))
            if not chunk:
                raise _PublicationError("PRIVATE_CONTAINER_INVALID")
            chunks.append(chunk)
            remaining -= len(chunk)
        current = os.fstat(descriptor)
        if (
            current.st_dev != information.st_dev
            or current.st_ino != information.st_ino
            or current.st_size != information.st_size
        ):
            raise _PublicationError("PRIVATE_CONTAINER_INVALID")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_private_container_once(path: Path) -> bytes:
    if os.name == "nt":
        return _read_private_container_windows(path)
    return _read_private_container_posix(path)


def _windows_close_read_handle(handle: int) -> bool:
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    return bool(close_handle(handle))
