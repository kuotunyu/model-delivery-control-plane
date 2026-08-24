# MDCP v0.2 Wave 5 Candidate Freeze and H2-Ready Machinery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the exact feasible candidate with an acyclic manifest and implement—but do not
authorize or bind to real data—the atomic single-use H2 capability boundary.

**Architecture:** A versioned freeze manifest binds every search, model, evaluator, feasibility,
stable-control, and H2-seal identity to a candidate source commit. A child freeze commit adds only
manifest/index files. PostgreSQL owns the one-shot state transition; an injected row-source protocol
has no production UCI implementation in this plan suite.

**Tech Stack:** Pydantic v2, RFC 8785/SHA-256, psycopg/PostgreSQL, existing atomic transaction
patterns, pytest, Hypothesis.

## Global Constraints

- Entry requires W4 PASS and no model/threshold/feature/evaluator change.
- P4 owner approval is required before creating the candidate manifest/freeze commit.
- Candidate source includes every byte affecting feature, prediction, stable comparison, gate,
  state transition, or evidence interpretation.
- Candidate freeze commit has that source as exact parent and adds only manifest/index JSON.
- Manifest contains no own freeze SHA and has `h2_unseal_authorized=false`,
  `one_shot_consumed=false`, `h2_status=SEALED_NOT_LOADED`, `h2_loaded_rows=0`.
- This suite creates no actual H2 authorization receipt and no real H2 row-source binding.
- Any transition mismatch or crash after consumption fails closed; authorization cannot reset.

---

## Wave 5 entry gate

Recompute W3 search and W4 final/feasibility identities, verify fit ledger 85, exact selected
artifact/image, clean Git state, no remotes/tags, and H2 sealed/zero. A single mismatch stops before
state/freeze work.

### Task 5.1: Define the complete temporal freeze manifest

**Files:**
- Create: `src/mdcp/temporal/freeze.py`
- Modify: `src/mdcp/contracts/release.py`
- Create: `schemas/v2/temporal-freeze-manifest.schema.json`
- Create: `tests/unit/temporal/test_freeze_manifest.py`
- Create: `tests/unit/contracts/test_temporal_freeze_manifest.py`

**Interfaces:**
- Consumes: W0–W4 digest inventories and existing canonical helpers.
- Produces: `TemporalFreezeManifest`,
  `temporal_freeze_manifest_digest(manifest) -> str`, and
  `build_temporal_freeze_manifest(inputs: FreezeInputs) -> TemporalFreezeManifest`.

- [ ] **Step 1: Write failing completeness/self-reference tests**

~~~python
def test_manifest_binds_every_pre_h2_identity() -> None:
    manifest = build_temporal_freeze_manifest(FROZEN_INPUTS)
    assert manifest.schema_version == "mdcp.temporal-freeze-manifest.v1"
    assert manifest.candidate_source_commit == FROZEN_INPUTS.candidate_source_commit
    assert "candidate_freeze_commit" not in manifest.model_fields
    assert manifest.h2_status == "SEALED_NOT_LOADED"
    assert manifest.h2_loaded_rows == 0
    assert manifest.h2_unseal_authorized is False
    assert manifest.one_shot_consumed is False
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_freeze_manifest.py tests/unit/contracts/test_temporal_freeze_manifest.py -q`

Expected: FAIL importing `TemporalFreezeManifest`.

- [ ] **Step 3: Implement exact manifest material**

The frozen model binds: schema/canonicalization/spec; search source/freeze/receipt/preflight;
candidate source; lock; complete trial/fold/quality/statistical/ranking/result/replay; dataset DOI,
archive, 13,003 development rows; temporal schema/adapter/timezone-data/golden vectors/features/
preprocessing/leakage; selected trial/config/seed/training/MLflow/native/ONNX/descriptor/image/SBOM/
provenance/scan/validation/parity/load/cgroup; stable-v1 config/feature/ONNX/descriptor; reason-code
and evaluator identities; v0.1 freeze digest
`f64004507703c342a0e116b6867185cdabee1a16870ed52f4d3ca16e0719dad7`;
logical H2 interval; and the four exact false/zero/sealed fields. It contains no path or freeze SHA.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_freeze_manifest.py tests/unit/contracts/test_temporal_freeze_manifest.py -q`

Expected: PASS; deleting or mutating any required identity fails schema/model validation or changes
the canonical digest.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/freeze.py src/mdcp/contracts/release.py schemas/v2/temporal-freeze-manifest.schema.json tests/unit/temporal/test_freeze_manifest.py tests/unit/contracts/test_temporal_freeze_manifest.py
git commit -m "feat: define temporal candidate freeze"
~~~

### Task 5.2: Implement the one-shot H2 state reducer and atomic ledger

**Files:**
- Create: `src/mdcp/temporal/h2_state.py`
- Create: `src/mdcp/temporal/h2_ledger.py`
- Create: `src/mdcp/temporal/sql/h2_ledger.sql`
- Modify: `compose.temporal-feasibility.yaml`
- Create: `tests/unit/temporal/test_h2_state.py`
- Create: `tests/integration/temporal/test_h2_ledger.py`
- Modify: `tests/contract/temporal/test_feasibility_compose.py`

**Interfaces:**
- Consumes: exact manifest/freeze identities and a future external owner authorization receipt.
- Produces: `H2State`, `H2Authorization`, `H2TransitionReceipt`, the `H2Ledger` protocol,
  `reduce_h2_state(current, event) -> H2State`, and `PostgresH2Ledger` methods
  `authorize`, `consume_start`, `finish`, `mark_crash_unknown`, `read_state`.

- [ ] **Step 1: Write failing state/concurrency tests**

~~~python
def test_state_machine_is_one_way() -> None:
    assert reduce_h2_state(H2State.SEALED_NOT_LOADED, "AUTHORIZE") is H2State.AUTHORIZED_FOR_SINGLE_USE
    assert reduce_h2_state(H2State.AUTHORIZED_FOR_SINGLE_USE, "CONSUME_START") is H2State.UNSEALED_EVALUATION_IN_PROGRESS
    assert reduce_h2_state(H2State.UNSEALED_EVALUATION_IN_PROGRESS, "FINISH_FAIL") is H2State.CONSUMED_FAIL
    with pytest.raises(H2StateError):
        reduce_h2_state(H2State.CONSUMED_FAIL, "AUTHORIZE")

def test_two_consumers_cannot_both_start(postgres_ledger) -> None:
    results = concurrently_call_consume_start(postgres_ledger, count=2)
    assert sorted(result.started for result in results) == [False, True]

def test_h2_ledger_profile_is_internal_and_ephemeral(compose_config) -> None:
    assert compose_config["services"]["h2-ledger-postgres"]["networks"] == ["h2-ledger"]
    assert compose_config["networks"]["h2-ledger"]["internal"] is True
    assert "ports" not in compose_config["services"]["h2-ledger-postgres"]
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_h2_state.py tests/integration/temporal/test_h2_ledger.py tests/contract/temporal/test_feasibility_compose.py -q`

Expected: FAIL importing H2 state/ledger modules.

- [ ] **Step 3: Implement append-only atomic transitions**

SQL creates one state row keyed by manifest digest plus append-only audit rows. `authorize` accepts
only a future receipt bound to manifest digest and freeze commit. `consume_start` performs one
`UPDATE ... WHERE state='AUTHORIZED_FOR_SINGLE_USE' RETURNING` and inserts its audit record in the
same transaction, committing before it returns success. `finish` allows PASS/FAIL/UNKNOWN only from
in-progress. Process/crash recovery changes in-progress to consumed-unknown; no SQL path transitions
from any consumed state. Receipts expose logical identities/digests and fixed codes only.

Add an internal `h2-ledger` network, an ephemeral read-only PostgreSQL service, and a non-root
`h2-ledger-test` service to the existing temporal Compose file. Both drop all capabilities, set
no-new-privileges, use bounded CPU/memory/pids/tmpfs, publish no host port, mount no Docker socket,
and contain generated synthetic state only.

- [ ] **Step 4: Run GREEN**

Run unit tests, then the disposable integration profile:

`uv run pytest tests/unit/temporal/test_h2_state.py tests/contract/temporal/test_feasibility_compose.py -q`

`docker compose -f compose.temporal-feasibility.yaml --profile h2-ledger-test up --build --abort-on-container-exit --exit-code-from h2-ledger-test`

Expected: PASS for truth table, two-consumer race, transaction rollback, crash, and no-reset cases;
then remove the Compose project and its ephemeral volume/network.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/h2_state.py src/mdcp/temporal/h2_ledger.py src/mdcp/temporal/sql/h2_ledger.sql compose.temporal-feasibility.yaml tests/unit/temporal/test_h2_state.py tests/integration/temporal/test_h2_ledger.py tests/contract/temporal/test_feasibility_compose.py
git commit -m "feat: add atomic single-use h2 ledger"
~~~

### Task 5.3: Enforce consume-before-read with no real H2 source binding

**Files:**
- Create: `src/mdcp/temporal/h2_guard.py`
- Modify: `src/mdcp/temporal/evaluation.py`
- Create: `tests/unit/temporal/test_h2_guard.py`
- Create: `tests/unit/temporal/test_confirmatory_policy.py`
- Create: `tests/security/temporal/test_no_real_h2_binding.py`

**Interfaces:**
- Consumes: `PostgresH2Ledger` through `H2Ledger` protocol and an injected `H2RowSource` protocol.
- Produces: immutable `H2EvaluationRow(source_identity, envelope: BikeRequestV2,
  label: float | None, evidence_role)`, `H2RowSource.load_once() -> Sequence[H2EvaluationRow]`, and
  `AuthorizedSingleUseEvaluator.start(authorization) -> EvaluationSession`; plus
  `evaluate_confirmatory(inventory, adapters, stable, candidate, labels, policy)
  -> ConfirmatoryQualityReport`.

- [ ] **Step 1: Write failing call-order/capability tests**

~~~python
def test_ledger_consumes_before_source_load() -> None:
    events: list[str] = []
    evaluator = AuthorizedSingleUseEvaluator(
        ledger=RecordingLedger(events), source=RecordingSyntheticSource(events)
    )
    evaluator.start(SYNTHETIC_AUTHORIZATION)
    assert events[:2] == ["consume_start_committed", "source_load"]

def test_production_tree_has_no_uci_h2_source_binding() -> None:
    assert find_concrete_implementations("H2RowSource", root=Path("src")) == ()

def test_confirmatory_policy_separates_label_missingness() -> None:
    report = evaluate_confirmatory(
        INVENTORY_2400, COMPLETE_ADAPTERS, COMPLETE_STABLE, COMPLETE_CANDIDATE,
        LABELS_AT_99_5_PERCENT, FROZEN_POLICY,
    )
    assert report.adapter_completeness == 1.0
    assert report.stable_prediction_completeness == 1.0
    assert report.candidate_prediction_completeness == 1.0
    assert report.label_completeness == 0.995
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_h2_guard.py tests/unit/temporal/test_confirmatory_policy.py tests/security/temporal/test_no_real_h2_binding.py -q`

Expected: FAIL because guard/protocol are absent.

- [ ] **Step 3: Implement protocol-only orchestration**

`start` validates manifest/freeze/authorization, calls and commits `consume_start`, then invokes
`source.load_once`. If loading or later evaluation raises, it writes `CONSUMED_UNKNOWN` and never
releases another token. The production package defines only the protocol and orchestrator; no class,
function, CLI option, config key, archive interval, or path can load real H2. Synthetic source
implementations exist under tests only in W6.

`H2EvaluationRow` is the protocol payload type, not a data-source implementation. It rejects a
missing/duplicate source identity, non-v2 envelope, non-finite present label, or evidence role other
than the authorization-bound role before prediction begins.

`evaluate_confirmatory` first uses the immutable inventory and Task 2.4 accounting. Adapter and both
prediction streams must be exactly 100%, and at least 2,000 valid pairs must exist before label
filtering. Only labels may use overall `>=99.5%` and every fixed subgroup `>=99.0%`; every subgroup
then needs at least 100 paired labeled rows. It reuses the exact 0.97/1.05, seven-subgroup, 2,000,
PCG64(2026), index-1,899 kernel. Any adapter/prediction/accounting problem is whole-gate `UNKNOWN`
and cannot enter the label-missing counters.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_h2_guard.py tests/unit/temporal/test_confirmatory_policy.py tests/security/temporal/test_no_real_h2_binding.py -q`

Expected: PASS; source is never called on absent/wrong/reused authorization.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/h2_guard.py src/mdcp/temporal/evaluation.py tests/unit/temporal/test_h2_guard.py tests/unit/temporal/test_confirmatory_policy.py tests/security/temporal/test_no_real_h2_binding.py
git commit -m "feat: enforce consume before h2 read"
~~~

### Task 5.4: Add candidate-source/freeze preflight and close production bytes

**Files:**
- Modify: `src/mdcp/temporal/freeze.py`
- Modify: `src/mdcp/temporal/cli.py`
- Create: `tests/integration/temporal/test_candidate_freeze_preflight.py`
- Create: `tests/security/temporal/test_candidate_freeze_boundary.py`

**Interfaces:**
- Consumes: candidate source commit, manifest, approved freeze index.
- Produces: `CandidateFreezeCheck` and
  `verify_candidate_freeze(repository_root, manifest_path, index_path) -> CandidateFreezeCheck`;
  CLI command `verify-candidate-freeze` invokes only that read-only check.

- [ ] **Step 1: Write failing parent/diff/tamper tests**

~~~python
def test_candidate_freeze_rejects_gate_code_change(git_fixture) -> None:
    make_freeze_child(git_fixture, extra_path="src/mdcp/temporal/evaluation.py")
    check = verify_candidate_freeze(git_fixture, MANIFEST, INDEX)
    assert check.verdict == "FAIL"
    assert check.reason_codes == ("CANDIDATE_FREEZE_DIFF_NOT_ALLOWLISTED",)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/integration/temporal/test_candidate_freeze_preflight.py tests/security/temporal/test_candidate_freeze_boundary.py -q`

Expected: FAIL because candidate freeze verification is absent.

- [ ] **Step 3: Implement exact-child verification**

Require a clean checkout at the candidate freeze commit; one parent exactly equal to manifest
`candidate_source_commit`; changed paths exactly
`evidence/public/v02/freeze/temporal-freeze-manifest.json` and
`evidence/public/v02/freeze/evidence-index.json`; no source/config/schema/lock/model/gate byte
change; every manifest/evidence digest recomputes; H2 state is sealed/zero/unauthorized/unconsumed.
Reject placeholder/backfill/amend/self-reference behavior.

- [ ] **Step 4: Run GREEN and full candidate-source tests**

Run:
`uv run pytest tests/unit tests/contract tests/integration/temporal tests/integration/validator tests/security/temporal -q && uv run ruff check src/mdcp tests && git diff --check`

Expected: PASS with clean source after committing this task.

- [ ] **Step 5: Commit and stop for P4**

~~~powershell
git add src/mdcp/temporal/freeze.py src/mdcp/temporal/cli.py tests/integration/temporal/test_candidate_freeze_preflight.py tests/security/temporal/test_candidate_freeze_boundary.py
git commit -m "feat: verify temporal candidate freeze"
~~~

This exact clean HEAD is the proposed `candidate_source_commit`. Report all W4/W5 digests and stop;
do not create the manifest until P4 owner authorization.

### Task 5.5: Create the manifest-only candidate freeze child

**Files:**
- Create: `evidence/public/v02/freeze/temporal-freeze-manifest.json`
- Create: `evidence/public/v02/freeze/evidence-index.json`
- Test: `tests/integration/temporal/test_candidate_freeze_preflight.py`

**Interfaces:**
- Consumes: exact P4-authorized candidate source commit and every recomputed manifest input.
- Produces: candidate freeze manifest digest and exact child `candidate_freeze_commit`.

- [ ] **Step 1: Run RED before manifest creation**

~~~powershell
uv run python -m mdcp.temporal.cli verify-candidate-freeze --manifest evidence/public/v02/freeze/temporal-freeze-manifest.json --index evidence/public/v02/freeze/evidence-index.json
~~~

Expected: nonzero `CANDIDATE_FREEZE_MANIFEST_MISSING` and no H2 transition.

- [ ] **Step 2: Verify P4 and generate canonical files**

Require the external owner P4 record to bind the proposed candidate source commit, W4 feasibility
bundle digest, and authorized action `ADD_CANDIDATE_FREEZE_MANIFEST_ONLY`. Generate the manifest via
`build_temporal_freeze_manifest` and an index of logical Git-external private evidence identities.
Neither file contains the child commit SHA, owner private metadata, or an H2 authorization.

- [ ] **Step 3: Pre-commit validation**

Validate both schemas, RFC 8785 bytes, public evidence scan, all manifest input digests, clean
candidate source, and staged-path equality. The staged set must be exactly the two named files.

- [ ] **Step 4: Commit and run GREEN**

~~~powershell
git add evidence/public/v02/freeze/temporal-freeze-manifest.json evidence/public/v02/freeze/evidence-index.json
git commit -m "chore: freeze v0.2 temporal candidate"
uv run python -m mdcp.temporal.cli verify-candidate-freeze --manifest evidence/public/v02/freeze/temporal-freeze-manifest.json --index evidence/public/v02/freeze/evidence-index.json
~~~

Expected: `CANDIDATE_FREEZE_PASS`; exact parent is candidate source and diff is the two additions.

- [ ] **Step 5: Record immutable identities and stop**

Record full source/freeze SHAs and manifest digest in the private operator ledger without modifying
the manifest. Confirm `h2_unseal_authorized=false`, `one_shot_consumed=false`,
`SEALED_NOT_LOADED`, rows 0. Do not create an authorization receipt.

## Wave 5 completion gate

- Freeze manifest/schema, one-shot state/ledger, consume-before-read, no-real-binding, and
  exact-parent/diff tests PASS.
- Candidate source/freeze identity is acyclic and every W0–W4 digest recomputes.
- Production gate-affecting bytes are frozen; no real H2 authorization or source exists.

**Immutable handoff:** candidate source/freeze commits, manifest digest, state/ledger/guard code
digests, and sealed/zero state.

**Owner checkpoint:** report `CANDIDATE_FROZEN / H2_SEALED`. W6 may add only synthetic test/support,
reviewer docs, and sanitized synthetic evidence; it may not change production/config/schema/lock
bytes.
