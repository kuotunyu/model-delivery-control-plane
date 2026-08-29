# MDCP Recruiter-Facing Public Release Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a truthful `zh-TW`, evidence-first public portfolio surface with an offline reviewer fast path and machine-verifiable local readiness evidence.

**Architecture:** Keep the production package and frozen temporal evidence unchanged. Add one read-only publication verifier under `scripts/`, bind the public docs/scripts/schema through an acyclic canonical inventory, and authenticate the historical formal closure from Git objects without requiring the later publication HEAD to equal the freeze HEAD.

**Tech Stack:** Python 3.12, Pydantic 2, RFC 8785 canonical JSON, Git, pytest, Ruff, PowerShell 7, Markdown, JSON Schema.

## Global Constraints

- Work only in the existing linked worktree on branch `codex/wave0-foundation-feasibility`.
- The approved design is `docs/superpowers/specs/2026-08-30-mdcp-recruiter-public-release-design.md`, commit `2b5edc85e0d476d486432b18e9664d004fc1688d`, SHA-256 `154e978d8fe097eec2b7cd26c6731956110f702334d4251119e9b0799651ffec`.
- Use TDD: obtain the specified RED result before each implementation change.
- Do not modify any `src/mdcp`, dependency, lock, model, workload, runtime, existing evidence, workflow, Docker, Compose, or private custody path.
- Preserve `uv.lock` SHA-256 `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`.
- Preserve technical closure commit `b1bb0d80cd40e6f39372c0a45892500cc9530712` and its parent `407f68b63c06a17ef54d5ec17722ef1f801b1689`.
- Preserve current search receipt SHA-256 `5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63` and index SHA-256 `2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205`.
- Preserve v0.1 serving identity `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`, v0.2 serving identity `198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea`, 47-path source identity `cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b`, four-path worker identity `ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3`, and firewall identity `e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1`.
- H2 remains `SEALED_NOT_LOADED`, loaded rows `0`; do not access UCI/H1/H2 rows, create authorization, or execute data/model workloads.
- README is primarily 正體中文 (`zh-TW`); preserve precise English technical terms.
- Do not claim CV/LLM workload implementation, Kubernetes production readiness, production HA, H2 execution, remote release, or production evidence.
- Do not create a remote, use network, push, merge, tag, publish a package, create a GitHub Release, or execute `.github/workflows/release-ci.yml`.
- The implementation allowlist after this plan commit is exactly ten paths:

```text
README.md
LICENSE
docs/architecture.md
docs/reviewer/quickstart.md
docs/reviewer/release-evidence.md
scripts/reviewer-fast-path.ps1
scripts/verify-public-release.py
schemas/portfolio/local-release-readiness.schema.json
evidence/public/portfolio/local-release-readiness.json
tests/publication/test_public_release_surface.py
```

---

### Task 0: Freeze the implementation baseline

**Files:**
- Read: `docs/superpowers/specs/2026-08-30-mdcp-recruiter-public-release-design.md`
- Read: `docs/superpowers/plans/2026-08-30-mdcp-recruiter-public-release.md`
- Modify: none

**Interfaces:**
- Consumes: approved spec commit `2b5edc85e0d476d486432b18e9664d004fc1688d` and this plan commit.
- Produces: controller-held plan-entry SHA, exact protected Git tree map, and a fresh green baseline.

- [ ] **Step 1: Verify branch, clean state, history, and external-action boundary**

```powershell
$expectedBranch = 'codex/wave0-foundation-feasibility'
if ((git branch --show-current) -ne $expectedBranch) { throw 'BRANCH_MISMATCH' }
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) { throw 'WORKTREE_DIRTY' }
if (@(git remote).Count -ne 0) { throw 'REMOTE_DRIFT' }
if (@(git tag --points-at HEAD).Count -ne 0) { throw 'HEAD_TAGGED' }
$planEntry = (git rev-parse HEAD).Trim()
if ((git rev-parse "$planEntry^").Trim() -ne '2b5edc85e0d476d486432b18e9664d004fc1688d') {
    throw 'PLAN_PARENT_MISMATCH'
}
```

Expected: all checks pass; store `$planEntry` for every later allowlist/protected-tree gate.

- [ ] **Step 2: Freeze protected Git objects in controller memory**

```powershell
$allowlist = @(
  'README.md',
  'LICENSE',
  'docs/architecture.md',
  'docs/reviewer/quickstart.md',
  'docs/reviewer/release-evidence.md',
  'scripts/reviewer-fast-path.ps1',
  'scripts/verify-public-release.py',
  'schemas/portfolio/local-release-readiness.schema.json',
  'evidence/public/portfolio/local-release-readiness.json',
  'tests/publication/test_public_release_surface.py'
)
$protected = @{}
foreach ($line in @(git ls-tree -r $planEntry)) {
    $parts = $line -split "`t", 2
    if ($parts[1] -notin $allowlist) { $protected[$parts[1]] = $parts[0] }
}
if ($allowlist.Count -ne 10) { throw 'ALLOWLIST_COUNT_INVALID' }
```

Expected: exact ten-path allowlist; every other entry-tree path stored without writing a file.

- [ ] **Step 3: Run the pre-implementation baseline**

```powershell
uv run pytest -q
uv run ruff check scripts tests/publication
uv lock --check
git diff --check
```

Expected: existing full suite passes; Ruff, lock, and diff checks pass. Record the fresh pytest count
and duration in the task report, but do not put them in public readiness evidence because that
evidence binds the already reviewed technical closure.

---

### Task 1: Add the closed read-only publication verifier

**Files:**
- Create: `scripts/verify-public-release.py`
- Create: `tests/publication/test_public_release_surface.py`

**Interfaces:**
- Consumes: `mdcp.common.canonical.canonicalize_json`, `mdcp.common.canonical.parse_json_bytes`, `mdcp.common.digests.sha256_hex`, `mdcp.temporal.evidence.public_evidence_violations`, and fixed historical Git identities from Global Constraints.
- Produces:
  - `PUBLIC_SURFACE_PATHS: tuple[str, ...]`
  - `LocalReleaseReadiness(BaseModel)`
  - `build_public_surface_inventory(root: Path) -> tuple[PublicSurfaceEntry, ...]`
  - `load_readiness(root: Path) -> LocalReleaseReadiness`
  - `verify_document_links(root: Path) -> None`
  - `verify_git_closure(root: Path, readiness: LocalReleaseReadiness) -> None`
  - `verify_public_release(root: Path) -> LocalReleaseReadiness`
  - `main(argv: Sequence[str] | None = None) -> int`

- [ ] **Step 1: Write RED contract, canonicalization, disclosure, and failure-code tests**

Create a loader in the test file so the non-package script can be tested directly:

```python
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
VERIFIER_PATH = REPOSITORY_ROOT / "scripts" / "verify-public-release.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("mdcp_public_release_verifier", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_verifier_exposes_only_the_closed_public_contract() -> None:
    verifier = _load_verifier()
    assert verifier.PUBLIC_SURFACE_PATHS == tuple(
        sorted(verifier.PUBLIC_SURFACE_PATHS, key=str.encode)
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
```

- [ ] **Step 2: Run the RED selector**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py::test_verifier_exposes_only_the_closed_public_contract
```

Expected: FAIL because `scripts/verify-public-release.py` does not exist.

- [ ] **Step 3: Implement the strict evidence models and canonical parser**

Use these exact constants and model boundaries:

```python
from __future__ import annotations

import argparse
import re
import stat
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.evidence import public_evidence_violations

FORMAL_CLOSURE_COMMIT = "b1bb0d80cd40e6f39372c0a45892500cc9530712"
FORMAL_CLOSURE_PARENT = "407f68b63c06a17ef54d5ec17722ef1f801b1689"
CORRECTION_COMMIT = "bfe517819ec2163d700519fc427dbe8bb8071258"
SEARCH_RECEIPT_SHA256 = "5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63"
SEARCH_INDEX_SHA256 = "2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205"
READINESS_PATH = "evidence/public/portfolio/local-release-readiness.json"
SCHEMA_PATH = "schemas/portfolio/local-release-readiness.schema.json"
PUBLIC_SURFACE_PATHS = (
    "LICENSE",
    "README.md",
    "docs/architecture.md",
    "docs/reviewer/quickstart.md",
    "docs/reviewer/release-evidence.md",
    "schemas/portfolio/local-release-readiness.schema.json",
    "scripts/reviewer-fast-path.ps1",
    "scripts/verify-public-release.py",
)
PUBLIC_MARKDOWN_PATHS = (
    "README.md",
    "docs/architecture.md",
    "docs/reviewer/quickstart.md",
    "docs/reviewer/release-evidence.md",
)
_MARKDOWN_LINK_TARGET = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)")

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class PublicReleaseError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicSurfaceEntry(ClosedModel):
    logical_path: str
    byte_size: Annotated[int, Field(ge=0)]
    sha256: Sha256


class TechnicalClosureVerification(ClosedModel):
    full_suite_passed: Literal[1546]
    full_suite_skipped: Literal[7]
    review_critical: Literal[0]
    review_important: Literal[0]
    review_minor: Literal[0]


class ClaimExecution(ClosedModel):
    remote_release_executed: Literal[False]
    push_executed: Literal[False]
    tag_created: Literal[False]
    production_deployed: Literal[False]
    kubernetes_production_ready: Literal[False]
    h2_executed: Literal[False]
    cv_workload_implemented: Literal[False]
    llm_workload_implemented: Literal[False]


class LocalReleaseReadiness(ClosedModel):
    schema_version: Literal["mdcp.local-release-readiness.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["local_portfolio_release_readiness"]
    publication_status: Literal["public"]
    formal_closure_commit: Literal["b1bb0d80cd40e6f39372c0a45892500cc9530712"]
    formal_closure_parent: Literal["407f68b63c06a17ef54d5ec17722ef1f801b1689"]
    correction_commit: Literal["bfe517819ec2163d700519fc427dbe8bb8071258"]
    search_receipt_sha256: Literal[
        "5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63"
    ]
    search_index_sha256: Literal[
        "2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205"
    ]
    source_inventory_sha256: Literal[
        "cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b"
    ]
    formal_worker_inventory_sha256: Literal[
        "ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3"
    ]
    v1_serving_identity: Literal[
        "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"
    ]
    v2_serving_identity: Literal[
        "198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea"
    ]
    static_firewall_sha256: Literal[
        "e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1"
    ]
    public_surface_entries: tuple[PublicSurfaceEntry, ...]
    public_surface_inventory_sha256: Sha256
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    technical_closure_verification: TechnicalClosureVerification
    reviewer_entrypoint: Literal["scripts/reviewer-fast-path.ps1"]
    claim_ceiling: Literal["mdcp.local-portfolio-claim-ceiling.v1"]
    claim_execution: ClaimExecution

    @model_validator(mode="after")
    def exact_public_surface(self) -> "LocalReleaseReadiness":
        paths = tuple(entry.logical_path for entry in self.public_surface_entries)
        if paths != PUBLIC_SURFACE_PATHS:
            raise ValueError("PUBLIC_RELEASE_SLICE_INVENTORY_INVALID")
        expected = sha256_hex(
            canonicalize_json(
                [entry.model_dump(mode="json") for entry in self.public_surface_entries]
            )
        )
        if self.public_surface_inventory_sha256 != expected:
            raise ValueError("PUBLIC_RELEASE_SLICE_INVENTORY_INVALID")
        return self
```

Implement `parse_readiness_bytes(raw)` inside `try/except Exception`, calling `parse_json_bytes`,
validating `LocalReleaseReadiness`, and requiring
`canonicalize_json(model.model_dump(mode="json")) == raw`. Map every caught exception to
`PublicReleaseError("PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID") from None`; do not embed or chain the
original exception.

- [ ] **Step 4: Implement regular-file, inventory, link, and Git-object helpers**

Use fixed subprocess arguments only:

```python
def _git(root: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=root,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID") from None
    if completed.returncode != 0:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")
    return completed.stdout


def _read_regular(root: Path, logical_path: str) -> bytes:
    candidate = PurePosixPath(logical_path)
    if (
        not logical_path
        or "\\" in logical_path
        or candidate.is_absolute()
        or ".." in candidate.parts
        or candidate.as_posix() != logical_path
    ):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
    target = root.joinpath(*candidate.parts)
    try:
        info = target.lstat()
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        reparse = getattr(info, "st_file_attributes", 0) & reparse_flag
        if not stat.S_ISREG(info.st_mode) or target.is_symlink() or reparse:
            raise PublicReleaseError("PUBLIC_RELEASE_SLICE_FILE_INVALID")
        return target.read_bytes()
    except PublicReleaseError:
        raise
    except OSError:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_FILE_INVALID") from None


def build_public_surface_inventory(root: Path) -> tuple[PublicSurfaceEntry, ...]:
    return tuple(
        PublicSurfaceEntry(
            logical_path=path,
            byte_size=len(raw := _read_regular(root, path)),
            sha256=sha256_hex(raw),
        )
        for path in PUBLIC_SURFACE_PATHS
    )
```

`verify_document_links` scans exactly `PUBLIC_MARKDOWN_PATHS` with `_MARKDOWN_LINK_TARGET`, ignores
`http://`, `https://`, `mailto:`, and fragment-only targets, strips a trailing fragment from local
targets, rejects absolute/backslash/`..` targets, resolves relative to the document parent, requires
containment under `root`, and calls `_read_regular` on the normalized repository-relative target.

`verify_git_closure` must require this exact chain and path topology:

```python
EXPECTED_COMMITS = (
    ("1ba0fecc4980ca488a24eb5e19ba3bb080e1a509", "504c3058f2b90c04d0f989c2aa6aab37d314b088", "D"),
    ("915083225e6c2013f06758d29aa4032b54768ccb", "1ba0fecc4980ca488a24eb5e19ba3bb080e1a509", "A"),
    ("bfe517819ec2163d700519fc427dbe8bb8071258", "915083225e6c2013f06758d29aa4032b54768ccb", "M"),
    ("407f68b63c06a17ef54d5ec17722ef1f801b1689", "bfe517819ec2163d700519fc427dbe8bb8071258", "D"),
    ("b1bb0d80cd40e6f39372c0a45892500cc9530712", "407f68b63c06a17ef54d5ec17722ef1f801b1689", "A"),
)
EVIDENCE_PATHS = (
    "evidence/public/v02/search/evidence-index.json",
    "evidence/public/v02/search/search-receipt.json",
)
CORRECTION_PATHS = (
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/runtime_guards.py",
    "tests/security/temporal/test_data_firewall.py",
    "tests/unit/temporal/test_run_evidence.py",
)
```

For each commit, compare `git show -s --format=%P <commit>` to the exact single parent. Compare
`git diff-tree --no-commit-id --name-status -r <commit>` to two exact evidence paths for `A`/`D` and
the four exact correction paths for `M`. Require the checked `_git(root, "merge-base",
"--is-ancestor", FORMAL_CLOSURE_COMMIT, "HEAD")` call to succeed; do not require current HEAD to
equal the closure. Read the two closure blobs with
`git cat-file blob <closure>:<path>`, recompute SHA-256, parse H2 fields, and require the exact public
receipt/index identities.

- [ ] **Step 5: Implement the orchestrator and sanitized CLI**

```python
def verify_public_release(root: Path) -> LocalReleaseReadiness:
    try:
        root = root.resolve(strict=True)
    except OSError:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID") from None
    if not root.is_dir():
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
    readiness = load_readiness(root)
    if public_evidence_violations(readiness.model_dump(mode="json")):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_DISCLOSURE")
    if build_public_surface_inventory(root) != readiness.public_surface_entries:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH")
    verify_document_links(root)
    verify_git_closure(root, readiness)
    return readiness


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    verify_public_release(arguments.repository_root)
    print("PUBLIC_RELEASE_SLICE_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicReleaseError as error:
        print(f"PUBLIC_RELEASE_SLICE_FAIL reason_code={error.reason_code}")
        raise SystemExit(1) from None
```

`load_readiness` reads only `READINESS_PATH` through `_read_regular`. Do not expose raw Pydantic,
JSON, subprocess, path, or OS errors.

- [ ] **Step 6: Run Task 1 GREEN and quality gates**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'closed_public_contract or readiness_parser or regular or git or link'
uv run ruff check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv run ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
git diff --check
```

Expected: Task 1 unit tests pass. Do not run the repository end-to-end verifier yet because the
public surface and readiness evidence deliberately do not exist.

- [ ] **Step 7: Review and commit Task 1**

Require staged paths exactly:

```text
A  scripts/verify-public-release.py
A  tests/publication/test_public_release_surface.py
```

Obtain a read-only scope/code review; require Critical `0`, Important `0`. Then:

```powershell
git add scripts/verify-public-release.py tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "feat: add public release verifier"
```

---

### Task 2: Add the truthful recruiter-facing documents and MIT license

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `docs/architecture.md`
- Create: `docs/reviewer/quickstart.md`
- Create: `docs/reviewer/release-evidence.md`
- Modify: `tests/publication/test_public_release_surface.py`

**Interfaces:**
- Consumes: `PUBLIC_SURFACE_PATHS`, link validation rules, and claim ceiling from Task 1.
- Produces: the human-readable public surface and all local Markdown link targets needed by the final inventory.

- [ ] **Step 1: Add RED document inventory, language, link, and claim tests**

Add these exact assertions and a table-driven required-phrase test:

```python
PUBLIC_DOCUMENTS = (
    "LICENSE",
    "README.md",
    "docs/architecture.md",
    "docs/reviewer/quickstart.md",
    "docs/reviewer/release-evidence.md",
)


def test_public_documents_exist_as_regular_nonlinks() -> None:
    for logical_path in PUBLIC_DOCUMENTS:
        path = REPOSITORY_ROOT / logical_path
        assert path.is_file()
        assert not path.is_symlink()


def test_readme_is_zh_tw_and_states_the_claim_ceiling() -> None:
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
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
    architecture = (REPOSITORY_ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    assert "Implemented verification path" in architecture
    assert "Designed deployment path" in architecture
    for component in ("control service", "router", "canary", "rollback", "recovery"):
        assert f"{component} | Designed only" in architecture
```

Add this line-scoped negative-claim test across the five public documents:

```python
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
        text = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
        for line in text.splitlines():
            if any(token.casefold() in line.casefold() for token in claim_tokens):
                assert any(marker.casefold() in line.casefold() for marker in negating_markers)
```

- [ ] **Step 2: Run Task 2 RED**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'public_documents or readme or designed_components'
```

Expected: FAIL because the five public documents do not exist.

- [ ] **Step 3: Write `README.md` with the approved recruiter hierarchy**

Use this exact section order and preserve the required claim text:

```markdown
<!-- lang: zh-TW -->
# Model Delivery Control Plane

> 把「模型表現較好」與「模型可以取得 production traffic」分開：offline score 不等於 deployment permission。

## 30 秒理解這個專案
## 目前完成度
## 實際 implemented verification path
## Reviewer fast path
## Evidence 與安全邊界
## Architecture 與程式碼導覽
## 技術棧與測試
## Claim ceiling
## License
```

The status table must use exactly four statuses: `Implemented`, `Verified locally`, `Designed only`,
and `Not executed remotely`. State that the concrete workload is temporal regression and that the
delivery controls are transferable engineering patterns, not proof of a CV/LLM implementation.
Link with repository-relative Markdown links to:

```text
docs/architecture.md
docs/reviewer/quickstart.md
docs/reviewer/release-evidence.md
docs/threat-model.md
.github/workflows/release-ci.yml
evidence/public/portfolio/local-release-readiness.json
evidence/public/v02/search/search-receipt.json
evidence/public/v02/search/evidence-index.json
LICENSE
```

The quick command is `pwsh ./scripts/reviewer-fast-path.ps1`; label `uv sync --frozen` as a separate
dependency setup step that may use network on first installation.

- [ ] **Step 4: Write actual-versus-designed architecture**

`docs/architecture.md` must contain:

1. An implemented Mermaid flow from contracts/source bytes to identities, offline validator,
   dedicated formal worker/firewall, and public evidence.
2. A separately labeled designed flow for control service, router, shadow/canary, rollback,
   recovery, and observability.
3. A literal component matrix row format `component | state | evidence` and these exact rows:

```text
workload contracts and serving identity | Implemented | src/mdcp/contracts, contract tests
offline artifact and bundle validator | Verified locally | src/mdcp/validator, src/mdcp/verify
dedicated temporal formal worker | Verified locally | src/mdcp/temporal/formal_worker.py
public search freeze | Verified locally | evidence/public/v02/search
GitHub release workflow | Not executed remotely | .github/workflows/release-ci.yml
control service | Designed only | v0.1 design specification
router | Designed only | v0.1 design specification
canary | Designed only | v0.1 design specification
rollback | Designed only | v0.1 design specification
recovery | Designed only | v0.1 design specification
```

Explain that publication commits are descendants of `b1bb0d8`; they do not redefine freeze HEAD.

- [ ] **Step 5: Write the reviewer and evidence guides**

`docs/reviewer/quickstart.md` must specify Python `3.12`, `uv`, Git full history, CPU-only, and three
levels. The fast path commands are exactly:

```powershell
uv sync --frozen
pwsh ./scripts/reviewer-fast-path.ps1
```

The shell-neutral manual equivalent is:

```text
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
```

State the warm target `3–5 minutes`, keep first dependency installation outside that timing, and
state that a source ZIP or shallow clone cannot authenticate the historical Git topology. The full
path is `uv run pytest -q`; report `1546 passed, 7 skipped in 681.43s` only as the historical
technical-closure measurement, not a guarantee for the later publication tree.

`docs/reviewer/release-evidence.md` must distinguish the five evidence classes from the approved
spec and state `LOCAL_PORTFOLIO_RELEASE_READY != REMOTE_RELEASED != PRODUCTION_READY`.

- [ ] **Step 6: Add the MIT license**

Create the standard MIT License text with:

```text
MIT License

Copyright (c) 2026 kuotunyu
```

Do not add dataset or dependency licenses to the project license; state in README that third-party
materials retain their own terms.

- [ ] **Step 7: Run Task 2 GREEN and document checks**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'public_documents or readme or designed_components or link or claim'
uv run ruff check tests/publication/test_public_release_surface.py
uv run ruff format --check tests/publication/test_public_release_surface.py
git diff --check
```

Expected: all Task 2 selectors pass. End-to-end verifier still fails only because schema, wrapper,
and readiness evidence are not created yet.

- [ ] **Step 8: Review and commit Task 2**

Require exactly five new documents plus the one modified test file, obtain Critical `0` and
Important `0`, then:

```powershell
git add README.md LICENSE docs/architecture.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "docs: add recruiter-facing project surface"
```

---

### Task 3: Add the offline CPU-only reviewer fast path

**Files:**
- Create: `scripts/reviewer-fast-path.ps1`
- Modify: `tests/publication/test_public_release_surface.py`

**Interfaces:**
- Consumes: Task 1 verifier CLI and Task 2 documented curated test list.
- Produces: `pwsh ./scripts/reviewer-fast-path.ps1` with terminal `PUBLIC_RELEASE_FAST_PATH_PASS`.

- [ ] **Step 1: Add RED PowerShell ordering, offline, and mutation tests**

```python
def test_fast_path_is_fail_fast_offline_and_matches_the_documented_selector() -> None:
    script = (REPOSITORY_ROOT / "scripts" / "reviewer-fast-path.ps1").read_text(
        encoding="utf-8"
    )
    assert "Set-StrictMode -Version Latest" in script
    assert "$ErrorActionPreference = 'Stop'" in script
    assert "uv run --no-sync python scripts/verify-public-release.py" in script
    assert "uv run --no-sync pytest -p no:cacheprovider -q" in script
    assert script.index("verify-public-release.py") < script.index("pytest -p no:cacheprovider")
    assert "PUBLIC_RELEASE_FAST_PATH_PASS" in script
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
```

Do not invoke the wrapper from this same pytest module: the wrapper intentionally selects this module,
so an in-module wrapper test would recurse. Task 4 and Task 5 execute the wrapper as an external gate
after readiness evidence exists.

- [ ] **Step 2: Run Task 3 RED**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py::test_fast_path_is_fail_fast_offline_and_matches_the_documented_selector
```

Expected: FAIL because `scripts/reviewer-fast-path.ps1` does not exist.

- [ ] **Step 3: Implement the exact wrapper**

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$before = @(git -C $repositoryRoot status --porcelain=v1 --untracked-files=all)
$previousLocation = Get-Location
$previousBytecode = $env:PYTHONDONTWRITEBYTECODE

try {
    Set-Location -LiteralPath $repositoryRoot
    $env:PYTHONDONTWRITEBYTECODE = '1'

    & uv run --no-sync python scripts/verify-public-release.py --repository-root .
    if ($LASTEXITCODE -ne 0) { throw 'public release verifier failed' }

    & uv run --no-sync pytest -p no:cacheprovider -q `
        tests/publication/test_public_release_surface.py `
        tests/publication/test_release_workflow.py `
        tests/contract/workload/test_serving_identity_isolation.py `
        tests/contract/workload/test_serving_identity_v2.py `
        tests/unit/temporal/test_formal_worker_protocol.py `
        tests/integration/temporal/test_formal_worker_process.py `
        tests/security/temporal/test_public_evidence_boundary.py
    if ($LASTEXITCODE -ne 0) { throw 'curated reviewer tests failed' }
}
finally {
    if ($null -eq $previousBytecode) {
        Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONDONTWRITEBYTECODE = $previousBytecode
    }
    Set-Location -LiteralPath $previousLocation
}

$after = @(git -C $repositoryRoot status --porcelain=v1 --untracked-files=all)
if (($before -join "`n") -ne ($after -join "`n")) {
    throw 'reviewer fast path changed repository state'
}

Write-Output 'PUBLIC_RELEASE_FAST_PATH_PASS evidence_class=local_portfolio mutations=0'
```

Do not invoke `uv sync` inside the wrapper. Dependency installation is the explicitly separate
setup command and the wrapper's `--no-sync` is the offline enforcement boundary.

- [ ] **Step 4: Run Task 3 GREEN**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'fast_path_is_fail_fast'
git diff --check
```

Expected: static wrapper contract passes. Do not run the wrapper end-to-end before Task 4 evidence.

- [ ] **Step 5: Review and commit Task 3**

Require staged paths exactly the wrapper and modified publication test, Critical `0`, Important
`0`, then:

```powershell
git add scripts/reviewer-fast-path.ps1 tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "test: add offline reviewer fast path"
```

---

### Task 4: Publish canonical local readiness evidence

**Files:**
- Create: `schemas/portfolio/local-release-readiness.schema.json`
- Create: `evidence/public/portfolio/local-release-readiness.json`
- Modify: `tests/publication/test_public_release_surface.py`

**Interfaces:**
- Consumes: Task 1 `LocalReleaseReadiness` and verifier, all eight final public surface paths, historical technical closure, Task 2 links, and Task 3 wrapper.
- Produces: canonical public evidence, exact checked-in schema, end-to-end `PUBLIC_RELEASE_SLICE_PASS`, and runnable fast path.

- [ ] **Step 1: Add RED schema, evidence, inventory, topology, and end-to-end tests**

At this task, add the imports that first become necessary here:

```python
import json

from mdcp.temporal.evidence import public_evidence_violations
```

```python
def test_checked_in_readiness_schema_matches_the_closed_model() -> None:
    verifier = _load_verifier()
    checked = json.loads(
        (REPOSITORY_ROOT / verifier.SCHEMA_PATH).read_text(encoding="utf-8")
    )
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
```

Add mutation tests using a copied eight-file public surface under `tmp_path` and monkeypatched fixed
Git responses. Each mutation must produce its exact code:

```text
missing file             PUBLIC_RELEASE_SLICE_FILE_INVALID
symlink/reparse          PUBLIC_RELEASE_SLICE_FILE_INVALID
wrong file digest        PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH
noncanonical JSON        PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID
unknown evidence field   PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID
true execution claim     PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID
wrong H2 state/row count PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID
private path disclosure  PUBLIC_RELEASE_SLICE_DISCLOSURE
wrong Git parent         PUBLIC_RELEASE_SLICE_GIT_INVALID
broken relative link     PUBLIC_RELEASE_SLICE_LINK_INVALID
repository escape link   PUBLIC_RELEASE_SLICE_LINK_INVALID
```

- [ ] **Step 2: Run Task 4 RED**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py -k 'readiness_schema or readiness_evidence or current_repository'
```

Expected: FAIL because schema and readiness evidence do not exist.

- [ ] **Step 3: Materialize and inspect the exact checked-in schema**

Use a read-only Python command to print the deterministic schema:

```powershell
uv run python -c "import importlib.util,json,sys; from pathlib import Path; p=Path('scripts/verify-public-release.py'); s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); print(json.dumps(m.LocalReleaseReadiness.model_json_schema(),indent=2,sort_keys=True))"
```

Inspect the output for recursively closed models, exact literals, digest/commit patterns, and all
eight false execution claims. Add that exact output through `apply_patch` at
`schemas/portfolio/local-release-readiness.schema.json` with one terminal LF. Do not add a schema
generation mode to the read-only verifier.

- [ ] **Step 4: Build the acyclic public-surface inventory and evidence bytes**

After the schema exists, use the verifier model in a read-only print command to calculate exact
entries. Construct this exact document shape:

```python
document = {
    "schema_version": "mdcp.local-release-readiness.v1",
    "canonicalization_version": "RFC8785",
    "evidence_class": "local_portfolio_release_readiness",
    "publication_status": "public",
    "formal_closure_commit": FORMAL_CLOSURE_COMMIT,
    "formal_closure_parent": FORMAL_CLOSURE_PARENT,
    "correction_commit": CORRECTION_COMMIT,
    "search_receipt_sha256": SEARCH_RECEIPT_SHA256,
    "search_index_sha256": SEARCH_INDEX_SHA256,
    "source_inventory_sha256": "cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b",
    "formal_worker_inventory_sha256": "ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3",
    "v1_serving_identity": "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209",
    "v2_serving_identity": "198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea",
    "static_firewall_sha256": "e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1",
    "public_surface_entries": [entry.model_dump(mode="json") for entry in entries],
    "public_surface_inventory_sha256": sha256_hex(
        canonicalize_json([entry.model_dump(mode="json") for entry in entries])
    ),
    "h2_status": "SEALED_NOT_LOADED",
    "h2_loaded_rows": 0,
    "technical_closure_verification": {
        "full_suite_passed": 1546,
        "full_suite_skipped": 7,
        "review_critical": 0,
        "review_important": 0,
        "review_minor": 0,
    },
    "reviewer_entrypoint": "scripts/reviewer-fast-path.ps1",
    "claim_ceiling": "mdcp.local-portfolio-claim-ceiling.v1",
    "claim_execution": {
        "remote_release_executed": False,
        "push_executed": False,
        "tag_created": False,
        "production_deployed": False,
        "kubernetes_production_ready": False,
        "h2_executed": False,
        "cv_workload_implemented": False,
        "llm_workload_implemented": False,
    },
}
```

Validate the model, print `canonicalize_json(model.model_dump(mode="json"))` as UTF-8, and add the
exact bytes through `apply_patch` at `evidence/public/portfolio/local-release-readiness.json` with no
BOM and no terminal newline. The readiness file is not a member of `PUBLIC_SURFACE_PATHS`, so the
inventory has no self-cycle.

- [ ] **Step 5: Run Task 4 GREEN, mutations, verifier, and wrapper**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py
uv run python scripts/verify-public-release.py --repository-root .
$elapsed = Measure-Command {
    pwsh ./scripts/reviewer-fast-path.ps1
    if ($LASTEXITCODE -ne 0) { throw 'FAST_PATH_FAILED' }
}
if ($elapsed.TotalSeconds -gt 300) { throw 'FAST_PATH_BUDGET_EXCEEDED' }
```

Expected: publication tests pass; verifier prints `PUBLIC_RELEASE_SLICE_PASS`; wrapper prints
`PUBLIC_RELEASE_FAST_PATH_PASS`; warm execution is at most 300 seconds. Record exact test count and
elapsed time in the task report, not in the self-excluding readiness record.

- [ ] **Step 6: Run quality, identity, and disclosure gates**

```powershell
uv run ruff check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv run ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
```

Recompute v0.1/v0.2 serving, 47-path source, four-path worker, static firewall, existing receipt/index,
H2, and `uv.lock` identities; require exact Global Constraint values. Run
`public_evidence_violations` on the new readiness document and require `()`.

- [ ] **Step 7: Review and commit Task 4**

Require exactly schema/evidence additions plus the modified publication test. Review canonical
bytes, schema equivalence, inventory acyclicity, Git topology, sanitized failures, and claim ceiling;
require Critical `0`, Important `0`. Then:

```powershell
git add schemas/portfolio/local-release-readiness.schema.json evidence/public/portfolio/local-release-readiness.json tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "evidence: record local portfolio readiness"
```

---

### Task 5: Final public-slice verification and independent review

**Files:**
- Modify: none unless the independent reviewer reports an in-allowlist issue

**Interfaces:**
- Consumes: Tasks 1–4 committed tree and Task 0 controller-held protected map.
- Produces: `LOCAL_PORTFOLIO_RELEASE_READY` local terminal and a clean, reviewable local history.

- [ ] **Step 1: Verify exact implementation range and protected tree**

```powershell
$changed = @(git diff --name-only "$planEntry..HEAD")
$outside = @($changed | Where-Object { $_ -notin $allowlist })
if ($outside.Count -ne 0) { throw 'IMPLEMENTATION_ALLOWLIST_DRIFT' }
foreach ($entry in $protected.GetEnumerator()) {
    $line = (git ls-tree HEAD -- $entry.Key)
    $currentMetadata = ($line -split "`t", 2)[0]
    if ($currentMetadata -ne $entry.Value) { throw "PROTECTED_TREE_DRIFT" }
}
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) {
    throw 'WORKTREE_DIRTY'
}
```

Expected: changed paths are a subset of the exact ten, outside `0`, protected drift `0`.

- [ ] **Step 2: Run every final dynamic gate**

```powershell
pwsh ./scripts/reviewer-fast-path.ps1
uv run pytest -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run pytest -q
uv run python scripts/verify-public-release.py --repository-root .
```

Expected: both stable PASS terminals and all tests pass. Report the new full-suite count and duration
as final public-slice verification, while retaining `1546/7` in readiness evidence as the historical
technical-closure measurement.

- [ ] **Step 3: Run every final static and identity gate**

```powershell
uv run ruff check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv run ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
git log --format='%H %P %an <%ae> %cn <%ce> %s' "$planEntry..HEAD"
git remote
git tag --points-at HEAD
```

Require approved identity for every new commit, linear one-parent history, remotes `0`, HEAD tags
`0`, no caches in `git status`, exact historical evidence hashes, H2 sealed/0, and unchanged
v0.1/v0.2/source/worker/firewall/lock identities.

- [ ] **Step 4: Obtain final independent whole-range review**

The reviewer must inspect each new commit separately and the aggregate. Require:

```text
Critical: 0
Important: 0
```

The review must confirm actual-versus-designed wording, CV/LLM/Kubernetes/remote/H2 claim ceiling,
MIT license presence, link safety, canonical evidence, public scanner result, fixed error codes,
Git-history authentication, inventory acyclicity, fast-path offline behavior, protected-tree
preservation, and absence of any external action.

- [ ] **Step 5: Handle findings without expanding scope**

If a Critical/Important finding exists, use `receiving-code-review` and `systematic-debugging`, add a
RED regression in `tests/publication/test_public_release_surface.py`, correct only an allowlisted
path, rerun Tasks 5.1–5.4, and commit one focused correction. If the correction changes any of the
eight `PUBLIC_SURFACE_PATHS`, regenerate the readiness inventory and canonical evidence in the same
correction before review. Do not waive a finding because tests pass. If correction requires a path
outside the ten-path allowlist, stop and request new scope.

- [ ] **Step 6: Record the local terminal boundary**

Successful terminal:

```text
PUBLIC_RELEASE_SLICE_PASS
PUBLIC_RELEASE_FAST_PATH_PASS
LOCAL_PORTFOLIO_RELEASE_READY
REMOTE_RELEASE_NOT_EXECUTED
H2_SEALED_NOT_LOADED
```

Report all new commit SHAs, exact changed paths, focused/full test counts and durations, fast-path
duration, evidence/schema/public-surface identities, review counts, clean branch/HEAD, remote/tag
counts, and explicit non-actions. Stop without push, merge, tag, release, package publication,
network campaign, H2/data/model execution, or work in another repository.
