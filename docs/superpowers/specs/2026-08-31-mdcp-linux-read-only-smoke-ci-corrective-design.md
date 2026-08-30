# MDCP Linux Read-Only Smoke CI Corrective Design

**Date:** 2026-08-31

**Repository:** `kuotunyu/model-delivery-control-plane`

**Branch:** `codex/wave0-foundation-feasibility`

**Base commit:** `f4f6223ee2dcaa463079d9dca64b2011ecc094d7`

## 1. Purpose

MDCP has an authoritative Windows-native full-suite Portfolio CI result, but a reviewer cannot yet
see a current successful Linux execution of the repository's shell-neutral publication boundary.
The historical Ubuntu full-suite run failed because it exercised inherited Windows-specific
contracts; that failure correctly prevents a cross-platform portability claim.

This corrective adds a separate `ubuntu-24.04` read-only smoke job that verifies only the bounded
public-review surface. It does not change production code, historical identities, runtime
semantics, or the meaning of the Windows full-suite result.

## 2. Approaches considered

### 2.1 Selected: parallel bounded Linux publication smoke

Keep the existing Windows `verify` job as the authoritative complete-suite gate and add a parallel
job named `Linux read-only smoke (not portability proof)`. The Linux job uses the same pinned
checkout and `setup-uv` actions, installs the existing frozen dependency graph, runs the public
verifier and deterministic reviewer demo, runs the two publication contract test modules, and
rejects tracked-file mutation.

This gives recruiters useful evidence that the public reviewer boundary executes on a current
Linux runner while making the claim ceiling explicit in the job name, documentation, tests, and
recorded run.

### 2.2 Rejected: restore the complete suite on Ubuntu

The complete suite includes frozen Windows byte, path, retained/private publication, file-mode,
Compose-renderer, and numeric contracts. Making those portable would require production and
evidence changes outside this corrective. Re-running the unchanged full suite or weakening it with
skips would repeat the historical mistake.

### 2.3 Rejected: mark the Linux job non-blocking

`continue-on-error` would allow the workflow to appear successful when the advertised smoke proof
failed. The smoke job is bounded rather than optional: its failure must fail the workflow, while
its success still supports only the explicitly limited smoke claim.

## 3. Workflow contract

`.github/workflows/portfolio-ci.yml` retains its current triggers, top-level `contents: read`
permission, same-ref cancellation, and Windows job byte-for-byte behavior. The added job is exactly:

- job id `linux_read_only_smoke`;
- display name `Linux read-only smoke (not portability proof)`;
- `runs-on: ubuntu-24.04` and `timeout-minutes: 15`;
- full-history checkout using
  `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`, with
  `fetch-depth: 0` and `persist-credentials: false`;
- Python `3.12` and `uv` `0.11.18` using
  `astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d`, with cache disabled;
- `uv sync --frozen --group ml` as the only dependency installation command;
- `uv lock --check`;
- `uv run --no-sync python scripts/verify-public-release.py --repository-root .`;
- `uv run --no-sync python scripts/reviewer-demo.py --repository-root .`;
- `uv run --no-sync pytest -p no:cacheprovider -q
  tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py`;
- `git diff --exit-code` as the terminal mutation check.

The two complete publication test modules are intentionally used instead of `pytest -k`,
`--ignore`, xfail, or a hand-picked list of passing test ids. They validate canonical public
evidence, the exact workflow authority boundary, the deterministic demo, Git topology, public
documentation, and mixed-EOL materialization without claiming that Windows-specific runtime and
formal-worker behavior is portable.

The Linux job has no Docker installation or command, GitHub CLI mutation, secret, OIDC, artifact
upload, cache, package, release, tag, deployment, model/data execution, or job-level permission
escalation. Its setup network is limited to the pinned GitHub actions and frozen dependency
installation already authorized for CI.

## 4. Evidence and claim taxonomy

The following statements remain distinct:

- `WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS`: the authoritative full suite passed on Windows.
- `LINUX_READ_ONLY_SMOKE_PASS`: the bounded publication verifier/demo/contracts passed on Linux.
- `CROSS_PLATFORM_PORTABLE`: remains false and unsupported.
- `REMOTE_RELEASED` and `PRODUCTION_READY`: remain false and unsupported.

The historical Ubuntu full-suite failure `33311024512` remains in the release-evidence guide and is
not retried, deleted, or relabeled. The successful Windows anchor remains commit
`8bc91a548846af0b1f1be1fc9ae6fbb80b7f63f1`, run `33322212462`, in both the verifier and canonical
readiness model.

The closed readiness schema has no Linux-smoke field and is not changed. Instead, the exact first
successful Linux-smoke commit and run URL are recorded in `README.md`, reviewer quickstart, and the
release-evidence guide. Because those files and the workflow are members of `PUBLIC_SURFACE_PATHS`,
the readiness document is regenerated to bind their final bytes while preserving every existing
identity, execution boolean, historical technical measurement, and Windows Portfolio CI anchor.

## 5. Two-push execution sequence

1. Encode the exact Linux job and pre-evidence documentation contract in failing publication tests.
2. Add the workflow and truthful interim wording: the job is configured, but no successful remote
   Linux-smoke run is yet claimed.
3. Regenerate the canonical readiness inventory, run all local gates, and obtain independent review
   with Critical `0` and Important `0`.
4. Commit all reviewed local work and non-force push once to `main`.
5. Wait for the exact pushed Portfolio CI run. Both the unchanged Windows full-suite job and the new
   Linux smoke job must finish `success`; a skipped, cancelled, failed, or missing job is not proof.
6. Replace only the interim Linux wording and its exact tests with the observed first-push commit and
   run URL. Regenerate canonical readiness evidence.
7. Repeat all local gates and independent review, commit, and non-force push a second and final time.
8. Require the Portfolio CI run for the final evidence commit to finish `success` with both jobs.
   The final run is closure proof; the checked-in evidence records the preceding exact smoke run to
   avoid a recursive self-reference.

No more than two pushes occur. A failed remote run is preserved and investigated; unchanged bytes
are not retried.

## 6. File boundary

Implementation may modify only:

- `.github/workflows/portfolio-ci.yml`;
- `README.md`;
- `docs/reviewer/quickstart.md`;
- `docs/reviewer/release-evidence.md`;
- `evidence/public/portfolio/local-release-readiness.json`;
- `tests/publication/test_public_release_surface.py`;
- `tests/publication/test_release_workflow.py`.

Process records may add only:

- `docs/superpowers/specs/2026-08-31-mdcp-linux-read-only-smoke-ci-corrective-design.md`;
- `docs/superpowers/plans/2026-08-31-mdcp-linux-read-only-smoke-ci-corrective.md`;
- git-ignored custody files under
  `.superpowers/sdd/2026-08-31-mdcp-linux-read-only-smoke-ci-corrective/`.

No schema, verifier implementation, release workflow, `.gitattributes`, dependency/lock file,
`src/mdcp/**`, model/data fixture, historical evidence, serving path set, formal-worker identity,
local `main`, other worktree, or other repository may change.

## 7. Testing and failure handling

TDD first proves that the current workflow lacks the required Linux job and that the interim/final
documentation contract is absent. The minimal workflow and copy changes then make those tests pass.
Every public-surface byte change is followed by deterministic readiness regeneration.

Local verification requires:

- `uv lock --check`;
- Ruff check and exact-file format checks;
- complete publication/workflow tests;
- public verifier and deterministic reviewer demo;
- reviewer fast path with zero repository mutations;
- focused serving/formal-worker/security tests;
- the complete pytest suite;
- frozen v1, v2, search-source, formal-worker, firewall, and `uv.lock` digests;
- H2 `SEALED_NOT_LOADED` with loaded rows `0`;
- `git diff --check`, exact path audit, and tracked-mutation audit;
- independent review with Critical `0` and Important `0` before each push.

Any failure is handled with systematic debugging inside the exact path boundary. A solution may not
use skip, xfail, selector weakening, wildcard authority, a broader claim, or an out-of-scope file.
If the root cause requires such a change, work stops with preserved evidence.

## 8. Acceptance criteria

The corrective is complete only when:

- local HEAD and remote `main` equal the final evidence commit;
- the final Portfolio CI run is `completed/success`;
- its Windows `verify` job and `Linux read-only smoke (not portability proof)` job both succeeded;
- the checked-in docs name the exact first successful Linux smoke commit and run URL;
- canonical readiness binds the final public-surface bytes and preserves all frozen anchors;
- release-ci runs, tags, GitHub Releases, and the matching container package remain zero;
- the tracked worktree is clean and `.hypothesis/` remains untracked non-source cache;
- no forbidden execution or repository mutation occurred.

The final supported statement is:

```text
PUBLIC_GITHUB_PORTFOLIO_READY
/ WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS
/ LINUX_READ_ONLY_SMOKE_PASS
!= CROSS_PLATFORM_PORTABLE
/ REMOTE_RELEASED
/ PRODUCTION_READY
```
