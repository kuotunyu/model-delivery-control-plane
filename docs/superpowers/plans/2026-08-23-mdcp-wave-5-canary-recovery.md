# MDCP Wave 5 Canary, Rollback, Quarantine, and Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement admission-based canary gates, staged progression, deterministic safeguards, atomic rollback/quarantine/manual safety actions, frozen-set convergence, recovery, and recomputable decision receipts.

**Architecture:** Canary policy is a pure evaluator over durable events with distinct denominators. Safety transitions use the existing atomic transition service and add convergence/recovery tables. Fault profiles are explicit test-plan inputs and never mingle with natural evidence. A receipt assembler binds the immutable identity chain to all state/window/route/convergence evidence.

**Tech Stack:** Python 3.12, Pydantic, SQLAlchemy/PostgreSQL, Alembic, FastAPI, NumPy, cgroup v2, pytest, Hypothesis, Docker Compose, and RFC-8785/Ed25519 interfaces from earlier waves.

## Global Constraints

- Entry requires Wave 4 PASS and immutable quality/window contracts.
- Candidate admission is counted once by `(request_id, release_id, route_revision)`; terminal identity additionally includes execution role.
- Application errors and accounting use all candidate admissions; schema validity uses candidate 2xx; latency p95 uses only successful schema-valid candidate terminal responses.
- Stage targets are two consecutive PASS windows: CANARY_10 `300`, CANARY_25 `500`, CANARY_50 `1000` candidate admissions per window, each with 15-minute maximum.
- p95 is nearest rank `ceil(0.95*n)` on integer microseconds; cgroup v2 `memory.peak` is reset after warm-up and <=256 MiB under a 384 MiB hard limit.
- Atomic control-plane rollback has bounded data-plane convergence; never claim instantaneous global rollback.
- Completion command: `uv run pytest tests/unit/policy/test_canary_policy.py tests/property/control/test_safety_properties.py tests/integration/control/test_canary_lifecycle.py tests/integration/control/test_recovery.py tests/integration/test_golden_rollback.py -q`.

---

### Task 5.1: Freeze canary denominators, quantiles, and memory evidence

**Files:**
- Create: `src/mdcp/policy/denominators.py`
- Create: `src/mdcp/policy/quantiles.py`
- Create: `src/mdcp/control/canary_policy.py`
- Create: `configs/policy/canary-v1.json`
- Test: `tests/unit/policy/test_denominators.py`
- Test: `tests/unit/policy/test_quantiles.py`
- Test: `tests/unit/policy/test_canary_policy.py`
- Test: `tests/property/policy/test_canary_denominators.py`

**Interfaces:**
- Consumes: `Sequence[CanaryEvent]`, verified post-warm-up `memory_peak_bytes`, `CanaryPolicy`.
- Produces: `CanaryGateResult`, `nearest_rank_us(samples: Sequence[int], percentile: Literal[0.95] = 0.95) -> int`, `evaluate_canary_window(events: Sequence[CanaryEvent], policy: CanaryPolicy) -> CanaryGateResult`.

- [ ] **Step 1: Write failing denominator/quantile tests**

```python
def test_failures_remain_in_admission_denominator(events):
    result = evaluate_canary_window(events.with_one_timeout_one_5xx(), POLICY)
    assert result.application_error.denominator == result.candidate_admissions
    assert result.application_error.numerator == 2
    assert result.latency.denominator == result.successful_schema_valid_count

def test_nearest_rank_has_no_interpolation():
    assert nearest_rank_us(list(range(1, 101)), .95) == 95
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/policy/test_denominators.py tests/unit/policy/test_quantiles.py tests/unit/policy/test_canary_policy.py tests/property/policy/test_canary_denominators.py -q`

Expected: FAIL because denominator/quantile evaluators are absent.

- [ ] **Step 3: Implement exact metric sets and verdict rules**

Deduplicate admissions, classify timeout/5xx/crash/disconnect as application errors, count exactly-one terminal for accounting, divide schema-valid 2xx by all 2xx, and admit latency only for successful schema-valid terminals. Exact duplicate changes only duplicate count; conflict is UNKNOWN. Convert monotonic ns with ceiling division. Missing/unresettable cgroup peak makes whole window UNKNOWN; >256 MiB is FAIL; OOM/restart is hard FAIL.

```python
def evaluate_canary_window(events: Sequence[CanaryEvent],
                           policy: CanaryPolicy) -> CanaryGateResult:
    accounted = deduplicate_admissions_and_terminals(events)
    if accounted.has_conflict or accounted.memory_peak is None:
        return CanaryGateResult.unknown(accounted.reason_code)
    if accounted.memory_peak > 256 * MIB or accounted.oom_or_restart:
        return CanaryGateResult.fail("MEMORY_OR_RESTART")
    return apply_operational_slo(accounted, policy, quantile=nearest_rank(0.95))
```

- [ ] **Step 4: Verify generated failure permutations**

Run: `uv run pytest tests/unit/policy/test_denominators.py tests/unit/policy/test_quantiles.py tests/unit/policy/test_canary_policy.py tests/property/policy/test_canary_denominators.py -q`

Expected: no timeout/5xx/crash disappears, duplicate cannot grow a denominator, nearest-rank vectors match on all platforms, and PASS/FAIL/UNKNOWN truth table is exact.

- [ ] **Step 5: Commit**

```powershell
git add configs/policy/canary-v1.json src/mdcp/policy/denominators.py src/mdcp/policy/quantiles.py src/mdcp/control/canary_policy.py tests/unit/policy tests/property/policy/test_canary_denominators.py
git commit -m "feat: freeze canary operational gates"
```

### Task 5.2: Implement two-window canary stage progression

**Files:**
- Modify: `src/mdcp/control/window_service.py`
- Modify: `src/mdcp/control/transitions.py`
- Test: `tests/unit/control/test_canary_progression.py`
- Test: `tests/property/control/test_canary_progression_properties.py`
- Test: `tests/integration/control/test_canary_lifecycle.py`

**Interfaces:**
- Consumes: sealed `CanaryGateResult`, current stage/revision, consecutive-window history.
- Produces: `CanaryStage`, `CanaryAction`, `next_canary_action(stage: CanaryStage, windows: Sequence[CanaryGateResult]) -> CanaryAction`, and exact signed weight plans 10/90, 25/75, 50/50, production 100/0 active mapping.

- [ ] **Step 1: Write failing stage-window tests**

```python
@pytest.mark.parametrize("state,target,count", [
    ("CANARY_10", "CANARY_25", 300),
    ("CANARY_25", "CANARY_50", 500),
    ("CANARY_50", "PRODUCTION", 1000),
])
def test_two_consecutive_passes_advance(state, target, count, service):
    assert service.apply_windows(state, pass_window(count), pass_window(count)).target == target
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_canary_progression.py tests/property/control/test_canary_progression_properties.py tests/integration/control/test_canary_lifecycle.py -q`

Expected: FAIL because canary progression is not connected to transitions.

- [ ] **Step 3: Implement consecutive immutable windows and exact weights**

Open windows by unique candidate-admission target or 15-minute duration. Require two consecutive PASS windows with identical release/stage/policy and monotonic revisions; UNKNOWN pauses stable-only, FAIL rolls back. Progression commits a fresh signed plan and resets consecutive count. Promotion stores candidate as active pointer and retained prior stable while plan keeps prior stable fallback/candidate active at 10,000 buckets.

```python
def next_canary_action(stage: CanaryStage, windows: Sequence[CanaryGateResult]) -> CanaryAction:
    latest = tuple(windows[-2:])
    if latest and latest[-1].verdict is GateVerdict.FAIL:
        return CanaryAction.ROLLBACK
    if latest and latest[-1].verdict is GateVerdict.UNKNOWN:
        return CanaryAction.PAUSE_STABLE_ONLY
    if len(latest) == 2 and all(w.verdict is GateVerdict.PASS for w in latest):
        return stage.advance_action()
    return CanaryAction.HOLD
```

- [ ] **Step 4: Verify interruption and stale-result behavior**

Run: `uv run pytest tests/unit/control/test_canary_progression.py tests/property/control/test_canary_progression_properties.py tests/integration/control/test_canary_lifecycle.py -q`

Expected: one PASS never advances, PASS+UNKNOWN pauses, PASS+FAIL rolls back, duration-short sample is UNKNOWN, duplicate evaluator result cannot skip a stage, and tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/control/window_service.py src/mdcp/control/transitions.py tests/unit/control/test_canary_progression.py tests/property/control/test_canary_progression_properties.py tests/integration/control/test_canary_lifecycle.py
git commit -m "feat: add staged canary progression"
```

### Task 5.3: Add explicit deterministic fault profiles and hard safeguards

**Files:**
- Create: `src/mdcp/predictor/fault_profiles.py`
- Modify: `src/mdcp/predictor/app.py`
- Create: `src/mdcp/replay/scenarios.py`
- Test: `tests/unit/predictor/test_fault_profiles.py`
- Test: `tests/unit/control/test_hard_safeguards.py`
- Test: `tests/integration/control/test_failure_injection.py`
- Test: `tests/fixtures/reviewer/fault-plan-v1.json`

**Interfaces:**
- Consumes: signed route plan fault field and deterministic HMAC-selected request IDs.
- Produces: profiles `latency_plus_30ms`, `error_rate`, `memory_pad`, `subgroup_corruption`, `telemetry_drop`, `duplicate_conflict`, `out_of_order`, `stale_route_revision`; `hard_safeguard(events: Sequence[CanaryEvent]) -> RollbackIntent | None`.

- [ ] **Step 1: Write failing profile-label and safeguard tests**

```python
def test_latency_profile_is_declared_everywhere(run):
    assert {e.fault_profile for e in run.events} == {"latency_plus_30ms"}
    assert run.evidence_class == EvidenceClass.INJECTED_TEST

def test_one_candidate_restart_triggers_rollback(events):
    assert hard_safeguard(events.with_candidate_restart()).reason_code == "CANARY_CANDIDATE_RESTART"
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/predictor/test_fault_profiles.py tests/unit/control/test_hard_safeguards.py tests/integration/control/test_failure_injection.py -q`

Expected: FAIL because fault profiles/safeguards are missing.

- [ ] **Step 3: Implement bounded, labeled injections**

Apply latency after validation, 5xx by deterministic bucket, memory padding above 256 but below 384 MiB, fixed subgroup output corruption, and event/order faults only when a signed test plan declares them. One OOM/restart/conflicting response/artifact inconsistency rolls back immediately; error rate >5% after 50 admissions also does. Preserve partial FAIL window and mark release ineligible for natural production claims.

```python
def apply_fault(plan: SignedFaultPlan, request: BikeRequest,
                prediction: float) -> FaultOutcome:
    verify_test_only_plan(plan)
    bucket = deterministic_fault_bucket(request.request_id, plan.seed)
    if bucket < plan.http_5xx_buckets:
        return FaultOutcome.http_5xx()
    corrupted = corrupt_fixed_subgroup(prediction, request, plan.subgroup_rule)
    return FaultOutcome.success(corrupted, latency_ms=plan.latency_ms,
                                memory_padding_mib=plan.memory_padding_mib)

def hard_safeguard(events: Sequence[CanaryEvent]) -> RollbackIntent | None:
    facts = CanaryFacts.from_events(events)
    if facts.oom_or_restart or facts.conflicting_response or facts.artifact_inconsistent:
        return RollbackIntent(reason_code=facts.first_hard_failure)
    if facts.admissions >= 50 and facts.application_error_rate > 0.05:
        return RollbackIntent(reason_code="CANARY_ERROR_RATE_HARD_LIMIT")
    return None
```

- [ ] **Step 4: Verify bounds and evidence separation**

Run: `uv run pytest tests/unit/predictor/test_fault_profiles.py tests/unit/control/test_hard_safeguards.py tests/integration/control/test_failure_injection.py -q`

Expected: each profile is deterministic, bounded memory never exhausts host, all events/windows/receipts carry the profile, natural and injected samples never pool, and safeguards emit one idempotent rollback intent.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/predictor src/mdcp/replay/scenarios.py tests/unit/predictor tests/unit/control/test_hard_safeguards.py tests/integration/control/test_failure_injection.py tests/fixtures/reviewer/fault-plan-v1.json
git commit -m "feat: add labeled canary fault profiles"
```

### Task 5.4: Implement atomic rollback, quarantine, and manual safety commands

**Files:**
- Modify: `src/mdcp/control/transitions.py`
- Modify: `src/mdcp/control/api_releases.py`
- Test: `tests/property/control/test_safety_properties.py`
- Test: `tests/integration/control/test_rollback_transaction.py`
- Test: `tests/integration/control/test_quarantine_transaction.py`
- Test: `tests/integration/control/test_manual_override.py`

**Interfaces:**
- Consumes: expected state/revision, retained previous stable, reason/evidence, manual actor/expiry.
- Produces: `rollback(command: RollbackCommand) -> TransitionResult`, `quarantine(command: QuarantineCommand) -> TransitionResult`, `pause(command: PauseCommand) -> TransitionResult`, `resume(command: ResumeCommand) -> TransitionResult`; no arbitrary weight command.

- [ ] **Step 1: Write failing atomic safety tests**

```python
def test_production_quarantine_restores_retained_stable(service, production_release):
    result = service.quarantine(production_release.command())
    assert result.state == "QUARANTINED"
    assert result.active_release_id == production_release.retained_previous_release_id
    assert result.route_weights == {"stable": 10_000, "candidate": 0}

def test_pause_expiry_never_resumes(service, paused_release, clock):
    clock.advance(days=2)
    assert service.reconcile(paused_release).state == "PAUSED"
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/property/control/test_safety_properties.py tests/integration/control/test_rollback_transaction.py tests/integration/control/test_quarantine_transaction.py tests/integration/control/test_manual_override.py -q`

Expected: FAIL because safety transaction variants are incomplete.

- [ ] **Step 3: Implement safety-reducing transactions only**

Canary rollback sets candidate 0/stable 10,000 and ROLLED_BACK; shadow/canary trust failure sets candidate 0/stable 10,000 and QUARANTINED; production trust failure restores retained validated/runnable stable pointer and quarantines candidate. Missing retained stable makes environment not-ready/503, never serve compromised artifact. Manual permits PAUSE only VALIDATING/SHADOW/canary and ROLLBACK only client-visible canary/PRODUCTION; expiry stays paused; resume revalidates cause/prerequisites and opens a new window/revision.

```python
def rollback(command: RollbackCommand, session: Session) -> TransitionResult:
    with session.begin():
        environment = lock_environment(session, command.environment_id)
        candidate = lock_release(session, command.release_id)
        stable = require_validated_runnable_fallback(session, candidate.retained_previous_release_id)
        plan = sign_stable_only_plan(environment, stable.release_id, environment.current_revision + 1)
        return persist_state_pointer_route_audit(session, candidate, stable, plan,
                                                 target_state=ReleaseState.ROLLED_BACK)
```

- [ ] **Step 4: Verify concurrency/idempotency and forbidden controls**

Run: `uv run pytest tests/property/control/test_safety_properties.py tests/integration/control/test_rollback_transaction.py tests/integration/control/test_quarantine_transaction.py tests/integration/control/test_manual_override.py -q`

Expected: state/pointer/weight/plan/audit are atomic, retries return one result, stale commands do not mutate, arbitrary weight/promotion/UNKNOWN bypass/quarantine recovery are rejected, and tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/control tests/property/control/test_safety_properties.py tests/integration/control/test_rollback_transaction.py tests/integration/control/test_quarantine_transaction.py tests/integration/control/test_manual_override.py
git commit -m "feat: enforce atomic safety transitions"
```

### Task 5.5: Freeze router convergence sets and restart-safe acknowledgements

**Files:**
- Create: `migrations/versions/0005_convergence_recovery.py`
- Create: `src/mdcp/db/recovery.py`
- Modify: `src/mdcp/contracts/events.py`
- Modify: `src/mdcp/control/api_routes.py`
- Modify: `src/mdcp/control/reconciliation.py`
- Modify: `src/mdcp/router/route_client.py`
- Test: `tests/unit/control/test_convergence.py`
- Test: `tests/integration/control/test_convergence_set.py`
- Test: `tests/integration/router/test_restart_convergence.py`

**Interfaces:**
- Consumes: heartbeat `(environment_id,instance_id,boot_id,ready,observed_revision,time)`, route commit time, acknowledgement.
- Produces: `RouterHeartbeat`, `RouteAcknowledgement`, `POST /v1/routers/heartbeat`, `POST /v1/routers/acknowledgements`, `required_convergence_set`, and `ConvergenceResult`.

- [ ] **Step 1: Write failing frozen-set/restart tests**

```python
def test_commit_freezes_preceding_one_second_set(service, heartbeats, commit_time):
    frozen = service.freeze_set(commit_time)
    assert frozen.members == heartbeats.ready_between(commit_time - timedelta(seconds=1), commit_time)

def test_crash_cannot_remove_member_to_make_pass(convergence):
    result = convergence.with_member_crash().evaluate()
    assert result.verdict != GateVerdict.PASS
    assert result.original_member_count == result.final_member_count
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_convergence.py tests/integration/control/test_convergence_set.py tests/integration/router/test_restart_convergence.py -q`

Expected: FAIL because convergence schema/service is absent.

- [ ] **Step 3: Implement migration, heartbeat/ack endpoints, and SLA evaluator**

Create router instances, immutable convergence sets/members, acknowledgements, recovery incidents/windows. Snapshot registered ready heartbeats from the exact preceding one second in the route-changing transaction. PASS requires every frozen member continuously ready and acknowledging by commit+2 seconds plus zero candidate admissions after deadline. Empty set blocks traffic increase but never blocks rollback/quarantine. New boot ID starts stable-only and is additional recovery evidence, not member replacement.

```python
def freeze_convergence_set(session: Session, environment_id: UUID,
                           committed_at: datetime) -> ConvergenceSet:
    members = ready_heartbeats(session, environment_id,
                              since=committed_at - timedelta(seconds=1),
                              until=committed_at)
    return persist_immutable_convergence_set(session, environment_id, committed_at, members)
```

- [ ] **Step 4: Verify lease-margin and frozen membership**

Run: `uv run alembic upgrade 0005; uv run pytest tests/unit/control/test_convergence.py tests/integration/control/test_convergence_set.py tests/integration/router/test_restart_convergence.py -q`

Expected: last valid precommit response at +500 ms expires at +2,000 ms, post-deadline candidate count is zero, crash remains pending/fail until safe restart, and membership cannot shrink.

- [ ] **Step 5: Commit**

```powershell
git add migrations/versions/0005_convergence_recovery.py src/mdcp/db/recovery.py src/mdcp/contracts/events.py src/mdcp/control/api_routes.py src/mdcp/control/reconciliation.py src/mdcp/router/route_client.py tests/unit/control/test_convergence.py tests/integration/control/test_convergence_set.py tests/integration/router/test_restart_convergence.py
git commit -m "feat: verify bounded router convergence"
```

### Task 5.6: Verify two-window recovery and produce decision receipts

**Files:**
- Create: `src/mdcp/contracts/receipts.py`
- Create: `schemas/v1/decision-receipt.schema.json`
- Create: `src/mdcp/control/recovery_service.py`
- Create: `src/mdcp/verify/receipt.py`
- Modify: `src/mdcp/verify/cli.py`
- Modify: `src/mdcp/replay/scenarios.py`
- Test: `tests/unit/control/test_recovery.py`
- Test: `tests/unit/verify/test_receipt.py`
- Test: `tests/integration/control/test_recovery.py`
- Test: `tests/integration/test_golden_rollback.py`
- Test: `tests/fixtures/reviewer/golden-receipt.json`

**Interfaces:**
- Consumes: two stable recovery windows, release/bundle/window/transition/route/convergence evidence.
- Produces: `DecisionReceipt`, `RecoveryService.evaluate(incident_id: UUID) -> RecoveryResult`, `verify_decision_receipt(path: Path) -> VerificationResult`, and CLI grammar `python -m mdcp.verify.cli receipt --path RECEIPT_PATH`.

- [ ] **Step 1: Write failing recovery/receipt tests**

```python
def test_incident_closes_only_after_two_recovery_passes(service, incident):
    assert service.add_window(incident, PASS_RECOVERY).status == "RECOVERY_PENDING"
    assert service.add_window(incident, PASS_RECOVERY).status == "RECOVERED"

def test_receipt_recomputes_decision(golden_receipt):
    result = verify_decision_receipt(golden_receipt)
    assert result.verdict == GateVerdict.PASS
    assert result.recorded_decision == "ROLLED_BACK"
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_recovery.py tests/unit/verify/test_receipt.py tests/integration/control/test_recovery.py tests/integration/test_golden_rollback.py -q`

Expected: FAIL because recovery service/receipt types are absent.

- [ ] **Step 3: Implement recovery and canonical receipt assembly**

Each recovery window requires 300 stable admissions, <=1% stable errors, <=25-ms p95, 100% schema-valid 2xx, >=99.9% accounting, convergence/restart-safe evidence, and zero post-deadline candidate admissions. Assemble candidate/stable manifests/descriptors, MLflow versions, OCI/supply-chain/policy/routing digests, all windows/transitions/plans, frozen set/acks/restarts, recovery and evidence-class labels. Offline verifier recomputes every digest and policy decision without claiming omitted raw data or DBA tamper protection.

```python
def verify_decision_receipt(path: Path) -> VerificationResult:
    receipt = DecisionReceipt.model_validate_json(path.read_text(encoding="utf-8"))
    checks = verify_receipt_member_digests(receipt)
    checks.extend(recompute_policy_decisions(receipt))
    checks.extend(verify_route_and_audit_chain(receipt))
    return VerificationResult.from_checks(checks, accepted_risks=receipt.accepted_risks)
```

- [ ] **Step 4: Verify the better-offline-but-slower golden rollback**

Run: `uv run pytest tests/unit/control/test_recovery.py tests/unit/verify/test_receipt.py tests/integration/control/test_recovery.py tests/integration/test_golden_rollback.py -q; uv run python -m mdcp.verify.cli receipt --path tests/fixtures/reviewer/golden-receipt.json`

Expected: synthetic H1/H2 PASS, first CANARY_10 window p95 >25 ms under `latency_plus_30ms`, automatic rollback, bounded convergence, two recovery PASS windows, and verifier prints `RECEIPT PASS decision=ROLLED_BACK evidence=INJECTED_TEST`.

- [ ] **Step 5: Commit**

```powershell
git add schemas/v1/decision-receipt.schema.json src/mdcp/contracts/receipts.py src/mdcp/control/recovery_service.py src/mdcp/verify src/mdcp/replay/scenarios.py tests/unit/control/test_recovery.py tests/unit/verify tests/integration/control/test_recovery.py tests/integration/test_golden_rollback.py tests/fixtures/reviewer/golden-receipt.json
git commit -m "feat: verify rollback recovery receipts"
```

## Wave 5 completion checkpoint

Run: `uv run alembic upgrade head; uv run pytest tests/unit/policy tests/unit/control tests/unit/predictor tests/unit/verify tests/property/control tests/property/policy tests/integration/control tests/integration/router tests/integration/test_golden_rollback.py -q; uv run python -m mdcp.verify.cli receipt --path tests/fixtures/reviewer/golden-receipt.json; git status --short`

Expected: M5 gates pass, all safety transitions are atomic/idempotent, frozen router sets cannot be rewritten, recovery requires two windows, injected evidence is labeled, receipt recomputes, and worktree is clean.
