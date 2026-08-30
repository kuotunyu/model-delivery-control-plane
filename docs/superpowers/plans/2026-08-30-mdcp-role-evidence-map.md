# MDCP zh-TW Role-to-Evidence Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a concise zh-TW README map from ML, AI, Computer Vision, LLM, and MLOps-related competencies to concrete repository evidence without expanding the repository's verified claim ceiling.

**Architecture:** One README section provides the human-facing map, one focused publication test freezes its semantic contract, and the existing canonical readiness document rebinds the changed README bytes. Runtime code, the verifier, the nine-path public inventory, schemas, dependencies, and historical identities remain unchanged.

**Tech Stack:** Markdown, Python 3.12, pytest, Pydantic 2, RFC 8785 canonical JSON, Git, PowerShell 7, Ruff, uv.

## Global Constraints

- Execute only in the existing linked worktree `D:\AI-Portfolio\CC_github部隊\model-delivery-control-plane\.worktrees\wave0-foundation-feasibility` on branch `codex/wave0-foundation-feasibility`.
- The approved design is `docs/superpowers/specs/2026-08-30-mdcp-role-evidence-map-design.md`, commit `bdc8ece81b1df31367ddf072679b751ae6f40d53`, SHA-256 `c7ae2d9991500b34ed811482b2f482404e26c5dd15e3cb1a671436c0f849cf92`.
- After this plan commit, the implementation allowlist is exactly three paths:

```text
README.md
evidence/public/portfolio/local-release-readiness.json
tests/publication/test_public_release_surface.py
```

- Modify no schema, verifier, demo, PowerShell wrapper, `.gitattributes`, production source, dependency, workflow, historical evidence, or identity path.
- Keep the nine-path `PUBLIC_SURFACE_PATHS` tuple unchanged and ASCII ordered. Readiness remains outside its own inventory.
- Preserve schema SHA-256 `64b6e3f7ed29b13dce46114345ab9f8c0b176a852fc884139916c7ba0494f202` and `uv.lock` SHA-256 `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`.
- Preserve v0.1 serving identity `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`, v0.2 serving identity `198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea`, source identity `cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b`, worker identity `ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3`, and firewall identity `e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1`.
- Preserve historical receipt SHA-256 `5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63`, historical index SHA-256 `2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205`, H2 status `SEALED_NOT_LOADED`, and loaded rows `0`.
- Keep the README zh-TW-first. Do not add an English resume, application summary, unverifiable performance/scale statement, CV/LLM workload claim, Kubernetes-production claim, or remote-release claim.
- Do not create a remote, use network, install dependencies, push, merge, tag, create a release, execute a workflow, publish a package/image, run H2/data/model work, or touch another repository.
- Use test-driven development for the README contract. On any unexpected failure, invoke systematic-debugging before changing files.
- Before every commit require exact author and committer `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`, a scoped staged diff, and Critical `0`, Important `0` self-review.
- Do not commit an intermediate state where README bytes changed but canonical readiness still describes the old README.
- Generated `.hypothesis`, `.pytest_cache`, `__pycache__`, and bytecode are non-source. Preview and remove only exact generated paths; never let cleanup touch public or historical evidence.

---

### Task 0: Freeze the plan-entry baseline and protected tree

**Files:**
- Read: `docs/superpowers/specs/2026-08-30-mdcp-role-evidence-map-design.md`
- Read: `docs/superpowers/plans/2026-08-30-mdcp-role-evidence-map.md`
- Modify: none

**Interfaces:**
- Consumes: the approved design commit and the commit containing this plan.
- Produces: controller-held `$planEntry`, the exact three-path allowlist, a 266-entry protected Git tree map, and fresh baseline evidence.

- [ ] **Step 1: Verify immutable entry conditions**

```powershell
$expectedBranch = 'codex/wave0-foundation-feasibility'
$approvedDesign = 'bdc8ece81b1df31367ddf072679b751ae6f40d53'
$approvedSpecSha256 = 'c7ae2d9991500b34ed811482b2f482404e26c5dd15e3cb1a671436c0f849cf92'
if ((git branch --show-current) -ne $expectedBranch) { throw 'BRANCH_MISMATCH' }
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) { throw 'WORKTREE_DIRTY' }
if (@(git remote).Count -ne 0) { throw 'REMOTE_DRIFT' }
if (@(git tag --points-at HEAD).Count -ne 0) { throw 'HEAD_TAGGED' }
$planEntry = (git rev-parse HEAD).Trim()
if ((git rev-parse "$planEntry^").Trim() -ne $approvedDesign) { throw 'PLAN_PARENT_MISMATCH' }
$specSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath 'docs/superpowers/specs/2026-08-30-mdcp-role-evidence-map-design.md').Hash.ToLowerInvariant()
if ($specSha256 -ne $approvedSpecSha256) { throw 'SPEC_DIGEST_MISMATCH' }
```

Expected: all checks pass. Keep `$planEntry` unchanged for every later range and protected-tree gate.

- [ ] **Step 2: Freeze the exact implementation allowlist and protected tree**

```powershell
$allowlist = @(
  'README.md',
  'evidence/public/portfolio/local-release-readiness.json',
  'tests/publication/test_public_release_surface.py'
)
if ($allowlist.Count -ne 3) { throw 'ALLOWLIST_COUNT_INVALID' }
if (@($allowlist | Sort-Object -Unique).Count -ne 3) { throw 'ALLOWLIST_DUPLICATE' }
$protected = @{}
foreach ($line in @(git ls-tree -r $planEntry)) {
    $parts = $line -split "`t", 2
    if ($parts[1] -notin $allowlist) { $protected[$parts[1]] = $parts[0] }
}
if ($protected.Count -ne 266) { throw 'PROTECTED_COUNT_MISMATCH' }
```

Expected: exactly three allowlisted paths and 266 protected entries.

- [ ] **Step 3: Record immutable byte baselines**

```powershell
$schemaBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath 'schemas/portfolio/local-release-readiness.schema.json').Hash.ToLowerInvariant()
$lockBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath 'uv.lock').Hash.ToLowerInvariant()
$readinessBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath 'evidence/public/portfolio/local-release-readiness.json').Hash.ToLowerInvariant()
if ($schemaBefore -ne '64b6e3f7ed29b13dce46114345ab9f8c0b176a852fc884139916c7ba0494f202') { throw 'SCHEMA_BASELINE_MISMATCH' }
if ($lockBefore -ne '781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae') { throw 'LOCK_BASELINE_MISMATCH' }
if ($readinessBefore -ne 'cde5f922329daa91041570df2b29b372e63bf6d4843fdd3b2fd0b5b41234d8ec') { throw 'READINESS_BASELINE_MISMATCH' }
```

- [ ] **Step 4: Run the fresh pre-implementation baseline**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run pytest -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
pwsh ./scripts/reviewer-fast-path.ps1
uv run pytest -q
uv run ruff check scripts tests/publication
uv run ruff format --check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
```

Expected: the known starting shape is publication/release `59 passed`, identity/runtime/security `449 passed, 2 skipped`, fast path `277 passed`, and full suite `1598 passed, 7 skipped`; record fresh counts and durations instead of assuming the known values.

- [ ] **Step 5: Remove only the generated Hypothesis cache and restore clean state**

```powershell
$dirty = @(git status --porcelain=v1 --untracked-files=all)
$outsideCache = @($dirty | Where-Object { $_ -notlike '?? .hypothesis/*' })
if ($outsideCache.Count -ne 0) { throw "UNEXPECTED_BASELINE_DIRTY: $($outsideCache -join '; ')" }
if (Test-Path -LiteralPath '.hypothesis') {
    $resolved = (Resolve-Path -LiteralPath '.hypothesis').Path
    $root = (Resolve-Path -LiteralPath '.').Path
    $item = Get-Item -LiteralPath $resolved -Force
    if (-not $resolved.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'CACHE_OUTSIDE_REPOSITORY' }
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'CACHE_REPARSE_POINT' }
    git clean -fd -- .hypothesis
}
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) { throw 'BASELINE_NOT_CLEAN' }
```

Expected: only an exact generated `.hypothesis` tree may be removed; worktree returns clean.

---

### Task 1: Add and evidence-bind the role-to-evidence map

**Files:**
- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `README.md`
- Modify: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**
- Consumes: the existing README hierarchy, Markdown link verifier, claim scanner, `PUBLIC_SURFACE_PATHS`, and canonical readiness model.
- Produces: one zh-TW README section with four role families, ten distinct tracked file targets across eleven link occurrences, four explicit claim boundaries, and canonical readiness bound to the new README bytes.

- [ ] **Step 1: Write the failing semantic README contract test**

Add this focused test immediately after `test_readme_heading_order_and_reviewer_setup_are_stable` in `tests/publication/test_public_release_surface.py`:

```python
def test_readme_maps_target_roles_to_concrete_evidence_without_expanding_claims() -> None:
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    heading = "## 對應 ML／AI／CV／LLM 職務能力"

    assert readme.index("## 目前完成度") < readme.index(heading)
    assert readme.index(heading) < readme.index("## 實際 implemented verification path")
    for role in (
        "ML Engineer",
        "AI Engineer",
        "Computer Vision / LLM Engineer",
        "MLOps / reliability / security",
    ):
        assert role in readme
    for target in (
        "src/mdcp/contracts/workload.py",
        "src/mdcp/contracts/serving_identity_v2.py",
        "tests/contract/workload/test_serving_identity_v2.py",
        "src/mdcp/validator/service.py",
        "src/mdcp/verify/bundle.py",
        "evidence/public/portfolio/local-release-readiness.json",
        "docs/reviewer/release-evidence.md",
        "src/mdcp/temporal/formal_worker.py",
        "src/mdcp/temporal/firewall.py",
        "src/mdcp/temporal/runtime_guards.py",
    ):
        assert f"]({target})" in readme
    for boundary in (
        "已實作的具體 workload 是 temporal regression",
        "local verification 不等於 remote release 或 production evidence",
        "不宣稱已實作 CV 或 LLM workload",
        "control/router/canary/rollback/recovery 仍是 Designed only",
    ):
        assert boundary in readme
```

- [ ] **Step 2: Run the new test and prove RED**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py::test_readme_maps_target_roles_to_concrete_evidence_without_expanding_claims
```

Expected: FAIL at `readme.index(heading)` because the approved heading is absent. If it fails for collection, encoding, or an unrelated assertion, stop and debug before editing README.

- [ ] **Step 3: Add the minimal README section**

Insert this exact block after the current `## 目前完成度` table and before `## 實際 implemented verification path`:

```markdown
## 對應 ML／AI／CV／LLM 職務能力

以下對照的是這個 repository 可直接驗證的 engineering evidence；CV／LLM 欄位表示
delivery-control patterns 的可轉用性，不是已完成對應 workload。

| 目標職務／能力 | 可直接檢查的 evidence | 誠實邊界 |
|---|---|---|
| ML Engineer | [workload contract](src/mdcp/contracts/workload.py)、[v2 serving identity](src/mdcp/contracts/serving_identity_v2.py)、[contract tests](tests/contract/workload/test_serving_identity_v2.py) | 已實作的具體 workload 是 temporal regression |
| AI Engineer | [offline validator](src/mdcp/validator/service.py)、[bundle verification](src/mdcp/verify/bundle.py)、[local readiness](evidence/public/portfolio/local-release-readiness.json) | local verification 不等於 remote release 或 production evidence |
| Computer Vision / LLM Engineer | [content-addressed serving identity](src/mdcp/contracts/serving_identity_v2.py)、[release evidence taxonomy](docs/reviewer/release-evidence.md) | engineering pattern 可轉用；不宣稱已實作 CV 或 LLM workload |
| MLOps / reliability / security | [dedicated formal worker](src/mdcp/temporal/formal_worker.py)、[static firewall](src/mdcp/temporal/firewall.py)、[runtime guards](src/mdcp/temporal/runtime_guards.py) | control/router/canary/rollback/recovery 仍是 Designed only |
```

Do not change any other README section, command, timing statement, historical measurement, or claim ceiling.

- [ ] **Step 4: Run the focused test and prove GREEN**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py::test_readme_maps_target_roles_to_concrete_evidence_without_expanding_claims
```

Expected: `1 passed`.

- [ ] **Step 5: Prove stale readiness fails closed before regeneration**

```powershell
uv run --no-sync python scripts/verify-public-release.py --repository-root .
if ($LASTEXITCODE -eq 0) { throw 'STALE_READINESS_UNEXPECTED_PASS' }
```

Expected terminal and exit code are exactly:

```text
PUBLIC_RELEASE_SLICE_FAIL reason_code=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH
exit 1
```

- [ ] **Step 6: Generate and apply the exact canonical readiness delta**

Print canonical bytes from the real verifier model and current nine public files:

```powershell
uv run python -c "import importlib.util,json,sys; from pathlib import Path; p=Path('scripts/verify-public-release.py'); s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); d=json.loads(Path(m.READINESS_PATH).read_text(encoding='utf-8')); e=m.build_public_surface_inventory(Path('.')); ed=[x.model_dump(mode='json') for x in e]; d['public_surface_entries']=ed; d['public_surface_inventory_sha256']=m.sha256_hex(m.canonicalize_json(ed)); model=m.LocalReleaseReadiness.model_validate(d); raw=m.canonicalize_json(model.model_dump(mode='json')); print(raw.decode('utf-8')); print('READINESS_SHA256=' + m.sha256_hex(raw), file=sys.stderr)"
```

Use `apply_patch` to replace the single JSON line in `evidence/public/portfolio/local-release-readiness.json` with exact stdout. `apply_patch` may add one final LF that canonical bytes do not contain; if and only if independent comparison shows the sole extra byte is final `0x0a`, remove exactly that byte with:

```powershell
$path = 'evidence/public/portfolio/local-release-readiness.json'
$raw = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $path))
if ($raw.Length -eq 0 -or $raw[-1] -ne 10) { throw 'NO_SINGLE_FINAL_LF_TO_REMOVE' }
[IO.File]::WriteAllBytes((Resolve-Path -LiteralPath $path), $raw[0..($raw.Length - 2)])
```

This `.NET` call is permitted only as a mechanical no-final-LF correction after the JSON content was changed through `apply_patch`; it must not alter any other byte or file.

- [ ] **Step 7: Independently prove canonical equality and exact evidence scope**

```powershell
uv run python -c "import importlib.util,json,sys; from pathlib import Path; p=Path('scripts/verify-public-release.py'); s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); d=json.loads(Path(m.READINESS_PATH).read_text(encoding='utf-8')); e=m.build_public_surface_inventory(Path('.')); ed=[x.model_dump(mode='json') for x in e]; d['public_surface_entries']=ed; d['public_surface_inventory_sha256']=m.sha256_hex(m.canonicalize_json(ed)); expected=m.canonicalize_json(m.LocalReleaseReadiness.model_validate(d).model_dump(mode='json')); actual=Path(m.READINESS_PATH).read_bytes(); assert actual == expected; print('READINESS_CANONICAL_MATCH'); print('READINESS_SHA256=' + m.sha256_hex(actual)); print('INVENTORY_SHA256=' + d['public_surface_inventory_sha256'])"
uv run python -c "import json,subprocess; from pathlib import Path; entry='$planEntry'; path='evidence/public/portfolio/local-release-readiness.json'; before=json.loads(subprocess.run(['git','show',f'{entry}:{path}'],check=True,capture_output=True).stdout); after=json.loads(Path(path).read_bytes()); before_entries={x['logical_path']:x for x in before['public_surface_entries']}; after_entries={x['logical_path']:x for x in after['public_surface_entries']}; changed={p for p in before_entries if before_entries[p] != after_entries[p]}; assert changed == {'README.md'}, changed; differing={k for k in before if before[k] != after[k]}; assert differing == {'public_surface_entries','public_surface_inventory_sha256'}, differing; print('READINESS_DELTA_SCOPE_PASS')"
```

Expected: `READINESS_CANONICAL_MATCH` and `READINESS_DELTA_SCOPE_PASS`. Record the new readiness and inventory SHA-256 values.

- [ ] **Step 8: Run focused, entrypoint, static, identity, and full gates**

```powershell
uv run pytest -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
$demoElapsed = Measure-Command {
    uv run --no-sync python scripts/reviewer-demo.py --repository-root .
    if ($LASTEXITCODE -ne 0) { throw 'REVIEWER_DEMO_FAILED' }
}
if ($demoElapsed.TotalSeconds -gt 120) { throw 'DEMO_BUDGET_EXCEEDED' }
pwsh ./scripts/reviewer-fast-path.ps1
uv run pytest -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run ruff check scripts tests/publication
uv run ruff format --check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
uv run pytest -q
```

Expected: focused and full suites pass; verifier prints `PUBLIC_RELEASE_SLICE_PASS`; demo prints its exact four lines in at most 120 seconds; fast path prints its exact final PASS; all frozen-identity tests and static gates pass.

- [ ] **Step 9: Remove generated cache, review the exact atomic diff, and commit**

Before staging, preview and remove only the exact generated Hypothesis cache:

```powershell
$dirty = @(git status --porcelain=v1 --untracked-files=all)
$expectedModified = @(' M README.md', ' M evidence/public/portfolio/local-release-readiness.json', ' M tests/publication/test_public_release_surface.py')
$unexpected = @($dirty | Where-Object { $_ -notin $expectedModified -and $_ -notlike '?? .hypothesis/*' })
if ($unexpected.Count -ne 0) { throw "UNEXPECTED_IMPLEMENTATION_DIRTY: $($unexpected -join '; ')" }
if (Test-Path -LiteralPath '.hypothesis') {
    $resolved = (Resolve-Path -LiteralPath '.hypothesis').Path
    $root = (Resolve-Path -LiteralPath '.').Path
    $item = Get-Item -LiteralPath $resolved -Force
    if (-not $resolved.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'CACHE_OUTSIDE_REPOSITORY' }
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'CACHE_REPARSE_POINT' }
    git clean -fd -- .hypothesis
}
```

Require exactly these three changed paths:

```text
README.md
evidence/public/portfolio/local-release-readiness.json
tests/publication/test_public_release_surface.py
```

Review heading placement, all ten distinct targets across eleven link occurrences, the four boundaries, canonical no-final-LF readiness, the unchanged schema/public-path tuple, and the absence of English resume or expanded claims. Require self-review Critical `0`, Important `0`. Then:

```powershell
git add README.md evidence/public/portfolio/local-release-readiness.json tests/publication/test_public_release_surface.py
if (@(git diff --cached --name-only).Count -ne 3) { throw 'STAGED_SCOPE_MISMATCH' }
git diff --cached --check
git commit -m "docs: map role skills to evidence"
```

Verify exact author/committer identity, one parent equal to `$planEntry`, and a clean worktree.

- [ ] **Step 10: Obtain fresh task review and close findings**

Invoke `requesting-code-review` with the approved spec, this task, the implementation report, and the exact `$planEntry..HEAD` diff. The reviewer must inspect semantic test strength, recruiter scanability, link validity, claim truthfulness, canonical readiness scope, allowlist preservation, and forbidden-action absence.

For each Critical/Important finding, invoke `receiving-code-review` and `systematic-debugging`, reproduce the issue with a focused RED test, modify only the exact three-path allowlist, regenerate readiness if README bytes change, rerun Steps 7–9, commit one focused corrective, and obtain a scoped re-review. Stop for explicit authorization if any fix needs another path.

Acceptance is exactly:

```text
Critical: 0
Important: 0
```

---

### Task 2: Run final whole-range verification and local-only closure

**Files:**
- Modify: none unless a verified Critical/Important finding requires an in-allowlist corrective

**Interfaces:**
- Consumes: every commit after `$planEntry`, the Task 0 protected map, and Task 1 review verdict.
- Produces: a clean local branch with fresh dynamic/static evidence, preserved identities, Critical `0`, Important `0`, and explicit non-actions.

- [ ] **Step 1: Verify the exact range, protected tree, and clean state**

```powershell
$changed = @(git diff --name-only "$planEntry..HEAD")
$outside = @($changed | Where-Object { $_ -notin $allowlist })
if ($outside.Count -ne 0) { throw 'IMPLEMENTATION_ALLOWLIST_DRIFT' }
foreach ($entry in $protected.GetEnumerator()) {
    $line = git ls-tree HEAD -- $entry.Key
    $metadata = if ($line) { ($line -split "`t", 2)[0] } else { '<missing>' }
    if ($metadata -ne $entry.Value) { throw "PROTECTED_TREE_DRIFT: $($entry.Key)" }
}
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) { throw 'WORKTREE_DIRTY' }
```

Expected: changed paths are a subset of the exact three, outside count `0`, protected drift `0`, worktree clean.

- [ ] **Step 2: Run final reviewer entrypoints and dynamic suites**

```powershell
uv run --no-sync python scripts/verify-public-release.py --repository-root .
$demoElapsed = Measure-Command {
    uv run --no-sync python scripts/reviewer-demo.py --repository-root .
    if ($LASTEXITCODE -ne 0) { throw 'REVIEWER_DEMO_FAILED' }
}
if ($demoElapsed.TotalSeconds -gt 120) { throw 'DEMO_BUDGET_EXCEEDED' }
$fastElapsed = Measure-Command {
    pwsh ./scripts/reviewer-fast-path.ps1
    if ($LASTEXITCODE -ne 0) { throw 'FAST_PATH_FAILED' }
}
uv run pytest -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run pytest -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run pytest -q
```

Record exact counts, skips, demo duration, fast-path duration, and full-suite duration. Do not replace the historical `1546 passed, 7 skipped` value inside readiness.

- [ ] **Step 3: Remove only the final generated Hypothesis cache**

```powershell
$dirty = @(git status --porcelain=v1 --untracked-files=all)
$outsideCache = @($dirty | Where-Object { $_ -notlike '?? .hypothesis/*' })
if ($outsideCache.Count -ne 0) { throw "UNEXPECTED_FINAL_DIRTY: $($outsideCache -join '; ')" }
if (Test-Path -LiteralPath '.hypothesis') {
    $resolved = (Resolve-Path -LiteralPath '.hypothesis').Path
    $root = (Resolve-Path -LiteralPath '.').Path
    $item = Get-Item -LiteralPath $resolved -Force
    if (-not $resolved.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'CACHE_OUTSIDE_REPOSITORY' }
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'CACHE_REPARSE_POINT' }
    git clean -fd -- .hypothesis
}
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) { throw 'FINAL_WORKTREE_NOT_CLEAN' }
```

- [ ] **Step 4: Run final static, schema, evidence, identity, and history gates**

```powershell
uv run ruff check scripts tests/publication
uv run ruff format --check scripts/reviewer-demo.py scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv lock --check
git diff --check
if ((Get-FileHash -Algorithm SHA256 -LiteralPath 'schemas/portfolio/local-release-readiness.schema.json').Hash.ToLowerInvariant() -ne $schemaBefore) { throw 'SCHEMA_DRIFT' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath 'uv.lock').Hash.ToLowerInvariant() -ne $lockBefore) { throw 'LOCK_DRIFT' }
$commits = @(git log --reverse --format='%H|%P|%an <%ae>|%cn <%ce>|%s' "$planEntry..HEAD")
$identity = 'kuotunyu <61350295+kuotunyu@users.noreply.github.com>'
foreach ($line in $commits) {
    $parts = $line -split '\|', 5
    if (($parts[1] -split ' ', [StringSplitOptions]::RemoveEmptyEntries).Count -ne 1) { throw 'NON_LINEAR_HISTORY' }
    if ($parts[2] -ne $identity -or $parts[3] -ne $identity) { throw 'COMMIT_IDENTITY_DRIFT' }
}
if (@(git remote).Count -ne 0) { throw 'REMOTE_DRIFT' }
if (@(git tag --points-at HEAD).Count -ne 0) { throw 'HEAD_TAGGED' }
```

Then use the real verifier model and production inventory functions to require:

```text
checked schema == LocalReleaseReadiness.model_json_schema()
public_evidence_violations(readiness.model_dump(mode="json")) == ()
readiness.public_surface_entries == build_public_surface_inventory(repository_root)
readiness.public_surface_inventory_sha256 == SHA-256(canonical inventory entries)
readiness.claim_execution.remote_release_executed == false
readiness.claim_execution.h2_executed == false
H2 == SEALED_NOT_LOADED / 0 rows
v0.1 == d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209
v0.2 == 198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea
source == cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b
worker == ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3
firewall == e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1
receipt == 5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63
index == 2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205
```

- [ ] **Step 5: Obtain independent commit and aggregate review**

Invoke `requesting-code-review` on each new commit and the whole `$planEntry..HEAD` range. The reviewer must explicitly inspect:

```text
role map appears before the detailed verification path
all four role families are present and recruiter-scannable
all ten distinct evidence targets across eleven link occurrences resolve to concrete tracked regular files
semantic test fails when the role map or a boundary disappears
temporal-regression implementation is not overstated
CV/LLM transferability is not presented as workload implementation
local verification is not presented as remote or production evidence
designed-only control-plane components remain designed-only
canonical readiness changes only for README bytes and derived inventory digest
schema, public-path tuple, protected tree, and frozen identities remain unchanged
absence of remote, network, dependency, H2, data, model, workflow, package, push, merge, tag, or release action
```

Acceptance is exactly Critical `0`, Important `0`. Minor findings may be recorded as parked only when they do not weaken correctness, evidence, safety, or the recruiter claim boundary.

- [ ] **Step 6: Handle final findings without widening scope**

For any Critical/Important finding, invoke `receiving-code-review` and `systematic-debugging`, add or refine a focused RED regression, correct only an allowlisted path, regenerate readiness whenever README bytes change, rerun Tasks 2.1–2.5, and create one focused corrective commit only after every gate passes. If correction needs another path, stop and request explicit new scope.

- [ ] **Step 7: Record the local-only stopping boundary**

Report:

```text
new commit SHA and subject
exact changed paths
new README SHA-256 and byte size
new readiness and public-inventory SHA-256 values
unchanged schema and eight frozen identities
focused/full test counts, skips, and durations
demo and fast-path durations
review Critical/Important/Minor counts
clean branch and HEAD
remotes == 0
HEAD tags == 0
REMOTE_RELEASE_NOT_EXECUTED
H2_SEALED_NOT_LOADED
CV_LLM_WORKLOAD_NOT_IMPLEMENTED
```

Keep branch `codex/wave0-foundation-feasibility` and its linked worktree local. Do not push, merge, tag, release, execute workflows, run H2/data/models, or touch another repository.
