# MDCP v0.2 Wave 3 Private-Evidence Container Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blocked directory-based private-evidence publisher with one canonical
Windows no-clobber container, finish the approved one-shot formal execution boundary, freeze the
exact corrected source, and stop before P2.

**Architecture:** One deterministic RFC 8785 container is built in memory, then written through one
exclusive handle-relative Windows `NtCreateFile(FILE_CREATE)` handle under a retained reparse-safe
ancestor chain. Non-Windows publication fails before mutation, while pure container verification
and source-archive identity remain cross-platform. The existing one-process runner, durable P2
authorization, public/private boundary, exact 41-path source identity, and receipt-only freeze are
completed serially after this correction.

**Tech Stack:** Python 3.12, Pydantic v2, RFC 8785, SHA-256, strict base64, Windows `ctypes` NT/file
APIs, pytest, Ruff, uv, and the repository's existing deterministic CPU-only fixtures.

## Approved identities and entry

- Normative temporal design:
  `docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md`.
- Execution-boundary corrective design:
  `docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md`.
- Single-container amendment:
  `docs/superpowers/specs/2026-08-26-mdcp-v02-private-evidence-container-design.md`.
- Single-container amendment review head:
  `6886ff191492bedd97e4f7782b265f6c4e0df50f`.
- Amendment SHA-256:
  `5446559e1161d6109db080ae4941dfba3c48d0a7e6d9c66db373d6007142a523`.
- Historical execution corrective plan, retained unchanged:
  `docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md`.
- Blocked directory implementation checkpoint:
  `90282ac6f753c7241a2e058f505de77976d210fe`.

The owner standing authorization binds the exact append-only commit containing this plan after the
plan passes self-review and independent review with Critical `0`, Important `0`. That commit is the
execution entry. A mismatched branch, dirty status, remote, HEAD tag, protected identity, or H2
state is an entry failure; do not repair it with Git history operations.

## Global constraints

- Locate the one registered worktree for branch `codex/wave0-foundation-feasibility` and the exact
  plan-entry HEAD with `git worktree list --porcelain`; zero or multiple matches stop.
- Entry and every task boundary require working tree clean, remote count `0`, no tag at HEAD, H2
  `SEALED_NOT_LOADED`, H2 loaded rows `0`, and unchanged protected bytes.
- Preserve history append-only. Never amend, reset, checkout-restore, rebase, stash, cherry-pick,
  squash, or delete the directory-based commits.
- Every commit uses `kuotunyu <61350295+kuotunyu@users.noreply.github.com>` as author and committer.
- Do not modify approved specifications, any historical plan, `pyproject.toml`, `uv.lock`, workload
  configs, Wave 0–2 protected source/evidence, v0.1/v0.2 identities, preserved rejection evidence,
  datasets, or H2 state.
- Do not read UCI/H1/H2 rows; perform model fitting, trial execution, ONNX, MLflow, Docker, GPU, or
  network activity; create/use a remote; push, merge, tag, or Release; consume P2; run the formal
  command; or begin Wave 4.
- Tests use only deterministic generated fixtures. No test opens the approved UCI archive or calls
  a real model family.
- Keep exactly four folds, 20 trials, 19 eligible candidates, 80 selection fits, at most four replay
  fits, one later Wave 4 final fit, at most 85 total fits, seed `2026`, one estimator thread, 2,000
  bootstrap replicates, index `1899`, exact 18 fields, thresholds `0.97`/`1.05`, and subgroup
  minimum `100`.
- Every task observes an exact RED caused by the missing behavior, implements minimum GREEN, runs
  its targeted and regression gates, obtains independent read-only review with Critical `0` and
  Important `0`, and creates one scoped append-only commit before the next task.
- If one blocker survives three separately evidenced hypotheses, a required file falls outside the
  allowlist, a protected byte drifts, or any Critical/Important remains, stop clean.
- Task 7 is terminal. PASS means `SEARCH_FREEZE_PASS` and P2 authorization required, never a formal
  development run.

## Exact implementation allowlist

Only these 19 paths may change during Tasks 2R–7:

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

The last two paths are forbidden before Task 7. If implementation requires a private-container
schema file, dependency change, or any other path, stop for owner review.

---

### Task 2R: Replace the private directory tree with one canonical container

**Files:**
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify only if its existing public identity needs exact closure:
  `schemas/v2/development-result-index.schema.json`
- Modify: `tests/unit/temporal/test_run_evidence.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Preserves: `PrivateFoldEvidence`, `PrivateRunBundle`, `PrivateBundleIdentity`,
  `write_synthetic_bundle_no_clobber(destination, bundle) -> PrivateBundleIdentity`.
- Adds: `PrivateContainerCheck` with only `verdict`, `reason_codes`, and optional validated
  `identity`; `_canonical_private_container(bundle) -> tuple[bytes, PrivateBundleIdentity]`; and
  `verify_private_container(path, expected_identity) -> PrivateContainerCheck`.
- Removes: staging-directory creation, descendant layout writers/verifiers, directory rename, and
  POSIX publication attempts.
- Does not add: a public natural writer or caller-supplied evidence class/digest/writer callback.

Use this exact sanitized verifier shape:

```python
class PrivateContainerCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    verdict: Literal["PASS", "FAIL"]
    reason_codes: tuple[
        Literal[
            "PRIVATE_CONTAINER_INVALID",
            "PRIVATE_CONTAINER_NONCANONICAL",
            "PRIVATE_CONTAINER_IDENTITY_MISMATCH",
            "PRIVATE_CONTAINER_SIZE_EXCEEDED",
        ],
        ...,
    ]
    identity: PrivateBundleIdentity | None = None
```

- [ ] **Step 1: Write exact container RED tests**

Replace directory-success assertions and add these tests before changing production code:

```python
def test_private_bundle_is_one_deterministic_canonical_file(tmp_path: Path) -> None:
    first = tmp_path / "first.container.json"
    second = tmp_path / "second.container.json"
    first_identity = write_synthetic_bundle_no_clobber(first, synthetic_private_bundle())
    second_identity = write_synthetic_bundle_no_clobber(second, synthetic_private_bundle())
    assert first.is_file() and second.is_file()
    assert first.read_bytes() == second.read_bytes()
    assert first_identity == second_identity
    assert verify_private_container(first, first_identity).verdict == "PASS"


def test_coordinated_internal_rehash_cannot_change_bound_container(tmp_path: Path) -> None:
    destination = tmp_path / "bundle.container.json"
    identity = write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    document = parse_json_bytes(destination.read_bytes())
    coordinate_payload_and_all_internal_digests(document)
    destination.write_bytes(canonicalize_json(document))
    assert verify_private_container(destination, identity).reason_codes == (
        "PRIVATE_CONTAINER_IDENTITY_MISMATCH",
    )
```

`coordinate_payload_and_all_internal_digests` changes one decoded payload, then recomputes that
entry's size/digest, `inventory_sha256`, `manifest_sha256`, and canonical outer bytes. It never uses
the production container builder.

Add closed negative matrices for top-level/entry extra and duplicate keys; missing, extra,
duplicate, and reordered logical paths; invalid count/size booleans; noncanonical JSON; strict
base64 alphabet/padding/re-encoding; noncanonical decoded payload; 129 entries; payload over
128 MiB; decoded aggregate over 384 MiB; container over 512 MiB; absolute/non-ASCII/dot/Windows-
alias logical paths; malformed lowercase digests; existing file/directory/link destination; second
publication; natural class without permit; and failure messages that contain only fixed codes.

Add Windows REDs for exact regular-file publication, `FILE_CREATE`, share `0`, descendant
`FILE_OPEN_REPARSE_POINT`, retained no-delete ancestor handles, junction/symlink/cross-volume and
normalized-handle-name rejection, destination create collision, short write, file-flush failure,
parent-directory-flush failure, post-write identity mismatch, handle-bound cleanup, and absence of
staging/rename/path-open calls. Add explicit raw destination REDs for every pre-mutation path class:
8.3/tilde component, trailing dot, trailing space, `CON`/`PRN`/`AUX`/`NUL`, `COM1..COM9`,
`LPT1..LPT9`, ADS colon, UNC, `\\?\`, `\\.\`, relative, dot/dot-dot, non-NFC, and normalized final-
handle mismatch. Assert the destination/parent remains unchanged and the fixed error does not echo
the raw path.
Add a platform-dispatch RED proving a forced `posix` branch returns `PUBLICATION_UNSUPPORTED` while
the test directory remains byte-for-byte empty. Only junction/cross-volume fixture setup may skip
for missing Windows capability.

- [ ] **Step 2: Run and record RED**

Run:

```powershell
uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py -q
```

Expected: the regular-file assertions fail because current success creates a directory; container
verification and exact create-option tests fail because the APIs/behavior do not exist. Preserve
the command, failing test names, and reason in the task ledger.

- [ ] **Step 3: Implement the closed pure container model**

Use exact internal constants:

```python
_PRIVATE_CONTAINER_SCHEMA = "mdcp.private-evidence-container.v1"
_MAX_PRIVATE_ENTRIES = 128
_MAX_PRIVATE_PAYLOAD_BYTES = 128 * 1024**2
_MAX_PRIVATE_TOTAL_BYTES = 384 * 1024**2
_MAX_PRIVATE_CONTAINER_BYTES = 512 * 1024**2
```

`_canonical_private_container` first validates exact runtime types and the already sorted logical
files. Encode each payload with
`base64.b64encode(item.canonical_bytes).decode("ascii")`; build entry models with only
`logical_path`, `byte_size`, `sha256`, and `payload_base64`. Construct digest layers exactly as
Sections 4.1–4.2 of the amendment specify. Validate the final exact model, canonicalize it once, and
enforce the container limit before filesystem dispatch.

`verify_private_container` performs the ten ordered checks in Section 4.3, strict-decodes base64
with `validate=True`, re-encodes for equality, recomputes every layer, and compares the four-field
expected identity. It accepts only a regular non-link file and returns only fixed codes from:

```text
PRIVATE_CONTAINER_INVALID
PRIVATE_CONTAINER_NONCANONICAL
PRIVATE_CONTAINER_IDENTITY_MISMATCH
PRIVATE_CONTAINER_SIZE_EXCEEDED
```

- [ ] **Step 4: Implement the exact Windows publisher and non-Windows denial**

Validate the raw `Path` with the design's drive-local/NFC/component oracle before opening. Open the
drive root once using `CreateFileW` with reparse-point and backup-semantics flags. Open every child
directory with handle-relative `NtCreateFile(FILE_OPEN)` and exact options
`FILE_DIRECTORY_FILE|FILE_OPEN_REPARSE_POINT|FILE_SYNCHRONOUS_IO_NONALERT`, sharing read/write but
not delete. Retain all ancestor handles.

Create the final non-directory child exactly once with handle-relative
`NtCreateFile(FILE_CREATE)`, share `0`, synchronous/write-through options, and write/delete/
synchronize/read-attributes authority. Loop until all prebuilt bytes are written; reject zero/short
progress. Call `FlushFileBuffers` on the file handle, recheck file and retained ancestor identities,
then call `FlushFileBuffers` on the retained trusted-parent directory handle while both the final
file and all ancestor handles remain live. A parent flush failure is `PUBLICATION_FAILED` and enters
the same handle-bound cleanup path; there is no success fallback for a filesystem that rejects the
authoritative Windows durability primitive. Only after both flushes and all checks pass may the
file close, followed by the ancestor handles. On a handled failure before successful close, call
`SetFileInformationByHandle(FileDispositionInfo)` only on the owned share-zero file handle. A
cleanup failure remains `PUBLICATION_FAILED`; do not reopen/delete by name. Remove all staging,
layout, and rename helpers.

For `os.name != "nt"`, return `PUBLICATION_UNSUPPORTED` before `_absolute_destination`, file open,
directory enumeration, or any mutation. Pure build/verification remains platform-neutral.

- [ ] **Step 5: Run GREEN and regression gates**

Run:

```powershell
uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q
uv run pytest tests/security/temporal/test_behavioral_data_firewall.py tests/integration/temporal/test_contract_gate.py -q
uv run ruff check src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git diff --check
```

Expected: all PASS; base Windows publication has no skip; behavioral H2 firewall is six PASS and
H2 remains sealed/zero.

- [ ] **Step 6: Independent review and scoped commit**

Review the Task 2R diff against this plan and the amendment. Require Critical `0`, Important `0`.
If review fixes are required, observe a focused RED and rerun Step 5 before review again.

Commit only the actually changed Task 2R paths:

```powershell
git add src/mdcp/temporal/run_evidence.py schemas/v2/development-result-index.schema.json src/mdcp/temporal/firewall.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "fix: publish one canonical private evidence container"
```

Omit the schema from `git add` if its bytes did not change.

### Task 3: Enforce one fit ledger and one transient replay session

**Files:**
- Modify: `src/mdcp/temporal/runner.py`
- Modify: `tests/unit/temporal/test_fit_ledger.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Produces: `FitPhase`, `FitRecord`, `FitLedger`, `DevelopmentRunBundle`,
  `_DevelopmentExecutionPlan`, and
  `_run_development_core(plan, guard) -> DevelopmentRunBundle`.
- Consumes: exact trial/fold inventories, existing Wave 2 evaluation/qualification/selection,
  `RuntimeGuard`, `PrivateRunBundle`, and closed public receipts.
- Removes: arbitrary replay target, reconstructable selection authority, final-fit permission,
  public callback injection, and any independently invocable replay function.

- [ ] **Step 1: Write one-shot RED tests**

```python
def test_fit_ledger_allows_only_frozen_selection_then_rank_one_replay() -> None:
    ledger = FitLedger()
    for trial_id in EXACT_TRIAL_IDS:
        for fold_id in ("F1", "F2", "F3", "F4"):
            ledger.record_selection(trial_id, fold_id)
    ledger.bind_provisional(EXACT_RANK_ONE)
    for fold_id in ("F1", "F2", "F3", "F4"):
        ledger.record_replay(EXACT_RANK_ONE.trial_id, fold_id)
    with pytest.raises(FitBudgetError, match="REPLAY_ALREADY_CONSUMED"):
        ledger.record_replay(EXACT_RANK_ONE.trial_id, "F1")


def test_core_uses_existing_rank_one_and_same_session_for_replay() -> None:
    result = synthetic_run(one_qualified_trial="STAT-A1")
    assert result.fit_ledger.selection_count == 80
    assert result.fit_ledger.replay_count == 4
    assert result.selection.final_winner.trial_id == "STAT-A1"
```

Add arbitrary/rank-two target, reconstructed/repeated session, wrong/duplicate fold, 81st selection,
fifth replay, Wave 3 final fit, changed replay digest, invalid typed verdict, poor-quality four-fold
completion, contract-invalid no replacement, runtime failure before next fit, and second invocation
with consumed state.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py -q`

Expected: one-shot/session tests fail against the unaccepted runner composition.

- [ ] **Step 3: Implement minimum GREEN orchestration**

Iterate exact trial IDs then F1–F4. Use the existing completeness, evaluation, qualification,
ranking, `ReplaySelectionSession`, and `finalize_selection` contracts; do not copy policy. Retain one
`FitLedger` and one session for the process lifetime. Rank only the closed 19-result inventory and,
if rank one exists, replay only its same four folds immediately through that same session. No API
accepts a provisional ID. Wave 3 never records final refit.

Checkpoint the runtime guard before load, before/after every started fit, before seal, and on exit.
Keep private values in `PrivateRunBundle`; emit only typed closed public receipts. The synthetic core
forces `evidence_class="synthetic_test"`, has no archive path, and performs no estimator fit.

- [ ] **Step 4: Run GREEN, review, and commit**

Run:

```powershell
uv run pytest tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py -q
uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_behavioral_data_firewall.py -q
uv run ruff check src/mdcp/temporal/runner.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
git diff --check
```

Require independent Critical `0`, Important `0`, then:

```powershell
git add src/mdcp/temporal/runner.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
git commit -m "fix: enforce one-shot formal development session"
```

### Task 4: Consume P2 durably and expose one trusted command

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
- Produces: exact `FormalRunAuthorization`, transient non-serializable `FormalRunPermit`,
  `FormalRunBinding`, `AuthorizationCheck`, `FormalDevelopmentInputs`,
  `consume_formal_run_authorization(authorization_path: Path, consumption_root: Path,
  binding: FormalRunBinding) -> AuthorizationCheck`,
  `run_formal_development(inputs: FormalDevelopmentInputs,
  permit: FormalRunPermit) -> DevelopmentRunBundle`, and
  `write_formal_bundle_no_clobber(destination: Path, bundle: PrivateRunBundle,
  permit: FormalRunPermit) -> PrivateBundleIdentity`.
- CLI commands after this task are exactly `run-development` and `verify-search-freeze`. Task 6
  later adds `prepare-search-freeze`, `verify-search-source`, and `verify-development-result`; no
  other command is permitted.
- Formal wrapper consumes: the exact permit, corrected freeze identity, trusted runtime guard,
  bounded loader, one new regular-file private-container destination, and one new public result path.
- Removes: `replay-provisional`, caller-injected clocks/probes/writers, and public natural writers.

- [ ] **Step 1: Write authorization/composition RED tests**

```python
def test_authorization_is_consumed_once_and_bound_to_exact_freeze(tmp_path: Path) -> None:
    authorization = write_authorization(tmp_path, expected_freeze())
    consumption_root = tmp_path / "consumed"
    consumption_root.mkdir()
    first = consume_formal_run_authorization(
        authorization, consumption_root, exact_binding()
    )
    second = consume_formal_run_authorization(
        authorization, consumption_root, exact_binding()
    )
    assert first.verdict == "PASS"
    assert type(first.permit) is FormalRunPermit
    assert second.reason_codes == ("FORMAL_RUN_AUTHORIZATION_CONSUMED",)
    assert second.permit is None


def test_formal_wrapper_requires_exact_runtime_permit_type() -> None:
    with pytest.raises(FormalRunAuthorizationError, match="FORMAL_RUN_PERMIT_REQUIRED"):
        run_formal_development(formal_inputs(), True)  # type: ignore[arg-type]
```

Add wrong source/freeze/receipt/protocol digest, noncanonical bytes, duplicate keys, extra fields,
malformed or non-UTC authorization timestamp, symlink/reparse file, dirty repository, existing consumption marker/output,
directory-valued private destination, serialized/forged/subclassed permit, alternate writer,
independent replay command, and failure-after-consumption no-restore cases. Assert CLI sets exact
thread environment values before estimator-bearing imports and constructs guards internally.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py -q`

Expected: missing exact authorization/permit and formal composition behavior fail.

- [ ] **Step 3: Implement authorization and formal wrapper without executing it**

Use these exact binding/result/input types:

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
    private_container_path: Path
    search_receipt_sha256: str
    protocol_sha256: str
```

Validate authorization through the checked-in closed schema and canonical bytes. The model has
exactly: schema version, exact 40-character freeze commit, search receipt SHA-256, protocol
SHA-256, authorization ID, action literal `ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN`, UTC authorization
time, and `consumed=false`. Atomically consume by exclusive creation of a canonical sibling marker
under the caller-precreated private `consumption_root` after clean/freeze checks; never restore it.
The marker binds authorization-file digest and exact freeze/receipt/protocol identities and is
durably flushed before any loader import/call or output creation.

`FormalRunPermit` is constructible only inside successful consumption, is not a Pydantic/dataclass
serialization surface, and is consumed in memory once. The private formal wrapper accepts exactly
that permit and delegates to the same internal single-container publisher. It requires the five
approved natural logical paths and a non-existing final leaf under a precreated trusted external
parent; an existing file, directory, link, reparse point, or other destination type fails closed.
No formal command is invoked in this task.

The CLI operational mutation surface has only `run-development`; its read-only command at this
boundary is `verify-search-freeze`. Remove `replay-provisional`. Set the exact BLAS/OpenMP/joblib
thread keys to `1` before estimator-bearing imports. Construct repository, clock, memory, loader,
firewall, container, and public-publisher dependencies internally.

- [ ] **Step 4: Run GREEN, review, and commit**

Run:

```powershell
uv run pytest tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py -q
uv run pytest tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_search_freeze_preflight.py -q
uv run ruff check src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/runner.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/runner.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
git diff --check
```

Require independent Critical `0`, Important `0`, then:

```powershell
git add src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/runner.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py schemas/v2/formal-run-authorization.schema.json tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
git commit -m "security: bind one consumed formal development permit"
```

### Task 5: Prove the full execution and publication boundary

**Files:**
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Modify only when the proof exposes a defect: `src/mdcp/temporal/runner.py`,
  `src/mdcp/temporal/cli.py`, `src/mdcp/temporal/run_evidence.py`,
  `src/mdcp/temporal/runtime_guards.py`, `src/mdcp/temporal/firewall.py`

**Interfaces:**
- Produces no new production API.
- Proves: one process/session/ledger, trusted dependency construction, single-file private
  publication, public sanitization, exact fit transitions, and H2 denial.

- [ ] **Step 1: Write end-to-end and adversarial RED proofs**

```python
def test_synthetic_composition_has_one_container_and_no_private_public_leak(
    tmp_path: Path,
) -> None:
    result = run_trusted_synthetic_composition(tmp_path, qualified="STAT-A1")
    assert result.fit_count == 84
    assert result.private_destination.is_file()
    assert verify_private_container(
        result.private_destination, result.private_identity
    ).verdict == "PASS"
    assert public_evidence_violations(result.public_result.model_dump(mode="json")) == ()
    assert (result.h2_status, result.h2_loaded_rows) == ("SEALED_NOT_LOADED", 0)
```

`run_trusted_synthetic_composition` is a local test helper: it writes one canonical temporary
authorization, consumes it through the production consumer, supplies deterministic generated fold
objects through the underscore-private test harness, publishes under `tmp_path`, and returns the
typed public result, four-field private identity, destination, fit count, and H2 fields. It has no
archive path and never imports an estimator-bearing family.

Add no-qualified 80-fit, qualified 84-fit, no 85th fit, one PID/thread, one permit, repeated command,
arbitrary replay, private directory/staging/rename creation, path reopen, injected writer/probe,
malicious bounded-loader object, legacy loader/split/open_h2 spy, row/prediction/timestamp/path/
exception/credential public leak, runtime failure, publication partial, and source mutation cases.
Behavioral spies must prove forbidden call counts remain exactly zero and only deterministic
generated development rows are presented.

- [ ] **Step 2: Run RED**

Run:

```powershell
uv run pytest tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/integration/temporal/test_formal_runner_synthetic.py -q
```

Expected: at least the new single-container composition or denial-spy assertion fails before its
minimal wiring/proof correction.

- [ ] **Step 3: Apply only proof-required minimum GREEN corrections**

Do not create a second implementation. Reuse Task 2R's container primitive and Task 4's exact
permit wrapper. Tighten only exact static firewall path/symbol/attribute rules and fixed public
models needed by a failing proof. No broad module/directory wildcard, arbitrary environment read,
loader callback, writer callback, or natural execution seam is allowed.

- [ ] **Step 4: Run GREEN, review, and commit**

Run:

```powershell
uv run pytest tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_behavioral_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/integration/temporal/test_formal_runner_synthetic.py -q
uv run pytest tests/unit/temporal/test_runtime_guards.py tests/unit/temporal/test_run_evidence.py tests/unit/temporal/test_fit_ledger.py -q
uv run ruff check src/mdcp/temporal tests/integration/temporal tests/security/temporal tests/unit/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git diff --check
```

Require independent Critical `0`, Important `0`. Commit only changed allowlisted paths:

```powershell
git add src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "test: prove the formal development boundary"
```

### Task 6: Bind the exact 41-path source and offline verifier

**Files:**
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/integration/temporal/test_search_freeze_preflight.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Modify only if required for already-approved public fields:
  `schemas/v2/development-result-index.schema.json`

**Interfaces:**
- Produces: `SearchSourceEntry`, `SearchEvidenceIndex`,
  `build_search_source_inventory(root)`, `prepare_search_freeze(root, created_at_utc)`, source-
  archive verifier, and offline `verify-development-result` CLI.
- Final CLI surface after this task is exactly `run-development`, `verify-search-freeze`,
  `prepare-search-freeze`, `verify-search-source`, and `verify-development-result`.
- Binds: the amendment's exact 41 ordered source paths and exactly five logical private outputs
  inside the single container.
- Excludes: test paths from production identity and both Task 7 freeze files from source identity.

- [ ] **Step 1: Write closed-inventory RED tests**

```python
def test_search_index_has_exact_41_sources_and_five_logical_outputs(tmp_path: Path) -> None:
    index = build_index(source_tree(tmp_path))
    assert len(index.source_entries) == 41
    assert tuple(entry.logical_path for entry in index.private_outputs) == (
        "trial-summary.json",
        "qualification-report.json",
        "ranking-report.json",
        "provisional-winner.json",
        "replay-report.json",
    )
    assert index.source_inventory_sha256 == independently_recompute(index.source_entries)


def test_source_archive_without_dot_git_recomputes_exact_inventory(tmp_path: Path) -> None:
    archive_root = export_fixture_source_without_git(tmp_path)
    assert verify_search_source_inventory(archive_root, frozen_index()).verdict == "PASS"
```

`source_tree` creates exactly the 41 paths listed in the amendment with deterministic bytes.
`independently_recompute` canonicalizes ordered path/mode/size/digest entries without calling the
production builder. The archive test uses a temporary fixture repository only; it does not alter
the MDCP repository.

Add missing/extra/duplicate/reordered/unknown path, symlink, wrong mode/size/digest, coordinated
source/index mutation, amendment/plan omission, 39-path legacy inventory, test-path addition,
private output missing/extra/duplicate/order/path, physical directory interpretation, pre-run
output digest, receipt/index mismatch, result fit transition, H2 inconsistency, and source archive
without `.git` tests. Add a parser test asserting the exact five-command tuple
`("run-development", "verify-search-freeze", "prepare-search-freeze",
"verify-search-source", "verify-development-result")` and rejecting every other command.

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py -q`

Expected: current builder lacks the exact 41-path contract and offline corrected source proof.

- [ ] **Step 3: Implement exact 41-path and output identities**

Use exactly this 41-path tuple in ASCII order:

```text
configs/workload/temporal-development-v2.json
configs/workload/uci-bike-sharing-v1.json
docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md
docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md
docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md
docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md
docs/superpowers/specs/2026-08-26-mdcp-v02-private-evidence-container-design.md
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

`SearchSourceEntry` contains only logical path, Git mode, byte size, and lowercase SHA-256. Reject
missing, extra, duplicate, reordered, unknown, linked, non-regular, or noncanonical entries.
Aggregate over RFC 8785 canonical entry documents. The five private outputs are logical container
entries only; they carry no pre-run digest or physical path.

`verify-development-result` validates public canonical bytes/schema, exact fit transitions, H2
sealed/zero, and the four-field private identity without opening the private container or dataset.
Pure private-container verification remains available separately for authorized private recovery.
`prepare_search_freeze` requires clean source HEAD and absent outputs, constructs canonical receipt
then index bytes, and publishes only the two Task 7 files no-clobber; this task does not call it.

- [ ] **Step 4: Run GREEN/source-archive proof, review, and commit**

Run:

```powershell
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q
uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_behavioral_data_firewall.py -q
uv run ruff check src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git diff --check
```

Require independent Critical `0`, Important `0`, then:

```powershell
git add src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py schemas/v2/development-result-index.schema.json tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "feat: bind the corrected formal development source"
```

Omit the schema from `git add` if unchanged. The resulting clean HEAD is the sole
`SEARCH_SOURCE_COMMIT`; do not create an empty source commit.

### Task 7: Run fresh completion gates and create the receipt-only freeze child

**Files:**
- Create: `evidence/public/v02/search/search-receipt.json`
- Create: `evidence/public/v02/search/evidence-index.json`

**Interfaces:**
- Consumes: clean Task 6 `SEARCH_SOURCE_COMMIT`, every fresh gate, exact 41-path source inventory,
  approved identities, and one explicit UTC creation timestamp.
- Produces: its direct child `SEARCH_FREEZE_COMMIT` containing only two canonical public files.

- [ ] **Step 1: Observe the missing-freeze RED without mutation**

Run:

```powershell
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
```

Expected: nonzero with fixed `SEARCH_RECEIPT_MISSING`, fit count `0`, no private destination, and no
authorization consumption.

- [ ] **Step 2: Run every fresh source gate at clean Task 6 HEAD**

Run:

```powershell
uv run pytest -q
uv run pytest tests/security/temporal tests/integration/temporal tests/unit/temporal tests/contract/temporal -q
uv run pytest tests/security/temporal/test_behavioral_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py -q
uv run ruff check src/mdcp/temporal tests/unit/temporal tests/integration/temporal tests/security/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py src/mdcp/temporal/search_identity.py tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_runner_synthetic.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

Run this exact credential/private-path/publication-boundary gate. Exclude only adversarial temporal
security tests and the defensive regex source `src/mdcp/temporal/evidence.py` from credential grep:

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
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py -q -k source_archive_without_dot_git_recomputes_exact_inventory
```

Expected: both grep finding counts are `0`, the public-evidence suite passes, and the deterministic
41-path no-`.git` fixture proof reports one PASS. `src/mdcp/temporal/evidence.py` is separately
covered by the exact 41-path builder/integration proof; after Task 7 creates the actual index, Step 5
recomputes its real committed hash through `verify-search-source`.

Recompute Wave 0–2 handoff/protected digests, v1/v2 serving identities, both corrective design and
plan digests, exact 41-source identity, static/behavioral firewall identities, public schemas,
dependency lock, branch/remote/tag status, and H2 sealed/zero. The integration command above proves
the archive algorithm before freeze without inventing an index; Step 5 performs the same proof
against the actual committed freeze index.

Require an independent read-only Task 6 source review with Critical `0`, Important `0` before
creating freeze outputs. Any gate failure stops before Step 3.

- [ ] **Step 3: Generate only the two canonical freeze files**

Run:

```powershell
$createdAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
uv run python -m mdcp.temporal.cli prepare-search-freeze --repository-root . --created-at-utc $createdAtUtc
git status --short --untracked-files=all
```

Expected: exactly the two allowlisted additions. Receipt source equals full Task 6 HEAD; index has
exactly 41 source entries and five logical private outputs; H2 is sealed/zero; no private container,
authorization, result, data, or model output exists.

- [ ] **Step 4: Verify and commit the direct freeze child**

Run:

```powershell
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q
git diff --check
```

Expected: `SEARCH_FREEZE_PASS`, exact parent source HEAD, two canonical sanitized files, no other
change. Then:

```powershell
git add evidence/public/v02/search/search-receipt.json evidence/public/v02/search/evidence-index.json
git commit -m "evidence: freeze corrected temporal search source"
```

- [ ] **Step 5: Fresh post-commit proof and whole-branch independent review**

From the committed freeze child rerun Step 4 verifier, full CPU suite, temporal suites, Ruff
check/format, `uv lock --check`, `git diff --check`, scans, protected identities, source archive,
branch/remote/tag, and behavioral H2 firewall. Verify `HEAD^` is the receipt's
`SEARCH_SOURCE_COMMIT`, HEAD is its direct child, and `git diff --name-only HEAD^ HEAD` is exactly
the two freeze files.

Run the actual no-`.git` proof against the committed freeze index with these exact commands:

```powershell
$archiveRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mdcp-w3-freeze-" + [guid]::NewGuid().ToString("N"))
$archiveTree = Join-Path $archiveRoot "tree"
New-Item -ItemType Directory -Path $archiveTree | Out-Null
git archive --format=tar HEAD -o (Join-Path $archiveRoot "freeze.tar")
tar -xf (Join-Path $archiveRoot "freeze.tar") -C $archiveTree
if (Test-Path -LiteralPath (Join-Path $archiveTree ".git")) { throw 'source archive contains .git' }
uv run python -m mdcp.temporal.cli verify-search-source --root $archiveTree --index (Join-Path $archiveTree "evidence/public/v02/search/evidence-index.json")
if ($LASTEXITCODE -ne 0) { throw 'source archive identity failed' }
```

Expected stdout is exactly `SEARCH_SOURCE_INVENTORY_PASS`; this recomputes the committed
`src/mdcp/temporal/evidence.py` entry and all other 40 entries without Git history. Preserve the
command output in the completion report. Clean only this invocation-owned temporary root after
verifying the resolved target is inside the OS temporary directory and has the generated prefix:

```powershell
$resolvedArchiveRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $archiveRoot).Path)
$resolvedTempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
if (-not $resolvedArchiveRoot.StartsWith($resolvedTempRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'temporary cleanup boundary failed' }
if (-not ([System.IO.Path]::GetFileName($resolvedArchiveRoot)).StartsWith("mdcp-w3-freeze-", [StringComparison]::Ordinal)) { throw 'temporary cleanup identity failed' }
Remove-Item -LiteralPath $resolvedArchiveRoot -Recurse -Force
```

Obtain final independent read-only review of the complete corrective range. Critical and Important
must both be zero. Confirm working tree clean, remote `0`, no tag, P2 absent/unconsumed, no UCI/H1/H2
row access, no model/Docker/GPU/network/remote operation, and H2 loaded rows `0`.

Stop with exactly:

```text
SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED /
H2_SEALED_NOT_LOADED
```

Do not invoke `run-development`, create an authorization, or start Wave 4.

## Completion evidence

The final report records:

- design amendment commits/hash and independent C0/I0 review;
- this plan commit/hash and independent C0/I0 review;
- Task 2R and Tasks 3–7 commit SHAs with exact changed-file inventories;
- every observed RED and GREEN command/result;
- canonical-container format/identity and Windows publication adversarial results;
- 80/84/85 fit-boundary synthetic results and one-session proof;
- P2 authorization denial/consumption tests without actual authorization;
- exact 41-path source and five logical private-output identities;
- `SEARCH_SOURCE_COMMIT`, `SEARCH_FREEZE_COMMIT`, receipt/index SHA-256, and direct-child proof;
- full CPU/security/publication/source-archive/credential/protected-byte results;
- independent task and whole-branch review counts;
- final branch/HEAD/clean/remote/tag state; and
- H2 `SEALED_NOT_LOADED`, loaded rows `0`, P2 required, Wave 4 not started.

Any blocked outcome instead records the preserved clean checkpoint and stops at:

```text
W3_PRIVATE_CONTAINER_CORRECTIVE_BLOCKED / P2_FORBIDDEN /
H2_SEALED_NOT_LOADED
```
