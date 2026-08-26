# MDCP v0.2 Wave 3 Formal-Seal Closure Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blocked caller-visible formal permit with one closure-owned consume, execute,
seal, and recover operation; prove the boundary without natural-data execution; freeze the exact
43-path source; and stop before P2.

**Architecture:** `run_evidence.py` owns one post-initialization natural mutation operation. It
validates and consumes authorization, runs the existing one-ledger core, encodes the five-file
private container, publishes private then terminal public seal through closure-local Windows
no-clobber primitives, and returns only closed identities. Synthetic publication stays public but
synthetic-only; natural encoding and raw publication are unreachable through named module state.
Task 6 binds the no-`.git` 43-path source inventory, and Task 7 creates only the receipt/index freeze
child plus a private external custody record for the independently validated index digest.

**Tech Stack:** Python 3.12, Pydantic v2, RFC 8785, SHA-256, Windows `ctypes` NT/file APIs,
`zoneinfo`, pytest, Ruff, uv, PowerShell 7, and deterministic CPU-only generated fixtures.

## Global Constraints

- Execute only in the unique registered worktree whose branch is
  `codex/wave0-foundation-feasibility` and whose HEAD is the reviewed commit containing this plan.
- Preserve history append-only. Never amend, reset, restore with checkout, rebase, stash,
  cherry-pick, squash, or rewrite an existing commit.
- Every implementation commit uses
  `kuotunyu <61350295+kuotunyu@users.noreply.github.com>` as author and committer.
- Entry and every task boundary require a clean working tree, remote count `0`, no tag at HEAD, H2
  `SEALED_NOT_LOADED`, H2 loaded rows `0`, and unchanged protected bytes.
- Do not modify approved specifications, historical plans, `pyproject.toml`, `uv.lock`, workload
  configs, Wave 0–2 evidence, v0.1/v0.2 serving identities, preserved rejection evidence, datasets,
  or any path outside the 19-path implementation allowlist below.
- Do not read UCI/H1/H2 rows; create or consume a real formal authorization; run
  `run-development`; fit or infer a model; run ONNX, MLflow, Docker, GPU, or network operations;
  create/use a remote; push, merge, tag, or Release; or start Wave 4.
- Tests use deterministic generated objects and temporary roots only. A recovery fixture that has
  `evidence_class="natural_development"` is adversarial test data, never accepted repository or
  external natural evidence.
- Keep exactly four folds, 20 trials, 19 eligible candidates, 80 selection fits, at most four replay
  fits, one later Wave 4 final fit, at most 85 total fits, seed `2026`, one estimator thread, 2,000
  bootstrap replicates, index `1899`, exact 18 fields, thresholds `0.97`/`1.05`, and subgroup
  minimum `100`.
- Tasks 4 and 6 observe real REDs caused by missing production behavior, implement minimum GREEN,
  run targeted/regression gates, receive an independent read-only review with Critical `0` and
  Important `0`, then create one scoped append-only commit. Task 5 is an explicit verification-only
  task: it independently tests an already-GREEN boundary and must not manufacture a failing RED.
  Task 7 observes the missing-freeze RED, performs the no-clobber evidence mutation, then runs its
  review/commit gates.
- If one blocker survives three separately evidenced hypotheses, a required path is outside the
  allowlist, a protected identity drifts, a test requires natural/UCI/H1/H2/model execution, or any
  Critical/Important remains, stop at a clean checkpoint.
- Task 7 is terminal. PASS is exactly
  `SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED / H2_SEALED_NOT_LOADED`.

## Approved Identities and Immutable Migration Baseline

- Immutable Task 3 baseline: `3c0fcddd7fded5f62d3f731864ff423f815fff16`.
- Completed Task 2R commits: `6d641a2`, `9bccd85`, `2712b44`.
- Completed Task 3 commits: `71a94ad`, `3c0fcdd`.
- Formal-seal closure design commit: `1874aa4ec57866873fcdbc96ab3552b2dcdbab09`.
- Owner-approval record commit: `2d6c703`.
- Approved design path:
  `docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-closure-design.md`.
- Approved design SHA-256 after the approval-status commit:
  `10d6d28106fdd288dc7bfd2cbd7c9a0acea39c0dbbbfa6599bf595fe3d1609a1`.
- Preserved blocked Task 4 diagnostic root:
  `C:/Users/3Hml/AppData/Local/Temp/mdcp-task4-blocked-20260825-222551Z`.
- Preserved blocked patch SHA-256:
  `790aaccd3e6a219c910bf61613525cb7974d5976f22f68d8517921df79aa2f2d`.

The diagnostic patch is reference-only and is never applied wholesale. The exact append-only commit
that contains this plan after self-review and independent Critical `0`/Important `0` review is the
sole implementation entry. Task 2R, Task 3, the design, and approval commits remain immutable.

## Exact 19-Path Implementation Allowlist

Only these repository paths may change during corrected Tasks 4–7:

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

The last two paths are forbidden before Task 7. A private-container schema, dependency change, new
production module, new test module, or any other repository path requires an owner stop.

## File Responsibility Map

- `run_evidence.py`: exact public/private models, synthetic-only writer, closure-owned formal
  operation, terminal-seal recovery, and closure-local Windows mutation primitives.
- `search_identity.py`: closed `FormalRunAuthorization`, search receipt/freeze, 43-path source index,
  and source-archive verification.
- `runner.py`: already-approved one-shot 80+4 pure execution core; it returns one internal typed
  fold/session result and gains no authorization, natural writer, destination, or callback surface.
  `run_evidence.py` alone formalizes that internal result into the five natural logical files.
- `runtime_guards.py`: authoritative/synthetic runtime checkpoints and the independently
  recomputable tracked-tree inventory algorithm.
- `cli.py`: exact command/argument surface, thread environment setup, fixed sanitized output, and no
  separate natural handler or replay command.
- `firewall.py`: exact named-callable, import, path, environment, Git, loader, and H2 capability
  allowlists.
- `development-result-index.schema.json`: top-level `FormalDevelopmentSeal` and closed nested
  `PublicDevelopmentResult`.
- `formal-run-authorization.schema.json`: exact canonical private authorization shape.
- Task 4 tests: model/schema/recovery/Windows matrix/CLI/closure reachability.
- Task 5 tests: independent whole-boundary and concurrency proof with synthetic objects only.
- Task 6 tests: 43-path/no-`.git`/external-index-anchor proof.
- Task 7 evidence: exactly the two canonical public freeze files.

---

### Task 4: Replace Permit Composition with One Closure-Owned Formal Seal

**Files:**
- Modify: `schemas/v2/development-result-index.schema.json`
- Create: `schemas/v2/formal-run-authorization.schema.json`
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `src/mdcp/temporal/runner.py`
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Create: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/unit/temporal/test_run_evidence.py`

**Interfaces:**
- Consumes: clean exact freeze repository, canonical receipt/index, private authorization path,
  private consumption root, approved archive path, and absent paired destinations.
- Produces exactly these new `run_evidence.py` public models/functions:

```python
@dataclass(frozen=True, slots=True)
class FormalDevelopmentRequest:
    repository_root: Path
    expected_freeze_head: str
    search_receipt_path: Path
    evidence_index_path: Path
    authorization_path: Path
    consumption_root: Path
    archive_path: Path
    private_container_path: Path


@dataclass(frozen=True, slots=True)
class FormalDevelopmentOutcome:
    verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    private_identity: PrivateBundleIdentity | None
    seal_record_sha256: str | None
    repository_inventory_sha256: str | None
    authorization_sha256: str
    consumption_marker_sha256: str | None
    fit_count: int
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]


def execute_authorized_formal_development(
    request: FormalDevelopmentRequest,
) -> FormalDevelopmentOutcome:
    """The sole natural mutation operation."""


def verify_formal_development_seal(
    consumption_marker_path: Path,
    private_container_path: Path,
    terminal_seal_path: Path,
    *,
    expected_authorization_sha256: str,
    expected_search_receipt_sha256: str,
    expected_source_inventory_sha256: str,
    expected_repository_inventory_sha256: str,
    expected_seal_record_sha256: str,
) -> FormalSealCheck:
    """Read-only exact-chain verification; never resumes a run."""


class FormalRunConsumptionMarker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal["mdcp.formal-run-consumption.v1"]
    canonicalization_version: Literal["RFC8785"]
    consumed: Literal[True]
    authorization_sha256: Sha256
    search_freeze_commit: GitCommit
    search_receipt_sha256: Sha256
    protocol_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]


class FormalDevelopmentSeal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal["mdcp.formal-development-seal.v1"]
    canonicalization_version: Literal["RFC8785"]
    terminal_state: Literal["SEALED"]
    authorization_sha256: Sha256
    consumption_marker_sha256: Sha256
    search_freeze_commit: GitCommit
    search_receipt_sha256: Sha256
    source_inventory_sha256: Sha256
    protocol_sha256: Sha256
    repository_inventory_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]
    private_identity: PrivateBundleIdentity
    exit_observation_sha256: Sha256
    fit_count: Literal[80, 84]
    selection_status: Literal[
        "PASS", "NO_ELIGIBLE_CANDIDATE", "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
    ]
    h1_role: Literal["OBSERVED_DEVELOPMENT_ONLY"]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    development_result: PublicDevelopmentResult


@dataclass(frozen=True, slots=True)
class FormalSealCheck:
    verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    private_identity: PrivateBundleIdentity | None
    seal_record_sha256: str | None
    repository_inventory_sha256: str | None
    fit_count: Literal[0, 80, 84]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
```

- Produces exactly one new `search_identity.py` public model: `FormalRunAuthorization`.
- Leaves `runner.py` with no new public formal callable.
- Leaves the Task 4 CLI tuple exactly `("run-development", "verify-search-freeze")`.
- Removes every caller-visible permit, claim, activation, consume-only, natural builder/writer,
  natural callback, and raw publisher surface.

- [ ] **Step 1: Write RED model, schema, and closed-outcome tests**

Add tests that import the exact models above and validate every row of the approved outcome matrix.
Use fixed digests instead of external data:

```python
ZERO = "0" * 64
A = "a" * 64
M = "b" * 64
R = "c" * 64
S = "d" * 64


def test_pass_outcome_requires_all_accepted_identities() -> None:
    outcome = FormalDevelopmentOutcome(
        verdict="PASS",
        reason_codes=(),
        private_identity=exact_private_identity(),
        seal_record_sha256=S,
        repository_inventory_sha256=R,
        authorization_sha256=A,
        consumption_marker_sha256=M,
        fit_count=84,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )
    assert outcome.fit_count == 84


@pytest.mark.parametrize("fit_count", (0, 1, 79, 81, 83, 85))
def test_pass_outcome_rejects_nonterminal_fit_counts(fit_count: int) -> None:
    with pytest.raises(ValueError, match="FORMAL_DEVELOPMENT_OUTCOME_INVALID"):
        replace(exact_pass_outcome(), fit_count=fit_count)
```

Add one explicit negative test for each closed FAIL/UNKNOWN reason, zero/nonzero authorization rule,
marker population rule, private/seal/repository `None` rule, boolean fit count, extra field, wrong
selection/status pair, 80-fit pre-replay UNKNOWN, 84-fit replay UNKNOWN, and H2 mutation.

Generate `FormalDevelopmentSeal.model_json_schema()` as the checked-in top level. Assert the nested
`PublicDevelopmentResult` is still exact, closed, and validates synthetic results only through its
definition. Mutate every top-level binding, nested extra key, digest shape, five-file identity,
selection/status pair, fit count, and EXIT/repository field and require schema/Pydantic rejection.

- [ ] **Step 2: Write RED recovery truth-table fixtures**

Build bounded artificial marker/private/terminal bytes only under `tmp_path`; do not call the formal
operation. Cover every recovery row with exact trusted inputs:

```python
def test_valid_chain_without_external_seal_anchor_is_unknown(tmp_path: Path) -> None:
    chain = write_artificial_chain(tmp_path, fit_count=84, selection_status="PASS")
    check = verify_formal_development_seal(
        chain.marker,
        chain.private,
        chain.terminal,
        expected_authorization_sha256=chain.authorization_sha256,
        expected_search_receipt_sha256=chain.search_receipt_sha256,
        expected_source_inventory_sha256=chain.source_inventory_sha256,
        expected_repository_inventory_sha256=chain.repository_inventory_sha256,
        expected_seal_record_sha256=ZERO,
    )
    assert (check.verdict, check.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_SEAL_UNANCHORED",),
    )
    assert check.private_identity is None
```

Add missing-all, marker-missing-with-artifact, partial/malformed marker, valid marker with missing or
malformed private/terminal, internal chain mismatch, each external-anchor mismatch, invalid/zero
expected digest, I/O uncertainty, fully anchored 80/84 PASS, and no-mutation assertions. Every
non-PASS result must expose `None/None/None/0` for private/seal/repository/fit.

Add exact sanitized EXIT tests. The independent test helper constructs only this closed RFC 8785
preimage and never calls a production encoder:

```python
def independent_exit_preimage(repository_sha256: str, freeze_head: str) -> bytes:
    return canonicalize_json(
        {
            "elapsed_within_budget": True,
            "max_elapsed_ns": 21_600_000_000_000,
            "max_peak_process_bytes": 4_294_967_296,
            "memory_within_budget": True,
            "reason_codes": [],
            "repository_inventory_sha256": repository_sha256,
            "schema_version": "mdcp.formal-exit-observation.v1",
            "search_freeze_commit": freeze_head,
            "stage": "EXIT",
            "verdict": "PASS",
        }
    )
```

Require exact digest equality with the seal, then mutate every key, literal, reason array, digest,
boolean, and commit. Reject boolean-as-integer, negative elapsed/memory, elapsed above
`21_600_000_000_000`, memory above `4_294_967_296`, missing/zero repository identity, wrong
stage/status, extra key, and opaque digest. The offline verifier independently reconstructs the same
bytes from the terminal seal and frozen constants.

- [ ] **Step 3: Write RED reachability, Windows matrix, and CLI tests**

Create `tests/security/temporal/test_formal_run_authorization.py` with exact post-import surface
enumeration. Walk named module attributes, aliases, bound methods, defaults, keyword defaults,
class attributes, registries, allowed factory results, and public return values. Assert:

```python
FORBIDDEN_NAMES = (
    "FormalRunPermit",
    "consume_formal_run_authorization",
    "claim_formal_run",
    "activate_formal_run",
    "write_formal_bundle_no_clobber",
    "canonical_natural_container",
    "publish_windows_container",
)


def test_no_named_intermediate_formal_authority_exists() -> None:
    for module in (cli, run_evidence, runner, search_identity):
        for name in FORBIDDEN_NAMES:
            assert not hasattr(module, name)
```

Extend the deterministic fake Windows API harness in
`tests/unit/temporal/test_run_evidence.py` through an exact isolated-loader mechanism. The test reads
the checked `run_evidence.py` bytes, parses them with `ast`, extracts the exact factory
`FunctionDef`, and in memory changes only that copied function's return tuple to append a test adapter
for the nested marker/pair/synthetic primitives. It compiles that function definition under a unique
temporary module namespace containing the real model/canonical helpers and fake `ctypes.windll`
bindings, then calls the extracted factory directly; it does not execute or modify the production
module's two-target assignment. The repository file is never rewritten; the ordinary production
import is separately asserted to expose no adapter, factory, raw publisher, or nested type. Use that
adapter to observe the exact `NtCreateFile` predicate:
`STATUS_SUCCESS == 0`, `IO_STATUS_BLOCK.Status == 0`,
`IO_STATUS_BLOCK.Information == FILE_CREATED == 2`, and a non-null/non-invalid owned handle. Add
rows for collision, handle on non-success, success without handle, warning/pending/missing status,
error with leaf present/absent/indeterminate, pre-call failure, short write, file flush, identity
recheck, and checked-close failure. No test claims parent-directory flush. Replace the historical
parent-flush expectation with file-flush plus retained-ancestor/checked-close assertions.

Add repeated and eight-caller concurrent rows for an indeterminate no-leaf marker attempt. The fake
API must record exactly one `NtCreateFile`; every later same-digest call returns the fixed consumption
UNKNOWN result, and the closure-local state never returns to reusable. Add the exact pre-call/
proved-absent row showing state removal and one permitted later attempt.
Add the exact `create_entered=False` plus handle-relative `PRESENT` row: it must return
`FAIL/FORMAL_RUN_AUTHORIZATION_CONSUMED`, store `CONSUMED`, and make every repeated/concurrent call
perform zero creates. A pre-call indeterminate leaf stores `UNKNOWN` and is likewise never retried.

Record the fake-call trace across successful private publication, successful `EXIT`, and terminal
publication. Private create/write/file-flush/identity-check/checked-close must complete before
`EXIT`. After successful `EXIT`, the exact allowed trace is only `build_sanitized_exit`,
`canonicalize_exit`, `hash_exit`, `build_terminal_seal`, `publish_terminal`, `return_outcome`;
reject any loader, Git, repository read, clock, memory, estimator, fit, replay, authorization,
environment, caller callback, or caller-selected-path operation in that suffix. Inject terminal
create, short-write, flush, identity, and close failures separately and require
`UNKNOWN/FORMAL_RUN_SEAL_UNKNOWN`, marker and private retained, any owned terminal partial retained,
zero path-based delete, and no second create.

Independently precompute full-repository `R` in an artificial temporary Git repository: run
`git ls-tree -r -z --name-only <HEAD>`, require one terminating NUL and safe relative path bytes, then
SHA-256 each `path + NUL + checked working-tree bytes + NUL` in returned order. Require equality with
the synthetic runtime guard's initial and EXIT observations, the artificial terminal seal's
`repository_inventory_sha256`, the returned PASS outcome, and the exact CLI custody line. Add wrong,
zero, reordered-path, tracked-byte-drift, newline-name, missing-path, link-target-byte, and runtime/
controller mismatch RED rows.

Test CLI output by replacing the named operation at the CLI dispatch edge with fixed closed outcomes;
never invoke natural execution:

```python
def test_cli_pass_emits_one_exact_custody_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_evidence,
        "execute_authorized_formal_development",
        lambda request: pass_outcome(),
    )
    completed = invoke_cli(valid_synthetic_arguments())
    assert completed.exit_code == 0
    assert completed.stderr == ""
    assert completed.stdout == (
        '{"repository_inventory_sha256":"' + R
        + '","schema_version":"mdcp.formal-seal-custody.v1",'
        + '"seal_record_sha256":"' + S + '"}\n'
    )
```

Add exact FAIL/UNKNOWN JSON, parser rejection without argparse usage, extra-output rejection,
write/flush failure exit `4`, fixed environment-variable names, no digest injection flags, and
command tuple tests. Enumerate callable attributes on `cli` and require the exact tuple
`("build_parser", "main")`; `main` must call the operation through the imported `run_evidence`
module object, never through a second CLI callable/alias.

In the existing Task 4 test paths, also add rejected formal-call concurrency proving zero marker,
loader, model, fit, or output calls; same-plan synthetic concurrency proving exactly one consumed
execution with one ledger/session/guard lifecycle and 80 or 84 fits; exact PRE_LOAD/PRE_FIT/
POST_FIT/PRE_SEAL/EXIT ordering; no 85th fit; and static plus behavioral legacy-loader/`split_rows`/
`open_h2` counts of zero. These are Task 4 REDs and must be GREEN before the Task 4 commit; Task 5
later re-proves the boundary independently rather than introducing first coverage.

- [ ] **Step 4: Run the real RED gate and record expected causes**

Run:

```powershell
uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py -q
```

Expected: failures because the formal models/operation/recovery/schema do not exist, the generic
natural encoder and raw publisher remain named, CLI still has `replay-provisional`, and the Windows
primitive does not expose the exact marker-status evidence.

- [ ] **Step 5: Implement the exact authorization and seal models**

In `search_identity.py`, define a frozen `FormalRunAuthorization` with exactly these fields and
closed validation: schema version `mdcp.formal-run-authorization.v1`, canonicalization `RFC8785`,
40-lowercase-hex `search_freeze_commit`, lowercase `search_receipt_sha256`, lowercase
`protocol_sha256`, frozen archive digest
  `b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401`, lowercase RFC 4122 version-4
  `authorization_id` matching
  `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`, action
  `ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN`, UTC `authorized_at_utc`, and `consumed=false`. Reject
  duplicate/noncanonical JSON, extra/coerced fields, symlink/reparse input, zero/sentinel identities,
  and all mismatches without echoing values.

In `run_evidence.py`, implement the exact frozen request/outcome/check models plus:

```python
class FormalRunConsumptionMarker(BaseModel):
    schema_version: Literal["mdcp.formal-run-consumption.v1"]
    canonicalization_version: Literal["RFC8785"]
    consumed: Literal[True]
    authorization_sha256: Sha256
    search_freeze_commit: GitCommit
    search_receipt_sha256: Sha256
    protocol_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]
```

Implement `FormalDevelopmentSeal` exactly as the approved design, including
`repository_inventory_sha256`, recomputable sanitized EXIT digest, 80/84 fit count,
`PASS`/`NO_ELIGIBLE_CANDIDATE`/`UNKNOWN/NO_ELIGIBLE_CANDIDATE` status mapping, nested closed public
result, and H2 sealed/zero. Update the checked-in schemas from these exact models; do not hand-loosen
generated constraints.

- [ ] **Step 6: Make natural encoding and raw mutation closure-local**

Refactor module initialization around one zero-argument factory that defines the complete mutation
stack inside its lexical body and returns only `write_synthetic_bundle_no_clobber` and
`execute_authorized_formal_development`. Move the bodies of `_absolute_destination`,
`_publish_windows_container`, `_windows_nt_relative_file`, `_windows_write_all`, disposition/
checked-close helpers, retained-ancestor checks, private encoding, marker creation, and the whole
formal lifecycle into nested functions. Do not capture any existing helper function object whose
bytecode still performs `LOAD_GLOBAL` against a name that will be deleted.

At factory invocation, capture `os.name` first. Only when that captured value is exactly `"nt"` may
the factory access `ctypes.windll.kernel32`/`ntdll` and bind Windows calls/structures/constants. On
every other platform it sets a closure-local unsupported sentinel without evaluating any `windll`
attribute; both mutation wrappers return the fixed publication-unsupported result before path/
repository/authorization access, while the module imports and the read-only recovery verifier remain
usable. Add an isolated import test whose fake `ctypes` has no `windll`: import and recovery must
succeed, and both mutation wrappers must fail closed without touching the filesystem.

On NT, assign the required Windows calls, structure types, numeric constants, `Path`, canonicalizer/
digest functions, exact runtime model classes, exact five paths, and `Lock` to factory locals. Every
nested mutation function must resolve its transitive mutation dependencies from closure locals.
After the two wrappers are returned, delete the factory name. No raw helper ever becomes a module
attribute, initialization alias, default, registry value, class attribute, or extra factory result.

The following exact types are defined inside the factory, never returned, and never installed in
module state:

```python
@dataclass(frozen=True, slots=True)
class RetainedAncestor:
    handle: int
    volume_serial_number: int
    file_index: int


@dataclass(slots=True)
class RetainedDestination:
    absolute_path: Path
    leaf_name: str
    ancestors: tuple[RetainedAncestor, ...]
    parent_handle: int
    created: bool = False
    closed: bool = False


@dataclass(slots=True)
class RetainedPublicationPair:
    private: RetainedDestination
    terminal: RetainedDestination
    private_published: bool = False
    terminal_published: bool = False
    closed: bool = False


@dataclass(frozen=True, slots=True)
class MarkerAttempt:
    create_entered: bool
    ntstatus: int | None
    iosb_status: int | None
    iosb_information: int | None
    owned_handle_value: int | None
    leaf_state: Literal["ABSENT", "PRESENT", "INDETERMINATE"]
    result: Literal["CREATED", "COLLISION", "PRECALL_FAILED", "INDETERMINATE"]
    marker_sha256: Sha256 | None


type AttemptState = Literal["IN_PROGRESS", "CONSUMED", "UNKNOWN"]
```

The factory creates one `Lock` and one `dict[Sha256, AttemptState]`. Immediately before the marker
create, the formal operation atomically inserts `IN_PROGRESS`; an existing `IN_PROGRESS` or
`UNKNOWN` returns `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN` without a second create, while existing
`CONSUMED` returns `FAIL/FORMAL_RUN_AUTHORIZATION_CONSUMED`. Exact create success or collision stores
`CONSUMED`; any create-entered indeterminate outcome stores `UNKNOWN`; only
`PRECALL_FAILED` with handle-relative absence proved removes the entry and permits a later retry. A
`create_entered=False` observation with handle-relative leaf `PRESENT` stores `CONSUMED` and returns
`FAIL/FORMAL_RUN_AUTHORIZATION_CONSUMED`; it never enters the retryable branch. An indeterminate leaf
stores `UNKNOWN`.

The nested operation set is exact:

- `preflight_pair(private_path)` derives the terminal sibling, opens and identity-binds both full
  ancestor chains, proves both leaves absent, and returns one `RetainedPublicationPair` before the
  attempt-state transition, marker create, loader access, or fit.
- `consume_marker(consumption_root, authorization_sha256, marker_bytes)` performs the one exact
  relative `NtCreateFile(FILE_CREATE)` call, captures raw status/IOSB/owned-handle/leaf evidence,
  writes/flushes/rechecks/closes on exact success, updates the attempt-state map, and returns one
  `MarkerAttempt`. No raw handle escapes the factory.
- `publish_private(pair, content)` and `publish_terminal(pair, content)` reuse only their respective
  retained parent/ancestor handles, require the expected leaf state, create once, completely write,
  file-flush, identity-recheck, checked-close, and advance the pair state. Formal failures retain any
  marker/private/terminal or partial artifact and never delete by path.
- `close_pair(pair)` checked-closes every still-owned retained handle exactly once. Any uncertainty
  after marker success maps to the current formal UNKNOWN phase and never restores authority.
- `publish_synthetic(destination, content)` performs its own retained preflight and no-clobber create;
  on an owned partial failure only, it uses handle-based disposition before checked close, preserving
  the existing synthetic cleanup contract. It never accepts natural content.
- `encode_synthetic(bundle)` rejects every runtime type/evidence class except exact
  `PrivateRunBundle/synthetic_test`; `encode_natural(exact_five_files)` accepts only the closure-built
  exact five-file tuple and is callable only from the nested formal lifecycle.
- `execute(request)` performs the whole ordered formal lifecycle directly and returns only
  `FormalDevelopmentOutcome`. It never accepts or passes a caller callback, raw publisher, encoder,
  retained pair, marker observation, or attempt-state object.

Module initialization is exactly:

```python
write_synthetic_bundle_no_clobber, execute_authorized_formal_development = (
    _make_evidence_mutation_surface()
)
del _make_evidence_mutation_surface
```

Add a post-import disassembly/closure-vars test that both returned wrappers have no unbound name and
no global reference to a raw mutation helper, then execute synthetic no-clobber publication in the
isolated fake-Windows module after factory deletion. This is the regression that prevents capturing
a function object whose transitive globals later become `NameError`.

Remove the named `_canonical_private_container` natural branch and every post-import module-level
combination that can encode natural content or write caller-chosen bytes. Keep post-import canonical
construction synthetic-only. Reading/verifying helpers remain read-only.

Use no parent-directory flush. Require write-through synchronous final handles, complete writes,
`FlushFileBuffers` on the file, retained-ancestor identity rechecks, and checked handle close.

- [ ] **Step 7: Implement the indivisible formal lifecycle and recovery**

Implement the exact ordered lifecycle from the approved design: request/platform/repository/freeze/
receipt validation; authorization parse/bind; paired destination preflight with retained Windows
ancestors; marker `FILE_CREATE`; guard construction; bounded development load; one 80+0/4 ledger;
exact five-file natural formalization; private bytes; one `PRE_SEAL`; private publication; one `EXIT`;
sanitized EXIT hash; terminal bytes; public publication; closed outcome.

The runner returns its existing 80 selection and optional four replay `PrivateFoldEvidence` objects,
20 public trial receipts, 19 qualification results, one selection decision, one replay result or
`None`, and the single fit ledger as an internal typed result. The formal lifecycle converts that
result to a new `PrivateRunBundle` whose evidence class is `natural_development` and whose files are
the exact five `PrivateFoldEvidence` values defined below; no runner API accepts a natural evidence
class. The files are RFC 8785 canonical JSON with closed top-level keys and no physical paths,
environment values, or exceptions. Private row timestamps remain only inside the already-approved
fold-evidence documents within the private container and never enter the public seal. The files use
this exact ASCII order:

```text
provisional-winner.json
qualification-report.json
ranking-report.json
replay-report.json
trial-summary.json
```

Their exact content inventory is:

- `trial-summary.json`: schema/canonicalization/evidence-class fields, exact 80 selection fold
  documents in `TRIAL-01/F1` through `TRIAL-20/F4` order, exact 20 public trial receipts in
  `TRIAL-01` through `TRIAL-20` order, and selection fit count `80`.
- `qualification-report.json`: schema/canonicalization/evidence-class fields, exact 19 qualification
  results in `TRIAL-02` through `TRIAL-20` order, each result's verdict/family/configuration/report/
  fold digests, and the independently recomputed qualification-inventory SHA-256.
- `ranking-report.json`: schema/canonicalization/evidence-class fields, terminal selection status and
  exact reason-code tuple, retry `false`, qualification-inventory SHA-256, and the provisional
  ranking key or literal `null` when no provisional winner exists.
- `provisional-winner.json`: schema/canonicalization/evidence-class fields plus the exact provisional
  and final winner identities or literal `null`. Each non-null winner contains trial/family/
  configuration/report identities, metrics, ranking key, fold digests, and qualification-inventory
  SHA-256; the final winner is non-null only for terminal `PASS`.
- `replay-report.json`: schema/canonicalization/evidence-class fields, replay status/reason codes, and
  either zero replay folds for `NO_ELIGIBLE_CANDIDATE` or exactly four F1–F4 replay fold documents
  plus their closed replay digests for the sole provisional winner. It never names a second target.

Use these exact closed structural aliases in the implementation and tests. `Sha256` is 64 lowercase
hex; `TrialId` is `TRIAL-01` through `TRIAL-20`; `FoldId` is `F1` through `F4`; `GateStatus` is
`PASS|FAIL|UNKNOWN`; `SelectionStatus` is the exact three-value literal already used by
`SelectionDecision`; `RankingKeyJson` is exactly `[finite-float, finite-float, finite-float,
integer-family-order, TrialId]`; and every tuple below is serialized as a JSON array:

```python
class SourceIdentityJson(TypedDict):
    fold_id: FoldId
    request_id: str
    local_timestamp: str
    source_position: int
    identity_sha256: Sha256


class AdapterJson(TypedDict):
    identity: SourceIdentityJson
    succeeded: bool
    calendar_day: str | None
    groups: list[str]
    reason_code: str | None


class ValueOutcomeJson(TypedDict):
    identity: SourceIdentityJson
    succeeded: bool
    value: float | None
    reason_code: str | None


class FoldEvidenceJson(TypedDict):
    phase: Literal["SELECTION", "REPLAY"]
    trial_id: TrialId
    fold_id: FoldId
    contract_verdict: GateStatus
    inventory: list[SourceIdentityJson]
    adapters: list[AdapterJson]
    predictions: list[ValueOutcomeJson]
    labels: list[ValueOutcomeJson]
    preprocessing_state_sha256: Sha256
    feature_vector_sha256: Sha256
    prediction_vector_sha256: Sha256
    metric_sha256: Sha256
    receipt_sha256: Sha256


class QualificationFoldJson(TypedDict):
    fold_id: FoldId
    configuration_sha256: Sha256
    preprocessing_state_sha256: Sha256
    feature_vector_sha256: Sha256
    prediction_vector_sha256: Sha256
    metric_sha256: Sha256
    receipt_sha256: Sha256


class ReplayFoldJson(TypedDict):
    fold_id: FoldId
    verdict: GateStatus
    configuration_sha256: Sha256
    preprocessing_state_sha256: Sha256
    feature_vector_sha256: Sha256
    prediction_vector_sha256: Sha256
    metric_sha256: Sha256
    receipt_sha256: Sha256


class QualificationJson(TypedDict):
    trial_id: TrialId
    family_id: str
    configuration_sha256: Sha256 | None
    report_sha256: Sha256 | None
    verdict: GateStatus
    qualified: bool
    reason_codes: list[str]
    pooled_ucb95: float | None
    worst_fold_point: float | None
    worst_subgroup_ucb95: float | None
    fold_digests: list[QualificationFoldJson] | None


class WinnerJson(TypedDict):
    trial_id: TrialId
    family_id: str
    configuration_sha256: Sha256
    report_sha256: Sha256
    pooled_ucb95: float
    worst_fold_point: float
    worst_subgroup_ucb95: float
    ranking_key: RankingKeyJson
    fold_digests: list[QualificationFoldJson]
    qualification_inventory_sha256: Sha256


class TrialSummaryJson(TypedDict):
    schema_version: Literal["mdcp.natural-trial-summary.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["natural_development"]
    selection_fit_count: Literal[80]
    selection_folds: list[FoldEvidenceJson]
    public_trials: list[PublicTrialReceiptJson]


class QualificationReportJson(TypedDict):
    schema_version: Literal["mdcp.natural-qualification-report.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["natural_development"]
    qualification_inventory_sha256: Sha256
    qualifications: list[QualificationJson]


class RankingReportJson(TypedDict):
    schema_version: Literal["mdcp.natural-ranking-report.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["natural_development"]
    selection_status: SelectionStatus
    reason_codes: list[str]
    retry_allowed: Literal[False]
    qualification_inventory_sha256: Sha256
    provisional_ranking_key: RankingKeyJson | None


class ProvisionalWinnerJson(TypedDict):
    schema_version: Literal["mdcp.natural-provisional-winner.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["natural_development"]
    provisional_winner: WinnerJson | None
    final_winner: WinnerJson | None


class ReplayReportJson(TypedDict):
    schema_version: Literal["mdcp.natural-replay-report.v1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["natural_development"]
    selection_status: SelectionStatus
    reason_codes: list[str]
    replay_trial_id: TrialId | None
    replay_folds: list[FoldEvidenceJson]
    replay_digests: list[ReplayFoldJson]
```

`PublicTrialReceiptJson` is exactly `PublicTrialReceipt.model_dump(mode="json")`, whose closed
existing schema is the type definition. Lists have closed cardinality/order: selection folds 80 in
trial/fold order; public trials 20; qualifications 19; every non-null fold-digest list four in F1–F4;
replay folds/digests both zero when no provisional exists and both four in F1–F4 when replay starts.
The replay trial ID is non-null exactly with four replay folds. Winner nullability and selection/
fit-count pairing follow the exact operation matrix. No alias above is required to survive as a
module attribute; production may implement them as closure-local validation contracts.

Add AST assertions against the exact production closure body for all five literal filenames, key
sets, nullability branches, trial/fold cardinalities/order, and 80-versus-84 status mapping. Feed
independently built, deterministic artificial five-file containers into the read-only verifier to
test missing/extra/duplicate files or items, coordinated internal-digest mutation, and canonical
byte equality. These fixtures are adversarial `natural_development`-shaped test data under
`tmp_path`, never accepted evidence. Do not expose or execute a production natural formalizer seam,
do not duplicate the formalizer in test code, and do not claim successful production natural
formalization before P2.

The public leaf is derived as `<private filename>.public.json`. Acquire the marker handle before any
loader import/call, fit, or output create. Once marker create is entered, map every indeterminate
state to `FORMAL_RUN_CONSUMPTION_UNKNOWN`; only a proven no-call preparation failure is retryable.
After a canonical marker, map pre-result uncertainty to `FORMAL_RUN_EXECUTION_UNKNOWN` and
private/seal/EXIT/public uncertainty to `FORMAL_RUN_SEAL_UNKNOWN`. Never delete, restore, retry,
return a partial identity, or accept a second run.

Recovery reads bounded regular no-link files once, verifies canonical bytes and the complete
authorization-marker-private-seal-EXIT/status/H2 chain, compares all five external expectations,
and implements every approved truth-table precedence. It performs no Git/data/model access and no
mutation.

- [ ] **Step 8: Correct CLI, runner integration, and firewall**

Remove `replay-provisional`. `build_parser` and `main` are the only named CLI callables; `main` is the
only dispatcher edge to the formal operation. Set the seven approved thread environment variables
to `1` before estimator-bearing imports. Accept only the exact Task 4 arguments and literal env-var
names from the approved design. Emit one canonical stdout line, empty stderr, and exit `0/2/3/4`
under the exact custody contract.

Keep the Task 3 runner core and one-shot session intact. Move the successful `EXIT` boundary so the
formal closure can publish private bytes before the one final EXIT; failure paths still attempt each
terminal guard checkpoint at most once. No runner function accepts authorization, destination,
writer, callback, replay target, or reconstructed session.

Update the static firewall for the exact `cli.py`, `run_evidence.py`, `search_identity.py`, and
`runner.py` callable/type surface. Reject natural codec/raw writer reachability through names,
aliases, defaults, registries, class attributes, factory results, or returned objects. Preserve
direct/alias/qualified/dynamic H2 denial and exact approved Git/env/file capabilities.

- [ ] **Step 9: Run Task 4 GREEN and focused non-natural regression**

Run:

```powershell
uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py -q
uv run pytest tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_behavioral_data_firewall.py tests/integration/temporal/test_search_freeze_preflight.py -q
uv run pytest tests/security/temporal/test_public_evidence_boundary.py tests/publication -q
uv run pytest -q
uv run ruff check src/mdcp/temporal/cli.py src/mdcp/temporal/firewall.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runner.py src/mdcp/temporal/search_identity.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/cli.py src/mdcp/temporal/firewall.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runner.py src/mdcp/temporal/search_identity.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py
uv lock --check
git diff --check
```

Run the exact Task 4 credential/private-path scan:

```powershell
$credentialPattern = '-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----|Bearer[ \t]+[A-Za-z0-9._~+/=-]+|\bgh[pousr]_[A-Za-z0-9]{20,255}\b|\bgithub_pat_[A-Za-z0-9_]{20,255}\b|\bhf_[A-Za-z0-9]{20,255}\b|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'
$credentialFindings = @(rg -n --pcre2 $credentialPattern src schemas configs tests --glob '!src/mdcp/temporal/evidence.py' --glob '!tests/security/temporal/**')
if ($LASTEXITCODE -notin 0, 1) { throw 'credential scan execution failed' }
if ($credentialFindings.Count -ne 0) { throw 'credential scan finding' }

$privatePathPattern = '(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+|/(?:root|home|Users|mnt|tmp|var/tmp|private|Volumes)(?=/|\s|$))'
$privatePathFindings = @(rg -n --pcre2 $privatePathPattern src schemas configs tests/fixtures --glob '!src/mdcp/temporal/evidence.py')
if ($LASTEXITCODE -notin 0, 1) { throw 'private-path scan execution failed' }
if ($privatePathFindings.Count -ne 0) { throw 'private-path scan finding' }
```

Recompute every protected tracked blob from the Task 4 entry HEAD, not from a saved hash list:

```powershell
$planEntry = (git rev-parse HEAD).Trim()
$task4Allowlist = @(
    'schemas/v2/development-result-index.schema.json',
    'schemas/v2/formal-run-authorization.schema.json',
    'src/mdcp/temporal/cli.py',
    'src/mdcp/temporal/firewall.py',
    'src/mdcp/temporal/run_evidence.py',
    'src/mdcp/temporal/runner.py',
    'src/mdcp/temporal/search_identity.py',
    'tests/integration/temporal/test_formal_runner_synthetic.py',
    'tests/security/temporal/test_data_firewall.py',
    'tests/security/temporal/test_formal_run_authorization.py',
    'tests/unit/temporal/test_run_evidence.py'
)
$changed = @(
    git diff --name-only $planEntry --
    git ls-files --others --exclude-standard
) | Sort-Object -Unique
$outside = @($changed | Where-Object { $_ -notin $task4Allowlist })
if ($outside.Count -ne 0) { throw 'Task 4 allowlist drift' }
foreach ($path in @(git ls-tree -r --name-only $planEntry)) {
    if ($path -in $task4Allowlist) { continue }
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'protected path missing' }
    $expectedBlob = (git rev-parse "$planEntry`:$path").Trim()
    $actualBlob = (git hash-object --path="$path" -- $path).Trim()
    if ($actualBlob -ne $expectedBlob) { throw 'protected blob drift' }
}
```

Expected: all PASS, the full CPU/publication/security suites are green, all protected blobs match,
H2 is sealed/zero, no formal command/model/data execution occurred, and the change set is a subset of
the exact 11 Task 4 paths.

- [ ] **Step 10: Obtain independent Task 4 review and commit**

Review the working diff against the approved design and this task. Require Critical `0`, Important
`0`; fix findings with additional RED/GREEN evidence before commit. Then commit only actual Task 4
paths:

```powershell
git add schemas/v2/development-result-index.schema.json schemas/v2/formal-run-authorization.schema.json src/mdcp/temporal/cli.py src/mdcp/temporal/firewall.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runner.py src/mdcp/temporal/search_identity.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/unit/temporal/test_run_evidence.py
git commit -m "security: seal formal development inside one closure"
```

### Task 5: Prove the Closure-Owned Execution and Publication Boundary

**Files:**
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Create: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Modify only if a proof exposes a defect: `src/mdcp/temporal/runner.py`,
  `src/mdcp/temporal/cli.py`, `src/mdcp/temporal/run_evidence.py`,
  `src/mdcp/temporal/runtime_guards.py`, `src/mdcp/temporal/firewall.py`

**Interfaces:**
- Produces no new production API.
- Proves structural natural-authority unreachability and behavioral synthetic one-shot execution.
- The synthetic harness cannot accept authorization/archive/formal destinations, emit
  `natural_development`, construct `FormalDevelopmentSeal`, or invoke the formal operation.

- [ ] **Step 1: Write the independent structural verification proof**

In `test_formal_runner_firewall.py`, independently enumerate the exact post-import callable/type
surface and recursively inspect all allowed named reachability edges. Assert only `cli.main`
dispatches `execute_authorized_formal_development`, no permit/intermediate authority exists, no
function accepts both natural content and an output destination, and public test calls return no raw
writer/natural encoder/factory object.

Add an AST proof that factory locals are never assigned to module/global/class/registry/default
state, returned except through the exact two allowed wrappers, or reachable through a second CLI
handler. The test may inspect source structure but must not introspect closure cells or monkeypatch
trusted modules after initialization.

- [ ] **Step 2: Write synthetic concurrency and denial verification proofs**

Use only the existing `_DevelopmentExecutionPlan` deterministic generator and public synthetic
writer:

```python
def test_concurrent_synthetic_plan_has_one_ledger_and_at_most_84_fits() -> None:
    plan, calls = deterministic_generated_plan()
    outcomes = invoke_same_plan_concurrently(plan, callers=8)
    assert sum(item.verdict == "PASS" for item in outcomes) == 1
    assert len(calls) in (80, 84)
    assert max(item.fit_count for item in outcomes) <= 84
```

Add no-qualified 80, replay PASS 84, replay FAIL/UNKNOWN 84, pre-replay UNKNOWN 80, runtime failure
before 80, no 85th fit, one process and one estimator-bearing execution invocation, one
ledger/session/replay, no rank-two fallback, private
row/prediction/timestamp/path/exception/credential public leak, and exact PRE_LOAD/PRE_FIT/POST_FIT/
PRE_SEAL/EXIT order. Behavioral spies must prove legacy loader, `split_rows`, and `open_h2` counts are
all zero. The eight adversarial caller threads exercise consumption races; they do not each create an
estimator or a second execution invocation.

Add CLI rejected-call concurrency using invalid requests only. Assert zero marker/output/model/data
calls and fixed sanitized errors. Do not create a canonical valid authorization.

- [ ] **Step 3: Run the independent verification suite**

Run:

```powershell
uv run pytest tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/integration/temporal/test_formal_runner_synthetic.py -q
```

Expected: PASS against the committed Task 4 boundary. Task 5 is verification-only; a failure is a
real Task 4 regression finding, not a required RED. Preserve the failing output and enter Step 4 only
when a specific assertion exposes a defect.

- [ ] **Step 4: If and only if verification fails, apply a proof-required RED→GREEN correction**

Do not add a successful-natural test seam, authorization fixture, loader callback, writer callback,
raw bytes callback, second implementation, broad wildcard, or new module. Tighten only the exact
allowlisted production edge exposed by a failing proof. Keep all generated fixtures
`evidence_class="synthetic_test"`, UCI rows `0`, and H2 sealed/zero.

- [ ] **Step 5: Run Task 5 GREEN and full CPU regression**

Run:

```powershell
uv run pytest tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_behavioral_data_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/integration/temporal/test_formal_runner_synthetic.py -q
uv run pytest tests/unit/temporal/test_runtime_guards.py tests/unit/temporal/test_run_evidence.py tests/unit/temporal/test_fit_ledger.py -q
uv run pytest -q
uv run ruff check src/mdcp/temporal tests/integration/temporal tests/security/temporal tests/unit/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv lock --check
git diff --check
```

- [ ] **Step 6: Obtain independent Task 5 review and commit**

Require Critical `0`, Important `0`. Commit only changed allowlisted paths:

```powershell
git add src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "test: prove the closure-owned formal seal boundary"
```

### Task 6: Bind the Exact 43-Path Source and Offline Verifiers

**Files:**
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/integration/temporal/test_search_freeze_preflight.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Produces `SearchSourceEntry`, `SearchEvidenceIndex`, `build_search_source_inventory(root)`,
  `prepare_search_freeze(root, created_at_utc)`,
  `verify_search_source_inventory(root, index_path, expected_index_sha256)`, and the read-only
  `verify-development-result` CLI backed by `verify_formal_development_seal`.
- Final CLI tuple is exactly `run-development`, `verify-search-freeze`, `prepare-search-freeze`,
  `verify-search-source`, and `verify-development-result`.
- Excludes both Task 7 freeze files and all non-listed tests from source identity.

- [ ] **Step 1: Write exact-inventory and external-anchor RED tests**

Define the exact ASCII-ordered 43-path tuple in production and in an independent test constant:

```text
configs/workload/temporal-development-v2.json
configs/workload/uci-bike-sharing-v1.json
docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md
docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-formal-seal-closure-corrective.md
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md
docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md
docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-closure-design.md
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

Test exact count/order plus missing entry, extra/unknown index entry, duplicate index entry, linked or
non-regular indexed path, wrong mode/size/digest, 41-path legacy inventory, omitted amendment/plan,
test-path index addition, five private logical output count/order, and both freeze files excluded.
Unrelated regular files present in a full source archive are outside the closed 43-entry index and are
ignored; they are not treated as an extra index entry.

Add `verify-search-source` tests requiring a nonzero exact
`--expected-index-sha256`; reject missing, zero, uppercase, malformed, mismatch, and coordinated
source-plus-index mutation before treating internal digests as authentic.

- [ ] **Step 2: Write no-`.git`, recovery CLI, and command-surface RED tests**

Export a deterministic fixture source tree without `.git` and verify all 43 entries from the
externally supplied index digest. Add symlink/reparse indexed path, extra/unknown index entry, indexed
file substitution, unrelated regular archive file, and absent-index cases. The unrelated archive
file must not change the 43-entry result. The test helper independently canonicalizes ordered
path/mode/size/digest entries and does not call the production builder.

Add exact `verify-development-result` arguments for marker/private/terminal paths and the five
expected digests. It must emit fixed PASS/FAIL/UNKNOWN output without opening data/model artifacts.
Assert the exact five-command tuple and reject every other command.

- [ ] **Step 3: Run RED**

Run:

```powershell
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q
```

Expected: failures because the builder still lacks the 43-path contract, source verification lacks
the required external index digest, and final read-only CLI surfaces are absent.

- [ ] **Step 4: Implement closed source/index and offline verification**

`SearchSourceEntry` contains only logical path, Git mode, byte size, and lowercase SHA-256. Its
`git_mode` is the exact literal `"100644"` for every one of the 43 frozen paths; Task 6 first confirms
the clean Git source tree has that mode for every path. The no-`.git` verifier does not infer a Git
mode from NTFS. It requires the externally anchored index entry to contain `"100644"`, independently
requires the extracted path to be a regular no-link/no-reparse file, and verifies exact size/content.
`SearchEvidenceIndex` contains the exact source entries, aggregate source inventory SHA-256, exact
five logical private outputs, search receipt SHA-256, H2 sealed/zero, and no pre-run private/output
digest or physical path. Every model is frozen and `extra="forbid"`.

Aggregate the source inventory over RFC 8785 canonical entry documents in exact ASCII order.
`verify_search_source_inventory` hashes the canonical index bytes first and rejects a mismatch with
the nonzero external expected digest before using any digest inside the index. With no `.git`, it
verifies path/mode/size/content from the source archive and claims structure/authenticity only under
that external anchor.

`prepare_search_freeze` requires clean source HEAD and absent exact outputs, constructs canonical
receipt/index bytes, and publishes only the two Task 7 files no-clobber; Task 6 does not invoke it.
`verify-development-result` calls the read-only chain verifier and never opens UCI, H1/H2, or model
artifacts.

- [ ] **Step 5: Run Task 6 GREEN and source-archive fixture proof**

Run:

```powershell
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q
uv run pytest tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_behavioral_data_firewall.py -q
uv run ruff check src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv lock --check
git diff --check
```

- [ ] **Step 6: Obtain independent Task 6 review and create `SEARCH_SOURCE_COMMIT`**

Require Critical `0`, Important `0`. Commit only changed allowlisted paths:

```powershell
git add src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "feat: bind the closure-owned formal seal source"
```

The Task 4 terminal schema is frozen at Task 4 commit and Task 6 does not reopen it. The clean
resulting HEAD is the sole `SEARCH_SOURCE_COMMIT`; do not create an empty source commit.

### Task 7: Run Fresh Completion Gates and Create the Receipt-Only Freeze Child

**Files:**
- Create: `evidence/public/v02/search/search-receipt.json`
- Create: `evidence/public/v02/search/evidence-index.json`
- Create outside Git: one private source-index custody record under
  `D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody`

**Interfaces:**
- Consumes: clean Task 6 `SEARCH_SOURCE_COMMIT`, all fresh gates, exact 43-path inventory, and one
  explicit UTC timestamp.
- Produces: direct child `SEARCH_FREEZE_COMMIT` with exactly two public files plus an external
  no-clobber `<index-sha256>.search-source-custody.json` trust anchor.

- [ ] **Step 1: Verify Task 7 entry and precreate the private custody root**

Require clean Task 6 HEAD, remote `0`, no HEAD tag, H2 sealed/zero, and no freeze files. Resolve
`D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody`; if it exists as a link,
reparse point, non-directory, or contains a leaf for the future digest, stop. If absent, create only
that exact directory after verifying its resolved parent is
`D:/model-delivery-control-plane-runtime/evidence`. Never delete or overwrite an existing custody
file.

- [ ] **Step 2: Observe missing-freeze RED without mutation**

Run:

```powershell
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
```

Expected: fixed `SEARCH_RECEIPT_MISSING`, fit count `0`, no authorization consumption, and no
private/model/data output.

- [ ] **Step 3: Run every fresh pre-freeze gate**

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

Run the exact credential/private-path/publication scan, excluding only adversarial security tests and
the defensive regex source from credential matching:

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
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py -q -k source_archive_without_dot_git
```

Recompute the approved design/plan digests, dependency lock, v1/v2 serving identities, protected
Wave 0–2 bytes, static/behavioral firewall identities, public schemas, branch/remote/tag state, and
H2 sealed/zero. Require independent read-only Task 6 source review Critical `0`, Important `0`
before generating freeze outputs.

- [ ] **Step 4: Generate only the two canonical freeze files**

Run:

```powershell
$createdAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
uv run python -m mdcp.temporal.cli prepare-search-freeze --repository-root . --created-at-utc $createdAtUtc
git status --short --untracked-files=all
```

Expected: exactly the two allowlisted additions. Receipt source equals Task 6 HEAD; index has exactly
43 source entries and five logical private outputs; H2 is sealed/zero; no authorization, private
container, result, data, or model output exists.

- [ ] **Step 5: Independently validate and preserve the index trust anchor**

Compute the physical index digest with PowerShell, then require the repository verifier to accept
that exact external value:

```powershell
$indexPath = 'evidence/public/v02/search/evidence-index.json'
$candidateIndexSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $indexPath).Hash.ToLowerInvariant()
if ($candidateIndexSha -notmatch '^[0-9a-f]{64}$' -or $candidateIndexSha -eq ('0' * 64)) { throw 'index digest invalid' }
uv run python -m mdcp.temporal.cli verify-search-source --root . --index $indexPath --expected-index-sha256 $candidateIndexSha
if ($LASTEXITCODE -ne 0) { throw 'search source verification failed' }
```

Publish the exact RFC 8785 object with UTF-8/no-BOM and `FileMode.CreateNew` to
`D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/$candidateIndexSha.search-source-custody.json`.
The private local evidence root is outside Git, is not public evidence, and is never copied into the
repository:

```powershell
$custodyPath = "D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/$candidateIndexSha.search-source-custody.json"
$custodyJson = '{"schema_version":"mdcp.search-source-custody.v1","source_inventory_index_sha256":"' + $candidateIndexSha + '"}'
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$custodyBytes = $utf8NoBom.GetBytes($custodyJson)
$stream = [System.IO.File]::Open(
    $custodyPath,
    [System.IO.FileMode]::CreateNew,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::Read
)
try {
    $stream.Write($custodyBytes, 0, $custodyBytes.Length)
    $stream.Flush($true)
} finally {
    $stream.Dispose()
}
$readBack = [System.IO.File]::ReadAllBytes($custodyPath)
if (-not [System.Linq.Enumerable]::SequenceEqual($custodyBytes, $readBack)) {
    throw 'custody byte verification failed'
}
$custodySha = (Get-FileHash -Algorithm SHA256 -LiteralPath $custodyPath).Hash.ToLowerInvariant()
if ($custodySha -notmatch '^[0-9a-f]{64}$') { throw 'custody digest invalid' }
$retainedIndexSha = $candidateIndexSha
```

`$retainedIndexSha` is now controller-held trust state obtained before reviewing any later archive.
It must stay distinct from every freshly computed working-tree/archive digest. If that value is lost,
stop; never reconstruct the trust anchor from the source or index under review. Never overwrite or
delete the custody leaf. If publication, checked close, exact readback, or digest verification is
uncertain, stop before the freeze commit.

Before Step 6, obtain an independent read-only Task 7 review of the exact uncommitted two-file diff,
their canonical bytes/direct-child identities, and the checked external custody bytes/path. Require
Critical `0`, Important `0`. A finding stops without committing, deleting, overwriting, or regenerating
any freeze/custody file; the no-clobber evidence remains as blocked private diagnostic state.

- [ ] **Step 6: Verify and commit the direct freeze child**

Run:

```powershell
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
uv run pytest tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -q
git diff --check
```

Expected: `SEARCH_FREEZE_PASS`, exact parent source HEAD, two canonical sanitized files, no other
repository change. Then:

```powershell
git add evidence/public/v02/search/search-receipt.json evidence/public/v02/search/evidence-index.json
git commit -m "evidence: freeze closure-owned temporal search source"
```

- [ ] **Step 7: Run fresh post-commit source-archive proof**

Create a unique OS-temporary root, archive committed HEAD, extract without `.git`, and require the
external index digest:

```powershell
$indexPath = 'evidence/public/v02/search/evidence-index.json'
if ($retainedIndexSha -notmatch '^[0-9a-f]{64}$' -or $retainedIndexSha -eq ('0' * 64)) { throw 'retained index anchor unavailable' }
$workingIndexSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $indexPath).Hash.ToLowerInvariant()
if ($workingIndexSha -ne $retainedIndexSha) { throw 'working index differs from retained anchor' }
$retainedCustodyPath = "D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/$retainedIndexSha.search-source-custody.json"
$expectedCustodyJson = '{"schema_version":"mdcp.search-source-custody.v1","source_inventory_index_sha256":"' + $retainedIndexSha + '"}'
$expectedCustodyBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($expectedCustodyJson)
$actualCustodyBytes = [System.IO.File]::ReadAllBytes($retainedCustodyPath)
if (-not [System.Linq.Enumerable]::SequenceEqual($expectedCustodyBytes, $actualCustodyBytes)) { throw 'retained custody mismatch' }
$archiveRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mdcp-w3-seal-freeze-" + [guid]::NewGuid().ToString("N"))
$archiveTree = Join-Path $archiveRoot "tree"
New-Item -ItemType Directory -Path $archiveTree | Out-Null
git archive --format=tar HEAD -o (Join-Path $archiveRoot "freeze.tar")
tar -xf (Join-Path $archiveRoot "freeze.tar") -C $archiveTree
if (Test-Path -LiteralPath (Join-Path $archiveTree ".git")) { throw 'source archive contains .git' }
$archiveIndexPath = Join-Path $archiveTree 'evidence/public/v02/search/evidence-index.json'
$archiveIndexSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $archiveIndexPath).Hash.ToLowerInvariant()
if ($archiveIndexSha -ne $retainedIndexSha) { throw 'archive index differs from retained anchor' }
uv run python -m mdcp.temporal.cli verify-search-source --root $archiveTree --index $archiveIndexPath --expected-index-sha256 $retainedIndexSha
if ($LASTEXITCODE -ne 0) { throw 'source archive identity failed' }
```

Expected stdout: exactly `SEARCH_SOURCE_INVENTORY_PASS`. Verify the resolved cleanup target remains
inside the OS temporary directory and its leaf starts with `mdcp-w3-seal-freeze-`; only then remove
that invocation-owned temporary root.

- [ ] **Step 8: Run final completion gates and whole-range independent review**

From committed freeze HEAD, rerun Step 3 full tests/Ruff/lock/diff/scans, Task 4 and Task 5 focused
suites, freeze verifier, actual no-`.git` proof, custody-byte check, protected identities, and H2
behavioral firewall. Verify `HEAD^` is the receipt's `SEARCH_SOURCE_COMMIT`, HEAD is its direct
child, and `git diff --name-only HEAD^ HEAD` is exactly the two freeze files.

Obtain independent read-only review of the complete range from the plan-entry commit through freeze
HEAD. Require Critical `0`, Important `0`. Confirm clean worktree, remote `0`, no HEAD tag, H2 loaded
rows `0`, no UCI/H1/H2/model/Docker/GPU/network/remote activity, no real authorization, no formal
command execution, P2 required, and Wave 4 not started.

Stop with exactly:

```text
SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED / H2_SEALED_NOT_LOADED
```

## Completion Evidence

The final report records:

- approved design and approval commits plus final design SHA-256;
- this plan commit/SHA-256 and independent plan review counts;
- immutable Task 2R/3 and new Task 4–7 commit SHAs with exact changed-file inventories;
- every observed RED and GREEN command/result;
- exact callable surface, marker matrix, outcome matrix, recovery truth table, EXIT digest, and
  custody-output results;
- synthetic 80/84/85, one-process/session/ledger/replay, public-boundary, and H2-denial proof;
- exact 43-path source and five logical private-output identities;
- `SEARCH_SOURCE_COMMIT`, `SEARCH_FREEZE_COMMIT`, receipt/index/custody SHA-256, direct-child, and
  no-`.git` proof;
- full CPU/security/publication/credential/protected-byte and independent review results; and
- final branch/HEAD/clean/remote/tag/H2 state, P2 required, Wave 4 not started.

Any blocked outcome preserves the last clean checkpoint and reports:

```text
W3_FORMAL_SEAL_CLOSURE_BLOCKED / P2_FORBIDDEN / H2_SEALED_NOT_LOADED
```
