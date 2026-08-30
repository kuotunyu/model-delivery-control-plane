# MDCP Safe GitHub Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the complete reviewed MDCP history as `kuotunyu/model-delivery-control-plane` through a Private staging gate, read-only Portfolio CI, truthful post-push readiness evidence, and a final Public visibility transition without executing any release or production path.

**Architecture:** Add one evidence-bound, read-only GitHub Actions workflow to the existing ten-file public surface. First prove the workflow and unchanged technical closure locally, then scan all Git history with a checksum-verified pinned `gitleaks`, create one Private GitHub repository, and push the reviewed branch to remote `main`. Record the observed Phase A workflow run in a closed readiness-v2 contract, re-run local and remote verification, and only then make the same repository Public and audit its externally visible state.

**Tech Stack:** Python 3.12, `uv` 0.11.18, Pydantic v2, pytest, Ruff, PowerShell, Git, GitHub CLI, GitHub Actions, `gitleaks` 8.30.1.

**Approved design:** `docs/superpowers/specs/2026-08-30-mdcp-safe-github-publication-design.md` at commit `1875712fb25d15eed97655d54b235ca9ed982685`, SHA-256 `ac1520811b651c33b8c6fa37bdb733cc2ebf1de7803cea2597d162d8088053f8`.

---

## Fixed scope and stop conditions

Implementation may modify only:

```text
.gitattributes
.github/workflows/portfolio-ci.yml
README.md
docs/reviewer/quickstart.md
docs/reviewer/release-evidence.md
evidence/public/portfolio/local-release-readiness.json
schemas/portfolio/local-release-readiness.schema.json
scripts/verify-public-release.py
tests/publication/test_public_release_surface.py
tests/publication/test_release_workflow.py
```

This plan file is already committed separately and is not an implementation path. Do not modify `.github/workflows/release-ci.yml`, `src/mdcp`, dependencies, `uv.lock`, historical search/formal evidence, serving identities, model/data fixtures, Docker or Compose files, any other repository, or local `main`.

The only allowed remote mutations are: create one Private repository named `kuotunyu/model-delivery-control-plane`; add its HTTPS URL as `origin`; non-force push the reviewed HEAD to remote `main`; later non-force push the scoped readiness-v2 commit; set remote default branch `main`; change this same repository to Public after both Portfolio CI gates pass; and set the exact description and topics in Task 4. Never dispatch release CI, create a tag or GitHub Release, publish a package/GHCR image, merge, force-push, delete or rename a repository, alter billing/secrets/branch protection, run Docker, execute model/data/H2/P2 work, or make production/Kubernetes claims.

Fail closed and stop before the next phase if the worktree is dirty outside the current task, GitHub authentication is not `kuotunyu`, the target repository unexpectedly exists before creation, any preflight has an unresolved finding, any action ref is not a full approved SHA, a local or remote gate is not successful, or review reports Critical or Important findings. Preserve the Private repository and local state for systematic debugging; never delete, recreate, force-push, or make Public as recovery.

Use the existing linked worktree:

```text
D:\AI-Portfolio\CC_github部隊\model-delivery-control-plane\.worktrees\wave0-foundation-feasibility
```

Keep the local branch named `codex/wave0-foundation-feasibility`. Map its reviewed HEAD to `origin/main`; do not checkout or rewrite local `main`.

## Shared verification gate

Run this complete gate after every source-changing task, before its commit:

```powershell
uv lock --check
uv run --no-sync ruff check src/mdcp tests scripts
uv run --no-sync ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reviewer-fast-path.ps1
uv run --no-sync pytest -p no:cacheprovider -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
uv run --no-sync pytest -p no:cacheprovider -q
git diff --check
git status --short
```

The repository has legacy Ruff-format drift outside this slice. Do not run or require global `ruff format --check src/mdcp tests scripts`; the exact three changed Python files above are the approved format surface. After the gate, request independent code review against the task and design. Commit only with Critical `0`, Important `0`, a clean index outside the exact task paths, and the existing approved author/committer identity.

Record the frozen reference hashes before Task 1 and compare them after Tasks 1 and 3:

```powershell
Get-FileHash README.md -Algorithm SHA256
Get-FileHash evidence/public/portfolio/local-release-readiness.json -Algorithm SHA256
Get-FileHash uv.lock -Algorithm SHA256
uv run --no-sync python -c "from mdcp.serving.identity import serving_identity_v1; print(serving_identity_v1())"
uv run --no-sync python -c "from mdcp.serving.identity import serving_identity_v2; print(serving_identity_v2())"
```

README and readiness hashes are expected to change inside this plan. `uv.lock`, v1 serving identity, v2 serving identity, the historical search receipt/index, source inventory, worker inventory, and static-firewall identity must not change.

---

## Task 1: Add and locally prove read-only Portfolio CI

**Files:**

- Create: `.github/workflows/portfolio-ci.yml`
- Modify: `.gitattributes`
- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Modify: `scripts/verify-public-release.py`
- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `tests/publication/test_release_workflow.py`
- Regenerate: `schemas/portfolio/local-release-readiness.schema.json`
- Regenerate: `evidence/public/portfolio/local-release-readiness.json`

### Step 1: Establish the exact starting state

- [ ] Verify clean scope and the reviewed plan parent:

```powershell
git status --short --branch
git rev-parse HEAD
git log -1 --format="%an%n%ae%n%cn%n%ce"
git remote -v
gh auth status
gh repo view kuotunyu/model-delivery-control-plane --json nameWithOwner,visibility
```

Expected: branch `codex/wave0-foundation-feasibility`; HEAD is the plan commit; no implementation changes; identity matches existing commits; no remote target exists. `gh repo view` must fail because the target is absent. If it succeeds, stop.

- [ ] Record all frozen reference hashes named in the shared gate and confirm the design SHA-256:

```powershell
(Get-FileHash docs/superpowers/specs/2026-08-30-mdcp-safe-github-publication-design.md -Algorithm SHA256).Hash.ToLowerInvariant()
```

Expected: `ac1520811b651c33b8c6fa37bdb733cc2ebf1de7803cea2597d162d8088053f8`.

### Step 2: Write failing workflow and public-surface tests

- [ ] In `tests/publication/test_release_workflow.py`, retain all release-workflow tests and add separate Portfolio CI constants and a reader:

```python
PORTFOLIO_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "portfolio-ci.yml"
PORTFOLIO_ACTIONS = {
    "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
    "astral-sh/setup-uv": "20cfd1bf945f4377ade1205e4dbc17946fc9a30d",
}


def _portfolio_workflow() -> str:
    return PORTFOLIO_WORKFLOW_PATH.read_text(encoding="utf-8")
```

- [ ] Add tests that require all of the following and reject nearby mutations:

  - name `Portfolio CI`;
  - only `push` to `main` and `pull_request` targeting `main`;
  - no `workflow_dispatch`, tag, schedule, or release trigger;
  - top-level `permissions` contains only `contents: read` and no job-level permission escalation;
  - `ubuntu-24.04`, timeout `30`, and same-ref cancellation;
  - checkout and setup-uv refs equal the exact full SHAs above;
  - checkout inputs `fetch-depth: 0` and `persist-credentials: false`;
  - setup inputs `version: "0.11.18"`, `python-version: "3.12"`, `enable-cache: false`;
  - locked install, lock check, global Ruff check, exact changed-Python format check, public verifier, reviewer demo, complete pytest with `-p no:cacheprovider`, and `git diff --exit-code`;
  - no `secrets`, write permission, Docker, GHCR, OIDC, attestations, uploads, packages, tags, or releases.

- [ ] In `tests/publication/test_public_release_surface.py`, first update `test_verifier_exposes_only_the_closed_public_contract` to require the byte-sorted ten-path tuple with `.github/workflows/portfolio-ci.yml` first. Add an assertion that `.gitattributes` fixes the new workflow to `text eol=lf`; keep the fresh `core.autocrlf=true` checkout regression covering every `PUBLIC_SURFACE_PATHS` member.

- [ ] Run RED:

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_release_workflow.py tests/publication/test_public_release_surface.py
```

Expected: failures identify the absent workflow and nine-path inventory. No pre-existing unrelated failure is acceptable.

### Step 3: Implement the exact Portfolio CI workflow

- [ ] Create `.github/workflows/portfolio-ci.yml` with these exact semantics:

```yaml
name: Portfolio CI

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

permissions:
  contents: read

concurrency:
  group: portfolio-ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  verify:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
      - name: Checkout complete evidence history
        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
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
      - name: Verify lock and static checks
        run: |
          uv lock --check
          uv run --no-sync ruff check src/mdcp tests scripts
          uv run --no-sync ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
      - name: Verify public evidence and deterministic demo
        run: |
          uv run --no-sync python scripts/verify-public-release.py --repository-root .
          uv run --no-sync python scripts/reviewer-demo.py --repository-root .
      - name: Run complete test suite
        run: uv run --no-sync pytest -p no:cacheprovider -q
      - name: Reject tracked-file mutation
        run: git diff --exit-code
```

Do not add caching, secrets, environment variables, artifact upload, release logic, or any additional action.

### Step 4: Bind the workflow into public evidence

- [ ] Add this exact LF rule to `.gitattributes` without modifying unrelated rules:

```gitattributes
.github/workflows/portfolio-ci.yml text eol=lf
```

- [ ] Add `.github/workflows/portfolio-ci.yml` first in `PUBLIC_SURFACE_PATHS` because UTF-8 byte sorting places `.` before `L`. Keep all other entries and order unchanged.

- [ ] Update public copy in `README.md`, `docs/reviewer/quickstart.md`, and `docs/reviewer/release-evidence.md` so a reviewer sees two separate authorities:

```text
Portfolio CI: configured, read-only verification; no remote execution recorded yet.
Release CI: manual design surface only; not dispatched and not evidence of a release.
```

Keep `zh-TW` primary, technical terms in English, and all release/GHCR/tag/production/Kubernetes/H2/CV/LLM claims explicitly false. Add no CI badge until a remotely observed run exists.

### Step 5: Regenerate schema and canonical readiness v1

- [ ] Regenerate the schema directly from the closed model:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); target=root/module.SCHEMA_PATH; target.write_text(json.dumps(module.LocalReleaseReadiness.model_json_schema(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')"
```

- [ ] Regenerate readiness while keeping schema v1 and every execution claim false:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); target=root/module.READINESS_PATH; document=json.loads(target.read_text(encoding='utf-8')); entries=module.build_public_surface_inventory(root); entry_documents=[entry.model_dump(mode='json') for entry in entries]; document['public_surface_entries']=entry_documents; document['public_surface_inventory_sha256']=module.sha256_hex(module.canonicalize_json(entry_documents)); model=module.LocalReleaseReadiness.model_validate(document); target.write_bytes(module.canonicalize_json(model.model_dump(mode='json')))"
```

- [ ] Confirm `push_executed`, `remote_release_executed`, `tag_created`, `production_deployed`, `kubernetes_production_ready`, `h2_executed`, `cv_workload_implemented`, and `llm_workload_implemented` are all exactly `false`.

### Step 6: Prove GREEN, review, and commit Phase A

- [ ] Run the shared verification gate and compare all frozen identities/hashes. The full suite is mandatory.
- [ ] Obtain independent review of the exact Task 1 diff. Require Critical `0`, Important `0`; address any in-scope finding with TDD and rerun the full gate.
- [ ] Inspect the exact staged paths:

```powershell
git diff --name-only
git diff -- .gitattributes .github/workflows/portfolio-ci.yml README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md scripts/verify-public-release.py tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py schemas/portfolio/local-release-readiness.schema.json evidence/public/portfolio/local-release-readiness.json
git status --short
```

- [ ] Commit only the ten Task 1 paths:

```powershell
git add -- .gitattributes .github/workflows/portfolio-ci.yml README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md scripts/verify-public-release.py tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py schemas/portfolio/local-release-readiness.schema.json evidence/public/portfolio/local-release-readiness.json
git diff --cached --check
git commit -m "ci: add read-only portfolio verification"
```

- [ ] Record the Phase A commit as `$phaseACommit = (git rev-parse HEAD).Trim()` and require a clean worktree. Do not create the remote until this task is fully green and reviewed.

---

## Task 2: Scan complete history and prove the Private staging checkout

**Repository files:** no source-file modifications. `.git/config` may gain only the `origin` HTTPS remote and upstream tracking through normal Git commands.

### Step 1: Repeat the publication preflight

- [ ] Require clean Task 1 commit state, expected authenticated owner, and absent target:

```powershell
git status --short --branch
$phaseACommit = (git rev-parse HEAD).Trim()
gh api user --jq .login
gh repo view kuotunyu/model-delivery-control-plane --json nameWithOwner,visibility
git remote -v
```

Expected login: `kuotunyu`. The target lookup must fail and no conflicting `origin` may exist. If the repository exists or an origin points elsewhere, stop without mutation.

- [ ] Recheck tracked-path count, history count, maximum blob size, authors, private-path patterns, and the frozen identities defined in the design. Inspect any delta; do not assume the earlier audit remains sufficient.

### Step 2: Download and checksum a pinned official scanner outside the repository

- [ ] Create an OS-managed temporary directory and download only official `gitleaks` 8.30.1 assets:

```powershell
$scanTemp = New-Item -ItemType Directory -Path ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Path]::GetRandomFileName()))
$zipPath = Join-Path $scanTemp.FullName 'gitleaks_8.30.1_windows_x64.zip'
$checksumsPath = Join-Path $scanTemp.FullName 'gitleaks_8.30.1_checksums.txt'
Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_windows_x64.zip' -OutFile $zipPath
Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt' -OutFile $checksumsPath
(Get-FileHash $checksumsPath -Algorithm SHA256).Hash.ToLowerInvariant()
(Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
```

Expected checksums:

```text
checksums file: 061476c21adaf5441516f96f185c1a4706a83cd6329b9b38762271b3d4a52fae
Windows x64 zip: d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e
```

Stop before extraction if either differs.

- [ ] Extract outside the repository and confirm version:

```powershell
Expand-Archive -LiteralPath $zipPath -DestinationPath $scanTemp.FullName
$gitleaks = Join-Path $scanTemp.FullName 'gitleaks.exe'
& $gitleaks version
```

Expected: `8.30.1`.

### Step 3: Scan every reachable historical object

- [ ] Run the official Git-history scanner with redacted terminal output and no repository report:

```powershell
& $gitleaks git --redact --no-banner --log-opts='--all' (Get-Location).Path
if ($LASTEXITCODE -ne 0) { throw 'FULL_HISTORY_GITLEAKS_FAILED' }
```

Require zero unresolved findings. For any finding, manually inspect its exact path, commit, and rule. Do not create a wildcard, repository-wide exclusion, tracked report, or scanner config. Any exact synthetic-test exception requires a new written scope decision before proceeding.

### Step 4: Create exactly one Private repository and push Phase A

- [ ] Recheck target absence immediately before creation, then create it Private with the exact description:

```powershell
gh repo view kuotunyu/model-delivery-control-plane --json nameWithOwner,visibility
gh repo create kuotunyu/model-delivery-control-plane --private --description "Evidence-gated model delivery reference implementation with content-addressed identity, temporal controls, and fail-closed verification."
```

The first command must fail. If creation fails or reports an existing repository, stop.

- [ ] Add only the exact HTTPS origin and non-force push the full reachable branch history to remote `main`:

```powershell
git remote add origin https://github.com/kuotunyu/model-delivery-control-plane.git
git push --set-upstream origin HEAD:main
gh repo edit kuotunyu/model-delivery-control-plane --default-branch main
```

Do not use `--force`, tags, mirrors, releases, packages, or another ref mapping.

- [ ] Verify the remote remains Private and points to `$phaseACommit`:

```powershell
gh repo view kuotunyu/model-delivery-control-plane --json nameWithOwner,visibility,defaultBranchRef,url
git ls-remote origin refs/heads/main
```

Expected: visibility `PRIVATE`; default branch `main`; remote SHA equals `$phaseACommit`.

### Step 5: Wait for the exact Phase A Portfolio CI run

- [ ] Find only the `Portfolio CI` run for `$phaseACommit`, record its database ID and URL, and wait for terminal state:

```powershell
$phaseARuns = gh run list --repo kuotunyu/model-delivery-control-plane --workflow portfolio-ci.yml --branch main --commit $phaseACommit --limit 5 --json databaseId,headSha,status,conclusion,url,workflowName | ConvertFrom-Json
$phaseARun = $phaseARuns | Where-Object { $_.headSha -eq $phaseACommit -and $_.workflowName -eq 'Portfolio CI' } | Select-Object -First 1
if ($null -eq $phaseARun) { throw 'PHASE_A_PORTFOLIO_CI_MISSING' }
gh run watch $phaseARun.databaseId --repo kuotunyu/model-delivery-control-plane --exit-status
```

- [ ] Read back the run and require exact `headSha`, `completed`, and `success`:

```powershell
gh run view $phaseARun.databaseId --repo kuotunyu/model-delivery-control-plane --json headSha,status,conclusion,url,workflowName,jobs
```

Record `$phaseARunUrl` from the canonical returned URL. A missing, failed, cancelled, or timed-out run ends this task with the repository still Private. Use systematic debugging for failures, make only allowlisted fixes under Task 1's full local gate/review, non-force push a new commit, and treat that new commit as the Phase A commit.

- [ ] Verify release workflow was not dispatched and tags/releases/packages remain absent before Task 3.

---

## Task 3: Record observed remote facts in closed readiness v2

**Files:**

- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Modify: `scripts/verify-public-release.py`
- Modify: `tests/publication/test_public_release_surface.py`
- Regenerate: `schemas/portfolio/local-release-readiness.schema.json`
- Regenerate: `evidence/public/portfolio/local-release-readiness.json`

Do not alter the already-proved Portfolio CI workflow in this task unless a genuine failed-run corrective returns execution to Task 1 gates.

### Step 1: Capture and validate the observed Phase A anchors

- [ ] From GitHub, not memory, populate and validate:

```powershell
$phaseACommit = (gh run view $phaseARun.databaseId --repo kuotunyu/model-delivery-control-plane --json headSha --jq .headSha).Trim()
$phaseARunUrl = (gh run view $phaseARun.databaseId --repo kuotunyu/model-delivery-control-plane --json url --jq .url).Trim()
if ($phaseACommit -notmatch '^[0-9a-f]{40}$') { throw 'PHASE_A_COMMIT_INVALID' }
if ($phaseARunUrl -notmatch '^https://github\.com/kuotunyu/model-delivery-control-plane/actions/runs/[1-9][0-9]*$') { throw 'PHASE_A_RUN_URL_INVALID' }
```

Reconfirm the run is successful, the remote is Private, and remote `main` still points to `$phaseACommit`.

### Step 2: Write failing readiness-v2 contract tests

- [ ] Update checked-in evidence/schema expectations so tests require:

```python
readiness.schema_version == "mdcp.local-release-readiness.v2"
readiness.evidence_class == "github_portfolio_publication_readiness"
readiness.claim_ceiling == "mdcp.github-portfolio-claim-ceiling.v2"
readiness.claim_execution.push_executed is True
readiness.claim_execution.portfolio_ci_executed is True
readiness.portfolio_ci_commit == phase_a_commit
readiness.portfolio_ci_run_url == phase_a_run_url
```

- [ ] Extend the mutation matrix to reject: a short or non-hex commit; an alternate owner/repository/scheme/path URL; missing or false `portfolio_ci_executed`; false `push_executed`; unknown fields; noncanonical bytes; affirmative release/tag/production/Kubernetes/H2/CV/LLM state; or a public-surface inventory mismatch. Continue mapping model-validation failures to `PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID`.

- [ ] Run RED:

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py
```

Expected: v1 implementation cannot satisfy the new v2 assertions.

### Step 3: Implement the closed v2 model

- [ ] In `scripts/verify-public-release.py`, add exact reusable constrained string types:

```python
CommitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
PortfolioCiRunUrl = Annotated[
    str,
    StringConstraints(
        pattern=(
            r"^https://github\.com/kuotunyu/model-delivery-control-plane/"
            r"actions/runs/[1-9][0-9]*$"
        )
    ),
]
```

- [ ] Evolve only the readiness/publication contract:

```python
class ClaimExecution(ClosedModel):
    remote_release_executed: Literal[False]
    push_executed: Literal[True]
    portfolio_ci_executed: Literal[True]
    tag_created: Literal[False]
    production_deployed: Literal[False]
    kubernetes_production_ready: Literal[False]
    h2_executed: Literal[False]
    cv_workload_implemented: Literal[False]
    llm_workload_implemented: Literal[False]
```

Set `LocalReleaseReadiness.schema_version` to `mdcp.local-release-readiness.v2`, `evidence_class` to `github_portfolio_publication_readiness`, and `claim_ceiling` to `mdcp.github-portfolio-claim-ceiling.v2`. Add required top-level fields `portfolio_ci_commit: CommitSha` and `portfolio_ci_run_url: PortfolioCiRunUrl`. Preserve all historical closure and identity literals, `publication_status: "public"`, `h2_status: "SEALED_NOT_LOADED"`, and `h2_loaded_rows: 0`.

The record authenticates the prior Phase A run only. Do not claim that it authenticates its own Phase C commit.

### Step 4: Update docs and generate the observed canonical evidence

- [ ] Update `README.md`, `docs/reviewer/quickstart.md`, and `docs/reviewer/release-evidence.md` to state that read-only Portfolio CI succeeded for the recorded Phase A commit/run. Preserve the exact distinction:

```text
REMOTE_PORTFOLIO_CI_PASS != REMOTE_RELEASED != PRODUCTION_READY
```

State that release CI, GHCR/package publication, tag, GitHub Release, P2, H2, CV/LLM workload execution, Kubernetes readiness, and production deployment remain unexecuted. `publication_status: "public"` classifies the evidence surface; it does not predict current GitHub visibility.

- [ ] Regenerate the model schema using Task 1's schema command.

- [ ] Construct the v2 document from the existing evidence, setting only observed anchors and the approved state transition, then rebuild the ten-path inventory after all public files reach final bytes:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); target=root/module.READINESS_PATH; document=json.loads(target.read_text(encoding='utf-8')); document['schema_version']='mdcp.local-release-readiness.v2'; document['evidence_class']='github_portfolio_publication_readiness'; document['portfolio_ci_commit']='$phaseACommit'; document['portfolio_ci_run_url']='$phaseARunUrl'; document['claim_ceiling']='mdcp.github-portfolio-claim-ceiling.v2'; document['claim_execution']['push_executed']=True; document['claim_execution']['portfolio_ci_executed']=True; entries=module.build_public_surface_inventory(root); entry_documents=[entry.model_dump(mode='json') for entry in entries]; document['public_surface_entries']=entry_documents; document['public_surface_inventory_sha256']=module.sha256_hex(module.canonicalize_json(entry_documents)); model=module.LocalReleaseReadiness.model_validate(document); target.write_bytes(module.canonicalize_json(model.model_dump(mode='json')))"
```

If PowerShell interpolates the URL or commit unexpectedly, use a temporary process environment variable; do not hard-code a guessed run ID.

### Step 5: Prove GREEN, review, commit, and push Phase C

- [ ] Run the complete shared verification gate and compare frozen identities/hashes.
- [ ] Independently review the Task 3 diff and require Critical `0`, Important `0`.
- [ ] Stage only the seven Task 3 paths and commit:

```powershell
git add -- README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md scripts/verify-public-release.py tests/publication/test_public_release_surface.py schemas/portfolio/local-release-readiness.schema.json evidence/public/portfolio/local-release-readiness.json
git diff --cached --check
git commit -m "evidence: record remote portfolio verification"
$phaseCCommit = (git rev-parse HEAD).Trim()
git push origin HEAD:main
```

No force option is permitted. Require remote `main` to equal `$phaseCCommit`.

### Step 6: Require the Phase C remote gate

- [ ] Locate, wait for, and inspect the exact Portfolio CI run for `$phaseCCommit` using the Task 2 commands with the new commit.
- [ ] Require success and inspect failed/cancelled/missing conditions before any visibility mutation.
- [ ] Confirm again that release workflow runs, tags, releases, and packages remain absent and the repository is still Private.

---

## Task 4: Transition the verified repository to Public and audit the result

**Repository files:** no modifications and no commit.

### Step 1: Final pre-transition gate

- [ ] Require all of these simultaneously:

  - clean local worktree at `$phaseCCommit`;
  - remote `main` equals `$phaseCCommit`;
  - exact Phase C Portfolio CI run is `completed/success`;
  - readiness v2 records the successful Phase A commit/run;
  - repository visibility is still Private;
  - release workflow run count, tags, releases, packages, GHCR publication, and HEAD tags are zero;
  - frozen identities and H2 sealed/zero state remain unchanged.

Any mismatch stops the visibility transition.

### Step 2: Make the same repository Public and set exact metadata

- [ ] Change only visibility and approved metadata:

```powershell
gh repo edit kuotunyu/model-delivery-control-plane --visibility public --accept-visibility-change-consequences
gh repo edit kuotunyu/model-delivery-control-plane --description "Evidence-gated model delivery reference implementation with content-addressed identity, temporal controls, and fail-closed verification."
gh repo edit kuotunyu/model-delivery-control-plane --remove-topic mlops --remove-topic model-delivery --remove-topic machine-learning --remove-topic ai-engineering --remove-topic onnx --remove-topic supply-chain-security
gh repo edit kuotunyu/model-delivery-control-plane --add-topic mlops --add-topic model-delivery --add-topic machine-learning --add-topic ai-engineering --add-topic onnx --add-topic supply-chain-security
```

Before the remove/add commands, read existing topics. If any unexpected topic exists, remove it explicitly only from this repository so the final set is exact; do not touch any other repository. The idempotent removals above may report absent topics and must not trigger any broader recovery.

### Step 3: Verify external public state without relying on the authenticated checkout

- [ ] Read repository metadata and require exact owner, Public visibility, default branch, description, and topic set:

```powershell
gh repo view kuotunyu/model-delivery-control-plane --json nameWithOwner,visibility,defaultBranchRef,description,repositoryTopics,url
git ls-remote origin refs/heads/main
```

- [ ] Verify unauthenticated HTTP access to both repository and raw README in a process that does not pass GitHub credentials:

```powershell
$repoResponse = Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/kuotunyu/model-delivery-control-plane'
$readmeResponse = Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/kuotunyu/model-delivery-control-plane/main/README.md'
if ($repoResponse.StatusCode -ne 200 -or $readmeResponse.StatusCode -ne 200) { throw 'ANONYMOUS_PUBLIC_READ_FAILED' }
```

- [ ] Re-read the exact Phase C run URL and require it remains visible and successful.

### Step 4: Verify negative release and production evidence

- [ ] Audit remote negative state:

```powershell
gh run list --repo kuotunyu/model-delivery-control-plane --workflow release-ci.yml --limit 100 --json databaseId,status,conclusion,headSha
gh release list --repo kuotunyu/model-delivery-control-plane --limit 100
gh api repos/kuotunyu/model-delivery-control-plane/tags
gh api users/kuotunyu/packages?package_type=container
```

Require no release-workflow runs, tags, GitHub Releases, or repository-associated package/GHCR publication. If the user account has unrelated packages, do not mutate them; identify only whether this repository name is absent.

- [ ] Run final local non-mutating verification on the exact public bytes:

```powershell
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reviewer-fast-path.ps1
git status --short --branch
```

- [ ] Report the public URL, local and remote final commit, Phase A recorded commit/run URL, Phase C successful run URL, final visibility/metadata, all local test counts, independent review counts, frozen identity checks, and negative release/tag/package/H2/P2/model/data/production state. State the final claim exactly:

```text
PUBLIC_GITHUB_PORTFOLIO_READY / REMOTE_PORTFOLIO_CI_PASS
!= REMOTE_RELEASED / PRODUCTION_READY
```

Do not create a tag, GitHub Release, package, badge that claims release, or any post-publication mutation beyond the exact metadata above.

---

## Expected commit and remote sequence

```text
1875712 docs: design safe GitHub publication
    |
    +-- plan commit: docs: plan safe GitHub publication
    |
    +-- Phase A: ci: add read-only portfolio verification
    |      local full gate + review
    |      checksum-verified full-history scan
    |      create Private repo
    |      non-force push HEAD -> origin/main
    |      remote Portfolio CI success
    |
    +-- Phase C: evidence: record remote portfolio verification
           local full gate + review
           non-force push HEAD -> origin/main
           remote Portfolio CI success
           Private -> Public
           external read-back and negative-release audit
```

There is intentionally no merge, tag, release, package publication, release-workflow dispatch, or local-main update in this plan.
