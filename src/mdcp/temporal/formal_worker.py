"""Exact isolated process target for one formal development operation."""

from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import stat
import sys
import unicodedata
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

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
_WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_WINDOWS_FILE_ATTRIBUTE_NORMAL = 0x00000080
_WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_WINDOWS_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_WINDOWS_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_WINDOWS_OBJECT_CASE_INSENSITIVE = 0x00000040
_WINDOWS_FILE_OPEN = 1
_WINDOWS_FILE_CREATE = 2
_WINDOWS_FILE_DIRECTORY_FILE = 0x00000001
_WINDOWS_FILE_OPEN_REPARSE_POINT = 0x00200000
_WINDOWS_FILE_WRITE_THROUGH = 0x00000002
_WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
_WINDOWS_FILE_NON_DIRECTORY_FILE = 0x00000040
_WINDOWS_STATUS_OBJECT_NAME_COLLISION = -1073741771
_WINDOWS_STATUS_OBJECT_NAME_NOT_FOUND = -1073741772
_WINDOWS_STATUS_OBJECT_PATH_NOT_FOUND = -1073741766
_WINDOWS_STATUS_FILE_IS_A_DIRECTORY = -1073741638
_APPROVED_ARCHIVE_SIZE = 279_992


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


class _WorkerDenied(RuntimeError):
    def __init__(self, reason: str, authorization_sha256: str = "0" * 64) -> None:
        self.reason = reason
        self.authorization_sha256 = authorization_sha256
        super().__init__(reason)


class _PublicationError(RuntimeError):
    pass


class _ExecutionUnknown(RuntimeError):
    pass


class _SealUnknown(RuntimeError):
    def __init__(self, fit_count: int) -> None:
        if fit_count not in (80, 84):
            raise ValueError
        self.fit_count = fit_count
        super().__init__("FORMAL_RUN_SEAL_UNKNOWN")


@dataclass(frozen=True, slots=True)
class _RetainedAncestor:
    handle: int
    volume_serial_number: int
    file_index: int


@dataclass(slots=True)
class _RetainedDestination:
    absolute_path: Path
    leaf_name: str
    ancestors: tuple[_RetainedAncestor, ...]
    parent_handle: int
    created: bool = False
    closed: bool = False


@dataclass(slots=True)
class _RetainedPublicationPair:
    private: _RetainedDestination
    terminal: _RetainedDestination
    private_published: bool = False
    terminal_published: bool = False
    closed: bool = False


@dataclass(frozen=True, slots=True)
class _WorkerContext:
    request: object
    receipt: object
    index: object
    authorization: object
    repository_root: Path
    source_root: Path
    archive_path: Path
    marker_destination: _RetainedDestination
    publications: _RetainedPublicationPair


@dataclass(frozen=True, slots=True)
class _NaturalResult:
    private_bytes: bytes
    private_identity: object
    seal_bytes: bytes
    fit_count: int


def _canonical_path(path: Path, *, directory: bool) -> Path:
    if not path.is_absolute():
        raise ValueError
    absolute = path.absolute()
    resolved = path.resolve(strict=True)
    information = path.lstat()
    attributes = getattr(information, "st_file_attributes", 0)
    if (
        absolute != resolved
        or path.is_symlink()
        or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
        or (directory and not stat.S_ISDIR(information.st_mode))
        or (not directory and not stat.S_ISREG(information.st_mode))
    ):
        raise ValueError
    return resolved


def _bootstrap_paths() -> tuple[Path, Path, Path]:
    if (
        __name__ != "__main__"
        or len(sys.argv) != 1
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or not sys.dont_write_bytecode
        or sys.version_info[:2] != (3, 12)
    ):
        raise ValueError
    if set(os.environ) != {"SYSTEMROOT", "WINDIR"}:
        raise ValueError
    script = _canonical_path(Path(__file__), directory=False)
    if _canonical_path(Path(sys.argv[0]), directory=False) != script:
        raise ValueError
    repository_root = _canonical_path(script.parents[3], directory=True)
    if _canonical_path(Path.cwd(), directory=True) != repository_root:
        raise ValueError
    source_root = _canonical_path(repository_root / "src", directory=True)
    executable = _canonical_path(Path(sys.executable), directory=False)
    site_packages = _canonical_path(executable.parents[1] / "Lib/site-packages", directory=True)
    sys.path.insert(0, str(site_packages))
    sys.path.insert(0, str(source_root))
    return script, repository_root, source_root


def _source_inventory(repository_root: Path) -> str:
    from mdcp.temporal.formal_worker_protocol import (
        FORMAL_WORKER_SOURCE_PATHS,
        FormalWorkerSourceEntry,
        formal_worker_inventory_sha256,
    )

    entries = []
    for logical_path in FORMAL_WORKER_SOURCE_PATHS:
        path = _canonical_path(repository_root / logical_path, directory=False)
        entries.append(
            FormalWorkerSourceEntry(
                logical_path=logical_path,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return formal_worker_inventory_sha256(tuple(entries))


def _read_regular(path: Path, maximum: int) -> bytes:
    checked = _canonical_path(path, directory=False)
    information = checked.lstat()
    if information.st_size <= 0 or information.st_size > maximum:
        raise ValueError
    raw = checked.read_bytes()
    if len(raw) != information.st_size:
        raise ValueError
    return raw


def _external_directory(path: Path, repository_root: Path) -> Path:
    checked = _canonical_path(path, directory=True)
    if checked == repository_root or checked.is_relative_to(repository_root):
        raise ValueError
    return checked


def _absent_external_leaf(path: Path, repository_root: Path) -> Path:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError
    parent = _external_directory(path.parent, repository_root)
    candidate = parent / path.name
    if candidate.absolute() != path.absolute() or candidate.exists():
        raise ValueError
    return candidate


def _absolute_destination(destination: Path) -> Path:
    if not isinstance(destination, Path):
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
        or unicodedata.normalize("NFC", value) != value
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
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }
    for component in components:
        base = component.split(".", 1)[0].rstrip(" .").upper()
        if (
            component in ("", ".", "..")
            or component.endswith((".", " "))
            or "~" in component
            or any(ord(character) < 32 for character in component)
            or any(character in '<>:"|?*' for character in component)
            or base in reserved
            or unicodedata.normalize("NFC", component) != component
        ):
            raise _PublicationError("TRUSTED_PARENT_REQUIRED")
    return destination


def _windows_last_error() -> int:
    get_last_error = ctypes.windll.kernel32.GetLastError
    get_last_error.argtypes = ()
    get_last_error.restype = wintypes.DWORD
    return int(get_last_error())


def _windows_close(handle: int) -> bool:
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
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
    get_information.argtypes = (wintypes.HANDLE, ctypes.POINTER(_WindowsFileInformation))
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
    desired_access: int,
    share_mode: int,
    create_disposition: int,
    create_options: int,
) -> tuple[bool, int | None, int | None, int | None, int | None]:
    entered = False
    status: int | None = None
    iosb_status: int | None = None
    information: int | None = None
    output_handle = None
    try:
        output_handle = wintypes.HANDLE(_WINDOWS_INVALID_HANDLE_VALUE)
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
        entered = True
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
    destination: Path,
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
            Path(expected),
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
            expected = str(Path(expected) / component)
            entered, status, iosb_status, _, handle = _windows_nt_relative_file(
                parent_handle,
                component,
                ancestor_access
                | (_WINDOWS_FILE_ADD_FILE if index == len(parent_components) - 1 else 0),
                _WINDOWS_FILE_SHARE_READ_WRITE,
                _WINDOWS_FILE_OPEN,
                directory_options,
            )
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


def _revalidate_retained_ancestors(destination: _RetainedDestination) -> None:
    root_volume = destination.ancestors[0].volume_serial_number
    expected_names = [destination.absolute_path.anchor]
    expected_name = destination.absolute_path.anchor
    for component in destination.absolute_path.parts[1:-1]:
        expected_name = str(Path(expected_name) / component)
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
                _windows_normalized_handle_name(ancestor.handle), expected_name
            )
        ):
            raise _PublicationError("PUBLICATION_FAILED")


def _revalidate_final_handle(
    destination: _RetainedDestination,
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
            _windows_normalized_handle_name(final_handle), str(destination.absolute_path)
        )
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
    if not write_file(handle, ctypes.byref(buffer), len(content), ctypes.byref(written), None):
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


def _retained_destination(destination: Path) -> _RetainedDestination:
    checked = _absolute_destination(destination)
    ancestors = _windows_open_trusted_ancestors(checked)
    entered, status, iosb_status, _, handle = _windows_nt_relative_file(
        ancestors[-1][0],
        checked.name,
        _WINDOWS_FILE_READ_ATTRIBUTES | _WINDOWS_SYNCHRONIZE,
        _WINDOWS_FILE_SHARE_READ_WRITE,
        _WINDOWS_FILE_OPEN,
        _WINDOWS_FILE_NON_DIRECTORY_FILE | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT,
    )
    exists = entered and status == 0 and iosb_status == 0 and handle is not None
    absent = (
        status
        in (
            _WINDOWS_STATUS_OBJECT_NAME_NOT_FOUND,
            _WINDOWS_STATUS_OBJECT_PATH_NOT_FOUND,
        )
        and handle is None
    )
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
        _RetainedAncestor(
            handle=item[0],
            volume_serial_number=item[1][0],
            file_index=(item[1][1] << 32) | item[1][2],
        )
        for item in ancestors
    )
    return _RetainedDestination(
        absolute_path=checked,
        leaf_name=checked.name,
        ancestors=retained,
        parent_handle=ancestors[-1][0],
    )


def _close_destination(destination: _RetainedDestination) -> bool:
    if destination.closed:
        return True
    destination.closed = True
    return _windows_close_all([item.handle for item in reversed(destination.ancestors)])


def _close_pair(pair: _RetainedPublicationPair) -> bool:
    if pair.closed:
        return True
    pair.closed = True
    terminal_closed = _close_destination(pair.terminal)
    private_closed = _close_destination(pair.private)
    return terminal_closed and private_closed


def _preflight_pair(private_path: Path) -> _RetainedPublicationPair:
    checked_private = _absolute_destination(private_path)
    terminal_path = checked_private.with_name(f"{checked_private.name}.public.json")
    if checked_private == terminal_path:
        raise _PublicationError("TRUSTED_PARENT_REQUIRED")
    private = _retained_destination(checked_private)
    try:
        terminal = _retained_destination(terminal_path)
    except Exception:
        if not _close_destination(private):
            raise _PublicationError("PUBLICATION_FAILED") from None
        raise
    return _RetainedPublicationPair(private=private, terminal=terminal)


def _publish_retained(destination: _RetainedDestination, content: bytes) -> None:
    final_handle: int | None = None
    published = False
    error: _PublicationError | None = None
    try:
        entered, status, iosb_status, information, final_handle = _windows_nt_relative_file(
            destination.parent_handle,
            destination.leaf_name,
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
                _windows_normalized_handle_name(final_handle), str(destination.absolute_path)
            )
        ):
            raise _PublicationError("PUBLICATION_FAILED")
        _windows_write_all(final_handle, content)
        _windows_flush(final_handle)
        _revalidate_retained_ancestors(destination)
        _revalidate_final_handle(destination, final_handle, identity)
        published = True
    except _PublicationError as caught:
        error = caught
    except Exception:
        error = _PublicationError("PUBLICATION_FAILED")
    close_failed = False
    if final_handle is not None:
        try:
            if not _windows_close(final_handle):
                close_failed = True
        except Exception:
            close_failed = True
    if close_failed:
        raise _PublicationError("PUBLICATION_FAILED") from None
    if error is not None:
        raise error
    if not published:
        raise _PublicationError("PUBLICATION_FAILED")
    destination.created = True


def _publish_private(pair: _RetainedPublicationPair, content: bytes) -> None:
    if pair.closed or pair.private_published:
        raise _PublicationError("PUBLICATION_FAILED")
    _publish_retained(pair.private, content)
    pair.private_published = True


def _publish_terminal(pair: _RetainedPublicationPair, content: bytes) -> None:
    if pair.closed or not pair.private_published or pair.terminal_published:
        raise _PublicationError("PUBLICATION_FAILED")
    _publish_retained(pair.terminal, content)
    pair.terminal_published = True


def _validate_preconsumption(
    request: object,
    repository_root: Path,
    source_root: Path,
) -> _WorkerContext:
    from mdcp.common.canonical import canonicalize_json, parse_json_bytes
    from mdcp.temporal.formal_worker_protocol import (
        PRIVATE_LOGICAL_OUTPUTS,
        SEARCH_SOURCE_PATHS,
        FormalRunAuthorization,
        SearchEvidenceIndex,
        SearchReceipt,
        SearchSourceEntry,
        search_source_inventory_sha256,
    )

    try:
        if set(os.environ) != {"SYSTEMROOT", "WINDIR"} or shutil.which("git") is not None:
            raise ValueError
        if Path(request.repository_root) != repository_root:
            raise _WorkerDenied("FORMAL_RUN_REPOSITORY_INVALID")
        receipt_raw = _read_regular(Path(request.search_receipt_path), 1_048_576)
        index_raw = _read_regular(Path(request.evidence_index_path), 4_194_304)
        authorization_raw = _read_regular(Path(request.authorization_path), 65_536)
        if (
            hashlib.sha256(receipt_raw).hexdigest() != request.search_receipt_sha256
            or hashlib.sha256(index_raw).hexdigest() != request.evidence_index_sha256
            or hashlib.sha256(authorization_raw).hexdigest() != request.authorization_sha256
        ):
            raise ValueError
        receipt = SearchReceipt.model_validate(parse_json_bytes(receipt_raw))
        index = SearchEvidenceIndex.model_validate(parse_json_bytes(index_raw))
        authorization = FormalRunAuthorization.model_validate(parse_json_bytes(authorization_raw))
        if (
            canonicalize_json(receipt.model_dump(mode="json")) != receipt_raw
            or canonicalize_json(index.model_dump(mode="json")) != index_raw
            or canonicalize_json(authorization.model_dump(mode="json")) != authorization_raw
        ):
            raise ValueError
    except _WorkerDenied:
        raise
    except Exception:
        raise _WorkerDenied("FORMAL_RUN_AUTHORIZATION_INVALID") from None

    authorization_sha256 = hashlib.sha256(authorization_raw).hexdigest()
    if (
        index.private_logical_outputs != PRIVATE_LOGICAL_OUTPUTS
        or index.search_receipt_sha256 != request.search_receipt_sha256
        or authorization.search_freeze_commit != request.expected_freeze_head
        or authorization.search_receipt_sha256 != request.search_receipt_sha256
        or authorization.protocol_sha256 != receipt.dataset_contract_sha256
        or authorization.dataset_archive_sha256 != receipt.dataset_archive_sha256
    ):
        raise _WorkerDenied("FORMAL_RUN_AUTHORIZATION_MISMATCH", authorization_sha256)

    entries = []
    try:
        for expected, logical_path in zip(index.source_entries, SEARCH_SOURCE_PATHS, strict=True):
            path = _canonical_path(repository_root / logical_path, directory=False)
            raw = path.read_bytes()
            entry = SearchSourceEntry(
                logical_path=logical_path,
                git_mode="100644",
                byte_size=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
            )
            if entry != expected:
                raise ValueError
            entries.append(entry)
        if (
            search_source_inventory_sha256(tuple(entries)) != request.source_inventory_sha256
            or index.source_inventory_sha256 != request.source_inventory_sha256
        ):
            raise ValueError
    except Exception:
        raise _WorkerDenied("SEARCH_FREEZE_INVALID") from None

    try:
        archive_path = _canonical_path(Path(request.archive_path), directory=False)
        if archive_path.lstat().st_size != _APPROVED_ARCHIVE_SIZE:
            raise ValueError
        consumption_root = _external_directory(Path(request.consumption_root), repository_root)
        private_path = _absent_external_leaf(Path(request.private_container_path), repository_root)
        terminal_path = _absent_external_leaf(
            Path(f"{request.private_container_path}.public.json"), repository_root
        )
        marker_path = consumption_root / f"{authorization_sha256}.consumed.json"
        if (
            marker_path in (private_path, terminal_path)
            or len({marker_path, private_path, terminal_path}) != 3
        ):
            raise ValueError
    except Exception:
        raise _WorkerDenied("FORMAL_RUN_DESTINATION_INVALID", authorization_sha256) from None
    try:
        marker_destination = _retained_destination(marker_path)
    except _PublicationError as error:
        reason = (
            "FORMAL_RUN_AUTHORIZATION_CONSUMED"
            if str(error) == "DESTINATION_EXISTS"
            else "FORMAL_RUN_DESTINATION_INVALID"
        )
        raise _WorkerDenied(reason, authorization_sha256) from None
    try:
        publications = _preflight_pair(private_path)
    except Exception:
        if not _close_destination(marker_destination):
            raise _PublicationError("PUBLICATION_FAILED") from None
        raise _WorkerDenied("FORMAL_RUN_DESTINATION_INVALID", authorization_sha256) from None
    return _WorkerContext(
        request=request,
        receipt=receipt,
        index=index,
        authorization=authorization,
        repository_root=repository_root,
        source_root=source_root,
        archive_path=archive_path,
        marker_destination=marker_destination,
        publications=publications,
    )


def _create_durable_marker(context: _WorkerContext) -> str:
    from mdcp.common.canonical import canonicalize_json

    authorization_sha256 = context.request.authorization_sha256
    marker = {
        "authorization_sha256": authorization_sha256,
        "canonicalization_version": "RFC8785",
        "consumed": True,
        "dataset_archive_sha256": context.receipt.dataset_archive_sha256,
        "protocol_sha256": context.receipt.dataset_contract_sha256,
        "schema_version": "mdcp.formal-run-consumption.v1",
        "search_freeze_commit": context.request.expected_freeze_head,
        "search_receipt_sha256": context.request.search_receipt_sha256,
    }
    marker_bytes = canonicalize_json(marker)
    error: Exception | None = None
    try:
        _publish_retained(context.marker_destination, marker_bytes)
    except _PublicationError as caught:
        error = (
            FileExistsError("FORMAL_RUN_AUTHORIZATION_CONSUMED")
            if str(caught) == "DESTINATION_EXISTS"
            else caught
        )
    if not _close_destination(context.marker_destination):
        raise _PublicationError("PUBLICATION_FAILED") from None
    if error is not None:
        raise error
    return hashlib.sha256(marker_bytes).hexdigest()


def _hash_archive(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1_048_576):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint(guard: object, stage: object) -> object:
    observation = guard.checkpoint(stage)
    if observation.verdict != "PASS" or observation.reason_codes:
        raise RuntimeError("WORKER_RUNTIME_GUARD_UNKNOWN")
    return observation


def _fit_natural_request(folds: dict[str, object], trials: dict[str, object], request: object):
    from datetime import datetime

    from mdcp.common.canonical import canonicalize_json
    from mdcp.common.digests import sha256_hex
    from mdcp.common.enums import GateVerdict
    from mdcp.temporal.completeness import AdapterOutcome, LabelOutcome, PredictionOutcome
    from mdcp.temporal.runner import DevelopmentFoldResult, _formal_groups
    from mdcp.temporal.trials import (
        _feature_names,
        _materialize_features,
        build_estimator,
        canonical_trial_identity,
        training_rows_for_trial,
    )

    fold = folds[request.fold_id]
    trial = trials[request.trial_id]
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
        "trial_id": request.trial_id,
        "fold_id": request.fold_id,
        "preprocessing_state_sha256": sha256_hex(
            canonicalize_json(
                {
                    "configuration_sha256": canonical_trial_identity(
                        request.trial_id
                    ).configuration_sha256,
                    "training_features": training_material,
                    "training_labels": tuple(float(value) for value in training["cnt"]),
                }
            )
        ),
        "feature_vector_sha256": sha256_hex(canonicalize_json(feature_material)),
        "prediction_vector_sha256": sha256_hex(canonicalize_json(prediction_values)),
        "metric_sha256": sha256_hex(
            canonicalize_json({"labels": label_values, "predictions": prediction_values})
        ),
    }
    return DevelopmentFoldResult(
        trial_id=request.trial_id,
        fold_id=request.fold_id,
        inventory=fold.inventory,
        adapters=adapters,
        predictions=predictions,
        labels=labels,
        contract_verdict=GateVerdict.PASS,
        preprocessing_state_sha256=declared["preprocessing_state_sha256"],
        feature_vector_sha256=declared["feature_vector_sha256"],
        prediction_vector_sha256=declared["prediction_vector_sha256"],
        metric_sha256=declared["metric_sha256"],
        receipt_sha256=sha256_hex(canonicalize_json(declared)),
    )


def _json_value(value: object) -> object:
    from dataclasses import asdict, is_dataclass

    if hasattr(value, "value") and type(value.value) is str:
        return value.value
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _winner_document(winner: object, qualification_sha256: str, labels: dict[str, str]):
    if winner is None:
        return None
    document = _json_value(winner)
    if not isinstance(document, dict):
        raise ValueError
    trial_id = document.get("trial_id")
    ranking_key = document.get("ranking_key")
    if type(trial_id) is not str or trial_id not in labels or not isinstance(ranking_key, list):
        raise ValueError
    document["trial_id"] = labels[trial_id]
    ranking_key[-1] = labels[trial_id]
    document["qualification_inventory_sha256"] = qualification_sha256
    return document


def _formalize_natural(result: object):
    from mdcp.common.canonical import canonicalize_json, parse_json_bytes
    from mdcp.common.digests import sha256_hex
    from mdcp.temporal.run_evidence import PrivateFoldEvidence, PublicDevelopmentResult
    from mdcp.temporal.runner import EXACT_FOLD_IDS, EXACT_TRIAL_IDS, DevelopmentRunBundle, FitPhase

    if type(result) is not DevelopmentRunBundle:
        raise ValueError
    labels = {trial_id: f"TRIAL-{index:02d}" for index, trial_id in enumerate(EXACT_TRIAL_IDS, 1)}
    selection_folds = []
    replay_folds = []
    for item in result.private_bundle.files:
        document = parse_json_bytes(item.canonical_bytes)
        trial_id = document.get("trial_id") if isinstance(document, dict) else None
        if type(trial_id) is not str or trial_id not in labels:
            raise ValueError
        document["trial_id"] = labels[trial_id]
        target = (
            selection_folds if document.get("phase") == FitPhase.SELECTION.value else replay_folds
        )
        target.append(document)
    expected_selection = tuple(
        (labels[trial_id], fold_id) for trial_id in EXACT_TRIAL_IDS for fold_id in EXACT_FOLD_IDS
    )
    if tuple((item["trial_id"], item["fold_id"]) for item in selection_folds) != expected_selection:
        raise ValueError
    qualifications = [_json_value(item) for item in result.qualifications]
    raw_qualification_sha256 = sha256_hex(canonicalize_json(qualifications))
    for expected, document in zip(EXACT_TRIAL_IDS[1:], qualifications, strict=True):
        if not isinstance(document, dict) or document.get("trial_id") != expected:
            raise ValueError
        document["trial_id"] = labels[expected]
    qualification_sha256 = sha256_hex(canonicalize_json(qualifications))
    replay_digests = (
        [] if result.replay is None else [_json_value(item) for item in result.replay.digests]
    )
    common = {"canonicalization_version": "RFC8785", "evidence_class": "natural_development"}
    documents = {
        "provisional-winner.json": {
            "schema_version": "mdcp.natural-provisional-winner.v1",
            **common,
            "provisional_winner": _winner_document(
                result.selection.provisional_winner, qualification_sha256, labels
            ),
            "final_winner": _winner_document(
                result.selection.final_winner, qualification_sha256, labels
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
                    labels[result.selection.provisional_winner.trial_id],
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
            "replay_trial_id": labels[result.replay.trial_id]
            if result.replay is not None
            else None,
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
        PrivateFoldEvidence(logical_path=name, canonical_bytes=canonicalize_json(documents[name]))
        for name in (
            "provisional-winner.json",
            "qualification-report.json",
            "ranking-report.json",
            "replay-report.json",
            "trial-summary.json",
        )
    )
    public = result.public_result.model_dump(mode="json")
    public["evidence_class"] = "natural_development"
    if result.selection.provisional_winner is not None and (
        result.selection.provisional_winner.qualification_inventory_sha256
        != raw_qualification_sha256
    ):
        raise ValueError
    return files, PublicDevelopmentResult.model_validate(public), result.selection.status


def _encode_natural(files: tuple[object, ...]):
    from base64 import b64encode

    from mdcp.common.canonical import canonicalize_json
    from mdcp.common.digests import sha256_hex
    from mdcp.temporal import run_evidence

    validated = run_evidence._validated_private_files(files)
    entries = tuple(
        run_evidence._PrivateContainerEntry(
            logical_path=item.logical_path,
            byte_size=len(item.canonical_bytes),
            sha256=sha256_hex(item.canonical_bytes),
            payload_base64=b64encode(item.canonical_bytes).decode("ascii"),
        )
        for item in validated
    )
    total_bytes = sum(item.byte_size for item in entries)
    inventory_sha256 = sha256_hex(canonicalize_json(run_evidence._inventory_core(entries)))
    manifest = run_evidence._manifest_core(
        "natural_development", len(entries), total_bytes, inventory_sha256
    )
    manifest_sha256 = sha256_hex(canonicalize_json(manifest))
    content = canonicalize_json(
        run_evidence._PrivateContainer(
            **manifest, entries=entries, manifest_sha256=manifest_sha256
        ).model_dump(mode="json")
    )
    return content, run_evidence.PrivateBundleIdentity(
        file_count=len(entries),
        total_bytes=total_bytes,
        inventory_sha256=inventory_sha256,
        manifest_sha256=manifest_sha256,
    )


def _complete_finalized_run(
    context: _WorkerContext,
    marker_sha256: str,
    guard: object,
    result: object,
    fit_count: int,
) -> _NaturalResult:
    from mdcp.common.canonical import canonicalize_json
    from mdcp.common.digests import sha256_hex
    from mdcp.temporal.formal_worker_protocol import worker_request_sha256
    from mdcp.temporal.run_evidence import FormalDevelopmentSeal
    from mdcp.temporal.runtime_guards import RuntimeStage

    try:
        files, public_result, selection_status = _formalize_natural(result)
        _checkpoint(guard, RuntimeStage.PRE_SEAL)
        private_bytes, private_identity = _encode_natural(files)
        _publish_private(context.publications, private_bytes)
        exit_observation = _checkpoint(guard, RuntimeStage.EXIT)
        exit_sha256 = sha256_hex(
            canonicalize_json(
                {
                    "elapsed_within_budget": True,
                    "max_elapsed_ns": 21_600_000_000_000,
                    "max_peak_process_bytes": 4_294_967_296,
                    "memory_within_budget": True,
                    "reason_codes": [],
                    "repository_inventory_sha256": context.request.repository_inventory_sha256,
                    "schema_version": "mdcp.formal-exit-observation.v1",
                    "search_freeze_commit": context.request.expected_freeze_head,
                    "stage": "EXIT",
                    "verdict": "PASS",
                }
            )
        )
        if exit_observation.verdict != "PASS":
            raise ValueError
        seal = FormalDevelopmentSeal(
            schema_version="mdcp.formal-development-seal.v1",
            canonicalization_version="RFC8785",
            terminal_state="SEALED",
            authorization_sha256=context.request.authorization_sha256,
            consumption_marker_sha256=marker_sha256,
            search_freeze_commit=context.request.expected_freeze_head,
            search_receipt_sha256=context.request.search_receipt_sha256,
            worker_request_sha256=worker_request_sha256(context.request),
            formal_worker_inventory_sha256=context.request.formal_worker_inventory_sha256,
            launch_profile_sha256=context.request.launch_profile_sha256,
            source_inventory_sha256=context.request.source_inventory_sha256,
            evidence_index_sha256=context.request.evidence_index_sha256,
            protocol_sha256=context.receipt.dataset_contract_sha256,
            repository_inventory_sha256=context.request.repository_inventory_sha256,
            dataset_archive_sha256=context.receipt.dataset_archive_sha256,
            private_identity=private_identity,
            exit_observation_sha256=exit_sha256,
            fit_count=fit_count,
            selection_status=selection_status,
            h1_role="OBSERVED_DEVELOPMENT_ONLY",
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
            development_result=public_result,
        )
        seal_bytes = canonicalize_json(seal.model_dump(mode="json"))
        _publish_terminal(context.publications, seal_bytes)
        return _NaturalResult(
            private_bytes=private_bytes,
            private_identity=private_identity,
            seal_bytes=seal_bytes,
            fit_count=fit_count,
        )
    except Exception:
        raise _SealUnknown(fit_count) from None


def _execute_natural_run(context: _WorkerContext, marker_sha256: str) -> _NaturalResult:
    try:
        from mdcp.common.canonical import parse_json_bytes
        from mdcp.common.digests import sha256_hex
        from mdcp.temporal.folds import load_fold_specs, materialize_folds
        from mdcp.temporal.runner import EXACT_FOLD_IDS, EXACT_TRIAL_IDS, DevelopmentStateMachine
        from mdcp.temporal.runtime_guards import RuntimeStage, build_worker_runtime_guard
        from mdcp.temporal.trials import load_trial_specs
        from mdcp.workload.dataset import load_uci_development_archive
        from mdcp.workload.splits import split_development_rows

        protocol_bytes = _read_regular(
            context.repository_root / "configs/workload/temporal-development-v2.json", 1_048_576
        )
        if sha256_hex(protocol_bytes) != context.receipt.dataset_contract_sha256:
            raise ValueError
        protocol = parse_json_bytes(protocol_bytes)
        guard = build_worker_runtime_guard(
            context.repository_root,
            context.request.source_inventory_sha256,
            context.request.formal_worker_inventory_sha256,
        )
        _checkpoint(guard, RuntimeStage.PRE_LOAD)
        rows = load_uci_development_archive(
            context.archive_path, context.receipt.dataset_archive_sha256
        )
        partitions = split_development_rows(rows)
        if len(partitions.train) != 8_645 or len(partitions.h1) != 4_358:
            raise ValueError
        folds = materialize_folds(partitions, load_fold_specs(protocol))
        trials = load_trial_specs(protocol)
        if (
            tuple(fold.spec.fold_id for fold in folds) != EXACT_FOLD_IDS
            or tuple(trial.trial_id for trial in trials) != EXACT_TRIAL_IDS
        ):
            raise ValueError
        fold_map = {fold.spec.fold_id: fold for fold in folds}
        trial_map = {trial.trial_id: trial for trial in trials}
        machine = DevelopmentStateMachine()
        while (fit_request := machine.next_fit_request()) is not None:
            _checkpoint(guard, RuntimeStage.PRE_FIT)
            fit_result = _fit_natural_request(fold_map, trial_map, fit_request)
            _checkpoint(guard, RuntimeStage.POST_FIT)
            machine.record_fit_result(fit_request, fit_result)
        result = machine.finalize()
        fit_count = result.fit_ledger.total_count
        if fit_count not in (80, 84):
            raise ValueError
    except Exception:
        raise _ExecutionUnknown from None
    return _complete_finalized_run(context, marker_sha256, guard, result, fit_count)


def _response(
    request: object,
    inventory_sha256: str,
    *,
    verdict: str,
    reason: str | None,
    authorization_sha256: str,
    marker_sha256: str | None = None,
    fit_count: int = 0,
    natural: _NaturalResult | None = None,
):
    from mdcp.common.digests import sha256_hex
    from mdcp.temporal.formal_worker_protocol import (
        FormalWorkerPrivateIdentity,
        FormalWorkerResponse,
        launch_profile_sha256,
        worker_request_sha256,
    )

    private_identity = None
    if natural is not None:
        private_identity = FormalWorkerPrivateIdentity(
            **natural.private_identity.model_dump(mode="python")
        )
    return FormalWorkerResponse(
        schema_version="mdcp.formal-worker-response.v1",
        canonicalization_version="RFC8785",
        verdict=verdict,
        reason_codes=() if reason is None else (reason,),
        private_identity=private_identity,
        seal_record_sha256=None if natural is None else sha256_hex(natural.seal_bytes),
        repository_inventory_sha256=(
            None if natural is None else request.repository_inventory_sha256
        ),
        authorization_sha256=authorization_sha256,
        consumption_marker_sha256=marker_sha256,
        fit_count=fit_count,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
        worker_request_sha256=worker_request_sha256(request),
        formal_worker_inventory_sha256=inventory_sha256,
        launch_profile_sha256=launch_profile_sha256(),
    )


def _close_publications(pair: _RetainedPublicationPair) -> bool:
    try:
        return _close_pair(pair)
    except Exception:
        return False


def _execute_worker_request(
    request: object,
    repository_root: Path,
    source_root: Path,
    inventory_sha256: str,
):
    try:
        context = _validate_preconsumption(request, repository_root, source_root)
    except _PublicationError:
        return _response(
            request,
            inventory_sha256,
            verdict="UNKNOWN",
            reason="FORMAL_RUN_CONSUMPTION_UNKNOWN",
            authorization_sha256=request.authorization_sha256,
        )
    except _WorkerDenied as denied:
        return _response(
            request,
            inventory_sha256,
            verdict="FAIL",
            reason=denied.reason,
            authorization_sha256=denied.authorization_sha256,
        )
    try:
        marker_sha256 = _create_durable_marker(context)
    except FileExistsError:
        if not _close_publications(context.publications):
            return _response(
                request,
                inventory_sha256,
                verdict="UNKNOWN",
                reason="FORMAL_RUN_CONSUMPTION_UNKNOWN",
                authorization_sha256=request.authorization_sha256,
            )
        return _response(
            request,
            inventory_sha256,
            verdict="FAIL",
            reason="FORMAL_RUN_AUTHORIZATION_CONSUMED",
            authorization_sha256=request.authorization_sha256,
        )
    except Exception:
        _close_publications(context.publications)
        return _response(
            request,
            inventory_sha256,
            verdict="UNKNOWN",
            reason="FORMAL_RUN_CONSUMPTION_UNKNOWN",
            authorization_sha256=request.authorization_sha256,
        )
    try:
        archive_sha256 = _hash_archive(context.archive_path)
    except Exception:
        archive_sha256 = None
    if archive_sha256 != context.receipt.dataset_archive_sha256:
        _close_publications(context.publications)
        return _response(
            request,
            inventory_sha256,
            verdict="UNKNOWN",
            reason="FORMAL_RUN_EXECUTION_UNKNOWN",
            authorization_sha256=request.authorization_sha256,
            marker_sha256=marker_sha256,
        )
    try:
        natural = _execute_natural_run(context, marker_sha256)
    except _SealUnknown as unknown:
        _close_publications(context.publications)
        return _response(
            request,
            inventory_sha256,
            verdict="UNKNOWN",
            reason="FORMAL_RUN_SEAL_UNKNOWN",
            authorization_sha256=request.authorization_sha256,
            marker_sha256=marker_sha256,
            fit_count=unknown.fit_count,
        )
    except _ExecutionUnknown:
        _close_publications(context.publications)
        return _response(
            request,
            inventory_sha256,
            verdict="UNKNOWN",
            reason="FORMAL_RUN_EXECUTION_UNKNOWN",
            authorization_sha256=request.authorization_sha256,
            marker_sha256=marker_sha256,
        )
    except Exception:
        _close_publications(context.publications)
        return _response(
            request,
            inventory_sha256,
            verdict="UNKNOWN",
            reason="FORMAL_RUN_EXECUTION_UNKNOWN",
            authorization_sha256=request.authorization_sha256,
            marker_sha256=marker_sha256,
        )
    if not _close_publications(context.publications):
        return _response(
            request,
            inventory_sha256,
            verdict="UNKNOWN",
            reason="FORMAL_RUN_SEAL_UNKNOWN",
            authorization_sha256=request.authorization_sha256,
            marker_sha256=marker_sha256,
            fit_count=natural.fit_count,
        )
    return _response(
        request,
        inventory_sha256,
        verdict="PASS",
        reason=None,
        authorization_sha256=request.authorization_sha256,
        marker_sha256=marker_sha256,
        fit_count=natural.fit_count,
        natural=natural,
    )


def _emit_response(response: object) -> None:
    from mdcp.temporal.formal_worker_protocol import encode_formal_worker_response

    raw = encode_formal_worker_response(response)
    if sys.stdout.buffer.write(raw) != len(raw):
        raise OSError
    sys.stdout.buffer.flush()


def main() -> int:
    if __name__ != "__main__":
        return 2
    try:
        _script, repository_root, source_root = _bootstrap_paths()
        from mdcp.temporal.formal_worker_protocol import (
            MAX_WORKER_MESSAGE_BYTES,
            launch_profile_sha256,
            parse_formal_worker_request,
        )

        raw = sys.stdin.buffer.read(MAX_WORKER_MESSAGE_BYTES + 1)
        request = parse_formal_worker_request(raw)
        inventory_sha256 = _source_inventory(repository_root)
        if (
            request.repository_root != repository_root.as_posix()
            or request.formal_worker_inventory_sha256 != inventory_sha256
            or request.launch_profile_sha256 != launch_profile_sha256()
        ):
            raise ValueError
        response = _execute_worker_request(request, repository_root, source_root, inventory_sha256)
        _emit_response(response)
        return 0
    except Exception:
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
