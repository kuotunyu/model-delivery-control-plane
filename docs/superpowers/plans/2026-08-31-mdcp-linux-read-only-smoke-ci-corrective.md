# MDCP Linux Read-Only Smoke CI Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and remotely prove a bounded `ubuntu-24.04` read-only publication smoke job while preserving the Windows authoritative full-suite gate and every existing negative release/production claim.

**Architecture:** Keep the existing Windows `verify` job byte-for-byte unchanged and append an independently failing Linux smoke job with no mutation authority. Use a two-push, non-recursive evidence sequence: the first push obtains the exact Linux run; the second records that run in the public surface and obtains final CI proof for the evidence commit.

**Tech Stack:** GitHub Actions, Ubuntu 24.04, Windows Server 2025, Python 3.12, uv 0.11.18, pytest 8.4.1, Ruff, PowerShell 7, RFC 8785 canonical JSON, Git, GitHub CLI.

## Global Constraints

- Work only in `D:\AI-Portfolio\CC_github部隊\model-delivery-control-plane\.worktrees\wave0-foundation-feasibility` on branch `codex/wave0-foundation-feasibility`.
- Reviewed base is `f4f6223ee2dcaa463079d9dca64b2011ecc094d7`; remote `main` must equal the expected pre-push base before each non-force push.
- Implementation paths are exactly `.github/workflows/portfolio-ci.yml`, `README.md`, `docs/reviewer/quickstart.md`, `docs/reviewer/release-evidence.md`, `evidence/public/portfolio/local-release-readiness.json`, `tests/publication/test_public_release_surface.py`, and `tests/publication/test_release_workflow.py`.
- Process paths are exactly this plan, `docs/superpowers/specs/2026-08-31-mdcp-linux-read-only-smoke-ci-corrective-design.md`, and git-ignored `.superpowers/sdd/2026-08-31-mdcp-linux-read-only-smoke-ci-corrective/**`.
- Preserve `.hypothesis/` as untracked non-source cache; never delete, stage, or use it as evidence.
- Windows `verify` remains the authoritative complete-suite job; Linux smoke never supports `CROSS_PLATFORM_PORTABLE`.
- CI network is limited to the pinned GitHub actions and `uv sync --frozen --group ml`; no Docker, registry, GitHub CLI mutation, upload, cache, model/data execution, or secret access in the Linux job.
- No skip, xfail, `pytest -k`, `--ignore`, test deletion, weakened assertion, wildcard authority, schema expansion, or verifier capability change.
- At most two non-force pushes to `main`; do not dispatch or rerun workflows.
- Do not merge, force-push, tag, create a GitHub Release, publish a package, execute release-ci, or touch P2/H2/model/data/CV/LLM/Kubernetes/production/another repository.
- Preserve frozen anchors exactly: v1 `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`; v2 `198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea`; source `cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b`; worker `ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3`; firewall `e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1`; `uv.lock` `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`; H2 `SEALED_NOT_LOADED`, rows `0`.
- Preserve readiness fields `technical_closure_verification = 1625/7/0/0/0` and Windows Portfolio CI anchor commit `8bc91a548846af0b1f1be1fc9ae6fbb80b7f63f1`, run `33322212462`.

---

### Task 1: Encode the exact Linux workflow contract with TDD

**Files:**

- Modify: `tests/publication/test_release_workflow.py`
- Modify: `.github/workflows/portfolio-ci.yml`

**Interfaces:**

- Consumes: the existing exact whole-workflow equality contract and pinned action SHAs.
- Produces: an exact `linux_read_only_smoke` YAML job and negative authority assertions.

- [ ] **Step 1: Read the test-quality rules before changing tests**

Read `C:\Users\3Hml\.codex\skills\test-driven-development\writing-good-tests.md` completely. Name the production change that would make each new assertion fail: removal, renaming, broadening, or authorization drift of the Linux smoke job.

- [ ] **Step 2: Add the failing exact-workflow expectation**

Append this exact block to `EXPECTED_PORTFOLIO_WORKFLOW`, after the unchanged Windows terminal mutation step:

```yaml

  linux_read_only_smoke:
    name: Linux read-only smoke (not portability proof)
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - name: Checkout complete evidence history
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Set up locked Python and uv
        uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d
        with:
          version: "0.11.18"
          python-version: "3.12"
          enable-cache: false
      - name: Install locked dependencies
        run: uv sync --frozen --group ml
      - name: Verify lock
        run: uv lock --check
      - name: Verify public evidence and deterministic demo
        run: |
          uv run --no-sync python scripts/verify-public-release.py --repository-root .
          uv run --no-sync python scripts/reviewer-demo.py --repository-root .
      - name: Run bounded Linux publication smoke
        run: uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
      - name: Reject tracked-file mutation
        run: git diff --exit-code
```

Update `test_portfolio_workflow_is_read_only_and_bounded()` to require both runner labels, the exact Linux display name, timeouts `30` and `15`, and no job-level permission. Update the action-ref test to compare the ordered pairs from both jobs rather than collapsing duplicate action names into a dictionary:

```python
assert reference_pairs == [
    ("actions/checkout", PORTFOLIO_ACTIONS["actions/checkout"]),
    ("astral-sh/setup-uv", PORTFOLIO_ACTIONS["astral-sh/setup-uv"]),
    ("actions/checkout", PORTFOLIO_ACTIONS["actions/checkout"]),
    ("astral-sh/setup-uv", PORTFOLIO_ACTIONS["astral-sh/setup-uv"]),
]
```

In `test_portfolio_workflow_runs_only_the_read_only_local_gate()`, require the exact Linux pytest command, require `ubuntu-24.04`, and keep every existing prohibition. Add Linux-job-specific assertions after splitting on `"  linux_read_only_smoke:\n"`:

```python
_, linux = workflow.split("  linux_read_only_smoke:\n", maxsplit=1)
assert "Linux read-only smoke (not portability proof)" in linux
assert "uv run --no-sync pytest -p no:cacheprovider -q " \
    "tests/publication/test_public_release_surface.py " \
    "tests/publication/test_release_workflow.py" in linux
for prohibited in (
    "docker ", "gh ", "secrets", "oidc", "attestation", "upload",
    "packages", "pytest -k", "--ignore", "uv run --no-sync pytest -p no:cacheprovider -q\n",
):
    assert prohibited not in linux.casefold()
```

- [ ] **Step 3: Run RED and inspect the expected failure**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_release_workflow.py
```

Expected: failure because the checked-in workflow still lacks `linux_read_only_smoke`; no import,
syntax, or fixture error is acceptable as RED evidence.

- [ ] **Step 4: Add the minimal Linux job**

Append the exact YAML block from Step 2 to `.github/workflows/portfolio-ci.yml`. Do not alter any byte
inside the existing Windows `verify` job.

- [ ] **Step 5: Run GREEN and format verification**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_release_workflow.py
uv run --no-sync ruff check tests/publication/test_release_workflow.py
uv run --no-sync ruff format --check tests/publication/test_release_workflow.py
git diff --check
```

Expected: every command exits `0`.

- [ ] **Step 6: Audit and commit Task 1**

```powershell
$changed = @(git diff --name-only)
$expected = @('.github/workflows/portfolio-ci.yml','tests/publication/test_release_workflow.py')
if (@(Compare-Object $expected $changed).Count -ne 0) { throw 'TASK_1_PATH_SET_INVALID' }
git add -- .github/workflows/portfolio-ci.yml tests/publication/test_release_workflow.py
git diff --cached --check
git commit -m "ci: add bounded Linux publication smoke"
```

---

### Task 2: Add truthful pre-run copy and canonical readiness

**Files:**

- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Modify: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**

- Consumes: Task 1's checked-in Linux smoke job without a remote success result.
- Produces: exact interim truth that the lane is configured but not yet remotely proven.

- [ ] **Step 1: Add the failing interim evidence contract**

Add a test named `test_linux_read_only_smoke_is_bounded_and_pending_remote_evidence()`:

```python
def test_linux_read_only_smoke_is_bounded_and_pending_remote_evidence() -> None:
    for logical_path in (
        "README.md",
        "docs/reviewer/quickstart.md",
        "docs/reviewer/release-evidence.md",
    ):
        text = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
        assert "Linux read-only smoke (not portability proof)" in text
        assert "Linux smoke is configured; successful remote evidence is not yet claimed." in text
        assert "LINUX_READ_ONLY_SMOKE_PASS != CROSS_PLATFORM_PORTABLE" in text
        assert "Linux read-only smoke success commit:" not in text
        assert "Linux read-only smoke success run:" not in text
```

Extend the existing claim-ceiling test so all three documents retain
`WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY`.

- [ ] **Step 2: Run RED and inspect the expected failure**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py::test_linux_read_only_smoke_is_bounded_and_pending_remote_evidence
```

Expected: failure because the exact pending wording is absent.

- [ ] **Step 3: Add the minimal interim wording**

Add this exact four-line block near the Portfolio CI state in all three documents:

```text
Linux read-only smoke (not portability proof)
Linux smoke is configured; successful remote evidence is not yet claimed.
LINUX_READ_ONLY_SMOKE_PASS != CROSS_PLATFORM_PORTABLE
Windows full suite remains the authoritative gate.
```

In `release-evidence.md`, keep historical run `33311024512` and state that the new bounded smoke does
not relabel that failed full-suite run. In README and quickstart, do not add the historical Ubuntu
URL.

- [ ] **Step 4: Regenerate the canonical public-surface inventory**

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.READINESS_PATH; document=json.loads(target.read_text(encoding='utf-8')); entries=module.build_public_surface_inventory(root); entry_documents=[entry.model_dump(mode='json') for entry in entries]; document['public_surface_entries']=entry_documents; document['public_surface_inventory_sha256']=module.sha256_hex(module.canonicalize_json(entry_documents)); model=module.LocalReleaseReadiness.model_validate(document); target.write_bytes(module.canonicalize_json(model.model_dump(mode='json')))"
```

- [ ] **Step 5: Run GREEN and the complete publication gate**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reviewer-fast-path.ps1
uv run --no-sync python -c "import json,pathlib; d=json.loads(pathlib.Path('evidence/public/portfolio/local-release-readiness.json').read_text()); assert d['technical_closure_verification']=={'full_suite_passed':1625,'full_suite_skipped':7,'review_critical':0,'review_important':0,'review_minor':0}; assert d['portfolio_ci_commit']=='8bc91a548846af0b1f1be1fc9ae6fbb80b7f63f1'; assert d['portfolio_ci_run_url'].endswith('/33322212462'); print('READINESS_HISTORY_PRESERVED')"
```

- [ ] **Step 6: Audit and commit Task 2**

```powershell
$expected = @('README.md','docs/reviewer/quickstart.md','docs/reviewer/release-evidence.md','evidence/public/portfolio/local-release-readiness.json','tests/publication/test_public_release_surface.py')
$changed = @(git diff --name-only)
if (@(Compare-Object $expected $changed).Count -ne 0) { throw 'TASK_2_PATH_SET_INVALID' }
git diff --check
git add -- README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md evidence/public/portfolio/local-release-readiness.json tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "docs: bound pending Linux smoke evidence"
```

---

### Task 3: Prove and review the first-push candidate

**Files:**

- Verify: all repository paths
- Correct only if required: Task 1 or Task 2 implementation paths

**Interfaces:**

- Consumes: committed exact workflow plus pending evidence copy.
- Produces: fresh complete local evidence and Critical `0`, Important `0` review.

- [ ] **Step 1: Run static, publication, and focused gates**

```powershell
uv lock --check
uv run --no-sync ruff check src/mdcp tests scripts
uv run --no-sync ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reviewer-fast-path.ps1
uv run --no-sync pytest -p no:cacheprovider -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
```

- [ ] **Step 2: Run the complete suite**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q
```

Record the fresh passed/skipped count in the ignored custody ledger. Do not rewrite the closed
historical `1625/7` readiness field.

- [ ] **Step 3: Recompute frozen anchors and H2 state**

```powershell
uv run --no-sync python -c "import hashlib; from pathlib import Path; from mdcp.contracts.release import serving_inventory_digest, serving_inventory_from_root; from mdcp.contracts.serving_identity_v2 import V2_SERVING_PATHS, build_v2_serving_inventory; from mdcp.temporal.runtime_guards import _worker_source_inventory, _formal_worker_source_inventory; from mdcp.temporal.evidence import HistoricalLedger; root=Path.cwd(); ledger=HistoricalLedger.frozen_v02(); print('V1='+serving_inventory_digest(serving_inventory_from_root(root))); print('V2='+build_v2_serving_inventory(root,V2_SERVING_PATHS).inventory_sha256); print('SOURCE='+str(_worker_source_inventory(root))); print('WORKER='+str(_formal_worker_source_inventory(root))); print('FIREWALL='+hashlib.sha256((root/'src/mdcp/temporal/firewall.py').read_bytes()).hexdigest()); print('UV_LOCK='+hashlib.sha256((root/'uv.lock').read_bytes()).hexdigest()); print('H2_STATUS='+ledger.h2_status); print('H2_LOADED_ROWS='+str(ledger.h2_loaded_rows))"
```

Require every value from Global Constraints.

- [ ] **Step 4: Obtain independent review**

Dispatch a clean reviewer with only the design, this plan, base SHA, and candidate SHA. Require an
explicit finding table and:

```text
Critical: 0
Important: 0
```

The review must inspect the exact workflow text, Linux-only command boundary, historical failure
preservation, pending evidence truth, canonical readiness bytes, path allowlist, and absence of
weakened tests or claims. Fix any valid Critical/Important finding with systematic debugging and TDD
inside the allowlist, then repeat all Task 3 gates and review.

- [ ] **Step 5: Audit the first-push checkpoint**

```powershell
git diff f4f6223ee2dcaa463079d9dca64b2011ecc094d7..HEAD --check
git diff --name-only f4f6223ee2dcaa463079d9dca64b2011ecc094d7..HEAD
git status --short
git rev-parse origin/main
```

Require only the authorized implementation/process paths, `origin/main` still at the reviewed base,
a clean tracked tree, and only `.hypothesis/` untracked.

---

### Task 4: Push once and authenticate the first Linux smoke run

**Files:** no repository modification.

**Interfaces:**

- Consumes: reviewed first-push candidate and unchanged remote base.
- Produces: exact successful first-push commit/run pair for final public evidence.

- [ ] **Step 1: Recheck external negative state and push once**

Require Public visibility/default `main`, approved description/topics, release-ci run count `0`, tag
count `0`, GitHub Release count `0`, matching container-package count `0`, then run:

```powershell
$firstPushCommit = git rev-parse HEAD
if ((git rev-parse origin/main) -ne 'f4f6223ee2dcaa463079d9dca64b2011ecc094d7') { throw 'REMOTE_MAIN_MOVED' }
git push origin codex/wave0-foundation-feasibility:main
```

- [ ] **Step 2: Poll the exact workflow run without dispatching**

Query Portfolio CI until exactly one `push` run with `headSha == $firstPushCommit` appears and reaches
`completed`:

```powershell
$deadline = (Get-Date).AddMinutes(45)
do {
  $runs = gh run list --repo kuotunyu/model-delivery-control-plane --workflow 'Portfolio CI' --limit 20 --json databaseId,headSha,status,conclusion,url,event,workflowName | ConvertFrom-Json
  $matching = @($runs | Where-Object { $_.headSha -eq $firstPushCommit -and $_.event -eq 'push' -and $_.workflowName -eq 'Portfolio CI' })
  if ($matching.Count -gt 1) { throw 'MULTIPLE_FIRST_PUSH_RUNS' }
  if ($matching.Count -eq 1 -and $matching[0].status -eq 'completed') { break }
  if ((Get-Date) -ge $deadline) { throw 'FIRST_PUSH_RUN_TIMEOUT' }
  Start-Sleep -Seconds 30
} while ($true)
$firstRun = gh run view $matching[0].databaseId --repo kuotunyu/model-delivery-control-plane --json headSha,status,conclusion,url,jobs | ConvertFrom-Json
if ($firstRun.headSha -ne $firstPushCommit -or $firstRun.status -ne 'completed' -or $firstRun.conclusion -ne 'success') { throw 'FIRST_PUSH_RUN_NOT_SUCCESSFUL' }
$jobs = @($firstRun.jobs)
if (@($jobs | Where-Object { $_.name -eq 'verify' -and $_.conclusion -eq 'success' }).Count -ne 1) { throw 'WINDOWS_JOB_NOT_SUCCESSFUL' }
if (@($jobs | Where-Object { $_.name -eq 'Linux read-only smoke (not portability proof)' -and $_.conclusion -eq 'success' }).Count -ne 1) { throw 'LINUX_SMOKE_JOB_NOT_SUCCESSFUL' }
$firstPushRunUrl = $firstRun.url
```

Preserve and debug any failed run; do not rerun unchanged bytes.

- [ ] **Step 3: Record the observed pair in ignored custody**

Append the exact 40-hex `$firstPushCommit`, canonical run URL, run id, both job conclusions, runner
labels, timestamps, and remote-main equality to the ignored ledger. These observed values are the
only values allowed in Task 5 public copy.

---

### Task 5: Record exact Linux smoke evidence with TDD

**Files:**

- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Modify: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**

- Consumes: Task 4's authenticated first-push commit and run URL.
- Produces: final non-recursive checked-in Linux smoke evidence.

- [ ] **Step 1: Replace the interim test with exact observed anchors**

Rename the interim test to `test_linux_read_only_smoke_binds_exact_remote_evidence()` and replace its
pending assertions with the exact `$firstPushCommit` and canonical Task 4 run URL:

```python
for logical_path in (
    "README.md",
    "docs/reviewer/quickstart.md",
    "docs/reviewer/release-evidence.md",
):
    text = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert "Linux read-only smoke (not portability proof)" in text
    assert f"Linux read-only smoke success commit: {FIRST_PUSH_COMMIT}" in text
    assert f"Linux read-only smoke success run: {FIRST_PUSH_RUN_URL}" in text
    assert "LINUX_READ_ONLY_SMOKE_PASS != CROSS_PLATFORM_PORTABLE" in text
    assert "successful remote evidence is not yet claimed" not in text
```

Define `FIRST_PUSH_COMMIT` and `FIRST_PUSH_RUN_URL` as exact local test constants using the observed
values. The commit must match `[0-9a-f]{40}` and the URL must match
`https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/[1-9][0-9]*`.

- [ ] **Step 2: Run RED and inspect the expected failure**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py::test_linux_read_only_smoke_binds_exact_remote_evidence
```

Expected: failure because the documents still contain only the interim wording.

- [ ] **Step 3: Replace interim copy with exact evidence**

Build the exact replacement lines from the authenticated Task 4 variables:

```powershell
$finalSmokeCopy = @(
  "Linux read-only smoke success commit: $firstPushCommit",
  "Linux read-only smoke success run: $firstPushRunUrl",
  'LINUX_READ_ONLY_SMOKE_PASS != CROSS_PLATFORM_PORTABLE',
  'Windows full suite remains the authoritative gate.'
)
```

In all three documents replace only the pending four-line block with those four exact lines. Confirm
that `$firstPushCommit` matches `[0-9a-f]{40}` and `$firstPushRunUrl` matches the repository-specific
Actions-run URL before editing. Keep the historical Ubuntu failure only in `release-evidence.md`.

- [ ] **Step 4: Regenerate readiness and run GREEN**

Run Task 2 Step 4's canonical regeneration command, then:

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
uv run --no-sync ruff check tests/publication/test_public_release_surface.py
uv run --no-sync ruff format --check tests/publication/test_public_release_surface.py
```

- [ ] **Step 5: Audit and commit final evidence**

```powershell
$expected = @('README.md','docs/reviewer/quickstart.md','docs/reviewer/release-evidence.md','evidence/public/portfolio/local-release-readiness.json','tests/publication/test_public_release_surface.py')
$changed = @(git diff --name-only)
if (@(Compare-Object $expected $changed).Count -ne 0) { throw 'TASK_5_PATH_SET_INVALID' }
git diff --check
git add -- README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md evidence/public/portfolio/local-release-readiness.json tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "evidence: record Linux read-only smoke"
```

---

### Task 6: Prove, review, push, and close the final evidence commit

**Files:** no planned repository modification after a green candidate.

**Interfaces:**

- Consumes: Task 5's final evidence commit.
- Produces: second successful remote Portfolio CI run and complete closure audit.

- [ ] **Step 1: Repeat the full local gate**

Repeat Task 3 Steps 1–3, including the complete pytest suite and exact frozen anchors. Run
`git diff --check` and verify all historical readiness fields remain exact.

- [ ] **Step 2: Obtain final independent review**

Review Task 4's first-push commit through current HEAD against the design and plan. Require Critical
`0`, Important `0`; explicitly validate that test constants, three documents, and custody record all
name the same authenticated first-push commit/run and that readiness binds their final bytes.

- [ ] **Step 3: Push the final evidence commit once**

```powershell
$finalCommit = git rev-parse HEAD
$readme = Get-Content -LiteralPath README.md -Raw
$match = [regex]::Match($readme, 'Linux read-only smoke success commit: ([0-9a-f]{40})')
if (-not $match.Success) { throw 'FIRST_PUSH_COMMIT_EVIDENCE_MISSING' }
$expectedRemote = $match.Groups[1].Value
if ((git rev-parse origin/main) -ne $expectedRemote) { throw 'REMOTE_MAIN_MOVED' }
git push origin codex/wave0-foundation-feasibility:main
```

Require `$expectedRemote` to equal the authenticated first-push commit recorded in custody before
executing the push.

- [ ] **Step 4: Authenticate final CI jobs**

Poll, without dispatch/rerun, for exactly one Portfolio CI `push` run whose head SHA equals
`$finalCommit`. Require overall `completed/success` and both Windows `verify` and
`Linux read-only smoke (not portability proof)` jobs `success`.

- [ ] **Step 5: Execute the final requirement-by-requirement audit**

Require:

- local HEAD, `origin/main`, and `refs/heads/main` all equal `$finalCommit`;
- Public visibility, default `main`, approved description, and exact six topics;
- anonymous repository and raw README HTTP `200`;
- README contains the exact first-push Linux run evidence and does not claim portability;
- the first-push and final Portfolio CI runs remain completed/success with both jobs successful;
- release-ci runs, remote tags, GitHub Releases, and exact matching container package all remain `0`;
- public verifier, deterministic demo, and reviewer fast path pass with zero mutations;
- all frozen anchors and H2 state equal Global Constraints;
- tracked worktree is clean, with only `.hypothesis/` untracked.

- [ ] **Step 6: Record custody and report the safe checkpoint**

Append both pushed commits/runs, exact job results, both local suite counts/durations, both review
results, frozen anchors, Public metadata, negative release/package state, and final clean status to
the ignored ledger. Notify Portfolio Control of the final HEAD and active/clean checkpoint without
modifying another repository.

Close only with:

```text
PUBLIC_GITHUB_PORTFOLIO_READY
/ WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS
/ LINUX_READ_ONLY_SMOKE_PASS
!= CROSS_PLATFORM_PORTABLE
/ REMOTE_RELEASED
/ PRODUCTION_READY
```
