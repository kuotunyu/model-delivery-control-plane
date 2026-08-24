# MDCP v0.2 Wave 6 Synthetic-Only H2 State-Machine Verification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently verify the frozen candidate's one-shot H2 machinery with generated fixtures
and finish at H2-unseal readiness while H2 remains sealed and unloaded.

**Architecture:** This wave adds only tests, test support, reviewer documentation, and sanitized
synthetic evidence after the candidate freeze. It runs production bytes bound by the freeze but
cannot modify them. Generated fixtures exercise PASS/FAIL/UNKNOWN, concurrency, crash, completeness,
claims, and capability boundaries without a real UCI H2 source.

**Tech Stack:** pytest, Hypothesis, PostgreSQL test profile, Pydantic/RFC 8785 verification, existing
temporal state/evaluation modules.

## Global Constraints

- Entry requires an exact W5 candidate freeze PASS and owner continuation approval.
- The diff after candidate freeze may contain only `tests/`, `docs/reviewer/`, and the named
  `evidence/public/v02/h2-readiness-report.json`.
- No `src/`, `configs/`, `schemas/`, dependency lock, model, manifest, or freeze-index byte changes.
- Every fixture declares `evidence_class="synthetic_test"` and `uci_rows=0`.
- No fixture is copied from UCI, preserved evidence, H1 row-level evidence, or H2.
- No real authorization receipt/source/loader/inference/evaluation command exists in this wave.
- `H2_UNSEAL_READY` means preconditions/machinery reviewed; it is not unseal authorization or PASS.

---

## Wave 6 entry gate

Run candidate-freeze preflight at its exact commit, verify W6 starts from that clean child, bind the
manifest digest, and verify sealed/zero/unauthorized/unconsumed state. Save source/config/schema/lock
tree digests for the end-of-wave equality check.

### Task 6.1: Freeze synthetic PASS, FAIL, and UNKNOWN cases

**Files:**
- Create: `tests/fixtures/temporal/synthetic-h2-cases.json`
- Create: `tests/temporal_h2_fixtures.py`
- Create: `tests/integration/temporal/test_synthetic_confirmatory_cases.py`

**Interfaces:**
- Consumes: frozen `evaluate_confirmatory`, completeness accounting, quality policy.
- Produces: `synthetic_confirmatory_case(name) -> SyntheticConfirmatoryCase` for exact cases
  `PASS`, `FAIL_OVERALL`, `UNKNOWN_ADAPTER`, `UNKNOWN_STABLE`, `UNKNOWN_CANDIDATE`,
  `UNKNOWN_LABEL_OVERALL`, `UNKNOWN_LABEL_SUBGROUP`, `UNKNOWN_SUBGROUP_N`.

- [ ] **Step 1: Write the failing case matrix test**

~~~python
@pytest.mark.parametrize(("name", "verdict"), [
    ("PASS", "PASS"),
    ("FAIL_OVERALL", "FAIL"),
    ("UNKNOWN_ADAPTER", "UNKNOWN"),
    ("UNKNOWN_STABLE", "UNKNOWN"),
    ("UNKNOWN_CANDIDATE", "UNKNOWN"),
    ("UNKNOWN_LABEL_OVERALL", "UNKNOWN"),
    ("UNKNOWN_LABEL_SUBGROUP", "UNKNOWN"),
    ("UNKNOWN_SUBGROUP_N", "UNKNOWN"),
])
def test_synthetic_confirmatory_case(name: str, verdict: str) -> None:
    case = synthetic_confirmatory_case(name)
    assert case.evidence_class == "synthetic_test"
    assert case.uci_rows == 0
    report = evaluate_confirmatory(
        case.inventory, case.adapters, case.stable_predictions,
        case.candidate_predictions, case.labels, FROZEN_POLICY,
    )
    assert report.verdict == verdict
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/integration/temporal/test_synthetic_confirmatory_cases.py -q`

Expected: FAIL because fixture JSON/helper are absent.

- [ ] **Step 3: Implement generated fixture material**

Use deterministic IDs `synthetic-h2-000000` onward and arithmetic-only features/labels. Include at
least 2,400 source identities and seven groups with `n>=100` in the valid cases. PASS has ratio 0.90;
FAIL_OVERALL exceeds 0.97; adapter/stable/candidate UNKNOWN cases remove one identity from exactly
that stream; label cases use 99.49% overall or 98.99% in one group; subgroup-N has 99 labeled pairs
in one fixed group. Store compact generator parameters/expected aggregates, not 2,400 raw rows.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/integration/temporal/test_synthetic_confirmatory_cases.py -q`

Expected: all eight cases produce their exact verdict/reason codes; adapter/prediction failures have
`label_missing_count=0` and never shrink `source_count`.

- [ ] **Step 5: Commit**

~~~powershell
git add tests/fixtures/temporal/synthetic-h2-cases.json tests/temporal_h2_fixtures.py tests/integration/temporal/test_synthetic_confirmatory_cases.py
git commit -m "test: add synthetic h2 policy cases"
~~~

### Task 6.2: Stress one token, consume-before-read, crash, and no reset

**Files:**
- Create: `tests/temporal_h2_concurrency.py`
- Create: `tests/integration/temporal/test_h2_concurrency_synthetic.py`
- Create: `tests/integration/temporal/test_h2_crash_synthetic.py`

**Interfaces:**
- Consumes: frozen `PostgresH2Ledger`, `AuthorizedSingleUseEvaluator`, synthetic row source.
- Produces: deterministic barriers/fault points for `before_consume`, `after_consume_before_read`,
  `during_read`, `after_read_before_finish`.

- [ ] **Step 1: Write failing race/crash tests**

~~~python
def test_exactly_one_of_eight_workers_reads(postgres_ledger) -> None:
    results, source_reads = race_workers(postgres_ledger, workers=8)
    assert sum(result.started for result in results) == 1
    assert source_reads == 1

@pytest.mark.parametrize("fault", [
    "after_consume_before_read", "during_read", "after_read_before_finish",
])
def test_crash_consumes_token_and_cannot_reset(fault, postgres_ledger) -> None:
    crash_once(postgres_ledger, fault)
    assert postgres_ledger.read_state() == H2State.CONSUMED_UNKNOWN
    assert retry_start(postgres_ledger).started is False
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/integration/temporal/test_h2_concurrency_synthetic.py tests/integration/temporal/test_h2_crash_synthetic.py -q`

Expected: FAIL because deterministic concurrency/fault helpers are absent.

- [ ] **Step 3: Implement test-only barriers and source**

The synthetic source increments one transaction-safe read counter and returns generated rows from
Task 6.1. Barriers synchronize all workers before `consume_start`. Fault injection raises fixed
test exceptions at the three named points; the harness invokes recovery and asserts
`CONSUMED_UNKNOWN`. No helper resides under `src` or accepts a filesystem/archive path.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/integration/temporal/test_h2_concurrency_synthetic.py tests/integration/temporal/test_h2_crash_synthetic.py -q`

Expected: PASS for repeated deterministic races; exactly one source read and no consumed-state reset.

- [ ] **Step 5: Commit**

~~~powershell
git add tests/temporal_h2_concurrency.py tests/integration/temporal/test_h2_concurrency_synthetic.py tests/integration/temporal/test_h2_crash_synthetic.py
git commit -m "test: verify single-use h2 concurrency"
~~~

### Task 6.3: Verify capability, privacy, claim, and legacy-Wave-3 boundaries

**Files:**
- Create: `tests/security/temporal/test_h2_capability_boundary.py`
- Create: `tests/security/temporal/test_v02_claim_boundary.py`
- Create: `tests/contract/temporal/test_wave_dependency.py`
- Create: `docs/reviewer/v02-h2-readiness.md`

**Interfaces:**
- Consumes: frozen manifest/state/evidence scanner and Git tree.
- Produces: reviewer commands that exercise synthetic machinery only.

- [ ] **Step 1: Write failing scans**

~~~python
def test_no_real_h2_execution_surface_exists() -> None:
    assert scan_production_for_h2_bindings() == ()

def test_legacy_delivery_wave_three_stays_blocked() -> None:
    state = evaluate_legacy_wave3_entry(h2_natural_verdict=None)
    assert state.allowed is False
    assert state.reason_code == "NATURAL_H2_PASS_REQUIRED"

def test_readiness_doc_never_claims_h2_pass() -> None:
    text = Path("docs/reviewer/v02-h2-readiness.md").read_text("utf-8")
    assert "H2_UNSEAL_READY" in text
    assert "natural H2 PASS" not in text
~~~

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/security/temporal/test_h2_capability_boundary.py tests/security/temporal/test_v02_claim_boundary.py tests/contract/temporal/test_wave_dependency.py -q`

Expected: FAIL because scans/doc are absent.

- [ ] **Step 3: Add exact scans and reviewer procedure**

Scan production AST/config/CLI/Compose for a concrete `H2RowSource` implementation, UCI H2 date
binding, real authorization creation, H2 path/env argument, network source, or second-candidate
command. Scan tracked docs/evidence for private paths, raw rows/predictions/labels, credentials, raw
exceptions, and forbidden claims. The reviewer doc runs only the synthetic case, concurrency,
crash, freeze, privacy, and claim tests and explains that a future separate plan/owner receipt is
required. Distinguish this suite's temporal W3 search from the still-blocked legacy delivery W3.

- [ ] **Step 4: Run GREEN**

Run:
`uv run pytest tests/security/temporal/test_h2_capability_boundary.py tests/security/temporal/test_v02_claim_boundary.py tests/contract/temporal/test_wave_dependency.py -q`

Expected: PASS with no real execution surface or promotion claim.

- [ ] **Step 5: Commit**

~~~powershell
git add tests/security/temporal/test_h2_capability_boundary.py tests/security/temporal/test_v02_claim_boundary.py tests/contract/temporal/test_wave_dependency.py docs/reviewer/v02-h2-readiness.md
git commit -m "docs: add synthetic h2 readiness review"
~~~

### Task 6.4: Aggregate the readiness receipt and prove frozen-byte equality

**Files:**
- Create: `tests/fixtures/temporal/h2-readiness-report.schema.json`
- Create: `evidence/public/v02/h2-readiness-report.json`
- Create: `tests/contract/temporal/test_h2_readiness_report.py`
- Create: `tests/integration/temporal/test_wave6_completion.py`

**Interfaces:**
- Consumes: candidate freeze identities and Task 6.1–6.3 test/evidence digests.
- Produces: sanitized `mdcp.h2-readiness-report.v1` and terminal readiness verdict.

- [ ] **Step 1: Write the failing aggregate/frozen-byte test**

~~~python
def test_readiness_report_is_synthetic_and_sealed() -> None:
    report = load_report()
    assert report["terminal_state"] == "H2_UNSEAL_READY / H2_SEALED_NOT_LOADED"
    assert report["evidence_class"] == "synthetic_test"
    assert report["uci_rows"] == 0
    assert report["h2_loaded_rows"] == 0
    assert report["h2_unseal_authorized"] is False

def test_production_bytes_equal_candidate_freeze() -> None:
    assert changed_paths_since_freeze() <= allowed_wave6_paths()
    assert source_config_schema_lock_digest_now() == digest_at_candidate_freeze()
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/contract/temporal/test_h2_readiness_report.py tests/integration/temporal/test_wave6_completion.py -q`

Expected: FAIL because report/schema are absent.

- [ ] **Step 3: Build a digest-only aggregate**

Report candidate source/freeze/manifest, synthetic fixture, test suite, state truth-table,
concurrency, crash, completeness, privacy, claim, and frozen-byte digests; counts/verdicts; and the
exact terminal state. It contains no private path, raw row/prediction/label, database DSN, exception,
authorization secret, or real H2 result. Validate with the test-only strict schema and RFC 8785.

- [ ] **Step 4: Run full GREEN and cleanup**

Run:
`uv run pytest tests/unit tests/contract tests/integration/temporal tests/integration/validator tests/security/temporal -q && uv run ruff check src/mdcp tests && git diff --check`

Expected: all tests PASS; PostgreSQL synthetic test profile is removed; Git diff since candidate
freeze contains only allowed W6 paths; H2 state is still sealed/zero/unauthorized/unconsumed.

- [ ] **Step 5: Commit and stop**

~~~powershell
git add tests/fixtures/temporal/h2-readiness-report.schema.json evidence/public/v02/h2-readiness-report.json tests/contract/temporal/test_h2_readiness_report.py tests/integration/temporal/test_wave6_completion.py
git commit -m "docs: record synthetic h2 readiness"
~~~

## Wave 6 completion gate

- Synthetic PASS/FAIL/UNKNOWN, denominator, concurrency, crash, no-reset, capability, privacy,
  claims, wave-dependency, manifest, and frozen-byte tests PASS.
- Production/config/schema/lock/model/manifest bytes equal candidate-freeze identities.
- No real authorization, H2 read, inference, evaluation, rollout, Docker/GPU deployment, remote, or
  external publication occurred.

**Immutable handoff:** candidate freeze plus synthetic readiness report and test digests.

**Owner checkpoint and terminal state:**

`H2_UNSEAL_READY / H2_SEALED_NOT_LOADED`

Stop. Real H2 work requires a new standalone plan and a new owner authorization bound to the exact
candidate freeze commit and manifest digest.
