# MDCP v0.2 Wave 3 Execution-Boundary Corrective Design

**Status:** OWNER APPROVED — IMPLEMENTATION PLANNING AUTHORIZED

**Date:** 2026-08-25

**Applies to:** Wave 3 formal-development Tasks 3.2, 3.3, and 3.5

**Does not authorize:** implementation, natural-data loading, model fitting, P2 consumption, H2
access, Docker, GPU, network, or publication

## 1. Decision and purpose

The approved temporal-retraining specification remains normative. This amendment corrects the
Wave 3 execution boundary without changing the frozen folds, trials, features, quality thresholds,
bootstrap, seed, chronology, or H2 policy.

The formal selection and sole provisional-winner replay SHALL execute in one process under one
consumed P2 authorization and one run-scoped fit ledger. There SHALL be no independently invocable
formal replay command. This preserves the existing transient, non-serializable
`ReplaySelectionSession` as the authority for rank-one replay and eliminates cross-process replay
reconstruction, repeat replay, and rank-two fallback.

The project SHALL finish this one preregistered development attempt and then stop model research:

- a replay-verified winner may proceed to the existing P3 checkpoint;
- `NO_ELIGIBLE_CANDIDATE`, replay failure, or terminal `UNKNOWN` is preserved as natural evidence;
- no second development run, new family, new feature, changed threshold, or result-driven v0.3
  search is implied by this amendment.

This keeps the flagship focused on model delivery and auditable rejection rather than indefinite
hyperparameter research.

## 2. Triggering evidence

Task 3.1 is accepted at commit `96f5e2bbb1faf547ffb186fafe87f9b1da7dfa21`. The initial Task 3.2
implementation exists at append-only commit `1eecbabc5016d8196787b8ae951792b1392d190b`, but it is not an
accepted `SEARCH_SOURCE_COMMIT`.

Independent review established these blocking defects:

1. replay could be reconstructed for an arbitrary trial and repeated with a new ledger;
2. caller-supplied clean-repository, clock, and memory callbacks could forge formal controls;
3. public receipt fields accepted unbounded caller strings and did not enforce the private/public
   boundary;
4. selection did not consume the existing completeness, evaluation, qualification, ranking, and
   replay-session contracts; and
5. deterministic static H2-firewall discovery rejected the new runner and CLI because the approved
   plan omitted their exact import and attribute policies.

The last defect cannot be repaired within the original four-file Task 3.2 allowlist. A corrective
plan therefore needs a narrow, reviewed scope expansion.

## 3. Preserved normative identities and rules

The corrective work SHALL NOT modify or reinterpret:

- the approved v0.2 temporal-retraining specification;
- the exact four folds, 20 trial identities, 19 eligible candidates, or trial parameters;
- the 80 selection, four replay, one later final-refit, and 85 total fit limits;
- seed `2026`, one estimator thread, 2,000 bootstrap replicates, or index `1899`;
- the exact 18-field feature schema or forbidden-feature rules;
- overall `0.97`, subgroup `1.05`, subgroup definitions, or minimum subgroup count `100`;
- the 13,003-row bounded development prefix: 8,645 train plus 4,358 observed H1;
- v0.1 or v0.2 serving identities and protected-byte inventories;
- H2 `SEALED_NOT_LOADED`, loaded rows `0`; or
- the acyclic `SEARCH_SOURCE_COMMIT -> SEARCH_FREEZE_COMMIT` construction.

The original Wave 3 plan remains an append-only historical execution record. After owner approval,
a new corrective plan SHALL supersede only its affected execution steps.

## 4. Formal execution lifecycle

The sole operational entry point is:

```text
run-development
  -> verify exact freeze and clean repository
  -> verify and atomically consume exact P2 authorization
  -> create a new, non-existing private external run root
  -> open the bounded development loader
  -> execute exactly 20 trials x F1..F4 in frozen order
  -> completeness + evaluation + qualification
  -> rank qualified trials through ReplaySelectionSession
  -> if no provisional winner: seal 80-fit terminal result
  -> if one provisional winner: replay its same four folds immediately
  -> finalize_selection using the same in-memory session
  -> atomically seal private bundle and sanitized public result
  -> terminate; never restore P2 or replay authority
```

`replay-provisional` SHALL be removed from the CLI during correction. It is not a frozen or released
compatibility surface. The final source and freeze inventories SHALL contain no independently
invocable replay command.

The possible Wave 3 fit counts are exactly:

- `80`: no qualified provisional winner or terminal selection failure before replay;
- `84`: exactly one provisional winner received exactly four replay fits; or
- fewer than `80`: only when a global integrity, runner-contract, or compute-budget failure
  terminates the run as `UNKNOWN`.

No Wave 3 path records a final-refit fit. The 85th fit remains a separately authorized Wave 4/P3
operation.

## 5. Component boundaries

### 5.1 CLI as the operational trust boundary

`cli.py` SHALL set the exact BLAS/OpenMP/joblib environment keys to `1` before importing any
estimator-bearing module. It SHALL then construct all production guards internally. Command-line,
environment, JSON, or Python callers SHALL NOT supply clock, process-memory, repository-integrity,
fit-ledger, selection-session, or evidence-sanitizer implementations.

Python helper functions remain testable, but they are not an authorization boundary. Only the CLI
composition path can create formal evidence. Test seams SHALL be private, typed, and incapable of
producing a formal evidence-class receipt.

### 5.2 Runner as deterministic orchestration

`runner.py` SHALL own only the serial state machine. It SHALL:

- iterate the frozen trial and fold inventories without replacement;
- call existing adapter, completeness, evaluation, qualification, ranking, and selection code;
- retain the one `FitLedger` and one `ReplaySelectionSession` for the run lifetime;
- reject any callback result that is not the exact internal typed result;
- complete all four folds for poor-quality but contract-valid trials;
- invalidate a contract-broken trial with fixed reason codes and no replacement; and
- return one sealed development result, never a caller-assembled provisional identity.

It SHALL NOT implement a second ranking rule, synthesize ranking keys, reconstruct a selection
session from public digests, or accept a replay target supplied by ID.

### 5.3 Runtime guards

A focused runtime-guard module SHALL provide production-only implementations for:

- `time.monotonic_ns()` deadline accounting;
- authoritative Windows `PeakWorkingSetSize` and Linux `VmHWM` process high-water marks;
- fixed-argument Git HEAD/status/tree inspection; and
- baseline/current protected-source inventory comparison.

An unavailable authoritative memory probe is terminal
`UNKNOWN/COMPUTE_BUDGET_EXCEEDED`; it is never replaced by RSS, `psutil`, Docker statistics, or a
host estimate. The guard checks deadline, peak memory, HEAD, clean status, and protected inventory
before the loader, before and after every fit, before evidence sealing, and on exit. A mismatch is
terminal and cannot authorize cleanup followed by retry.

The formal code never writes inside the repository. The same-user host and Git installation are
trusted infrastructure; unrelated host processes that mutate the checkout are detected but are not
claimed to be sandboxed by Python.

### 5.4 Evidence models

A focused run-evidence module SHALL separate:

- **private external evidence:** logical row identities, labels, stable/candidate predictions,
  preprocessing state, feature-vector material, per-fit receipts, and atomic run state; and
- **public evidence:** fixed status/reason enums, bounded counts, fixed metric fields, finite numeric
  values, lowercase 64-character SHA-256 digests, and aggregate inventory identities.

Public models SHALL use exact fields with extra fields forbidden. Metric keys are a closed schema;
arbitrary callback keys and strings are not copied. Every public document is RFC-8785 canonicalized,
validated, and passed through `public_evidence_violations` before atomic publication. It may contain
no row, prediction, label, raw timestamp, private path, hostname, environment dump, exception,
credential-shaped value, or opaque private payload.

Private output uses a destination that resolves outside the repository, does not exist at start,
and is created only after P2 is consumed. Writes are atomic and no-clobber. A handled partial run is
sealed terminal `UNKNOWN`. If process death prevents sealing, the consumed authorization plus the
incomplete no-clobber run root is authoritative `UNKNOWN` during recovery inspection; the
authorization remains consumed in both cases.

## 6. H2 static and behavioral firewall

The corrective plan SHALL add exact path-specific policies for the new formal modules to
`firewall.py`; it SHALL NOT add a directory wildcard or reusable broad exemption.

For each module, the policy fixes the exact imported symbols, module attributes, environment keys,
and file-access calls required by the design. The following remain fail closed in direct, alias,
qualified, relative, and dynamic forms:

- `load_uci_archive` and every legacy full-data loader;
- `DatasetPartitions`, `split_rows`, and `open_h2`;
- parsing `day.csv` or `hour.csv` beyond the bounded development prefix;
- socket/network/process-launch capabilities not required by fixed Git inspection;
- arbitrary environment enumeration; and
- import/reflection techniques outside the exact policy.

Behavioral tests SHALL execute the production composition path with deterministic generated data
and denial spies. They SHALL prove that legacy loaders, `split_rows`, and `open_h2` were never
called, the synthetic source exposes only the declared development rows, and H2 remains sealed/zero.
No real UCI row is loaded during corrective implementation tests.

## 7. Identity and publication model

The defective Task 3.2 commit remains in history; no amend, rebase, reset, or history rewrite is
allowed. Corrective commits replace its behavior append-only.

After all corrective tests and independent review pass:

1. the final clean corrective HEAD becomes the only proposed `SEARCH_SOURCE_COMMIT`;
2. all search-affecting modules, runtime guards, evidence models, firewall policy, schemas, and
   tests are included in its bound inventory;
3. its child adds only the two approved canonical search freeze JSON files; and
4. the child preflight recomputes the final corrected source identities without relying on Git
   history beyond the exact parent relationship.

No receipt hashes itself. No public pre-run index claims a digest for an output that does not yet
exist. Private absolute paths never enter a public identity.

## 8. Corrective implementation scope

The future corrective plan may modify or create only these exact implementation paths before the
P2 checkpoint:

- `src/mdcp/temporal/runner.py`;
- `src/mdcp/temporal/cli.py`;
- `src/mdcp/temporal/runtime_guards.py`;
- `src/mdcp/temporal/run_evidence.py`;
- `src/mdcp/temporal/firewall.py`;
- `src/mdcp/temporal/search_identity.py` for the already-planned P2 gate only;
- `schemas/v2/development-result-index.schema.json`;
- `schemas/v2/formal-run-authorization.schema.json`;
- `tests/unit/temporal/test_fit_ledger.py`;
- `tests/unit/temporal/test_runtime_guards.py`;
- `tests/unit/temporal/test_run_evidence.py`;
- `tests/integration/temporal/test_formal_runner_synthetic.py`;
- `tests/integration/temporal/test_search_freeze_preflight.py`;
- `tests/security/temporal/test_data_firewall.py`;
- `tests/security/temporal/test_formal_runner_firewall.py`;
- `tests/security/temporal/test_formal_run_authorization.py`;
- `tests/security/temporal/test_public_evidence_boundary.py`;
- `evidence/public/v02/search/search-receipt.json`; and
- `evidence/public/v02/search/evidence-index.json`.

The corrective plan SHALL finish all search-affecting code, schemas, and tests before creating the
two freeze files. It SHALL stop after the corrected Task 3.4/P2 checkpoint. Creation of
`evidence/public/v02/development/result-index.json` remains a post-P2 Task 3.5 action and is not in
the corrective implementation allowlist.

Existing Wave 2 selection, completeness, evaluation, fold, trial, dataset, split, adapter, golden,
and evidence implementations are read-only dependencies. If a correction requires changing one of
them, implementation SHALL stop for a separate design review.

The existing Wave 3 plan, approved specification, dependency lock, v0.1/v0.2 evidence, protected
inventories, datasets, and H2 state are outside the corrective allowlist.

## 9. RED-to-GREEN verification strategy

The corrective plan SHALL use append-only scoped commits and establish RED before each behavior:

1. **Session and fit ledger:** arbitrary target, second replay, reconstructed session, rank-two
   fallback, duplicate fold, wrong order, 81st selection fit, fifth replay fit, and Wave 3 final fit
   fail closed.
2. **Trusted runtime:** caller-injected probes cannot create formal evidence; missing/non-monotonic
   clock, missing/oversized peak, deadline breach, dirty or changed repository, and output inside the
   repository become terminal before another fit.
3. **Selection integration:** controlled qualification fixtures yield no winner or the exact Wave 2
   rank-one winner; poor-quality trials finish all folds; invalid verdict/status values fail closed;
   replay equality is checked by the existing session.
4. **Evidence boundary:** unknown metric keys, non-finite values, malformed digests, extra fields,
   row-like content, timestamps, paths, exceptions, and credentials are rejected without echoing the
   sensitive value.
5. **Static and behavioral firewall:** the real formal source set passes exact discovery; every
   legacy/H2 import spelling and malicious synthetic loader is denied; production wiring invokes
   only the bounded development interface.
6. **End-to-end synthetic run:** exactly 80 or 84 fits, single process, one thread, one private root,
   deterministic receipt recomputation, public/private separation, and H2 sealed/zero.

Fresh completion requires targeted tests, the entire CPU suite, all temporal security/publication
tests, source-archive identity recomputation, Ruff check and format check, dependency-lock check,
`git diff --check`, credential/private-path scan, protected-byte verification, and independent
review with Critical `0` and Important `0`.

## 10. Failure and rollback rules

Implementation stops without scope expansion when:

- a required change reaches a read-only Wave 2 or protected path;
- an authoritative memory or repository check cannot be implemented on the supported CPU hosts;
- exact one-process replay conflicts with a normative requirement rather than the old plan;
- a security/full-suite gate remains red after three separately evidenced hypotheses;
- any test needs UCI/H1/H2 row-level data, model fitting, network, Docker, GPU, or dependency changes;
  or
- independent review retains a Critical or Important finding.

Rollback is append-only: preserve the defective commit and add a correcting commit or stop. Never
amend, reset, rebase, delete evidence, relax a gate, or reuse an authorization/output root.

## 11. Checkpoints and terminal outcomes

Owner approval of this document authorizes only creation of a new corrective implementation plan.
It does not authorize implementation.

The implementation checkpoint is:

```text
W3_EXECUTION_BOUNDARY_CORRECTED / TASK_3_3_NOT_STARTED / H2_SEALED_NOT_LOADED
```

After a separately approved corrective plan completes, Tasks 3.3 and 3.4 may resume serially. Task
3.4 still stops at the exact P2 checkpoint. No natural fit occurs without a new P2 authorization
bound to the corrected freeze and receipt.

After a future one-shot formal run:

- a replay-verified winner proceeds only to P3;
- `NO_ELIGIBLE_CANDIDATE` or terminal `UNKNOWN` ends temporal model research and preserves natural
  rejection evidence; and
- neither outcome authorizes H2, delivery Wave 3, external publication, or another search.

The approved written-spec terminal state is:

```text
W3_CORRECTIVE_DESIGN_APPROVED / H2_SEALED_NOT_LOADED /
IMPLEMENTATION_PLANNING_AUTHORIZED
```
