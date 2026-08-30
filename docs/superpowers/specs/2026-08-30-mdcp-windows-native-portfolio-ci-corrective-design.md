# MDCP Windows-Native Portfolio CI Corrective Design

## Status

- Date: 2026-08-30
- Repository: `kuotunyu/model-delivery-control-plane`
- Current visibility: Private
- Current local publication-branch HEAD and remote `main` commit:
  `1b44a3e001d6522b6409bae24e07740bf053186d`
- Failed Phase A run: `https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512`
- Selected approach: Windows-native full-suite Portfolio CI with an explicit failed-run evidence transition

This corrective supersedes only the `ubuntu-24.04` runner and pre-success evidence-state portions of
`docs/superpowers/specs/2026-08-30-mdcp-safe-github-publication-design.md`. Every release,
production, data/model, P2/H2, repository-ownership, and external-action prohibition from that
design remains binding.

## 1. Problem statement

The first Private staging sequence completed safely:

- the official `gitleaks` 8.30.1 checksums and binary version were verified;
- the complete Git history scan returned zero unresolved findings;
- the repository was created exactly once as Private;
- remote `main` exactly matched reviewed Phase A commit
  `1b44a3e001d6522b6409bae24e07740bf053186d`;
- checkout, locked dependency installation, Ruff, public verifier, and deterministic demo passed;
- the existing release workflow was not dispatched and no tag, release, package command, Docker
  container, merge, force-push, or Public visibility transition occurred.

The Phase A full suite failed on Ubuntu with:

```text
51 failed, 1562 passed, 12 skipped
```

Systematic debugging identified six inherited platform contracts:

1. sixteen historical identity inputs use the repository's established Windows
   `core.autocrlf=true` working-tree bytes, while the Ubuntu checkout materialized LF bytes;
2. the dedicated formal-worker protocol deliberately validates absolute Windows paths and the
   affected process tests construct platform-native temporary paths;
3. retained/private publication primitives are Windows-only and correctly fail closed as
   `PUBLICATION_UNSUPPORTED` on other operating systems;
4. two search-freeze tests depend on Windows `core.fileMode=false` semantics;
5. two Compose config tests correctly require explicit `create_host_path: false`, but the runner's
   older Compose JSON renderer incorrectly omitted an explicitly false value;
6. one golden-vector equality uses the Windows CPython/libm result frozen by the project.

The Ubuntu failures therefore do not show that the reviewed Windows contract is broken. They show
that the original Portfolio CI design accidentally claimed cross-platform portability that this
project neither implements nor documents. Retrying the unchanged run cannot test a new hypothesis.

## 2. Approaches considered

### 2.1 Selected: Windows-native full-suite verification

Run Portfolio CI on `windows-2025`, materialize the same CRLF/file-mode contract before checkout,
retain the complete pytest suite, and make the reviewer documentation explicitly state that this is
a Windows-native verification claim.

This is selected because it verifies the platform the formal worker and publication boundary were
designed for without changing production code, historical identities, formal evidence, serving
identities, or expanding the claim ceiling to cross-platform or release readiness.

### 2.2 Rejected: make the repository fully cross-platform

This would require new canonical byte identities, changes to historical evidence, alternate path
semantics, publication abstractions, file-mode behavior, and float tolerances. It is a separate
engineering program rather than a publication corrective and would risk invalidating already
reviewed security properties.

### 2.3 Rejected: keep Ubuntu but exclude failing tests

This would make the workflow green by weakening the promised complete-suite gate. It would also
hide the platform contract instead of documenting it. No test group is removed, xfailed, or skipped
by the workflow.

## 3. Corrected workflow contract

`.github/workflows/portfolio-ci.yml` remains the sole automatic verification workflow and retains:

- push-only `main` and pull requests targeting `main` triggers;
- top-level `permissions: contents: read` with no job escalation;
- a 30-minute timeout and same-ref concurrency cancellation;
- full-history checkout with `fetch-depth: 0` and `persist-credentials: false`;
- Python 3.12, `uv` 0.11.18, disabled dependency caching, and `uv sync --frozen --group ml`;
- lock, Ruff, exact changed-Python formatting, public verifier, deterministic reviewer demo, complete
  pytest with the cache provider disabled, and tracked-file mutation rejection;
- no secrets, OIDC, upload, attestation, package/GHCR, tag, release, deployment, or write authority.

The corrective changes are exact:

1. use `runs-on: windows-2025`;
2. set job run steps to `shell: pwsh`;
3. before checkout, run only:

   ```powershell
   git config --global core.autocrlf true
   git config --global core.fileMode false
   ```

   This configures the ephemeral runner before repository bytes are materialized. It does not
   rewrite local history or any user checkout.
4. update checkout to official Node24-based `actions/checkout` v7.0.1 commit:

   ```text
   3d3c42e5aac5ba805825da76410c181273ba90b1
   ```

5. retain official `astral-sh/setup-uv` v10.0.1 commit:

   ```text
   20cfd1bf945f4377ade1205e4dbc17946fc9a30d
   ```

6. install official Docker Compose v5.5.0 as an ephemeral CLI plugin from:

   ```text
   https://github.com/docker/compose/releases/download/v5.5.0/docker-compose-windows-x86_64.exe
   ```

   Require exact SHA-256 before use:

   ```text
   51e1e61195f3616896265487ed64551095f3bd27ac7fbd5758d3538c3bfa1b19
   ```

   Install it only under the runner user's temporary `.docker/cli-plugins` directory and require
   `docker compose version --short` to return `5.5.0` before tests.

The exact action tag, commit, and Node24 runtime were read from the official GitHub repository on
2026-08-30. The current official `windows-2025` image manifest lists Windows Server 2025, Git,
Python 3.12, PowerShell, Docker, and Docker Compose. Portfolio CI does not start a daemon, image,
container, network, or volume. The inherited full suite may invoke `docker compose config` only to
render static configuration; that is not a deployment or model/data execution.

## 4. Compose config compatibility

Docker's Compose reference states that `bind.create_host_path` defaults to `true`. Therefore an
empty rendered `bind` object cannot be accepted as equivalent evidence for an explicitly false
value. The existing feasibility tests correctly require:

```json
{"bind":{"create_host_path":false}}
```

The upstream `compose-go` release history records a renderer fix so an explicitly false
`create_host_path` is not omitted. The corrective pins official Docker Compose v5.5.0 and its
GitHub-asset SHA-256 instead of weakening either test.

The workflow may download and checksum only that exact Windows x86-64 Compose binary. It may use
the plugin only for the existing full-suite `docker compose config` calls. It must not log in,
contact a Docker registry, start a daemon, pull/build/run an image, or create a container, network,
or volume. No Compose YAML, feasibility test, production code, image, or dependency file changes.

## 5. Truthful intermediate evidence

The checked-in readiness v1 currently says `push_executed: false`, which was true at its commit but
is no longer current after Private staging. The next corrective commit must not repeat that stale
claim while waiting for a successful replacement run.

Before the next push, evolve the readiness record to a closed intermediate state:

```text
schema_version: mdcp.local-release-readiness.v1.1
evidence_class: github_private_staging_corrective_readiness
claim_ceiling: mdcp.private-staging-corrective-claim-ceiling.v1
portfolio_ci_commit: 1b44a3e001d6522b6409bae24e07740bf053186d
portfolio_ci_run_url: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512
portfolio_ci_conclusion: failure
```

Its execution state is exact:

```text
push_executed: true
portfolio_ci_executed: true
portfolio_ci_passed: false
remote_release_executed: false
tag_created: false
production_deployed: false
kubernetes_production_ready: false
h2_executed: false
cv_workload_implemented: false
llm_workload_implemented: false
```

The commit and run URL use the same constrained 40-hex and repository-specific HTTPS types planned
for final readiness v2. An impossible state such as `portfolio_ci_passed: true` with conclusion
`failure`, a different repository URL, an unknown field, or an affirmative release/production
claim must fail closed.

README and reviewer docs must say that Private staging executed, the recorded Ubuntu run failed,
the failure is not release or portability evidence, and a Windows-native corrective is pending.
They must not display a success badge or imply that the corrective commit has already passed.

## 6. Corrective execution sequence

The sequence is:

1. implement workflow, checksum-pinned Compose CLI setup, exact-contract tests, Windows-native
   documentation, readiness v1.1, schema, and canonical inventory;
2. run focused tests, verifier, demo, fast path, frozen identity/security tests, Ruff, lock check,
   complete local suite, and independent review with Critical `0` and Important `0`;
3. commit with existing identity and non-force push the corrective HEAD to remote `main`;
4. wait for the exact Windows-native Portfolio CI run;
5. if it fails, keep the repository Private, preserve the run, and return to systematic debugging;
6. only after it passes, execute the previously designed final readiness-v2 transition, recording
   the successful corrective commit and canonical run URL;
7. run the same local gate/review, commit, non-force push, and require a second successful
   Windows-native Portfolio CI run;
8. stop before Public visibility unless every final external audit gate is satisfied.

The failed Ubuntu run remains visible and is never deleted or hidden.

## 7. Corrective path allowlist

The corrective implementation may modify only:

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
docs/superpowers/plans/2026-08-30-mdcp-windows-native-portfolio-ci-corrective.md
```

This design spec is committed separately and is not an implementation path.

No `src/mdcp`, `.github/workflows/release-ci.yml`, Docker/Compose configuration, dependency,
`uv.lock`, historical search/formal evidence, serving identity, model/data fixture, local `main`, or
other repository may change.

## 8. Testing and review

Implementation uses TDD and systematic debugging:

- workflow tests first fail on the old Ubuntu runner, Node20 checkout pin, missing pre-checkout Git
  policy, and stale v1 evidence;
- exact workflow-text tests reject added triggers, permissions, actions, network commands, release
  behavior, or weaker test selection;
- readiness tests reject fabricated/alternate run anchors and impossible pass/failure combinations;
- fresh `core.autocrlf=true` checkout tests continue to authenticate all ten public-surface bytes;
- workflow tests pin the exact Compose URL, expected binary SHA-256, plugin destination, version
  check, and config-only/no-container authority boundary;
- all existing full local and frozen identity/security gates remain mandatory;
- every source-changing commit receives independent spec/quality review with Critical `0` and
  Important `0`.

Remote CI is additional evidence and never replaces local verification.

## 9. Package-readback boundary

The current GitHub token can prove release-workflow runs, tags, and GitHub Releases are zero, but the
user package-list endpoint returns HTTP 403 without `read:packages`.

No token-scope change is included in this corrective. Before a final Public visibility transition,
the controller must obtain explicit authorization for a read-only `read:packages` scope or another
independent GitHub-supported readback. Absence of package-producing commands and workflows is useful
negative evidence but does not substitute for the final API readback required by the publication
design.

## 10. Acceptance criteria

The corrective is complete only when:

- local publication-branch HEAD and remote `main` share the reviewed corrective commit;
- the exact Windows-native Portfolio CI run is completed/successful;
- final readiness v2 records that successful corrective commit/run, not the failed Ubuntu run;
- the final readiness-v2 commit also passes Windows-native Portfolio CI;
- workflow permission remains exactly `contents: read` and release CI remains unexecuted;
- tags, GitHub Releases, package publication, GHCR, P2, H2, model/data execution, Kubernetes, and
  production deployment remain absent;
- all frozen serving/source/worker/firewall/search identities remain unchanged;
- the repository remains Private until the package-readback and all original Public-transition
  gates pass.

The truthful supported claim remains:

```text
WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS
!= CROSS_PLATFORM_PORTABLE
!= REMOTE_RELEASED
!= PRODUCTION_READY
```
