"""Closed public development receipts and synthetic private evidence publication."""

from __future__ import annotations

import ctypes
import errno
import json
import math
import os
import stat
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
_RENAME_NOREPLACE = 1

_WINDOWS_DELETE = 0x00010000
_WINDOWS_FILE_READ_ATTRIBUTES = 0x00000080
_WINDOWS_GENERIC_WRITE = 0x40000000
_WINDOWS_FILE_SHARE_READ_WRITE = 0x00000003
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
        if os.name == "nt":
            _publish_windows_bundle(destination, files, manifest)
        elif os.name == "posix":
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


def _posix_directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _open_posix_trusted_parent(parent: Path) -> int:
    current = -1
    try:
        parts = parent.parts
        if not parts or parts[0] != "/":
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
        current = os.open("/", _posix_directory_flags())
        for component in parts[1:]:
            following = os.open(component, _posix_directory_flags(), dir_fd=current)
            os.close(current)
            current = following
        return current
    except _PublicationError:
        if current >= 0:
            os.close(current)
        raise
    except OSError:
        if current >= 0:
            os.close(current)
        raise _PublicationError("TRUSTED_PARENT_REQUIRED") from None


def _posix_require_absent(directory: int, name: str, code: str) -> None:
    try:
        os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError:
        raise _PublicationError("PUBLICATION_FAILED") from None
    raise _PublicationError(code) from None


def _posix_identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _posix_open_owned_staging(parent: int, name: str) -> tuple[int, tuple[int, int]]:
    descriptor = -1
    try:
        descriptor = os.open(name, _posix_directory_flags(), dir_fd=parent)
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(named.st_mode)
            or _posix_identity(opened) != _posix_identity(named)
        ):
            raise _PublicationError("PUBLICATION_FAILED")
        return descriptor, _posix_identity(opened)
    except _PublicationError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError:
        if descriptor >= 0:
            os.close(descriptor)
        raise _PublicationError("PUBLICATION_FAILED") from None


def _posix_write_file(directory: int, name: str, content: bytes) -> None:
    descriptor = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=directory,
    )
    try:
        offset = 0
        while offset < len(content):
            written = os.write(descriptor, content[offset:])
            if written <= 0:
                raise OSError
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(directory)


def _posix_write_layout(
    staging: int,
    files: tuple[PrivateFoldEvidence, ...],
    manifest: bytes,
) -> None:
    directories: dict[tuple[str, ...], int] = {(): staging}
    opened: list[int] = []
    try:
        for item in files:
            parts = PurePosixPath(item.logical_path).parts
            prefix: tuple[str, ...] = ()
            for component in parts[:-1]:
                parent = directories[prefix]
                prefix = (*prefix, component)
                if prefix not in directories:
                    os.mkdir(component, 0o700, dir_fd=parent)
                    os.fsync(parent)
                    descriptor = os.open(component, _posix_directory_flags(), dir_fd=parent)
                    directories[prefix] = descriptor
                    opened.append(descriptor)
            _posix_write_file(directories[prefix], parts[-1], item.canonical_bytes)
        _posix_write_file(staging, "manifest.json", manifest)
        for descriptor in reversed(opened):
            os.fsync(descriptor)
        os.fsync(staging)
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


def _load_posix_renameat2() -> object:
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        return renameat2
    except (AttributeError, OSError):
        raise _PublicationError("PUBLICATION_FAILED") from None


def _posix_rename_noreplace(
    old_directory: int,
    old_name: str,
    new_directory: int,
    new_name: str,
) -> None:
    renameat2 = _load_posix_renameat2()
    result = renameat2(
        old_directory,
        os.fsencode(old_name),
        new_directory,
        os.fsencode(new_name),
        _RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in (errno.EEXIST, errno.ENOTEMPTY):
        raise _PublicationError("DESTINATION_EXISTS") from None
    raise _PublicationError("PUBLICATION_FAILED") from None


def _posix_clear_directory(directory: int) -> None:
    for name in os.listdir(directory):
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if stat.S_ISDIR(named.st_mode):
            child = os.open(name, _posix_directory_flags(), dir_fd=directory)
            try:
                if _posix_identity(os.fstat(child)) != _posix_identity(named):
                    raise OSError
                _posix_clear_directory(child)
            finally:
                os.close(child)
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if _posix_identity(current) != _posix_identity(named):
                raise OSError
            os.rmdir(name, dir_fd=directory)
        else:
            os.unlink(name, dir_fd=directory)
    os.fsync(directory)


def _cleanup_posix_staging(
    parent: int,
    name: str,
    identity: tuple[int, int],
) -> None:
    try:
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(named.st_mode) or _posix_identity(named) != identity:
            return
        staging = os.open(name, _posix_directory_flags(), dir_fd=parent)
        try:
            if _posix_identity(os.fstat(staging)) != identity:
                return
            _posix_clear_directory(staging)
        finally:
            os.close(staging)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if _posix_identity(current) != identity:
            return
        os.rmdir(name, dir_fd=parent)
        os.fsync(parent)
    except OSError:
        return


def _publish_posix_bundle(
    destination: Path,
    files: tuple[PrivateFoldEvidence, ...],
    manifest: bytes,
) -> None:
    parent = _open_posix_trusted_parent(destination.parent)
    staging_name = f".{destination.name}.staging"
    staging = -1
    staging_identity: tuple[int, int] | None = None
    published = False
    try:
        _posix_require_absent(parent, destination.name, "DESTINATION_EXISTS")
        try:
            os.mkdir(staging_name, 0o700, dir_fd=parent)
        except FileExistsError:
            raise _PublicationError("STAGING_EXISTS") from None
        os.fsync(parent)
        staging, staging_identity = _posix_open_owned_staging(parent, staging_name)
        _posix_write_layout(staging, files, manifest)
        current = os.stat(staging_name, dir_fd=parent, follow_symlinks=False)
        if _posix_identity(current) != staging_identity:
            raise _PublicationError("PUBLICATION_FAILED")
        _posix_rename_noreplace(parent, staging_name, parent, destination.name)
        published = True
        os.fsync(parent)
    except _PublicationError:
        raise
    except OSError:
        raise _PublicationError("PUBLICATION_FAILED") from None
    finally:
        if staging >= 0:
            os.close(staging)
        if not published and staging_identity is not None:
            _cleanup_posix_staging(parent, staging_name, staging_identity)
        os.close(parent)


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


def _windows_create_directory(path: Path) -> tuple[bool, int]:
    create_directory = ctypes.windll.kernel32.CreateDirectoryW
    create_directory.argtypes = (wintypes.LPCWSTR, ctypes.c_void_p)
    create_directory.restype = wintypes.BOOL
    if create_directory(str(path), None):
        return True, 0
    return False, _windows_last_error()


def _windows_flush(handle: int) -> None:
    flush_file_buffers = ctypes.windll.kernel32.FlushFileBuffers
    flush_file_buffers.argtypes = (wintypes.HANDLE,)
    flush_file_buffers.restype = wintypes.BOOL
    if not flush_file_buffers(handle):
        raise _PublicationError("PUBLICATION_FAILED")


def _windows_write_file(path: Path, content: bytes, created_files: list[Path]) -> None:
    handle, _ = _windows_create_file(
        path,
        _WINDOWS_GENERIC_WRITE,
        _WINDOWS_CREATE_NEW,
        _WINDOWS_FILE_ATTRIBUTE_NORMAL,
    )
    if handle is None:
        raise _PublicationError("PUBLICATION_FAILED")
    created_files.append(path)
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
    finally:
        _windows_close(handle)


def _windows_write_layout(
    staging_path: Path,
    staging_handle: int,
    files: tuple[PrivateFoldEvidence, ...],
    manifest: bytes,
    created_files: list[Path],
    created_directories: list[Path],
    directory_handles: list[int],
) -> None:
    directories: dict[tuple[str, ...], tuple[Path, int]] = {(): (staging_path, staging_handle)}
    for item in files:
        parts = PurePosixPath(item.logical_path).parts
        prefix: tuple[str, ...] = ()
        for component in parts[:-1]:
            parent_path, parent_handle = directories[prefix]
            prefix = (*prefix, component)
            if prefix not in directories:
                path = parent_path / component
                created, _ = _windows_create_directory(path)
                if not created:
                    raise _PublicationError("PUBLICATION_FAILED")
                handle, identity, _ = _windows_open_directory(
                    path,
                    _WINDOWS_GENERIC_WRITE | _WINDOWS_DELETE | _WINDOWS_FILE_READ_ATTRIBUTES,
                )
                if handle is None or identity is None:
                    raise _PublicationError("PUBLICATION_FAILED")
                created_directories.append(path)
                directory_handles.append(handle)
                directories[prefix] = (path, handle)
                _windows_flush(parent_handle)
        parent_path, parent_handle = directories[prefix]
        path = parent_path / parts[-1]
        _windows_write_file(path, item.canonical_bytes, created_files)
        _windows_flush(parent_handle)
    manifest_path = staging_path / "manifest.json"
    _windows_write_file(manifest_path, manifest, created_files)
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


def _windows_delete_file(path: Path) -> None:
    delete_file = ctypes.windll.kernel32.DeleteFileW
    delete_file.argtypes = (wintypes.LPCWSTR,)
    delete_file.restype = wintypes.BOOL
    delete_file(str(path))


def _windows_remove_directory(path: Path) -> None:
    remove_directory = ctypes.windll.kernel32.RemoveDirectoryW
    remove_directory.argtypes = (wintypes.LPCWSTR,)
    remove_directory.restype = wintypes.BOOL
    remove_directory(str(path))


def _windows_mark_directory_for_deletion(handle: int) -> None:
    information = _WindowsDispositionInformation(DeleteFile=True)
    set_information = ctypes.windll.kernel32.SetFileInformationByHandle
    set_information.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    set_information.restype = wintypes.BOOL
    set_information(
        handle,
        _WINDOWS_FILE_DISPOSITION_INFO,
        ctypes.byref(information),
        ctypes.sizeof(information),
    )


def _cleanup_windows_staging(
    staging_handle: int,
    created_files: list[Path],
    created_directories: list[Path],
) -> None:
    for path in reversed(created_files):
        _windows_delete_file(path)
    for path in reversed(created_directories):
        _windows_remove_directory(path)
    _windows_mark_directory_for_deletion(staging_handle)


def _windows_flush_cleanup(handle: int) -> None:
    try:
        _windows_flush(handle)
    except _PublicationError:
        return


def _publish_windows_bundle(
    destination: Path,
    files: tuple[PrivateFoldEvidence, ...],
    manifest: bytes,
) -> None:
    ancestors = _windows_open_trusted_ancestors(destination.parent)
    parent_handle = ancestors[-1][1]
    staging_path = destination.parent / f".{destination.name}.staging"
    staging_handle: int | None = None
    created_files: list[Path] = []
    created_directories: list[Path] = []
    directory_handles: list[int] = []
    published = False
    try:
        _windows_require_destination_absent(destination)
        created, error = _windows_create_directory(staging_path)
        if not created:
            if error in (_WINDOWS_ERROR_FILE_EXISTS, _WINDOWS_ERROR_ALREADY_EXISTS):
                raise _PublicationError("STAGING_EXISTS")
            raise _PublicationError("PUBLICATION_FAILED")
        staging_handle, identity, _ = _windows_open_directory(
            staging_path,
            _WINDOWS_GENERIC_WRITE | _WINDOWS_DELETE | _WINDOWS_FILE_READ_ATTRIBUTES,
        )
        if staging_handle is None or identity is None:
            raise _PublicationError("PUBLICATION_FAILED")
        _windows_flush(parent_handle)
        _windows_write_layout(
            staging_path,
            staging_handle,
            files,
            manifest,
            created_files,
            created_directories,
            directory_handles,
        )
        for handle in reversed(directory_handles):
            _windows_close(handle)
        directory_handles.clear()
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
        for handle in reversed(directory_handles):
            _windows_close(handle)
        if staging_handle is not None:
            if not published:
                _cleanup_windows_staging(
                    staging_handle,
                    created_files,
                    created_directories,
                )
            _windows_close(staging_handle)
            if not published:
                _windows_flush_cleanup(parent_handle)
        for _, handle, _ in reversed(ancestors):
            _windows_close(handle)
