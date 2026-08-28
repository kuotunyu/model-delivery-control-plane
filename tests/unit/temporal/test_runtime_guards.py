from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

import mdcp.temporal.runtime_guards as runtime_guards
from mdcp.temporal.runner import DevelopmentStateMachine
from mdcp.temporal.runtime_guards import (
    RuntimeGuard,
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


def test_pure_state_machine_accepts_no_runtime_guard_or_probe() -> None:
    assert tuple(inspect.signature(DevelopmentStateMachine).parameters) == ()
    for method_name in ("next_fit_request", "record_fit_result", "finalize"):
        parameters = set(
            inspect.signature(getattr(DevelopmentStateMachine, method_name)).parameters
        )
        assert parameters.isdisjoint({"guard", "probe", "clock", "memory"})


def test_synthetic_guard_is_not_a_production_runtime_guard(tmp_path: Path) -> None:
    guard = guarded_fixture(tmp_path, "clean")

    assert not isinstance(guard, RuntimeGuard)


def test_runtime_guard_rejects_a_forged_authoritative_core(tmp_path: Path) -> None:
    expected_head = _committed_repository(tmp_path)
    forged_core = runtime_guards._RuntimeGuardCore(
        evidence_class="authoritative_runtime",
        repository_root=tmp_path,
        expected_head=expected_head,
        start_ns=0,
        monotonic_ns=lambda: 1,
        peak_process_bytes=lambda: 0,
        tracked_paths=(),
        repository_inventory_sha256="forged",
    )

    with pytest.raises(TypeError):
        RuntimeGuard(forged_core)


def test_module_exposes_no_production_builder_accepting_a_caller_core() -> None:
    missing_name = "_build_authoritative_runtime_guard"
    with pytest.raises(AttributeError):
        getattr(runtime_guards, missing_name)


def test_production_runtime_guard_core_cannot_be_replaced(tmp_path: Path) -> None:
    expected_head = _committed_repository(tmp_path)
    guard = build_production_runtime_guard(tmp_path, expected_head)

    with pytest.raises(AttributeError):
        guard._core = object()  # type: ignore[attr-defined]


def test_runtime_guard_detects_a_tracked_filename_containing_a_newline(tmp_path: Path) -> None:
    _committed_repository(tmp_path)
    tracked_path = tmp_path / "tracked\nname.txt"
    try:
        tracked_path.write_text("initial\n", encoding="utf-8")
    except OSError:
        pytest.skip("newline-containing filenames are unavailable in this test environment")
    _git(tmp_path, "add", tracked_path.name)
    _git(
        tmp_path,
        "-c",
        "user.name=runtime-guard-test",
        "-c",
        "user.email=runtime-guard-test@example.invalid",
        "commit",
        "-m",
        "newline-path",
    )
    expected_head = _git(tmp_path, "rev-parse", "HEAD")
    guard = _build_synthetic_runtime_guard(
        tmp_path,
        expected_head,
        monotonic_ns=iter((0, 1)).__next__,
        peak_process_bytes=lambda: 0,
    )
    tracked_path.write_text("changed\n", encoding="utf-8")

    result = guard.checkpoint(RuntimeStage.POST_FIT)

    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == ("REPOSITORY_BYTES_CHANGED",)


def test_runtime_guard_inventories_tracked_symlink_bytes(
    tmp_path: Path,
) -> None:
    expected_head = _committed_repository(tmp_path)
    target_path = tmp_path / "first.txt"
    link_path = tmp_path / "tracked-link.txt"
    try:
        link_path.symlink_to(target_path.name)
    except OSError:
        pytest.skip("creating a symlink is unavailable in this test environment")
    _git(tmp_path, "add", link_path.name)
    _git(
        tmp_path,
        "-c",
        "user.name=runtime-guard-test",
        "-c",
        "user.email=runtime-guard-test@example.invalid",
        "commit",
        "-m",
        "symlink-path",
    )
    expected_head = _git(tmp_path, "rev-parse", "HEAD")
    guard = _build_synthetic_runtime_guard(
        tmp_path,
        expected_head,
        monotonic_ns=iter((0, 1)).__next__,
        peak_process_bytes=lambda: 0,
    )
    link_path.unlink()
    link_path.symlink_to("second.txt")

    result = guard.checkpoint(RuntimeStage.POST_FIT)

    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == ("REPOSITORY_BYTES_CHANGED",)


def test_runtime_guard_fails_closed_when_construction_inventory_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_head = _committed_repository(tmp_path)
    monkeypatch.setattr(runtime_guards, "_tracked_paths", lambda *_: None)
    guard = _build_synthetic_runtime_guard(
        tmp_path,
        expected_head,
        monotonic_ns=iter((0, 1)).__next__,
        peak_process_bytes=lambda: 0,
    )

    result = guard.checkpoint(RuntimeStage.POST_FIT)

    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == ("REPOSITORY_BYTES_UNAVAILABLE",)


def test_runtime_guard_rechecks_head_after_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_head = _committed_repository(tmp_path)
    guard = _build_synthetic_runtime_guard(
        tmp_path,
        expected_head,
        monotonic_ns=iter((0, 1)).__next__,
        peak_process_bytes=lambda: 0,
    )
    heads = iter((expected_head, "moved-after-inventory"))
    monkeypatch.setattr(runtime_guards, "_repository_head", lambda _: next(heads))

    result = guard.checkpoint(RuntimeStage.POST_FIT)

    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == ("REPOSITORY_IDENTITY_CHANGED",)


def test_runtime_guard_rechecks_head_after_final_dirty_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_head = _committed_repository(tmp_path)
    guard = _build_synthetic_runtime_guard(
        tmp_path,
        expected_head,
        monotonic_ns=iter((0, 1)).__next__,
        peak_process_bytes=lambda: 0,
    )
    heads = iter((expected_head, expected_head, "moved-during-final-status"))
    monkeypatch.setattr(runtime_guards, "_repository_head", lambda _: next(heads))

    result = guard.checkpoint(RuntimeStage.POST_FIT)

    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == ("REPOSITORY_IDENTITY_CHANGED",)


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
def test_runtime_checkpoint_fails_closed(tmp_path: Path, mutation: str, reason: str) -> None:
    guard = guarded_fixture(tmp_path, mutation)

    result = guard.checkpoint(RuntimeStage.POST_FIT)

    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == (reason,)
