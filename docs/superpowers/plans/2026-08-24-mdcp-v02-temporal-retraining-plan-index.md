# MDCP v0.2 Temporal Retraining Implementation Plan Suite

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved v0.2 causal temporal retraining protocol through a sealed,
evidence-gated development path that stops before any real H2 access.

**Architecture:** Reuse the existing `mdcp.workload`, `mdcp.policy.cluster_bootstrap`,
`mdcp.predictor`, `mdcp.validator`, and `mdcp.feasibility` code. Add one focused
`mdcp.temporal` package for the v2 envelope/adapter, development protocol, search identity,
finalization, freeze, and H2 authorization state. Raw rows, predictions, models, MLflow state, and
private receipts remain Git-external.

**Tech Stack:** Python 3.12, Pydantic v2, pandas, NumPy 2, scikit-learn 1.7, ONNX,
ONNX Runtime, skl2onnx, MLflow, RFC 8785, PostgreSQL/psycopg, FastAPI, pytest, Hypothesis,
Docker Compose, and existing Linux cgroup v2 probes. CPU only; no new dependency is planned.

## Global Constraints

- Normative source: `docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md`
  at approved content commit `dc4ff73cc407ce0a903a6c16b4637f2404c0113f` and SHA-256
  `44e14c7fa4ab4fe3717d50a6f2909229fa5832fef56c786aaf10b8c6c0daa04c`. The
  approval-status commit may change metadata only.
- H1 is `OBSERVED_DEVELOPMENT_ONLY`. It is neither blind nor confirmatory.
- H2 stays `SEALED_NOT_LOADED` with `h2_loaded_rows=0` throughout Waves 0–6.
- Real H2 unseal, row loading, stable/candidate inference, and confirmatory evaluation are absent
  from every executable command in this suite.
- Accepted local time is exactly
  `[2011-01-01 00:00:00, 2013-01-01 00:00:00)` in `America/New_York`.
- The v2 model schema has exactly 18 ordered fields and the formulas in spec §4.2. No task may
  introduce `yr`, `dteday`, `instant`, `casual`, `registered`, or `cnt` as model input.
- Development folds are exactly F1–F4 from spec §5; validation ends at
  `2012-07-01 00:00` and never crosses into H2.
- The formal table is exactly 20 trials: one ineligible control and 19 eligible candidates.
  `random_state=2026`, one estimator thread, `PCG64(2026)`, and at most 85 fits are immutable.
- The serial formal process has a 4 GiB peak-resident-memory budget and a six-hour monotonic
  wall-clock budget; exceeding either yields `UNKNOWN/COMPUTE_BUDGET_EXCEEDED`.
- Quality gates remain overall point/UCB95 `<= 0.97` and every fixed subgroup point/UCB95
  `<= 1.05`, with seven fixed subgroups and `n >= 100`.
- Bootstrap remains 2,000 paired calendar-day cluster replicates with zero-based nearest-rank
  element 1,899.
- Adapter completeness, stable prediction completeness, and candidate prediction completeness
  each equal 100% before label-only missingness handling. A missing, duplicate, invalid, or
  unaccounted identity makes the whole trial or H2-shaped synthetic gate `UNKNOWN`.
- Qualification precedes ranking. Only rank one is provisional; only it is replayed. Replay
  `FAIL`/`UNKNOWN` yields `UNKNOWN/NO_ELIGIBLE_CANDIDATE` with no rank-two fallback.
- Formal model selection has no network, paid API, GPU, Docker socket, repository-history write
  capability, or H2 capability.
- Raw UCI data, H2 rows, labels, predictions, native models, ONNX artifacts, MLflow state,
  PostgreSQL runtime state, and private evidence stay under ignored Git-external roots.
- Public files contain no credential, username, hostname, absolute private path, raw exception,
  raw environment dump, container ID, or opaque private payload.
- Any `FAIL` or `UNKNOWN` is preserved and stops the dependent path. It never authorizes another
  trial, seed, dataset, candidate, threshold, subgroup, feature, or retry.
- Git author and committer for every future commit are
  `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`.

---

## Suite and task inventory

| Wave | Plan | Tasks | Entry gate | Completion state |
|---:|---|---:|---|---|
| 0 | `2026-08-24-mdcp-v02-wave-0-temporal-foundation.md` | 4 | New owner execution approval bound to this plan-suite commit | `V02_W0_FOUNDATION_PASS` |
| 1 | `2026-08-24-mdcp-v02-wave-1-adapter-routing-firewall.md` | 6 | W0 immutable constants/config/test-harness identities | `V02_W1_ADAPTER_FIREWALL_PASS` |
| 2 | `2026-08-24-mdcp-v02-wave-2-development-protocol.md` | 6 | W1 development-only rows and v2 envelope identities | `V02_W2_PROTOCOL_PASS` |
| 3 | `2026-08-24-mdcp-v02-wave-3-formal-development.md` | 5 | W2 PASS; separate owner approval before the formal 20-trial run | `FINAL_DEVELOPMENT_WINNER` or terminal `NO_ELIGIBLE_CANDIDATE` |
| 4 | `2026-08-24-mdcp-v02-wave-4-final-feasibility.md` | 5 | Replay-verified winner plus owner checkpoint | `V02_W4_FEASIBILITY_PASS` |
| 5 | `2026-08-24-mdcp-v02-wave-5-freeze-h2-ready.md` | 5 | W4 PASS plus owner checkpoint before candidate freeze | `CANDIDATE_FROZEN / H2_SEALED` |
| 6 | `2026-08-24-mdcp-v02-wave-6-synthetic-h2-verification.md` | 4 | Exact candidate-freeze identity; production bytes unchanged | `H2_UNSEAL_READY / H2_SEALED_NOT_LOADED` |

Total planned tasks: **35**.

## Critical path and bounded parallelism

The cross-wave critical path is strictly:

`W0 -> W1 -> W2 -> W3 source/freeze -> owner formal-run approval -> W3 formal run/replay
-> owner final-refit checkpoint -> W4 -> owner candidate-freeze checkpoint -> W5 -> W6`

No wave completion overlaps its predecessor. Within a wave, only these CPU-only, non-mutating,
non-shared-state test/doc lanes may run in parallel:

- after W1 Task 1.1 freezes types, adapter golden-vector tests (1.2) and development-data firewall
  tests (1.4) may be authored independently, but their commits are integrated serially;
- after W2 Task 2.2 freezes family builders, converter qualification tests (2.3) and completeness
  property tests (2.4) may run independently against separate temporary directories;
- after W6 Task 6.1 freezes synthetic fixtures, concurrency tests (6.2) and claim/security tests
  (6.3) may run independently.

No model fit, formal execution, Git freeze, or evidence aggregation is parallelized.

## Planned file ownership

This is a responsibility map, not permission to create files early.

| Path | First owner | Responsibility |
|---|---|---|
| `src/mdcp/temporal/constants.py` | W0.1 | Immutable v2 time, feature, subgroup, fold, seed, and budget constants |
| `configs/workload/temporal-development-v2.json` | W0.2 | Canonical exact folds/trials/quality protocol |
| `schemas/v2/temporal-development.schema.json` | W0.2 | JSON contract for that protocol |
| `tests/temporal_fixtures.py` | W0.3 | Synthetic 2011/H1-shaped rows only; zero UCI/H2 payload |
| `src/mdcp/contracts/workload.py` | W1.1 | Existing v1 plus strict `BikeRequestV2` envelope |
| `schemas/v2/bike-request.schema.json` | W1.1 | Checked-in v2 request schema |
| `src/mdcp/temporal/adapter.py` | W1.2 | Strict timestamp validation and exact 18-field vector |
| `src/mdcp/temporal/routing.py` | W1.3 | Legacy/v2/invalid admission classification |
| `src/mdcp/workload/dataset.py`, `src/mdcp/workload/splits.py` | W1.4 | Bounded 13,003-row development loader; no H2 parsing |
| `src/mdcp/workload/features.py` | W1.5 | v1 and exact v2 feature-lineage audits |
| `src/mdcp/temporal/folds.py` | W2.1 | Four rolling folds and source-row inventories |
| `src/mdcp/temporal/trials.py` | W2.2 | Exact 20 trial specs and estimator factories |
| `configs/policy/onnx-operators-v2.json` | W2.3 | Hand-reviewed v2 converter operator allowlist |
| `configs/policy/validation-v2.json` | W2.3 | Exact v2 schema, input, output, and operator validation policy |
| `src/mdcp/temporal/completeness.py` | W2.4 | Adapter/prediction/label identity accounting |
| `src/mdcp/temporal/evaluation.py` | W2.5 | Fold/pooled quality and qualification |
| `src/mdcp/temporal/selection.py` | W2.6 | Lexicographic ranking and no-fallback replay decision |
| `src/mdcp/temporal/search_identity.py` | W3.1 | Search receipt and exact-parent/allowlist preflight |
| `schemas/v2/search-receipt.schema.json` | W3.1 | Canonical search receipt contract |
| `src/mdcp/temporal/runner.py`, `src/mdcp/temporal/cli.py` | W3.2 | Bounded formal development execution and fit ledger |
| `evidence/public/v02/search/*.json` | W3.3 | Search receipt and approved immutable evidence index only |
| `src/mdcp/temporal/finalize.py` | W4.1 | Exact final refit and lineage receipt |
| `src/mdcp/workload/onnx_export.py` | W4.2 | Existing export plus 18-input temporal export |
| `src/mdcp/predictor/runtime.py`, `src/mdcp/predictor/app.py` | W1/W4 | Admission-aware serving and selected-model runtime |
| `src/mdcp/contracts/release.py` | W4.3/W5.1 | v2 descriptor and freeze-manifest types |
| `compose.temporal-feasibility.yaml` | W4.4 | Internal-network CPU/load/cgroup feasibility profile |
| `src/mdcp/temporal/freeze.py` | W5.1 | Candidate manifest identity and freeze preflight |
| `schemas/v2/temporal-freeze-manifest.schema.json` | W5.1 | Candidate freeze schema |
| `src/mdcp/temporal/h2_state.py` | W5.2 | One-shot state reducer and typed receipts |
| `src/mdcp/temporal/h2_ledger.py` | W5.2 | Atomic PostgreSQL consume-before-read ledger |
| `src/mdcp/temporal/h2_guard.py` | W5.3 | Injected row-source protocol; no real H2 binding |
| `tests/fixtures/temporal/synthetic-h2-cases.json` | W6.1 | Explicit `synthetic_test` PASS/FAIL/UNKNOWN cases |
| `evidence/public/v02/h2-readiness-report.json` | W6.4 | Sanitized synthetic-only readiness aggregate |

No other large framework, workflow, cloud resource, deployment stack, or dependency is planned.

## Immutable handoffs

| From | Handoff |
|---:|---|
| W0 | Constants digest, development-config digest, schema digest, synthetic-fixture generator digest |
| W1 | v2 schema/adapter/golden-vector digests, admission truth table, 13,003-row development identity, H2-firewall receipt |
| W2 | Fold/trial/operator-policy/statistical-code digests, completeness properties, deterministic synthetic dry-run receipt |
| W3 | `SEARCH_SOURCE_COMMIT`, `SEARCH_FREEZE_COMMIT`, search-receipt digest, 20-trial summary, qualification/ranking receipt, sole replay receipt |
| W4 | Final training/MLflow/native/ONNX/parity/descriptor/image/load/cgroup/validator/supply-chain digests |
| W5 | Candidate source commit, candidate freeze commit, freeze-manifest digest, H2 ledger/schema/preflight identities |
| W6 | Synthetic state-machine report bound to the candidate freeze; H2 remains sealed and unloaded |

## Owner checkpoints and stop rules

| Checkpoint | Required evidence | Authorized next action |
|---|---|---|
| P0 plan-suite review | This exact plans commit, 35-task inventory, full spec mapping | Begin W0 implementation only |
| P1 each wave boundary | Prior completion receipt and clean commit | Begin the next implementation wave named by owner |
| P2 formal development | Clean `SEARCH_FREEZE_COMMIT`, exact parent/source, receipt and allowlisted diff | Execute one 20-trial development run |
| P3 final refit | Replay PASS and unique final development winner | Execute one final refit and pre-H2 feasibility |
| P4 candidate freeze | W4 PASS, exact candidate source commit, all identity digests | Add manifest/index-only candidate freeze commit |
| P5 future H2 unseal | Not produced by this suite; requires exact freeze commit and manifest digest | A future separate plan may create one authorization receipt |

At any P1–P4 `FAIL`/`UNKNOWN`, preserve evidence and stop. Do not alter the protocol or continue to
the dependent checkpoint.

## Normative spec coverage map

| Approved spec | Owning tasks | Closure |
|---|---|---|
| `1 purpose/relationship` | Index, W6.3 | v0.1 remains historical; v0.2 is additive and claim-bounded |
| `2 historical ledger` | W0.4, W6.3 | Candidate-v1/v2 failures and preservation digests are immutable assertions |
| `3 dataset roles/H2 boundary` | W1.4, W5.2–5.3, W6.1–6.4 | Development-only loader; no real H2 source binding |
| `4.1 envelope/time` | W1.1–1.3 | Strict v2 schema, timezone/domain reason codes, legacy routing |
| `4.2 feature schema` | W0.1, W1.2/W1.5 | Exact 18-field order/formulas and canonical digest |
| `4.3 leakage` | W1.4–1.5 | Target/future/H2 property tests and read-only data capability |
| `4.4 ONNX/serving` | W1.2–1.3, W2.3, W4.2–4.4 | 18 inputs, stable reduction, converter/serving parity |
| `4.5 completeness` | W2.1/W2.4–2.5, W6.1 | Fixed inventories; adapter/prediction 100%; label-only missingness |
| `5 folds/baselines` | W2.1–2.2 | Four exact folds and fold-specific stable control |
| `6.1 search identity` | W3.1/W3.3 | Acyclic source/freeze commits and code-byte preflight |
| `6.2–6.3 trials/budget` | W0.2, W2.2–2.3, W3.2/W3.4 | Exact table, one thread, 80+4+1 fit ledger |
| `6.4 ranking` | W2.6, W3.4–3.5 | Qualification first; sole provisional replay; no fallback |
| `7 development gate` | W2.4–2.6, W3.4–3.5 | Paired metrics, frozen bootstrap, subgroup/cross-fold gates |
| `8.1 final refit` | W4.1 | 2011+H1 only, winning pipeline unchanged |
| `8.2 feasibility` | W4.2–4.5 | ONNX, validator, CPU/load/cgroup and offline evidence |
| `8.3 freeze` | W5.1/W5.4–5.5 | Acyclic candidate source/freeze and manifest |
| `9.1–9.2 H2 preconditions/state` | W5.2–5.3, W6.1–6.2 | Atomic consume-before-read; no real source |
| `9.3 confirmatory contract` | W5.3, W6.1 | Synthetic fixtures only; policy machinery cannot start a real run |
| `10 milestones/Wave integration` | Index, every completion gate | Legacy delivery Wave 3 remains blocked until a future natural H2 PASS |
| `11 evidence/security/tests` | Every wave, W6.3–6.4 | Role labels, capability isolation, full requirement scan |
| `12 claim ceiling` | W0.4, W6.3 | Public claim tests retain `NO_ELIGIBLE_CANDIDATE` until real H2 PASS |
| `13 approved stop state` | Index | Planning only; W0 execution requires new owner approval |

## Requirement-to-task audit

The 29 owner review items map in order to:

1–6 W1.1–1.5; 7–10 W2.1/W2.4; 11–18 W2.1–2.6 and W3.4–3.5;
19–20 W3.1/W3.3; 21 W4.1; 22–23 W2.3 and W4.2–4.5; 24 W5.1/W5.4–5.5;
25–26 W5.2–5.3 and W6.1–6.2; 27 Index `10 mapping and W6.4; 28 W0.4/W6.3;
29 W6.3–6.4.

## Plan-suite self-review

| Invariant | Result |
|---|---|
| Approved spec §§1–13 and all 29 owner review items have task owners | PASS |
| Seven wave plans contain 35 tasks: `4 + 6 + 6 + 5 + 5 + 5 + 4` | PASS |
| Every task names exact files/interfaces, RED command/expected failure, minimum implementation, GREEN command/expected result, and commit scope | PASS |
| Every planned `Create` path has one owner; no path is modified before it exists | PASS |
| Search/refit budget is exactly `20 × 4 + 4 + 1 = 85` fits | PASS |
| Sole provisional winner receives one replay; no rank-two fallback | PASS |
| Development/H2 inventories preserve denominator and separate label missingness from adapter/prediction failure | PASS |
| Real H2 has no loader, binding, unseal receipt, evaluation command, or execution step in this suite | PASS |
| No alternate bootstrap count, threshold relaxation, legacy delivery-Wave-3 authorization, workflow/cloud expansion, or public release step exists | PASS |

These assertions are mechanically rechecked before the plan-suite commit; a failed check blocks the
commit rather than weakening the approved protocol.

## Execution rule

The suite is documentation only until P0 owner approval. Execute exactly one task at a time using
its RED command, observe the named failure, implement only the shown minimum, run the GREEN command,
commit with the named scope, and re-check the wave gate. Plan commands are future instructions; none
were executed while authoring this suite.

The suite terminal state is:

`IMPLEMENTATION_PLAN_READY / H2_SEALED / OWNER_PLAN_REVIEW_REQUIRED`
