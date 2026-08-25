from __future__ import annotations

import ctypes
import hashlib
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
class RuntimeGuard:
    _repository_root: Path
    _expected_head: str
    _start_ns: int
    _monotonic_ns: Callable[[], int]
    _peak_process_bytes: Callable[[], int | None]
    _tracked_paths: tuple[str, ...]
    _repository_inventory_sha256: str

    def checkpoint(self, stage: RuntimeStage) -> RuntimeObservation:
        del stage
        elapsed_ns = self._monotonic_ns() - self._start_ns
        peak_process_bytes = self._peak_process_bytes()
        if type(peak_process_bytes) is not int or peak_process_bytes < 0:
            return self._unknown(
                "AUTHORITATIVE_MEMORY_UNAVAILABLE", elapsed_ns, peak_process_bytes
            )
        if peak_process_bytes > _MAX_PEAK_PROCESS_BYTES:
            return self._unknown("COMPUTE_MEMORY_EXCEEDED", elapsed_ns, peak_process_bytes)
        if type(elapsed_ns) is not int or elapsed_ns < 0 or elapsed_ns > _MAX_ELAPSED_NS:
            return self._unknown("COMPUTE_DEADLINE_EXCEEDED", elapsed_ns, peak_process_bytes)
        if _repository_head(self._repository_root) != self._expected_head:
            return self._unknown("REPOSITORY_IDENTITY_CHANGED", elapsed_ns, peak_process_bytes)
        inventory_sha256 = _repository_inventory(self._repository_root, self._tracked_paths)
        if inventory_sha256 != self._repository_inventory_sha256:
            return self._unknown("REPOSITORY_BYTES_CHANGED", elapsed_ns, peak_process_bytes)
        if _repository_is_dirty(self._repository_root):
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
            repository_inventory_sha256=self._repository_inventory_sha256,
        )


def build_production_runtime_guard(repository_root: Path, expected_head: str) -> RuntimeGuard:
    return _build_runtime_guard(
        repository_root,
        expected_head,
        monotonic_ns=time.monotonic_ns,
        peak_process_bytes=_authoritative_peak_process_bytes,
    )


def _build_synthetic_runtime_guard(
    repository_root: Path,
    expected_head: str,
    *,
    monotonic_ns: Callable[[], int],
    peak_process_bytes: Callable[[], int | None],
) -> RuntimeGuard:
    return _build_runtime_guard(
        repository_root,
        expected_head,
        monotonic_ns=monotonic_ns,
        peak_process_bytes=peak_process_bytes,
    )


def _build_runtime_guard(
    repository_root: Path,
    expected_head: str,
    *,
    monotonic_ns: Callable[[], int],
    peak_process_bytes: Callable[[], int | None],
) -> RuntimeGuard:
    tracked_paths = _tracked_paths(repository_root, expected_head)
    inventory_sha256 = _repository_inventory(repository_root, tracked_paths)
    return RuntimeGuard(
        _repository_root=repository_root,
        _expected_head=expected_head,
        _start_ns=monotonic_ns(),
        _monotonic_ns=monotonic_ns,
        _peak_process_bytes=peak_process_bytes,
        _tracked_paths=tracked_paths,
        _repository_inventory_sha256=inventory_sha256,
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


def _tracked_paths(repository_root: Path, expected_head: str) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ("git", "ls-tree", "-r", "--name-only", expected_head),
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ()
    if completed.returncode != 0:
        return ()
    paths = tuple(completed.stdout.splitlines())
    for path in paths:
        candidate = PurePosixPath(path)
        if not path or candidate.is_absolute() or ".." in candidate.parts:
            return ()
    return paths


def _repository_inventory(repository_root: Path, tracked_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for tracked_path in tracked_paths:
        working_path = repository_root / tracked_path
        try:
            if not working_path.is_file() or working_path.is_symlink():
                return ""
            contents = working_path.read_bytes()
        except OSError:
            return ""
        digest.update(tracked_path.encode("utf-8"))
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
        process = ctypes.windll.kernel32.GetCurrentProcess()
        success = ctypes.windll.psapi.GetProcessMemoryInfo(
            process, ctypes.byref(counters), counters.cb
        )
    except (AttributeError, OSError):
        return None
    return int(counters.PeakWorkingSetSize) if success else None
