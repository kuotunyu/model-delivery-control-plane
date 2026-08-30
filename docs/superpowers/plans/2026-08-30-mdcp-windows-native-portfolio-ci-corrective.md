# MDCP Windows-Native Portfolio CI Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the failed Ubuntu staging gate with a read-only Windows-native full-suite Portfolio CI, truthfully record the failed and successful remote states, and resume the approved Private-to-Public sequence without broadening release or production claims.

**Architecture:** The first corrective commit configures the ephemeral Windows checkout before repository materialization, pins Node24 checkout and a checksum-verified Compose config renderer, and evolves readiness to a closed v1.1 failed-staging state. After that commit passes Private Portfolio CI, a second commit evolves the contract to final readiness v2 bound to the successful corrective run. Public visibility remains separately gated on package API readback, a second successful Windows run, frozen identities, and the original negative-release checks.

**Tech Stack:** Windows Server 2025 GitHub-hosted runner, PowerShell 7, Git, Python 3.12, `uv` 0.11.18, Pydantic v2, pytest, Ruff, GitHub Actions, GitHub CLI, Docker Compose 5.5.0 config renderer.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-30-mdcp-windows-native-portfolio-ci-corrective-design.md` at commit `5d7611a11b3a5d490698ff280dec6fce40e3c945`, SHA-256 `7eaed881b029c1294cdd680375f965b8a827443bada3a1cc2ed5715f35001751`.
- Use the existing linked worktree and branch `codex/wave0-foundation-feasibility`; do not checkout, merge, reset, delete, or force-update local `main`.
- Remote remains exactly `origin=https://github.com/kuotunyu/model-delivery-control-plane.git` and Private until every final gate passes.
- Failed Phase A anchors are immutable: commit `1b44a3e001d6522b6409bae24e07740bf053186d`, run `https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512`, conclusion `failure`.
- Portfolio CI remains push-to-`main`/pull-request-to-`main` only, `contents: read`, complete history, no persisted credentials, no cache, complete pytest, and tracked-file mutation rejection.
- Runner is exactly `windows-2025`; run steps use `pwsh`; pre-checkout policy is only `core.autocrlf=true` and `core.fileMode=false`.
- Pin `actions/checkout` to Node24 v7.0.1 commit `3d3c42e5aac5ba805825da76410c181273ba90b1` and `astral-sh/setup-uv` to v10.0.1 commit `20cfd1bf945f4377ade1205e4dbc17946fc9a30d`.
- Docker Compose config tooling is exactly v5.5.0 official Windows x86-64 binary with SHA-256 `51e1e61195f3616896265487ed64551095f3bd27ac7fbd5758d3538c3bfa1b19`; it may render `docker compose config` only. No login, registry request, daemon, image pull/build/run, container, network, or volume action.
- No test group may be removed, xfailed, filtered, or conditionally skipped. Do not modify feasibility tests or Compose YAML.
- Preserve `uv.lock`, production code, historical search/formal evidence, v1/v2 serving identities, source/worker inventories, static firewall, H2 sealed/zero state, model/data fixtures, and historical closure.
- Never dispatch `release-ci.yml`; never force-push, merge, tag, create a GitHub Release, publish a package/GHCR image, run P2/H2/model/data, claim Kubernetes/production readiness, delete/recreate the repository, or touch another repository.
- Every source-changing task uses TDD, the complete local gate, independent review, existing Git identity, and Critical `0`/Important `0` before commit or push.
- A failed/missing/cancelled/timed-out remote run leaves the repository Private and triggers systematic debugging. Never retry unchanged bytes.
- `read:packages` is not authorized. Stop before any auth-scope or Public-visibility mutation until the user separately authorizes read-only package access.
- Implementation may modify only `.github/workflows/portfolio-ci.yml`, `README.md`, `docs/reviewer/quickstart.md`, `docs/reviewer/release-evidence.md`, `evidence/public/portfolio/local-release-readiness.json`, `schemas/portfolio/local-release-readiness.schema.json`, `scripts/verify-public-release.py`, `tests/publication/test_public_release_surface.py`, and `tests/publication/test_release_workflow.py`. This plan file is committed separately and is not an implementation path.

## Shared local verification gate

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

Require formatting only for the exact three changed Python files above; global format has inherited drift. Treat `.hypothesis/`, `__pycache__`, and pytest caches as non-source and never stage them.

Use the verified identity APIs:

```powershell
uv run --no-sync python -c "from mdcp.contracts.release import serving_identity_v1; print(serving_identity_v1())"
uv run --no-sync python -c "from mdcp.contracts.serving_identity_v2 import serving_identity_v2; print(serving_identity_v2())"
```

Expected v1 is `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`; v2 is `198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea`; `uv.lock` is `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`. Search receipt/index, source/worker inventory, and static-firewall values remain those frozen in the design.

---

### Task 1: Build Windows-native CI and truthful failed-staging readiness v1.1

**Files:**

- Modify: `.github/workflows/portfolio-ci.yml`
- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Modify: `scripts/verify-public-release.py`
- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `tests/publication/test_release_workflow.py`
- Regenerate: `schemas/portfolio/local-release-readiness.schema.json`
- Regenerate: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**

- Consumes: failed Phase A anchors and unchanged ten-path `PUBLIC_SURFACE_PATHS`.
- Produces: `CommitSha`, `PortfolioCiRunUrl`, closed readiness v1.1, and `$correctiveCommit`.

- [ ] **Step 1: Re-establish Private staging state**

```powershell
git status --short --branch
git rev-parse HEAD
git remote -v
git ls-remote origin refs/heads/main
gh api user --jq .login
gh repo view kuotunyu/model-delivery-control-plane --json visibility,defaultBranchRef,url
gh run view 33311024512 --repo kuotunyu/model-delivery-control-plane --json headSha,status,conclusion,url,workflowName
```

Require clean local HEAD at this plan commit, owner `kuotunyu`, only the exact origin, Private visibility, remote main at `1b44a3e001d6522b6409bae24e07740bf053186d`, and the immutable run at `completed/failure`.

- [ ] **Step 2: Write workflow RED tests**

Update constants in `tests/publication/test_release_workflow.py`:

```python
PORTFOLIO_ACTIONS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "astral-sh/setup-uv": "20cfd1bf945f4377ade1205e4dbc17946fc9a30d",
}
COMPOSE_VERSION = "5.5.0"
COMPOSE_SHA256 = "51e1e61195f3616896265487ed64551095f3bd27ac7fbd5758d3538c3bfa1b19"
COMPOSE_URL = (
    "https://github.com/docker/compose/releases/download/v5.5.0/"
    "docker-compose-windows-x86_64.exe"
)
```

Replace the exact expected-workflow literal so it requires `windows-2025`, `defaults.run.shell: pwsh`, both pre-checkout Git commands, exact action SHAs, exact Compose URL/SHA/version/plugin setup, and all existing full gates. Retain whole-workflow equality. Add negative assertions for `ubuntu-24.04`, Docker login/pull/build/run/up, secrets, write/OIDC permissions, `pytest -k`, and `--ignore`.

- [ ] **Step 3: Run workflow RED**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_release_workflow.py
```

Expected: old Ubuntu/Node20 workflow fails the new contract.

- [ ] **Step 4: Write readiness-v1.1 RED tests**

Require:

```python
assert readiness.schema_version == "mdcp.local-release-readiness.v1.1"
assert readiness.evidence_class == "github_private_staging_corrective_readiness"
assert readiness.portfolio_ci_commit == "1b44a3e001d6522b6409bae24e07740bf053186d"
assert readiness.portfolio_ci_run_url == (
    "https://github.com/kuotunyu/model-delivery-control-plane/"
    "actions/runs/33311024512"
)
assert readiness.portfolio_ci_conclusion == "failure"
assert readiness.claim_execution.push_executed is True
assert readiness.claim_execution.portfolio_ci_executed is True
assert readiness.claim_execution.portfolio_ci_passed is False
```

Mutation tests reject short commit, alternate repository/scheme URL, success conclusion, false push/executed, true passed, affirmative release, unknown field, and noncanonical bytes with `PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID`.

- [ ] **Step 5: Run readiness RED**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py
```

Expected: v1 cannot satisfy v1.1.

- [ ] **Step 6: Implement constrained anchors and v1.1**

Add:

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

Use this exact execution state:

```python
class ClaimExecution(ClosedModel):
    remote_release_executed: Literal[False]
    push_executed: Literal[True]
    portfolio_ci_executed: Literal[True]
    portfolio_ci_passed: Literal[False]
    tag_created: Literal[False]
    production_deployed: Literal[False]
    kubernetes_production_ready: Literal[False]
    h2_executed: Literal[False]
    cv_workload_implemented: Literal[False]
    llm_workload_implemented: Literal[False]
```

Set `schema_version` to `mdcp.local-release-readiness.v1.1`, `evidence_class` to `github_private_staging_corrective_readiness`, `portfolio_ci_commit: CommitSha`, `portfolio_ci_run_url: PortfolioCiRunUrl`, `portfolio_ci_conclusion: Literal["failure"]`, and `claim_ceiling` to `mdcp.private-staging-corrective-claim-ceiling.v1`. Preserve every other field and validator.

- [ ] **Step 7: Implement exact Windows workflow**

```yaml
name: Portfolio CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: portfolio-ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  verify:
    runs-on: windows-2025
    timeout-minutes: 30
    defaults:
      run:
        shell: pwsh
    steps:
      - name: Configure Windows checkout policy
        run: |
          git config --global core.autocrlf true
          git config --global core.fileMode false
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
      - name: Install checksum-pinned Docker Compose config renderer
        run: |
          $pluginDirectory = Join-Path $env:USERPROFILE ".docker\cli-plugins"
          New-Item -ItemType Directory -Force -Path $pluginDirectory | Out-Null
          $composePath = Join-Path $pluginDirectory "docker-compose.exe"
          Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/docker/compose/releases/download/v5.5.0/docker-compose-windows-x86_64.exe" -OutFile $composePath
          $actualSha256 = (Get-FileHash -LiteralPath $composePath -Algorithm SHA256).Hash.ToLowerInvariant()
          if ($actualSha256 -ne "51e1e61195f3616896265487ed64551095f3bd27ac7fbd5758d3538c3bfa1b19") { throw "DOCKER_COMPOSE_SHA256_MISMATCH" }
          if ((docker compose version --short).Trim() -ne "5.5.0") { throw "DOCKER_COMPOSE_VERSION_MISMATCH" }
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

- [ ] **Step 8: Update truthful docs**

In README and both reviewer docs state: Private push executed; Ubuntu run recorded failure; failure is not success/release/portability evidence; Windows corrective awaits verification; every release/tag/package/P2/H2/workload/Kubernetes/production claim remains false. Include `WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY`; add no badge.

- [ ] **Step 9: Regenerate schema and canonical v1.1**

Generate the schema with the required module registration:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.SCHEMA_PATH; target.write_text(json.dumps(module.LocalReleaseReadiness.model_json_schema(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')"
```

Then set the exact failed anchors/state and rebuild the inventory after final public bytes:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.READINESS_PATH; document=json.loads(target.read_text(encoding='utf-8')); document['schema_version']='mdcp.local-release-readiness.v1.1'; document['evidence_class']='github_private_staging_corrective_readiness'; document['portfolio_ci_commit']='1b44a3e001d6522b6409bae24e07740bf053186d'; document['portfolio_ci_run_url']='https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512'; document['portfolio_ci_conclusion']='failure'; document['claim_ceiling']='mdcp.private-staging-corrective-claim-ceiling.v1'; document['claim_execution']['push_executed']=True; document['claim_execution']['portfolio_ci_executed']=True; document['claim_execution']['portfolio_ci_passed']=False; entries=module.build_public_surface_inventory(root); entry_documents=[entry.model_dump(mode='json') for entry in entries]; document['public_surface_entries']=entry_documents; document['public_surface_inventory_sha256']=module.sha256_hex(module.canonicalize_json(entry_documents)); model=module.LocalReleaseReadiness.model_validate(document); target.write_bytes(module.canonicalize_json(model.model_dump(mode='json')))"
```

- [ ] **Step 10: GREEN, full gate, review, commit**

Run the shared gate and frozen identity comparisons. Obtain independent spec/quality review with Critical `0`, Important `0`. Then:

```powershell
git add -- .github/workflows/portfolio-ci.yml README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md evidence/public/portfolio/local-release-readiness.json schemas/portfolio/local-release-readiness.schema.json scripts/verify-public-release.py tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
git diff --cached --check
git commit -m "ci: align portfolio verification with Windows contract"
$correctiveCommit = (git rev-parse HEAD).Trim()
git status --short --branch
```

Require clean state and no push until report/review are complete.

---

### Task 2: Non-force push and prove the corrective Private run

**Files:** no repository file modification or commit.

**Interfaces:**

- Consumes: `$correctiveCommit` from Task 1.
- Produces: `$correctiveRunId` and `$correctiveRunUrl` for Task 3.

- [ ] **Step 1: Verify pre-push state**

Require clean worktree, Private visibility, remote main still at `1b44a3e001d6522b6409bae24e07740bf053186d`, failed run 33311024512 preserved, and local HEAD equal `$correctiveCommit`:

```powershell
git status --short --branch
$correctiveCommit = (git rev-parse HEAD).Trim()
git ls-remote origin refs/heads/main
gh repo view kuotunyu/model-delivery-control-plane --json visibility,defaultBranchRef,url
gh run view 33311024512 --repo kuotunyu/model-delivery-control-plane --json headSha,status,conclusion,url
```

- [ ] **Step 2: Push only reviewed HEAD**

```powershell
git push origin HEAD:main
git ls-remote origin refs/heads/main
```

Require remote main equals `$correctiveCommit`; no force, tag, or alternate ref.

- [ ] **Step 3: Discover and wait for the exact run**

```powershell
$runs = gh run list --repo kuotunyu/model-delivery-control-plane --workflow portfolio-ci.yml --branch main --commit $correctiveCommit --limit 5 --json databaseId,headSha,status,conclusion,url,workflowName | ConvertFrom-Json
$correctiveRun = $runs | Where-Object { $_.headSha -eq $correctiveCommit -and $_.workflowName -eq 'Portfolio CI' } | Select-Object -First 1
if ($null -eq $correctiveRun) { throw 'WINDOWS_CORRECTIVE_RUN_MISSING' }
$correctiveRunId = $correctiveRun.databaseId
gh run watch $correctiveRunId --repo kuotunyu/model-delivery-control-plane --exit-status
```

- [ ] **Step 4: Authenticate success**

```powershell
$run = gh run view $correctiveRunId --repo kuotunyu/model-delivery-control-plane --json headSha,status,conclusion,url,workflowName,jobs | ConvertFrom-Json
if ($run.headSha -ne $correctiveCommit -or $run.status -ne 'completed' -or $run.conclusion -ne 'success') { throw 'WINDOWS_CORRECTIVE_RUN_NOT_SUCCESSFUL' }
$correctiveRunUrl = $run.url
```

Every step, including Compose checksum/version, full suite, and mutation rejection, must succeed. Otherwise keep Private and enter systematic debugging; never enter Task 3.

- [ ] **Step 5: Recheck negative state**

Require Private visibility, zero release-workflow runs, zero GitHub Releases, zero remote/HEAD tags, clean local status, and remote main equal corrective commit. Package API remains deferred.

---

### Task 3: Bind final readiness v2 to the successful corrective run

**Files:**

- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Modify: `scripts/verify-public-release.py`
- Modify: `tests/publication/test_public_release_surface.py`
- Regenerate: `schemas/portfolio/local-release-readiness.schema.json`
- Regenerate: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**

- Consumes: `$correctiveCommit` and `$correctiveRunUrl` observed in Task 2.
- Produces: final closed readiness v2 and `$finalEvidenceCommit`.

- [ ] **Step 1: Recapture observed anchors**

```powershell
$correctiveCommit = (gh run view $correctiveRunId --repo kuotunyu/model-delivery-control-plane --json headSha --jq .headSha).Trim()
$correctiveRunUrl = (gh run view $correctiveRunId --repo kuotunyu/model-delivery-control-plane --json url --jq .url).Trim()
if ($correctiveCommit -notmatch '^[0-9a-f]{40}$') { throw 'CORRECTIVE_COMMIT_INVALID' }
if ($correctiveRunUrl -notmatch '^https://github\.com/kuotunyu/model-delivery-control-plane/actions/runs/[1-9][0-9]*$') { throw 'CORRECTIVE_RUN_URL_INVALID' }
```

Require success, Private visibility, and remote main equal `$correctiveCommit`.

- [ ] **Step 2: Write final-v2 RED tests**

```python
assert readiness.schema_version == "mdcp.local-release-readiness.v2"
assert readiness.evidence_class == "github_portfolio_publication_readiness"
assert readiness.portfolio_ci_commit == corrective_commit
assert readiness.portfolio_ci_run_url == corrective_run_url
assert readiness.portfolio_ci_conclusion == "success"
assert readiness.claim_ceiling == "mdcp.github-portfolio-claim-ceiling.v2"
assert readiness.claim_execution.push_executed is True
assert readiness.claim_execution.portfolio_ci_executed is True
assert readiness.claim_execution.portfolio_ci_passed is True
```

Mutations reject failure conclusion, false push/executed/passed, alternate commit/URL, affirmative release/production/H2/CV/LLM, unknown field, noncanonical bytes, and stale inventory.

- [ ] **Step 3: Run RED**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py
```

Expected: v1.1 failed-state contract cannot satisfy final v2.

- [ ] **Step 4: Implement final v2**

Retain the constrained anchor types. Change `ClaimExecution.portfolio_ci_passed` to `Literal[True]`. Set schema version `mdcp.local-release-readiness.v2`, evidence class `github_portfolio_publication_readiness`, conclusion `Literal["success"]`, and claim ceiling `mdcp.github-portfolio-claim-ceiling.v2`. Preserve all negative and frozen fields.

- [ ] **Step 5: Update final public copy**

Replace “corrective pending” with the observed successful Windows commit/run in the three public docs. Keep failed Ubuntu run as historical context only in `release-evidence.md`. Preserve:

```text
WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY
```

- [ ] **Step 6: Regenerate schema and canonical v2**

Regenerate the schema:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.SCHEMA_PATH; target.write_text(json.dumps(module.LocalReleaseReadiness.model_json_schema(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')"
```

Pass only the observed anchors through temporary process environment variables and generate canonical v2:

```powershell
$env:MDCP_CORRECTIVE_COMMIT = $correctiveCommit
$env:MDCP_CORRECTIVE_RUN_URL = $correctiveRunUrl
uv run --no-sync python -c "import importlib.util,json,os,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.READINESS_PATH; document=json.loads(target.read_text(encoding='utf-8')); document['schema_version']='mdcp.local-release-readiness.v2'; document['evidence_class']='github_portfolio_publication_readiness'; document['portfolio_ci_commit']=os.environ['MDCP_CORRECTIVE_COMMIT']; document['portfolio_ci_run_url']=os.environ['MDCP_CORRECTIVE_RUN_URL']; document['portfolio_ci_conclusion']='success'; document['claim_ceiling']='mdcp.github-portfolio-claim-ceiling.v2'; document['claim_execution']['push_executed']=True; document['claim_execution']['portfolio_ci_executed']=True; document['claim_execution']['portfolio_ci_passed']=True; entries=module.build_public_surface_inventory(root); entry_documents=[entry.model_dump(mode='json') for entry in entries]; document['public_surface_entries']=entry_documents; document['public_surface_inventory_sha256']=module.sha256_hex(module.canonicalize_json(entry_documents)); model=module.LocalReleaseReadiness.model_validate(document); target.write_bytes(module.canonicalize_json(model.model_dump(mode='json')))"
Remove-Item Env:MDCP_CORRECTIVE_COMMIT
Remove-Item Env:MDCP_CORRECTIVE_RUN_URL
```

- [ ] **Step 7: Full gate, review, commit, push**

Run the shared gate and frozen comparisons. Obtain Critical `0`/Important `0` review. Then:

```powershell
git add -- README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md evidence/public/portfolio/local-release-readiness.json schemas/portfolio/local-release-readiness.schema.json scripts/verify-public-release.py tests/publication/test_public_release_surface.py
git diff --cached --check
git commit -m "evidence: record Windows portfolio verification"
$finalEvidenceCommit = (git rev-parse HEAD).Trim()
git push origin HEAD:main
```

- [ ] **Step 8: Require second Windows run success**

Discover/wait for the exact run whose head SHA equals `$finalEvidenceCommit`; require every step and overall conclusion success. Final v2 intentionally binds Task 2's prior successful run, not its own run.

- [ ] **Step 9: Stop at the package authorization boundary**

Require repository still Private, zero release workflow/tag/release state, final remote SHA, clean worktree, and frozen identities. Do not proceed until `read:packages` is separately authorized.

---

### Task 4: Authorized package readback, Public transition, and final audit

**Files:** no repository modification or commit.

**Interfaces:**

- Consumes: final evidence commit and two successful Windows runs.
- Produces: externally verified Public portfolio state.

- [ ] **Step 1: Obtain explicit read-only scope authorization**

Ask the user to authorize only `read:packages`. Do not invoke auth refresh or alter token scopes before approval. After approval:

```powershell
gh auth refresh -h github.com -s read:packages
gh auth status
```

If browser/device confirmation is required, stop for the user. Never request write/delete package scopes.

- [ ] **Step 2: Prove package absence before Public**

```powershell
$pages = gh api 'users/kuotunyu/packages?package_type=container&per_page=100' --paginate --slurp | ConvertFrom-Json
$packages = @($pages | ForEach-Object { $_ })
$matching = @($packages | Where-Object { $_.name -eq 'model-delivery-control-plane' })
if ($matching.Count -ne 0) { throw 'UNEXPECTED_GHCR_PACKAGE_PRESENT' }
```

Also require zero release-workflow runs, tags, and GitHub Releases. Stop if 403 or a matching package appears.

- [ ] **Step 3: Re-run the pre-Public gate**

Require clean local status; remote main equals final evidence commit; both Windows runs completed/success; verifier/demo/fast path pass; release workflow, tags, releases, and matching packages are zero; visibility is Private; frozen identities and H2 sealed/zero state are unchanged.

- [ ] **Step 4: Change only visibility and approved metadata**

```powershell
gh repo edit kuotunyu/model-delivery-control-plane --visibility public --accept-visibility-change-consequences
gh repo edit kuotunyu/model-delivery-control-plane --description "Evidence-gated model delivery reference implementation with content-addressed identity, temporal controls, and fail-closed verification."
gh api --method PUT repos/kuotunyu/model-delivery-control-plane/topics -f 'names[]=mlops' -f 'names[]=model-delivery' -f 'names[]=machine-learning' -f 'names[]=ai-engineering' -f 'names[]=onnx' -f 'names[]=supply-chain-security'
```

- [ ] **Step 5: Authenticate Public state**

```powershell
gh repo view kuotunyu/model-delivery-control-plane --json nameWithOwner,visibility,defaultBranchRef,description,repositoryTopics,url
git ls-remote origin refs/heads/main
$repoResponse = Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/kuotunyu/model-delivery-control-plane'
$readmeResponse = Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/kuotunyu/model-delivery-control-plane/main/README.md'
if ($repoResponse.StatusCode -ne 200 -or $readmeResponse.StatusCode -ne 200) { throw 'ANONYMOUS_PUBLIC_READ_FAILED' }
```

Require Public visibility, main, exact final SHA/description/six topics, and anonymous HTTP 200.

- [ ] **Step 6: Repeat negative and local audit**

Re-run release-workflow, tag, GitHub Release, and package queries. Re-read both Windows run URLs. Run local verifier, demo, fast path, frozen identities, and clean status. Repository bytes did not change, so metadata-only transition does not require another full suite.

- [ ] **Step 7: Report closure**

Report public URL; final SHA; failed Ubuntu run; both successful Windows runs; local test/review evidence; gitleaks zero findings; frozen identities; visibility/default branch/description/topics; negative release/package/P2/H2/model/data/Kubernetes/production state. End with:

```text
PUBLIC_GITHUB_PORTFOLIO_READY / WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS
!= CROSS_PLATFORM_PORTABLE / REMOTE_RELEASED / PRODUCTION_READY
```

## Expected sequence

```text
1b44a3e  Phase A source -> Private Ubuntu run failure (preserved)
5d7611a  corrective design
plan      corrective implementation plan
corrective commit -> local gate/review -> non-force push -> Windows CI success
final v2 commit   -> local gate/review -> non-force push -> Windows CI success
explicit read:packages authorization/readback -> Private to Public -> final audit
```

There is no merge, force-push, tag, GitHub Release, package publication, release-workflow dispatch, Docker container execution, local-main update, or other-repository mutation.
