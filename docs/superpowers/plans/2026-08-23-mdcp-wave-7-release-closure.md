# MDCP Wave 7 Release and Portfolio Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close M7 with reproducible CI/security/publication gates, exact claim traceability, an authorized final OCI/attestation chain, and separately authorized `v0.1.0` tag and GitHub Release.

**Architecture:** Local and GitHub CI run the same locked commands and never infer success from dashboards. Publication verification starts from a clean clone, follows the acyclic descriptor-to-receipt chain, scans tracked content/claims/identity, and produces a release preflight report. External mutations are split into repository/GHCR/attestation, tag, and Release approvals.

**Tech Stack:** GitHub Actions, uv/pytest, Docker BuildKit/GHCR, GitHub artifact attestation, SPDX, PowerShell, RFC 8785 verifier, git, and the Wave 6 reviewer bundle.

## Global Constraints

- Entry requires all Wave 0–6 completion reports and clean commits.
- Actions are pinned to full SHAs; no secret is a Docker build argument or tracked file.
- A clean public clone contains source, docs, synthetic fixtures, and reviewed public aggregate evidence only; no raw UCI, runtime DB, credentials, local paths, or private evidence.
- Public claims remain within spec §2 and use the phrase `atomic control-plane rollback with bounded data-plane convergence`.
- No v0.1 document claims Kubernetes, cloud scale, HA/DR, multi-tenancy, real incident evidence, real production bike service, or paired canary quality.
- External GHCR/attestation execution, tag creation, and GitHub Release publication each require their own owner approval; a prior approval does not imply the next.
- Completion command: `$releaseCommit = (git rev-parse HEAD).Trim(); pwsh ./scripts/release-preflight.ps1 -Version v0.1.0 -ExpectedCommit $releaseCommit` followed by authorized external verification.

---

### Task 7.1: Build the complete local/GitHub CI matrix

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/security.yml`
- Test: `tests/publication/test_ci_workflows.py`
- Modify: `pyproject.toml`
- Modify: `constraints/github-actions.lock`

**Interfaces:**
- Consumes: every wave's locked commands, action SHA lock, Python 3.12, Compose profiles.
- Produces: required jobs `unit-contract`, `property`, `postgres`, `compose`, `security`, `clean-clone`, `reviewer-smoke`; no release mutation.

- [ ] **Step 1: Write failing CI coverage/pinning tests**

```python
def test_ci_jobs_cover_all_test_layers(ci):
    assert set(ci.jobs) >= {"unit-contract", "property", "postgres", "compose",
                            "security", "clean-clone", "reviewer-smoke"}
    assert all(ref.is_full_commit_sha for ref in ci.action_refs)

def test_pull_request_ci_has_no_write_permissions(ci):
    assert ci.permissions == {"contents": "read"}
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/publication/test_ci_workflows.py -q`

Expected: FAIL because CI/security workflows are absent.

- [ ] **Step 3: Implement scoped, cached, locked workflows**

Use full action SHAs from the reviewed lock, `uv sync --frozen`, exact wave completion test groups, ephemeral PostgreSQL, Compose config/integration, secret/payload scans, clean-clone, and a bounded reviewer smoke that does not publish. Upload sanitized reports with retention; never upload runtime DB/raw data/private keys.

```yaml
permissions:
  contents: read
jobs:
  unit-contract:
    permissions: {contents: read}
  property:
    permissions: {contents: read}
  postgres:
    permissions: {contents: read}
  compose:
    permissions: {contents: read}
  security:
    permissions: {contents: read}
  clean-clone:
    permissions: {contents: read}
  reviewer-smoke:
    permissions: {contents: read}
```

- [ ] **Step 4: Verify workflow syntax, commands, and permissions locally**

Run: `uv run pytest tests/publication/test_ci_workflows.py -q; uv run python -m mdcp.verify.publication workflows --root .github/workflows`

Expected: tests pass; verifier prints `WORKFLOWS PASS pinned=true pr_permissions=read release_mutations=0`.

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows/ci.yml .github/workflows/security.yml constraints/github-actions.lock pyproject.toml tests/publication/test_ci_workflows.py
git commit -m "ci: add complete verification matrix"
```

### Task 7.2: Enforce clean-clone, tracked-content, and security boundaries

**Files:**
- Create: `src/mdcp/verify/publication.py`
- Create: `scripts/verify-clean-clone.ps1`
- Test: `tests/security/test_tracked_content.py`
- Test: `tests/security/test_secret_and_payload_leakage.py`
- Test: `tests/publication/test_clean_clone.py`
- Modify: `docs/superpowers/specs/2026-08-23-model-delivery-control-plane-design.md`
- Modify: `.gitignore`
- Modify: `.dockerignore`
- Modify: `docs/threat-model.md`

**Interfaces:**
- Consumes: repository tree and a fresh temporary clone path.
- Produces: `scan_tracked_tree(root: Path) -> PublicationScanResult`, CLI `python -m mdcp.verify.publication scan --root .`, and PowerShell clean-clone gate.

- [ ] **Step 1: Write failing tracked-content tests**

```python
def test_tracked_tree_has_no_private_runtime_material(scan):
    assert scan.credentials == []
    assert scan.raw_uci_files == []
    assert scan.runtime_databases == []
    assert scan.private_keys == []
    assert scan.local_absolute_paths == []

def test_publication_cleanup_cannot_change_normative_spec(current_spec, approved_spec):
    assert current_spec[current_spec.index("## 1. Purpose"):] == approved_spec[
        approved_spec.index("## 1. Purpose"):]
    assert "- Local repository: `C:\\Users\\" not in current_spec
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/security/test_tracked_content.py tests/security/test_secret_and_payload_leakage.py tests/publication/test_clean_clone.py -q`

Expected: FAIL because publication scanner/clean-clone script are absent.

- [ ] **Step 3: Implement explicit allow/deny inventory and disposable clone verification**

Scan git-indexed bytes and rendered docs for credentials/private-key markers, Windows user paths, database formats, raw UCI signatures, request payload/label dumps, oversized artifacts, Kubernetes/cloud artifacts, and unapproved generated files. Remove only the top-level `Local repository` metadata line from the design spec; compare every byte from `## 1. Purpose` onward with approved commit `6bfa2e6781f1f1ba6fbcd13833c5e3b03691f28f` and fail on any normative-body difference. Clean clone uses a verified temporary directory, `uv sync --frozen`, unit/contract tests, Compose config, offline bundle/receipt checks, and never recursively deletes an unresolved path.

```python
def scan_tracked_tree(root: Path) -> PublicationScanResult:
    tracked = git_indexed_files(root)
    findings = tuple(finding for path in tracked for finding in scan_public_file(path))
    return PublicationScanResult(
        credentials=select(findings, FindingKind.CREDENTIAL),
        raw_uci_files=select(findings, FindingKind.RAW_UCI),
        runtime_databases=select(findings, FindingKind.DATABASE),
        private_keys=select(findings, FindingKind.PRIVATE_KEY),
        local_absolute_paths=select(findings, FindingKind.LOCAL_PATH),
    )
```

- [ ] **Step 4: Verify the scanner and clean-clone behavior in disposable test repositories**

Run: `uv run pytest tests/security/test_tracked_content.py tests/security/test_secret_and_payload_leakage.py tests/publication/test_clean_clone.py -q; uv run python -m mdcp.verify.publication scan --root .`

Expected: tests pass; the clean-clone test creates and commits a disposable fixture repository, invokes the PowerShell gate there, and observes `CLEAN-CLONE PASS tracked_private=0 uci=0 credentials=0`; current-tree scan reports the same zero findings. The actual project clean-clone run remains a Wave 7 checkpoint after source commits are complete.

- [ ] **Step 5: Commit**

```powershell
git add .gitignore .dockerignore src/mdcp/verify/publication.py scripts/verify-clean-clone.ps1 docs/threat-model.md docs/superpowers/specs/2026-08-23-model-delivery-control-plane-design.md tests/security tests/publication/test_clean_clone.py
git commit -m "test: enforce public repository boundary"
```

### Task 7.3: Complete portfolio documentation and requirement traceability

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `CITATION.cff`
- Create: `SECURITY.md`
- Create: `docs/architecture.md`
- Create: `docs/evidence-claims.md`
- Create: `docs/traceability/requirements.csv`
- Test: `tests/publication/test_claims.py`
- Test: `tests/publication/test_traceability.py`

**Interfaces:**
- Consumes: approved spec requirements, wave artifacts/commands/digests, three dashboards, reviewer receipts.
- Produces: stable requirement IDs such as `MDCP-S16-R001`, mapping `requirement -> test -> command -> output artifact -> digest -> milestone`, reviewer-facing claims and architecture.

- [ ] **Step 1: Write failing claim/coverage tests**

```python
def test_every_normative_requirement_is_mapped(spec, matrix):
    assert matrix.requirement_ids == spec.normative_requirement_ids
    assert all(row.test and row.command and row.artifact and row.milestone for row in matrix.rows)

def test_prohibited_claims_absent(rendered_docs):
    assert rendered_docs.findings == []
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/publication/test_claims.py tests/publication/test_traceability.py -q`

Expected: FAIL because public docs and traceability matrix do not exist.

- [ ] **Step 3: Write evidence-first documentation**

README leads with model-delivery decision, not model accuracy; shows CPU demo, identity chain, state flow, better-offline-but-rollback result, dashboards, evidence classes, costs/limits, and project differentiation. Architecture names four custom roles and EventIngest as control module. Evidence claims distinguish natural/injected/release-CI/local recomputation and state accepted admin/DBA limitations. Map every MUST/MUST NOT and acceptance bullet to exact tests/artifacts.

```python
@dataclass(frozen=True)
class TraceabilityRow:
    requirement_id: str
    test_nodeid: str
    command: str
    output_artifact: PurePosixPath
    artifact_digest: str
    milestone: Literal["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]
```

- [ ] **Step 4: Verify claims and traceability**

Run: `uv run pytest tests/publication/test_claims.py tests/publication/test_traceability.py -q; uv run python -m mdcp.verify.publication claims --spec docs/superpowers/specs/2026-08-23-model-delivery-control-plane-design.md --docs README.md docs`

Expected: `CLAIMS PASS prohibited=0 unsupported=0 requirements_unmapped=0`; no Kubernetes completion, instantaneous global rollback, production incident, or paired-canary-quality claim appears.

- [ ] **Step 5: Commit**

```powershell
git add README.md LICENSE CITATION.cff SECURITY.md docs/architecture.md docs/evidence-claims.md docs/traceability tests/publication/test_claims.py tests/publication/test_traceability.py
git commit -m "docs: publish evidence backed portfolio story"
```

### Task 7.4: Prepare the final release workflow, notes, and exact-commit preflight

**Files:**
- Create: `.github/workflows/release.yml`
- Create: `scripts/release-preflight.ps1`
- Test: `tests/publication/test_release_preflight.py`
- Test: `tests/publication/test_release_notes.py`
- Test: `tests/publication/test_release_publication.py`
- Create: `docs/releases/v0.1.0.md`

**Interfaces:**
- Consumes: Wave 2 release-CI workflow primitives and recorded fixtures, all M0–M6 reports, approved claims, and the acyclic release identity model.
- Produces: a committed dispatch-only release workflow, local/remote preflight verifier, publication acceptance tests, and immutable release notes. Dynamic OCI and evidence digests live in signed workflow/Release assets, never in the source commit that the image digest identifies.

- [ ] **Step 1: Write failing release-preflight, notes, and publication tests**

```python
def test_preflight_rejects_dirty_or_wrong_identity(preflight):
    assert preflight.run(dirty=True).verdict == "FAIL"
    assert preflight.run(author_email="other@example.com").verdict == "FAIL"

def test_release_workflow_does_not_create_tag_or_release(workflow):
    assert workflow.tag_mutation is False
    assert workflow.github_release_mutation is False

def test_release_notes_do_not_create_an_identity_cycle(notes):
    assert notes.names_asset("release-inventory.json")
    assert notes.names_asset("release-ci-verification.json")
    assert notes.embedded_future_oci_digest is False
    assert notes.claims <= APPROVED_CLAIMS
```

- [ ] **Step 2: Verify red without external mutation**

Run: `uv run pytest tests/publication/test_release_preflight.py tests/publication/test_release_notes.py tests/publication/test_release_publication.py -q; pwsh ./scripts/release-preflight.ps1 -Version v0.1.0 -Mode LocalOnly`

Expected: tests FAIL because preflight, workflow, release notes, and remote verifier are absent; PowerShell exits nonzero because the script is absent.

- [ ] **Step 3: Implement immutable preflight, notes, and dispatch-only workflow**

Require clean tree, exact author/committer, approved spec/status/plan ancestry, all wave reports/digests, test/clean-clone/demo PASS, version `v0.1.0`, and full-SHA actions. The manual `workflow_dispatch` requires `expected_commit` and builds, pushes, attests, scans, and verifies exactly that commit. It emits `release-inventory.json`, `release-ci-verification.json`, `sbom.spdx.json`, final manifest, validation receipt, and evidence bundle as immutable workflow artifacts; it cannot create tags, Releases, or source commits. Release notes describe these exact asset names, CPU reviewer path, evidence classes, claim ceiling, limitations, and cold/warm distinction without embedding a not-yet-computable OCI digest.

```powershell
$sourceCommit = (git rev-parse HEAD).Trim()
if ((git status --short).Length -ne 0) { throw 'dirty worktree' }
if ($ExpectedCommit -ne $sourceCommit) { throw 'source commit mismatch' }
if ($Version -ne 'v0.1.0') { throw 'unsupported release version' }
uv run python -m mdcp.verify.publication preflight --root . --expected-commit $sourceCommit --mode $Mode
```

- [ ] **Step 4: Verify local-only behavior and the recorded remote fixture**

Run:

```powershell
uv run pytest tests/publication/test_release_preflight.py tests/publication/test_release_notes.py tests/publication/test_release_publication.py -q
$recordedInventory = Get-Content -LiteralPath tests/fixtures/supply-chain/recorded-release-ci/release-inventory.json -Raw | ConvertFrom-Json
uv run python -m mdcp.verify.publication release-assets --root tests/fixtures/supply-chain/recorded-release-ci --expected-commit $recordedInventory.source_commit
```

Expected: tests pass, including a disposable clean-Git-repository invocation that prints `PREFLIGHT LOCAL PASS version=v0.1.0 mutations=0`; recorded-fixture verification prints `RELEASE-ASSETS PASS evidence_class=recorded-release-ci` and makes no network request.

- [ ] **Step 5: Commit the complete release source before any final publication**

```powershell
git add .github/workflows/release.yml scripts/release-preflight.ps1 tests/publication/test_release_preflight.py tests/publication/test_release_notes.py tests/publication/test_release_publication.py docs/releases/v0.1.0.md
git commit -m "ci: prepare exact commit release closure"
```

This commit becomes the only permitted `source_commit` for the final OCI chain and `v0.1.0`. Any later source change invalidates the preflight and requires repeating Task 7.5 from a new clean commit.

### Task 7.5: Publish the exact committed release under separate approvals

**Files:**
- Modify: none in the Git worktree; generated evidence remains in GitHub workflow artifacts and GitHub Release assets.
- Test: `tests/publication/test_release_publication.py`

**Interfaces:**
- Consumes: the exact clean Task 7.4 commit, owner authorization to push that exact source commit, separate authorization for final GHCR/attestation, separate tag creation/push authorization, and later separate GitHub Release authorization.
- Produces: digest-qualified final OCI subject and SBOM/provenance/attestation/scan/manifest/receipt/bundle assets, annotated tag `v0.1.0` pointing to the same source commit, GitHub Release, and remotely verifiable publication record.

- [ ] **Step 1: Establish the failing external acceptance check**

Run:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
pwsh ./scripts/release-preflight.ps1 -Version v0.1.0 -ExpectedCommit $releaseCommit -Mode RemoteVerify
```

Expected before publication: nonzero exit with `PUBLICATION INCOMPLETE version=v0.1.0` and an explicit list of absent final workflow artifacts, tag, or Release. Any identity mismatch reports `PUBLICATION FAIL`, not `INCOMPLETE`.

- [ ] **Step 2: Pass local preflight and stop for final GHCR/attestation authorization**

Run:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
git status --short
pwsh ./scripts/release-preflight.ps1 -Version v0.1.0 -ExpectedCommit $releaseCommit -Mode LocalOnly
```

Expected: no `git status` output and `PREFLIGHT LOCAL PASS version=v0.1.0 mutations=0`. Stop for explicit final-source-push authorization. After it is granted, run `git push origin main` and verify `git ls-remote origin refs/heads/main` resolves exactly to `$releaseCommit`. Stop again until the owner separately authorizes final GHCR push and GitHub attestation generation.

- [ ] **Step 3: After that approval, build and verify the final chain without tagging**

Run the reviewed workflow from `main`, passing the exact source commit:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
gh workflow run release.yml --ref main -f expected_commit=$releaseCommit -f version=v0.1.0
$run = gh run list --workflow release.yml --branch main --event workflow_dispatch --limit 20 --json databaseId,headSha,status,conclusion | ConvertFrom-Json | Where-Object headSha -eq $releaseCommit | Select-Object -First 1
if ($null -eq $run) { throw 'no release workflow run for exact source commit' }
gh run watch $run.databaseId --exit-status
pwsh ./scripts/release-preflight.ps1 -Version v0.1.0 -ExpectedCommit $releaseCommit -Mode ChainVerify -RunId $run.databaseId
```

Expected: `RELEASE-CHAIN PASS source=$releaseCommit attestation=verified bundle=verified`, with an OCI subject matching `^ghcr.io/kuotunyu/model-delivery-control-plane@sha256:[0-9a-f]{64}$`. If workflow `headSha`, provenance source, OCI repository, or any digest link differs, stop and do not create the tag.

- [ ] **Step 4: Obtain tag creation/push approval, then separate Release approval**

Run after explicit approval covering tag creation and push:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
git tag -a v0.1.0 $releaseCommit -m "Model Delivery Control Plane v0.1.0"
git rev-list -n 1 v0.1.0
git tag -n1 v0.1.0
git push origin refs/tags/v0.1.0
git ls-remote --tags origin refs/tags/v0.1.0 'refs/tags/v0.1.0^{}'
```

Expected: `git rev-list` prints exactly `$releaseCommit`; `git push` succeeds; `git ls-remote` includes a peeled commit equal to `$releaseCommit`. Stop for separate explicit GitHub Release approval.

Run after GitHub Release approval to download the verified workflow artifacts and publish only those verified files:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
$releaseRun = gh run list --workflow release.yml --branch main --event workflow_dispatch --limit 20 --json databaseId,headSha,conclusion | ConvertFrom-Json | Where-Object { $_.headSha -eq $releaseCommit -and $_.conclusion -eq 'success' } | Select-Object -First 1
if ($null -eq $releaseRun) { throw 'no successful release run for exact source commit' }
$runId = $releaseRun.databaseId
$releaseAssetDir = Join-Path ([System.IO.Path]::GetTempPath()) "mdcp-v0.1.0-$runId-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $releaseAssetDir -ErrorAction Stop | Out-Null
gh run download $runId --name release-chain-v0.1.0 --dir $releaseAssetDir
gh release create v0.1.0 --verify-tag --title "Model Delivery Control Plane v0.1.0" --notes-file docs/releases/v0.1.0.md (Join-Path $releaseAssetDir 'release-inventory.json') (Join-Path $releaseAssetDir 'release-ci-verification.json') (Join-Path $releaseAssetDir 'sbom.spdx.json') (Join-Path $releaseAssetDir 'final-release-manifest.json') (Join-Path $releaseAssetDir 'validation-receipt.json') (Join-Path $releaseAssetDir 'evidence-bundle.tar.zst')
gh release view v0.1.0 --json tagName,isDraft,isPrerelease
```

Expected: `gh release create` prints the public Release URL; `gh release view` returns `{"tagName":"v0.1.0","isDraft":false,"isPrerelease":false}`.

- [ ] **Step 5: Verify green remotely and preserve the clean source identity**

Run:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
pwsh ./scripts/release-preflight.ps1 -Version v0.1.0 -ExpectedCommit $releaseCommit -Mode RemoteVerify
uv run pytest tests/publication/test_release_publication.py -q
git status --short
```

Expected: `PUBLICATION PASS tag=v0.1.0 release=published source=$releaseCommit assets=verified`; tests pass; `git status` prints nothing. Do not create a post-release source commit: doing so would make the tag, OCI provenance, and source tree disagree.

## Wave 7 completion checkpoint

Run:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
uv run pytest -q
pwsh ./scripts/verify-clean-clone.ps1 -Source .
pwsh ./scripts/demo.ps1 -Scenario GoldenRollback -Warm -Verify
pwsh ./scripts/release-preflight.ps1 -Version v0.1.0 -ExpectedCommit $releaseCommit -Mode RemoteVerify
git status --short
```

Expected: all local test layers pass, clean clone and warm demo pass, release inventory follows the same acyclic identity chain, public claims and evidence classes verify, authorized tag/Release point to the exact source, and worktree is clean. Only then declare M7 Portfolio Complete. Kubernetes/k3d reconsideration is a separate v0.2 design process.
