from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
VERIFIER_PATH = REPOSITORY_ROOT / "scripts" / "verify-public-release.py"


def _load_verifier():
    assert VERIFIER_PATH.is_file(), "public release verifier is missing"
    spec = importlib.util.spec_from_file_location("mdcp_public_release_verifier", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_verifier_exposes_only_the_closed_public_contract() -> None:
    verifier = _load_verifier()

    assert tuple(sorted(verifier.PUBLIC_SURFACE_PATHS, key=str.encode)) == (
        verifier.PUBLIC_SURFACE_PATHS
    )
    assert len(verifier.PUBLIC_SURFACE_PATHS) == 8
    assert verifier.FORMAL_CLOSURE_COMMIT == "b1bb0d80cd40e6f39372c0a45892500cc9530712"
    assert verifier.FORMAL_CLOSURE_PARENT == "407f68b63c06a17ef54d5ec17722ef1f801b1689"


@pytest.mark.parametrize(
    "raw",
    (
        b"{}",
        b'{"unknown":true}',
        b"\xef\xbb\xbf{}",
        b'{"schema_version":"mdcp.local-release-readiness.v1"} ',
    ),
)
def test_readiness_parser_fails_closed_with_fixed_reason_codes(raw: bytes) -> None:
    verifier = _load_verifier()

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier.parse_readiness_bytes(raw)

    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID"
    assert "C:\\" not in str(error.value)


def test_regular_reader_and_link_verifier_fail_with_fixed_codes(tmp_path: Path) -> None:
    verifier = _load_verifier()

    with pytest.raises(verifier.PublicReleaseError) as missing:
        verifier._read_regular(tmp_path, "missing.md")
    assert missing.value.reason_code == "PUBLIC_RELEASE_SLICE_FILE_INVALID"

    for logical_path in verifier.PUBLIC_MARKDOWN_PATHS:
        target = tmp_path / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("[escape](../outside.md)", encoding="utf-8")

    with pytest.raises(verifier.PublicReleaseError) as escaped:
        verifier.verify_document_links(tmp_path)
    assert escaped.value.reason_code == "PUBLIC_RELEASE_SLICE_LINK_INVALID"


def test_git_runner_sanitizes_process_start_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_verifier()

    def fail_to_start(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("private path must not escape")

    monkeypatch.setattr(verifier.subprocess, "run", fail_to_start)

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier._git(tmp_path, "rev-parse", "HEAD")

    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_GIT_INVALID"
    assert "private path" not in str(error.value)


def _run_git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=10,
    ).stdout.strip()


def test_git_runner_ignores_replacement_refs(tmp_path: Path) -> None:
    verifier = _load_verifier()
    repository = tmp_path / "repository"
    repository.mkdir()
    _run_git(repository, "init", "--quiet")

    surface = repository / "surface.txt"
    surface.write_bytes(b"original")
    _run_git(repository, "add", "surface.txt")
    _run_git(
        repository,
        "-c",
        "user.name=Public Release Test",
        "-c",
        "user.email=public-release@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "original",
    )
    original_commit = _run_git(repository, "rev-parse", "HEAD").decode("ascii")

    surface.write_bytes(b"replacement")
    _run_git(repository, "add", "surface.txt")
    _run_git(
        repository,
        "-c",
        "user.name=Public Release Test",
        "-c",
        "user.email=public-release@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "replacement",
    )
    replacement_commit = _run_git(repository, "rev-parse", "HEAD").decode("ascii")
    _run_git(repository, "replace", original_commit, replacement_commit)

    assert _run_git(repository, "show", f"{original_commit}:surface.txt") == b"replacement"
    assert verifier._git(repository, "show", f"{original_commit}:surface.txt") == b"original"


def _create_directory_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError:
        if os.name != "nt":
            raise
    subprocess.run(
        ("cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)),
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=10,
    )


def test_regular_reader_rejects_intermediate_directory_link(tmp_path: Path) -> None:
    verifier = _load_verifier()
    root = tmp_path / "root"
    root.mkdir()
    actual = root / "actual"
    actual.mkdir()
    (actual / "private.txt").write_bytes(b"must not be read through a link")

    linked_directory = root / "docs"
    _create_directory_link(linked_directory, actual)

    with pytest.raises(verifier.PublicReleaseError) as linked:
        verifier._read_regular(root, "docs/private.txt")
    assert linked.value.reason_code == "PUBLIC_RELEASE_SLICE_FILE_INVALID"


@pytest.mark.parametrize("logical_path", (".", "nested/file.txt:stream"))
def test_regular_reader_sanitizes_nonportable_paths(tmp_path: Path, logical_path: str) -> None:
    verifier = _load_verifier()

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier._read_regular(tmp_path, logical_path)

    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_PATH_INVALID"


def test_link_verifier_allows_contained_parent_segments_and_rejects_underflow(
    tmp_path: Path,
) -> None:
    verifier = _load_verifier()
    root = tmp_path / "root"
    for logical_path in verifier.PUBLIC_MARKDOWN_PATHS:
        target = root / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    evidence = root / "evidence" / "readiness.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}", encoding="utf-8")
    quickstart = root / "docs" / "reviewer" / "quickstart.md"
    quickstart.write_text(
        "[readiness](../../evidence/readiness.json)",
        encoding="utf-8",
    )

    verifier.verify_document_links(root)

    quickstart.write_text("[escape](../../../outside.md)", encoding="utf-8")
    with pytest.raises(verifier.PublicReleaseError) as underflow:
        verifier.verify_document_links(root)
    assert underflow.value.reason_code == "PUBLIC_RELEASE_SLICE_LINK_INVALID"
