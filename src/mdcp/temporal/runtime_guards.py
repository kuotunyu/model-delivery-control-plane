from __future__ import annotations

import ctypes
import hashlib
import os
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal

_MAX_ELAPSED_NS = 21_600_000_000_000
_MAX_PEAK_PROCESS_BYTES = 4 * 1024**3


class RuntimeStage(StrEnum):
    PRE_LOAD = "PRE_LOAD"
    PRE_FIT = "PRE_FIT"
    POST_FIT = "POST_FIT"
    PRE_SEAL = "PRE_SEAL"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    verdict: Literal["PASS", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    elapsed_ns: int
    peak_process_bytes: int | None
    repository_inventory_sha256: str


@dataclass(frozen=True, slots=True)
class _RuntimeGuardCore:
    evidence_class: Literal["authoritative_runtime", "synthetic_test"]
    repository_root: Path
    expected_head: str
    start_ns: int
    monotonic_ns: Callable[[], int]
    peak_process_bytes: Callable[[], int | None]
    tracked_paths: tuple[bytes, ...] | None
    repository_inventory_sha256: str | None


class _CheckpointGuard:
    __slots__ = ("_core",)

    def __init__(self, core: _RuntimeGuardCore) -> None:
        super().__setattr__("_core", core)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("runtime guard state is immutable")

    def checkpoint(self, stage: RuntimeStage) -> RuntimeObservation:
        del stage
        core = self._core
        elapsed_ns = core.monotonic_ns() - core.start_ns
        peak_process_bytes = core.peak_process_bytes()
        if type(peak_process_bytes) is not int or peak_process_bytes < 0:
            return self._unknown("AUTHORITATIVE_MEMORY_UNAVAILABLE", elapsed_ns, peak_process_bytes)
        if peak_process_bytes > _MAX_PEAK_PROCESS_BYTES:
            return self._unknown("COMPUTE_MEMORY_EXCEEDED", elapsed_ns, peak_process_bytes)
        if type(elapsed_ns) is not int or elapsed_ns < 0 or elapsed_ns > _MAX_ELAPSED_NS:
            return self._unknown("COMPUTE_DEADLINE_EXCEEDED", elapsed_ns, peak_process_bytes)
        if core.tracked_paths is None or core.repository_inventory_sha256 is None:
            return self._unknown("REPOSITORY_BYTES_UNAVAILABLE", elapsed_ns, peak_process_bytes)
        if _repository_head(core.repository_root) != core.expected_head:
            return self._unknown("REPOSITORY_IDENTITY_CHANGED", elapsed_ns, peak_process_bytes)
        dirty_before_inventory = _repository_is_dirty(core.repository_root)
        inventory_sha256 = _repository_inventory(core.repository_root, core.tracked_paths)
        if _repository_head(core.repository_root) != core.expected_head:
            return self._unknown("REPOSITORY_IDENTITY_CHANGED", elapsed_ns, peak_process_bytes)
        dirty_after_inventory = _repository_is_dirty(core.repository_root)
        if _repository_head(core.repository_root) != core.expected_head:
            return self._unknown("REPOSITORY_IDENTITY_CHANGED", elapsed_ns, peak_process_bytes)
        if inventory_sha256 is None:
            return self._unknown("REPOSITORY_BYTES_UNAVAILABLE", elapsed_ns, peak_process_bytes)
        if inventory_sha256 != core.repository_inventory_sha256:
            return self._unknown("REPOSITORY_BYTES_CHANGED", elapsed_ns, peak_process_bytes)
        if dirty_before_inventory or dirty_after_inventory:
            return self._unknown("REPOSITORY_DIRTY", elapsed_ns, peak_process_bytes)
        return RuntimeObservation(
            verdict="PASS",
            reason_codes=(),
            elapsed_ns=elapsed_ns,
            peak_process_bytes=peak_process_bytes,
            repository_inventory_sha256=inventory_sha256,
        )

    def _unknown(
        self,
        reason_code: str,
        elapsed_ns: int,
        peak_process_bytes: int | None,
    ) -> RuntimeObservation:
        return RuntimeObservation(
            verdict="UNKNOWN",
            reason_codes=(reason_code,),
            elapsed_ns=elapsed_ns,
            peak_process_bytes=peak_process_bytes,
            repository_inventory_sha256=self._core.repository_inventory_sha256 or "",
        )


@dataclass(frozen=True, slots=True)
class _WorkerRuntimeGuard:
    """Worker-local source, wall, memory, and sealed-H2 checkpoint guard."""

    repository_root: Path
    source_inventory_sha256: str
    expected_formal_worker_inventory_sha256: str
    start_ns: int

    def checkpoint(self, stage: RuntimeStage) -> RuntimeObservation:
        if type(stage) is not RuntimeStage:
            return self._unknown("RUNTIME_GUARD_INVALID", 0, None)
        elapsed_ns = time.monotonic_ns() - self.start_ns
        peak_process_bytes = _authoritative_peak_process_bytes()
        if type(peak_process_bytes) is not int or peak_process_bytes < 0:
            return self._unknown("AUTHORITATIVE_MEMORY_UNAVAILABLE", elapsed_ns, peak_process_bytes)
        if peak_process_bytes > _MAX_PEAK_PROCESS_BYTES:
            return self._unknown("COMPUTE_MEMORY_EXCEEDED", elapsed_ns, peak_process_bytes)
        if type(elapsed_ns) is not int or elapsed_ns < 0 or elapsed_ns > _MAX_ELAPSED_NS:
            return self._unknown("COMPUTE_DEADLINE_EXCEEDED", elapsed_ns, peak_process_bytes)
        current_source = _worker_source_inventory(self.repository_root)
        current_worker = _formal_worker_source_inventory(self.repository_root)
        if current_source is None:
            return self._unknown("SOURCE_INVENTORY_UNAVAILABLE", elapsed_ns, peak_process_bytes)
        if current_worker is None:
            return self._unknown(
                "FORMAL_WORKER_INVENTORY_UNAVAILABLE", elapsed_ns, peak_process_bytes
            )
        if current_source != self.source_inventory_sha256:
            return self._unknown("SOURCE_INVENTORY_CHANGED", elapsed_ns, peak_process_bytes)
        if current_worker != self.expected_formal_worker_inventory_sha256:
            return self._unknown("FORMAL_WORKER_INVENTORY_CHANGED", elapsed_ns, peak_process_bytes)
        return RuntimeObservation(
            verdict="PASS",
            reason_codes=(),
            elapsed_ns=elapsed_ns,
            peak_process_bytes=peak_process_bytes,
            repository_inventory_sha256=current_source,
        )

    def _unknown(
        self,
        reason_code: str,
        elapsed_ns: int,
        peak_process_bytes: int | None,
    ) -> RuntimeObservation:
        return RuntimeObservation(
            verdict="UNKNOWN",
            reason_codes=(reason_code,),
            elapsed_ns=elapsed_ns,
            peak_process_bytes=peak_process_bytes,
            repository_inventory_sha256=self.source_inventory_sha256,
        )


def _worker_source_inventory(repository_root: Path) -> str | None:
    from mdcp.temporal.formal_worker_protocol import (
        SEARCH_SOURCE_PATHS,
        SearchSourceEntry,
        search_source_inventory_sha256,
    )

    entries = []
    try:
        for logical_path in SEARCH_SOURCE_PATHS:
            path = repository_root / logical_path
            information = path.lstat()
            attributes = getattr(information, "st_file_attributes", 0)
            if (
                path.is_symlink()
                or attributes & 0x00000400
                or not stat.S_ISREG(information.st_mode)
            ):
                return None
            raw = path.read_bytes()
            if len(raw) != information.st_size:
                return None
            entries.append(
                SearchSourceEntry(
                    logical_path=logical_path,
                    git_mode="100644",
                    byte_size=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                )
            )
    except Exception:
        return None
    return search_source_inventory_sha256(tuple(entries))


def _formal_worker_source_inventory(repository_root: Path) -> str | None:
    from mdcp.temporal.formal_worker_protocol import (
        FORMAL_WORKER_SOURCE_PATHS,
        FormalWorkerSourceEntry,
        formal_worker_inventory_sha256,
    )

    entries = []
    try:
        for logical_path in FORMAL_WORKER_SOURCE_PATHS:
            path = repository_root / logical_path
            information = path.lstat()
            attributes = getattr(information, "st_file_attributes", 0)
            if (
                path.is_symlink()
                or attributes & 0x00000400
                or not stat.S_ISREG(information.st_mode)
            ):
                return None
            raw = path.read_bytes()
            if len(raw) != information.st_size:
                return None
            entries.append(
                FormalWorkerSourceEntry(
                    logical_path=logical_path,
                    sha256=hashlib.sha256(raw).hexdigest(),
                )
            )
    except Exception:
        return None
    return formal_worker_inventory_sha256(tuple(entries))


def build_worker_runtime_guard(
    repository_root: Path,
    source_inventory_sha256: str,
    expected_formal_worker_inventory_sha256: str,
) -> _WorkerRuntimeGuard:
    """Create the fixed worker guard without Git, callbacks, or probe injection."""
    if (
        not isinstance(repository_root, Path)
        or type(source_inventory_sha256) is not str
        or len(source_inventory_sha256) != 64
        or source_inventory_sha256 == "0" * 64
        or type(expected_formal_worker_inventory_sha256) is not str
        or len(expected_formal_worker_inventory_sha256) != 64
        or expected_formal_worker_inventory_sha256 == "0" * 64
    ):
        raise ValueError("WORKER_RUNTIME_GUARD_INVALID")
    current_source = _worker_source_inventory(repository_root)
    current_worker = _formal_worker_source_inventory(repository_root)
    if (
        current_source != source_inventory_sha256
        or current_worker != expected_formal_worker_inventory_sha256
    ):
        raise ValueError("WORKER_RUNTIME_GUARD_INVALID")
    return _WorkerRuntimeGuard(
        repository_root=repository_root,
        source_inventory_sha256=source_inventory_sha256,
        expected_formal_worker_inventory_sha256=expected_formal_worker_inventory_sha256,
        start_ns=time.monotonic_ns(),
    )


def _make_runtime_guard_type() -> tuple[
    type[_CheckpointGuard], Callable[[Path, str], _CheckpointGuard]
]:
    construction_token = object()

    class ProductionRuntimeGuard(_CheckpointGuard):
        """Authoritative-runtime guard created only by the closure-bound production builder."""

        def __init__(self, core: _RuntimeGuardCore, token: object) -> None:
            if token is not construction_token or core.evidence_class != "authoritative_runtime":
                raise TypeError("production guard requires authoritative runtime evidence")
            super().__init__(core)

    def build(repository_root: Path, expected_head: str) -> _CheckpointGuard:
        core = _build_runtime_guard_core(
            repository_root,
            expected_head,
            evidence_class="authoritative_runtime",
            monotonic_ns=time.monotonic_ns,
            peak_process_bytes=_authoritative_peak_process_bytes,
        )
        return ProductionRuntimeGuard(core, construction_token)

    return ProductionRuntimeGuard, build


RuntimeGuard, build_production_runtime_guard = _make_runtime_guard_type()


class _SyntheticRuntimeGuard(_CheckpointGuard):
    def __init__(self, core: _RuntimeGuardCore) -> None:
        if core.evidence_class != "synthetic_test":
            raise ValueError("synthetic guard requires synthetic test evidence")
        super().__init__(core)


def _build_synthetic_runtime_guard(
    repository_root: Path,
    expected_head: str,
    *,
    monotonic_ns: Callable[[], int],
    peak_process_bytes: Callable[[], int | None],
) -> _SyntheticRuntimeGuard:
    return _SyntheticRuntimeGuard(
        _build_runtime_guard_core(
            repository_root,
            expected_head,
            evidence_class="synthetic_test",
            monotonic_ns=monotonic_ns,
            peak_process_bytes=peak_process_bytes,
        )
    )


def _build_runtime_guard_core(
    repository_root: Path,
    expected_head: str,
    *,
    evidence_class: Literal["authoritative_runtime", "synthetic_test"],
    monotonic_ns: Callable[[], int],
    peak_process_bytes: Callable[[], int | None],
) -> _RuntimeGuardCore:
    tracked_paths = _tracked_paths(repository_root, expected_head)
    inventory_sha256 = (
        _repository_inventory(repository_root, tracked_paths) if tracked_paths is not None else None
    )
    return _RuntimeGuardCore(
        evidence_class=evidence_class,
        repository_root=repository_root,
        expected_head=expected_head,
        start_ns=monotonic_ns(),
        monotonic_ns=monotonic_ns,
        peak_process_bytes=peak_process_bytes,
        tracked_paths=tracked_paths,
        repository_inventory_sha256=inventory_sha256,
    )


def _repository_head(repository_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _tracked_paths(repository_root: Path, expected_head: str) -> tuple[bytes, ...] | None:
    try:
        completed = subprocess.run(
            ("git", "ls-tree", "-r", "-z", "--name-only", expected_head),
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=False,
        )
    except OSError:
        return None
    if completed.returncode != 0 or not isinstance(completed.stdout, bytes):
        return None
    if not completed.stdout.endswith(b"\0"):
        return None
    paths = tuple(completed.stdout[:-1].split(b"\0"))
    for path in paths:
        candidate = PurePosixPath(os.fsdecode(path))
        if not path or candidate.is_absolute() or ".." in candidate.parts:
            return None
    return paths


def _repository_inventory(repository_root: Path, tracked_paths: tuple[bytes, ...]) -> str | None:
    digest = hashlib.sha256()
    for tracked_path in tracked_paths:
        working_path = repository_root / os.fsdecode(tracked_path)
        try:
            if working_path.is_symlink():
                contents = os.fsencode(os.readlink(working_path))
            elif working_path.is_file():
                contents = working_path.read_bytes()
            else:
                return None
        except OSError:
            return None
        digest.update(tracked_path)
        digest.update(b"\0")
        digest.update(contents)
        digest.update(b"\0")
    return digest.hexdigest()


def _repository_is_dirty(repository_root: Path) -> bool:
    try:
        completed = subprocess.run(
            ("git", "status", "--porcelain=v1", "--untracked-files=all"),
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return True
    return completed.returncode != 0 or completed.stdout != ""


def _authoritative_peak_process_bytes() -> int | None:
    if sys.platform == "win32":
        return _windows_peak_process_bytes()
    if sys.platform.startswith("linux"):
        return _linux_peak_process_bytes()
    return None


def _linux_peak_process_bytes() -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmHWM:"):
                fields = line.split()
                if len(fields) == 3 and fields[2] == "kB":
                    return int(fields[1]) * 1024
    except (OSError, ValueError):
        return None
    return None


def _windows_peak_process_bytes() -> int | None:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.argtypes = ()
        get_current_process.restype = ctypes.c_void_p
        get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            ctypes.c_ulong,
        )
        get_process_memory_info.restype = ctypes.c_int
        process = get_current_process()
        success = get_process_memory_info(process, ctypes.byref(counters), counters.cb)
    except (AttributeError, OSError):
        return None
    return int(counters.PeakWorkingSetSize) if success else None
