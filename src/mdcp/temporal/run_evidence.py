"""Closed public development receipts and synthetic private evidence publication."""

from __future__ import annotations

import base64
import ctypes
import json
import math
import os
import unicodedata
from ctypes import wintypes
from pathlib import Path, PurePosixPath
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
_WINDOWS_FILE_WRITE_DATA = 0x00000002
_WINDOWS_FILE_ADD_FILE = 0x00000002
_WINDOWS_FILE_TRAVERSE = 0x00000020
_WINDOWS_FILE_READ_ATTRIBUTES = 0x00000080
_WINDOWS_FILE_SHARE_READ_WRITE = 0x00000003
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

    @field_validator("logical_path")
    @classmethod
    def _canonical_logical_path(cls, value: str) -> str:
        if not _is_canonical_logical_path(value):
            raise ValueError("LOGICAL_PATH_INVALID")
        return value


class PrivateRunBundle(BaseModel):
    """Private logical files for a synthetic run only."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    evidence_class: Literal["synthetic_test", "natural_development"]
    files: tuple[PrivateFoldEvidence, ...]


class PrivateBundleIdentity(BaseModel):
    """The deliberately narrow public identity of private published files."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    file_count: StrictInt
    total_bytes: StrictInt
    inventory_sha256: Sha256
    manifest_sha256: Sha256

    @field_validator("file_count", "total_bytes")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("IDENTITY_COUNT_INVALID")
        return value


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
    destination: Path, bundle: PrivateRunBundle
) -> PrivateBundleIdentity:
    """Publish one canonical synthetic container without clobbering a destination."""
    if type(bundle) is not PrivateRunBundle:
        raise _PublicationError("PRIVATE_BUNDLE_INVALID")
    if bundle.evidence_class != "synthetic_test":
        raise _PublicationError("FORMAL_RUN_PERMIT_REQUIRED")
    container_bytes, identity = _canonical_private_container(bundle)
    if _publication_platform() != "nt":
        raise _PublicationError("PUBLICATION_UNSUPPORTED")
    try:
        checked_destination = _absolute_destination(destination)
        _publish_windows_container(checked_destination, container_bytes)
    except _PublicationError:
        raise
    except Exception:
        raise _PublicationError("PUBLICATION_FAILED") from None
    return identity


def _publication_platform() -> str:
    return os.name


def _checked_in_schema() -> object:
    try:
        return json.loads(
            Path("schemas/v2/development-result-index.schema.json").read_text(encoding="utf-8")
        )
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
        if type(item.canonical_bytes) is not bytes:
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
) -> tuple[bytes, PrivateBundleIdentity]:
    """Build and validate the sole deterministic physical private artifact."""
    if type(bundle) is not PrivateRunBundle:
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


def verify_private_container(
    path: Path, expected_identity: PrivateBundleIdentity
) -> PrivateContainerCheck:
    """Verify one regular canonical container against its narrow public identity."""
    if not isinstance(path, Path) or type(expected_identity) is not PrivateBundleIdentity:
        return _private_container_failure("PRIVATE_CONTAINER_INVALID")
    try:
        if path.is_symlink() or not path.is_file():
            return _private_container_failure("PRIVATE_CONTAINER_INVALID")
        file_size = path.stat().st_size
        if file_size > _MAX_PRIVATE_CONTAINER_BYTES:
            return _private_container_failure("PRIVATE_CONTAINER_SIZE_EXCEEDED")
        raw = path.read_bytes()
        if len(raw) != file_size:
            return _private_container_failure("PRIVATE_CONTAINER_INVALID")
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
            try:
                payload = base64.b64decode(entry.payload_base64, validate=True)
            except Exception:
                return _private_container_failure("PRIVATE_CONTAINER_INVALID")
            if base64.b64encode(payload).decode("ascii") != entry.payload_base64:
                return _private_container_failure("PRIVATE_CONTAINER_INVALID")
            if len(payload) > _MAX_PRIVATE_PAYLOAD_BYTES:
                return _private_container_failure("PRIVATE_CONTAINER_SIZE_EXCEEDED")
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
    except Exception:
        return _private_container_failure("PRIVATE_CONTAINER_INVALID")
    return PrivateContainerCheck(verdict="PASS", reason_codes=(), identity=identity)


def _absolute_destination(destination: Path) -> Path:
    if not isinstance(destination, Path):
        raise _PublicationError("TRUSTED_PARENT_REQUIRED")
    value = str(destination)
    if (
        not value
        or unicodedata.normalize("NFC", value) != value
        or value.startswith("\\\\")
        or not destination.is_absolute()
        or len(destination.drive) != 2
        or destination.drive[1:] != ":"
        or not destination.drive[0].isalpha()
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
            or unicodedata.normalize("NFC", component) != component
        ):
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
    return destination


def _windows_last_error() -> int:
    get_last_error = ctypes.windll.kernel32.GetLastError
    get_last_error.argtypes = ()
    get_last_error.restype = wintypes.DWORD
    return int(get_last_error())


def _windows_close(handle: int) -> None:
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    close_handle(handle)


def _windows_create_file(
    path: Path,
    desired_access: int,
    creation_disposition: int,
    flags: int,
) -> tuple[int | None, int]:
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
    get_information = ctypes.windll.kernel32.GetFileInformationByHandle
    get_information.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_WindowsFileInformation),
    )
    get_information.restype = wintypes.BOOL
    information = _WindowsFileInformation()
    if not get_information(handle, ctypes.byref(information)):
        raise _PublicationError("PUBLICATION_FAILED")
    return information.dwFileAttributes, (
        information.dwVolumeSerialNumber,
        information.nFileIndexHigh,
        information.nFileIndexLow,
    )


def _windows_normalized_handle_name(handle: int) -> str:
    get_name = ctypes.windll.kernel32.GetFinalPathNameByHandleW
    get_name.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    get_name.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    length = int(get_name(handle, buffer, len(buffer), 0))
    if length == 0 or length >= len(buffer):
        raise _PublicationError("PUBLICATION_FAILED")
    value = buffer.value
    if value.startswith("\\\\?\\"):
        value = value[4:]
    return unicodedata.normalize("NFC", value)


def _windows_names_equal(left: str, right: str) -> bool:
    compare = ctypes.windll.kernel32.CompareStringOrdinal
    compare.argtypes = (
        wintypes.LPCWSTR,
        ctypes.c_int,
        wintypes.LPCWSTR,
        ctypes.c_int,
        wintypes.BOOL,
    )
    compare.restype = ctypes.c_int
    return int(compare(left, -1, right, -1, True)) == 2


def _windows_nt_relative_file(
    parent_handle: int,
    name: str,
    is_directory: bool,
    desired_access: int,
    share_mode: int,
    create_disposition: int,
    create_options: int,
) -> tuple[int | None, tuple[int, int, int] | None, int]:
    name_buffer = ctypes.create_unicode_buffer(name)
    name_length = len(name.encode("utf-16-le"))
    unicode_name = _WindowsUnicodeString(
        Length=name_length,
        MaximumLength=name_length + 2,
        Buffer=ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attributes = _WindowsObjectAttributes(
        Length=ctypes.sizeof(_WindowsObjectAttributes),
        RootDirectory=parent_handle,
        ObjectName=ctypes.pointer(unicode_name),
        Attributes=_WINDOWS_OBJECT_CASE_INSENSITIVE,
        SecurityDescriptor=None,
        SecurityQualityOfService=None,
    )
    io_status = _WindowsIoStatusBlock()
    output_handle = wintypes.HANDLE()
    nt_create_file = ctypes.windll.ntdll.NtCreateFile
    nt_create_file.argtypes = (
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.ULONG,
        ctypes.POINTER(_WindowsObjectAttributes),
        ctypes.POINTER(_WindowsIoStatusBlock),
        ctypes.c_void_p,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
    )
    nt_create_file.restype = wintypes.LONG
    status = int(
        nt_create_file(
            ctypes.byref(output_handle),
            desired_access,
            ctypes.byref(attributes),
            ctypes.byref(io_status),
            None,
            _WINDOWS_FILE_ATTRIBUTE_NORMAL,
            share_mode,
            create_disposition,
            create_options,
            None,
            0,
        )
    )
    if status < 0:
        return None, None, status
    return int(output_handle.value), None, 0


def _windows_open_trusted_ancestors(
    destination: Path,
) -> list[tuple[int, tuple[int, int, int], str]]:
    records: list[tuple[int, tuple[int, int, int], str]] = []
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
            Path(expected),
            ancestor_access | (_WINDOWS_FILE_ADD_FILE if len(destination.parts) == 2 else 0),
            _WINDOWS_OPEN_EXISTING,
            _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT | _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS,
        )
        if root_handle is None:
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        try:
            attributes, root_identity = _windows_file_information(root_handle)
        except _PublicationError:
            _windows_close(root_handle)
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
            expected = str(Path(expected) / component)
            try:
                handle, _, _ = _windows_nt_relative_file(
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
            if handle is None:
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
            try:
                attributes, identity = _windows_file_information(handle)
            except _PublicationError:
                _windows_close(handle)
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
    except Exception:
        for handle, _, _ in reversed(records):
            _windows_close(handle)
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


def _windows_flush(handle: int) -> None:
    flush_file_buffers = ctypes.windll.kernel32.FlushFileBuffers
    flush_file_buffers.argtypes = (wintypes.HANDLE,)
    flush_file_buffers.restype = wintypes.BOOL
    if not flush_file_buffers(handle):
        raise _PublicationError("PUBLICATION_FAILED")


def _windows_write_chunk(handle: int, content: bytes) -> int:
    write_file = ctypes.windll.kernel32.WriteFile
    write_file.argtypes = (
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    )
    write_file.restype = wintypes.BOOL
    buffer = ctypes.create_string_buffer(content, len(content))
    written = wintypes.DWORD()
    if not write_file(
        handle,
        ctypes.byref(buffer),
        len(content),
        ctypes.byref(written),
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
    set_information = ctypes.windll.kernel32.SetFileInformationByHandle
    set_information.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    set_information.restype = wintypes.BOOL
    return bool(
        set_information(
            handle,
            _WINDOWS_FILE_DISPOSITION_INFO,
            ctypes.byref(information),
            ctypes.sizeof(information),
        )
    )


def _publish_windows_container(destination: Path, content: bytes) -> None:
    ancestors = _windows_open_trusted_ancestors(destination)
    parent_handle = ancestors[-1][0]
    final_handle: int | None = None
    published = False
    cleanup_failed = False
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
        final_handle, _, status = _windows_nt_relative_file(
            parent_handle,
            destination.name,
            False,
            final_access,
            0,
            _WINDOWS_FILE_CREATE,
            final_options,
        )
        if final_handle is None:
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
        _windows_flush(parent_handle)
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
            _windows_close(final_handle)
        for handle, _, _ in reversed(ancestors):
            _windows_close(handle)
    if cleanup_failed:
        raise _PublicationError("PUBLICATION_FAILED") from None
    if error is not None:
        raise error
