# MDCP Wave 6 Observability and Reviewer Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision bounded observability and a CPU-only, offline, warm-image reviewer path that demonstrates validation, shadow, canary failure, rollback, convergence, recovery, and receipt verification within five minutes.

**Architecture:** Durable PostgreSQL evidence remains the decision source while services expose low-cardinality Prometheus mirrors. Exactly three provisioned Grafana dashboards read those metrics. A deterministic replay container and PowerShell entry point orchestrate prebuilt synthetic fixtures, cgroup measurement, fault injection, and receipt export without UCI, retraining, GPU, GitHub CLI, or Kubernetes.

**Tech Stack:** Prometheus, Grafana, FastAPI/prometheus-client, Docker Compose, PowerShell 7, Python asyncio/httpx, Linux cgroup v2, pytest, and the Wave 5 golden scenario.

## Global Constraints

- Entry requires Wave 5 PASS and a recomputable golden rollback receipt.
- Grafana is read-only and has exactly three dashboards: Release Overview, Canary Comparison, Decision Timeline.
- Prometheus/Grafana outages cannot alter durable policy decisions.
- Dynamic metric labels are limited to release ID, execution role, stage, status class, fixed subgroup, fixed reason code, service name, and evidence class; request IDs/payloads/raw exceptions/paths/tokens are forbidden.
- Warm reviewer scenarios must run with 8 GB available RAM, CPU only, and no network/UCI/retraining/GPU/GitHub CLI/Kubernetes/paid API.
- The conservative request schedule is 212.5 seconds with 87.5 seconds remaining; a measured warm path over 300 seconds fails M6 without reducing any count or threshold.
- Every reviewer receipt, report, and Canary Comparison dashboard shows `measurement_mode`; unsupported reset selects a fresh candidate and `WHOLE_LIFETIME_PEAK_UPPER_BOUND` without weakening the 256 MiB policy threshold or 384 MiB hard limit.
- Public reviewer evidence contains no username, absolute local path, raw container ID, hostname, secret, or raw environment dump.
- Completion command: `pwsh ./scripts/demo.ps1 -Scenario GoldenRollback -Warm -Verify; pwsh ./scripts/demo.ps1 -Scenario FullSuccess -Warm -Verify`.

---

### Task 6.1: Freeze metric names, labels, and service instrumentation

**Files:**
- Create: `src/mdcp/observability/metric_names.py`
- Create: `src/mdcp/control/metrics.py`
- Create: `src/mdcp/router/metrics.py`
- Create: `src/mdcp/predictor/metrics.py`
- Modify: `src/mdcp/control/app.py`
- Modify: `src/mdcp/router/app.py`
- Modify: `src/mdcp/predictor/app.py`
- Test: `tests/unit/observability/test_metric_catalogue.py`
- Test: `tests/contract/observability/test_metrics_endpoints.py`

**Interfaces:**
- Consumes: control/router/predictor domain events.
- Produces: `/metrics` on each service and frozen names `mdcp_requests_total`, `mdcp_predictor_rpc_latency_seconds`, `mdcp_route_revision`, `mdcp_route_plan_age_seconds`, `mdcp_router_ack_lag_seconds`, `mdcp_candidate_errors_total`, `mdcp_candidate_memory_peak_bytes`, `mdcp_candidate_memory_measurement_mode`, `mdcp_window_progress_ratio`, `mdcp_label_completeness_ratio`, `mdcp_subgroup_denominator`, `mdcp_gate_verdict`, `mdcp_transition_total`, `mdcp_validator_checks_total`.

- [ ] **Step 1: Write failing label/cardinality tests**

```python
def test_metric_catalogue_uses_only_allowed_labels(catalogue):
    allowed = {"release_id", "execution_role", "stage", "status_class", "subgroup",
               "reason_code", "service", "evidence_class"}
    assert set().union(*(m.labels for m in catalogue)) <= allowed

def test_latency_histogram_contains_policy_boundary(catalogue):
    assert .025 in catalogue["mdcp_predictor_rpc_latency_seconds"].buckets

def test_memory_mode_is_bounded_without_container_identity_label(catalogue):
    metric = catalogue["mdcp_candidate_memory_measurement_mode"]
    assert metric.allowed_values == {"FD_LOCAL_POST_WARMUP_PEAK": 1,
                                     "WHOLE_LIFETIME_PEAK_UPPER_BOUND": 2}
    assert "container_id" not in metric.labels
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/observability/test_metric_catalogue.py tests/contract/observability/test_metrics_endpoints.py -q`

Expected: FAIL because metric catalogue/endpoints are absent.

- [ ] **Step 3: Implement bounded mirrors**

Define the exact catalogue once and have service wrappers update it from durable outcomes. Never use metric output to call transition code. Sanitize exception/status to fixed classes; expose W3C trace context only in request headers/log correlation and never baggage payloads. Include the 25-ms latency bucket. Encode the two measurement modes as documented numeric values rather than a new unbounded label; dashboards translate 1/2 back to the exact mode name.

```python
REQUESTS = Counter("mdcp_requests_total", "Completed requests",
                   ("service", "release_id", "execution_role", "status_class"))
LATENCY = Histogram("mdcp_predictor_rpc_latency_seconds", "Full-body latency",
                    ("service", "release_id", "execution_role"),
                    buckets=(0.005, 0.010, 0.015, 0.020, 0.025, 0.050, 0.100))
WINDOW_VERDICT = Gauge("mdcp_gate_verdict", "Durable sealed-window verdict",
                       ("release_id", "stage", "status_class"))
MEMORY_MODE = Gauge("mdcp_candidate_memory_measurement_mode",
                    "1=FD local post-warm-up, 2=whole-lifetime upper bound",
                    ("release_id", "evidence_class"))
```

- [ ] **Step 4: Verify endpoints and decision isolation**

Run: `uv run pytest tests/unit/observability/test_metric_catalogue.py tests/contract/observability/test_metrics_endpoints.py -q`

Expected: all metric names/help/types/labels match catalogue, forbidden-label scan is empty, and monkeypatched Prometheus failure leaves a seeded transition result unchanged.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/observability src/mdcp/control/metrics.py src/mdcp/router/metrics.py src/mdcp/predictor/metrics.py src/mdcp/control/app.py src/mdcp/router/app.py src/mdcp/predictor/app.py tests/unit/observability tests/contract/observability
git commit -m "feat: expose bounded control plane metrics"
```

### Task 6.2: Build the full Docker Compose review topology

**Files:**
- Create: `compose.yaml`
- Create: `docker/replay.Dockerfile`
- Create: `monitoring/prometheus/prometheus.yml`
- Create: `monitoring/grafana/provisioning/datasources/prometheus.yml`
- Create: `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- Test: `tests/contract/compose/test_compose_contract.py`
- Test: `tests/integration/compose/test_stack_health.py`
- Test: `tests/security/test_compose_boundary.py`

**Interfaces:**
- Consumes: locked images/config/secrets and all four custom roles.
- Produces: profiles `review`, `validator`, `replay`, `natural`; services `postgres`, `mlflow`, `control`, `router`, `stable`, `candidate`, `prometheus`, `grafana`.

- [ ] **Step 1: Write failing topology/resource/security tests**

```python
def test_predictor_resources(compose):
    for name in ("stable", "candidate"):
        assert compose[name].cpus == 1.0
        assert compose[name].memory_bytes == 384 * 1024 * 1024

def test_no_data_plane_docker_socket(compose):
    assert all("/var/run/docker.sock" not in s.mounts for s in compose.services.values())

def test_whole_lifetime_measurement_mounts_are_exact_and_read_only(compose):
    assert compose.measurement.cgroup_mounts == {
        "memory.peak": "ro", "memory.current": "ro",
        "memory.max": "ro", "cpu.max": "ro",
    }
    assert compose.measurement.privileged is False
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/contract/compose/test_compose_contract.py tests/integration/compose/test_stack_health.py tests/security/test_compose_boundary.py -q`

Expected: FAIL because `compose.yaml` and monitoring provisioning are missing.

- [ ] **Step 3: Implement resource/network/secret-isolated Compose profiles**

Pin image references, health checks, memory/CPU/pids, non-root/read-only/cap-drop/no-new-privileges, bounded tmpfs/volumes, and explicit internal networks. Predictor accepts only router; router accepts replay and calls predictors/control; control alone reaches PostgreSQL/signing secret; MLflow/Grafana bind loopback. Host PowerShell may use Docker CLI to locate the exact candidate cgroup, but passes no Docker authority into the measurement container. In whole-lifetime mode, measurement receives exact read-only file mounts for candidate `memory.peak`, `memory.current`, `memory.max`, and `cpu.max`; in FD-local mode only that exact `memory.peak` file may be writable. It is never privileged, has no Docker socket, and cannot see a cgroup directory/parent/peer. An exact scoped mount failure is `UNKNOWN` and stops the scenario. Keep runtime state under named volumes excluded from Git.

```yaml
services:
  control:
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    networks: [control_db, router_control]
  router:
    read_only: true
    cap_drop: [ALL]
    networks: [reviewer_router, router_control, router_predictors]
  predictor-stable:
    cpus: 1.0
    mem_limit: 384m
    networks: [router_predictors]
```

- [ ] **Step 4: Verify healthy 8-GB topology**

Run: `docker compose --profile review config --quiet; docker compose --profile review up --wait --detach; uv run pytest tests/contract/compose/test_compose_contract.py tests/integration/compose/test_stack_health.py tests/security/test_compose_boundary.py -q`

Expected: config exits 0, all eight required services healthy within 120 seconds, exact cgroup mounts and 1.0-CPU/384-MiB limits match, no privileged/socket authority exists, security assertions pass, and the formal measured stack peak remains <=6.5 GiB.

- [ ] **Step 5: Commit**

```powershell
git add compose.yaml docker/replay.Dockerfile monitoring tests/contract/compose tests/integration/compose tests/security/test_compose_boundary.py
git commit -m "feat: add isolated review compose profile"
```

### Task 6.3: Provision exactly three reviewer dashboards

**Files:**
- Create: `monitoring/grafana/dashboards/release-overview.json`
- Create: `monitoring/grafana/dashboards/canary-comparison.json`
- Create: `monitoring/grafana/dashboards/decision-timeline.json`
- Test: `tests/contract/observability/test_dashboards.py`
- Test: `tests/integration/observability/test_dashboard_queries.py`

**Interfaces:**
- Consumes: frozen metric catalogue and Prometheus datasource UID `mdcp-prometheus`.
- Produces: dashboard UIDs `mdcp-release-overview`, `mdcp-canary-comparison`, `mdcp-decision-timeline` and no mutation controls.

- [ ] **Step 1: Write failing dashboard-count/query tests**

```python
def test_exact_dashboard_set(dashboard_files):
    assert {d.uid for d in dashboard_files} == {
        "mdcp-release-overview", "mdcp-canary-comparison", "mdcp-decision-timeline"}

def test_injected_panels_are_labeled(dashboards):
    assert "INJECTED FAILURE — EXPECTED TEST OUTCOME" in dashboards.canary.text
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/contract/observability/test_dashboards.py tests/integration/observability/test_dashboard_queries.py -q`

Expected: FAIL because dashboard JSON files do not exist.

- [ ] **Step 3: Implement the three fixed dashboards**

Release Overview shows pointer/release/state/policy/revision/gates/evidence age/supply-chain class. Canary Comparison shows intended/observed weights, admissions, distinct denominators, nearest-rank latency, cgroup peak, the exact decoded `measurement_mode`, errors/restarts/accounting, and natural-vs-injected labels. Decision Timeline shows transitions/windows/pause/rollback/quarantine/frozen set/acks/restarts/recovery. Use only catalogue metrics and read-only links to receipt/MLflow; include no control buttons.

```json
{
  "dashboards": [
    {"uid": "mdcp-release-overview", "title": "Release Overview"},
    {"uid": "mdcp-canary-comparison", "title": "Canary Comparison"},
    {"uid": "mdcp-decision-timeline", "title": "Decision Timeline"}
  ],
  "editable": false,
  "control_links": []
}
```

- [ ] **Step 4: Verify provisioning and query validity**

Run: `uv run pytest tests/contract/observability/test_dashboards.py tests/integration/observability/test_dashboard_queries.py -q`

Expected: exactly three dashboards parse/provision, every PromQL metric exists, no request_id/unbounded label query appears, both memory mode names render correctly, and seeded golden evidence renders expected panels.

- [ ] **Step 5: Commit**

```powershell
git add monitoring/grafana/dashboards tests/contract/observability tests/integration/observability
git commit -m "feat: provision reviewer dashboards"
```

### Task 6.4: Implement deterministic replay, scheduling, and cgroup measurement

**Files:**
- Create: `src/mdcp/replay/cli.py`
- Create: `src/mdcp/replay/scheduler.py`
- Create: `src/mdcp/replay/measurement.py`
- Modify: `src/mdcp/replay/scenarios.py`
- Test: `tests/unit/replay/test_scheduler.py`
- Test: `tests/unit/replay/test_measurement.py`
- Test: `tests/integration/replay/test_request_schedule.py`
- Test: `tests/fixtures/reviewer/request-schedule-v1.json`
- Test: `tests/fixtures/reviewer/synthetic-labels-v1.json`

**Interfaces:**
- Consumes: deterministic request IDs/features/labels, router URL, candidate cgroup path, scenario/fault profile.
- Produces: CLI `python -m mdcp.replay.cli scenario {golden-rollback|full-success} --rate 80 --max-in-flight 32`, `ReplayReport` with explicit `measurement_mode` and identity/resource/evidence digests, authoritative cgroup peak in either approved mode, exact HMAC stage counts.

- [ ] **Step 1: Write failing schedule/timing tests**

```python
def test_full_request_schedule(schedule):
    assert schedule.warmup_requests == 400
    assert schedule.shadow_requests == 2_000
    assert schedule.canary_total_requests == {"CANARY_10": 6_000, "CANARY_25": 4_000, "CANARY_50": 4_000}
    assert schedule.recovery_requests == 600
    assert schedule.request_seconds == 212.5

def test_whole_lifetime_mode_includes_warmup_and_requires_fresh_candidate(measurement):
    assert measurement.measurement_mode == "WHOLE_LIFETIME_PEAK_UPPER_BOUND"
    assert measurement.captured_phases == {
        "container_start", "model_load", "warmup", "scenario_end"}
    assert measurement.fresh_candidate is True
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/replay/test_scheduler.py tests/unit/replay/test_measurement.py tests/integration/replay/test_request_schedule.py -q`

Expected: FAIL because scheduler/measurement modules and schedule fixture are absent.

- [ ] **Step 3: Implement exact 80-Hz replay and measurement lifecycle**

Use precomputed request IDs whose HMAC buckets produce exact configured shares, one monotonic admission clock, semaphore 32, full-body latency, and 200 warm-ups per predictor excluded from latency/error/quality/admission evidence by flag. Select memory mode before each scenario. If writable reset is proven, use one `O_RDWR` descriptor for read/write/seek-read/bounded-allocation/seek-read proof and keep same-descriptor semantics for the exact candidate measurement. Otherwise create a fresh candidate/cgroup per natural or injected scenario and capture `memory.peak` from start/model-load/warm-up through scenario end as `WHOLE_LIFETIME_PEAK_UPPER_BOUND`; never reset or call it post-warm-up. Separate candidate lifetimes, container identity digests, revisions, windows, and receipts for natural and injected runs. Delayed labels arrive only after routing and carry source calendar day/digest.

Return memory `UNKNOWN` only for missing/unreadable peak, inability to bind the exact candidate cgroup, `memory.max`/`cpu.max` mismatch, a reset claim without same-FD proof, a whole-lifetime claim without a fresh candidate, or evidence not bound to container/revision/window. Unsupported reset alone selects the whole-lifetime mode. RSS, `psutil`, Docker UI, authoritative `docker stats`, host estimates, and threshold relaxation are forbidden.

```python
async def replay(schedule: Sequence[ScheduledRequest], send: SendRequest) -> ReplayReport:
    semaphore = asyncio.Semaphore(32)
    start = time.perf_counter_ns()
    tasks = [asyncio.create_task(admit_one(start, item, semaphore, send)) for item in schedule]
    outcomes = await asyncio.gather(*tasks)
    measured = [outcome for outcome in outcomes if not outcome.warmup]
    return ReplayReport.from_outcomes(measured, warmups=len(outcomes) - len(measured))
```

- [ ] **Step 4: Verify arithmetic and bounded execution behavior**

Run: `uv run pytest tests/unit/replay/test_scheduler.py tests/unit/replay/test_measurement.py tests/integration/replay/test_request_schedule.py -q`

Expected: schedule reports warm 5 s, shadow 25 s, C10 75 s, C25 50 s, C50 50 s, recovery 7.5 s, total 212.5 s; golden request schedule is 75 s; concurrency never exceeds 32; both modes and all enumerated `UNKNOWN` cases pass unit tests; the owner-host fixture reports `WHOLE_LIFETIME_PEAK_UPPER_BOUND` with warm-up included.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/replay tests/unit/replay tests/integration/replay tests/fixtures/reviewer/request-schedule-v1.json tests/fixtures/reviewer/synthetic-labels-v1.json
git commit -m "feat: add deterministic reviewer replay"
```

### Task 6.5: Deliver and verify the five-minute reviewer entry point

**Files:**
- Create: `scripts/demo.ps1`
- Create: `docs/reviewer-guide.md`
- Test: `tests/integration/reviewer/test_demo_contract.py`
- Test: `tests/integration/reviewer/test_observability_outages.py`
- Test: `tests/integration/reviewer/test_warm_wall_time.py`
- Create at run time and review: `evidence/public/reviewer/golden-rollback-receipt.json`
- Create at run time and review: `evidence/public/reviewer/timing-report.json`

**Interfaces:**
- Consumes: Compose review profile, synthetic fixtures, release-CI recording, replay CLI, verifier, dashboards.
- Produces: `pwsh ./scripts/demo.ps1 -Scenario GoldenRollback -Warm -Verify` and `-Scenario FullSuccess`; exit 0 only with receipt verification and <=300-second warm wall time.

- [ ] **Step 1: Write failing orchestration/outage tests**

```python
def test_demo_requires_no_gpu_uci_or_github_cli(demo_contract):
    assert demo_contract.external_commands.isdisjoint({"nvidia-smi", "gh", "kubectl", "k3d"})
    assert demo_contract.network_required is False

def test_prometheus_outage_does_not_change_decision(run_with_prometheus_down):
    assert run_with_prometheus_down.control_decision == run_with_prometheus_down.expected_decision

def test_public_reports_are_sanitized(public_reports):
    assert public_reports.forbidden_fields_found == []
    assert all(report.measurement_mode for report in public_reports.reviewer_reports)
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/integration/reviewer/test_demo_contract.py tests/integration/reviewer/test_observability_outages.py tests/integration/reviewer/test_warm_wall_time.py -q`

Expected: FAIL because `scripts/demo.ps1` and public reviewer reports are absent.

- [ ] **Step 3: Implement idempotent demo and explicit cold/warm reporting**

Validate Docker/cgroup capability and selected memory mode, start Compose, create a fresh candidate for each whole-lifetime scenario, load prebuilt fixtures, offline-verify bundle, bootstrap, validate, shadow, run selected canary scenario, observe rollback/convergence/recovery, export/verify receipt, and print public-safe logical MLflow/Grafana/receipt locations. Measure cold pull/extract separately and exclude only that named interval; warm timer includes validation through receipt verification. Grafana/Prometheus outage removes views only; MLflow outage blocks new validation only; PostgreSQL outage stops transitions and lease-expiry becomes stable-only. Before commit, reject any public report containing username, absolute local path, raw container ID, hostname, secret, or raw environment dump.

```powershell
$ErrorActionPreference = 'Stop'
pwsh ./scripts/feasibility.ps1 -Gate CgroupResource
docker compose --profile reviewer up --detach --wait
uv run python -m mdcp.verify.cli bundle --root tests/fixtures/supply-chain/recorded-release-ci --offline
uv run python -m mdcp.replay.cli run --scenario GoldenRollback --warm --verify
uv run python -m mdcp.verify.cli receipt --path evidence/public/reviewer/golden-rollback-receipt.json
```

- [ ] **Step 4: Execute both reviewer acceptance scenarios**

Run: `pwsh ./scripts/demo.ps1 -Scenario GoldenRollback -Warm -Verify; pwsh ./scripts/demo.ps1 -Scenario FullSuccess -Warm -Verify`

Expected: each exits 0 in <=300 seconds; golden prints `INJECTED FAILURE — EXPECTED TEST OUTCOME`, `decision=ROLLED_BACK`, `recovery=PASS`, `receipt=PASS`; full-success prints `decision=PRODUCTION`; both show the exact `measurement_mode`, enforce 256/384 MiB unchanged, and bind candidate cgroup/container/revision/window evidence; neither accesses UCI/network/GPU/GitHub CLI/Kubernetes or emits forbidden public metadata.

- [ ] **Step 5: Commit public-safe reviewer evidence and guide**

```powershell
git add scripts/demo.ps1 docs/reviewer-guide.md tests/integration/reviewer evidence/public/reviewer
git commit -m "feat: complete cpu reviewer path"
```

## Wave 6 completion checkpoint

Run: `uv run pytest tests/unit/observability tests/unit/replay tests/contract/observability tests/contract/compose tests/integration/observability tests/integration/compose tests/integration/replay tests/integration/reviewer tests/security/test_compose_boundary.py -q; pwsh ./scripts/demo.ps1 -Scenario GoldenRollback -Warm -Verify; pwsh ./scripts/demo.ps1 -Scenario FullSuccess -Warm -Verify; git status --short`

Expected: M6 PASS, exactly three dashboards, both warm scenarios <=300 seconds with fixed counts, cold timing separate, formal reviewer-path stack/memory evidence (not the W0 feasibility claim), selected `measurement_mode` visible in receipt/report/dashboard, decision isolation proven during observability outages, no prohibited dependency or public metadata, verified public-safe receipts, and clean worktree.
