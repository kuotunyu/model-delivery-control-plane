# MDCP zh-TW Role-to-Evidence Map Design

## Status

Approved for specification on 2026-08-30. This document defines a minimal recruiter-facing
documentation slice; it does not authorize remote publication, data/model execution, or production
claims.

## Goal

Let a Taiwan-based recruiter or interviewer map the repository's verified engineering work to ML,
AI, Computer Vision, and LLM engineering competencies in under 30 seconds, without implying that
the repository implements CV/LLM workloads or production deployment.

## Problem

The current README already explains the system, its actual-versus-designed boundary, and a
deterministic reviewer demo. It does not yet provide a compact role-oriented index that answers:

1. Which job-relevant capability is demonstrated?
2. Where is the implementation or test evidence?
3. What claim is explicitly not being made?

Without that mapping, a non-specialist recruiter must infer the relevance of content-addressed
identity, temporal leakage controls, validation, process isolation, and fail-closed evidence from
several sections and documents.

## Audience and language

- Primary audience: Taiwan recruiters and engineering interviewers for ML Engineer, AI Engineer,
  Computer Vision Engineer, and LLM Engineer roles.
- Primary language: Traditional Chinese (`zh-TW`). Established technical terms remain in English
  where translation would reduce precision.
- This slice is repository documentation, not a resume, cover letter, or English application
  summary.

## Selected approach

Add one concise `## 對應 ML／AI／CV／LLM 職務能力` section to `README.md`, immediately
after `## 目前完成度` and before `## 實際 implemented verification path`.

The section contains a short framing sentence and a four-row table. Each row must identify a
job-relevant competency, link to concrete repository evidence, and state the honest boundary.

| Role-oriented competency | Required concrete evidence | Required boundary |
|---|---|---|
| ML Engineer: workload contract, serving identity, reproducibility | `src/mdcp/contracts`, serving-identity contract tests | Demonstrates the implemented temporal-regression workload only |
| AI Engineer: offline validation and evidence-gated delivery | `src/mdcp/validator`, `src/mdcp/verify`, public readiness evidence | Local verification is not remote release or production evidence |
| Computer Vision / LLM Engineer: transferable delivery controls | content-addressed identity, artifact/evidence validation, claim ceiling | Transferable pattern only; no CV or LLM workload implementation claim |
| MLOps / reliability / security: isolation and fail-closed controls | dedicated formal worker, static firewall, runtime guards, security/process tests | Control/router/canary/rollback/recovery remain designed-only where documented |

The final wording may be tightened during implementation, but it must preserve every competency,
evidence target, and boundary above. It must not add unverifiable performance, scale, production,
deployment, CV, or LLM claims.

## Alternatives considered

### Separate interview guide

A new `docs/reviewer/interview-guide.md` could provide deeper talking points. It was rejected for
this slice because it adds navigation and public-inventory complexity before demonstrating that a
compact README mapping is insufficient.

### New domain demo

A CV or LLM demo would offer stronger domain-specific evidence, but it requires a separate design,
data/model execution authorization, dependency and resource review, and new claim boundaries. It is
explicitly out of scope here.

### No change

The existing README is technically complete, but it leaves the role-to-evidence inference to the
reader. The proposed table is a small, high-leverage improvement with no runtime behavior change.

## Exact implementation scope

The implementation allowlist is exactly:

```text
README.md
evidence/public/portfolio/local-release-readiness.json
tests/publication/test_public_release_surface.py
```

- `README.md`: add only the approved role-to-evidence section and any minimal surrounding spacing.
- `tests/publication/test_public_release_surface.py`: add a focused semantic contract test for the
  heading, four role categories, concrete evidence links, and explicit CV/LLM/local-only boundary.
- `evidence/public/portfolio/local-release-readiness.json`: regenerate canonical bytes because
  `README.md` is an evidence-bound public path.

No schema, verifier, demo, PowerShell wrapper, `.gitattributes`, production source, dependency,
workflow, historical evidence, or identity path may change.

## Data and control flow

1. A reviewer opens the README and sees the role-oriented mapping before the deeper architecture
   path.
2. Each evidence link points to an already tracked source, test, or public-evidence location.
3. The existing public-release verifier checks every Markdown link and the exact public-surface
   inventory.
4. Changing README bytes requires a regenerated README entry and inventory digest in canonical
   readiness evidence.
5. The deterministic reviewer demo and fast path continue to verify the same real baseline and
   fail-closed mutations; no new command is introduced.

## Truthfulness and failure handling

- Existing claim-scanner rules continue to reject unqualified CV, LLM, remote-release, and
  production claims.
- The new test must fail if the four role categories or their explicit boundaries disappear.
- The public verifier must fail on a broken evidence link or stale README inventory entry.
- Canonical readiness regeneration must change only the README entry and derived public inventory
  digest; all unrelated public entries remain byte-identical.
- Any unexpected test, canonicalization, identity, or protected-tree failure stops the change and
  is investigated with systematic debugging.

## Testing strategy

Use TDD for the README contract:

1. Add the focused publication test first and demonstrate RED against the current README.
2. Add the approved README section and demonstrate GREEN.
3. Regenerate readiness and independently compare its bytes with the canonical model output.
4. Run the focused publication/release suite, standalone verifier, deterministic demo, and real
   PowerShell fast path.
5. Run the frozen identity/runtime/security suite, Ruff/static checks, `uv lock --check`,
   `git diff --check`, and the full pytest suite.
6. Obtain independent review of the implementation commit and the aggregate range.

## Preserved invariants

- The nine-path `PUBLIC_SURFACE_PATHS` tuple and schema remain unchanged.
- `uv.lock`, v0.1/v0.2 serving, source, worker, firewall, historical receipt, and historical index
  identities remain unchanged.
- H2 remains `SEALED_NOT_LOADED` with loaded rows `0`.
- The worktree remains local with no remote, push, merge, tag, release, workflow execution,
  dependency installation, network action, or data/model execution.
- The README remains zh-TW-first and does not gain an English resume or application summary.

## Acceptance criteria

- The role map is visible before the detailed implemented verification path.
- All four target role families have concrete, valid evidence links.
- CV/LLM transferability is clearly separated from workload implementation.
- Local verification is clearly separated from remote release and production evidence.
- Exactly the three allowlisted implementation paths change.
- Canonical readiness and all preserved identities verify exactly.
- Focused and full tests pass.
- Independent review reports Critical `0` and Important `0`.
