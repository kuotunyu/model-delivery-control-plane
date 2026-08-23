# MDCP Wave 4 Evidence Windows and Quality Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn durable paired events into immutable evidence windows and fail-closed H1/H2 quality/drift decisions that can safely advance, reject, or pause a release.

**Architecture:** PostgreSQL window rows snapshot exact event membership and recomputable aggregates before sealing. Pure policy functions consume typed rows and frozen policy, never Grafana/Prometheus queries. Wave 1's calendar-day bootstrap kernel is reused byte-for-byte; this wave adds H2 completeness, subgroup, window, drift, and transition integration.

**Tech Stack:** Python 3.12, Pydantic v2, SQLAlchemy/PostgreSQL, Alembic, NumPy PCG64, pytest, Hypothesis, RFC 8785, and the Wave 3 control API.

## Global Constraints

- Entry requires Wave 3 PASS and committed paired shadow admissions/terminal/label events.
- `UNKNOWN` never promotes. Missing, stale, conflicting, or insufficient validation/shadow/canary evidence pauses with candidate traffic zero.
- H1/H2 use identical day-cluster sampling, 2,000 resamples, PCG64 seed 2026, nearest-rank element 1899, overall 0.97, subgroup 1.05, and every fixed subgroup `n >= 100`.
- H2 requires at least 2,000 valid pairs, 99.5% overall label completeness, and 99.0% in every predeclared subgroup.
- Sealed windows are immutable; late evidence is retained but cannot mutate a verdict.
- Prometheus/Grafana are not decision inputs.
- Completion command: `uv run pytest tests/unit/policy tests/unit/control/test_window_service.py tests/property/policy tests/integration/control/test_quality_windows.py -q`.

---

### Task 4.1: Define sealed-window contracts and immutable storage

**Files:**
- Create: `src/mdcp/contracts/windows.py`
- Create: `schemas/v1/sealed-window.schema.json`
- Create: `migrations/versions/0004_evidence_windows_policy.py`
- Modify: `src/mdcp/db/evidence.py`
- Test: `tests/unit/contracts/test_window_contract.py`
- Test: `tests/integration/control/test_window_migration.py`
- Test: `tests/integration/control/test_sealed_window_immutability.py`

**Interfaces:**
- Consumes: release/stable IDs, route revision, policy digest, event identities, UTC/monotonic bounds.
- Produces: `MetricFraction`, `SubgroupMetrics`, `SealedWindow`, `GateVerdict`, tables `evidence_windows`, `window_event_members`, `policy_evaluations`.

- [ ] **Step 1: Write failing schema/immutability tests**

```python
def test_sealed_window_digest_covers_members(window):
    assert window.evidence_digest == content_digest(window.without_digest())

def test_application_role_cannot_mutate_sealed_window(app_db, sealed_window_id):
    with pytest.raises(InsufficientPrivilege):
        app_db.execute("update evidence_windows set verdict='PASS' where window_id=%s", [sealed_window_id])
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/contracts/test_window_contract.py tests/integration/control/test_window_migration.py tests/integration/control/test_sealed_window_immutability.py -q`

Expected: FAIL because window types/migration are absent.

- [ ] **Step 3: Implement versioned windows and DB protections**

Include every spec §15.1 field, explicit numerators/denominators, event-member digests, verdict/reason codes, and evidence digest. Migration creates checked window kinds/states, unique immutable membership, indexes on `(environment_id,release_id,kind,sealed_at)` and `(route_revision,kind)`, and application permissions that allow insert/seal transaction but reject post-seal update/delete.

```python
def seal_window(window_id: WindowId, now: datetime, session: Session) -> SealedWindow:
    with session.begin():
        window = lock_open_window(session, window_id)
        members = snapshot_eligible_members(session, window, now)
        sealed = window.seal(member_digests=tuple(sorted(m.digest for m in members)), sealed_at=now)
        persist_sealed_window_and_members(session, sealed, members)
    return sealed
```

- [ ] **Step 4: Verify schema, migration, and mutation denial**

Run: `uv run alembic upgrade 0004; uv run pytest tests/unit/contracts/test_window_contract.py tests/integration/control/test_window_migration.py tests/integration/control/test_sealed_window_immutability.py -q`

Expected: tests pass, schema regenerates exactly, a second seal is idempotent only for identical content, and changed content is rejected.

- [ ] **Step 5: Commit**

```powershell
git add schemas/v1/sealed-window.schema.json migrations/versions/0004_evidence_windows_policy.py src/mdcp/contracts/windows.py src/mdcp/db/evidence.py tests/unit/contracts tests/integration/control
git commit -m "feat: add immutable evidence windows"
```

### Task 4.2: Implement event identity, pairing, duplicates, and lateness accounting

**Files:**
- Create: `src/mdcp/control/window_service.py`
- Test: `tests/unit/control/test_window_service.py`
- Test: `tests/property/policy/test_event_accounting.py`
- Test: `tests/integration/control/test_event_ordering.py`

**Interfaces:**
- Consumes: durable admissions, terminal events, delayed labels, route/policy IDs, window target/duration, 30-second lateness allowance.
- Produces: `WindowService.open_window(environment_id: UUID, release_id: str, route_revision: int, policy_digest: str, target_admissions: int, opened_at: datetime) -> WindowId`, `WindowService.seal(window_id: WindowId, now: datetime) -> SealedWindow`, and exact/conflicting/missing/late/out-of-order counts.

- [ ] **Step 1: Write failing accounting properties**

```python
@given(event_streams_with_duplicates())
def test_exact_duplicates_never_change_denominator(stream, service):
    window = service.ingest_and_seal(stream)
    assert window.terminal_denominator == len(unique_terminal_identities(stream))

def test_late_event_cannot_rewrite_sealed_digest(service, late_stream):
    before = service.seal(late_stream.window_id).evidence_digest
    service.ingest(late_stream.late_event)
    assert service.get(late_stream.window_id).evidence_digest == before
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_window_service.py tests/property/policy/test_event_accounting.py tests/integration/control/test_event_ordering.py -q`

Expected: FAIL because `WindowService` does not exist.

- [ ] **Step 3: Implement deterministic joins and sealing**

Join stable/candidate/label only by identical request and declared revision/policy; track expected versus observed, exact duplicate counter without denominator increment, conflicting duplicate as integrity incident/UNKNOWN, and late evidence in a separate immutable audit record. Seal on target or maximum duration plus allowance using database time and a transactionally captured event-member set.

```python
def account_event(state: WindowAccounting, event: EvidenceEvent) -> WindowAccounting:
    identity = event.terminal_identity()
    if identity in state.exact_events:
        return state.increment_exact_duplicate(identity)
    if identity in state.conflicting_events:
        return state.with_integrity_conflict(identity)
    if event.arrived_at > state.lateness_deadline:
        return state.record_late_audit(event)
    return state.add_denominator_event(event)
```

- [ ] **Step 4: Verify permutations**

Run: `uv run pytest tests/unit/control/test_window_service.py tests/property/policy/test_event_accounting.py tests/integration/control/test_event_ordering.py -q`

Expected: shuffled order yields identical digest/verdict, exact duplicates preserve denominators, conflict becomes UNKNOWN, late rows do not mutate, and all property examples pass.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/control/window_service.py tests/unit/control/test_window_service.py tests/property/policy/test_event_accounting.py tests/integration/control/test_event_ordering.py
git commit -m "feat: seal deterministic evidence membership"
```

### Task 4.3: Apply paired H2 quality and subgroup completeness policy

**Files:**
- Create: `src/mdcp/control/quality_policy.py`
- Test: `tests/unit/policy/test_quality_policy.py`
- Test: `tests/property/policy/test_quality_invariants.py`
- Test: `tests/fixtures/workload/h2-quality-pass.json`
- Test: `tests/fixtures/workload/h2-quality-unknown.json`
- Test: `tests/fixtures/workload/h2-quality-fail.json`

**Interfaces:**
- Consumes: `Sequence[PairedQualityRow]`, Wave 1 `cluster_bootstrap_ratios`, `QualityPolicy` from `quality-v1.json`.
- Produces: `QualityGateResult` and `evaluate_paired_quality(rows: Sequence[PairedQualityRow], policy: QualityPolicy) -> QualityGateResult`.

- [ ] **Step 1: Write failing threshold/completeness tests**

```python
def test_quality_requires_point_and_ucb(pass_rows, policy):
    result = evaluate_paired_quality(pass_rows, policy)
    assert result.overall.point_ratio <= .97
    assert result.overall.ucb95 <= .97

def test_any_small_fixed_subgroup_makes_whole_unknown(rows_with_n99, policy):
    assert evaluate_paired_quality(rows_with_n99, policy).verdict == GateVerdict.UNKNOWN
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/policy/test_quality_policy.py tests/property/policy/test_quality_invariants.py -q`

Expected: FAIL because `evaluate_paired_quality` is undefined.

- [ ] **Step 3: Implement fixed groups and fail-closed quality evaluation**

Compute groups outside predictor: weather is `clear` for `weathersit=1`, `mist` for `2`, and `adverse` for `{3,4}`; day type is `workingday_0` or `workingday_1`; demand period is `peak` for `hr in {7,8,9,16,17,18}` and `off_peak` otherwise. Require 2,000 valid pairs, overall/subgroup completeness, finite non-negative successes, positive stable MAE in every point/replicate, and both point/UCB thresholds. Do not omit sparse groups or reinterpret natural outcomes.

```python
def evaluate_paired_quality(rows: Sequence[PairedQualityRow],
                            policy: QualityPolicy) -> QualityGateResult:
    completeness = require_fixed_groups(rows, policy.groups, minimum=100)
    if not completeness.complete or len(rows) < 2000:
        return QualityGateResult.unknown("PAIR_OR_SUBGROUP_INCOMPLETE")
    bootstrap = cluster_bootstrap_ratios(rows, policy.groups, resamples=2000, seed=2026)
    return apply_ratio_thresholds(bootstrap, overall=0.97, subgroup=1.05)
```

- [ ] **Step 4: Verify golden and adversarial policy vectors**

Run: `uv run pytest tests/unit/policy/test_cluster_bootstrap.py tests/unit/policy/test_quality_policy.py tests/property/policy/test_quality_invariants.py -q`

Expected: synthetic PASS fixture reports overall 0.90/UCB 0.95, n99 and missing-label fixtures are UNKNOWN, threshold regressions are FAIL, row-IID sampler sentinel is never called.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/control/quality_policy.py tests/unit/policy tests/property/policy tests/fixtures/workload/h2-quality-*.json
git commit -m "feat: enforce paired quality policy"
```

### Task 4.4: Prove the policy truth table and UNKNOWN state invariants

**Files:**
- Test: `tests/property/control/test_policy_transition_properties.py`
- Test: `tests/unit/control/test_policy_truth_table.py`
- Modify: `src/mdcp/control/state_machine.py`
- Modify: `src/mdcp/control/transitions.py`

**Interfaces:**
- Consumes: sealed quality window and current release state.
- Produces: `quality_transition(verdict, state) -> TransitionIntent`; PASS from SHADOW targets CANARY_10, FAIL targets REJECTED, UNKNOWN targets PAUSED with `resume_state=SHADOW` and stable-only route.

- [ ] **Step 1: Write the failing complete truth table**

```python
@pytest.mark.parametrize("verdict,target", [
    (GateVerdict.PASS, ReleaseState.CANARY_10),
    (GateVerdict.FAIL, ReleaseState.REJECTED),
    (GateVerdict.UNKNOWN, ReleaseState.PAUSED),
])
def test_shadow_quality_transition(verdict, target):
    assert quality_transition(verdict, ReleaseState.SHADOW).target == target
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_policy_truth_table.py tests/property/control/test_policy_transition_properties.py -q`

Expected: FAIL because `quality_transition` is absent.

- [ ] **Step 3: Implement guarded transition intents**

Require matching window release/stable/revision/policy, immutable digest, current prerequisites, and non-stale evidence. UNKNOWN from VALIDATING/SHADOW/canary creates PAUSED stable-only revision; production UNKNOWN creates unresolved alert without PAUSED. Resume verifies cause-resolution evidence, all prerequisites, a fresh window ID, and a new route revision.

```python
def resolve_quality_verdict(state: ReleaseState, verdict: GateVerdict) -> SafetyAction:
    if verdict is GateVerdict.UNKNOWN and state in VALIDATION_OR_TRAFFIC_INCREASE_STATES:
        return SafetyAction.PAUSE_STABLE_ONLY
    if verdict is GateVerdict.UNKNOWN and state is ReleaseState.PRODUCTION:
        return SafetyAction.ALERT_AND_BLOCK_PROGRESSION
    return {GateVerdict.PASS: SafetyAction.ADVANCE,
            GateVerdict.FAIL: SafetyAction.REJECT}[verdict]
```

- [ ] **Step 4: Verify generated invariants**

Run: `uv run pytest tests/unit/control/test_policy_truth_table.py tests/property/control/test_policy_transition_properties.py -q`

Expected: UNKNOWN never reaches a promotion target, production never pauses, reused/stale window never advances, resume always changes window/revision, and tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/control/state_machine.py src/mdcp/control/transitions.py tests/unit/control/test_policy_truth_table.py tests/property/control/test_policy_transition_properties.py
git commit -m "feat: apply fail closed policy transitions"
```

### Task 4.5: Implement drift and traffic-comparability monitoring

**Files:**
- Create: `src/mdcp/policy/drift.py`
- Create: `configs/policy/drift-v1.json`
- Test: `tests/unit/policy/test_drift.py`
- Test: `tests/property/policy/test_drift_invariants.py`
- Test: `tests/fixtures/workload/drift-reference.json`

**Interfaces:**
- Consumes: 2011 month-matched reference, accepted request features, frozen bins/probabilities, epsilon `1e-6`.
- Produces: `evaluate_drift(reference, observed, policy) -> DriftResult` with PSI/JSD/schema/missingness, warning and comparability verdict.

- [ ] **Step 1: Write failing threshold/sample tests**

```python
def test_drift_under_300_is_unknown(reference, observed_299, policy):
    assert evaluate_drift(reference, observed_299, policy).verdict == GateVerdict.UNKNOWN

def test_month_specific_reference_is_required(reference, observed, policy):
    assert evaluate_drift(reference.with_month(1), observed.with_month(7), policy).reason == "DRIFT_REFERENCE_MONTH_MISMATCH"
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/policy/test_drift.py tests/property/policy/test_drift_invariants.py -q`

Expected: FAIL because drift evaluator is missing.

- [ ] **Step 3: Implement frozen PSI/JSD rules**

Use 2011 same-month deciles for `temp,atemp,hum,windspeed`, base-2 JSD for `weathersit,workingday,hr`, epsilon `1e-6`, minimum 300, warning PSI/JSD `0.20/0.10`, UNKNOWN PSI/JSD `0.30/0.20`, schema rejection >1%, or unexpected missingness. Drift does not claim quality degradation; during shadow/canary UNKNOWN pauses, after production it alerts/blocks new progression only.

```python
def drift_verdict(rows: Sequence[BikeRequest], reference: DriftReference) -> DriftResult:
    if len(rows) < 300 or schema_rejection_rate(rows) > 0.01:
        return DriftResult.unknown("INSUFFICIENT_OR_INVALID_TRAFFIC")
    psi = max(psi_same_month(rows, reference, field, epsilon=1e-6)
              for field in ("temp", "atemp", "hum", "windspeed"))
    jsd = max(jsd_base2(rows, reference, field, epsilon=1e-6)
              for field in ("weathersit", "workingday", "hr"))
    return classify_drift(psi, jsd, warn=(0.20, 0.10), unknown=(0.30, 0.20))
```

- [ ] **Step 4: Verify numerical vectors and claim boundary**

Run: `uv run pytest tests/unit/policy/test_drift.py tests/property/policy/test_drift_invariants.py -q`

Expected: frozen values match, sample 299 is UNKNOWN, thresholds are inclusive as specified, and no result field calls drift a quality failure.

- [ ] **Step 5: Commit**

```powershell
git add configs/policy/drift-v1.json src/mdcp/policy/drift.py tests/unit/policy tests/property/policy tests/fixtures/workload/drift-reference.json
git commit -m "feat: monitor release comparability drift"
```

### Task 4.6: Integrate shadow-window sealing with release progression

**Files:**
- Modify: `src/mdcp/control/app.py`
- Modify: `src/mdcp/control/api_evidence.py`
- Modify: `src/mdcp/control/window_service.py`
- Modify: `src/mdcp/control/transitions.py`
- Test: `tests/integration/control/test_quality_windows.py`
- Test: `tests/integration/control/test_shadow_to_canary.py`
- Test: `tests/integration/control/test_shadow_pause_resume.py`

**Interfaces:**
- Consumes: event/label endpoints, `WindowService`, `QualityGateResult`, current state transaction.
- Produces: `POST /v1/windows/{window_id}/seal`, auditable SHADOW -> CANARY_10/REJECTED/PAUSED behavior, fresh resume window.

- [ ] **Step 1: Write failing end-to-end quality decisions**

```python
def test_pass_window_opens_canary10(client, seeded_shadow_pass):
    response = client.post(f"/v1/windows/{seeded_shadow_pass}/seal")
    assert response.json()["next_state"] == "CANARY_10"

def test_unknown_pause_resume_opens_new_window(client, seeded_shadow_unknown):
    paused = client.post(f"/v1/windows/{seeded_shadow_unknown}/seal").json()
    resumed = client.post(paused["resume_url"], json=CAUSE_RESOLVED).json()
    assert resumed["window_id"] != seeded_shadow_unknown
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/integration/control/test_quality_windows.py tests/integration/control/test_shadow_to_canary.py tests/integration/control/test_shadow_pause_resume.py -q`

Expected: FAIL because seal endpoint/progression integration is absent.

- [ ] **Step 3: Implement one-shot seal/evaluate/transition orchestration**

Lock the open window, snapshot membership, seal/digest, evaluate policy, and issue an idempotent transition command referencing the sealed digest. Do not hold a DB transaction during bootstrap computation; recheck state/revision before transition. PASS commits CANARY_10 signed plan, FAIL commits REJECTED stable-only, UNKNOWN commits PAUSED stable-only. Resume never reopens the sealed window.

```python
def close_shadow(window_id: WindowId, command: CloseShadowCommand) -> TransitionResult:
    sealed = window_service.seal(window_id, command.database_now)
    quality = evaluate_paired_quality(load_sealed_pairs(sealed), command.policy)
    transition = shadow_action_for(quality.verdict)
    return transitions.commit_if_current(command.release_id, command.expected_revision,
                                         transition, evidence_digest=sealed.digest)
```

- [ ] **Step 4: Verify PASS/FAIL/UNKNOWN and race behavior**

Run: `uv run pytest tests/integration/control/test_quality_windows.py tests/integration/control/test_shadow_to_canary.py tests/integration/control/test_shadow_pause_resume.py -q`

Expected: all three paths store immutable receipts; concurrent duplicate seal produces one transition; stale evaluation becomes audited no-op; tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/control tests/integration/control/test_quality_windows.py tests/integration/control/test_shadow_to_canary.py tests/integration/control/test_shadow_pause_resume.py
git commit -m "feat: gate shadow progression on sealed quality"
```

## Wave 4 completion checkpoint

Run: `uv run alembic upgrade head; uv run pytest tests/unit/policy tests/unit/control/test_window_service.py tests/unit/control/test_policy_truth_table.py tests/property/policy tests/property/control/test_policy_transition_properties.py tests/integration/control/test_window_migration.py tests/integration/control/test_sealed_window_immutability.py tests/integration/control/test_event_ordering.py tests/integration/control/test_quality_windows.py tests/integration/control/test_shadow_to_canary.py tests/integration/control/test_shadow_pause_resume.py -q; git status --short`

Expected: M4 tests pass; every sealed digest recomputes, all fixed subgroups are visible, UNKNOWN cannot promote, Prometheus is not queried, duplicate/late/stale behavior is deterministic, and the worktree is clean.
