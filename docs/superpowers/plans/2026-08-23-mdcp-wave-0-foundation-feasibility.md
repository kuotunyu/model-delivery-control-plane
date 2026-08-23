# MDCP Wave 0 Foundation and Feasibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove every platform-sensitive v0.1 invariant before downstream implementation begins and establish the locked repository/tooling foundation.

**Architecture:** Feasibility probes run as explicit Docker Compose profiles and emit one canonical aggregate report. Probe code is isolated under `src/mdcp/feasibility`; it does not become a substitute data/control plane. Any failed gate returns nonzero, marks Wave 0 failed, and blocks Waves 1–7.

**Tech Stack:** Python 3.12, uv, pytest, FastAPI, httpx, Docker Compose, Linux cgroup v2, RFC 8785, Ed25519/cryptography, PostgreSQL 16, MLflow, Prometheus, Grafana, and PowerShell 7.

## Global Constraints

- Entry requires approved spec commit `6bfa2e6781f1f1ba6fbcd13833c5e3b03691f28f`, approval-status commit `69cba0a798454ddee04012251f1116afcf2a038a`, and cgroup-mode amendment commit `219eb81660f0fb36c7d22c5444d798259a274e1f`.
- Execute Wave 0 only on branch `codex/wave0-foundation-feasibility`, in `.worktrees/wave0-foundation-feasibility`, with untracked runtime state under `D:\model-delivery-control-plane-runtime\wave0`. Do not create Wave 1–7 skeletons.
- Do not download UCI data, create a remote, authenticate to GHCR, generate a real attestation, tag, release, install Kubernetes/k3d, or use cloud/GPU resources.
- A cgroup failure cannot be converted to an RSS measurement. A load failure cannot be hidden by reducing 80 rps, 32 in-flight, 25 ms, 256 MiB, 384 MiB, or the sample schedule.
- The aggregate gate must report exactly eight named feasibility results: `cgroup_v2`, `scoped_memory_peak`, `compose_resource_limits`, `load_harness`, `rfc8785_ed25519_vectors`, `postgres_atomic_transition`, `reviewer_stack_budget`, and `github_supply_chain_research`.
- Expected owner-host memory mode is `WHOLE_LIFETIME_PEAK_UPPER_BOUND`; unsupported reset is not failure when exact readable files, fresh-candidate lifetime, resource limits, and identity bindings pass. Never fake reset PASS.
- Public reports must contain no username, absolute local path, raw container ID, hostname, secret, or raw environment dump. Raw diagnostic evidence stays under the external runtime root; public evidence uses logical identities and digests.
- Wave 0 completion command is `uv run python -m mdcp.feasibility.gate --report evidence/public/feasibility/wave0-report.json`; expected terminal line is `WAVE0 PASS 8/8`.

---

### Task 0.1: Lock the repository and Python foundation

**Files:**
- Create: `.gitignore`
- Create: `.dockerignore`
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `constraints/versions.env`
- Create: `src/mdcp/__init__.py`
- Create: `src/mdcp/config/settings.py`
- Create: `src/mdcp/config/logging.py`
- Create: `src/mdcp/feasibility/__init__.py`
- Test: `tests/unit/config/test_settings.py`

**Interfaces:**
- Consumes: approved Compose-only scope and reviewer resource limits.
- Produces: `Settings.load() -> Settings`, Python `>=3.12,<3.13`, locked dependency graph, and image/version keys `POSTGRES_IMAGE`, `MLFLOW_IMAGE`, `PROMETHEUS_IMAGE`, `GRAFANA_IMAGE`.

- [ ] **Step 1: Write the failing settings contract**

```python
def test_frozen_performance_defaults():
    settings = Settings()
    assert settings.predictor_cpus == 1.0
    assert settings.predictor_memory_mib == 384
    assert settings.memory_policy_mib == 256
    assert settings.admission_rate_rps == 80
    assert settings.max_in_flight == 32
```

- [ ] **Step 2: Run the test and verify red**

Run: `uv run pytest tests/unit/config/test_settings.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'mdcp.config'`.

- [ ] **Step 3: Create the minimal locked foundation**

Implement immutable Pydantic settings with the five values above, JSON logging that redacts keys matching `token|secret|password|private`, Python 3.12 metadata, `src` packaging, pytest configuration, and dependency groups `runtime`, `ml`, `observability`, and `dev`. Resolve and commit `uv.lock`; write the exact selected infrastructure image references to `constraints/versions.env` and reject mutable `latest` tags in `Settings.load()`.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True)
    predictor_cpus: Literal[1.0] = 1.0
    predictor_memory_mib: Literal[384] = 384
    memory_policy_mib: Literal[256] = 256
    admission_rate_rps: Literal[80] = 80
    max_in_flight: Literal[32] = 32
```

- [ ] **Step 4: Verify the foundation**

Run: `uv sync --frozen --all-groups; uv run pytest tests/unit/config/test_settings.py -q; uv run python -c "from mdcp.config.settings import Settings; print(Settings().model_dump_json())"`

Expected: sync exits 0, pytest prints `1 passed`, and JSON contains `"admission_rate_rps":80` without a secret value.

- [ ] **Step 5: Commit**

```powershell
git add .gitignore .dockerignore .python-version pyproject.toml uv.lock constraints/versions.env src/mdcp tests/unit/config
git commit -m "build: lock mdcp foundation"
```

### Task 0.2: Qualify cgroup v2 peak mode and Compose resource enforcement

**Files:**
- Create: `src/mdcp/feasibility/cgroup.py`
- Create: `src/mdcp/feasibility/resource_probe.py`
- Test: `tests/feasibility/cgroup_probe.py`
- Test: `tests/feasibility/test_cgroup_contract.py`
- Create: `compose.feasibility.yaml`
- Create: `scripts/feasibility.ps1`

**Interfaces:**
- Consumes: `Settings` and the version-locked Python image.
- Produces: `CgroupProbeResult(measurement_mode, kernel, cgroup_version, memory_current_bytes, memory_peak_bytes, memory_max_bytes, cpu_max, candidate_cgroup_identity_digest, reset_capability_verdict, fresh_candidate, captured_phases, docker_socket_present, evidence_digest)`, feasibility results `cgroup_v2`, `scoped_memory_peak`, `compose_resource_limits`, and command `pwsh ./scripts/feasibility.ps1 -Gate CgroupResource`.

- [ ] **Step 1: Write the failing platform contract**

```python
def test_candidate_cgroup_contract(probe_result):
    assert probe_result.cgroup_version == 2
    assert probe_result.kernel
    assert probe_result.memory_current_bytes >= 0
    assert probe_result.memory_peak_bytes >= probe_result.memory_current_bytes
    assert probe_result.memory_peak_bytes <= 256 * 1024 * 1024
    assert probe_result.memory_max_bytes == 384 * 1024 * 1024
    assert probe_result.cpu_max == "100000 100000"
    assert probe_result.docker_socket_present is False
    assert len(probe_result.candidate_cgroup_identity_digest) == 64
    assert len(probe_result.evidence_digest) == 64
    assert probe_result.measurement_mode in {
        "FD_LOCAL_POST_WARMUP_PEAK", "WHOLE_LIFETIME_PEAK_UPPER_BOUND"
    }
    if probe_result.measurement_mode == "FD_LOCAL_POST_WARMUP_PEAK":
        assert probe_result.reset_capability_verdict == "SUPPORTED_SAME_FD"
    else:
        assert probe_result.reset_capability_verdict == "UNSUPPORTED_READ_ONLY"
        assert probe_result.fresh_candidate is True
        assert probe_result.captured_phases == {
            "container_start", "model_load", "warmup", "scenario_end"}
```

- [ ] **Step 2: Verify the probe is red before capability code exists**

Run: `uv run pytest tests/feasibility/test_cgroup_contract.py -q`

Expected: FAIL with `fixture 'probe_result' not found`.

- [ ] **Step 3: Implement the bounded measurement probe**

Implement `read_cgroup_v2(root: Path)`, `prove_fd_local_reset(peak: Path, allocate: Callable[[], None])`, `read_resource_limits(root: Path)`, and candidate identity binding. Host PowerShell uses Docker CLI only to resolve the exact candidate cgroup files. Whole-lifetime mode mounts exactly `memory.peak`, `memory.current`, `memory.max`, and `cpu.max` read-only into an unprivileged measurement container; FD-local mode may make only the exact `memory.peak` mount writable. Neither mode mounts `/var/run/docker.sock`. The candidate has `cpus: 1.0`, `mem_limit: 384m`, `pids_limit: 128`, and a read-only root filesystem.

The reset capability proof MUST keep one `O_RDWR` descriptor open while it reads the previous peak, writes non-empty `b"0"`, seeks/reads the reset value, invokes a bounded allocation, then seeks/reads a strictly increased peak. Do not use `Path.write_text()`/`Path.read_text()`. `EROFS`, `EACCES`, or an unwritable mode selects `WHOLE_LIFETIME_PEAK_UPPER_BOUND` only if the orchestrator creates a new synthetic candidate, starts the observer at container start, records synthetic model-load allocation, performs 200 warm-up calls, runs the bounded allocation scenario, and captures scenario-end peak before teardown. All exact read-only mounts and container/revision/window bindings must pass. Missing/unreadable peak, wrong/missing limits, wrong cgroup identity, reset claims without same-FD proof, or whole-lifetime reuse yields `UNKNOWN`.

```python
def read_int_same_fd(fd: int) -> int:
    os.lseek(fd, 0, os.SEEK_SET)
    return int(os.read(fd, 64).decode("ascii").strip())

def prove_fd_local_reset(peak: Path, allocate: Callable[[], None]) -> tuple[int, int, int]:
    fd = os.open(peak, os.O_RDWR)
    try:
        before = read_int_same_fd(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, b"0")
        reset_value = read_int_same_fd(fd)
        allocate()
        increased = read_int_same_fd(fd)
        if not (reset_value <= before and increased > reset_value):
            raise EvidenceUnavailable("same-fd reset proof")
        return before, reset_value, increased
    finally:
        os.close(fd)
```

- [ ] **Step 4: Run the real Compose feasibility gate**

Run: `pwsh ./scripts/feasibility.ps1 -Gate CgroupResource`

Expected on the declared owner host: PASS JSON contains `"measurement_mode":"WHOLE_LIFETIME_PEAK_UPPER_BOUND"`, kernel `6.6.114.1-microsoft-standard-WSL2`, `"cgroup_version":2`, integer `memory_current_bytes` and `memory_peak_bytes`, `"memory_max_bytes":402653184`, `"cpu_max":"100000 100000"`, `"docker_socket_present":false`, `"reset_capability_verdict":"UNSUPPORTED_READ_ONLY"`, a candidate cgroup identity digest, and an evidence digest. `scoped_memory_peak` passes because the conservative mode is authoritative. An enumerated identity/mount/read/limit/freshness failure exits 1 with `FEAS-CGROUP-UNKNOWN`; no RSS, `psutil`, Docker UI, authoritative `docker stats`, host estimate, or relaxed threshold field may appear.

- [ ] **Step 5: Commit**

```powershell
git add compose.feasibility.yaml scripts/feasibility.ps1 src/mdcp/feasibility tests/feasibility
git commit -m "test: prove cgroup resource contract"
```

### Task 0.3: Prove the 80-rps, 32-in-flight measurement harness

**Files:**
- Create: `src/mdcp/feasibility/synthetic_predictor.py`
- Create: `src/mdcp/feasibility/load_probe.py`
- Test: `tests/feasibility/test_load_probe.py`
- Modify: `compose.feasibility.yaml`
- Modify: `scripts/feasibility.ps1`

**Interfaces:**
- Consumes: cgroup-qualified predictor container from Task 0.2.
- Produces: `LoadProbeResult(admitted, completed, errors, achieved_rps, max_in_flight, p95_us, wall_time_ms)` and feasibility result `load_harness`.

This probe proves only that the frozen scheduler/load harness is feasible on the owner host. It is not final predictor performance evidence and MUST NOT be reported as natural or release-candidate latency.

- [ ] **Step 1: Write the failing deterministic load assertion**

```python
def test_load_probe_meets_frozen_profile(load_result):
    assert load_result.admitted == 2_000
    assert load_result.completed == 2_000
    assert load_result.errors == 0
    assert load_result.max_in_flight <= 32
    assert load_result.achieved_rps >= 80.0
    assert load_result.p95_us <= 25_000
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/feasibility/test_load_probe.py -q`

Expected: FAIL with `fixture 'load_result' not found`.

- [ ] **Step 3: Implement the probe and monotonic nearest-rank timing**

Create a single-row synthetic FastAPI predictor and an asyncio scheduler using `time.perf_counter_ns()`, a fixed 80-Hz admission clock, and `asyncio.Semaphore(32)`. Convert elapsed nanoseconds by `(ns + 999) // 1000`; compute p95 at one-based index `ceil(0.95*n)`. Record queueing from immediately before enqueue through full body receipt.

```python
async def admit_at_80_hz(send: SendRequest, count: int) -> list[int]:
    semaphore = asyncio.Semaphore(32)
    epoch = time.perf_counter_ns()
    tasks = [asyncio.create_task(_at(epoch + i * 12_500_000, semaphore, send))
             for i in range(count)]
    return await asyncio.gather(*tasks)
```

- [ ] **Step 4: Run the constrained profile**

Run: `pwsh ./scripts/feasibility.ps1 -Gate LoadHarness`

Expected: `FEAS-LOAD-PASS admitted=2000 completed=2000 errors=0 max_in_flight<=32 p95_us<=25000`; otherwise the command exits 1 and Wave 0 is blocked.

- [ ] **Step 5: Commit**

```powershell
git add compose.feasibility.yaml scripts/feasibility.ps1 src/mdcp/feasibility tests/feasibility
git commit -m "test: prove frozen load profile"
```

### Task 0.4: Freeze cross-process RFC 8785 and Ed25519 vectors

**Files:**
- Create: `src/mdcp/common/canonical.py`
- Create: `src/mdcp/common/digests.py`
- Test: `tests/fixtures/crypto/route-plan-v1.json`
- Test: `tests/fixtures/crypto/route-plan-v1.canonical.hex`
- Test: `tests/fixtures/crypto/route-plan-v1.public.hex`
- Test: `tests/fixtures/crypto/route-plan-v1.signature.hex`
- Test: `tests/unit/common/test_canonical_vectors.py`
- Test: `tests/feasibility/test_crypto_subprocess.py`

**Interfaces:**
- Consumes: UTF-8 JSON value.
- Produces: `JsonValue`, `canonicalize_json(value: JsonValue) -> bytes`, `sha256_hex(data: bytes) -> str`, `content_digest(model: BaseModel) -> str`, frozen RFC 8032 test-key vectors that are never production credentials, and feasibility result `rfc8785_ed25519_vectors`.

- [ ] **Step 1: Write failing canonical/signature vector tests**

```python
def test_route_plan_vector(vector):
    canonical = canonicalize_json(vector.payload)
    assert canonical.hex() == vector.canonical_hex
    assert sha256_hex(canonical) == vector.payload_sha256
    Ed25519PublicKey.from_public_bytes(vector.public_key).verify(vector.signature, canonical)
```

- [ ] **Step 2: Verify red in-process and cross-process**

Run: `uv run pytest tests/unit/common/test_canonical_vectors.py tests/feasibility/test_crypto_subprocess.py -q`

Expected: FAIL with `ImportError: cannot import name 'canonicalize_json'`.

- [ ] **Step 3: Implement canonicalization and fixed vectors**

Wrap one RFC 8785 implementation behind `canonicalize_json`; reject NaN, infinity, duplicate parsed object keys, and non-UTF-8 input before canonicalization. Generate the signature from the published deterministic test seed, store only its public vector outputs, and make the subprocess test call a fresh Python interpreter that reads the JSON file.

```python
def canonicalize_json(value: JsonValue) -> bytes:
    reject_non_finite(value)
    return rfc8785.dumps(value)

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def content_digest(model: BaseModel) -> str:
    return sha256_hex(canonicalize_json(model.model_dump(mode="json")))

def verify_ed25519(public_key: bytes, message: bytes, signature: bytes) -> None:
    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
```

- [ ] **Step 4: Verify byte-for-byte portability**

Run: `uv run pytest tests/unit/common/test_canonical_vectors.py tests/feasibility/test_crypto_subprocess.py -q`

Expected: `2 passed`; both processes emit the same canonical SHA-256 and signature verification returns normally.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/common tests/fixtures/crypto tests/unit/common tests/feasibility/test_crypto_subprocess.py
git commit -m "feat: freeze canonical signing vectors"
```

### Task 0.5: Prove one-transaction state, pointer, route, and audit persistence

**Files:**
- Create: `src/mdcp/feasibility/transaction_probe.py`
- Test: `tests/feasibility/sql/atomic_transition_probe.sql`
- Test: `tests/feasibility/test_atomic_transaction.py`
- Modify: `compose.feasibility.yaml`
- Modify: `scripts/feasibility.ps1`

**Interfaces:**
- Consumes: canonical payload/signature vector and a PostgreSQL connection URL.
- Produces: `AtomicTransitionProbe.run(inject_failure_at: str | None) -> AtomicProbeResult` covering environment, release state, active pointer, revision, signed plan, and chained audit event, plus feasibility result `postgres_atomic_transition`.

- [ ] **Step 1: Write rollback-on-fault and success tests**

```python
def test_injected_signature_persist_failure_rolls_back(probe):
    result = probe.run(inject_failure_at="route_plan_insert")
    assert result.visible_row_counts == {"environment": 0, "release": 0, "route_plan": 0, "audit": 0}

def test_success_commits_one_consistent_revision(probe):
    result = probe.run(inject_failure_at=None)
    assert result.revisions == {"environment": 1, "release": 1, "route_plan": 1, "audit": 1}
```

- [ ] **Step 2: Verify red against the PostgreSQL profile**

Run: `pwsh ./scripts/feasibility.ps1 -Gate AtomicTransaction`

Expected: exit 1 with `FEAS-TX-UNIMPLEMENTED`.

- [ ] **Step 3: Implement the disposable transactional proof**

Use one psycopg transaction, row locks, a unique route revision, canonical payload/digest/signature, and an audit row. Inject an exception immediately before route-plan insertion and again immediately before commit; after each failure query from a new connection and require zero visible rows. The success branch must expose all rows with revision 1 and matching payload digest.

```python
with connection.transaction():
    environment = lock_environment(connection, ENVIRONMENT_ID)
    route = sign_route_plan(environment, revision=1)
    insert_release_state(connection, release_id=BASELINE_ID, state="PRODUCTION")
    set_active_pointer(connection, BASELINE_ID, revision=1)
    insert_route_plan(connection, route)
    append_audit_event(connection, route.digest)
```

- [ ] **Step 4: Verify atomicity**

Run: `pwsh ./scripts/feasibility.ps1 -Gate AtomicTransaction`

Expected: `FEAS-TX-PASS rollback_cases=2 committed_revision=1 split_state=0` and pytest reports `2 passed`.

- [ ] **Step 5: Commit**

```powershell
git add compose.feasibility.yaml scripts/feasibility.ps1 src/mdcp/feasibility/transaction_probe.py tests/feasibility
git commit -m "test: prove atomic transition persistence"
```

### Task 0.6: Prove the full infrastructure set fits the 8-GB reviewer profile

**Files:**
- Create: `src/mdcp/feasibility/stack_probe.py`
- Test: `tests/feasibility/test_stack_budget.py`
- Modify: `compose.feasibility.yaml`
- Modify: `scripts/feasibility.ps1`
- Modify: `constraints/versions.env`

**Interfaces:**
- Consumes: locked PostgreSQL, MLflow, Prometheus, Grafana, predictor, and probe images.
- Produces: `StackBudgetResult(services, ready, peak_bytes, disk_bytes)` with required services `postgres`, `mlflow`, `prometheus`, `grafana`, `control-probe`, `router-probe`, `stable`, `candidate`, plus feasibility result `reviewer_stack_budget`.

This is a `FEASIBILITY` budget result. Only Wave 6 may produce the formal reviewer-path resource and wall-time acceptance claim.

- [ ] **Step 1: Write the failing resource-budget test**

```python
def test_full_stack_is_ready_under_budget(stack_result):
    assert set(stack_result.ready) == set(stack_result.services)
    assert stack_result.peak_bytes <= int(6.5 * 1024**3)
    assert stack_result.disk_bytes < 5 * 1024**3
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/feasibility/test_stack_budget.py -q`

Expected: FAIL with `fixture 'stack_result' not found`.

- [ ] **Step 3: Implement bounded full-stack readiness measurement**

Pin every infrastructure image to a reviewed tag and resolved digest in `constraints/versions.env`; configure health checks and explicit memory limits matching the index budget. Measure cgroup memory for each service and Docker volume/image bytes, not host RSS. The probe waits at most 120 seconds and reports an unavailable service by fixed name.

```yaml
services:
  postgres:
    image: "${POSTGRES_IMAGE}"
    mem_limit: 512m
  mlflow:
    image: "${MLFLOW_IMAGE}"
    mem_limit: 768m
  prometheus:
    image: "${PROMETHEUS_IMAGE}"
    mem_limit: 384m
  grafana:
    image: "${GRAFANA_IMAGE}"
    mem_limit: 384m
```

- [ ] **Step 4: Run the reviewer-budget profile**

Run: `pwsh ./scripts/feasibility.ps1 -Gate StackBudget`

Expected: `FEAS-STACK-PASS ready=8/8 peak_gib<=6.5 disk_gib<5.0`; a timeout, OOM, or budget overrun exits 1.

- [ ] **Step 5: Commit**

```powershell
git add compose.feasibility.yaml constraints/versions.env scripts/feasibility.ps1 src/mdcp/feasibility/stack_probe.py tests/feasibility/test_stack_budget.py
git commit -m "test: prove reviewer stack budget"
```

### Task 0.7: Record GitHub capability research and enforce the Wave 0 stop/go gate

**Files:**
- Create: `docs/research/github-supply-chain-capability.md`
- Create: `src/mdcp/feasibility/gate.py`
- Test: `tests/feasibility/test_github_research.py`
- Test: `tests/feasibility/test_wave0_gate.py`
- Create: `evidence/public/feasibility/wave0-report.schema.json`
- Create at run time and review before commit: `evidence/public/feasibility/wave0-report.json`
- Modify: `scripts/feasibility.ps1`

**Interfaces:**
- Consumes: seven local probe result JSON files plus official GitHub/GHCR documentation read-only research.
- Produces: feasibility result `github_supply_chain_research`, `Wave0Gate.evaluate(results: Sequence[FeasibilityResult]) -> Wave0Report`, canonical report digest, exit code 0 only for exactly eight PASS results.

- [ ] **Step 1: Write failing research and aggregate-gate tests**

```python
def test_wave0_requires_all_named_gates():
    report = Wave0Gate.evaluate(pass_results_except("scoped_memory_peak"))
    assert report.verdict == "FAIL"
    assert report.next_wave_allowed is False

def test_research_declares_read_only_boundary(research_text):
    assert "Retrieved: 2026-08-24" in research_text
    assert "packages permission" in research_text
    assert "attestations permission" in research_text
    assert "No remote mutation performed" in research_text
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/feasibility/test_github_research.py tests/feasibility/test_wave0_gate.py -q`

Expected: FAIL because the research document and `Wave0Gate` do not exist.

- [ ] **Step 3: Perform read-only research and implement fail-closed aggregation**

Use only official GitHub documentation and record each URL plus retrieval date `2026-08-24`. Document GHCR subject naming, workflow design, and public-repository/quota caveats; describe package publication permissions separately from artifact-attestation permissions. This research proves only that the workflow design is feasible—it does not verify the future account, repository, GHCR subject, real attestation, quota, or runtime permissions. Do not log in, create a repository, push, dispatch a workflow, or call a mutating API.

`Wave0Gate` validates report schema/version, unique gate names, timestamps, the eight-name exact set, and an evidence digest for every gate. The cgroup result also requires `measurement_mode`, kernel, cgroup version, `memory.current`, `memory.peak`, `memory.max`, `cpu.max`, candidate cgroup identity digest, and reset capability verdict. Its identity binds the candidate container/revision/window and full-lifetime freshness without publishing a raw container ID. `UNKNOWN` and missing are non-PASS. The public aggregate report is rejected if it contains a username, absolute path, raw container ID, hostname, secret, or raw environment dump.

```python
REQUIRED_GATES = frozenset({
    "cgroup_v2", "scoped_memory_peak", "compose_resource_limits", "load_harness",
    "rfc8785_ed25519_vectors", "postgres_atomic_transition",
    "reviewer_stack_budget", "github_supply_chain_research",
})

class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"

class FeasibilityResult(BaseModel):
    name: str
    verdict: GateStatus
    evidence_digest: str

def wave0_verdict(results: Sequence[FeasibilityResult]) -> GateStatus:
    by_name = {result.name: result for result in results}
    return GateStatus.PASS if set(by_name) == REQUIRED_GATES and all(
        result.verdict is GateStatus.PASS for result in by_name.values()
    ) else GateStatus.FAIL
```

- [ ] **Step 4: Run the complete Wave 0 gate**

Run: `pwsh ./scripts/feasibility.ps1 -Gate All; uv run python -m mdcp.feasibility.gate --report evidence/public/feasibility/wave0-report.json`

Expected: all probe commands exit 0 and final output is `WAVE0 PASS 8/8`. Any other output blocks Waves 1–7 and requires owner review of the exact failed spec section; no fallback metric or lower threshold is allowed.

- [ ] **Step 5: Commit the reviewed public aggregate evidence**

```powershell
git add docs/research/github-supply-chain-capability.md scripts/feasibility.ps1 src/mdcp/feasibility/gate.py tests/feasibility evidence/public/feasibility
git commit -m "test: close wave zero feasibility gates"
```

## Wave 0 completion checkpoint

Run: `uv run pytest tests/unit tests/feasibility -q; uv run python -m mdcp.feasibility.gate --report evidence/public/feasibility/wave0-report.json; git status --short`

Expected: all tests pass, terminal output contains `WAVE0 PASS 8/8`, the report digest recomputes, and `git status --short` is empty. If any gate is FAIL/UNKNOWN, stop without executing Wave 1 and return the failed gate, evidence path, approved-spec section, and spec-revision options to the owner.
