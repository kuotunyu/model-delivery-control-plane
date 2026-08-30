# MDCP Public-State Consistency Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every recruiter-facing document truthfully describe the repository's current Public visibility while preserving Private-staging history and all existing negative claim boundaries.

**Architecture:** Update only the three public documents and their exact publication contract, then regenerate the non-recursive canonical public-surface inventory in local readiness evidence. Preserve the offline verifier, closed schema, workflow, production code, historical CI anchors, frozen identities, and release boundary; validate locally before one non-force push and one exact Windows Portfolio CI readback.

**Tech Stack:** Markdown, Python 3.12, Pydantic v2, RFC 8785 canonical JSON, pytest, Ruff, PowerShell 7, Git, GitHub CLI, GitHub Actions.

## Global Constraints

- Work only in `D:\AI-Portfolio\CC_github部隊\model-delivery-control-plane\.worktrees\wave0-foundation-feasibility` on `codex/wave0-foundation-feasibility`.
- Base repository state is Public `main` at `6588d4e1c0b79b9120f7e43f50bb45a3b6a8ede2`; the design commits are local descendants and must remain linear.
- Implementation may modify only `README.md`, `docs/reviewer/quickstart.md`, `docs/reviewer/release-evidence.md`, `tests/publication/test_public_release_surface.py`, and `evidence/public/portfolio/local-release-readiness.json`.
- This plan and `docs/superpowers/specs/2026-08-31-mdcp-public-state-consistency-corrective-design.md` are process paths, not implementation paths.
- Do not modify `.github/workflows/portfolio-ci.yml`, `.gitattributes`, schemas, verifier/demo/fast-path scripts, `src/mdcp/**`, `uv.lock`, frozen evidence, model/data fixtures, or release workflow.
- Preserve the historical Ubuntu failure `33311024512`, Windows mixed-EOL failure `33316653641`, successful Windows run `33322212462`, and successful final-readiness run `33326076709`.
- Preserve readiness schema version `mdcp.local-release-readiness.v2`, evidence class `github_portfolio_publication_readiness`, Portfolio CI anchor commit/run `8bc91a548846af0b1f1be1fc9ae6fbb80b7f63f1` / `33322212462`, and historical `technical_closure_verification` values `1625 passed, 7 skipped`.
- Preserve v1 `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`, v2 `198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea`, source `cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b`, worker `ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3`, and `uv.lock` `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`.
- H2 remains `SEALED_NOT_LOADED` with loaded rows `0`; P2/H2/model/data execution remains forbidden.
- Never force-push, merge, tag, create a GitHub Release, publish a package, dispatch `release-ci.yml`, run a release workflow, or touch another repository.
- Use TDD, systematic debugging for any failure, exact-path staging, independent review, Critical `0`/Important `0`, and one non-force push only after all local gates pass.
- Treat `.hypothesis/`, `__pycache__`, pytest caches, and `.superpowers/sdd/**` as non-source; never stage them.

---

### Task 1: Encode and implement truthful Public-state copy

**Files:**

- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Modify: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**

- Consumes: existing `PUBLIC_SURFACE_PATHS`, `build_public_surface_inventory()`, `LocalReleaseReadiness`, and the three historical run URLs.
- Produces: exact present-state copy `repository is Public; portfolio_ci_passed: true`, preserved Private-staging history, and canonical readiness bytes matching the final public-surface inventory.

- [ ] **Step 1: Write the failing Public-state contract**

In `test_evidence_taxonomy_and_license_qualifiers_are_explicit`, replace the evidence class string `Private Windows-native Portfolio CI evidence` with `Windows-native Portfolio CI evidence`.

Replace `test_final_readiness_docs_bind_success_and_preserve_failed_history` with:

```python
def test_final_readiness_docs_bind_public_state_and_preserve_failed_history() -> None:
    ubuntu = "https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512"
    windows = "https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33316653641"
    success = "https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33322212462"
    for logical_path in (
        "README.md",
        "docs/reviewer/quickstart.md",
        "docs/reviewer/release-evidence.md",
    ):
        text = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
        assert success in text
        assert "repository is Public; portfolio_ci_passed: true" in text
        assert "repository remains Private" not in text
        assert "portfolio_ci_passed: true" in text
        assert "WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE" in text
    for logical_path in ("README.md", "docs/reviewer/quickstart.md"):
        text = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
        assert ubuntu not in text
        assert windows not in text
    evidence_guide = (REPOSITORY_ROOT / "docs/reviewer/release-evidence.md").read_text(
        encoding="utf-8"
    )
    assert ubuntu in evidence_guide
    assert windows in evidence_guide
    assert "during Private staging" in evidence_guide
```

- [ ] **Step 2: Run the exact RED tests**

Run:

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py::test_evidence_taxonomy_and_license_qualifiers_are_explicit tests/publication/test_public_release_surface.py::test_final_readiness_docs_bind_public_state_and_preserve_failed_history
```

Expected: both tests fail because the current documents still use the old present-tense Private copy and heading.

- [ ] **Step 3: Apply the minimal document copy**

Use these exact current-state lines in all three documents:

```text
repository is Public; portfolio_ci_passed: true
The mixed-EOL corrective passed Windows-native remote Portfolio CI during Private staging.
WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY
```

In `README.md`:

- change the Portfolio CI table status to `Public；Windows-native remote gate 已通過；evidence recorded during Private staging`;
- replace both `repository remains Private` current-state sentences;
- change the workflow-link qualifier to `repository is Public；Windows-native corrective run 已通過`.

In `docs/reviewer/quickstart.md`:

- replace the current-state sentence and mixed-EOL sentence with the exact lines above;
- rename the link label to `Windows-native Portfolio CI`.

In `docs/reviewer/release-evidence.md`:

- rename section 4 to `### 4. Windows-native Portfolio CI evidence`;
- state that the recorded runs were executed `during Private staging` while the repository's current state is Public;
- replace the current-state sentence with the exact Public line;
- rename the machine-verifiable link label to `Windows-native Portfolio CI`.

Do not remove or alter any historical run URL, commit SHA, negative claim, or H2 statement.

- [ ] **Step 4: Run the RED tests again for GREEN**

Run the exact command from Step 2.

Expected: `2 passed`.

- [ ] **Step 5: Regenerate the non-recursive canonical readiness inventory**

Run:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.READINESS_PATH; document=json.loads(target.read_text(encoding='utf-8')); entries=module.build_public_surface_inventory(root); entry_documents=[entry.model_dump(mode='json') for entry in entries]; document['public_surface_entries']=entry_documents; document['public_surface_inventory_sha256']=module.sha256_hex(module.canonicalize_json(entry_documents)); model=module.LocalReleaseReadiness.model_validate(document); target.write_bytes(module.canonicalize_json(model.model_dump(mode='json')))"
```

Then assert that `technical_closure_verification` is still exactly `1625/7/0/0/0` and that the historical Portfolio CI anchor is unchanged:

```powershell
uv run --no-sync python -c "import json,pathlib; d=json.loads(pathlib.Path('evidence/public/portfolio/local-release-readiness.json').read_text()); assert d['technical_closure_verification']=={'full_suite_passed':1625,'full_suite_skipped':7,'review_critical':0,'review_important':0,'review_minor':0}; assert d['portfolio_ci_commit']=='8bc91a548846af0b1f1be1fc9ae6fbb80b7f63f1'; assert d['portfolio_ci_run_url'].endswith('/33322212462'); print('READINESS_HISTORY_PRESERVED')"
```

- [ ] **Step 6: Run the complete publication gate**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reviewer-fast-path.ps1
```

Expected: publication/workflow tests pass; verifier prints `PUBLIC_RELEASE_SLICE_PASS`; demo prints `MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0`; fast path prints `PUBLIC_RELEASE_FAST_PATH_PASS evidence_class=local_portfolio mutations=0`.

- [ ] **Step 7: Audit paths and commit the implementation**

```powershell
$allowed = @(
  'README.md',
  'docs/reviewer/quickstart.md',
  'docs/reviewer/release-evidence.md',
  'tests/publication/test_public_release_surface.py',
  'evidence/public/portfolio/local-release-readiness.json'
)
$changed = @(git diff --name-only)
if (@(Compare-Object $allowed $changed).Count -ne 0) { throw 'IMPLEMENTATION_PATH_SET_INVALID' }
git diff --check
git add -- README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md tests/publication/test_public_release_surface.py evidence/public/portfolio/local-release-readiness.json
git diff --cached --check
git commit -m "docs: align portfolio copy with Public state"
```

---

### Task 2: Prove the complete local contract and review the change

**Files:**

- Verify only: all repository paths
- Correct only if required: the five Task 1 implementation paths

**Interfaces:**

- Consumes: committed Public-state copy and regenerated readiness bytes.
- Produces: full local verification evidence, exact frozen anchors, and an independent review with Critical `0` and Important `0`.

- [ ] **Step 1: Run static and formatting checks**

```powershell
uv lock --check
uv run --no-sync ruff check src/mdcp tests scripts
uv run --no-sync ruff format --check tests/publication/test_public_release_surface.py
git diff origin/main --check
```

- [ ] **Step 2: Run focused frozen/security tests**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
```

- [ ] **Step 3: Run the complete test suite**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q
```

Record the fresh passed/skipped counts in the ignored SDD ledger and review package. Do not write them into the closed historical readiness field.

- [ ] **Step 4: Recompute frozen anchors and H2 state**

```powershell
uv run --no-sync python -c "import hashlib; from pathlib import Path; from mdcp.contracts.release import serving_inventory_digest, serving_inventory_from_root; from mdcp.contracts.serving_identity_v2 import V2_SERVING_PATHS, build_v2_serving_inventory; from mdcp.temporal.runtime_guards import _worker_source_inventory, _formal_worker_source_inventory; from mdcp.temporal.evidence import HistoricalLedger; root=Path.cwd(); ledger=HistoricalLedger.frozen_v02(); print('V1='+serving_inventory_digest(serving_inventory_from_root(root))); print('V2='+build_v2_serving_inventory(root,V2_SERVING_PATHS).inventory_sha256); print('SOURCE='+str(_worker_source_inventory(root))); print('WORKER='+str(_formal_worker_source_inventory(root))); print('UV_LOCK='+hashlib.sha256((root/'uv.lock').read_bytes()).hexdigest()); print('H2_STATUS='+ledger.h2_status); print('H2_LOADED_ROWS='+str(ledger.h2_loaded_rows))"
```

Require the exact values in Global Constraints.

- [ ] **Step 5: Obtain independent spec and quality review**

Review `origin/main..HEAD` against the design and this plan. Require:

```text
Critical: 0
Important: 0
```

Review must explicitly check present-state versus historical Private wording, unchanged negative claims, exact implementation paths, non-recursive evidence regeneration, unchanged verifier/schema/workflow/production bytes, and absence of unrelated changes.

- [ ] **Step 6: Apply review corrections only if required**

For any Critical or Important finding, use systematic debugging and TDD within the exact five-path implementation allowlist. Re-run Tasks 1 Step 6 and Task 2 Steps 1–4, obtain another review, and create a separate corrective commit. Stop after five review rounds rather than broadening scope.

- [ ] **Step 7: Build the pre-push checkpoint**

```powershell
git status --short
git log --oneline origin/main..HEAD
git diff --stat origin/main..HEAD
git diff --name-only origin/main..HEAD
```

Require a clean tracked worktree. The only paths beyond the five implementation paths must be the design and plan documents. Verify repository Public metadata, anonymous HTTP 200, both prior successful Windows runs, and zero release-ci runs/tags/GitHub Releases/exact matching package before push.

---

### Task 3: Push once, authenticate the exact run, and close

**Files:** no repository modification or commit.

**Interfaces:**

- Consumes: clean reviewed local HEAD and authenticated pre-push negative state.
- Produces: one non-force push, one exact completed/success Windows Portfolio CI run, and a final Public portfolio audit.

- [ ] **Step 1: Push the reviewed linear history once**

```powershell
git push origin codex/wave0-foundation-feasibility:main
```

No force option is allowed. Stop if the remote is not a fast-forward of the verified base.

- [ ] **Step 2: Identify the exact Portfolio CI run**

Read the pushed HEAD, then query Portfolio CI runs until exactly one run for that SHA appears. It must have workflow name `Portfolio CI`, event `push`, and eventually status `completed` with conclusion `success`. Use condition-based polling; do not dispatch or rerun a workflow.

- [ ] **Step 3: Authenticate final GitHub state**

Require:

- `gh repo view` returns Public visibility, `main`, the approved description, and exactly topics `ai-engineering`, `machine-learning`, `mlops`, `model-delivery`, `onnx`, `supply-chain-security`;
- anonymous repository and raw README requests return HTTP `200`;
- `git ls-remote origin refs/heads/main` equals local HEAD;
- release-ci runs, tags, GitHub Releases, and exact `model-delivery-control-plane` container-package matches remain `0`;
- both historical successful Windows runs and the new exact run remain `completed/success`.

- [ ] **Step 4: Re-run the metadata-only closure gate**

```powershell
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reviewer-fast-path.ps1
git status --short
```

Require verifier/demo/fast path PASS with zero mutations and a clean tracked worktree.

- [ ] **Step 5: Record custody and report closure**

Append the exact commits, test counts, review counts, pushed SHA, new run URL/conclusion, Public metadata, anonymous HTTP results, negative release/package state, frozen anchors, H2 state, and clean worktree to the ignored SDD ledger. Notify Portfolio Control of the new safe checkpoint without modifying another repository.

End with:

```text
PUBLIC_GITHUB_PORTFOLIO_READY / WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS
!= CROSS_PLATFORM_PORTABLE / REMOTE_RELEASED / PRODUCTION_READY
```
