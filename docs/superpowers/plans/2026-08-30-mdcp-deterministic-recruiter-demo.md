# MDCP Deterministic Recruiter Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cross-platform, read-only two-minute recruiter demo that proves one genuine public-release baseline PASS and two genuine fail-closed rejections without modifying repository state or overstating remote/production evidence.

**Architecture:** A new `scripts/reviewer-demo.py` dynamically loads the existing closed public-release verifier, buffers all success terminals, runs the canonical baseline, mutates a false remote-release claim in memory, mutates only temporary public-surface bytes, and emits output only after cleanup plus a fixed Git porcelain no-clobber check. The demo becomes the ninth evidence-bound public path, is integrated between the standalone verifier and curated tests in the PowerShell fast path, and is documented in zh-TW.

**Tech Stack:** Python 3.12, Pydantic 2, RFC 8785 canonical JSON, Git, PowerShell 7, pytest, Ruff, uv.

## Global Constraints

- Execute only in the existing linked worktree `D:\AI-Portfolio\CC_github部隊\model-delivery-control-plane\.worktrees\wave0-foundation-feasibility` on branch `codex/wave0-foundation-feasibility`.
- The approved design is commit `1932a4e557fb4902c690a7ba35fdf9b283503fce`; its parent is public-release closure commit `2707f98a3cd4c71843b74053c8400b127267ae55`.
- The approved design document is `docs/superpowers/specs/2026-08-30-mdcp-recruiter-demo-design.md`, SHA-256 `8209f381387462919ae5d1510ff60e6a7189995fadb575d78d09688f73b7d4b6`.
- The implementation allowlist after this plan commit is exactly nine paths:

```text
.gitattributes
README.md
docs/reviewer/quickstart.md
evidence/public/portfolio/local-release-readiness.json
schemas/portfolio/local-release-readiness.schema.json
scripts/reviewer-demo.py
scripts/reviewer-fast-path.ps1
scripts/verify-public-release.py
tests/publication/test_public_release_surface.py
```

- `schemas/portfolio/local-release-readiness.schema.json` is conditional: modify it only if `LocalReleaseReadiness.model_json_schema()` produces different bytes. A change to `PUBLIC_SURFACE_PATHS` alone is not a reason to manufacture a schema diff.
- Do not modify `src/mdcp`, temporal evidence, dependency files, models, workloads, workflow files, Docker/Compose files, private custody, any other repository, or the approved design spec.
- Do not create a remote, use network, install dependencies, push, merge, tag, create a release, execute a workflow, publish a package/image, run H2/data/model work, or claim CV/LLM workload implementation or Kubernetes production readiness.
- Preserve `uv.lock` SHA-256 `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`.
- Preserve v0.1 serving identity `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`, v0.2 serving identity `198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea`, 47-path source identity `cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b`, four-path worker identity `ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3`, and firewall identity `e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1`.
- Preserve historical receipt SHA-256 `5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63`, index SHA-256 `2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205`, H2 status `SEALED_NOT_LOADED`, and loaded rows `0`.
- Use `test-driven-development` for every behavior change. If any test or command fails unexpectedly, stop the implementation path, invoke `systematic-debugging`, identify the root cause, and correct only an allowlisted path.
- Before each commit, require a clean staged diff, exact author and committer `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`, Critical `0`, Important `0`, and all task-specific gates. Do not commit an intermediate state in which the new executable exists but is not bound into the public inventory.
- Generated `.hypothesis`, `.pytest_cache`, `__pycache__`, and bytecode are non-source. Inspect exact targets before removing only those generated paths; never let cleanup touch readiness or historical evidence.

---

### Task 0: Freeze the plan-entry baseline and protected tree

**Files:**
- Read: `docs/superpowers/specs/2026-08-30-mdcp-recruiter-demo-design.md`
- Read: `docs/superpowers/plans/2026-08-30-mdcp-deterministic-recruiter-demo.md`
- Modify: none

**Interfaces:**
- Consumes: approved design commit and the commit containing this plan.
- Produces: controller-held `$planEntry`, exact nine-path allowlist, protected Git tree map, and a fresh green baseline.

- [ ] **Step 1: Verify the immutable entry conditions**

```powershell
$expectedBranch = 'codex/wave0-foundation-feasibility'
$approvedDesign = '1932a4e557fb4902c690a7ba35fdf9b283503fce'
$approvedSpecSha256 = '8209f381387462919ae5d1510ff60e6a7189995fadb575d78d09688f73b7d4b6'
if ((git branch --show-current) -ne $expectedBranch) { throw 'BRANCH_MISMATCH' }
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) { throw 'WORKTREE_DIRTY' }
if (@(git remote).Count -ne 0) { throw 'REMOTE_DRIFT' }
if (@(git tag --points-at HEAD).Count -ne 0) { throw 'HEAD_TAGGED' }
$planEntry = (git rev-parse HEAD).Trim()
if ((git rev-parse "$planEntry^").Trim() -ne $approvedDesign) { throw 'PLAN_PARENT_MISMATCH' }
$specSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath 'docs/superpowers/specs/2026-08-30-mdcp-recruiter-demo-design.md').Hash.ToLowerInvariant()
if ($specSha256 -ne $approvedSpecSha256) { throw 'SPEC_DIGEST_MISMATCH' }
```

Expected: every check passes. Keep `$planEntry` in controller memory for all later range and protected-tree gates.

- [ ] **Step 2: Freeze the exact implementation allowlist and every protected tree entry**

```powershell
$allowlist = @(
  '.gitattributes',
  'README.md',
  'docs/reviewer/quickstart.md',
  'evidence/public/portfolio/local-release-readiness.json',
  'schemas/portfolio/local-release-readiness.schema.json',
  'scripts/reviewer-demo.py',
  'scripts/reviewer-fast-path.ps1',
  'scripts/verify-public-release.py',
  'tests/publication/test_public_release_surface.py'
)
if ($allowlist.Count -ne 9) { throw 'ALLOWLIST_COUNT_INVALID' }
if (@($allowlist | Sort-Object -Unique).Count -ne 9) { throw 'ALLOWLIST_DUPLICATE' }
$protected = @{}
foreach ($line in @(git ls-tree -r $planEntry)) {
    $parts = $line -split "`t", 2
    if ($parts[1] -notin $allowlist) { $protected[$parts[1]] = $parts[0] }
}
```

Expected: all entry-tree paths outside the exact nine are frozen without writing an auxiliary file.

- [ ] **Step 3: Record the immutable schema and dependency baselines**

```powershell
$schemaBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath 'schemas/portfolio/local-release-readiness.schema.json').Hash.ToLowerInvariant()
if ($schemaBefore -ne '64b6e3f7ed29b13dce46114345ab9f8c0b176a852fc884139916c7ba0494f202') { throw 'SCHEMA_BASELINE_MISMATCH' }
$lockSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath 'uv.lock').Hash.ToLowerInvariant()
if ($lockSha256 -ne '781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae') { throw 'LOCK_DRIFT' }
```

- [ ] **Step 4: Run the pre-implementation baseline**

```powershell
uv run pytest -q
uv run ruff check scripts tests/publication
uv run ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
```

Expected: the existing suite remains green; the most recent known result is `1582 passed, 7 skipped`. Record the fresh count and duration in the task report, not in canonical readiness.

---

### Task 1: Build the buffered read-only demo with TDD

**Files:**
- Create: `scripts/reviewer-demo.py`
- Modify: `tests/publication/test_public_release_surface.py`

**Interfaces:**
- Consumes: `scripts/verify-public-release.py` through a fixed local module load.
- Produces: `run_demo(repository_root: Path) -> tuple[str, ...]` and `main(argv: Sequence[str] | None = None) -> int`.
- Success stdout is exactly four lines and is emitted only after all cases, cleanup, and no-clobber pass.
- Failure stdout is empty; stderr is one fixed `MDCP_REVIEWER_DEMO_FAIL` terminal.

- [ ] **Step 1: Add the demo test loader and exact CLI helper**

Add these constants and helpers near the current verifier loader in `tests/publication/test_public_release_surface.py`:

```python
DEMO_PATH = REPOSITORY_ROOT / "scripts" / "reviewer-demo.py"
DEMO_SUCCESS_LINES = (
    "MDCP_DEMO_PASS case=baseline",
    "MDCP_DEMO_REJECT case=remote_release_claim reason=PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID",
    "MDCP_DEMO_REJECT case=public_surface_tamper reason=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH",
    "MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0",
)


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
```

- [ ] **Step 2: Add RED subprocess, no-clobber, and cleanup tests**

```python
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
```

Run:

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'reviewer_demo_emits or reviewer_demo_removes'
```

Expected: RED because `scripts/reviewer-demo.py` does not exist.

- [ ] **Step 3: Add RED fixed-taxonomy and partial-output tests**

```python
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
    assert completed.stderr == (
        b"MDCP_REVIEWER_DEMO_FAIL reason=MDCP_REVIEWER_DEMO_INTERNAL\n"
    )
    assert b"private" not in completed.stderr


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
```

Run the three tests and require RED only because the demo implementation is absent.

- [ ] **Step 4: Implement the minimal demo exactly**

Create `scripts/reviewer-demo.py` with this implementation shape. Keep the fixed strings and ordering exact; do not add plugin loading, callbacks, arbitrary commands, fixture-retention flags, verbose errors, or repository writes.

```python
from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from types import ModuleType

BASELINE_INVALID = "MDCP_REVIEWER_DEMO_BASELINE_INVALID"
CASE_INVALID = "MDCP_REVIEWER_DEMO_CASE_INVALID"
STATE_CHANGED = "MDCP_REVIEWER_DEMO_STATE_CHANGED"
INTERNAL = "MDCP_REVIEWER_DEMO_INTERNAL"
SUCCESS_LINES = (
    "MDCP_DEMO_PASS case=baseline",
    "MDCP_DEMO_REJECT case=remote_release_claim reason=PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID",
    "MDCP_DEMO_REJECT case=public_surface_tamper reason=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH",
    "MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0",
)


class DemoFailure(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ClosedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise DemoFailure(INTERNAL)


def _load_verifier() -> ModuleType:
    path = Path(__file__).with_name("verify-public-release.py")
    spec = importlib.util.spec_from_file_location("mdcp_reviewer_demo_verifier", path)
    if spec is None or spec.loader is None:
        raise DemoFailure(INTERNAL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        raise DemoFailure(INTERNAL) from None
    return module


def _repository_state(verifier: ModuleType, root: Path) -> bytes:
    return verifier._git(root, "status", "--porcelain=v1", "--untracked-files=all")


def _expect_rejection(
    verifier: ModuleType,
    operation: Callable[[], object],
    expected_reason: str,
) -> None:
    try:
        operation()
    except verifier.PublicReleaseError as error:
        if error.reason_code != expected_reason:
            raise DemoFailure(CASE_INVALID) from None
        return
    except DemoFailure:
        raise
    except Exception:
        raise DemoFailure(INTERNAL) from None
    raise DemoFailure(CASE_INVALID)


def _copy_public_fixture(verifier: ModuleType, root: Path, destination: Path) -> None:
    for logical_path in (*verifier.PUBLIC_SURFACE_PATHS, verifier.READINESS_PATH):
        raw = verifier._read_regular(root, logical_path)
        target = destination.joinpath(*PurePosixPath(logical_path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def _run_cases(verifier: ModuleType, root: Path) -> tuple[str, ...]:
    try:
        readiness = verifier.verify_public_release(root)
    except verifier.PublicReleaseError:
        raise DemoFailure(BASELINE_INVALID) from None

    document = readiness.model_dump(mode="json")
    claim_execution = dict(document["claim_execution"])
    claim_execution["remote_release_executed"] = True
    document["claim_execution"] = claim_execution
    false_claim = verifier.canonicalize_json(document)
    _expect_rejection(
        verifier,
        lambda: verifier.parse_readiness_bytes(false_claim),
        "PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID",
    )

    try:
        with tempfile.TemporaryDirectory(prefix="mdcp-reviewer-demo-") as raw_directory:
            temporary_root = Path(raw_directory)
            _copy_public_fixture(verifier, root, temporary_root)
            readme = temporary_root / "README.md"
            readme.write_bytes(readme.read_bytes() + b"\n<!-- mdcp reviewer demo tamper -->\n")
            _expect_rejection(
                verifier,
                lambda: verifier.verify_public_release(temporary_root),
                "PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH",
            )
    except DemoFailure:
        raise
    except verifier.PublicReleaseError:
        raise DemoFailure(CASE_INVALID) from None
    except Exception:
        raise DemoFailure(INTERNAL) from None

    return SUCCESS_LINES


def run_demo(repository_root: Path) -> tuple[str, ...]:
    verifier = _load_verifier()
    try:
        before = _repository_state(verifier, repository_root)
    except Exception:
        raise DemoFailure(INTERNAL) from None

    failure: DemoFailure | None = None
    lines: tuple[str, ...] = ()
    try:
        lines = _run_cases(verifier, repository_root)
    except DemoFailure as error:
        failure = error
    except Exception:
        failure = DemoFailure(INTERNAL)

    try:
        after = _repository_state(verifier, repository_root)
    except Exception:
        raise DemoFailure(STATE_CHANGED) from None
    if after != before:
        raise DemoFailure(STATE_CHANGED)
    if failure is not None:
        raise failure
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = ClosedArgumentParser()
        parser.add_argument("--repository-root", type=Path, default=Path.cwd())
        arguments = parser.parse_args(argv)
        lines = run_demo(arguments.repository_root)
    except DemoFailure as error:
        print(f"MDCP_REVIEWER_DEMO_FAIL reason={error.reason}", file=sys.stderr)
        return 1
    except Exception:
        print(f"MDCP_REVIEWER_DEMO_FAIL reason={INTERNAL}", file=sys.stderr)
        return 1

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

During implementation, Ruff may require a narrow typing adjustment around the dynamically loaded verifier or JSON object. Preserve the interfaces and behavior above; do not solve typing by adding `Any` across the module or by weakening the closed verifier.

- [ ] **Step 5: Prove that real verifier operations back all three cases**

Add an in-process regression that wraps the real verifier rather than replacing it with a fake:

```python
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
```

The three parser calls are the normal readiness parse inside the baseline verifier, the false-claim parse, and the readiness parse inside the temporary tamper verifier. The two verifier calls are the real repository baseline and the temporary tamper fixture.

- [ ] **Step 6: Run Task 1 GREEN and quality checks, but do not commit**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'reviewer_demo'
uv run ruff check scripts/reviewer-demo.py tests/publication/test_public_release_surface.py
uv run ruff format --check scripts/reviewer-demo.py tests/publication/test_public_release_surface.py
git diff --check
```

Expected: all demo-focused tests pass. The worktree is intentionally dirty and the existing readiness still describes eight paths. Do not commit this intermediate state; proceed directly to Task 2 so no commit exposes an unbound recruiter executable.

---

### Task 2: Bind the demo into the nine-path public identity and commit atomically

**Files:**
- Modify: `.gitattributes`
- Modify: `scripts/verify-public-release.py`
- Modify: `evidence/public/portfolio/local-release-readiness.json`
- Modify: `tests/publication/test_public_release_surface.py`
- Modify only if generated bytes differ: `schemas/portfolio/local-release-readiness.schema.json`
- Include uncommitted Task 1 files: `scripts/reviewer-demo.py`, `tests/publication/test_public_release_surface.py`

**Interfaces:**
- Evolves `PUBLIC_SURFACE_PATHS` from 8 to 9 in exact ASCII byte order.
- Keeps readiness outside its own inventory.
- Produces the first commit containing the demo only after the demo bytes are identity-bound.

- [ ] **Step 1: Add RED nine-path membership, order, acyclicity, and EOL assertions**

Change the existing public-contract test and add the EOL contract:

```python
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


def test_reviewer_demo_has_an_exact_non_wildcard_lf_rule() -> None:
    lines = (REPOSITORY_ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()

    assert "scripts/reviewer-demo.py text eol=lf" in lines
    assert not any("*" in line and "reviewer-demo.py" in line for line in lines)
```

Run:

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'closed_public_contract or exact_non_wildcard_lf'
```

Expected: RED because the verifier still exposes eight paths and `.gitattributes` lacks the exact demo rule.

- [ ] **Step 2: Make the minimal public-surface and EOL changes**

Insert `"scripts/reviewer-demo.py"` between the schema and PowerShell paths in `PUBLIC_SURFACE_PATHS`. Add exactly this root `.gitattributes` line, without a wildcard:

```text
scripts/reviewer-demo.py text eol=lf
```

Run the focused contract test again. Inventory/readiness tests should now fail with the old eight-path evidence; that is the expected RED for regeneration.

- [ ] **Step 3: Prove whether the generated JSON Schema changed**

Run this read-only comparison:

```powershell
uv run python -c "import importlib.util,json,sys; from pathlib import Path; p=Path('scripts/verify-public-release.py'); s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); checked=json.loads(Path(m.SCHEMA_PATH).read_text(encoding='utf-8')); generated=m.LocalReleaseReadiness.model_json_schema(); print('SCHEMA_EQUAL=' + str(checked == generated).lower())"
```

Expected: `SCHEMA_EQUAL=true`. Confirm the checked-in schema SHA-256 remains `$schemaBefore`. If it is false, inspect the actual generated delta, update the schema with exactly `json.dumps(generated, indent=2, sort_keys=True) + "\n"` through `apply_patch`, and record why the model schema changed. Do not edit the schema if the command reports true.

- [ ] **Step 4: Regenerate canonical readiness from the existing closed document**

Use a read-only print command based on the real model and the nine current surface files:

```powershell
uv run python -c "import importlib.util,json,sys; from pathlib import Path; p=Path('scripts/verify-public-release.py'); s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); d=json.loads(Path(m.READINESS_PATH).read_text(encoding='utf-8')); e=m.build_public_surface_inventory(Path('.')); ed=[x.model_dump(mode='json') for x in e]; d['public_surface_entries']=ed; d['public_surface_inventory_sha256']=m.sha256_hex(m.canonicalize_json(ed)); model=m.LocalReleaseReadiness.model_validate(d); raw=m.canonicalize_json(model.model_dump(mode='json')); print(raw.decode('utf-8')); print('READINESS_SHA256=' + m.sha256_hex(raw), file=sys.stderr)"
```

Apply the exact stdout JSON to `evidence/public/portfolio/local-release-readiness.json` with `apply_patch`, no BOM, whitespace, or terminal newline. Then independently require byte equality:

```powershell
uv run python -c "import importlib.util,json,sys; from pathlib import Path; p=Path('scripts/verify-public-release.py'); s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); d=json.loads(Path(m.READINESS_PATH).read_text(encoding='utf-8')); e=m.build_public_surface_inventory(Path('.')); ed=[x.model_dump(mode='json') for x in e]; d['public_surface_entries']=ed; d['public_surface_inventory_sha256']=m.sha256_hex(m.canonicalize_json(ed)); expected=m.canonicalize_json(m.LocalReleaseReadiness.model_validate(d).model_dump(mode='json')); actual=Path(m.READINESS_PATH).read_bytes(); assert actual == expected; print('READINESS_CANONICAL_MATCH')"
```

- [ ] **Step 5: Run the atomic binding gates**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
$elapsed = Measure-Command {
    uv run --no-sync python scripts/reviewer-demo.py --repository-root .
    if ($LASTEXITCODE -ne 0) { throw 'REVIEWER_DEMO_FAILED' }
}
if ($elapsed.TotalSeconds -gt 120) { throw 'DEMO_BUDGET_EXCEEDED' }
uv run ruff check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv run ruff format --check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
```

Expected: verifier prints `PUBLIC_RELEASE_SLICE_PASS`; demo prints the exact four lines; warm demo is at most 120 seconds; focused tests and static checks pass.

- [ ] **Step 6: Review and commit the first fully bound demo**

Require that the pending diff is a subset of these six paths and that the schema is absent unless Step 3 proved a generated change:

```text
.gitattributes
evidence/public/portfolio/local-release-readiness.json
schemas/portfolio/local-release-readiness.schema.json  # conditional
scripts/reviewer-demo.py
scripts/verify-public-release.py
tests/publication/test_public_release_surface.py
```

Review sanitized failure behavior, no repository writes, temporary-only mutation, exact Git arguments, real verifier reuse, inventory acyclicity, and claim ceiling. Require Critical `0`, Important `0`. Then stage only actual paths and commit:

```powershell
git add .gitattributes scripts/reviewer-demo.py scripts/verify-public-release.py evidence/public/portfolio/local-release-readiness.json tests/publication/test_public_release_surface.py
if ((git diff --name-only -- schemas/portfolio/local-release-readiness.schema.json).Length -ne 0) {
    git add schemas/portfolio/local-release-readiness.schema.json
}
git diff --cached --check
git commit -m "feat: add deterministic reviewer demo"
```

After committing, verify exact identity and a clean worktree. If commit identity differs from the approved identity, stop before further commits.

---

### Task 3: Integrate the demo into zh-TW reviewer documentation and the fast path

**Files:**
- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `scripts/reviewer-fast-path.ps1`
- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**
- Documents the shell-neutral two-minute proof in zh-TW.
- Runs verifier → demo → curated tests in that exact order.
- Preserves fail-fast, location restoration, `PYTHONDONTWRITEBYTECODE` restoration, and final repository-state comparison.

- [ ] **Step 1: Add RED documentation assertions**

Extend `test_readme_heading_order_and_reviewer_setup_are_stable` or add a focused test with these exact requirements:

```python
def test_reviewer_demo_command_and_claim_ceiling_are_documented() -> None:
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPOSITORY_ROOT / "docs/reviewer/quickstart.md").read_text(
        encoding="utf-8"
    )
    command = "uv run --no-sync python scripts/reviewer-demo.py --repository-root ."

    for document in (readme, quickstart):
        assert command in document
        assert "MDCP_DEMO_PASS case=baseline" in document
        assert "PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID" in document
        assert "PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH" in document
        assert "repository" in document
        assert "temporary" in document.casefold() or "暫存" in document
    assert "MDCP_REVIEWER_DEMO_PASS != REMOTE_RELEASED != PRODUCTION_READY" in quickstart
```

Run this test and require RED because neither document has the demo path yet.

- [ ] **Step 2: Add RED fast-path ordering and three-command fail-fast assertions**

Update the existing static test to require:

```python
assert "uv run --no-sync python scripts/verify-public-release.py" in script
assert "uv run --no-sync python scripts/reviewer-demo.py" in script
assert "uv run --no-sync pytest -p no:cacheprovider -q" in script
assert script.index("verify-public-release.py") < script.index("reviewer-demo.py")
assert script.index("reviewer-demo.py") < script.index("pytest -p no:cacheprovider")
```

Change the failure-path parametrization from `(1, 2)` to `(1, 2, 3)`. Keep the assertions `UV_CALLS={failing_call}`, `GIT_CALLS=2`, location restored, bytecode restored, mutation detected, and no unexpected PASS.

Run:

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'fast_path'
```

Expected: RED because the wrapper has only two `uv` calls.

- [ ] **Step 3: Insert the demo into the PowerShell wrapper**

Between the standalone verifier block and the pytest block, add exactly:

```powershell
    if ($null -eq $commandFailure) {
        & uv run --no-sync python scripts/reviewer-demo.py --repository-root .
        if ($LASTEXITCODE -ne 0) {
            $commandFailure = 'reviewer demo failed'
        }
    }
```

Do not change the existing `try/catch/finally`, state comparison, environment restoration, test selector, or final terminal.

- [ ] **Step 4: Add the concise zh-TW recruiter path**

In `README.md`, inside `## Reviewer fast path`, add a `### 2 分鐘 fail-closed demo` subsection after dependency setup and before the PowerShell fast path. Include the exact command, the one PASS plus two expected rejection meanings, and this explicit boundary:

```text
所有故意 mutation 都只發生在 memory 或 OS-managed temporary directory；demo 不會修改 repository 內的檔案。這是 local reviewer evidence，不是 remote release 或 production evidence。
```

In `docs/reviewer/quickstart.md`, insert `## 2 分鐘 fail-closed demo` before `## Level 1：Fast path（建議先跑）`. Include the exact command and exact four-line output:

```text
MDCP_DEMO_PASS case=baseline
MDCP_DEMO_REJECT case=remote_release_claim reason=PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID
MDCP_DEMO_REJECT case=public_surface_tamper reason=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH
MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0
```

Explain in zh-TW that `repository_mutations=0` means before/after Git porcelain bytes are identical, and include:

```text
MDCP_REVIEWER_DEMO_PASS != REMOTE_RELEASED != PRODUCTION_READY
```

In the shell-neutral Level 1 commands, keep the standalone verifier first, add the demo second, and keep curated pytest third. Do not add an English README or resume material.

- [ ] **Step 5: Regenerate readiness after the three public files change**

Repeat Task 2 Step 4 after README, quickstart, and fast-path bytes are final. Apply only the exact canonical readiness delta and independently prove byte equality. The schema and all historical identities must remain unchanged.

- [ ] **Step 6: Run Task 3 GREEN, wrapper behavior, and budget gates**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
$demoElapsed = Measure-Command {
    uv run --no-sync python scripts/reviewer-demo.py --repository-root .
    if ($LASTEXITCODE -ne 0) { throw 'REVIEWER_DEMO_FAILED' }
}
if ($demoElapsed.TotalSeconds -gt 120) { throw 'DEMO_BUDGET_EXCEEDED' }
pwsh ./scripts/reviewer-fast-path.ps1
uv run ruff check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv run ruff format --check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
```

Expected: exact demo terminals, `PUBLIC_RELEASE_SLICE_PASS`, `PUBLIC_RELEASE_FAST_PATH_PASS evidence_class=local_portfolio mutations=0`, all focused tests green, and measured demo duration at most 120 seconds.

- [ ] **Step 7: Review and commit documentation integration**

Require exactly these five changed paths:

```text
README.md
docs/reviewer/quickstart.md
evidence/public/portfolio/local-release-readiness.json
scripts/reviewer-fast-path.ps1
tests/publication/test_public_release_surface.py
```

Review zh-TW wording, exact commands/output, no false English/CV/LLM/Kubernetes/remote claims, wrapper order, failure-path state guard, and canonical evidence. Require Critical `0`, Important `0`. Then:

```powershell
git add README.md docs/reviewer/quickstart.md scripts/reviewer-fast-path.ps1 evidence/public/portfolio/local-release-readiness.json tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "docs: integrate deterministic reviewer demo"
```

Verify exact author/committer identity and a clean worktree.

---

### Task 4: Run final whole-range verification and independent review

**Files:**
- Modify: none unless a verified Critical/Important finding requires an in-allowlist corrective

**Interfaces:**
- Consumes: all commits after `$planEntry` and the Task 0 protected map.
- Produces: a clean local branch with evidence-bound demo, fresh test evidence, Critical `0`, Important `0`, and explicit non-actions.

- [ ] **Step 1: Verify the exact implementation range and protected tree**

```powershell
$changed = @(git diff --name-only "$planEntry..HEAD")
$outside = @($changed | Where-Object { $_ -notin $allowlist })
if ($outside.Count -ne 0) { throw 'IMPLEMENTATION_ALLOWLIST_DRIFT' }
foreach ($entry in $protected.GetEnumerator()) {
    $line = git ls-tree HEAD -- $entry.Key
    $currentMetadata = ($line -split "`t", 2)[0]
    if ($currentMetadata -ne $entry.Value) { throw 'PROTECTED_TREE_DRIFT' }
}
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) { throw 'WORKTREE_DIRTY' }
```

Expected: changed paths are a subset of the exact nine, outside count `0`, protected drift `0`, worktree clean.

- [ ] **Step 2: Run the final reviewer entrypoints with exact terminals and timing**

```powershell
uv run --no-sync python scripts/verify-public-release.py --repository-root .
$demoElapsed = Measure-Command {
    uv run --no-sync python scripts/reviewer-demo.py --repository-root .
    if ($LASTEXITCODE -ne 0) { throw 'REVIEWER_DEMO_FAILED' }
}
if ($demoElapsed.TotalSeconds -gt 120) { throw 'DEMO_BUDGET_EXCEEDED' }
pwsh ./scripts/reviewer-fast-path.ps1
```

Require exactly the verifier PASS, the four demo lines, and the fast-path PASS. Record the measured warm demo and fast-path durations only in the final task report.

- [ ] **Step 3: Run focused and full dynamic verification**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run pytest -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run pytest -q
```

Expected: all focused and full suites pass. Report fresh counts, skips, and durations; do not replace the historical `1546/7` measurement inside readiness.

- [ ] **Step 4: Run all static, schema, evidence, and frozen-identity gates**

```powershell
uv run ruff check scripts tests/publication
uv run ruff format --check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
git log --format='%H %P %an <%ae> %cn <%ce> %s' "$planEntry..HEAD"
git remote
git tag --points-at HEAD
```

Then require:

```text
checked schema == LocalReleaseReadiness.model_json_schema()
public_evidence_violations(readiness.model_dump(mode="json")) == ()
readiness.public_surface_entries == build_public_surface_inventory(repository_root)
readiness.public_surface_inventory_sha256 == SHA-256(canonical inventory entries)
readiness.claim_execution.remote_release_executed == false
readiness.claim_execution.h2_executed == false
H2 == SEALED_NOT_LOADED / 0 rows
uv.lock, v0.1, v0.2, source, worker, firewall, receipt, and index identities == Global Constraints
new commits == linear one-parent history with exact approved identity
remotes == 0
HEAD tags == 0
```

- [ ] **Step 5: Obtain independent commit-by-commit and aggregate review**

Invoke `requesting-code-review`. Review each new commit and `$planEntry..HEAD` as a whole. The reviewer must explicitly inspect:

```text
real baseline verifier reuse
false-claim parser rejection
temporary byte-tamper rejection before Git/link checks
success buffering and empty failure stdout
fixed sanitized error taxonomy
custom argparse error handling
temporary cleanup and repository no-clobber
nine-path ASCII ordering and acyclic readiness
exact LF rule and fresh autocrlf checkout
verifier -> demo -> curated tests ordering
failure-path environment/location/state restoration
zh-TW recruiter wording and claim ceiling
allowlist/protected-tree preservation
absence of remote, network, H2, data, model, workflow, package, tag, push, merge, or release actions
```

Acceptance is exactly:

```text
Critical: 0
Important: 0
```

- [ ] **Step 6: Handle findings without widening scope**

For any Critical/Important finding, invoke `receiving-code-review` and `systematic-debugging`, reproduce it with a RED regression in `tests/publication/test_public_release_surface.py`, correct only an allowlisted path, regenerate readiness whenever any of the nine public bytes change, and rerun Tasks 4.1–4.5. Commit one focused corrective only after all gates pass. If a correction needs any path outside the nine, stop and request explicit new scope.

- [ ] **Step 7: Record the final local-only boundary**

Successful terminals and claim boundary:

```text
PUBLIC_RELEASE_SLICE_PASS
MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0
PUBLIC_RELEASE_FAST_PATH_PASS evidence_class=local_portfolio mutations=0
LOCAL_PORTFOLIO_RECRUITER_DEMO_READY
REMOTE_RELEASE_NOT_EXECUTED
H2_SEALED_NOT_LOADED
```

Report all new commit SHAs and subjects, exact changed paths, readiness/schema/public-inventory SHA-256 values, focused/full counts and durations, demo/fast-path durations, frozen identities, review counts, clean branch/HEAD, remotes/tags counts, and every explicit non-action. Stop with the branch kept local; do not push, merge, tag, release, execute workflows, run H2/data/models, or touch another repository.
