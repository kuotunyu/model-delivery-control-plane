# MDCP Safe GitHub Publication Design

## Status

- Date: 2026-08-30
- Owner decision: publish as `kuotunyu/model-delivery-control-plane`
- Final visibility: Public
- Selected approach: Private staging, read-only portfolio CI, evidence correction, then Public
- Current reviewed source HEAD: `ae7581c335715c6c077c8d686bb353483c572334`

This design authorizes publication planning and the gated external sequence defined below. It does
not authorize the existing release workflow, GHCR publication, a tag, a GitHub Release, P2, H2,
data/model execution, Docker execution, or production claims.

## 1. Goal

Publish the complete MDCP repository as a truthful, recruiter-facing GitHub portfolio without
weakening its evidence model. A reviewer must be able to clone the repository, retain the Git
objects required by the historical verifier, run a read-only CI-equivalent path, and distinguish
portfolio CI from a model release or production deployment.

The final public repository is:

```text
https://github.com/kuotunyu/model-delivery-control-plane
```

The repository remains `zh-TW`-first. Established technical terms remain in English when
translation would reduce precision. No English resume or application summary is added.

## 2. Audited starting state

The pre-publication audit established:

- branch `codex/wave0-foundation-feasibility` is clean at the reviewed source HEAD;
- the GitHub CLI is authenticated as `kuotunyu`;
- `kuotunyu/model-delivery-control-plane` does not yet exist;
- the repository has 269 tracked paths and 186 commits at the audited HEAD;
- the current branch is 180 commits ahead of local `main`, with no divergent local-main commits;
- the largest historical blob is approximately 193 KB, so Git LFS is unnecessary;
- no tracked path is an external private-custody container, raw UCI/H2 row, or non-synthetic model
  output; tracked ONNX and CSV test fixtures are synthetic;
- credential-pattern matches are scanner expressions or deliberately constructed security-test
  markers, not credential values;
- the only private-key marker is a non-key test string in
  `tests/security/temporal/test_public_evidence_boundary.py`;
- commit authors use the expected GitHub noreply identity;
- v1/v2 serving, source, worker, firewall, receipt, and index identities are frozen and verified;
- H2 remains `SEALED_NOT_LOADED` with loaded rows `0`.

The complete history must be published. Squashing or starting a new orphan history is prohibited
because `scripts/verify-public-release.py` authenticates historical closure objects and direct
parent topology.

Before repository creation, repeat the audit with a checksum-verified, pinned official `gitleaks`
binary against the complete `--all` Git history. Use redacted terminal output, write no report into
the repository, and require zero unresolved findings. Scanner rules and synthetic credential-test
markers may be allowlisted only by exact path and exact finding after manual inspection; a wildcard
or repository-wide exclusion is prohibited.

## 3. Approaches considered

### 3.1 Selected: Private staging, CI, evidence correction, Public

Create the target repository as Private, push the complete history to remote `main`, run a new
read-only portfolio CI, record the already-completed push and CI in a later evidence commit, verify
that final commit remotely, and only then change visibility to Public.

This is selected because no unverified remote checkout becomes public and the final repository does
not retain the false statement that no push or remote CI has occurred.

### 3.2 Rejected: direct Public push

This is faster, but it exposes the repository before the GitHub-hosted checkout and CI path are
known to pass. It also creates a period in which the current `push_executed: false` evidence is
publicly stale.

### 3.3 Rejected: Public without portfolio CI

This avoids workflow implementation but gives recruiters weaker evidence and leaves the existing
manual release workflow as the only visible Actions entry point. That workflow has write
permissions and must not be mistaken for ordinary verification CI.

## 4. Two workflows with separate authority

### 4.1 Portfolio CI

Add `.github/workflows/portfolio-ci.yml` as the default verification workflow.

Its contract is:

- triggers only on pushes to remote `main` and pull requests targeting `main`;
- top-level `permissions` grants only `contents: read`;
- no job or step may add write permission;
- uses `ubuntu-24.04` and a bounded timeout;
- checks out full history with `fetch-depth: 0`;
- every third-party action is pinned to an exact full commit SHA;
- dependency setup uses the checked-in `uv.lock` and Python 3.12;
- network is allowed only for runner setup and dependency acquisition;
- verification commands use `--no-sync` after setup;
- runs `uv lock --check`, Ruff, public-release verification, reviewer demo, and the complete pytest
  suite with the cache provider disabled;
- does not use repository or environment secrets;
- does not use Docker, GHCR, attestations, OIDC, package publication, artifact upload, tags, or
  releases;
- does not mutate tracked repository files.

The workflow may use a concurrency group that cancels superseded verification runs for the same
branch or pull request. Dependency caching is disabled in the first publication slice to reduce
implicit state and permissions.

### 4.2 Existing release CI

`.github/workflows/release-ci.yml` remains manual `workflow_dispatch` source for inspection only.
It retains its existing GHCR and attestation design, but this publication must not dispatch it.

Portfolio CI success means only:

```text
REMOTE_PORTFOLIO_CI_PASS != REMOTE_RELEASED != PRODUCTION_READY
```

## 5. Public-surface integration

The portfolio workflow becomes an evidence-bound public path rather than an untracked GitHub UI
detail.

The implementation must:

- grow `PUBLIC_SURFACE_PATHS` from nine to ten entries by adding
  `.github/workflows/portfolio-ci.yml` in exact UTF-8 byte order;
- pin the workflow as `text eol=lf` in `.gitattributes`;
- add exact workflow contract and mutation tests;
- update README, reviewer quickstart, and release-evidence taxonomy so portfolio CI and release CI
  are visibly separate;
- regenerate canonical public-surface inventory evidence;
- preserve the historical formal closure and all serving/source/worker/firewall identities.

The readiness evidence itself remains outside `PUBLIC_SURFACE_PATHS` to avoid self-inventory.

## 6. Evidence state transition

### 6.1 Phase A: pre-push readiness

The first implementation commit adds the portfolio workflow and updates the nine-to-ten-path public
inventory while the repository is still local. At that point these statements remain true:

- `push_executed: false`;
- portfolio CI is configured but not remotely executed;
- `remote_release_executed: false`;
- `tag_created: false`;
- `production_deployed: false`.

All local tests, verifier checks, and independent review must pass before any remote is created.

### 6.2 Phase B: private staging execution

After the Phase A gate:

1. create `kuotunyu/model-delivery-control-plane` as Private;
2. add the exact HTTPS origin;
3. push local `HEAD` to `refs/heads/main`, preserving all reachable history;
4. set remote `main` as the default branch;
5. wait for the exact Phase A portfolio-CI run;
6. inspect its conclusion and logs.

Any failure leaves the repository Private. Fixes follow systematic debugging, repeat the complete
local gate, and then push a new scoped commit. The process never deletes the remote automatically,
force-pushes, rewrites history, or falls through to Public after a failed or missing run.

### 6.3 Phase C: post-push readiness v2

Only after Phase A portfolio CI passes, evolve the readiness contract to a closed v2 document that
records already-observed facts:

- `claim_execution.push_executed: true`;
- `claim_execution.portfolio_ci_executed: true`;
- top-level `portfolio_ci_commit` containing the exact verified Phase A commit SHA;
- top-level `portfolio_ci_run_url` containing the canonical GitHub Actions run URL;
- `remote_release_executed: false`;
- `tag_created: false`;
- all production, Kubernetes, H2, CV-workload, and LLM-workload booleans remain `false`.

The v2 schema and verifier must reject a CI claim without a 40-hex commit, an HTTPS run URL under
`github.com/kuotunyu/model-delivery-control-plane/actions/runs/`, and both executed booleans set to
their exact values. The record binds the prior completed CI run; it does not claim to authenticate
the run that validates its own commit.

The existing `publication_status: "public"` continues to classify the checked-in public evidence
surface; it is not a statement about GitHub repository visibility. Remote visibility is verified
from GitHub after the Phase C gate and is not predicted by committed evidence.

README and evidence taxonomy may state that remote portfolio CI passed for the recorded commit.
They must continue to say that release CI, GHCR publication, tag creation, H2, and production
deployment did not occur.

Phase C receives the same focused/full/static/independent-review gate, is pushed to remote `main`,
and must pass portfolio CI a second time.

### 6.4 Phase D: visibility transition

Only after the Phase C run passes:

1. change repository visibility from Private to Public;
2. set the exact repository description to
   `Evidence-gated model delivery reference implementation with content-addressed identity, temporal controls, and fail-closed verification.`;
3. set exactly these topics: `mlops`, `model-delivery`, `machine-learning`, `ai-engineering`,
   `onnx`, and `supply-chain-security`;
4. verify unauthenticated access to the repository and README;
5. verify remote default branch `main` points to the Phase C commit;
6. verify the successful portfolio-CI run remains visible;
7. verify release count, package publication, HEAD tags, and release-workflow runs remain zero.

No post-publication tag, release, package, GHCR image, or release-workflow dispatch is part of this
design.

## 7. Local and remote branch handling

The local linked worktree remains on `codex/wave0-foundation-feasibility`. Local `main` is not
checked out, merged, reset, deleted, or force-updated.

The publication push maps the reviewed local HEAD directly to remote `main`:

```text
codex/wave0-foundation-feasibility HEAD -> origin/main
```

This preserves the full history without mutating the shared local-main checkout. The local branch
may track `origin/main`; its local name does not have to equal the remote default-branch name.

## 8. Failure handling

Publication fails closed when:

- GitHub authentication is not the `kuotunyu` account;
- the target repository unexpectedly exists before creation;
- the local worktree is dirty or HEAD differs from the reviewed commit expected by the current
  phase;
- a secret, private path, unexpectedly large object, or unknown author is found;
- the pinned full-history `gitleaks` preflight has an unresolved finding or cannot verify its tool
  checksum;
- a workflow action is not fully SHA-pinned;
- portfolio CI requests write permissions or references secrets;
- checkout is shallow;
- the verifier, demo, Ruff, lock, focused tests, full suite, or independent review fails;
- a GitHub Actions run is missing, cancelled, timed out, or not successful;
- post-push evidence does not match the observed commit and run URL;
- the final visibility or anonymous-read verification fails.

On any remote-stage failure, preserve the Private repository and local worktree for diagnosis. Do
not delete, recreate, force-push, make Public, or dispatch release CI as an automatic recovery.

## 9. Testing strategy

Implementation uses TDD. Workflow tests must first demonstrate RED for the absent portfolio CI and
then cover at least:

- exact push/pull-request triggers and no release/tag/manual trigger;
- exact `contents: read` authority and absence of write permissions;
- full-history checkout;
- full-SHA action pins;
- locked setup followed by no-sync verification;
- verifier, demo, Ruff, lock, and full-suite commands;
- absence of secrets, Docker, GHCR, OIDC, uploads, releases, and tracked-file mutation;
- inclusion in the ten-path public inventory and LF contract;
- readiness v1 pre-push and v2 post-push state contracts;
- rejection of a fabricated CI URL, mismatched commit, impossible boolean combination, unknown
  field, stale public inventory, or affirmative release/production/H2/CV/LLM claim.

Every source-changing phase requires:

- focused publication/workflow tests;
- standalone public verifier and deterministic reviewer demo;
- reviewer fast path;
- frozen identity/runtime/security tests;
- complete pytest suite;
- Ruff and exact changed-Python format checks;
- `uv lock --check` and `git diff --check`;
- independent review with Critical `0` and Important `0`;
- clean, scoped commits using the existing author/committer identity.

Remote CI output is additional evidence. It never replaces local full-suite and review gates.

## 10. Planned implementation scope

The implementation plan may authorize only these repository paths:

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
docs/superpowers/plans/2026-08-30-mdcp-safe-github-publication.md
```

The plan itself is committed separately and is not an implementation path. No `src/mdcp`,
dependency, serving-identity path, historical search evidence, formal evidence, model/data fixture,
Docker, Compose, or release-workflow path may change.

## 11. External action scope

After written-spec and implementation-plan approval, the external-action allowlist is exactly:

- create one Private repository named `kuotunyu/model-delivery-control-plane`;
- download and execute one checksum-verified official `gitleaks` binary in an OS-managed temporary
  directory for the pre-creation full-history audit;
- add its HTTPS URL as `origin` in this repository;
- push the reviewed branch HEAD to remote `main` without force;
- read and wait for portfolio-CI runs;
- push scoped corrective/evidence commits to remote `main` without force;
- change that repository from Private to Public after all gates pass;
- set its description and topics;
- read back repository, Actions, tags, releases, and packages state for verification.

It does not include deleting or renaming a repository, force-push, merge, tag, GitHub Release,
package/GHCR publication, release-workflow dispatch, billing changes, organization changes, secrets,
branch-protection changes, or any other repository.

## 12. Acceptance criteria

The publication is complete only when:

- the public URL resolves without authentication;
- remote `main` contains the complete historical closure topology and the final reviewed commit;
- portfolio CI passes on the final public bytes;
- canonical readiness v2 truthfully records the prior push and portfolio-CI run;
- public verifier and reviewer demo pass from the final checkout;
- release CI remains unexecuted;
- tags, GitHub Releases, packages, GHCR publication, P2, H2, data/model execution, and production
  deployment remain absent;
- all frozen identities and H2 sealed/zero state remain unchanged;
- the local worktree is clean and no other repository was modified.

The final supported claim is:

```text
PUBLIC_GITHUB_PORTFOLIO_READY / REMOTE_PORTFOLIO_CI_PASS
!= REMOTE_RELEASED / PRODUCTION_READY
```
