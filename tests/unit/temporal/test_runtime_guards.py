from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

from mdcp.temporal.runtime_guards import (
    RuntimeStage,
    _build_synthetic_runtime_guard,
    build_production_runtime_guard,
)


def _git(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _committed_repository(repository_root: Path) -> str:
    _git(repository_root, "init")
    (repository_root / "first.txt").write_text("first\n", encoding="utf-8")
    (repository_root / "second.txt").write_text("second\n", encoding="utf-8")
    _git(repository_root, "add", "first.txt", "second.txt")
    _git(
        repository_root,
        "-c",
        "user.name=runtime-guard-test",
        "-c",
        "user.email=runtime-guard-test@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    return _git(repository_root, "rev-parse", "HEAD")


def guarded_fixture(tmp_path: Path, mutation: str):
    expected_head = _committed_repository(tmp_path)
    clock_values = [0, 1]
    if mutation == "elapsed_over_21600s":
        clock_values[-1] = 21_600_000_000_001
    peak_values: list[int | None] = [0]
    if mutation == "missing_peak":
        peak_values[0] = None
    if mutation == "peak_over_4_gib":
        peak_values[0] = 4 * 1024**3 + 1

    def monotonic_ns() -> int:
        return clock_values.pop(0)

    def peak_process_bytes() -> int | None:
        return peak_values.pop(0)

    guard = _build_synthetic_runtime_guard(
        tmp_path,
        expected_head,
        monotonic_ns=monotonic_ns,
        peak_process_bytes=peak_process_bytes,
    )
    if mutation == "head_changed":
        (tmp_path / "first.txt").write_text("replacement\n", encoding="utf-8")
        _git(tmp_path, "add", "first.txt")
        _git(
            tmp_path,
            "-c",
            "user.name=runtime-guard-test",
            "-c",
            "user.email=runtime-guard-test@example.invalid",
            "commit",
            "-m",
            "changed-head",
        )
    if mutation == "tracked_byte_changed":
        (tmp_path / "first.txt").write_text("replacement\n", encoding="utf-8")
    if mutation == "dirty_untracked":
        (tmp_path / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    return guard


def test_production_guard_has_no_public_probe_injection() -> None:
    signature = inspect.signature(build_production_runtime_guard)
    assert tuple(signature.parameters) == ("repository_root", "expected_head")


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing_peak", "AUTHORITATIVE_MEMORY_UNAVAILABLE"),
        ("peak_over_4_gib", "COMPUTE_MEMORY_EXCEEDED"),
        ("elapsed_over_21600s", "COMPUTE_DEADLINE_EXCEEDED"),
        ("head_changed", "REPOSITORY_IDENTITY_CHANGED"),
        ("tracked_byte_changed", "REPOSITORY_BYTES_CHANGED"),
        ("dirty_untracked", "REPOSITORY_DIRTY"),
    ],
)
def test_runtime_checkpoint_fails_closed(
    tmp_path: Path, mutation: str, reason: str
) -> None:
    guard = guarded_fixture(tmp_path, mutation)

    result = guard.checkpoint(RuntimeStage.POST_FIT)

    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == (reason,)
