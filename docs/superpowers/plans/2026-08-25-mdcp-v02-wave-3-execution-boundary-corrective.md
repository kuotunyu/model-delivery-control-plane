# MDCP v0.2 Wave 3 Execution-Boundary Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unaccepted Task 3.2 runner with one trusted, single-process, one-shot formal
development boundary, then create the corrected source/freeze pair and stop before P2 execution.

**Architecture:** The CLI consumes one external P2 authorization and internally constructs trusted
runtime guards before opening the bounded loader. One process owns one fit ledger and the existing
transient `ReplaySelectionSession`, completing selection and the sole rank-one replay without an
independent replay command. Strict public/private evidence models, exact static/behavioral H2
firewall policies, and an offline-recomputable source inventory are frozen before any natural fit.

**Tech Stack:** Python 3.12, Pydantic v2, scikit-learn CPU contracts already in the repository,
RFC 8785/SHA-256, Git fixed-argument inspection, Windows `PeakWorkingSetSize`, Linux `VmHWM`, pytest,
Ruff, and uv.

## Approved identities

- Normative temporal design:
  `docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md`.
- Corrective design approval commit:
  `f642d8b524209bfb42feceeb3fcaba64a64d6634`.
- Corrective design SHA-256:
  `5e75c7613cf38136e2a2ce65f68362a1a2f7031a64300d4afe8605003e53d4ad`.
- Accepted Task 3.1 head:
  `96f5e2bbb1faf547ffb186fafe87f9b1da7dfa21`.
- Unaccepted append-only Task 3.2 implementation:
  `1eecbabc5016d8196787b8ae951792b1392d190b`.
- Historical Wave 3 plan, retained unchanged:
  `docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md`.

Owner execution approval MUST bind the exact commit containing this plan and its SHA-256. Absence
or mismatch is an entry failure; the worker does not infer an entry SHA from this document.

## Global constraints

- Locate the unique registered worktree with `git worktree list --porcelain` by matching the owner-
  supplied entry HEAD and branch `codex/wave0-foundation-feasibility`; zero or multiple matches stop.
- Entry requires clean status, remote count `0`, no tag at HEAD, H2 `SEALED_NOT_LOADED`, H2 loaded
  rows `0`, full Wave 0–2 handoff recomputation, and the existing six-test behavioral firewall PASS.
- Preserve all history append-only. Do not amend, reset, checkout-restore, rebase, stash,
  cherry-pick, squash, or delete the unaccepted Task 3.2 commit.
- Use author and committer `kuotunyu <61350295+kuotunyu@users.noreply.github.com>` for every commit.
- Do not modify the approved designs, the historical Wave 3 plan, `pyproject.toml`, `uv.lock`,
  workload configs, Wave 0–2 source/evidence, v0.1/v0.2 serving inventories, preserved rejection
  evidence, datasets, or H2 state.
- Do not read UCI/H1/H2 rows, run a natural fit, perform trial search, use ONNX/MLflow/Docker/GPU/
  network, create a remote, push, merge, tag, Release, or begin formal Task 3.5 execution.
- Standard CPU regression tests may use their existing deterministic synthetic model fixtures; no
  corrective test may open the approved UCI archive.
- Keep exactly four folds, 20 trials, 19 eligible candidates, 80 selection-fit ceiling, four replay-
  fit ceiling, one later final-refit ceiling, 85 total ceiling, seed `2026`, one estimator thread,
  2,000 bootstrap replicates, index `1899`, the exact 18-field schema, thresholds `0.97`/`1.05`, and
  subgroup minimum `100`.
- Poor quality is not early stopping. Contract invalidity receives one fixed code and no
  replacement. A global integrity/resource failure is terminal `UNKNOWN` and never permits rerun.
- Every task follows observed RED -> minimum GREEN -> targeted tests -> scoped independent review
  -> append-only commit. A Critical or Important review finding blocks the next task.
- Task 7 is the terminal boundary. Even PASS stops before P2 and before any natural development run.

## Exact implementation allowlist

Only these paths may change during Tasks 1–7:

```text
src/mdcp/temporal/runner.py
src/mdcp/temporal/cli.py
src/mdcp/temporal/runtime_guards.py
src/mdcp/temporal/run_evidence.py
src/mdcp/temporal/firewall.py
src/mdcp/temporal/search_identity.py
schemas/v2/development-result-index.schema.json
schemas/v2/formal-run-authorization.schema.json
tests/unit/temporal/test_fit_ledger.py
tests/unit/temporal/test_runtime_guards.py
tests/unit/temporal/test_run_evidence.py
tests/integration/temporal/test_formal_runner_synthetic.py
tests/integration/temporal/test_search_freeze_preflight.py
tests/security/temporal/test_data_firewall.py
tests/security/temporal/test_formal_runner_firewall.py
tests/security/temporal/test_formal_run_authorization.py
tests/security/temporal/test_public_evidence_boundary.py
evidence/public/v02/search/search-receipt.json
evidence/public/v02/search/evidence-index.json
```

The last two paths are forbidden before Task 7. If any task needs another path, preserve the state
and stop for owner review.

---

### Task 1: Build authoritative runtime guards and admit only their exact capabilities

**Files:**
- Create: `src/mdcp/temporal/runtime_guards.py`
- Create: `tests/unit/temporal/test_runtime_guards.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: a repository root, the exact expected freeze HEAD, fixed OS/Git facilities, and the
  process start time.
- Produces: `RuntimeStage`, `RuntimeObservation`, `RuntimeGuard.checkpoint(stage)`, and
  `build_production_runtime_guard(repository_root, expected_head) -> RuntimeGuard`.

- [ ] **Step 1: Write RED tests for authoritative and fail-closed checks**

```python
def test_production_guard_has_no_public_probe_injection() -> None:
    signature = inspect.signature(build_production_runtime_guard)
    assert tuple(signature.parameters) == ("repository_root", "expected_head")


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing_peak", "AUTHORITATIVE_MEMORY_UNAVAILABLE"),
        ("peak_over_4_gib", "COMPUTE_MEMORY_EXCEEDED"),
        ("elapsed_over_21600s", "COMPUTE_DEADLINE_EXCEEDED"),
        ("head_changed", "REPOSITORY_IDENTITY_CHANGED"),
        ("tracked_byte_changed", "REPOSITORY_BYTES_CHANGED"),
        ("dirty_untracked", "REPOSITORY_DIRTY"),
    ],
)
def test_runtime_checkpoint_fails_closed(
    tmp_path: Path, mutation: str, reason: str
) -> None:
    guard = guarded_fixture(tmp_path, mutation)
    result = guard.checkpoint(RuntimeStage.POST_FIT)
    assert result.verdict == "UNKNOWN"
    assert result.reason_codes == (reason,)
```

The local `guarded_fixture(tmp_path, mutation)` helper creates a two-file Git repository, commits
both files, constructs the underscore-private synthetic guard with a list-backed monotonic clock
and peak probe, then applies exactly the named mutation before `POST_FIT`. Add `tmp_path: Path` to
the parametrized test signature as shown.

Add static-firewall RED cases proving `runtime_guards.py`, the current `runner.py`, and `cli.py` are
discovered, while unlisted imports, module attributes, environment keys, arbitrary subprocess
arguments, and arbitrary file paths remain denied.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_data_firewall.py -q`

Expected: collection fails because `runtime_guards` is absent; deterministic source discovery still
fails on `runner.py`/`cli.py` with `H2_IMPORT_CAPABILITY_FORBIDDEN`.

- [ ] **Step 3: Implement the fixed production guard**

Use these exact public types:

```python
class RuntimeStage(StrEnum):
    PRE_LOAD = "PRE_LOAD"
    PRE_FIT = "PRE_FIT"
    POST_FIT = "POST_FIT"
    PRE_SEAL = "PRE_SEAL"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    verdict: Literal["PASS", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    elapsed_ns: int
    peak_process_bytes: int | None
    repository_inventory_sha256: str
```

`RuntimeGuard.checkpoint(stage: RuntimeStage) -> RuntimeObservation` is the only public method.
`build_production_runtime_guard(repository_root: Path, expected_head: str) -> RuntimeGuard` is the
only production constructor.

`build_production_runtime_guard` internally binds `time.monotonic_ns`, Windows
`GetProcessMemoryInfo.PeakWorkingSetSize` or Linux `/proc/self/status:VmHWM`, fixed-argument Git
inspection, and a direct working-byte inventory of every tracked path at the expected HEAD. It
accepts no injected callable. Test-only factories remain underscore-prefixed and their observations
can be passed only to Task 3's synthetic core, which forces `evidence_class="synthetic_test"`; the
formal wrapper accepts only a guard built by the production constructor.

Add exact path-specific firewall entries for only the imports, attributes, environment keys, Git
subprocess argument literals, and `/proc/self/status` read used here. Do not add directory-wide or
module-wide wildcards.

- [ ] **Step 4: Run GREEN**

Run:
`uv run pytest tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_data_firewall.py -q`

Expected: all tests PASS; the real formal source set is statically admitted and every adversarial
mutation returns only `H2_IMPORT_CAPABILITY_FORBIDDEN`.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_data_firewall.py
git commit -m "security: add authoritative formal runtime guards"
```

### Task 2: Define closed public receipts and private no-clobber evidence

**Files:**
- Create: `src/mdcp/temporal/run_evidence.py`
- Create: `schemas/v2/development-result-index.schema.json`
- Create: `tests/unit/temporal/test_run_evidence.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: exact typed private fold results, canonical JSON/digest helpers, and the public evidence
  scanner.
- Produces: `ClosedMetrics`, `PublicFoldReceipt`, `PublicTrialReceipt`,
  `PublicDevelopmentResult`, `PrivateFoldEvidence`, `PrivateRunBundle`,
  `canonical_public_result_bytes(result) -> bytes`,
  `write_synthetic_bundle_no_clobber(root, bundle) -> PrivateBundleIdentity`, and
  `verify_development_result(path) -> DevelopmentResultCheck`.

- [ ] **Step 1: Write RED receipt/schema/privacy tests**

```python
@pytest.mark.parametrize(
    "mutation",
    ["extra_key", "unknown_metric", "nan", "uppercase_digest", "short_digest",
     "private_path", "raw_timestamp", "traceback", "credential", "raw_prediction"],
)
def test_public_result_fails_closed(tmp_path: Path, mutation: str) -> None:
    document = mutate(valid_public_result(), mutation)
    path = write_raw_result(tmp_path, document)
    assert verify_development_result(path).verdict == "FAIL"


def test_private_bundle_public_identity_contains_no_private_material(tmp_path: Path) -> None:
    identity = write_synthetic_bundle_no_clobber(tmp_path / "new-run", synthetic_private_bundle())
    assert set(identity.model_dump()) == {
        "file_count", "total_bytes", "inventory_sha256", "manifest_sha256"
    }
    assert public_evidence_violations(identity.model_dump()) == ()
```

`valid_public_result()` returns a schema-valid `synthetic_test` result with the closed 20-trial,
four-fold, 80-selection-fit inventory;
`mutate(document, mutation)` performs exactly one named adversarial change; and
`write_raw_result(tmp_path, document)` writes the deliberately untrusted JSON bytes to a new test
path without using the production publisher.
`synthetic_private_bundle()` returns two canonical private logical files with deterministic bytes.
Define these private helpers at the top of `test_run_evidence.py`; they never read files, clocks,
environment variables, or random devices.

Add no-clobber RED cases for existing destination, missing trusted parent, symlink/junction target,
partial destination, duplicate logical path, noncanonical bytes, and second publication. Error
objects and messages assert only fixed codes and never include the offending value.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py -q`

Expected: FAIL importing `mdcp.temporal.run_evidence` and missing the result-index schema.

- [ ] **Step 3: Implement exact evidence models and schema**

All public Pydantic models use `ConfigDict(extra="forbid", frozen=True)`. `ClosedMetrics` contains
only the fixed aggregate fields `row_count`, `stable_mae`, `candidate_mae`, `point_ratio`, and
`ucb95`; numeric values are finite non-negative `float` or the explicitly allowed `None` for an
`UNKNOWN` receipt. Digest fields use `^[0-9a-f]{64}$`. Status, evidence class, H1 role, H2 state,
reason codes, fit counts, fold IDs, trial IDs, and subgroup names are closed enums/inventories.

`canonical_public_result_bytes` validates the Pydantic model, validates the checked-in schema,
runs `public_evidence_violations`, then RFC-8785 canonicalizes. The internal no-clobber writer uses
an exact non-existing child under a caller-precreated trusted external parent, rejects links, writes
canonical files through exclusive temporary files, fsyncs, and publishes with no replace. Task 2
exports only `write_synthetic_bundle_no_clobber`, which requires
`evidence_class="synthetic_test"`; `natural_development` fails with
`FORMAL_RUN_PERMIT_REQUIRED`. Task 4 adds the permit-bearing formal wrapper. The writer returns only
count/size/digest identity.

Add exact firewall policy for `run_evidence.py` only.

- [ ] **Step 4: Run GREEN**

Run:
`uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q`

Expected: PASS, including schema closure, sanitized failures, atomic no-clobber publication, and
static H2 firewall discovery.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/temporal/run_evidence.py schemas/v2/development-result-index.schema.json src/mdcp/temporal/firewall.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "feat: add closed formal development evidence"
```

### Task 3: Replace the runner with one ledger and one transient selection session

**Files:**
- Modify: `src/mdcp/temporal/runner.py`
- Modify: `tests/unit/temporal/test_fit_ledger.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: exact trial/fold inventories, existing completeness/evaluation/selection contracts,
  `RuntimeGuard`, and strict run-evidence types.
- Produces: `FitPhase`, `FitRecord`, `FitLedger`, `DevelopmentRunBundle`,
  `_DevelopmentExecutionPlan`, and underscore-private
  `_run_development_core(plan: _DevelopmentExecutionPlan, guard: RuntimeGuard) -> DevelopmentRunBundle`
  used by deterministic synthetic tests. Task 3 exposes no natural loader or formal evidence entry
  point.
- Removes: `FormalRunContext`, public injected callbacks, and `replay_provisional`.

- [ ] **Step 1: Write RED ledger/session/selection tests**

```python
def test_fit_ledger_accepts_only_frozen_order_and_one_rank_one_replay() -> None:
    ledger = FitLedger()
    for trial_id in EXACT_TRIAL_IDS:
        for fold_id in ("F1", "F2", "F3", "F4"):
            ledger.record_selection(trial_id, fold_id)
    ledger.bind_provisional(EXACT_RANK_ONE)
    for fold_id in ("F1", "F2", "F3", "F4"):
        ledger.record_replay(EXACT_RANK_ONE.trial_id, fold_id)
    with pytest.raises(FitBudgetError, match="REPLAY_ALREADY_CONSUMED"):
        ledger.record_replay(EXACT_RANK_ONE.trial_id, "F1")


def test_runner_uses_existing_rank_one_and_same_session_for_replay() -> None:
    result = synthetic_run(one_qualified_trial="STAT-A1")
    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 4
    assert result.selection.final_winner.trial_id == "STAT-A1"
    assert result.selection.reason_codes == ()
```

`EXACT_RANK_ONE` is the `ProvisionalWinner` produced by the existing `ReplaySelectionSession` from a
closed 19-result fixture. `synthetic_run(one_qualified_trial)` builds all 20 x four deterministic
typed fold results in frozen order and calls only `_run_development_core`; the fold helper returns
digests derived from trial/fold literals and performs no estimator fit.

Add RED cases for arbitrary replay target, rank two, reconstructed session, duplicate/wrong fold,
81st selection, fifth replay, Wave 3 final fit, changed replay digest, invalid status/verdict,
contract-invalid no replacement, poor quality completing four folds, budget/repository failure
stopping before another fit, and repeated invocation with the same run state.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py -q`

Expected: the one-shot/rank-one tests FAIL because the current runner fabricates replay identities,
creates a new ledger, and never returns the Wave 2 selection result.

- [ ] **Step 3: Implement single-process orchestration**

Use these exact public signatures:

```python
@dataclass(frozen=True, slots=True)
class DevelopmentRunBundle:
    public_result: PublicDevelopmentResult
    private_bundle: PrivateRunBundle
    fit_ledger: FitLedger
    selection: SelectionDecision
```

The underscore-private synthetic core accepts test dependencies but always emits
`evidence_class="synthetic_test"`; it cannot open the bounded loader, accept a private archive path,
or write a natural receipt. Task 4 adds the only permit-bearing formal wrapper after authorization
exists.

Iterate exact trial IDs then F1–F4. Fit `CTRL-01` once per fold and bind its stable predictions for
candidate comparison. Use existing `assemble_development_pairs`, `evaluate_fold`, `evaluate_pooled`,
`qualify_trial`, `ReplaySelectionSession`, and `finalize_selection`; do not copy their policies.
After the closed 19-result qualification inventory, rank only through the session. If rank one
exists, refit only it on the same four folds in the same process, build `ReplayResult` from the
session and actual exact digests, then call `finalize_selection` once. If no winner, finalize the
same session with `None` replay. No API accepts a provisional trial ID.

Call runtime checkpoints before loading, before/after every started fit, before sealing, and on
exit. Any terminal observation stops without replacement or retry. Keep private rows/predictions in
`PrivateRunBundle`; construct public receipts only through `run_evidence.py`.

- [ ] **Step 4: Run GREEN**

Run:
`uv run pytest tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py -q`

Expected: PASS with deterministic `80`/`84` synthetic cases, no exported replay function, no
caller-injected production guard, exact Wave 2 selection identity, and H2 sealed/zero.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/temporal/runner.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
git commit -m "fix: enforce one-shot formal development session"
```

### Task 4: Add durable P2 consumption and a single trusted CLI command

**Files:**
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `src/mdcp/temporal/runner.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Create: `schemas/v2/formal-run-authorization.schema.json`
- Create: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: canonical search receipt, exact freeze HEAD/digest, external authorization file, and
  external no-clobber consumption directory.
- Produces: `FormalRunAuthorization`, opaque non-serializable `FormalRunPermit`,
  `AuthorizationCheck` with optional permit, `FormalDevelopmentInputs`,
  `consume_formal_run_authorization(authorization_path: Path, consumption_root: Path,
  binding: FormalRunBinding) -> AuthorizationCheck`,
  `run_formal_development(inputs: FormalDevelopmentInputs,
  permit: FormalRunPermit) -> DevelopmentRunBundle`,
  `write_formal_bundle_no_clobber(root, bundle, permit) -> PrivateBundleIdentity`, and CLI commands
  `run-development`, `verify-search-freeze`, and `verify-development-result`.
- Removes: CLI command `replay-provisional`.

- [ ] **Step 1: Write RED authorization/order/CLI tests**

```python
def test_absent_p2_refuses_before_loader_or_output(spies: BoundarySpies) -> None:
    result = cli(["run-development", "--search-receipt", str(RECEIPT)])
    assert (result.exit_code, result.stdout) == (3, "FORMAL_RUN_NOT_AUTHORIZED\n")
    assert spies.bounded_loader_calls == 0
    assert spies.output_creations == 0


def test_same_authorization_cannot_start_twice(tmp_path: Path) -> None:
    first = consume_formal_run_authorization(valid_auth(tmp_path), exact_binding())
    second = consume_formal_run_authorization(valid_auth(tmp_path), exact_binding())
    assert first.verdict == "PASS"
    assert type(first.permit) is FormalRunPermit
    assert second.reason_codes == ("FORMAL_RUN_AUTHORIZATION_CONSUMED",)
    assert second.permit is None


def test_formal_runner_rejects_missing_or_forged_permit() -> None:
    with pytest.raises(FormalRunAuthorizationError, match="FORMAL_RUN_PERMIT_REQUIRED"):
        run_formal_development(formal_inputs(), object())


def test_same_permit_cannot_start_a_second_run(valid_permit: FormalRunPermit) -> None:
    run_formal_development_with_synthetic_dependencies(formal_inputs(), valid_permit)
    with pytest.raises(FormalRunAuthorizationError, match="FORMAL_RUN_PERMIT_CONSUMED"):
        run_formal_development_with_synthetic_dependencies(formal_inputs(), valid_permit)
```

`BoundarySpies` is a local dataclass with integer `bounded_loader_calls` and `output_creations`.
`valid_auth(tmp_path)` writes one canonical external authorization under a precreated parent;
`exact_binding()` returns the exact matching `FormalRunBinding`; `formal_inputs()` returns paths
inside the pytest temporary root and the same binding digests. No helper points at the approved UCI
archive or repository evidence roots. `run_formal_development_with_synthetic_dependencies` is an
underscore-private test harness that replaces loader/fold execution with deterministic generated
objects after the real temporary permit is claimed. The `valid_permit` fixture calls the production
consumer once against canonical files under `tmp_path` and yields its non-`None` permit.

Add wrong freeze, receipt/protocol digest mismatch, dirty repository, uppercase/placeholder digest,
wrong action, extra field, symlink authorization, existing marker, concurrent consumption, crash
after consumption, private-value sanitization, and parser-absence tests for `replay-provisional`.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/security/temporal/test_formal_run_authorization.py -q`

Expected: FAIL because no authorization model/atomic consumer exists and the current CLI still
registers `replay-provisional`.

- [ ] **Step 3: Implement consume-before-open and lazy formal imports**

`FormalRunAuthorization` has exactly: schema version, exact 40-character freeze commit, search
receipt SHA-256, protocol SHA-256, authorization ID, action literal
`ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN`, UTC authorization time, and `consumed=false`.

Use these exact runner inputs:

```python
@dataclass(frozen=True, slots=True)
class FormalRunBinding:
    expected_freeze_head: str
    search_receipt_sha256: str
    protocol_sha256: str


@dataclass(frozen=True, slots=True)
class AuthorizationCheck:
    verdict: Literal["PASS", "FAIL"]
    reason_codes: tuple[str, ...]
    permit: FormalRunPermit | None


@dataclass(frozen=True, slots=True)
class FormalDevelopmentInputs:
    repository_root: Path
    expected_freeze_head: str
    archive_path: Path
    archive_sha256: str
    private_output_root: Path
    search_receipt_sha256: str
    protocol_sha256: str
```

Consume by exclusive creation of a canonical sibling marker under the caller-precreated private
authorization root. The marker binds the authorization file digest and exact freeze/receipt/
protocol identities. Marker creation and fsync occur before bounded loader import/call and before
private run-root creation. Existing/partial marker is terminal consumed; no reset surface exists.
The returned `FormalRunPermit` is registered in private process memory, non-serializable, exposes
only authorization ID and bound digests, and cannot be constructed from public receipt bytes. The
formal wrapper atomically claims it once, keeps it active while the same run writes its private
bundle, and closes it on every exit path. A second start with the same object is consumed.

`run_formal_development` accepts the exact permit, constructs the production runtime guard, opens
only `load_uci_development_archive`, uses the Task 3 core in `natural_development` evidence class,
and hands the same permit to `write_formal_bundle_no_clobber`. Missing, forged, mismatched, or reused
permit fails before loader/output. Tests replace the loader/fold executor with deterministic
generated data only after a valid temporary permit; no UCI/model fit occurs.

At module import, `cli.py` sets the exact thread environment keys to `1` before any estimator-bearing
import. It lazily imports runner code only inside the authorized handler. It accepts only env-var
names for private paths, prints one fixed status/reason line, and never prints resolved values or raw
exceptions. Remove the independent replay parser and handler completely.

Update exact firewall policies for the authorization and CLI capabilities only.

- [ ] **Step 4: Run GREEN**

Run:
`uv run pytest tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py -q`

Expected: all mismatch/reuse/concurrency cases fail before loader/output; valid synthetic wiring
consumes once; CLI has no replay command.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/runner.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py schemas/v2/formal-run-authorization.schema.json tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
git commit -m "feat: consume one formal development authorization"
```

### Task 5: Prove the complete H2, publication, and synthetic execution boundary

**Files:**
- Create: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `src/mdcp/temporal/runner.py`
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `src/mdcp/temporal/runtime_guards.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: the production CLI composition path with deterministic generated folds and denial spies.
- Produces: behavioral proof that the formal boundary cannot reach H2, network, GPU, or repository
  writes and can emit only closed evidence.

- [ ] **Step 1: Write RED adversarial composition tests**

```python
def test_production_wiring_uses_only_bounded_development_capability(spies: DenialSpies) -> None:
    result = run_authorized_synthetic_composition(spies)
    assert result.public_result.h2_status == "SEALED_NOT_LOADED"
    assert result.public_result.h2_loaded_rows == 0
    assert spies.calls == {
        "load_uci_development_archive": 1,
        "split_development_rows": 1,
        "load_uci_archive": 0,
        "split_rows": 0,
        "DatasetPartitions.open_h2": 0,
    }


def test_fit_callback_cannot_mutate_repository_and_continue() -> None:
    result = synthetic_run_that_mutates_tracked_byte()
    assert result.public_result.status == "UNKNOWN/REPOSITORY_INTEGRITY"
    assert result.fit_ledger.next_fit_started is False
```

`DenialSpies` is a fixed counter map initialized with all five keys shown above. The authorized
synthetic composition replaces only the bounded loader and fold executor after creating a valid
temporary permit; every forbidden function raises before incrementing its counter.
`synthetic_run_that_mutates_tracked_byte()` mutates one file in a temporary Git repository from its
first fold executor and uses the synthetic runtime guard, proving the next checkpoint terminates.

Add malicious import modules covering direct, alias, qualified, relative, dynamic, reflection, and
module-rebinding access to all legacy/full/H2 symbols. Add adversarial executor outputs containing
row-like keys, arbitrary metrics, non-finite values, paths, exceptions, environment dumps, and
credentials. Add source import-order proof that estimator-bearing modules are absent until thread
keys are set.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/security/temporal/test_formal_runner_firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q`

Expected: at least the new production-composition and repository-mutation tests FAIL before any
real UCI/model access occurs.

- [ ] **Step 3: Make only boundary corrections exposed by the RED tests**

Keep the exact APIs from Tasks 1–4. Corrections may tighten validation, ordering, fixed reason
codes, or exact firewall policy but may not add a loader, fit path, metric, retry, replay command,
or caller-supplied production dependency. Every handled failure still checkpoints and seals private
state without copying sensitive values to public output.

- [ ] **Step 4: Run GREEN and the Wave 0–2 regression subset**

Run:

```powershell
uv run pytest tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_behavioral_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/integration/temporal/test_formal_runner_synthetic.py -q
uv run pytest tests/unit/temporal tests/contract/temporal tests/integration/temporal -q
```

Expected: PASS; only deterministic generated inputs are used; H2 remains sealed/zero.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "test: prove the formal development boundary"
```

### Task 6: Bind the complete search source and offline result verifier

**Files:**
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/integration/temporal/test_search_freeze_preflight.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Modify: `schemas/v2/development-result-index.schema.json`

**Interfaces:**
- Consumes: final search-affecting source bytes, canonical receipt/result schemas, and the exact
  approved logical private-output names.
- Produces: `SearchSourceEntry`, `SearchEvidenceIndex`, `build_search_source_inventory(root)`,
  `prepare_search_freeze(root, created_at_utc)`, and offline CLI verifier
  `verify-development-result`.

- [ ] **Step 1: Write RED closed-inventory/source-archive tests**

```python
def test_search_index_has_exact_source_and_output_inventories(tmp_path: Path) -> None:
    index = build_index(source_tree(tmp_path))
    assert tuple(entry.logical_path for entry in index.private_outputs) == (
        "trial-summary.json",
        "qualification-report.json",
        "ranking-report.json",
        "provisional-winner.json",
        "replay-report.json",
    )
    assert index.source_inventory_sha256 == recompute_source_inventory(index.source_entries)


def test_source_archive_without_dot_git_recomputes_search_inventory(tmp_path: Path) -> None:
    archive_root = export_source_without_git(tmp_path)
    assert verify_search_source_inventory(archive_root, frozen_index()).verdict == "PASS"
```

`source_tree(tmp_path)` is a pytest temporary directory containing the exact 39 logical paths with
deterministic bytes. `build_index` calls the production inventory builder. `recompute_source_inventory`
RFC-8785 canonicalizes the ordered entry documents independently in the test. `export_source_without_git`
uses `git archive` on a temporary fixture repository and extracts it under `tmp_path`; `frozen_index`
is created in memory from the committed fixture before `.git` is removed.

Add missing/extra/duplicate/unknown logical source path, wrong mode, symlink, malformed digest,
coordinated file/index mutation, noncanonical bytes, private output path, pre-run output digest,
receipt/index mismatch, changed approved design/plan/runtime/evidence/firewall byte, and result-index
fit-count/status/H2 inconsistency tests.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py -q`

Expected: FAIL because the current evidence index accepts open `object` entries and has no closed
source inventory or offline development-result verifier.

- [ ] **Step 3: Implement closed source and output inventories**

`SearchSourceEntry` contains exactly logical path, Git mode, byte size, and lowercase SHA-256.
`SearchEvidenceIndex` contains exactly schema version, search-receipt digest, ordered source entries,
their aggregate digest, and the five ordered logical private-output descriptors. The source
inventory is the canonical ASCII ordering of exactly these 39 paths:

```text
configs/workload/temporal-development-v2.json
configs/workload/uci-bike-sharing-v1.json
docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md
docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md
docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md
docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md
pyproject.toml
schemas/v2/bike-request.schema.json
schemas/v2/development-result-index.schema.json
schemas/v2/formal-run-authorization.schema.json
schemas/v2/search-receipt.schema.json
schemas/v2/temporal-contract-receipt.schema.json
schemas/v2/temporal-development.schema.json
src/mdcp/common/canonical.py
src/mdcp/common/digests.py
src/mdcp/common/enums.py
src/mdcp/contracts/workload.py
src/mdcp/contracts/workload_v2.py
src/mdcp/policy/cluster_bootstrap.py
src/mdcp/temporal/adapter.py
src/mdcp/temporal/cli.py
src/mdcp/temporal/completeness.py
src/mdcp/temporal/constants.py
src/mdcp/temporal/contract_gate.py
src/mdcp/temporal/evaluation.py
src/mdcp/temporal/evidence.py
src/mdcp/temporal/firewall.py
src/mdcp/temporal/folds.py
src/mdcp/temporal/golden_vectors.py
src/mdcp/temporal/run_evidence.py
src/mdcp/temporal/runner.py
src/mdcp/temporal/runtime_guards.py
src/mdcp/temporal/search_identity.py
src/mdcp/temporal/selection.py
src/mdcp/temporal/trials.py
src/mdcp/workload/dataset.py
src/mdcp/workload/splits.py
tests/fixtures/temporal/adapter-golden-vectors.json
uv.lock
```

It excludes the two freeze files and all future output.

Aggregate over RFC-8785 canonical logical-path/size/mode/digest entries. Reject missing, extra,
duplicate, unknown, link, or noncanonical entries. `prepare_search_freeze` requires a clean source
HEAD and absent destinations, creates canonical receipt bytes first, binds their digest into the
index, and publishes only the two Task 7 paths no-clobber. It performs no data/model operation.

`verify-development-result` validates canonical bytes, the checked-in result schema, fixed fit-count
transitions, public/private bundle identity, H2 sealed/zero, and publication boundary without
opening the private bundle or dataset.

- [ ] **Step 4: Run GREEN and source-archive proof**

Run:

```powershell
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py -q
```

Expected: targeted PASS. The integration test creates a source tree and matching index entirely
under `tmp_path`, removes `.git`, and observes `SEARCH_SOURCE_INVENTORY_PASS`. No persistent fixture
or allowlist-external file is created. Task 7 repeats the proof against the actual committed freeze
index after it exists.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py schemas/v2/development-result-index.schema.json tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "feat: bind the formal development source inventory"
```

### Task 7: Run the fresh completion gate and create the exact receipt-only freeze child

**Files:**
- Create: `evidence/public/v02/search/search-receipt.json`
- Create: `evidence/public/v02/search/evidence-index.json`

**Interfaces:**
- Consumes: clean Task 6 HEAD as `SEARCH_SOURCE_COMMIT`, every fresh completion result, approved
  identities, and current UTC creation time.
- Produces: exact child `SEARCH_FREEZE_COMMIT`, canonical search-receipt digest, and P2 checkpoint.

- [ ] **Step 1: Run the missing-freeze RED without creating output**

Run:
`uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json`

Expected: nonzero and exactly `SEARCH_RECEIPT_MISSING`; fit ledger count `0`; no external run root.

- [ ] **Step 2: Run every fresh source gate at the clean Task 6 HEAD**

Run:

```powershell
uv run pytest -q
uv run pytest tests/security/temporal tests/integration/temporal tests/unit/temporal tests/contract/temporal -q
uv run ruff check src/mdcp/temporal tests/unit/temporal tests/integration/temporal tests/security/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py src/mdcp/temporal/search_identity.py tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_runner_synthetic.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

Run the credential/private-path source scan, excluding only adversarial temporal security tests and
the defensive regex source `src/mdcp/temporal/evidence.py`:

```powershell
$credentialPattern = '-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----|Bearer[ \t]+[A-Za-z0-9._~+/=-]+|\bgh[pousr]_[A-Za-z0-9]{20,255}\b|\bgithub_pat_[A-Za-z0-9_]{20,255}\b|\bhf_[A-Za-z0-9]{20,255}\b|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'
$credentialFindings = @(rg -n --pcre2 $credentialPattern src schemas configs tests --glob '!src/mdcp/temporal/evidence.py' --glob '!tests/security/temporal/**')
if ($LASTEXITCODE -notin 0, 1) { throw 'credential scan execution failed' }
if ($credentialFindings.Count -ne 0) { throw 'credential scan finding' }
$privatePathPattern = '(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+|/(?:root|home|Users|mnt|tmp|var/tmp|private|Volumes)(?=/|\s|$))'
$privatePathFindings = @(rg -n --pcre2 $privatePathPattern src schemas configs tests/fixtures --glob '!src/mdcp/temporal/evidence.py')
if ($LASTEXITCODE -notin 0, 1) { throw 'private-path scan execution failed' }
if ($privatePathFindings.Count -ne 0) { throw 'private-path scan finding' }
uv run pytest tests/security/temporal/test_public_evidence_boundary.py -q
```

Separately verify `src/mdcp/temporal/evidence.py` against its source inventory. Recompute W0–W2
protected digests, v1/v2 serving identities, corrective design/plan digests, static/behavioral
firewall identities, and H2 sealed/zero. Require independent read-only review Critical `0`,
Important `0`.

Expected: all gates PASS, working tree clean, remote `0`, no HEAD tag, no UCI/H1/H2 row access, and
no natural/model/Docker/GPU/network operation. Record the full current HEAD as
`SEARCH_SOURCE_COMMIT`; do not create an empty commit.

- [ ] **Step 3: Generate only the two canonical freeze files**

Run:

```powershell
uv run python -m mdcp.temporal.cli prepare-search-freeze --repository-root . --created-at-utc ((Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ"))
git status --short --untracked-files=all
```

Expected: exactly the two allowlisted JSON additions; their receipt source equals the full Task 6
HEAD; the index has the exact closed source/output inventories; no private path or output digest.

- [ ] **Step 4: Commit the exact child and run GREEN**

```powershell
git add evidence/public/v02/search/search-receipt.json evidence/public/v02/search/evidence-index.json
git commit -m "chore: freeze corrected v0.2 development search"
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
```

Expected: `SEARCH_FREEZE_PASS`; HEAD has exactly one parent equal to `SEARCH_SOURCE_COMMIT`; the
parent/child diff is exactly two added regular `100644` JSON blobs.

- [ ] **Step 5: Verify final stop invariants and report P2 checkpoint**

Run the actual no-`.git` source-inventory proof from the committed freeze:

```powershell
$archiveRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mdcp-w3-freeze-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $archiveRoot | Out-Null
git archive --format=tar HEAD -o (Join-Path $archiveRoot "freeze.tar")
New-Item -ItemType Directory -Path (Join-Path $archiveRoot "tree") | Out-Null
tar -xf (Join-Path $archiveRoot "freeze.tar") -C (Join-Path $archiveRoot "tree")
uv run python -m mdcp.temporal.cli verify-search-source --root (Join-Path $archiveRoot "tree") --index (Join-Path $archiveRoot "tree/evidence/public/v02/search/evidence-index.json")
```

Expected: `SEARCH_SOURCE_INVENTORY_PASS`; the extracted tree contains no `.git` directory.

Verify clean status, remote `0`, no tag, H2 `SEALED_NOT_LOADED`/`0`, authorization absent and
unconsumed, fit ledger `0`, and no private development output root. Report source/freeze SHAs,
receipt/index/source-inventory digests, all seven commits, tests, review, and protected identities.

Stop at:

```text
W3_EXECUTION_BOUNDARY_CORRECTED / SEARCH_FREEZE_PASS /
P2_FORMAL_RUN_AUTHORIZATION_REQUIRED / H2_SEALED_NOT_LOADED
```

Do not execute `run-development`, load the UCI archive, create a result index, begin Task 3.5, or
enter Wave 4.

## Hard stop conditions

Stop without scope expansion if any of these occurs:

- entry identity, branch, unique registered worktree, clean state, remote, tag, protected digest,
  design/plan digest, or H2 state differs;
- a change is needed outside the exact allowlist;
- a production test seam can create natural evidence or caller-controlled probes can reach the
  formal CLI;
- the runtime cannot obtain authoritative Windows/Linux peak memory;
- a second replay, rank-two fallback, replay reconstruction, or retry path remains;
- static/behavioral firewall, public evidence, source archive, full CPU, Ruff, lock, diff, or
  independent review gate fails;
- three separately evidenced fix hypotheses fail for the same blocker; or
- any step requires UCI/H1/H2 rows, a natural/formal model fit outside the existing synthetic CPU
  regression suite, dependency change, network, Docker, GPU, remote, history rewrite, deletion, or
  relaxed threshold.

On a hard stop, preserve the cleanest reachable state and report:

```text
V02_W3_EXECUTION_CORRECTIVE_BLOCKED / P2_FORBIDDEN / H2_SEALED_NOT_LOADED
```
