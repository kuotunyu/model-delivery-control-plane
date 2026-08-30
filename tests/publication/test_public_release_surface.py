from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mdcp.temporal.evidence import public_evidence_violations

REPOSITORY_ROOT = Path(__file__).parents[2]
VERIFIER_PATH = REPOSITORY_ROOT / "scripts" / "verify-public-release.py"
DEMO_PATH = REPOSITORY_ROOT / "scripts" / "reviewer-demo.py"
DEMO_SUCCESS_LINES = (
    "MDCP_DEMO_PASS case=baseline",
    "MDCP_DEMO_REJECT case=remote_release_claim reason=PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID",
    "MDCP_DEMO_REJECT case=public_surface_tamper reason=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH",
    "MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0",
)
PUBLIC_DOCUMENTS = (
    "LICENSE",
    "README.md",
    "docs/architecture.md",
    "docs/reviewer/quickstart.md",
    "docs/reviewer/release-evidence.md",
)


def _load_verifier():
    assert VERIFIER_PATH.is_file(), "public release verifier is missing"
    spec = importlib.util.spec_from_file_location("mdcp_public_release_verifier", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_demo():
    assert DEMO_PATH.is_file(), "reviewer demo is missing"
    spec = importlib.util.spec_from_file_location("mdcp_reviewer_demo", DEMO_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_demo_cli(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        (
            sys.executable,
            str(DEMO_PATH),
            "--repository-root",
            str(REPOSITORY_ROOT),
            *arguments,
        ),
        cwd=REPOSITORY_ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        env=environment,
    )


def test_verifier_exposes_only_the_closed_public_contract() -> None:
    verifier = _load_verifier()

    assert verifier.PUBLIC_SURFACE_PATHS == (
        "LICENSE",
        "README.md",
        "docs/architecture.md",
        "docs/reviewer/quickstart.md",
        "docs/reviewer/release-evidence.md",
        "schemas/portfolio/local-release-readiness.schema.json",
        "scripts/reviewer-demo.py",
        "scripts/reviewer-fast-path.ps1",
        "scripts/verify-public-release.py",
    )
    assert tuple(sorted(verifier.PUBLIC_SURFACE_PATHS, key=str.encode)) == (
        verifier.PUBLIC_SURFACE_PATHS
    )
    assert verifier.READINESS_PATH not in verifier.PUBLIC_SURFACE_PATHS
    assert verifier.FORMAL_CLOSURE_COMMIT == "b1bb0d80cd40e6f39372c0a45892500cc9530712"
    assert verifier.FORMAL_CLOSURE_PARENT == "407f68b63c06a17ef54d5ec17722ef1f801b1689"


def test_reviewer_demo_has_lf_attributes_in_git() -> None:
    attributes = _run_git(
        REPOSITORY_ROOT,
        "check-attr",
        "text",
        "eol",
        "--",
        "scripts/reviewer-demo.py",
    ).decode("utf-8", errors="strict")

    assert attributes.splitlines() == [
        "scripts/reviewer-demo.py: text: set",
        "scripts/reviewer-demo.py: eol: lf",
    ]

    lookalikes = _run_git(
        REPOSITORY_ROOT,
        "check-attr",
        "text",
        "eol",
        "--",
        "scripts/reviewer-demo-sibling.py",
        "nested/scripts/reviewer-demo.py",
    ).decode("utf-8", errors="strict")
    assert lookalikes.splitlines() == [
        "scripts/reviewer-demo-sibling.py: text: unspecified",
        "scripts/reviewer-demo-sibling.py: eol: unspecified",
        "nested/scripts/reviewer-demo.py: text: unspecified",
        "nested/scripts/reviewer-demo.py: eol: unspecified",
    ]


def test_reviewer_demo_disables_bytecode_writes_from_verifier_load(tmp_path: Path) -> None:
    demo_path = tmp_path / "reviewer-demo.py"
    verifier_path = tmp_path / "verify-public-release.py"
    shutil.copyfile(DEMO_PATH, demo_path)
    shutil.copyfile(VERIFIER_PATH, verifier_path)
    environment = os.environ.copy()
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    environment.pop("PYTHONPYCACHEPREFIX", None)
    before_repository = _run_git(
        REPOSITORY_ROOT, "status", "--porcelain=v1", "--untracked-files=all"
    )
    before_temporary_state = tuple(
        sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    )

    completed = subprocess.run(
        (
            sys.executable,
            str(demo_path),
            "--repository-root",
            str(REPOSITORY_ROOT),
        ),
        cwd=REPOSITORY_ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        env=environment,
    )

    assert completed.returncode == 0
    assert completed.stdout.decode("utf-8", errors="strict").splitlines() == list(
        DEMO_SUCCESS_LINES
    )
    assert completed.stderr == b""
    assert _run_git(REPOSITORY_ROOT, "status", "--porcelain=v1", "--untracked-files=all") == (
        before_repository
    )
    assert tuple(sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))) == (
        before_temporary_state
    )


def test_reviewer_demo_emits_only_the_exact_buffered_success_terminals() -> None:
    before = _run_git(REPOSITORY_ROOT, "status", "--porcelain=v1", "--untracked-files=all")

    completed = _run_demo_cli()

    after = _run_git(REPOSITORY_ROOT, "status", "--porcelain=v1", "--untracked-files=all")
    assert completed.returncode == 0
    assert completed.stdout.decode("utf-8", errors="strict").splitlines() == list(
        DEMO_SUCCESS_LINES
    )
    assert completed.stderr == b""
    assert after == before


def test_reviewer_demo_removes_its_temporary_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = _load_demo()
    original = demo.tempfile.TemporaryDirectory
    temporary_paths: list[Path] = []

    def tracked_temporary_directory(*args: object, **kwargs: object):
        directory = original(*args, **kwargs)
        temporary_paths.append(Path(directory.name))
        return directory

    monkeypatch.setattr(demo.tempfile, "TemporaryDirectory", tracked_temporary_directory)

    assert demo.run_demo(REPOSITORY_ROOT) == DEMO_SUCCESS_LINES
    assert len(temporary_paths) == 1
    assert all(not path.exists() for path in temporary_paths)


def test_reviewer_demo_rejection_contract_rejects_pass_wrong_reason_and_exception() -> None:
    demo = _load_demo()
    verifier = demo._load_verifier()

    with pytest.raises(demo.DemoFailure) as unexpected_pass:
        demo._expect_rejection(verifier, lambda: None, "EXPECTED")
    assert unexpected_pass.value.reason == "MDCP_REVIEWER_DEMO_CASE_INVALID"

    def wrong_reason() -> None:
        raise verifier.PublicReleaseError("WRONG")

    with pytest.raises(demo.DemoFailure) as mismatch:
        demo._expect_rejection(verifier, wrong_reason, "EXPECTED")
    assert mismatch.value.reason == "MDCP_REVIEWER_DEMO_CASE_INVALID"

    def unexpected_exception() -> None:
        raise RuntimeError("C:/private/raw-exception")

    with pytest.raises(demo.DemoFailure) as internal:
        demo._expect_rejection(verifier, unexpected_exception, "EXPECTED")
    assert internal.value.reason == "MDCP_REVIEWER_DEMO_INTERNAL"


def test_reviewer_demo_sanitizes_malformed_arguments_without_partial_pass() -> None:
    completed = _run_demo_cli("--private-token", "C:/private/secret")

    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr == (b"MDCP_REVIEWER_DEMO_FAIL reason=MDCP_REVIEWER_DEMO_INTERNAL\n")
    assert b"private" not in completed.stderr


@pytest.mark.parametrize("argument", ("-h", "--help"))
def test_reviewer_demo_sanitizes_help_flags_without_partial_output(argument: str) -> None:
    completed = _run_demo_cli(argument)

    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr == (b"MDCP_REVIEWER_DEMO_FAIL reason=MDCP_REVIEWER_DEMO_INTERNAL\n")


def test_reviewer_demo_state_guard_overrides_buffered_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = _load_demo()
    states = iter((b"", b"?? changed.txt\n"))
    monkeypatch.setattr(demo, "_repository_state", lambda *_args: next(states))
    monkeypatch.setattr(demo, "_run_cases", lambda *_args: DEMO_SUCCESS_LINES)

    with pytest.raises(demo.DemoFailure) as error:
        demo.run_demo(REPOSITORY_ROOT)

    assert error.value.reason == "MDCP_REVIEWER_DEMO_STATE_CHANGED"


@pytest.mark.parametrize(
    ("behavior", "expected_reason"),
    (
        ("baseline", "MDCP_REVIEWER_DEMO_BASELINE_INVALID"),
        ("case", "MDCP_REVIEWER_DEMO_CASE_INVALID"),
        ("internal", "MDCP_REVIEWER_DEMO_INTERNAL"),
    ),
)
def test_reviewer_demo_cli_buffers_all_case_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    behavior: str,
    expected_reason: str,
) -> None:
    demo = _load_demo()
    monkeypatch.setattr(demo, "_repository_state", lambda *_args: b"")

    def fail_cases(*_args: object) -> tuple[str, ...]:
        if behavior == "baseline":
            raise demo.DemoFailure(demo.BASELINE_INVALID)
        if behavior == "case":
            raise demo.DemoFailure(demo.CASE_INVALID)
        raise RuntimeError("C:/private/raw-exception")

    monkeypatch.setattr(demo, "_run_cases", fail_cases)

    assert demo.main(("--repository-root", str(REPOSITORY_ROOT))) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"MDCP_REVIEWER_DEMO_FAIL reason={expected_reason}\n"
    assert "private" not in captured.err


def test_reviewer_demo_uses_real_baseline_parser_and_temporary_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = _load_demo()
    verifier = demo._load_verifier()
    verify_calls: list[Path] = []
    parse_calls = 0
    real_verify = verifier.verify_public_release
    real_parse = verifier.parse_readiness_bytes

    def tracked_verify(root: Path):
        verify_calls.append(root)
        return real_verify(root)

    def tracked_parse(raw: bytes):
        nonlocal parse_calls
        parse_calls += 1
        return real_parse(raw)

    monkeypatch.setattr(verifier, "verify_public_release", tracked_verify)
    monkeypatch.setattr(verifier, "parse_readiness_bytes", tracked_parse)
    monkeypatch.setattr(demo, "_load_verifier", lambda: verifier)

    assert demo.run_demo(REPOSITORY_ROOT) == DEMO_SUCCESS_LINES
    assert parse_calls == 3
    assert len(verify_calls) == 2
    assert verify_calls[0] == REPOSITORY_ROOT
    assert verify_calls[1] != REPOSITORY_ROOT
    assert not verify_calls[1].exists()


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


def test_public_documents_exist_as_regular_nonlinks() -> None:
    for logical_path in PUBLIC_DOCUMENTS:
        path = REPOSITORY_ROOT / logical_path
        assert path.is_file()
        assert not path.is_symlink()


def test_readme_is_zh_tw_and_states_the_claim_ceiling() -> None:
    path = REPOSITORY_ROOT / "README.md"
    assert path.is_file()
    readme = path.read_text(encoding="utf-8")

    assert readme.startswith("<!-- lang: zh-TW -->\n")
    for required in (
        "offline score 不等於 deployment permission",
        "temporal regression",
        "H2",
        "SEALED_NOT_LOADED",
        "未執行 remote release",
        "不宣稱 Kubernetes production readiness",
        "不宣稱已實作 CV 或 LLM workload",
        "不宣稱 production HA、multi-region 或 disaster recovery",
        "沒有 real production incident evidence",
        "不宣稱支援任意 model framework 或 task",
    ):
        assert required in readme


def test_public_docs_do_not_present_designed_components_as_implemented() -> None:
    path = REPOSITORY_ROOT / "docs" / "architecture.md"
    assert path.is_file()
    architecture = path.read_text(encoding="utf-8")

    assert "Implemented verification path" in architecture
    assert "Designed deployment path" in architecture
    for component in ("control service", "router", "canary", "rollback", "recovery"):
        assert f"{component} | Designed only" in architecture


def test_public_documents_keep_production_and_workload_claims_negated() -> None:
    claim_tokens = (
        "production-ready",
        "Kubernetes-ready",
        "Kubernetes production readiness",
        "remote release completed",
        "production deployed",
        "H2 PASS",
        "CV workload implemented",
        "LLM workload implemented",
        "已實作 CV",
        "已實作 LLM",
    )
    negating_markers = (
        "未完成",
        "未執行",
        "不宣稱",
        "Designed only",
        "Not executed remotely",
    )
    for logical_path in PUBLIC_DOCUMENTS:
        path = REPOSITORY_ROOT / logical_path
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if any(token.casefold() in line.casefold() for token in claim_tokens):
                assert any(marker.casefold() in line.casefold() for marker in negating_markers)


def test_readme_heading_order_and_reviewer_setup_are_stable() -> None:
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPOSITORY_ROOT / "docs/reviewer/quickstart.md").read_text(encoding="utf-8")
    headings = (
        "## 30 秒理解這個專案",
        "## 目前完成度",
        "## 實際 implemented verification path",
        "## Reviewer fast path",
        "## Evidence 與安全邊界",
        "## Architecture 與程式碼導覽",
        "## 技術棧與測試",
        "## Claim ceiling",
        "## License",
    )

    assert tuple(readme.index(heading) for heading in headings) == tuple(
        sorted(readme.index(heading) for heading in headings)
    )
    assert "uv sync --frozen --group ml" in readme
    assert "uv sync --frozen --group ml" in quickstart
    assert "pwsh ./scripts/reviewer-fast-path.ps1" in quickstart
    assert "uv run --no-sync python scripts/verify-public-release.py" in quickstart


def test_evidence_taxonomy_and_license_qualifiers_are_explicit() -> None:
    guide = (REPOSITORY_ROOT / "docs/reviewer/release-evidence.md").read_text(encoding="utf-8")
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    license_text = (REPOSITORY_ROOT / "LICENSE").read_text(encoding="utf-8")

    for evidence_class in (
        "Historical formal closure evidence",
        "Local portfolio readiness evidence",
        "Synthetic fixture evidence",
        "Designed remote release-CI evidence",
        "不存在的 evidence",
    ):
        assert evidence_class in guide
    assert "LOCAL_PORTFOLIO_RELEASE_READY != REMOTE_RELEASED != PRODUCTION_READY" in guide
    assert "reported historical closure-review measurement" in guide
    assert "not authenticated by the closure commit" in guide
    assert license_text.startswith("MIT License\n\nCopyright (c) 2026 kuotunyu\n")
    assert "第三方 dependency、dataset 或其他材料仍保留其各自" in readme


def test_fast_path_is_fail_fast_offline_and_matches_the_documented_selector() -> None:
    path = REPOSITORY_ROOT / "scripts" / "reviewer-fast-path.ps1"
    assert path.is_file()
    script = path.read_text(encoding="utf-8")
    quickstart = (REPOSITORY_ROOT / "docs/reviewer/quickstart.md").read_text(encoding="utf-8")
    selected_tests = (
        "tests/publication/test_public_release_surface.py",
        "tests/publication/test_release_workflow.py",
        "tests/contract/workload/test_serving_identity_isolation.py",
        "tests/contract/workload/test_serving_identity_v2.py",
        "tests/unit/temporal/test_formal_worker_protocol.py",
        "tests/integration/temporal/test_formal_worker_process.py",
        "tests/security/temporal/test_public_evidence_boundary.py",
    )

    assert "Set-StrictMode -Version Latest" in script
    assert "$ErrorActionPreference = 'Stop'" in script
    assert "uv run --no-sync python scripts/verify-public-release.py" in script
    assert "uv run --no-sync python scripts/reviewer-demo.py" in script
    assert "uv run --no-sync pytest -p no:cacheprovider -q" in script
    assert script.index("verify-public-release.py") < script.index("pytest -p no:cacheprovider")
    assert script.index("verify-public-release.py") < script.index("reviewer-demo.py")
    assert script.index("reviewer-demo.py") < script.index("pytest -p no:cacheprovider")
    assert "PUBLIC_RELEASE_FAST_PATH_PASS" in script
    assert "uv sync" not in script
    for selected_test in selected_tests:
        assert selected_test in script
        assert selected_test in quickstart
    for prohibited in (
        "Invoke-WebRequest",
        "curl ",
        "docker ",
        "git push",
        "gh ",
        "prepare-search-freeze",
        "formal-run",
    ):
        assert prohibited.casefold() not in script.casefold()


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell unavailable")
@pytest.mark.parametrize("failing_call", (1, 2, 3))
def test_fast_path_detects_mutation_when_a_command_fails(tmp_path: Path, failing_call: int) -> None:
    repository = tmp_path / "repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    wrapper = scripts / "reviewer-fast-path.ps1"
    wrapper.write_bytes((REPOSITORY_ROOT / "scripts/reviewer-fast-path.ps1").read_bytes())
    escaped_repository = str(repository).replace("'", "''")
    harness = repository / "harness.ps1"
    harness.write_text(
        f"""$ErrorActionPreference = 'Stop'
$repository = '{escaped_repository}'
$startingLocation = (Get-Location).Path
$env:PYTHONDONTWRITEBYTECODE = 'original'
$script:gitCalls = 0
$script:uvCalls = 0
$script:uvArguments = @()

function git {{
    $script:gitCalls += 1
    if (Test-Path -LiteralPath (Join-Path $repository 'mutation.txt')) {{
        Write-Output '?? mutation.txt'
    }}
    $global:LASTEXITCODE = 0
}}

function uv {{
    $script:uvCalls += 1
    $script:uvArguments += ($args -join ' ')
    if ($script:uvCalls -eq {failing_call}) {{
        [IO.File]::WriteAllText((Join-Path $repository 'mutation.txt'), 'mutation')
        $global:LASTEXITCODE = 1
    }}
    else {{
        $global:LASTEXITCODE = 0
    }}
}}

try {{
    . (Join-Path $repository 'scripts/reviewer-fast-path.ps1')
    Write-Output 'UNEXPECTED_PASS'
}}
catch {{
    Write-Output "ERROR=$($_.Exception.Message)"
}}

Write-Output "UV_CALLS=$script:uvCalls"
Write-Output "UV_ARGUMENTS=$($script:uvArguments -join '|')"
Write-Output "GIT_CALLS=$script:gitCalls"
$locationRestored = ((Get-Location).Path -eq $startingLocation).ToString().ToLowerInvariant()
$bytecodeRestored = ($env:PYTHONDONTWRITEBYTECODE -eq 'original').ToString().ToLowerInvariant()
Write-Output "LOCATION_RESTORED=$locationRestored"
Write-Output "BYTECODE_RESTORED=$bytecodeRestored"
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        ("pwsh", "-NoProfile", "-File", str(harness)),
        cwd=tmp_path,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=20,
    )
    output = completed.stdout.decode("utf-8", errors="strict")

    assert completed.returncode == 0
    assert "ERROR=reviewer fast path changed repository state" in output
    assert f"UV_CALLS={failing_call}" in output
    expected_arguments = (
        "run --no-sync python scripts/verify-public-release.py --repository-root .",
        "run --no-sync python scripts/reviewer-demo.py --repository-root .",
        "run --no-sync pytest -p no:cacheprovider -q "
        "tests/publication/test_public_release_surface.py "
        "tests/publication/test_release_workflow.py "
        "tests/contract/workload/test_serving_identity_isolation.py "
        "tests/contract/workload/test_serving_identity_v2.py "
        "tests/unit/temporal/test_formal_worker_protocol.py "
        "tests/integration/temporal/test_formal_worker_process.py "
        "tests/security/temporal/test_public_evidence_boundary.py",
    )
    assert f"UV_ARGUMENTS={'|'.join(expected_arguments[:failing_call])}" in output
    assert "GIT_CALLS=2" in output
    assert "LOCATION_RESTORED=true" in output
    assert "BYTECODE_RESTORED=true" in output
    assert "UNEXPECTED_PASS" not in output


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell unavailable")
def test_fast_path_runs_verifier_demo_and_curated_tests_in_order(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    wrapper = scripts / "reviewer-fast-path.ps1"
    wrapper.write_bytes((REPOSITORY_ROOT / "scripts/reviewer-fast-path.ps1").read_bytes())
    escaped_repository = str(repository).replace("'", "''")
    harness = repository / "harness.ps1"
    harness.write_text(
        f"""$ErrorActionPreference = 'Stop'
$repository = '{escaped_repository}'
$startingLocation = (Get-Location).Path
$env:PYTHONDONTWRITEBYTECODE = 'original'
$script:gitCalls = 0
$script:uvCalls = 0
$script:uvArguments = @()

function git {{
    $script:gitCalls += 1
    $global:LASTEXITCODE = 0
}}

function uv {{
    $script:uvCalls += 1
    $script:uvArguments += ($args -join ' ')
    $global:LASTEXITCODE = 0
}}

try {{
    . (Join-Path $repository 'scripts/reviewer-fast-path.ps1')
    Write-Output 'PASS'
}}
catch {{
    Write-Output "ERROR=$($_.Exception.Message)"
}}

Write-Output "UV_CALLS=$script:uvCalls"
Write-Output "UV_ARGUMENTS=$($script:uvArguments -join '|')"
Write-Output "GIT_CALLS=$script:gitCalls"
$locationRestored = ((Get-Location).Path -eq $startingLocation).ToString().ToLowerInvariant()
$bytecodeRestored = ($env:PYTHONDONTWRITEBYTECODE -eq 'original').ToString().ToLowerInvariant()
Write-Output "LOCATION_RESTORED=$locationRestored"
Write-Output "BYTECODE_RESTORED=$bytecodeRestored"
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        ("pwsh", "-NoProfile", "-File", str(harness)),
        cwd=tmp_path,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=20,
    )
    output = completed.stdout.decode("utf-8", errors="strict")

    expected_arguments = (
        "run --no-sync python scripts/verify-public-release.py --repository-root .",
        "run --no-sync python scripts/reviewer-demo.py --repository-root .",
        "run --no-sync pytest -p no:cacheprovider -q "
        "tests/publication/test_public_release_surface.py "
        "tests/publication/test_release_workflow.py "
        "tests/contract/workload/test_serving_identity_isolation.py "
        "tests/contract/workload/test_serving_identity_v2.py "
        "tests/unit/temporal/test_formal_worker_protocol.py "
        "tests/integration/temporal/test_formal_worker_process.py "
        "tests/security/temporal/test_public_evidence_boundary.py",
    )

    assert completed.returncode == 0
    assert "PUBLIC_RELEASE_FAST_PATH_PASS evidence_class=local_portfolio mutations=0" in output
    assert "PASS" in output
    assert "ERROR=" not in output
    assert "UV_CALLS=3" in output
    assert f"UV_ARGUMENTS={'|'.join(expected_arguments)}" in output
    assert "GIT_CALLS=2" in output
    assert "LOCATION_RESTORED=true" in output
    assert "BYTECODE_RESTORED=true" in output


def test_checked_in_readiness_schema_matches_the_closed_model() -> None:
    verifier = _load_verifier()
    checked = json.loads((REPOSITORY_ROOT / verifier.SCHEMA_PATH).read_text(encoding="utf-8"))

    assert checked == verifier.LocalReleaseReadiness.model_json_schema()
    assert checked["additionalProperties"] is False


def test_readiness_evidence_is_canonical_public_and_binds_surface() -> None:
    verifier = _load_verifier()
    readiness = verifier.load_readiness(REPOSITORY_ROOT)

    assert readiness.public_surface_entries == verifier.build_public_surface_inventory(
        REPOSITORY_ROOT
    )
    assert public_evidence_violations(readiness.model_dump(mode="json")) == ()
    assert readiness.claim_execution.remote_release_executed is False
    assert readiness.claim_execution.h2_executed is False


def test_current_repository_public_release_slice_passes() -> None:
    verifier = _load_verifier()
    result = verifier.verify_public_release(REPOSITORY_ROOT)

    assert result.formal_closure_commit == verifier.FORMAL_CLOSURE_COMMIT


def _write_fixture_readiness(repository: Path, verifier: object) -> None:
    document = json.loads((REPOSITORY_ROOT / verifier.READINESS_PATH).read_text(encoding="utf-8"))
    entries = verifier.build_public_surface_inventory(repository)
    entry_documents = [entry.model_dump(mode="json") for entry in entries]
    document["public_surface_entries"] = entry_documents
    document["public_surface_inventory_sha256"] = verifier.sha256_hex(
        verifier.canonicalize_json(entry_documents)
    )
    model = verifier.LocalReleaseReadiness.model_validate(document)
    target = repository / verifier.READINESS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(verifier.canonicalize_json(model.model_dump(mode="json")))


def _copy_public_release_fixture(tmp_path: Path, verifier: object) -> Path:
    repository = tmp_path / "repository"
    for logical_path in verifier.PUBLIC_SURFACE_PATHS:
        source = REPOSITORY_ROOT / logical_path
        target = repository / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    for logical_path in verifier.PUBLIC_MARKDOWN_PATHS:
        (repository / logical_path).write_text("# Public fixture\n", encoding="utf-8")
    _write_fixture_readiness(repository, verifier)
    return repository


@pytest.mark.parametrize("mutation", ("missing", "directory_link"))
def test_public_surface_rejects_missing_or_linked_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    verifier = _load_verifier()
    repository = _copy_public_release_fixture(tmp_path, verifier)
    monkeypatch.setattr(verifier, "verify_git_closure", lambda *_args: None)

    if mutation == "missing":
        (repository / "LICENSE").unlink()
    else:
        external_docs = tmp_path / "external-docs"
        shutil.copytree(repository / "docs", external_docs)
        shutil.rmtree(repository / "docs")
        _create_directory_link(repository / "docs", external_docs)

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier.verify_public_release(repository)
    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_FILE_INVALID"


def test_public_surface_rejects_wrong_file_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_verifier()
    repository = _copy_public_release_fixture(tmp_path, verifier)
    monkeypatch.setattr(verifier, "verify_git_closure", lambda *_args: None)
    (repository / "README.md").write_text("# Mutated after inventory\n", encoding="utf-8")

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier.verify_public_release(repository)
    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH"


@pytest.mark.parametrize(
    "mutation",
    ("noncanonical", "unknown_field", "true_execution_claim", "wrong_h2_state"),
)
def test_readiness_mutations_fail_with_the_evidence_reason_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    verifier = _load_verifier()
    repository = _copy_public_release_fixture(tmp_path, verifier)
    monkeypatch.setattr(verifier, "verify_git_closure", lambda *_args: None)
    target = repository / verifier.READINESS_PATH
    document = json.loads(target.read_text(encoding="utf-8"))

    if mutation == "unknown_field":
        document["private_extension"] = False
    elif mutation == "true_execution_claim":
        document["claim_execution"]["remote_release_executed"] = True
    elif mutation == "wrong_h2_state":
        document["h2_status"] = "LOADED"
        document["h2_loaded_rows"] = 1
    raw = verifier.canonicalize_json(document)
    if mutation == "noncanonical":
        raw += b"\n"
    target.write_bytes(raw)

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier.verify_public_release(repository)
    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID"


def test_private_disclosure_gate_uses_the_fixed_reason_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_verifier()
    repository = _copy_public_release_fixture(tmp_path, verifier)
    monkeypatch.setattr(verifier, "verify_git_closure", lambda *_args: None)

    def report_private_path(document: dict[str, object]) -> tuple[str, ...]:
        mutated = {**document, "private_path": "C:/Users/private/secret"}
        return public_evidence_violations(mutated)

    monkeypatch.setattr(verifier, "public_evidence_violations", report_private_path)
    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier.verify_public_release(repository)
    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_DISCLOSURE"


def test_wrong_git_parent_uses_the_fixed_git_reason_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_verifier()
    repository = _copy_public_release_fixture(tmp_path, verifier)
    monkeypatch.setattr(verifier, "_git_text", lambda *_args: "0" * 40)

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier.verify_public_release(repository)
    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_GIT_INVALID"


@pytest.mark.parametrize("target", ("missing.md", "../repository-escape.md"))
def test_broken_or_escaping_relative_link_uses_the_fixed_link_reason_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    verifier = _load_verifier()
    repository = _copy_public_release_fixture(tmp_path, verifier)
    monkeypatch.setattr(verifier, "verify_git_closure", lambda *_args: None)
    (repository / "README.md").write_text(f"[invalid]({target})\n", encoding="utf-8")
    _write_fixture_readiness(repository, verifier)

    with pytest.raises(verifier.PublicReleaseError) as error:
        verifier.verify_public_release(repository)
    assert error.value.reason_code == "PUBLIC_RELEASE_SLICE_LINK_INVALID"


def test_public_surface_bytes_survive_a_fresh_autocrlf_checkout(tmp_path: Path) -> None:
    verifier = _load_verifier()
    source_repository = tmp_path / "source"
    source_repository.mkdir()
    _run_git(source_repository, "init", "--quiet")

    tracked_paths = (".gitattributes", *verifier.PUBLIC_SURFACE_PATHS)
    for logical_path in tracked_paths:
        source = REPOSITORY_ROOT / logical_path
        target = source_repository / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    _run_git(source_repository, "add", "--", *tracked_paths)
    _run_git(
        source_repository,
        "-c",
        "user.name=Public Release Test",
        "-c",
        "user.email=public-release@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "public surface fixture",
    )
    nested_attributes = _run_git(
        source_repository,
        "check-attr",
        "text",
        "eol",
        "--",
        "nested/LICENSE",
        "nested/README.md",
    ).decode("utf-8")
    assert nested_attributes.splitlines() == [
        "nested/LICENSE: text: unspecified",
        "nested/LICENSE: eol: unspecified",
        "nested/README.md: text: unspecified",
        "nested/README.md: eol: unspecified",
    ]

    checkout = tmp_path / "autocrlf-checkout"
    subprocess.run(
        (
            "git",
            "-c",
            "core.autocrlf=true",
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(source_repository),
            str(checkout),
        ),
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=20,
    )

    for logical_path in verifier.PUBLIC_SURFACE_PATHS:
        expected = (source_repository / logical_path).read_bytes()
        assert b"\r\n" not in expected
        assert (checkout / logical_path).read_bytes() == expected
