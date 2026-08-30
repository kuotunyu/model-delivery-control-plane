# MDCP Public-State Consistency Corrective Design

**Date:** 2026-08-31  
**Repository:** `kuotunyu/model-delivery-control-plane`  
**Branch:** `codex/wave0-foundation-feasibility`  
**Base commit:** `6588d4e1c0b79b9120f7e43f50bb45a3b6a8ede2`

## 1. Purpose

The repository is externally verified Public, but three recruiter-facing documents still describe
the current repository as Private. The underlying Windows-native CI evidence is valid: its runs
occurred while the repository was Private. The defect is a copy/evidence consistency error between
the current GitHub visibility and the documents' present-tense wording.

This corrective makes the present state truthful without rewriting historical staging facts,
expanding the technical claim ceiling, or changing runtime behavior.

## 2. Selected approach

Apply a minimal offline corrective to the three recruiter-facing documents, their publication
contract tests, and the canonical local readiness evidence. Preserve the existing verifier and
schema interfaces. Regenerate the public-surface inventory after the final document bytes exist,
then prove the result locally and with one new Windows Portfolio CI run.

This approach is selected because it fixes the public contradiction with the smallest review
surface and preserves the offline, deterministic reviewer path.

### 2.1 Rejected: add live GitHub API verification

The verifier could query GitHub visibility on every run. That would turn an offline evidence
validator into a network-dependent tool, introduce authentication and rate-limit failure modes,
and weaken deterministic local review. External visibility remains a final-audit concern.

### 2.2 Rejected: bundle Linux portability

Linux portability changes runner semantics, path contracts, file modes, retained/private behavior,
and a frozen numeric vector. Combining it with copy correction would enlarge the failure domain and
make a recruiter-facing truth fix depend on an unrelated portability campaign.

## 3. Truth taxonomy

The documents must distinguish current state from historical execution:

- Current state: `repository is Public; portfolio_ci_passed: true`.
- Historical fact: the recorded Ubuntu failure, Windows mixed-EOL failure, and successful Windows
  corrective runs occurred during Private staging.
- Supported claim: `PUBLIC_GITHUB_PORTFOLIO_READY` and
  `WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS`.
- Unsupported claims remain `CROSS_PLATFORM_PORTABLE`, `REMOTE_RELEASED`, and
  `PRODUCTION_READY`.
- Release CI remains an undispatched manual design surface.
- Package, tag, GitHub Release, P2, H2, workload, Kubernetes, and production claims remain false.

The legacy present-tense sentence `repository remains Private` must not appear in any of the three
recruiter-facing documents. The word `Private` may remain only when it modifies historical staging,
push, or run context.

## 4. File and interface boundaries

### 4.1 Implementation paths

- `README.md`: correct the current Portfolio CI and claim-ceiling copy.
- `docs/reviewer/quickstart.md`: correct the current state and workflow link label.
- `docs/reviewer/release-evidence.md`: separate Public current state from Private historical runs.
- `tests/publication/test_public_release_surface.py`: replace the obsolete Private-state contract
  with exact current-state and historical-context assertions.
- `evidence/public/portfolio/local-release-readiness.json`: regenerate the public-surface entries and
  aggregate digest after the three documents reach final bytes; record the fresh local full-suite
  result in `technical_closure_verification`.

### 4.2 Process paths

- `docs/superpowers/specs/2026-08-31-mdcp-public-state-consistency-corrective-design.md`
- `docs/superpowers/plans/2026-08-31-mdcp-public-state-consistency-corrective.md`

### 4.3 Explicitly unchanged

- `.github/workflows/portfolio-ci.yml`
- `schemas/portfolio/local-release-readiness.schema.json`
- `scripts/verify-public-release.py`
- `scripts/reviewer-demo.py`
- `scripts/reviewer-fast-path.ps1`
- all `src/mdcp/**` production paths
- `.gitattributes`, `uv.lock`, serving path sets, firewall policy, search evidence, formal-worker
  evidence, H2 state, model/data fixtures, and release workflow

No new command, schema field, verifier capability, dependency, workflow permission, or network call
is introduced.

## 5. Evidence data flow

1. Tests first encode the required Public current-state sentence and reject the legacy present-tense
   Private sentence.
2. The three documents are updated while preserving all historical run URLs and negative claims.
3. `build_public_surface_inventory()` computes final byte sizes and SHA-256 values for the existing
   ordered `PUBLIC_SURFACE_PATHS` tuple.
4. The readiness document receives those entries and their RFC 8785 aggregate digest. Its existing
   v2 schema, evidence class, successful Windows commit/run anchor, and negative claim fields remain
   unchanged.
5. The full suite is run. The observed passed/skipped counts replace the historical counts in
   `technical_closure_verification`, and the publication tests plus full suite are rerun against the
   final readiness bytes.
6. Local review proves Critical `0` and Important `0`, then all local commits are sent with one
   non-force push to `main`.
7. One exact Portfolio CI run for the pushed HEAD must finish `completed/success` before closure.

The readiness document is not a member of `PUBLIC_SURFACE_PATHS`, so regenerating its inventory is
non-recursive.

## 6. Failure handling

- Any unexpected changed path stops staging and commit.
- Any frozen identity, lock, H2, release, tag, package, or worktree-state drift stops the push.
- A local test failure is handled with systematic debugging within the exact file boundary.
- A remote failure is preserved and inspected; unchanged bytes are not retried.
- A failed, cancelled, missing, or timed-out run prevents a success claim.
- No force push, workflow dispatch, tag, GitHub Release, package publication, merge, or release action
  is allowed.

## 7. Verification

The local gate requires:

- `uv lock --check`;
- Ruff check and exact-file format checks;
- publication/workflow tests;
- public release verifier and reviewer demo;
- reviewer fast path with zero repository mutations;
- focused serving/formal-worker/security tests;
- complete pytest suite;
- exact v1, v2, search-source, formal-worker, and `uv.lock` digests;
- H2 `SEALED_NOT_LOADED` with loaded rows `0`;
- `git diff --check` and an exact path audit;
- independent review with Critical `0` and Important `0`.

The remote closure requires:

- Public visibility, default branch `main`, approved description, and exact six topics;
- anonymous repository and README HTTP `200`;
- local HEAD and remote `main` equal the pushed commit;
- the exact new Portfolio CI run is `completed/success`;
- release-ci runs, tags, GitHub Releases, and an exact matching container package remain zero;
- tracked worktree is clean.

## 8. Success statement

The corrective may close only with:

```text
PUBLIC_GITHUB_PORTFOLIO_READY / WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS
!= CROSS_PLATFORM_PORTABLE / REMOTE_RELEASED / PRODUCTION_READY
```

Linux portability remains a separate future design after this truthful Public-state checkpoint.
