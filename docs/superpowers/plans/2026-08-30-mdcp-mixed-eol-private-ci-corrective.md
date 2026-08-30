# MDCP Mixed-EOL Private CI Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every supported Git checkout materialize the repository's frozen mixed-EOL byte profile, truthfully bind readiness v1.2 to the failed Windows run, and obtain one exact successful replacement Windows Portfolio CI run without broadening release or production authority.

**Architecture:** `.gitattributes` becomes the repository-native byte-materialization contract: LF is the text baseline, sixteen exact identity inputs are CRLF, and the existing supply-chain binary subtree remains non-text. A fresh local repository test clones the complete tracked tree under `core.autocrlf=true`, `false`, and `input`, then authenticates line endings, binaries, public bytes, and frozen identities. Readiness v1.2 records the failed base run before a single atomic corrective commit is reviewed, pushed once, and authenticated remotely.

**Tech Stack:** Git attributes, Git 2.x, Windows PowerShell 7, Python 3.12, `uv` 0.11.18, Pydantic v2, pytest, Ruff, GitHub Actions, GitHub CLI, GitHub REST API.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-30-mdcp-mixed-eol-private-ci-corrective-design.md` at commit `a82713ae8b447c43a8e281653b7bd5fa4db5572a`, SHA-256 `3227e7755edc6af5460a61376048ff701114bd97c6dc78afb9b0fef3a493bcca`.
- Use only the existing linked worktree and branch `codex/wave0-foundation-feasibility`; do not checkout, reset, stash, merge, delete, or force-update local `main`.
- Remote remains exactly `origin=https://github.com/kuotunyu/model-delivery-control-plane.git`; remote `main` starts at `13b922849f89691ab2d98d89d8750bee40309f32` and repository visibility remains Private.
- Preserve failed runs `33311024512` (Ubuntu platform-contract failure) and `33316653641` (Windows mixed-EOL failure). Never delete, hide, or rerun either commit.
- The mixed-EOL contract is exactly LF baseline `* text=auto eol=lf`, the existing `tests/fixtures/supply-chain/** -text` protection, the sixteen exact CRLF paths from the approved design, and all existing explicit public LF rules.
- Do not change `.github/workflows/portfolio-ci.yml`, `.github/workflows/release-ci.yml`, any `src/mdcp` path, `V1_SERVING_PATHS`, `V2_SERVING_PATHS`, identity algorithms, dependency files, Docker/Compose configuration, model/data fixtures, or historical search/formal evidence.
- Preserve v1 identity `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`, v2 identity `198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea`, `uv.lock` SHA-256 `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`, search source identity `cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b`, worker identity `ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3`, and static firewall identity `e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1`.
- Readiness v1.2 authenticates failed base commit `13b922849f89691ab2d98d89d8750bee40309f32`, run `33316653641`, conclusion `failure`, and that base commit's `1625 passed, 7 skipped`, Critical `0`, Important `0`, Minor `0` local closure. Later tests do not rewrite those historical counts.
- `PUBLIC_SURFACE_PATHS` remains the existing ordered ten-path tuple. `.gitattributes` is protected by the checkout test and readiness does not inventory itself.
- Use TDD: observe the new checkout/readiness tests fail for the intended reason before implementation, then make the minimum in-scope change.
- The implementation is one atomic commit after all eight implementation files are mutually consistent, the complete local gate passes, and independent review reports Critical `0`, Important `0`.
- Existing author and committer must both be exactly `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`.
- One non-force push of reviewed HEAD to remote `main` is authorized after all local gates. Do not push an intermediate commit or rerun unchanged bytes.
- Never dispatch `release-ci.yml`; never force-push, merge, tag, create a GitHub Release, publish a package/GHCR image, change visibility, change auth scopes, run P2/H2/model/data, start a container/network, or touch another repository.
- A failed, missing, cancelled, or timed-out replacement run leaves the repository Private and requires `systematic-debugging`; do not enter the existing final-readiness Task 3.
- Treat `.hypothesis/`, `__pycache__`, pytest caches, and the existing ignored diagnostic archive/extraction as non-source. Do not stage or delete active evidence while executing this plan.
- Implementation may modify only `.gitattributes`, `README.md`, `docs/reviewer/quickstart.md`, `docs/reviewer/release-evidence.md`, `evidence/public/portfolio/local-release-readiness.json`, `schemas/portfolio/local-release-readiness.schema.json`, `scripts/verify-public-release.py`, and `tests/publication/test_public_release_surface.py`. This plan file is the ninth approved path and is committed separately before implementation.

## File responsibility map

- `.gitattributes`: authoritative checkout byte profile; no runtime policy.
- `tests/publication/test_public_release_surface.py`: fresh-checkout, frozen identity, readiness, disclosure, copy, and canonical inventory regressions.
- `scripts/verify-public-release.py`: closed readiness v1.2 Pydantic contract and public inventory verifier.
- `schemas/portfolio/local-release-readiness.schema.json`: generated JSON Schema from the closed verifier model.
- `evidence/public/portfolio/local-release-readiness.json`: RFC 8785 canonical failed-Windows-run evidence; excluded from its own public inventory.
- `README.md`: recruiter-facing summary and honest Private/failed-run claim ceiling.
- `docs/reviewer/quickstart.md`: reviewer commands and remote-evidence status.
- `docs/reviewer/release-evidence.md`: durable evidence taxonomy containing both failed-run anchors.

## Shared local verification gate

Run from the worktree root:

```powershell
uv lock --check
uv run --no-sync ruff check src/mdcp tests scripts
uv run --no-sync ruff format --check scripts/verify-public-release.py tests/publication/test_public_release_surface.py
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py
uv run --no-sync pytest -p no:cacheprovider -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/contract/workload/test_wave1_inventory.py tests/integration/temporal/test_contract_gate.py tests/integration/temporal/test_search_freeze_preflight.py tests/unit/temporal/test_golden_vectors.py
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
pwsh -NoProfile -File scripts/reviewer-fast-path.ps1
uv run --no-sync pytest -p no:cacheprovider -q
git diff --check
git status --short
```

Global Ruff check remains required. Format only the two changed Python files because the repository has inherited unrelated format drift. The complete suite must disable pytest's cache provider.

Use these independent frozen comparisons after focused and full tests:

```powershell
uv run --no-sync python -c "from pathlib import Path; from mdcp.contracts.release import serving_inventory_digest, serving_inventory_from_root; print(serving_inventory_digest(serving_inventory_from_root(Path.cwd())))"
uv run --no-sync python -c "from pathlib import Path; from mdcp.contracts.serving_identity_v2 import V2_SERVING_PATHS, build_v2_serving_inventory; print(build_v2_serving_inventory(Path.cwd(), V2_SERVING_PATHS).inventory_sha256)"
uv run --no-sync python -c "from pathlib import Path; from mdcp.temporal.search_identity import build_search_source_inventory; from mdcp.temporal.formal_worker_protocol import search_source_inventory_sha256; print(search_source_inventory_sha256(build_search_source_inventory(Path.cwd())))"
uv run --no-sync python -c "import hashlib; from pathlib import Path; from mdcp.temporal.formal_worker_protocol import FORMAL_WORKER_SOURCE_PATHS, FormalWorkerSourceEntry, formal_worker_inventory_sha256; root=Path.cwd(); entries=tuple(FormalWorkerSourceEntry(logical_path=path,sha256=hashlib.sha256((root/path).read_bytes()).hexdigest()) for path in FORMAL_WORKER_SOURCE_PATHS); print(formal_worker_inventory_sha256(entries))"
(Get-FileHash -Algorithm SHA256 uv.lock).Hash.ToLowerInvariant()
```

---

### Task 1: Establish and prove the repository-native mixed-EOL contract

**Files:**

- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `.gitattributes`

**Interfaces:**

- Consumes: `SERVING_PATHS`, `V2_SERVING_PATHS`, `SEARCH_SOURCE_PATHS`, `FORMAL_WORKER_SOURCE_PATHS`, the ten-path `PUBLIC_SURFACE_PATHS`, and complete tracked worktree bytes.
- Produces: `CRLF_IDENTITY_PATHS`, `FROZEN_IDENTITY_SNAPSHOT`, `_identity_lf_paths()`, `_identity_snapshot()`, and `test_repository_mixed_eol_profile_survives_all_autocrlf_modes()`.

- [ ] **Step 1: Re-establish exact local and remote base state**

```powershell
git status --short --branch
$implementationBase = (git rev-parse HEAD).Trim()
git branch --show-current
git remote -v
git ls-remote origin refs/heads/main
(Get-FileHash -Algorithm SHA256 docs/superpowers/specs/2026-08-30-mdcp-mixed-eol-private-ci-corrective-design.md).Hash.ToLowerInvariant()
git diff --name-only 13b922849f89691ab2d98d89d8750bee40309f32..HEAD
```

Require a clean worktree, branch `codex/wave0-foundation-feasibility`, only the exact `origin`, remote `main` at `13b922849f89691ab2d98d89d8750bee40309f32`, approved design hash `3227e7755edc6af5460a61376048ff701114bd97c6dc78afb9b0fef3a493bcca`, and only the already committed design/plan paths after the remote base. Store `$implementationBase`; it is the exact implementation diff base for Task 3.

- [ ] **Step 2: Replace the narrow checkout test with RED profile helpers**

Add `tempfile` to standard-library imports. Add these constants after `PUBLIC_DOCUMENTS`:

```python
CRLF_IDENTITY_PATHS = (
    "docs/superpowers/plans/2026-08-23-mdcp-wave-0-foundation-feasibility.md",
    "docs/superpowers/plans/2026-08-23-mdcp-wave-1-workload-identity.md",
    "docs/superpowers/plans/2026-08-23-mdcp-wave-2-validator-supply-chain.md",
    "docs/superpowers/plans/2026-08-23-mdcp-wave-3-control-routing-shadow.md",
    "docs/superpowers/plans/2026-08-23-mdcp-wave-4-windows-policy.md",
    "docs/superpowers/plans/2026-08-23-mdcp-wave-5-canary-recovery.md",
    "docs/superpowers/plans/2026-08-23-mdcp-wave-6-observability-reviewer.md",
    "docs/superpowers/plans/2026-08-23-mdcp-wave-7-release-closure.md",
    "docs/superpowers/plans/2026-08-23-model-delivery-control-plane-plan-index.md",
    "docs/superpowers/specs/2026-08-23-model-delivery-control-plane-design.md",
    "evidence/public/feasibility/wave0-report.json",
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/runner.py",
    "src/mdcp/temporal/search_identity.py",
    "tests/fixtures/artifacts/candidate/artifact-descriptor.json",
    "tests/fixtures/artifacts/stable/artifact-descriptor.json",
)
FROZEN_IDENTITY_SNAPSHOT = {
    "v1": "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209",
    "v2": "198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea",
    "search_source": "cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b",
    "formal_worker": "ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3",
    "golden_manifest": "ddeb4c7d52223589828b927ce744f53c5ca6981ce303b853230976fb88dc9eae",
    "wave0_report": "900f038e34b92cdf14e32042ea8aa44910c4c35758ec2335300f64ba4f621194",
    "wave1_freeze": "f64004507703c342a0e116b6867185cdabee1a16870ed52f4d3ca16e0719dad7",
    "stable_descriptor": "92dac42877c500ad60bb982768bb5477077c5755b165ddbbe8a97af3b20e0522",
    "candidate_descriptor": "f5cd7a452deae4d2b90c90b875f65f7b538ee1593aed27a4358cadb6ec53b80b",
}
```

Add exact helpers before the checkout test:

```python
def _lf_bytes(raw: bytes) -> bytes:
    normalized = raw.replace(b"\r\n", b"\n")
    assert b"\r" not in normalized
    return normalized


def _crlf_bytes(raw: bytes) -> bytes:
    return _lf_bytes(raw).replace(b"\n", b"\r\n")


def _identity_lf_paths(verifier: object) -> tuple[str, ...]:
    from mdcp.contracts.release import SERVING_PATHS
    from mdcp.contracts.serving_identity_v2 import V2_SERVING_PATHS
    from mdcp.temporal.formal_worker_protocol import (
        FORMAL_WORKER_SOURCE_PATHS,
        SEARCH_SOURCE_PATHS,
    )

    paths = {
        ".gitattributes",
        "evidence/public/wave1/workload-identity-report.json",
        "tests/fixtures/workload/freeze-manifest.json",
        *SERVING_PATHS,
        *V2_SERVING_PATHS,
        *SEARCH_SOURCE_PATHS,
        *FORMAL_WORKER_SOURCE_PATHS,
        *verifier.PUBLIC_SURFACE_PATHS,
    }
    return tuple(sorted(paths.difference(CRLF_IDENTITY_PATHS), key=str.encode))


def _identity_snapshot(root: Path) -> dict[str, str]:
    from mdcp.common.digests import sha256_hex
    from mdcp.contracts.release import serving_inventory_digest, serving_inventory_from_root
    from mdcp.contracts.serving_identity_v2 import V2_SERVING_PATHS, build_v2_serving_inventory
    from mdcp.temporal.formal_worker_protocol import (
        FORMAL_WORKER_SOURCE_PATHS,
        FormalWorkerSourceEntry,
        formal_worker_inventory_sha256,
        search_source_inventory_sha256,
    )
    from mdcp.temporal.golden_vectors import verify_golden_vector_manifest
    from mdcp.temporal.search_identity import build_search_source_inventory
    from mdcp.workload.reviewer_fixtures import verify_reviewer_fixtures

    worker_entries = tuple(
        FormalWorkerSourceEntry(
            logical_path=logical_path,
            sha256=hashlib.sha256((root / logical_path).read_bytes()).hexdigest(),
        )
        for logical_path in FORMAL_WORKER_SOURCE_PATHS
    )
    wave1 = json.loads(
        (root / "evidence/public/wave1/workload-identity-report.json").read_text(
            encoding="utf-8"
        )
    )
    reviewer = verify_reviewer_fixtures(root / "tests/fixtures/artifacts")
    return {
        "v1": serving_inventory_digest(serving_inventory_from_root(root)),
        "v2": build_v2_serving_inventory(root, V2_SERVING_PATHS).inventory_sha256,
        "search_source": search_source_inventory_sha256(build_search_source_inventory(root)),
        "formal_worker": formal_worker_inventory_sha256(worker_entries),
        "golden_manifest": verify_golden_vector_manifest(
            root / "tests/fixtures/temporal/adapter-golden-vectors.json"
        ).manifest_sha256,
        "wave0_report": sha256_hex(
            (root / "evidence/public/feasibility/wave0-report.json").read_bytes()
        ),
        "wave1_freeze": sha256_hex(
            (root / "tests/fixtures/workload/freeze-manifest.json").read_bytes()
        ),
        "stable_descriptor": reviewer.descriptor_digests["stable"],
        "candidate_descriptor": reviewer.descriptor_digests["candidate"],
    }
```

Replace `test_public_surface_bytes_survive_a_fresh_autocrlf_checkout` with:

```python
def test_repository_mixed_eol_profile_survives_all_autocrlf_modes() -> None:
    verifier = _load_verifier()
    temporary_root = Path(tempfile.mkdtemp(prefix="mdcp-eol-"))
    try:
        source_repository = temporary_root / "source"
        source_repository.mkdir()
        _run_git(source_repository, "init", "--quiet")
        tracked_raw = _run_git(REPOSITORY_ROOT, "ls-files", "-z")
        tracked_paths = tuple(
            item.decode("utf-8", errors="strict") for item in tracked_raw.split(b"\0") if item
        )
        for logical_path in tracked_paths:
            target = source_repository / logical_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPOSITORY_ROOT / logical_path, target)
        _run_git(source_repository, "add", "--all")
        _run_git(
            source_repository,
            "-c",
            "user.name=Mixed EOL Test",
            "-c",
            "user.email=mixed-eol@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "mixed EOL fixture",
        )

        binary_paths = tuple(
            path for path in tracked_paths if path.startswith("tests/fixtures/supply-chain/")
        )
        lf_paths = _identity_lf_paths(verifier)
        observed_profiles = []
        observed_snapshots = []
        for mode in ("true", "false", "input"):
            checkout = temporary_root / f"checkout-{mode}"
            subprocess.run(
                (
                    "git",
                    "-c",
                    f"core.autocrlf={mode}",
                    "clone",
                    "--quiet",
                    "--no-hardlinks",
                    str(source_repository),
                    str(checkout),
                ),
                check=True,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=30,
            )
            for logical_path in CRLF_IDENTITY_PATHS:
                assert (checkout / logical_path).read_bytes() == _crlf_bytes(
                    (REPOSITORY_ROOT / logical_path).read_bytes()
                )
                attributes = _run_git(
                    checkout, "check-attr", "text", "eol", "--", logical_path
                ).decode("utf-8", errors="strict")
                assert attributes.splitlines() == [
                    f"{logical_path}: text: set",
                    f"{logical_path}: eol: crlf",
                ]
            for logical_path in lf_paths:
                assert (checkout / logical_path).read_bytes() == _lf_bytes(
                    (REPOSITORY_ROOT / logical_path).read_bytes()
                )
            for logical_path in verifier.PUBLIC_SURFACE_PATHS:
                attributes = _run_git(
                    checkout, "check-attr", "text", "eol", "--", logical_path
                ).decode("utf-8", errors="strict")
                assert attributes.splitlines() == [
                    f"{logical_path}: text: set",
                    f"{logical_path}: eol: lf",
                ]
            for logical_path in binary_paths:
                assert (checkout / logical_path).read_bytes() == (
                    REPOSITORY_ROOT / logical_path
                ).read_bytes()
                attributes = _run_git(
                    checkout, "check-attr", "text", "--", logical_path
                ).decode("utf-8", errors="strict")
                assert attributes == f"{logical_path}: text: unset"
            snapshot = _identity_snapshot(checkout)
            assert snapshot == FROZEN_IDENTITY_SNAPSHOT
            observed_profiles.append(
                tuple((checkout / path).read_bytes() for path in (*CRLF_IDENTITY_PATHS, *lf_paths))
            )
            observed_snapshots.append(snapshot)

        assert observed_profiles[0] == observed_profiles[1] == observed_profiles[2]
        assert observed_snapshots[0] == observed_snapshots[1] == observed_snapshots[2]
    finally:
        shutil.rmtree(temporary_root)
```

Do not add network access, a Git remote, symlinks, or a dependency installation to this test. The source repository is built only from `git ls-files` and current worktree bytes; the short OS temporary path avoids the previously proven deep-path collection failure.

- [ ] **Step 3: Run the new test and authenticate RED**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py::test_repository_mixed_eol_profile_survives_all_autocrlf_modes -vv
```

Expected: FAIL before snapshot completion because current `.gitattributes` leaves the sixteen paths unspecified and checkout bytes differ by `core.autocrlf` mode. A path-length, import, missing-file, timeout, or binary-copy failure is not the intended RED; invoke `systematic-debugging` before changing attributes if one occurs.

- [ ] **Step 4: Implement the exact attribute contract**

Replace `.gitattributes` with this exact ordered content:

```gitattributes
* text=auto eol=lf
tests/fixtures/supply-chain/** -text
docs/superpowers/plans/2026-08-23-mdcp-wave-0-foundation-feasibility.md text eol=crlf
docs/superpowers/plans/2026-08-23-mdcp-wave-1-workload-identity.md text eol=crlf
docs/superpowers/plans/2026-08-23-mdcp-wave-2-validator-supply-chain.md text eol=crlf
docs/superpowers/plans/2026-08-23-mdcp-wave-3-control-routing-shadow.md text eol=crlf
docs/superpowers/plans/2026-08-23-mdcp-wave-4-windows-policy.md text eol=crlf
docs/superpowers/plans/2026-08-23-mdcp-wave-5-canary-recovery.md text eol=crlf
docs/superpowers/plans/2026-08-23-mdcp-wave-6-observability-reviewer.md text eol=crlf
docs/superpowers/plans/2026-08-23-mdcp-wave-7-release-closure.md text eol=crlf
docs/superpowers/plans/2026-08-23-model-delivery-control-plane-plan-index.md text eol=crlf
docs/superpowers/specs/2026-08-23-model-delivery-control-plane-design.md text eol=crlf
evidence/public/feasibility/wave0-report.json text eol=crlf
src/mdcp/temporal/firewall.py text eol=crlf
src/mdcp/temporal/runner.py text eol=crlf
src/mdcp/temporal/search_identity.py text eol=crlf
tests/fixtures/artifacts/candidate/artifact-descriptor.json text eol=crlf
tests/fixtures/artifacts/stable/artifact-descriptor.json text eol=crlf
.github/workflows/portfolio-ci.yml text eol=lf
/LICENSE text eol=lf
/README.md text eol=lf
docs/architecture.md text eol=lf
docs/reviewer/quickstart.md text eol=lf
docs/reviewer/release-evidence.md text eol=lf
schemas/portfolio/local-release-readiness.schema.json text eol=lf
scripts/reviewer-demo.py text eol=lf
scripts/reviewer-fast-path.ps1 text eol=lf
scripts/verify-public-release.py text eol=lf
```

Do not add a wildcard CRLF rule, extension rule, directory-wide identity exception, `src/mdcp/temporal/run_evidence.py`, or any path not shown above.

- [ ] **Step 5: Run GREEN and the identity-focused suite**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py::test_repository_mixed_eol_profile_survives_all_autocrlf_modes -vv
uv run --no-sync pytest -p no:cacheprovider -q tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/contract/workload/test_wave1_inventory.py tests/integration/temporal/test_contract_gate.py tests/integration/temporal/test_search_freeze_preflight.py tests/unit/temporal/test_golden_vectors.py
git diff --check
git status --short
```

Expected: the checkout test passes for all three modes; focused suite passes with frozen identities; only `.gitattributes` and the publication test are modified. Do not commit yet because readiness and its canonical public inventory are intentionally still stale.

---

### Task 2: Record truthful failed-Windows readiness v1.2 and regenerate the public inventory

**Files:**

- Modify: `tests/publication/test_public_release_surface.py`
- Modify: `scripts/verify-public-release.py`
- Modify: `README.md`
- Modify: `docs/reviewer/quickstart.md`
- Modify: `docs/reviewer/release-evidence.md`
- Regenerate: `schemas/portfolio/local-release-readiness.schema.json`
- Regenerate: `evidence/public/portfolio/local-release-readiness.json`

**Interfaces:**

- Consumes: failed base commit/run anchors, unchanged ten-path `PUBLIC_SURFACE_PATHS`, and Task 1's deterministic checkout contract.
- Produces: closed `LocalReleaseReadiness` v1.2, generated JSON Schema, canonical readiness bytes, and documents containing both failed-run anchors.

- [ ] **Step 1: Write readiness and public-copy RED assertions**

Update `test_readiness_evidence_is_canonical_public_and_binds_surface` to require:

```python
assert readiness.schema_version == "mdcp.local-release-readiness.v1.2"
assert readiness.evidence_class == "github_private_staging_eol_corrective_readiness"
assert readiness.portfolio_ci_commit == "13b922849f89691ab2d98d89d8750bee40309f32"
assert readiness.portfolio_ci_run_url == (
    "https://github.com/kuotunyu/model-delivery-control-plane/"
    "actions/runs/33316653641"
)
assert readiness.portfolio_ci_conclusion == "failure"
assert readiness.claim_ceiling == "mdcp.private-staging-eol-corrective-claim-ceiling.v1"
assert readiness.technical_closure_verification.full_suite_passed == 1625
assert readiness.technical_closure_verification.full_suite_skipped == 7
assert readiness.technical_closure_verification.review_critical == 0
assert readiness.technical_closure_verification.review_important == 0
assert readiness.technical_closure_verification.review_minor == 0
assert readiness.claim_execution.push_executed is True
assert readiness.claim_execution.portfolio_ci_executed is True
assert readiness.claim_execution.portfolio_ci_passed is False
assert readiness.claim_execution.remote_release_executed is False
assert readiness.claim_execution.production_deployed is False
assert readiness.claim_execution.kubernetes_production_ready is False
assert readiness.claim_execution.h2_executed is False
assert readiness.claim_execution.cv_workload_implemented is False
assert readiness.claim_execution.llm_workload_implemented is False
```

Extend the mutation parameter tuple with exact cases:

```python
"affirmative_production",
"affirmative_kubernetes",
"affirmative_h2",
"affirmative_cv",
"affirmative_llm",
```

Implement their branches by setting the corresponding `claim_execution` field to `True`; `affirmative_h2` also sets `h2_status` to `LOADED` and `h2_loaded_rows` to `1`. Keep the expected reason `PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID`.

Add:

```python
def test_private_staging_docs_preserve_both_failed_run_anchors() -> None:
    ubuntu = (
        "https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512"
    )
    windows = (
        "https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33316653641"
    )
    for logical_path in (
        "README.md",
        "docs/reviewer/quickstart.md",
        "docs/reviewer/release-evidence.md",
    ):
        text = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
        assert ubuntu in text
        assert windows in text
        assert "repository remains Private" in text
        assert "portfolio_ci_passed: false" in text
        assert "WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE" in text
```

- [ ] **Step 2: Run readiness RED**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py -vv
```

Expected: readiness/doc assertions fail because v1.1 still points to run `33311024512`; Task 1's checkout regression remains green.

- [ ] **Step 3: Evolve only the closed verifier model**

In `TechnicalClosureVerification`, change only:

```python
full_suite_passed: Literal[1625]
full_suite_skipped: Literal[7]
```

In `LocalReleaseReadiness`, change only these literals:

```python
schema_version: Literal["mdcp.local-release-readiness.v1.2"]
evidence_class: Literal["github_private_staging_eol_corrective_readiness"]
claim_ceiling: Literal["mdcp.private-staging-eol-corrective-claim-ceiling.v1"]
```

Retain `CommitSha`, repository-specific `PortfolioCiRunUrl`, `portfolio_ci_conclusion: Literal["failure"]`, every frozen identity, all `ClaimExecution` false literals except the already true push/executed fields, the exact public path tuple, and all fail-closed validators. Do not add a generic string, optional anchor, alternate verifier, or new public path.

- [ ] **Step 4: Update all three public documents with exact truthful copy**

Each document must contain this block, adapted only for surrounding Markdown layout:

```text
repository remains Private; portfolio_ci_passed: false
Ubuntu failed run: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512
Windows mixed-EOL failed run: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33316653641
The replacement mixed-EOL corrective has not passed remote CI yet.
WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY
```

Keep Traditional Chinese as the primary prose, preserve English technical tokens, and keep every release/tag/package/P2/H2/model/data/CV/LLM/Kubernetes/production claim explicitly false. Add no badge and do not describe a future run as successful.

- [ ] **Step 5: Regenerate schema and canonical readiness in dependency order**

Generate schema only after the verifier model is final:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.SCHEMA_PATH; target.write_text(json.dumps(module.LocalReleaseReadiness.model_json_schema(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')"
```

Then regenerate readiness from the final physical public files:

```powershell
uv run --no-sync python -c "import importlib.util,json,pathlib,sys; root=pathlib.Path('.').resolve(); path=root/'scripts/verify-public-release.py'; spec=importlib.util.spec_from_file_location('public_release_verifier',path); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); target=root/module.READINESS_PATH; document=json.loads(target.read_text(encoding='utf-8')); document['schema_version']='mdcp.local-release-readiness.v1.2'; document['evidence_class']='github_private_staging_eol_corrective_readiness'; document['portfolio_ci_commit']='13b922849f89691ab2d98d89d8750bee40309f32'; document['portfolio_ci_run_url']='https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33316653641'; document['portfolio_ci_conclusion']='failure'; document['claim_ceiling']='mdcp.private-staging-eol-corrective-claim-ceiling.v1'; document['technical_closure_verification']={'full_suite_passed':1625,'full_suite_skipped':7,'review_critical':0,'review_important':0,'review_minor':0}; document['claim_execution'].update({'push_executed':True,'portfolio_ci_executed':True,'portfolio_ci_passed':False,'remote_release_executed':False,'tag_created':False,'production_deployed':False,'kubernetes_production_ready':False,'h2_executed':False,'cv_workload_implemented':False,'llm_workload_implemented':False}); entries=module.build_public_surface_inventory(root); entry_documents=[entry.model_dump(mode='json') for entry in entries]; document['public_surface_entries']=entry_documents; document['public_surface_inventory_sha256']=module.sha256_hex(module.canonicalize_json(entry_documents)); model=module.LocalReleaseReadiness.model_validate(document); target.write_bytes(module.canonicalize_json(model.model_dump(mode='json')))"
```

The readiness file must be canonical bytes with no final newline. Do not hand-edit `public_surface_entries`, sizes, hashes, or inventory digest.

- [ ] **Step 6: Run Task 2 GREEN verification**

```powershell
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py -vv
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
git diff --check
git status --short
```

Expected: publication tests, verifier, and demo pass; exactly the eight implementation paths are modified. Do not commit until Task 3 completes the full gate and review.

---

### Task 3: Run the complete gate, obtain zero-finding review, and create one atomic corrective commit

**Files:**

- Review and commit exactly the eight implementation files from Tasks 1 and 2.
- Do not modify the separately committed design or implementation plan.

**Interfaces:**

- Consumes: `$implementationBase`, deterministic checkout test, readiness v1.2, generated schema/inventory, and all frozen anchors.
- Produces: `$mixedEolCorrectiveCommit`, a clean local branch, and Critical `0`/Important `0` review evidence.

- [ ] **Step 1: Authenticate the exact implementation diff**

```powershell
$implementationBase = (git log -1 --format=%H -- docs/superpowers/plans/2026-08-30-mdcp-mixed-eol-private-ci-corrective.md).Trim()
$expectedPaths = @(
  '.gitattributes',
  'README.md',
  'docs/reviewer/quickstart.md',
  'docs/reviewer/release-evidence.md',
  'evidence/public/portfolio/local-release-readiness.json',
  'schemas/portfolio/local-release-readiness.schema.json',
  'scripts/verify-public-release.py',
  'tests/publication/test_public_release_surface.py'
) | Sort-Object
$actualPaths = @(git diff --name-only $implementationBase --) | Sort-Object
if (Compare-Object $expectedPaths $actualPaths) { throw 'MIXED_EOL_PATH_ALLOWLIST_MISMATCH' }
if (git diff --name-only $implementationBase -- .github src/mdcp uv.lock) { throw 'PROTECTED_PATH_CHANGED' }
git diff --check
git diff --stat $implementationBase --
```

Require all eight paths exactly once and no protected-path output.

- [ ] **Step 2: Run the entire shared local gate**

Run every command under `Shared local verification gate` in order. Capture the focused and full pytest summaries, Ruff results, verifier/demo/fast-path terminals, and frozen comparison outputs. The fresh full-suite count may increase because of new parametrized tests; record the observed count in the execution ledger but keep readiness v1.2's historical `1625/7` anchor unchanged.

After the full suite:

```powershell
if ((Get-FileHash -Algorithm SHA256 uv.lock).Hash.ToLowerInvariant() -ne '781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae') { throw 'LOCK_DRIFT' }
git diff --check
$postGatePaths = @(git diff --name-only $implementationBase --) | Sort-Object
if (Compare-Object $expectedPaths $postGatePaths) { throw 'TEST_MUTATED_TRACKED_PATHS' }
```

Any test failure or unexpected mutation invokes `systematic-debugging`; do not patch outside the allowlist and do not weaken a test.

- [ ] **Step 3: Complete self-review and independent review**

Invoke the `requesting-code-review` skill against the approved design, this plan, and the exact uncommitted diff from `$implementationBase`. Require the reviewer to inspect:

```text
attribute precedence and exact 16-path CRLF list
all three core.autocrlf modes
binary subtree byte equality
frozen identity snapshot construction
short-path cleanup and no network/remotes
readiness v1.2 anchors and impossible-state rejection
canonical inventory regeneration order
zh-TW copy and explicit false claim ceiling
eight-path allowlist and unchanged workflow/production paths
```

Acceptance is Critical `0`, Important `0`. Resolve any in-scope finding with a new RED/GREEN cycle and rerun the complete gate. A finding requiring an additional path stops execution for a design delta.

- [ ] **Step 4: Stage only the atomic corrective and verify identity**

```powershell
git add -- .gitattributes README.md docs/reviewer/quickstart.md docs/reviewer/release-evidence.md evidence/public/portfolio/local-release-readiness.json schemas/portfolio/local-release-readiness.schema.json scripts/verify-public-release.py tests/publication/test_public_release_surface.py
git diff --cached --name-only
git diff --cached --check
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

Require the staged set equals `$expectedPaths`; author and committer are both exactly `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`. Caches, ignored diagnostics, design, plan, workflow, and production files remain unstaged.

- [ ] **Step 5: Commit once and verify clean local closure**

```powershell
git commit -m "fix: make mixed-EOL checkouts deterministic"
$mixedEolCorrectiveCommit = (git rev-parse HEAD).Trim()
git status --short --branch
git show --name-status --format=fuller --no-renames HEAD
git ls-remote origin refs/heads/main
```

Require a 40-hex commit, exactly eight committed paths, clean worktree, local branch ahead of remote, and remote `main` still `13b922849f89691ab2d98d89d8750bee40309f32`. Do not push in this task.

---

### Task 4: Push once and authenticate the exact replacement Private Windows run

**Files:** no repository modification or commit.

**Interfaces:**

- Consumes: clean `$mixedEolCorrectiveCommit`, failed-run anchors, existing Private repository, and restored GitHub REST quota.
- Produces: `$mixedEolCorrectiveRunId`, `$mixedEolCorrectiveRunUrl`, authenticated success/negative-state evidence, or a fail-closed systematic-debugging stop.

- [ ] **Step 1: Perform authenticated pre-push readback**

```powershell
$mixedEolCorrectiveCommit = (git rev-parse HEAD).Trim()
$rate = gh api rate_limit | ConvertFrom-Json
if ($rate.resources.core.remaining -lt 50) { throw 'GITHUB_API_BUDGET_INSUFFICIENT' }
if ((gh api user --jq .login).Trim() -ne 'kuotunyu') { throw 'GITHUB_OWNER_MISMATCH' }
$repository = gh api repos/kuotunyu/model-delivery-control-plane | ConvertFrom-Json
if (-not $repository.private -or $repository.visibility -ne 'private' -or $repository.default_branch -ne 'main') { throw 'PRIVATE_REPOSITORY_STATE_INVALID' }
if ((git ls-remote origin refs/heads/main).Split("`t")[0] -ne '13b922849f89691ab2d98d89d8750bee40309f32') { throw 'REMOTE_MAIN_MOVED' }
foreach ($runId in (33311024512,33316653641)) {
  $run = gh api "repos/kuotunyu/model-delivery-control-plane/actions/runs/$runId" | ConvertFrom-Json
  if ($run.status -ne 'completed' -or $run.conclusion -ne 'failure') { throw "FAILED_RUN_HISTORY_CHANGED_$runId" }
}
$releaseRuns = gh api 'repos/kuotunyu/model-delivery-control-plane/actions/workflows/release-ci.yml/runs?per_page=1' | ConvertFrom-Json
if ($releaseRuns.total_count -ne 0) { throw 'RELEASE_WORKFLOW_RUN_EXISTS' }
$releases = @(gh api 'repos/kuotunyu/model-delivery-control-plane/releases?per_page=1' | ConvertFrom-Json)
if ($releases.Count -ne 0) { throw 'GITHUB_RELEASE_EXISTS' }
if (git ls-remote --tags origin) { throw 'REMOTE_TAG_EXISTS' }
if (git status --porcelain) { throw 'WORKTREE_NOT_CLEAN' }
```

Do not query packages, change scopes, dispatch a workflow, or continue with insufficient authenticated API budget.

- [ ] **Step 2: Perform the one authorized non-force push**

```powershell
git push origin HEAD:main
$remoteMain = (git ls-remote origin refs/heads/main).Split("`t")[0]
if ($remoteMain -ne $mixedEolCorrectiveCommit) { throw 'REMOTE_MAIN_MISMATCH' }
```

No `--force`, tag, alternate ref, merge, second push, or metadata mutation is allowed.

- [ ] **Step 3: Discover exactly one run for the corrective commit**

```powershell
$matchingRuns = @()
for ($attempt = 0; $attempt -lt 5; $attempt++) {
  $runs = gh api 'repos/kuotunyu/model-delivery-control-plane/actions/workflows/portfolio-ci.yml/runs?branch=main&event=push&per_page=20' | ConvertFrom-Json
  $matchingRuns = @($runs.workflow_runs | Where-Object { $_.head_sha -eq $mixedEolCorrectiveCommit })
  if ($matchingRuns.Count -gt 0) { break }
  if ($attempt -lt 4) { Start-Sleep -Seconds 15 }
}
if ($matchingRuns.Count -ne 1) { throw 'MIXED_EOL_CORRECTIVE_RUN_CARDINALITY_INVALID' }
$mixedEolCorrectiveRunId = [long]$matchingRuns[0].id
$mixedEolCorrectiveRunUrl = [string]$matchingRuns[0].html_url
if ($mixedEolCorrectiveRunUrl -notmatch '^https://github\.com/kuotunyu/model-delivery-control-plane/actions/runs/[1-9][0-9]*$') { throw 'MIXED_EOL_CORRECTIVE_RUN_URL_INVALID' }
gh run watch $mixedEolCorrectiveRunId --repo kuotunyu/model-delivery-control-plane --exit-status --interval 30
```

When executing through a terminal session, start the watch with a 30-second yield and poll the same session at intervals no longer than 60 seconds so the user receives progress updates. Do not start a second watch or dispatch.

- [ ] **Step 4: Authenticate terminal success and every mandatory step**

```powershell
$run = gh api "repos/kuotunyu/model-delivery-control-plane/actions/runs/$mixedEolCorrectiveRunId" | ConvertFrom-Json
if ($run.head_sha -ne $mixedEolCorrectiveCommit -or $run.head_branch -ne 'main' -or $run.event -ne 'push' -or $run.status -ne 'completed' -or $run.conclusion -ne 'success' -or $run.name -ne 'Portfolio CI') { throw 'MIXED_EOL_CORRECTIVE_RUN_NOT_SUCCESSFUL' }
$jobs = gh api "repos/kuotunyu/model-delivery-control-plane/actions/runs/$mixedEolCorrectiveRunId/jobs?per_page=100" | ConvertFrom-Json
$verifyJobs = @($jobs.jobs | Where-Object { $_.name -eq 'verify' })
if ($verifyJobs.Count -ne 1 -or $verifyJobs[0].conclusion -ne 'success') { throw 'PORTFOLIO_VERIFY_JOB_NOT_SUCCESSFUL' }
$requiredSteps = @(
  'Configure Windows checkout policy',
  'Checkout complete evidence history',
  'Set up locked Python and uv',
  'Install checksum-pinned Docker Compose config renderer',
  'Install locked dependencies',
  'Verify lock and static checks',
  'Verify public evidence and deterministic demo',
  'Run complete test suite',
  'Reject tracked-file mutation'
)
foreach ($requiredStep in $requiredSteps) {
  $matches = @($verifyJobs[0].steps | Where-Object { $_.name -eq $requiredStep })
  if ($matches.Count -ne 1 -or $matches[0].conclusion -ne 'success') { throw "PORTFOLIO_STEP_NOT_SUCCESSFUL_$requiredStep" }
}
```

If the run is not `completed/success`, preserve its URL and terminal logs, keep the repository Private, invoke `systematic-debugging`, and stop before the next task. Never rewrite readiness to success and never rerun unchanged commit bytes.

- [ ] **Step 5: Recheck negative external state and local identities**

```powershell
$repository = gh api repos/kuotunyu/model-delivery-control-plane | ConvertFrom-Json
if (-not $repository.private -or $repository.visibility -ne 'private') { throw 'VISIBILITY_CHANGED' }
$releaseRuns = gh api 'repos/kuotunyu/model-delivery-control-plane/actions/workflows/release-ci.yml/runs?per_page=1' | ConvertFrom-Json
if ($releaseRuns.total_count -ne 0) { throw 'RELEASE_WORKFLOW_RUN_EXISTS' }
$releases = @(gh api 'repos/kuotunyu/model-delivery-control-plane/releases?per_page=1' | ConvertFrom-Json)
if ($releases.Count -ne 0) { throw 'GITHUB_RELEASE_EXISTS' }
if (git ls-remote --tags origin) { throw 'REMOTE_TAG_EXISTS' }
if ((git ls-remote origin refs/heads/main).Split("`t")[0] -ne $mixedEolCorrectiveCommit) { throw 'REMOTE_MAIN_MISMATCH' }
if (git status --porcelain) { throw 'WORKTREE_NOT_CLEAN' }
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
```

Re-run the five frozen comparison commands from the shared gate and require the exact approved values. Package readback remains deferred and no auth scope changes are allowed.

- [ ] **Step 6: Close this corrective and resume only the existing final-readiness sequence**

Record in the execution ledger:

```text
mixed-EOL corrective commit: $mixedEolCorrectiveCommit
replacement Portfolio CI run: $mixedEolCorrectiveRunUrl
run conclusion: success
repository visibility: Private
release-ci runs: 0
tags: 0
GitHub Releases: 0
packages queried: false
P2/H2/model/data executed: false
```

Expand the two PowerShell variables to the actual values captured in Steps 2–5 when writing the ledger. After successful closure, return to Task 3 of `docs/superpowers/plans/2026-08-30-mdcp-windows-native-portfolio-ci-corrective.md` and bind final readiness v2 to this successful run. Do not enter package authorization, Public visibility, release, tag, or production steps.

## Expected sequence

```text
13b9228 base -> Windows run 33316653641 failure (preserved)
design commit -> plan commit -> atomic mixed-EOL corrective commit
one non-force push -> exact Windows Portfolio CI success
authenticated Private/negative-state readback
resume existing Task 3 final readiness v2 only
```

This plan ends before final readiness v2, package readback, Public visibility, release, tag, deployment, P2/H2, model/data execution, or any other repository action.
