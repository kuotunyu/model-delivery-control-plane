"""Closed public development receipts and synthetic private evidence publication."""

from __future__ import annotations

import ctypes
import json
import math
import os
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
_WINDOWS_FILE_APPEND_DATA = 0x00000004
_WINDOWS_FILE_ADD_FILE = 0x00000002
_WINDOWS_FILE_ADD_SUBDIRECTORY = 0x00000004
_WINDOWS_FILE_TRAVERSE = 0x00000020
_WINDOWS_FILE_READ_ATTRIBUTES = 0x00000080
_WINDOWS_FILE_WRITE_ATTRIBUTES = 0x00000100
_WINDOWS_GENERIC_WRITE = 0x40000000
_WINDOWS_FILE_SHARE_READ_WRITE = 0x00000003
_WINDOWS_FILE_SHARE_ALL = 0x00000007
_WINDOWS_CREATE_NEW = 1
_WINDOWS_OPEN_EXISTING = 3
_WINDOWS_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_WINDOWS_FILE_ATTRIBUTE_NORMAL = 0x00000080
_WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_WINDOWS_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_WINDOWS_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_WINDOWS_FILE_RENAME_INFO = 3
_WINDOWS_FILE_DISPOSITION_INFO = 4
_WINDOWS_ERROR_ACCESS_DENIED = 5
_WINDOWS_ERROR_FILE_NOT_FOUND = 2
_WINDOWS_ERROR_PATH_NOT_FOUND = 3
_WINDOWS_ERROR_FILE_EXISTS = 80
_WINDOWS_ERROR_ALREADY_EXISTS = 183
_WINDOWS_OBJECT_CASE_INSENSITIVE = 0x00000040
_WINDOWS_FILE_OPEN = 1
_WINDOWS_FILE_CREATE = 2
_WINDOWS_FILE_DIRECTORY_FILE = 0x00000001
_WINDOWS_FILE_WRITE_THROUGH = 0x00000002
_WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
_WINDOWS_FILE_NON_DIRECTORY_FILE = 0x00000040
_WINDOWS_STATUS_OBJECT_NAME_NOT_FOUND = -1073741772
_WINDOWS_STATUS_OBJECT_NAME_COLLISION = -1073741771


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


class _WindowsRenameInformation(ctypes.Structure):
    _fields_ = (
        ("ReplaceIfExists", wintypes.BOOL),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", wintypes.DWORD),
        ("FileName", wintypes.WCHAR * 1),
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
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or path.is_absolute()
            or any(part in ("", ".", "..") for part in path.parts)
            or any(_is_windows_alias_component(part) for part in path.parts)
            or path.as_posix() != value
        ):
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
    root: Path, bundle: PrivateRunBundle
) -> PrivateBundleIdentity:
    """Atomically publish a private synthetic bundle under an already trusted parent."""
    if type(bundle) is not PrivateRunBundle:
        raise _PublicationError("PRIVATE_BUNDLE_INVALID")
    if bundle.evidence_class != "synthetic_test":
        raise _PublicationError("FORMAL_RUN_PERMIT_REQUIRED")
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
    try:
        destination = _absolute_destination(root)
        platform = _publication_platform()
        if platform == "nt":
            _publish_windows_bundle(destination, files, manifest)
        elif platform == "posix":
            _publish_posix_bundle(destination, files, manifest)
        else:
            raise _PublicationError("PUBLICATION_FAILED")
    except _PublicationError:
        raise
    except Exception:
        raise _PublicationError("PUBLICATION_FAILED") from None
    return PrivateBundleIdentity(
        file_count=len(files),
        total_bytes=sum(len(item.canonical_bytes) for item in files),
        inventory_sha256=inventory_sha256,
        manifest_sha256=manifest_sha256,
    )


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


def _absolute_destination(root: Path) -> Path:
    if (
        not isinstance(root, Path)
        or root.name in ("", ".", "..")
        or _is_windows_alias_component(root.name)
    ):
        raise _PublicationError("TRUSTED_PARENT_REQUIRED")
    return Path(os.path.abspath(os.fspath(root)))


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
        except Exception:
            raise _PublicationError("NONCANONICAL_PRIVATE_BYTES") from None
    return files


def _publish_posix_bundle(
    destination: Path,
    files: tuple[PrivateFoldEvidence, ...],
    manifest: bytes,
) -> None:
    del destination, files, manifest
    raise _PublicationError("PUBLICATION_UNSUPPORTED") from None


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


def _windows_directory_information(handle: int) -> tuple[int, tuple[int, int, int]]:
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


def _windows_nt_relative_file(
    parent_handle: int,
    name: str,
    is_directory: bool,
    share_mode: int,
    create_disposition: int,
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
    desired_access = (
        _WINDOWS_SYNCHRONIZE
        | _WINDOWS_DELETE
        | _WINDOWS_FILE_READ_ATTRIBUTES
        | _WINDOWS_FILE_WRITE_ATTRIBUTES
    )
    if is_directory:
        desired_access |= (
            _WINDOWS_FILE_LIST_DIRECTORY
            | _WINDOWS_FILE_ADD_FILE
            | _WINDOWS_FILE_ADD_SUBDIRECTORY
            | _WINDOWS_FILE_TRAVERSE
        )
    else:
        desired_access |= _WINDOWS_FILE_WRITE_DATA | _WINDOWS_FILE_APPEND_DATA
    create_options = _WINDOWS_FILE_WRITE_THROUGH | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT
    create_options |= (
        _WINDOWS_FILE_DIRECTORY_FILE if is_directory else _WINDOWS_FILE_NON_DIRECTORY_FILE
    )
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
    handle = int(output_handle.value)
    try:
        file_attributes, identity = _windows_directory_information(handle)
        if bool(file_attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY) != is_directory:
            raise _PublicationError("PUBLICATION_FAILED")
        if file_attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT:
            raise _PublicationError("PUBLICATION_FAILED")
        return handle, identity, 0
    except Exception:
        _windows_close(handle)
        raise


def _windows_nt_create_relative(
    parent_handle: int,
    name: str,
    is_directory: bool,
    share_mode: int,
) -> tuple[int | None, tuple[int, int, int] | None, int]:
    return _windows_nt_relative_file(
        parent_handle,
        name,
        is_directory,
        share_mode,
        _WINDOWS_FILE_CREATE,
    )


def _windows_nt_open_relative(
    parent_handle: int,
    name: str,
    is_directory: bool,
) -> tuple[int | None, tuple[int, int, int] | None, int]:
    return _windows_nt_relative_file(
        parent_handle,
        name,
        is_directory,
        _WINDOWS_FILE_SHARE_ALL,
        _WINDOWS_FILE_OPEN,
    )


def _windows_open_directory(
    path: Path,
    desired_access: int,
) -> tuple[int | None, tuple[int, int, int] | None, int]:
    handle, error = _windows_create_file(
        path,
        desired_access,
        _WINDOWS_OPEN_EXISTING,
        _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS | _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT,
    )
    if handle is None:
        return None, None, error
    try:
        attributes, identity = _windows_directory_information(handle)
        if not attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY:
            _windows_close(handle)
            return None, None, _WINDOWS_ERROR_ACCESS_DENIED
        if attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT:
            _windows_close(handle)
            return None, None, _WINDOWS_ERROR_ACCESS_DENIED
        return handle, identity, 0
    except Exception:
        _windows_close(handle)
        raise


def _windows_ancestor_paths(parent: Path) -> tuple[Path, ...]:
    parts = parent.parts
    if not parts or not parent.anchor:
        raise _PublicationError("TRUSTED_PARENT_REQUIRED")
    current = Path(parts[0])
    result = [current]
    for component in parts[1:]:
        current = current / component
        result.append(current)
    return tuple(result)


def _windows_open_trusted_ancestors(
    parent: Path,
) -> list[tuple[Path, int, tuple[int, int, int]]]:
    records: list[tuple[Path, int, tuple[int, int, int]]] = []
    try:
        paths = _windows_ancestor_paths(parent)
        for index, path in enumerate(paths):
            access = _WINDOWS_FILE_READ_ATTRIBUTES
            if index == len(paths) - 1:
                access |= _WINDOWS_GENERIC_WRITE
            handle, identity, _ = _windows_open_directory(path, access)
            if handle is None or identity is None:
                raise _PublicationError("TRUSTED_PARENT_REQUIRED")
            records.append((path, handle, identity))
        return records
    except Exception:
        for _, handle, _ in reversed(records):
            _windows_close(handle)
        raise


def _windows_revalidate_ancestors(
    records: list[tuple[Path, int, tuple[int, int, int]]],
) -> None:
    for path, _, expected_identity in records:
        probe, identity, _ = _windows_open_directory(path, _WINDOWS_FILE_READ_ATTRIBUTES)
        if probe is None or identity != expected_identity:
            if probe is not None:
                _windows_close(probe)
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        _windows_close(probe)


def _windows_require_destination_absent(destination: Path) -> None:
    handle, _, error = _windows_open_directory(destination, _WINDOWS_FILE_READ_ATTRIBUTES)
    if handle is not None:
        _windows_close(handle)
        raise _PublicationError("DESTINATION_EXISTS")
    if error in (_WINDOWS_ERROR_FILE_NOT_FOUND, _WINDOWS_ERROR_PATH_NOT_FOUND):
        return
    raise _PublicationError("DESTINATION_EXISTS")


def _windows_flush(handle: int) -> None:
    flush_file_buffers = ctypes.windll.kernel32.FlushFileBuffers
    flush_file_buffers.argtypes = (wintypes.HANDLE,)
    flush_file_buffers.restype = wintypes.BOOL
    if not flush_file_buffers(handle):
        raise _PublicationError("PUBLICATION_FAILED")


def _windows_write_file(
    parent_handle: int,
    name: str,
    logical_components: tuple[str, ...],
    content: bytes,
    created_entries: list[tuple[tuple[str, ...], bool, tuple[int, int, int]]],
    file_handles: list[int],
) -> None:
    handle, identity, _ = _windows_nt_create_relative(
        parent_handle,
        name,
        False,
        _WINDOWS_FILE_SHARE_READ_WRITE,
    )
    if handle is None or identity is None:
        raise _PublicationError("PUBLICATION_FAILED")
    created_entries.append((logical_components, False, identity))
    sealed = False
    try:
        write_file = ctypes.windll.kernel32.WriteFile
        write_file.argtypes = (
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        )
        write_file.restype = wintypes.BOOL
        offset = 0
        while offset < len(content):
            chunk = content[offset : offset + 1_048_576]
            buffer = ctypes.create_string_buffer(chunk, len(chunk))
            written = wintypes.DWORD()
            if not write_file(
                handle,
                ctypes.byref(buffer),
                len(chunk),
                ctypes.byref(written),
                None,
            ) or written.value != len(chunk):
                raise _PublicationError("PUBLICATION_FAILED")
            offset += written.value
        _windows_flush(handle)
        sealed = True
    finally:
        if not sealed:
            _windows_close(handle)
    file_handles.append(handle)


def _windows_write_layout(
    staging_handle: int,
    files: tuple[PrivateFoldEvidence, ...],
    manifest: bytes,
    created_entries: list[tuple[tuple[str, ...], bool, tuple[int, int, int]]],
    directory_handles: list[int],
    file_handles: list[int],
) -> None:
    directories: dict[tuple[str, ...], int] = {(): staging_handle}
    for item in files:
        parts = PurePosixPath(item.logical_path).parts
        prefix: tuple[str, ...] = ()
        for component in parts[:-1]:
            parent_handle = directories[prefix]
            prefix = (*prefix, component)
            if prefix not in directories:
                handle, identity, _ = _windows_nt_create_relative(
                    parent_handle,
                    component,
                    True,
                    _WINDOWS_FILE_SHARE_READ_WRITE,
                )
                if handle is None or identity is None:
                    raise _PublicationError("PUBLICATION_FAILED")
                created_entries.append((prefix, True, identity))
                directory_handles.append(handle)
                directories[prefix] = handle
                _windows_flush(parent_handle)
        parent_handle = directories[prefix]
        _windows_write_file(
            parent_handle,
            parts[-1],
            parts,
            item.canonical_bytes,
            created_entries,
            file_handles,
        )
        _windows_flush(parent_handle)
    _windows_write_file(
        staging_handle,
        "manifest.json",
        ("manifest.json",),
        manifest,
        created_entries,
        file_handles,
    )
    _windows_flush(staging_handle)
    for handle in reversed(directory_handles):
        _windows_flush(handle)
    _windows_flush(staging_handle)


def _windows_rename_noreplace(staging_handle: int, destination: Path) -> None:
    encoded_name = str(destination).encode("utf-16-le")
    buffer_size = _WindowsRenameInformation.FileName.offset + len(encoded_name) + 2
    buffer = ctypes.create_string_buffer(buffer_size)
    information = _WindowsRenameInformation.from_buffer(buffer)
    information.ReplaceIfExists = False
    information.RootDirectory = None
    information.FileNameLength = len(encoded_name)
    ctypes.memmove(
        ctypes.addressof(buffer) + _WindowsRenameInformation.FileName.offset,
        encoded_name,
        len(encoded_name),
    )
    set_information = ctypes.windll.kernel32.SetFileInformationByHandle
    set_information.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    set_information.restype = wintypes.BOOL
    if set_information(
        staging_handle,
        _WINDOWS_FILE_RENAME_INFO,
        ctypes.byref(buffer),
        buffer_size,
    ):
        return
    error = _windows_last_error()
    if error in (_WINDOWS_ERROR_FILE_EXISTS, _WINDOWS_ERROR_ALREADY_EXISTS):
        raise _PublicationError("DESTINATION_EXISTS") from None
    raise _PublicationError("PUBLICATION_FAILED") from None


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


def _windows_open_verified_layout(
    staging_handle: int,
    created_entries: list[tuple[tuple[str, ...], bool, tuple[int, int, int]]],
) -> tuple[list[tuple[tuple[str, ...], int]], list[int]]:
    directories: dict[tuple[str, ...], int] = {(): staging_handle}
    opened_directories: list[tuple[tuple[str, ...], int]] = []
    opened_files: list[int] = []
    try:
        for components, is_directory, expected_identity in created_entries:
            parent_handle = directories[components[:-1]]
            handle, identity, _ = _windows_nt_open_relative(
                parent_handle,
                components[-1],
                is_directory,
            )
            if handle is None or identity != expected_identity:
                if handle is not None:
                    _windows_close(handle)
                raise _PublicationError("PUBLICATION_FAILED")
            if is_directory:
                directories[components] = handle
                opened_directories.append((components, handle))
            else:
                opened_files.append(handle)
        return opened_directories, opened_files
    except Exception:
        for handle in opened_files:
            _windows_close(handle)
        for _, handle in reversed(opened_directories):
            _windows_close(handle)
        raise


def _windows_verify_owned_layout(
    staging_handle: int,
    created_entries: list[tuple[tuple[str, ...], bool, tuple[int, int, int]]],
) -> None:
    opened_directories, opened_files = _windows_open_verified_layout(
        staging_handle,
        created_entries,
    )
    for handle in opened_files:
        _windows_close(handle)
    for _, handle in reversed(opened_directories):
        _windows_close(handle)


def _cleanup_windows_staging(
    staging_handle: int,
    created_entries: list[tuple[tuple[str, ...], bool, tuple[int, int, int]]],
) -> None:
    opened_directories, opened_files = _windows_open_verified_layout(
        staging_handle,
        created_entries,
    )
    try:
        while opened_files:
            handle = opened_files.pop(0)
            if not _windows_set_delete_disposition(handle):
                _windows_close(handle)
                raise _PublicationError("PUBLICATION_FAILED")
            _windows_close(handle)
        while opened_directories:
            _, handle = opened_directories.pop()
            if not _windows_set_delete_disposition(handle):
                _windows_close(handle)
                raise _PublicationError("PUBLICATION_FAILED")
            _windows_close(handle)
        if not _windows_set_delete_disposition(staging_handle):
            raise _PublicationError("PUBLICATION_FAILED")
    finally:
        for handle in opened_files:
            _windows_close(handle)
        for _, handle in reversed(opened_directories):
            _windows_close(handle)


def _windows_require_staging_absent(parent_handle: int, staging_name: str) -> None:
    handle, _, status = _windows_nt_open_relative(parent_handle, staging_name, True)
    if handle is not None:
        _windows_close(handle)
        raise _PublicationError("PUBLICATION_FAILED")
    if status != _WINDOWS_STATUS_OBJECT_NAME_NOT_FOUND:
        raise _PublicationError("PUBLICATION_FAILED")


def _publish_windows_bundle(
    destination: Path,
    files: tuple[PrivateFoldEvidence, ...],
    manifest: bytes,
) -> None:
    ancestors = _windows_open_trusted_ancestors(destination.parent)
    parent_handle = ancestors[-1][1]
    staging_name = f".{destination.name}.staging"
    staging_handle: int | None = None
    created_entries: list[tuple[tuple[str, ...], bool, tuple[int, int, int]]] = []
    directory_handles: list[int] = []
    file_handles: list[int] = []
    published = False
    cleanup_failed = False
    try:
        _windows_require_destination_absent(destination)
        staging_handle, identity, status = _windows_nt_create_relative(
            parent_handle,
            staging_name,
            True,
            _WINDOWS_FILE_SHARE_READ_WRITE,
        )
        if staging_handle is None or identity is None:
            if status == _WINDOWS_STATUS_OBJECT_NAME_COLLISION:
                raise _PublicationError("STAGING_EXISTS")
            raise _PublicationError("PUBLICATION_FAILED")
        _windows_flush(parent_handle)
        _windows_write_layout(
            staging_handle,
            files,
            manifest,
            created_entries,
            directory_handles,
            file_handles,
        )
        for handle in reversed(file_handles):
            _windows_close(handle)
        file_handles.clear()
        for handle in reversed(directory_handles):
            _windows_close(handle)
        directory_handles.clear()
        _windows_verify_owned_layout(staging_handle, created_entries)
        _windows_revalidate_ancestors(ancestors)
        attributes, current_identity = _windows_directory_information(staging_handle)
        if attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT or current_identity != identity:
            raise _PublicationError("PUBLICATION_FAILED")
        _windows_rename_noreplace(staging_handle, destination)
        published = True
        _windows_flush(parent_handle)
    except _PublicationError:
        raise
    except Exception:
        raise _PublicationError("PUBLICATION_FAILED") from None
    finally:
        for handle in reversed(file_handles):
            _windows_close(handle)
        for handle in reversed(directory_handles):
            _windows_close(handle)
        if staging_handle is not None:
            if not published:
                try:
                    _cleanup_windows_staging(staging_handle, created_entries)
                except Exception:
                    cleanup_failed = True
            _windows_close(staging_handle)
            if not published:
                try:
                    _windows_flush(parent_handle)
                except Exception:
                    cleanup_failed = True
                try:
                    _windows_require_staging_absent(parent_handle, staging_name)
                except Exception:
                    cleanup_failed = True
        for _, handle, _ in reversed(ancestors):
            _windows_close(handle)
        if cleanup_failed:
            raise _PublicationError("PUBLICATION_FAILED") from None
