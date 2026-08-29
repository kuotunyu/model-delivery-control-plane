# MDCP Recruiter-Facing Public Release Slice Design

- Status: approved for written specification by owner delegation
- Date: 2026-08-30
- Audience: ML Engineer, AI Engineer, Computer Vision Engineer, LLM Engineer, and technical recruiters
- Primary language: 正體中文 (`zh-TW`), with established technical terms kept in English
- Repository profile: local Git history only; no remote creation, push, tag, GitHub Release, or package publication

## 1. Purpose

This slice turns the existing Model Delivery Control Plane repository into a truthful, low-friction
portfolio entry without expanding the production system. A reviewer should be able to answer these
questions quickly:

1. What model-delivery problem does this project solve?
2. Which capabilities are implemented and verified now?
3. Which capabilities exist only as approved architecture or future work?
4. What can the reviewer reproduce locally without data, GPU, Docker, or network access?
5. Which evidence proves the repository's strongest claims?

The public surface must make one central idea clear: a better offline metric is not deployment
permission. Immutable identity, validation, isolation, evidence completeness, and fail-closed gates
must authorize model delivery.

The implemented example workload is temporal bike-demand regression. The controls are relevant to
ML, AI, CV, and LLM delivery, but the repository must not claim that a CV or LLM application has
been implemented.

## 2. Design choice

### 2.1 Selected approach: evidence-first

The selected approach leads with a concise README, then offers actual architecture, a tiered
reviewer path, and machine-verifiable public readiness evidence. The slice adds only documentation,
publication tooling, evidence, and tests. It does not modify `src/mdcp`, model artifacts, runtime
configuration, the formal worker, serving identities, or frozen temporal evidence.

This approach is preferred because it gives recruiters a short path to verified engineering depth
while keeping every claim auditable.

### 2.2 Rejected alternatives

- **Architecture-first:** rejected because the complete v0.1 design is larger than the implemented
  repository surface and could blur the line between implemented and planned behavior.
- **Demo-first:** rejected because a new UI, control-plane demo, or Docker scenario would expand the
  product and validation scope instead of producing a minimal public release slice.

## 3. Claim contract

### 3.1 Permitted claims

The public surface may describe the repository as demonstrating:

- content-addressed model and source identity;
- strict workload and schema contracts;
- offline artifact and release-bundle validation;
- deterministic synthetic reviewer fixtures;
- temporal leakage and development-protocol controls;
- a dedicated formal worker with bounded process transport;
- fail-closed public/private evidence boundaries;
- static and behavioral H2 firewalls;
- immutable search-source freeze and independently recoverable custody;
- locally reproducible tests and evidence verification.

### 3.2 Required qualifiers

The public surface must say that:

- the implemented workload is temporal regression, not CV or LLM inference;
- the technical formal closure is the immutable historical commit
  `b1bb0d80cd40e6f39372c0a45892500cc9530712`;
- later publication-only commits do not redefine that commit as the current freeze HEAD;
- H2 remains `SEALED_NOT_LOADED` with loaded rows `0`;
- the checked-in GitHub Actions workflow has not been executed as a remote release in this slice;
- local and synthetic PASS evidence is not production evidence.

### 3.3 Prohibited claims

The public surface must not claim:

- Kubernetes production readiness;
- production HA, disaster recovery, or multi-region operation;
- a completed remote GitHub/GHCR release;
- real production incident evidence;
- H2 execution or confirmatory results;
- a completed end-to-end control service, router, canary, rollback, or recovery deployment;
- a CV or LLM workload implementation;
- generic support for arbitrary model frameworks or tasks.

## 4. Public components

### 4.1 Root README

`README.md` is written primarily in `zh-TW`. Established terms such as `fail-closed`,
`content-addressed identity`, `dedicated worker`, `release evidence`, `shadow`, `canary`, and
`custody` remain in English when translation would reduce precision.

The first line is the machine-checkable comment `<!-- lang: zh-TW -->`; it is not displayed by
GitHub but makes the language contract deterministic.

The README contains, in this order:

1. a one-sentence value proposition;
2. a short recruiter-oriented explanation of the engineering problem;
3. a compact status table distinguishing implemented, verified, designed, and not executed;
4. a small actual architecture diagram;
5. the three-tier reviewer path;
6. links to architecture, reviewer, threat-model, evidence, workflow, and license documents;
7. an explicit claim ceiling and exclusions;
8. a concise technology and test summary.

The README must remain skimmable. Detailed protocol history and long corrective narratives remain in
the existing specifications and plans.

### 4.2 Actual architecture document

`docs/architecture.md` describes the repository that exists, not only the intended full platform.
It contains two visibly separate diagrams or sections:

- **Implemented verification path:** workload contracts and source bytes flow through identity,
  validation, formal worker/firewall, and public evidence.
- **Designed deployment path:** control service, router, shadow/canary, rollback, recovery, and
  observability are labeled as designed or incomplete where no end-to-end implementation exists.

The document includes a component matrix with `Implemented`, `Verified locally`, `Designed only`,
and `Not executed remotely` states.

### 4.3 Reviewer guide

`docs/reviewer/quickstart.md` defines three levels:

1. **Fast path:** `uv`, Python 3.12, CPU-only, no Docker, no dataset, no model execution, and no
   network during verification. Warm execution target is 3–5 minutes; dependency installation time
   is reported separately.
2. **Full test path:** the complete test suite, with the most recently measured duration stated as
   historical guidance rather than a guarantee.
3. **Architecture/deep path:** optional Docker, validator, threat model, and release-workflow
   inspection. It must not imply that the workflow was remotely executed.

The fast path is a PowerShell entry point at `scripts/reviewer-fast-path.ps1`. It invokes only
offline publication verification and a curated test set. It prints one stable PASS terminal and
returns nonzero on any failed command.

The guide also lists the same underlying `uv` commands individually so a reviewer without
PowerShell can run the path from any shell supported by the repository. The PowerShell wrapper is a
convenience entry point, not a second implementation of verification logic.

### 4.4 Release-evidence guide

`docs/reviewer/release-evidence.md` explains the evidence taxonomy and links to the machine-readable
record. It distinguishes:

- historical formal closure evidence;
- local portfolio readiness evidence;
- synthetic fixture evidence;
- designed remote release-CI evidence;
- evidence that does not exist because the corresponding action was not authorized or executed.

### 4.5 License

The repository uses the MIT License with copyright attributed to `kuotunyu` for 2026. MIT is
selected for a portfolio repository because it is concise, recognizable, and imposes minimal reuse
friction. The license does not convert any third-party dataset or dependency into project-owned
material; their own terms continue to apply.

## 5. Machine-readable local readiness evidence

### 5.1 Evidence file

`evidence/public/portfolio/local-release-readiness.json` is canonical RFC 8785 JSON with no BOM or
terminal newline. It is public and contains no absolute paths, credentials, raw environment,
private custody paths, or exception text.

Its closed fields record:

- schema and canonicalization versions;
- evidence class `local_portfolio_release_readiness`;
- publication status `public`;
- technical formal-closure commit and its exact parent topology;
- search source, receipt, index, worker, serving, and firewall identities;
- an exact ASCII-ordered public-surface inventory and its canonical digest, covering README,
  license, architecture, reviewer guides, verifier, fast-path wrapper, and evidence schema while
  excluding the readiness evidence itself;
- H2 sealed/unloaded state;
- fresh test and independent-review counts;
- repository-relative `reviewer_entrypoint`;
- booleans for remote release, push, tag, production, Kubernetes, H2, CV workload, and LLM workload;
- a fixed claim-ceiling identifier.

The record binds the already completed technical closure. It does not include its own Git commit and
does not claim to be a GitHub Release.

### 5.2 Schema

`schemas/portfolio/local-release-readiness.schema.json` is a closed JSON Schema. It forbids unknown
fields and constrains every status, digest, commit, counter, and boolean. All non-executed claims are
represented explicitly, not omitted.

No new validation dependency is added. The verifier uses an exact closed Pydantic model from the
already locked runtime dependencies and separately requires the checked-in JSON Schema's field,
type, enum, pattern, and closed-object contract to describe the same evidence surface. Publication
tests exercise both representations and reject drift between them.

## 6. Publication verifier

`scripts/verify-public-release.py` is a reviewer utility, not production runtime code. It performs
read-only checks against a repository root:

1. require every documented public entry point to exist as a regular non-link file;
2. parse and schema-validate the readiness evidence;
3. require canonical JSON bytes;
4. run the existing public-evidence scanner and require zero violations;
5. authenticate the historical formal-closure commit, its direct parent, and the separate D/D and
   A/A evidence topology from Git objects;
6. recompute exact public receipt and index hashes from the historical closure commit;
7. require the closure commit to be an ancestor of the current publication branch;
8. recompute the exact public-surface file inventory and canonical digest;
9. require the declared H2 and claim-ceiling fields;
10. validate that README and reviewer links resolve inside the repository;
11. print `PUBLIC_RELEASE_SLICE_PASS` only after all checks pass.

The verifier must not require the current HEAD to equal the historical freeze commit. That would be
incorrect after documentation-only publication commits. It must not read external private custody,
access data/model rows, invoke the formal producer, use network, or mutate Git.

Errors use fixed reason codes and never echo a supplied absolute path or file contents.

## 7. Data and trust flow

The publication flow is:

```text
historical formal closure Git objects
        +
public receipt/index identities
        +
closed claim-ceiling fields
        |
        v
canonical local-readiness evidence
        |
        v
read-only publication verifier
        |
        +--> fast-path curated tests
        |
        v
PUBLIC_RELEASE_SLICE_PASS
```

Private custody remains external and is mentioned only by public-safe digest when necessary. The
public verifier proves Git-object and public-evidence facts; it does not downgrade the private
custody boundary.

## 8. Failure behavior

The fast path and verifier fail closed on:

- missing or linked public files;
- invalid, noncanonical, or schema-incomplete readiness evidence;
- unknown fields;
- identity or Git-topology drift;
- a missing historical closure ancestor;
- public-evidence disclosure;
- a broken or repository-escaping documentation link;
- a claim boolean that implies unexecuted remote, production, H2, CV, LLM, or Kubernetes evidence;
- any failed curated test command.

The verifier returns a fixed `PUBLIC_RELEASE_SLICE_*` reason code and a nonzero exit status. It does
not attempt repair, retry a producer, contact a remote, or change files.

## 9. Testing strategy

Implementation follows TDD. New tests under `tests/publication/` must first fail because the public
surface does not yet exist. Tests cover:

- exact required file inventory;
- README language marker and required sections;
- internal Markdown links and repository-relative safety;
- required honest exclusions and absence of prohibited affirmative claims;
- strict schema and canonical evidence;
- every evidence digest and count;
- exact public-surface inventory membership, ordering, file identities, and digest;
- historical commit ancestry and separate D/D/A/A topology;
- verifier PASS on the repository;
- mutations for missing file, link escape, wrong digest, wrong parent, noncanonical JSON, disclosure,
  unknown field, and false executed/production claims;
- PowerShell fast-path command ordering and fail-fast behavior;
- no changes to `src/mdcp`, serving identity paths, temporal source identity, frozen evidence, or
  dependency lock.

Completion requires:

- focused publication tests pass;
- the fast path passes within the warm 3–5 minute target;
- the full suite passes;
- Ruff and formatting pass for new Python/test files;
- Markdown links and JSON schema/evidence pass;
- `uv lock --check` and `git diff --check` pass;
- an independent code review reports Critical 0 and Important 0;
- local commit history is clean and scoped.

## 10. Planned file scope

The implementation plan may modify or add only:

```text
README.md
LICENSE
docs/architecture.md
docs/reviewer/quickstart.md
docs/reviewer/release-evidence.md
scripts/reviewer-fast-path.ps1
scripts/verify-public-release.py
schemas/portfolio/local-release-readiness.schema.json
evidence/public/portfolio/local-release-readiness.json
tests/publication/test_public_release_surface.py
docs/superpowers/plans/2026-08-30-mdcp-recruiter-public-release.md
```

This design specification is committed separately before the implementation plan and is not part of
the implementation allowlist above.

No `src/mdcp`, dependency, model, workload, runtime, existing evidence, workflow, Docker, Compose,
or private custody path may change.

## 11. Commit and release boundary

The work uses a short, reviewable local history:

1. design specification commit;
2. implementation plan commit;
3. one or more scoped TDD implementation commits;
4. final review correction commit only if needed.

There is no history rewrite. Existing corrective, evidence, and custody history remains reachable.
The work must not create a remote, push, merge, tag, publish a package, create a GitHub Release, or
execute the release workflow. A future external publication action requires separate authorization.

## 12. Acceptance result

The slice is complete when a reviewer can clone the repository, read a truthful `zh-TW` overview,
understand actual versus designed architecture, run the CPU-only fast path, and receive
`PUBLIC_RELEASE_SLICE_PASS` backed by canonical local evidence and tests.

The terminal claim is `LOCAL_PORTFOLIO_RELEASE_READY`, not `PRODUCTION_READY` or `REMOTE_RELEASED`.
