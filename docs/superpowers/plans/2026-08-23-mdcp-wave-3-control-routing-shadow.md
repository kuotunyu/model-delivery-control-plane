# MDCP Wave 3 Control Service, Signed Routing, and Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the durable release state core, one-time bootstrap, transactionally signed route plans, bounded router cache, exact response-source behavior, and non-blocking paired shadow evidence.

**Architecture:** FastAPI control and router are distinct processes sharing only versioned HTTP/Pydantic contracts. SQLAlchemy repositories use PostgreSQL transactions and Alembic migrations; the control service alone holds the Ed25519 private key. Router serves from a verified in-memory lease and writes evidence through control-service endpoints, never directly to PostgreSQL.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, psycopg 3, Alembic, PostgreSQL 16, cryptography Ed25519, RFC 8785, HMAC-SHA256, httpx, pytest, Hypothesis, Docker Compose.

## Global Constraints

- Entry requires Waves 0–2 PASS, including a real owner-authorized release-CI evidence bundle.
- Control service never loads ONNX, proxies predictions, invokes Docker, mounts Docker socket, or resolves MLflow aliases for traffic.
- Router never queries PostgreSQL/MLflow and never replaces a stable error/timeout with candidate output.
- Every committed lifecycle transition persists state/pointer/revision/signed route plan/audit/idempotency result in one transaction.
- Ed25519 private key is a control-only Compose secret; router contains the pinned public key/fingerprint.
- Poll and RPC deadline are 500 ms; lease is at most 1.5 seconds; expired lease is stable-only.
- EventIngest is `POST /v1/evidence/events` inside the control deployable, not a fifth service.
- Completion command: `uv run pytest tests/unit/control tests/unit/router tests/property/control tests/contract/control tests/contract/router tests/integration/control tests/integration/router -q`.

---

### Task 3.1: Create core PostgreSQL schema and migration order

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_environment_release_idempotency.py`
- Create: `migrations/versions/0002_route_plan_audit.py`
- Create: `migrations/versions/0003_request_evidence.py`
- Create: `src/mdcp/db/base.py`
- Create: `src/mdcp/db/session.py`
- Create: `src/mdcp/db/environment.py`
- Create: `src/mdcp/db/releases.py`
- Create: `src/mdcp/db/routing.py`
- Create: `src/mdcp/db/audit.py`
- Create: `src/mdcp/db/idempotency.py`
- Create: `src/mdcp/db/evidence.py`
- Test: `tests/integration/control/test_migrations.py`
- Test: `tests/integration/control/test_db_constraints.py`

**Interfaces:**
- Consumes: release object digests and PostgreSQL URL.
- Produces: `DatabaseSessionFactory`, focused repository classes, and schema revisions `0001`, `0002`, `0003`.

- [ ] **Step 1: Write failing migration/constraint tests**

```python
def test_uninitialized_environment_requires_null_pointer(db):
    db.execute("insert into environments(environment_id, initialized, active_release_id) values ('e', false, 'sha256:x')")
    with pytest.raises(IntegrityError):
        db.commit()

def test_terminal_identity_is_unique(db, terminal_event):
    db.add_all([terminal_event, terminal_event.copy_with(status="timeout")])
    with pytest.raises(IntegrityError):
        db.commit()
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/integration/control/test_migrations.py tests/integration/control/test_db_constraints.py -q`

Expected: FAIL because Alembic configuration and tables do not exist.

- [ ] **Step 3: Implement exact tables and constraints**

`environments`: PK `environment_id`, `initialized`, nullable `active_release_id`, `current_revision`, `policy_digest`, `signing_public_key_fingerprint`, timestamps, and initialized/pointer check. `releases`: PK `release_id`, environment FK, checked `state`, checked nullable `resume_state`, descriptor/manifest/bundle digests, digest-qualified OCI ref, numeric MLflow version, nullable retained previous release, `validated`, `runnable`. `idempotency_records`: PK `(environment_id,idempotency_key)`, request digest, stored response/status. `route_plans`: PK `(environment_id,revision)`, canonical JSON, digest, signature, policy/stable/candidate IDs, weights, created time. `audit_events`: UUID PK, transition fields, previous/event digests, insert-only application grants. `request_admissions`, `terminal_events`, `delayed_labels`: exact identities/foreign keys, duplicate counters, monotonic/UTC timestamps, fixed roles/statuses.

```python
def upgrade() -> None:
    op.create_table("environments",
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("initialized", sa.Boolean(), nullable=False),
        sa.Column("active_release_id", sa.Text(), nullable=True),
        sa.Column("current_revision", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("(NOT initialized) OR active_release_id IS NOT NULL"))
    op.create_index("ix_environment_revision", "environments",
                    ["environment_id", "current_revision"], unique=True)
```

- [ ] **Step 4: Verify upgrade, downgrade, permissions, and constraints**

Run: `uv run alembic upgrade head; uv run pytest tests/integration/control/test_migrations.py tests/integration/control/test_db_constraints.py -q; uv run alembic downgrade base; uv run alembic upgrade head`

Expected: migrations complete in order, tests pass, application role cannot update/delete `audit_events`, and final schema is at `0003`.

- [ ] **Step 5: Commit**

```powershell
git add alembic.ini migrations src/mdcp/db tests/integration/control/test_migrations.py tests/integration/control/test_db_constraints.py
git commit -m "feat: add durable control plane schema"
```

### Task 3.2: Define and sign canonical route plans

**Files:**
- Create: `src/mdcp/contracts/route.py`
- Create: `src/mdcp/control/route_signing.py`
- Create: `schemas/v1/route-plan.schema.json`
- Test: `tests/unit/control/test_route_signing.py`
- Test: `tests/contract/control/test_route_plan_schema.py`
- Modify: `tests/fixtures/crypto/route-plan-v1.json`

**Interfaces:**
- Consumes: Wave 0 canonical vectors, control private key path, router pinned public key/fingerprint.
- Produces: `LeaseContract`, `RouteWeights`, `RoutePlanPayload`, `SignedRoutePlan`, `RoutePlanSigner.sign(payload: RoutePlanPayload) -> SignedRoutePlan`, and `RoutePlanVerifier.verify(plan: SignedRoutePlan) -> RoutePlanPayload`.

- [ ] **Step 1: Write failing signing/pinned-key tests**

```python
def test_signer_round_trip(payload, signer, verifier):
    signed = signer.sign(payload)
    assert signed.payload_digest == sha256_hex(canonicalize_json(payload.model_dump(mode="json")))
    assert verifier.verify(signed) == payload

def test_wrong_pinned_key_fails(signed, other_verifier):
    with pytest.raises(RoutePlanTrustError, match="ROUTE_KEY_MISMATCH"):
        other_verifier.verify(signed)
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_route_signing.py tests/contract/control/test_route_plan_schema.py -q`

Expected: FAIL because route contracts/signers do not exist.

- [ ] **Step 3: Implement exact signed payload**

Bind environment, positive revision, policy digest, retained stable ID, optional candidate ID, integer stable/candidate/shadow bucket weights totaling 10,000, UTC created time, and lease contract `{version:1,poll_ms:500,rpc_deadline_ms:500,max_lease_ms:1500}`. Sign RFC-8785 canonical payload bytes; verify schema/digest/signature/fingerprint/weights before returning payload. Never serialize private material.

```python
class RoutePlanSigner:
    def sign(self, payload: RoutePlanPayload) -> SignedRoutePlan:
        body = canonicalize_json(payload.model_dump(mode="json"))
        return SignedRoutePlan(payload=payload, digest=sha256_hex(body),
                               signature_b64=b64encode(self._key.sign(body)).decode("ascii"),
                               key_fingerprint=self.fingerprint)
```

- [ ] **Step 4: Verify frozen vectors and schema**

Run: `uv run pytest tests/unit/control/test_route_signing.py tests/contract/control/test_route_plan_schema.py -q`

Expected: frozen bytes/signature match Wave 0, invalid weights/revision/key/digest fail fixed codes, and schema regeneration has zero diff.

- [ ] **Step 5: Commit**

```powershell
git add schemas/v1/route-plan.schema.json src/mdcp/contracts/route.py src/mdcp/control/route_signing.py tests/unit/control tests/contract/control tests/fixtures/crypto/route-plan-v1.json
git commit -m "feat: sign immutable route plans"
```

### Task 3.3: Implement state machine, one-time bootstrap, and atomic transitions

**Files:**
- Create: `src/mdcp/control/state_machine.py`
- Create: `src/mdcp/control/transitions.py`
- Create: `src/mdcp/control/api_releases.py`
- Create: `src/mdcp/control/dependencies.py`
- Create: `src/mdcp/control/app.py`
- Create: `docker/control.Dockerfile`
- Test: `tests/unit/control/test_state_machine.py`
- Test: `tests/property/control/test_transition_properties.py`
- Test: `tests/integration/control/test_bootstrap_transaction.py`
- Test: `tests/integration/control/test_transition_atomicity.py`

**Interfaces:**
- Consumes: `TransitionCommand(release_id, expected_state, expected_route_revision, policy_digest, evidence_window_id, idempotency_key, actor, reason_code)`, repositories, signer, validated bundle.
- Produces: `TransitionResult`, `POST /v1/environments/{environment_id}/bootstrap`, `POST /v1/releases`, and `POST /v1/releases/{release_id}/transitions`.

- [ ] **Step 1: Write failing transition/property tests**

```python
def test_production_cannot_pause(machine):
    assert machine.allowed(ReleaseState.PRODUCTION, ReleaseState.PAUSED) is False

@given(valid_transition_sequences())
def test_valid_sequences_keep_one_active_pointer(sequence, service):
    result = service.apply_all(sequence)
    assert result.active_pointer_count in {0, 1}
    assert not result.initialized or result.active_pointer_count == 1
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_state_machine.py tests/property/control/test_transition_properties.py tests/integration/control/test_bootstrap_transaction.py tests/integration/control/test_transition_atomicity.py -q`

Expected: FAIL because state machine and transition service are absent.

- [ ] **Step 3: Implement full allowed-transition table and transaction**

Encode spec §10.2 exactly. Bootstrap verifies `bootstrap_baseline`, environment uninitialized, public-key fingerprint, artifact/schema/runtime/supply-chain PASS; one transaction writes baseline `PRODUCTION`, singleton pointer, revision 1 signed stable plan, audit, and idempotency result. Every later command locks environment/release, checks expected state/revision, signs next plan inside the transaction, writes state/pointer/revision/plan/audit/receipt reference, and commits once. Exact retries return stored result; key/content mismatch rejects.

```python
def transition(command: TransitionCommand, session: Session) -> TransitionResult:
    with session.begin():
        environment = lock_environment(session, command.environment_id)
        previous = require_expected_state(environment, command)
        route = build_and_sign_next_plan(previous, command)
        result = persist_state_pointer_route_audit(session, previous, route, command)
        store_idempotent_result(session, command.idempotency_key, command.digest, result)
    return result
```

- [ ] **Step 4: Verify concurrency and failure injection**

Run: `uv run pytest tests/unit/control/test_state_machine.py tests/property/control/test_transition_properties.py tests/integration/control/test_bootstrap_transaction.py tests/integration/control/test_transition_atomicity.py -q`

Expected: concurrent bootstrap yields one success/one idempotent-or-conflict result, invalid transitions leave state/route unchanged, injected sign/insert failures expose no partial rows, `UNKNOWN` never promotes, and all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add docker/control.Dockerfile src/mdcp/control tests/unit/control/test_state_machine.py tests/property/control tests/integration/control/test_bootstrap_transaction.py tests/integration/control/test_transition_atomicity.py
git commit -m "feat: add atomic release transitions"
```

### Task 3.4: Implement route-plan API, deterministic assignment, and bounded cache

**Files:**
- Create: `src/mdcp/control/api_routes.py`
- Create: `src/mdcp/router/assignment.py`
- Create: `src/mdcp/router/route_client.py`
- Create: `src/mdcp/router/route_cache.py`
- Test: `tests/unit/router/test_assignment.py`
- Test: `tests/unit/router/test_route_cache.py`
- Test: `tests/contract/router/test_route_api.py`
- Test: `tests/fixtures/crypto/routing-buckets-v1.json`

**Interfaces:**
- Consumes: current committed `SignedRoutePlan`, pinned verifier, monotonic clock, request ID.
- Produces: `GET /v1/environments/{environment_id}/route-plan`, `route_bucket(request_id: str, release_id: str, route_revision: int, policy_routing_seed: bytes) -> int`, `RoutePlanClient.fetch(deadline_ms: Literal[500] = 500) -> SignedRoutePlan`, and `RoutePlanCache.bind_for_admission(now_ns: int) -> RouteSnapshot`.

- [ ] **Step 1: Write failing bucket/lease tests**

```python
def test_bucket_vector(vector):
    assert route_bucket(**vector.input) == vector.expected_bucket

def test_late_old_response_cannot_extend_beyond_two_seconds(cache, clock):
    cache.install(OLD_PLAN, received_ns=clock.at_ms(500))
    assert cache.bind_for_admission(clock.at_ms(2001)).mode == "stable_only"
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/router/test_assignment.py tests/unit/router/test_route_cache.py tests/contract/router/test_route_api.py -q`

Expected: FAIL because route assignment/client/cache are undefined.

- [ ] **Step 3: Implement HMAC routing and live-response-only lease renewal**

Use HMAC-SHA256 with NUL separators and `UINT64_BE(revision)`, first eight digest bytes modulo 10,000. API selects only the committed current row and sets `Cache-Control: no-store`. Client starts every 500 ms with hard 500-ms deadline; cache accepts monotonic nondecreasing verified revisions. Same revision renews only from a distinct within-deadline live response; cached/replayed/late responses do not. Expiry chooses signed retained stable; no prior stable returns not-ready 503.

```python
def route_bucket(request_id: str, release_id: str, route_revision: int,
                 policy_routing_seed: bytes) -> int:
    message = (request_id.encode("utf-8") + b"\0" + release_id.encode("utf-8") +
               b"\0" + struct.pack(">Q", route_revision))
    digest = hmac.digest(policy_routing_seed, message, "sha256")
    return int.from_bytes(digest[:8], "big") % 10_000
```

- [ ] **Step 4: Verify cross-platform/stale behavior**

Run: `uv run pytest tests/unit/router/test_assignment.py tests/unit/router/test_route_cache.py tests/contract/router/test_route_api.py -q`

Expected: bucket vectors match, old/lower/bad-signature plans reject, last precommit response expires by 2,000 ms, same-response replay cannot renew, and API never returns an uncommitted row.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/control/api_routes.py src/mdcp/router tests/unit/router tests/contract/router tests/fixtures/crypto/routing-buckets-v1.json
git commit -m "feat: add bounded signed route cache"
```

### Task 3.5: Guarantee one client-visible response source

**Files:**
- Create: `src/mdcp/router/proxy.py`
- Create: `src/mdcp/router/app.py`
- Create: `docker/router.Dockerfile`
- Test: `tests/unit/router/test_proxy.py`
- Test: `tests/property/router/test_single_response_source.py`
- Test: `tests/contract/router/test_router_api.py`

**Interfaces:**
- Consumes: `BikeRequest`, bound `RouteSnapshot`, stable/candidate predictor clients, W3C `traceparent`.
- Produces: router `POST /v1/predict`, `GET /health/ready`, `ProxyResult(client_response, admission_event, terminal_event)`, exactly one `response_source`.

- [ ] **Step 1: Write failing response-source tests**

```python
@given(router_outcomes())
def test_exactly_one_response_source(outcome, proxy):
    result = proxy.execute(outcome.request)
    assert len(result.client_visible_sources) == 1

def test_stable_failure_does_not_fail_over_to_shadow(proxy):
    assert proxy.shadow_with_stable_timeout().client_response.source == "stable"
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/router/test_proxy.py tests/property/router/test_single_response_source.py tests/contract/router/test_router_api.py -q`

Expected: FAIL because proxy/router app do not exist.

- [ ] **Step 3: Implement snapshot-at-admission proxying**

Validate envelope/request ID, bind one snapshot once, measure monotonic dispatch-to-full-response latency, send client-visible request only to HMAC-selected role, preserve safe error/timeout source, propagate traceparent without payload baggage, and emit response-source accounting. Never retry candidate after stable failure or vice versa.

```python
async def proxy_once(snapshot: RoutingSnapshot, request: BikeRequest) -> PredictionResponse:
    role = snapshot.assignment_for(request.request_id)
    started = time.perf_counter_ns()
    response = await snapshot.client_for(role).post("/v1/predict", json=request.model_dump())
    body = PredictionResponse.model_validate_json(await response.aread())
    emit_terminal(role=role, latency_ns=time.perf_counter_ns() - started, status=response.status_code)
    return body
```

- [ ] **Step 4: Verify all failure permutations**

Run: `uv run pytest tests/unit/router/test_proxy.py tests/property/router/test_single_response_source.py tests/contract/router/test_router_api.py -q`

Expected: every generated timeout/5xx/disconnect/invalid-response permutation has exactly one source, old in-flight request retains old revision, and tests pass.

- [ ] **Step 5: Commit**

```powershell
git add docker/router.Dockerfile src/mdcp/router/proxy.py src/mdcp/router/app.py tests/unit/router/test_proxy.py tests/property/router tests/contract/router/test_router_api.py
git commit -m "feat: enforce single response routing"
```

### Task 3.6: Add non-blocking shadow, idempotent ingest, and delayed labels

**Files:**
- Create: `src/mdcp/contracts/events.py`
- Create: `schemas/v1/evidence-event.schema.json`
- Create: `src/mdcp/router/shadow.py`
- Create: `src/mdcp/router/accounting.py`
- Create: `src/mdcp/control/api_evidence.py`
- Create: `src/mdcp/replay/request_ids.py`
- Create: `src/mdcp/replay/labels.py`
- Test: `tests/unit/router/test_shadow.py`
- Test: `tests/contract/control/test_evidence_api.py`
- Test: `tests/integration/router/test_shadow_nonblocking.py`
- Test: `tests/integration/control/test_delayed_labels.py`

**Interfaces:**
- Consumes: shadow route snapshot, identical `BikeRequest`, predictor results, delayed label source.
- Produces: `AdmissionEvent`, `TerminalEvent`, `DelayedLabelEvent`, `POST /v1/evidence/events`, `POST /v1/labels`, `ShadowExecutor.submit(request, snapshot) -> None`, deterministic `review_request_id(index, scenario) -> str`.

- [ ] **Step 1: Write failing non-blocking/idempotency tests**

```python
async def test_shadow_timeout_never_delays_stable(shadow_client):
    result = await shadow_client.predict(candidate_delay_ms=500)
    assert result.client_source == "stable"
    assert result.client_elapsed_ms < 100

def test_exact_duplicate_does_not_add_terminal(api, event):
    assert api.post(event).duplicate is False
    assert api.post(event).duplicate is True
    assert terminal_count(event.identity) == 1
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/router/test_shadow.py tests/contract/control/test_evidence_api.py tests/integration/router/test_shadow_nonblocking.py tests/integration/control/test_delayed_labels.py -q`

Expected: FAIL because event contracts and endpoints are absent.

- [ ] **Step 3: Implement independent shadow lifecycle and control-owned ingest**

Duplicate the identical request/policy/revision to candidate in an independent bounded task; stable completion never awaits it. Persist router admission and predictor terminal events through control endpoint. Exact duplicate increments a counter without denominator change; conflicting duplicate is stored as integrity conflict. Labels contain request ID/value/source digest/calendar day/arrival and join only evaluator-side after routing.

```python
def dispatch_shadow(snapshot: RoutingSnapshot, request: BikeRequest) -> None:
    task = asyncio.create_task(run_shadow(snapshot.candidate, request, snapshot.revision))
    SHADOW_TASKS.add(task)
    task.add_done_callback(SHADOW_TASKS.discard)

async def ingest_event(event: EvidenceEvent, session: Session) -> IngestResult:
    return upsert_by_event_identity(session, event, conflict_verdict=GateVerdict.UNKNOWN)
```

- [ ] **Step 4: Verify pairing, loss, and ordering cases**

Run: `uv run pytest tests/unit/router/test_shadow.py tests/contract/control/test_evidence_api.py tests/integration/router/test_shadow_nonblocking.py tests/integration/control/test_delayed_labels.py -q`

Expected: stable response timing is independent, paired rows share request/revision/policy, missing candidate/label remains visible, exact/conflicting duplicates differ, and late labels do not overwrite source rows.

- [ ] **Step 5: Commit**

```powershell
git add schemas/v1/evidence-event.schema.json src/mdcp/contracts/events.py src/mdcp/router src/mdcp/control/api_evidence.py src/mdcp/replay tests/unit/router tests/contract/control tests/integration/router tests/integration/control/test_delayed_labels.py
git commit -m "feat: capture paired shadow evidence"
```

### Task 3.7: Reconcile committed state after control/router restarts

**Files:**
- Create: `src/mdcp/control/reconciliation.py`
- Test: `tests/unit/control/test_reconciliation.py`
- Test: `tests/integration/control/test_control_restart.py`
- Test: `tests/integration/router/test_router_restart.py`
- Test: `tests/integration/control/test_shadow_lifecycle.py`
- Modify: `compose.feasibility.yaml`

**Interfaces:**
- Consumes: committed environment/release/route/audit rows and router cache startup state.
- Produces: `Reconciler.run_once(environment_id) -> ReconciliationResult`; safe result kinds `CONSISTENT`, `REPUBLISHED_CURRENT`, `SAFE_ROLLBACK_REQUIRED`, `BLOCKED_DB_UNAVAILABLE`.

- [ ] **Step 1: Write failing restart/reconciliation tests**

```python
def test_router_restart_has_no_candidate_before_signed_plan(restarted_router):
    assert restarted_router.ready is False
    assert restarted_router.candidate_admissions == 0

def test_control_restart_serves_committed_plan_only(restarted_control):
    assert restarted_control.route_plan.revision == restarted_control.environment.current_revision
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/control/test_reconciliation.py tests/integration/control/test_control_restart.py tests/integration/router/test_router_restart.py tests/integration/control/test_shadow_lifecycle.py -q`

Expected: FAIL because reconciliation/restart behavior is missing.

- [ ] **Step 3: Implement reconstruction and safe outcomes**

Every five seconds compare state, pointer, current revision, signed plan, audit digest chain, and validated releases. Serve/re-publish only the committed current row; detect split/tampered state and request a safety transition rather than inventing rows. Database outage stops transitions; router uses lease then stable-only. Router restart begins without lease and permits candidate only after current signature verification.

```python
def reconcile_environment(environment_id: UUID, session: Session) -> ReconciliationResult:
    committed = load_committed_snapshot(session, environment_id)
    verify_audit_chain(committed.audit_events)
    verify_signed_route(committed.route_plan)
    if not committed.is_consistent:
        return request_stable_only_safety_transition(committed)
    return ReconciliationResult.publish(committed.route_plan)
```

- [ ] **Step 4: Verify restart and M3 lifecycle**

Run: `uv run pytest tests/unit/control/test_reconciliation.py tests/integration/control/test_control_restart.py tests/integration/router/test_router_restart.py tests/integration/control/test_shadow_lifecycle.py -q`

Expected: pre-bootstrap returns controlled 503, bootstrap becomes ready, validated candidate reaches shadow, stable remains sole client source, restart never emits unleased candidate traffic, and all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add compose.feasibility.yaml src/mdcp/control/reconciliation.py tests/unit/control/test_reconciliation.py tests/integration/control/test_control_restart.py tests/integration/router/test_router_restart.py tests/integration/control/test_shadow_lifecycle.py
git commit -m "feat: reconcile control and router restarts"
```

## Wave 3 completion checkpoint

Run: `uv run alembic upgrade head; uv run pytest tests/unit/control tests/unit/router tests/property/control tests/property/router tests/contract/control tests/contract/router tests/integration/control tests/integration/router -q; git status --short`

Expected: M3 lifecycle tests pass; bootstrap pointer invariant, signature vectors, HMAC buckets, 500/500/1500-ms cache behavior, controlled 503, single response source, shadow non-blocking, delayed labels, transaction atomicity, and restart safety all have executable evidence; worktree is clean.
