# MDCP v0.2 Wave 3 Final-Review Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The shared Git/evidence topology is strictly serial; do not parallelize implementation tasks.

**Goal:** Close the final formal-seal authority, publication, recovery, CLI, and firewall findings; establish a corrected 43-path source identity; retire the rejected current-tree freeze recoverably; and create one new no-clobber receipt-only freeze without executing P2.

**Architecture:** The natural 80+4 engine becomes closure-local to the sole authorized formal operation, while module state retains only non-authoritative records and pure transformations. Formal outputs are preflighted outside the repository, recovery recomputes one semantic five-file chain, and the unchanged add-only freeze verifier is satisfied through an append-only `D/D` tombstone source commit followed immediately by an `A/A` freeze child.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Ruff, uv, RFC 8785 canonical JSON, SHA-256, Git, Windows retained-handle publication, PowerShell 7.

## Global Constraints

- Execute only in the Git-registered worktree whose branch is
  `codex/wave0-foundation-feasibility` and whose HEAD is the exact commit that adds this plan. The
  owner execution authorization must name that commit; the plan cannot contain its own commit hash.
- The approved final-review corrective spec is
  `docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md`, approved
  at `c5bca04e9ac5c129ce0770684d2eae0863ee1784`, physical SHA-256
  `edc498a4ff5cc6110fb546a4f8f0fae7c6531c67925768892cbd5f386c2ae111`.
- The approved topology amendment is
  `docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md`, approved at
  `c632eafff4bebb707ac1fdec29ac5165c628a929`, physical SHA-256
  `240852dabf6d541db4cac9b2f9ac771cb74c75c96132813c573b69a31105d541`.
- Work strictly serially: Task 1 -> 2 -> 3 -> 4 -> 5 -> 6A -> 6B -> 7 -> completion review.
- Use test-driven-development for every production correction, systematic-debugging for every
  unexpected failure, receiving-code-review for every finding, requesting-code-review at each task
  boundary, and verification-before-completion before every commit and final claim.
- Each RED must be observed against the current implementation and fail for the stated missing
  contract. Never weaken an assertion or bless an existing authority surface to manufacture GREEN.
- Every implementation commit is append-only and uses
  `kuotunyu <61350295+kuotunyu@users.noreply.github.com>` for author and committer. Do not amend,
  reset, restore, rebase, squash, cherry-pick, stash, rewrite history, merge, create a remote, push,
  tag, or Release.
- Keep exactly four folds, 20 trials, 19 eligible candidates, 80 selection fits, at most four replay
  fits, at most one final fit, and maximum 85 fits. Do not change any threshold, protocol, feature,
  schema family, dependency, or platform claim.
- H2 remains `SEALED_NOT_LOADED`, loaded rows `0`. Do not read UCI, H1, or H2 rows; create or consume
  a real formal authorization; run `run-development`; fit or infer a model; run ONNX, MLflow,
  Docker, GPU, or network operations; or start P2/Wave 4.
- Tests use deterministic generated objects and OS temporary roots only. Any fixture labeled
  `natural_development` is adversarial structure, never natural evidence.
- Preserve all v0.1/v0.2 serving identities, Wave 0-2 evidence, dependency lock, approved protocol,
  historical commits, and external custody. The only destructive action is Task 6B's explicitly
  approved, recoverable deletion of the two rejected current-tree search evidence leaves.
- Stop if a required change is outside the exact 19-path allowlist, a protected blob drifts, an
  evidence/custody identity differs, a task needs natural execution, one blocker survives three
  evidenced hypotheses, or any Critical/Important review finding remains.
- Task 6B and Task 7 are an indivisible operational sequence. After Task 6B, do no unrelated work.
  If Task 7 cannot complete exactly, stop at the clean tombstone source commit with P2 forbidden.

---

## Approved identities and rejected-freeze baseline

- Rejected freeze commit:
  `2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598`.
- Rejected receipt SHA-256:
  `7bf1f01f5883c563639152b8eda6fbff8ab1171c85a5865e21ee0303afdbdc94`.
- Rejected evidence-index SHA-256:
  `ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d`.
- Rejected external custody SHA-256:
  `38fc225f45fc2a282be339c8d6974154bd90a94af93132ed2132ca5c9b04bf9f`.
- Rejected external custody leaf:
  `D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d.search-source-custody.json`.
- Rejected receipt path:
  `evidence/public/v02/search/search-receipt.json`.
- Rejected index path:
  `evidence/public/v02/search/evidence-index.json`.
- v0.1 serving identity:
  `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`.
- v0.2 serving identity:
  `afa14abec0951a117ce1bd729bbd04fd3d645cf530022257df209559af85d7d1`.
- Dependency lock SHA-256:
  `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`.

## Exact 19-path implementation allowlist

Only these paths may change after the plan entry commit:

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

The last two paths remain byte-for-byte unchanged through Task 6A. Task 6B deletes exactly those two
paths. Task 7 recreates exactly those two paths. A new source, test, schema, fixture, attributes,
configuration, or evidence path requires an owner stop.

## File responsibility map

- `run_evidence.py`: closure-owned formal operation, retained publication, private encoding,
  terminal seal, and read-only semantic recovery.
- `runner.py`: non-authoritative records and pure transformations only; no callback-taking or
  natural-capable formal execution surface.
- `cli.py`: exact five-command parser and sole dispatcher; only `build_parser` and `main` are named
  callables.
- `firewall.py`: static capability policy, post-import reachability proof, exact CLI dispatch edge,
  file/environment/Git/H2 denial.
- `search_identity.py`: exact 43-path inventory, canonical receipt/index production, source/freeze
  verification.
- `runtime_guards.py`: unchanged lifecycle contract unless a Task 1 RED proves a narrowly required
  allowlisted correction.
- `development-result-index.schema.json` and `formal-run-authorization.schema.json`: unchanged
  unless Task 3 proves an existing model/schema inconsistency; do not add a schema family.
- Task 1 tests: closure-local authority and synthetic 80+4 engine.
- Task 2 tests: paired destination and checked-close matrix.
- Task 3 tests: five-file semantic recovery.
- Task 4 tests: exact CLI surface and sanitized output.
- Task 5 tests: cross-module static/dynamic capability proof.
- Task 6 tests: exact 43-path source inventory and no-`.git` archive.
- Task 7 evidence: the sole terminal receipt/index pair.

## Entry preflight

- [ ] **Step 1: Locate the unique registered worktree**

Run from the repository root:

```powershell
git worktree list --porcelain
```

Select the unique worktree whose branch is `refs/heads/codex/wave0-foundation-feasibility` and whose
HEAD equals the owner-authorized plan commit. Stop if there is no unique match. Use Git's exact
registered path for every later command.

- [ ] **Step 2: Verify Git and immutable entry state**

```powershell
$planEntry = (git rev-parse HEAD).Trim()
git branch --show-current
git status --porcelain=v1
git remote
git tag --points-at HEAD
git log -1 --format='%an <%ae>|%cn <%ce>|%H'
```

Expected: exact branch, owner-named plan entry, empty status, zero remotes, zero HEAD tags, official
identity.

- [ ] **Step 3: Verify rejected evidence and custody identities without writing**

```powershell
$receipt = 'evidence/public/v02/search/search-receipt.json'
$index = 'evidence/public/v02/search/evidence-index.json'
$custody = 'D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d.search-source-custody.json'
(Get-FileHash -Algorithm SHA256 -LiteralPath $receipt).Hash.ToLowerInvariant()
(Get-FileHash -Algorithm SHA256 -LiteralPath $index).Hash.ToLowerInvariant()
(Get-FileHash -Algorithm SHA256 -LiteralPath $custody).Hash.ToLowerInvariant()
git ls-tree 2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598 -- $receipt $index
uv run python -c "import hashlib,subprocess; paths=['evidence/public/v02/search/search-receipt.json','evidence/public/v02/search/evidence-index.json']; print(*[hashlib.sha256(subprocess.check_output(['git','cat-file','blob','2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598:'+p])).hexdigest() for p in paths],sep='\n')"
```

Expected: the exact three SHA-256 values above; both historical leaves mode `100644`; historical blob
SHA-256 values equal the working-tree receipt/index identities.

- [ ] **Step 4: Freeze protected bytes and H2 state**

```powershell
$allowlist = @(
'src/mdcp/temporal/runner.py','src/mdcp/temporal/cli.py','src/mdcp/temporal/runtime_guards.py','src/mdcp/temporal/run_evidence.py','src/mdcp/temporal/firewall.py','src/mdcp/temporal/search_identity.py','schemas/v2/development-result-index.schema.json','schemas/v2/formal-run-authorization.schema.json','tests/unit/temporal/test_fit_ledger.py','tests/unit/temporal/test_runtime_guards.py','tests/unit/temporal/test_run_evidence.py','tests/integration/temporal/test_formal_runner_synthetic.py','tests/integration/temporal/test_search_freeze_preflight.py','tests/security/temporal/test_data_firewall.py','tests/security/temporal/test_formal_runner_firewall.py','tests/security/temporal/test_formal_run_authorization.py','tests/security/temporal/test_public_evidence_boundary.py','evidence/public/v02/search/search-receipt.json','evidence/public/v02/search/evidence-index.json'
)
$protected = @{}
foreach ($path in @(git ls-tree -r --name-only $planEntry)) {
  if ($path -notin $allowlist) { $protected[$path] = (git rev-parse "$planEntry`:$path").Trim() }
}
$oldReceipt = Get-Content -Raw -LiteralPath 'evidence/public/v02/search/search-receipt.json' | ConvertFrom-Json
$oldIndex = Get-Content -Raw -LiteralPath 'evidence/public/v02/search/evidence-index.json' | ConvertFrom-Json
if ($oldReceipt.h2_status -ne 'SEALED_NOT_LOADED' -or $oldReceipt.h2_loaded_rows -ne 0) { throw 'H2 invariant failed' }
if ($oldIndex.h2_status -ne 'SEALED_NOT_LOADED' -or $oldIndex.h2_loaded_rows -ne 0) { throw 'H2 invariant failed' }
```

Retain `$planEntry`, `$allowlist`, and `$protected` in the controller session. Do not serialize a
private absolute path into public evidence.

---

### Task 1: Remove module-reachable formal execution authority

**Files:**
- Modify: `src/mdcp/temporal/runner.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: existing `execute_authorized_formal_development`, deleted bootstrap factory pattern,
  `FitLedger`, `DevelopmentRunBundle`, runtime guard, frozen fold/trial inventory.
- Produces: the same `execute_authorized_formal_development(request) -> FormalDevelopmentOutcome`,
  with natural loader/model/core objects reachable only through its closure; an AST-isolated
  synthetic harness for 80+4 verification.

- [ ] **Step 1: Add exact RED authority tests**

Add tests equivalent to:

```python
@dataclass(slots=True)
class SyntheticProbe:
    selection_fit_count: int = 0
    replay_fit_count: int = 0
    uci_rows: int = 0

FORBIDDEN_RUNNER_NAMES = {
    "_FormalDevelopmentInputs",
    "_DevelopmentRunState",
    "_DevelopmentExecutionPlan",
    "_checkpoint",
    "_execute_fit",
    "_run_development_core",
    "_build_formal_execution_plan",
    "_load_formal_execution_state",
    "_fit_formal_fold",
}

def test_runner_exposes_no_module_reachable_execution_authority() -> None:
    assert FORBIDDEN_RUNNER_NAMES.isdisjoint(vars(runner))

def test_named_reachability_rejects_callback_loader_and_fit_capabilities() -> None:
    report = inspect_owned_formal_surface()
    assert report.forbidden_paths == ()

def test_isolated_factory_executes_exact_synthetic_80_plus_4() -> None:
    operation, probe = isolated_factory_operation_with_generated_bindings()
    outcome = operation(synthetic_formal_request())
    assert probe.selection_fit_count == 80
    assert probe.replay_fit_count in {0, 4}
    assert outcome.fit_count in {80, 84}
    assert probe.uci_rows == 0
```

The isolated helper lives in the existing test file. It parses the production bootstrap factory AST,
injects deterministic generated module bindings, and exposes the nested core only in that isolated
namespace. It must not monkeypatch the imported production module.

For the test-only extraction, deep-copy the factory `FunctionDef`, replace its final `Return` with a
tuple containing the two production wrappers plus `_run_development_core` and
`_DevelopmentExecutionPlan`, compile that copied AST under a synthetic module name, and discard the
namespace after each test. Assert the imported production module still lacks those two private
objects before and after extraction.

Replace every existing test call to `runner._run_development_core` and construction of
`runner._DevelopmentExecutionPlan` with this isolated-factory harness. Preserve each existing
assertion for replay selection, changed digests, contract failure, checkpoint order, concurrency,
single consumption, private-data exclusion, and the 85th-fit denial.

- [ ] **Step 2: Observe RED**

```powershell
uv run pytest -q tests/security/temporal/test_formal_runner_firewall.py -k "module_reachable or callback_loader"
uv run pytest -q tests/integration/temporal/test_formal_runner_synthetic.py -k "isolated_factory_executes"
```

Expected: the first command fails because the listed runner objects exist. The second fails because
the isolated factory does not yet own the one-shot core.

- [ ] **Step 3: Move the capability, not just the names**

In `runner.py`, remove every module-level type/function that accepts a fit callback or can import,
load, construct, or fit natural state. Keep only non-authoritative records and pure transformations.

Add `dataclasses.field` to the consumed-and-deleted mutation binding tuple as `closure_field`. In the
deleted bootstrap factory in `run_evidence.py`, define the formal state and engine locally:

```python
def _make_evidence_mutation_surface():
    @closure_dataclass(frozen=True, slots=True)
    class FormalInputs:
        repository_root: ClosurePath
        expected_freeze_head: str
        archive_path: ClosurePath
        archive_sha256: str
        search_receipt_sha256: str
        protocol_sha256: str

    @closure_dataclass(slots=True)
    class _DevelopmentRunState:
        lock: ClosureLock = closure_field(default_factory=ClosureLock)
        consumed: bool = False

    @closure_dataclass(frozen=True, slots=True)
    class _DevelopmentExecutionPlan:
        fit_fold: object
        state: _DevelopmentRunState = closure_field(default_factory=_DevelopmentRunState, init=False)

    def _load_formal_execution_state(inputs: FormalInputs, protocol: object, state: dict[str, object]) -> None:
        from mdcp.temporal.folds import load_fold_specs, materialize_folds
        from mdcp.temporal.trials import load_trial_specs
        from mdcp.workload.dataset import load_uci_development_archive
        from mdcp.workload.splits import split_development_rows
        if not isinstance(protocol, dict):
            raise DevelopmentRunError("PROTOCOL_INVALID")
        rows = load_uci_development_archive(inputs.archive_path, inputs.archive_sha256)
        partitions = split_development_rows(rows)
        folds = materialize_folds(partitions, load_fold_specs(protocol))
        trials = load_trial_specs(protocol)
        if tuple(f.spec.fold_id for f in folds) != EXACT_FOLD_IDS or tuple(t.trial_id for t in trials) != EXACT_TRIAL_IDS:
            raise DevelopmentRunError("FORMAL_INVENTORY_INVALID")
        state.update({"folds": {f.spec.fold_id: f for f in folds}, "trials": {t.trial_id: t for t in trials}})

    def _fit_formal_fold(state: dict[str, object], phase: FitPhase, trial_id: str, fold_id: str) -> _DevelopmentFoldResult:
        from mdcp.temporal.trials import _feature_names, _materialize_features, build_estimator, training_rows_for_trial
        # Relocate the existing feature materialization, estimator fit, prediction, label,
        # subgroup, digest, and typed-result statements without changing their order or preimages.

    def _build_formal_execution_plan(inputs: FormalInputs) -> _DevelopmentExecutionPlan:
        protocol_bytes = (inputs.repository_root / "configs/workload/temporal-development-v2.json").read_bytes()
        if closure_sha256_hex(protocol_bytes) != inputs.protocol_sha256:
            raise DevelopmentRunError("PROTOCOL_IDENTITY_MISMATCH")
        protocol = closure_parse_json_bytes(protocol_bytes)
        loaded: dict[str, object] = {}
        def fit_fold(phase: FitPhase, trial_id: str, fold_id: str) -> object:
            if not loaded:
                _load_formal_execution_state(inputs, protocol, loaded)
            return _fit_formal_fold(loaded, phase, trial_id, fold_id)
        return _DevelopmentExecutionPlan(fit_fold=fit_fold)

    def _run_development_core(plan: _DevelopmentExecutionPlan, guard: RuntimeGuard, *, defer_final_checkpoints: bool = False) -> DevelopmentRunBundle:
        # Relocate the existing one-shot 80+4 body without changing fit order, budget,
        # ranking, replay, digest, checkpoint, or exception behavior.

    def execute_authorized_formal_development(request: FormalDevelopmentRequest) -> FormalDevelopmentOutcome:
        # Authorization/freeze/destination/marker validation remains before run_closed_core.
        result = _run_development_core(_build_formal_execution_plan(inputs), guard, defer_final_checkpoints=True)
        # Keep the existing formalize, private-first publication, EXIT, terminal-seal, and outcome code here.

    return write_synthetic_bundle_no_clobber, execute_authorized_formal_development

write_synthetic_bundle_no_clobber, execute_authorized_formal_development = _make_evidence_mutation_surface()
del _make_evidence_mutation_surface
del _MUTATION_BINDINGS
```

Relocate the complete existing bodies of `_fit_formal_fold`, `_build_formal_execution_plan`, and
`_run_development_core`, plus their callback-taking helper state, into the factory; the abbreviated
comments above mark those exact bodies and are not new abstraction seams. Preserve the existing
exception mapping, guard order, ranking rule, digest material, ledger, replay session, and fit limits.

Update firewall allowlists to remove the old runner capability names. Do not add replacement names
to module allowlists.

- [ ] **Step 4: Run Task 1 GREEN**

```powershell
uv run pytest -q tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py
uv run ruff check src/mdcp/temporal/runner.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py
git diff --check
```

Expected: all pass; the synthetic matrix proves 80/84/85, one ledger/session, zero UCI rows, and no
module-reachable natural capability.

- [ ] **Step 5: Review and commit Task 1**

Obtain independent read-only review of the Task 1 diff. Require Critical `0`, Important `0`.

```powershell
git add src/mdcp/temporal/runner.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py
git commit -m "security: close module-reachable formal execution"
```

---

### Task 2: Bind paired output outside the repository and check every close

**Files:**
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `tests/unit/temporal/test_run_evidence.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`

**Interfaces:**
- Consumes: closure-local `_safe_external_directory`, `preflight_pair`, retained destinations,
  marker matrix, existing fixed failure outcomes.
- Produces: pre-consumption proof that both output leaves are outside the repository and a complete
  checked-close verdict matrix.

- [ ] **Step 1: Add RED external-boundary and close tests**

```python
def test_ignored_repository_destination_fails_before_marker_and_loader(tmp_path: Path) -> None:
    repository = initialized_clean_repository(tmp_path)
    private = repository / "runtime" / "formal.json"
    private.parent.mkdir()
    outcome, calls = isolated_formal_operation(private_container_path=private)
    assert (outcome.verdict, outcome.reason_codes) == ("FAIL", ("FORMAL_RUN_DESTINATION_INVALID",))
    assert calls.marker == calls.loader == calls.fit == 0

@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("preflight", ("FAIL", "FORMAL_RUN_DESTINATION_INVALID")),
        ("marker_owned", ("UNKNOWN", "FORMAL_RUN_CONSUMPTION_UNKNOWN")),
        ("private_publish", ("UNKNOWN", "FORMAL_RUN_EXECUTION_UNKNOWN")),
        ("terminal_publish", ("UNKNOWN", "FORMAL_RUN_SEAL_UNKNOWN")),
    ],
)
def test_each_checked_close_failure_is_consumed(phase: str, expected: tuple[str, str]) -> None:
    outcome = isolated_close_failure(phase)
    assert (outcome.verdict, outcome.reason_codes[0]) == expected
```

Do not add a new publication reason; `FORMAL_RUN_EXECUTION_UNKNOWN` is the existing fixed reason for
private-publication failure before the terminal seal phase.

- [ ] **Step 2: Observe RED**

```powershell
uv run pytest -q tests/security/temporal/test_formal_run_authorization.py -k "ignored_repository_destination"
uv run pytest -q tests/unit/temporal/test_run_evidence.py -k "checked_close_failure"
```

Expected: repository destination reaches pair preflight instead of failing externally; at least one
close-failure row is ignored.

- [ ] **Step 3: Implement the exact boundary**

Before `preflight_pair`:

```python
private_parent = request.private_container_path.parent
if not _safe_external_directory(request.consumption_root, repository):
    return _outcome("FAIL", "FORMAL_RUN_CONSUMPTION_ROOT_INVALID", authorization_sha256=authorization_sha256)
if not _safe_external_directory(private_parent, repository):
    return _outcome("FAIL", "FORMAL_RUN_DESTINATION_INVALID", authorization_sha256=authorization_sha256)
pair = preflight_pair(request.private_container_path)
```

Consume every close result:

```python
if not close_destination(private):
    raise _PublicationError("PUBLICATION_FAILED")

if owned is not None and not _windows_close(owned):
    return marker_unknown("FORMAL_RUN_CONSUMPTION_UNKNOWN")

if not close_pair(pair):
    return publication_unknown(current_phase)
```

Do not delete by path, retry after owned/possibly-owned marker state, or echo OS status. Preserve the
sole approved no-handle/proven-absent pre-create retry row.

- [ ] **Step 4: Run Task 2 GREEN**

```powershell
uv run pytest -q tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
uv run pytest -q tests/security/temporal/test_public_evidence_boundary.py
uv run ruff check src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
uv run ruff format --check src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
git diff --check
```

- [ ] **Step 5: Review and commit Task 2**

Require independent Critical `0`, Important `0`.

```powershell
git add src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
git commit -m "security: bind formal outputs outside repository"
```

---

### Task 3: Close the five-file semantic recovery chain

**Files:**
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `tests/unit/temporal/test_run_evidence.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify only if a model/schema mismatch is proven: `schemas/v2/development-result-index.schema.json`

**Interfaces:**
- Consumes: `_valid_natural_container`, canonical five-file decoder, external expected seal digest,
  exact fold/trial IDs and ranking rule.
- Produces: recovery PASS only for one semantically closed qualification/winner/ranking/summary/replay
  chain.

- [ ] **Step 1: Replace the permissive fixture and add coordinated RED mutations**

Build one internally consistent fixture: every fold document and corresponding digest object uses
the same configuration, preprocessing, feature, prediction, metric, and receipt identities.

```python
def test_recovery_rejects_winner_not_equal_to_selected_qualification() -> None:
    chain = valid_anchored_five_file_chain()
    chain.provisional_winner["configuration_sha256"] = B
    chain.rehash_all_container_layers()
    assert verify_chain(chain).verdict == "FAIL"

def test_recovery_rejects_replay_document_digest_divergence() -> None:
    chain = valid_anchored_five_file_chain()
    chain.replay_folds[0]["prediction_vector_sha256"] = B
    chain.rehash_all_container_layers()
    assert verify_chain(chain).verdict == "FAIL"

def test_coordinated_five_file_rehash_still_requires_one_semantic_chain() -> None:
    chain = valid_anchored_five_file_chain()
    chain.coordinate_superficial_rehash_with_inconsistent_winner_and_replay()
    assert verify_chain(chain).verdict == "FAIL"
```

Keep a separate test proving that coordinated terminal-byte mutation fails against the unchanged
external `expected_seal_record_sha256`.

- [ ] **Step 2: Observe RED**

```powershell
uv run pytest -q tests/security/temporal/test_formal_run_authorization.py -k "winner_not_equal or replay_document_digest or coordinated_five_file"
```

Expected: at least the replay/document and inconsistent chain cases incorrectly return PASS.

- [ ] **Step 3: Recompute semantic relationships**

Keep new helpers nested inside `_valid_natural_container` so no new module attribute appears:

```python
def fold_digest_from_document(document: dict[str, object], *, replay: bool) -> dict[str, object]:
    digest = {
        "fold_id": document["fold_id"],
        "configuration_sha256": document["configuration_sha256"],
        "preprocessing_state_sha256": document["preprocessing_state_sha256"],
        "feature_vector_sha256": document["feature_vector_sha256"],
        "prediction_vector_sha256": document["prediction_vector_sha256"],
        "metric_sha256": document["metric_sha256"],
        "receipt_sha256": document["receipt_sha256"],
    }
    if replay:
        digest["verdict"] = document["contract_verdict"]
    return digest

winner = unique_selected_qualification(qualification, ranking)
if provisional != winner_projection(winner, qualification_inventory_sha256):
    return False
for document, declared in zip(replay_folds, replay_digests, strict=True):
    if fold_digest_from_document(document, replay=True) != declared:
        return False
```

Recompute ranking order from the approved ranking key, require exact 20-trial summary and 19 eligible
qualification inventory, and cross-bind selection status, reason codes, winner, replay target,
fit count, private identity, and terminal seal. Do not trust an independently supplied digest when
its preimage is available in the container.

- [ ] **Step 4: Run Task 3 GREEN**

```powershell
uv run pytest -q tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
uv run pytest -q tests/security/temporal/test_public_evidence_boundary.py
uv run ruff check src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
uv run ruff format --check src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
git diff --check
```

- [ ] **Step 5: Review and commit Task 3**

Require independent Critical `0`, Important `0`.

```powershell
git add src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/security/temporal/test_formal_run_authorization.py
if (git diff --name-only -- schemas/v2/development-result-index.schema.json) { git add schemas/v2/development-result-index.schema.json }
git commit -m "security: bind formal recovery semantics"
```

---

### Task 4: Restore the exact CLI callable surface

**Files:**
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: existing five commands, fixed canonical output documents, exit-code mapping.
- Produces: `cli.py` named callable surface exactly `build_parser`, `main`; one dispatch edge from
  `main` to `execute_authorized_formal_development`.

- [ ] **Step 1: Add the RED exact-surface assertion**

```python
def test_final_cli_named_callable_surface_is_exact() -> None:
    names = tuple(sorted(name for name, value in vars(cli).items() if inspect.isfunction(value) and value.__module__ == cli.__name__))
    assert names == ("build_parser", "main")
```

Keep the existing exact five-command assertion and write/flush failure tests.

- [ ] **Step 2: Observe RED**

```powershell
uv run pytest -q tests/security/temporal/test_formal_run_authorization.py -k "named_callable_surface"
```

Expected: `_emit_check` is an extra callable.

- [ ] **Step 3: Inline fixed emission inside `main`**

Delete `_emit_check`. Inside `main`, use a local closure or direct branch:

```python
def main(arguments: Sequence[str] | None = None) -> int:
    # parse and dispatch unchanged
    document = {"reason_code": reason_code, "schema_version": schema_version, "verdict": verdict}
    try:
        sys.stdout.buffer.write(canonicalize_json(document) + b"\n")
        sys.stdout.buffer.flush()
    except Exception:
        return 4
    return 0 if verdict == "PASS" else 2 if verdict == "FAIL" else 3
```

Update firewall file-access/callable inventories to remove `_emit_check`; do not add an equivalent
module helper or command handler.

- [ ] **Step 4: Run Task 4 GREEN**

```powershell
uv run pytest -q tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run ruff check src/mdcp/temporal/cli.py src/mdcp/temporal/firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/cli.py src/mdcp/temporal/firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git diff --check
```

- [ ] **Step 5: Review and commit Task 4**

Require independent Critical `0`, Important `0`.

```powershell
git add src/mdcp/temporal/cli.py src/mdcp/temporal/firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "security: close formal cli surface"
```

---

### Task 5: Prove the final cross-module capability boundary

**Files:**
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`

**Interfaces:**
- Consumes: corrected Tasks 1-4 module surfaces.
- Produces: static and post-import proof that spelling changes, aliases, defaults, registries,
  classes, returned objects, and callback indirection cannot reintroduce formal authority.

- [ ] **Step 1: Add adversarial RED source mutations**

```python
@pytest.mark.parametrize("mutation", ["renamed_callback", "aliased_loader", "class_registry", "default_bound_fit"])
def test_static_firewall_rejects_capability_equivalent_runner_mutation(tmp_path: Path, mutation: str) -> None:
    source = mutate_runner_source(committed_runner_source(), mutation)
    path = tmp_path / "runner.py"
    path.write_text(source, encoding="utf-8")
    assert inspect_temporal_source(path).reason_code == "H2_IMPORT_CAPABILITY_FORBIDDEN"

def test_post_import_surface_has_only_one_formal_mutation_edge() -> None:
    graph = inspect_owned_formal_surface()
    assert graph.formal_mutation_edges == (("mdcp.temporal.cli.main", "mdcp.temporal.run_evidence.execute_authorized_formal_development"),)
```

Mutation fixtures are source strings in the existing test file. They do not import or execute
natural loaders.

- [ ] **Step 2: Observe RED**

```powershell
uv run pytest -q tests/security/temporal/test_formal_runner_firewall.py -k "capability_equivalent or one_formal_mutation_edge"
uv run pytest -q tests/security/temporal/test_data_firewall.py -k "runner"
```

Expected: at least one capability-equivalent renamed callback/import is not rejected by the current
static rules.

- [ ] **Step 3: Enforce structural capability rules**

Update `firewall.py` so runner source fails closed when it contains:

```python
FORBIDDEN_RUNNER_IMPORTS = {
    ("mdcp.workload.dataset", "load_uci_development_archive"),
    ("mdcp.workload.splits", "split_development_rows"),
    ("mdcp.temporal.trials", "build_estimator"),
}
```

Also reject runner functions that invoke a parameter/default/attribute as an execution callback,
and require natural imports to occur only inside the deleted `run_evidence.py` bootstrap factory.
Keep exact callable inventories for the four protected modules, but do not rely on normalized names
as the only defense. Preserve the static H2 denial of legacy loader, `split_rows`,
`DatasetPartitions.open_h2`, dynamic import, environment recovery, file recovery, and alias forms.

- [ ] **Step 4: Run Task 5 GREEN and full CPU regression**

```powershell
uv run pytest -q tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_data_firewall.py tests/integration/temporal/test_formal_runner_synthetic.py
uv run pytest -q
uv run ruff check src/mdcp/temporal tests/unit/temporal tests/integration/temporal tests/security/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv lock --check
git diff --check
```

- [ ] **Step 5: Independent whole-boundary review and commit Task 5**

Review Tasks 1-5 together from their common parent. Require Critical `0`, Important `0`.

```powershell
git add src/mdcp/temporal/firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_data_firewall.py tests/integration/temporal/test_formal_runner_synthetic.py
git commit -m "test: prove final formal capability boundary"
```

---

### Task 6A: Bind the corrected exact 43-path source identity

**Files:**
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `tests/integration/temporal/test_search_freeze_preflight.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: corrected committed source, approved final-review and topology specs, this plan.
- Produces: exact ASCII-ordered 43-path inventory with a three-for-three normative substitution and
  byte-identical no-`.git` archive proof.

- [ ] **Step 1: Add RED exact-inventory assertions**

Replace the three superseded paths in the independent test constant and assert:

```python
assert len(EXACT_SEARCH_SOURCE_PATHS) == 43
assert tuple(sorted(EXACT_SEARCH_SOURCE_PATHS)) == EXACT_SEARCH_SOURCE_PATHS
assert "docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-final-review-corrective.md" in EXACT_SEARCH_SOURCE_PATHS
assert "docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md" in EXACT_SEARCH_SOURCE_PATHS
assert "docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md" in EXACT_SEARCH_SOURCE_PATHS
assert "docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-formal-seal-closure-corrective.md" not in EXACT_SEARCH_SOURCE_PATHS
assert "docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md" not in EXACT_SEARCH_SOURCE_PATHS
assert "docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-closure-design.md" not in EXACT_SEARCH_SOURCE_PATHS
assert SEARCH_SOURCE_PATHS == EXACT_SEARCH_SOURCE_PATHS
```

Add missing/extra/duplicate/substitution negative cases for each of the three new normative paths.

- [ ] **Step 2: Observe RED**

```powershell
uv run pytest -q tests/integration/temporal/test_search_freeze_preflight.py -k "exact_ascii_ordered_43 or required_document_omission or unknown_path_substitution"
```

Expected: production inventory still names the superseded documents and omits the three approved
current documents.

- [ ] **Step 3: Apply the exact three-for-three production substitution**

In `SEARCH_SOURCE_PATHS`, remove exactly:

```text
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-formal-seal-closure-corrective.md
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-closure-design.md
```

Add exactly, in ASCII order:

```text
docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-final-review-corrective.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md
docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md
```

Keep inventory length 43. Do not alter historical files or add evidence paths to source inventory.

- [ ] **Step 4: Prove mixed-EOL archive behavior in temporary fixtures**

The external attributes profile content is exact:

```text
* text eol=lf
src/mdcp/temporal/firewall.py text eol=crlf
src/mdcp/temporal/run_evidence.py text eol=crlf
src/mdcp/temporal/runner.py text eol=crlf
src/mdcp/temporal/search_identity.py text eol=crlf
```

Add/retain tests that archive a temporary committed fixture under `core.autocrlf=true`, `false`, and
`input`, extract without `.git`, and require identical tar SHA-256 plus 43/43 verifier equality. The
profile is created under the OS temporary root; no tracked `.gitattributes` changes.

- [ ] **Step 5: Run Task 6A GREEN**

```powershell
uv run pytest -q tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run pytest -q
uv run ruff check src/mdcp/temporal/search_identity.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/search_identity.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv lock --check
git diff --check
```

- [ ] **Step 6: Review and commit Task 6A**

Require independent Critical `0`, Important `0`.

```powershell
git add src/mdcp/temporal/search_identity.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
git commit -m "feat: bind final formal seal source"
```

This is not yet `SEARCH_SOURCE_COMMIT` because the rejected evidence leaves remain tracked.

---

### Task 6B: Retire the rejected current-tree freeze and establish `SEARCH_SOURCE_COMMIT`

**Files:**
- Delete from current tree: `evidence/public/v02/search/search-receipt.json`
- Delete from current tree: `evidence/public/v02/search/evidence-index.json`

**Interfaces:**
- Consumes: Task 6A committed source, exact rejected Git blobs and external custody.
- Produces: a clean source commit where both canonical freeze leaves are absent and recoverable from
  `2cb2f0b`; this commit is the new `SEARCH_SOURCE_COMMIT`.

- [ ] **Step 1: Repeat the destructive-action preflight**

Run the Entry Step 3 identity commands again. Also require:

```powershell
git status --porcelain=v1
git ls-files --stage -- evidence/public/v02/search/search-receipt.json evidence/public/v02/search/evidence-index.json
git diff --name-only $planEntry..HEAD --
```

Expected: clean; both evidence leaves mode `100644`; all changes since plan entry remain inside the
19-path allowlist; current receipt/index/custody identities equal the rejected baseline.

- [ ] **Step 2: Obtain pre-deletion independent review**

The reviewer verifies Task 6A, the exact two deletion targets, historical recoverability, custody,
and the planned `D/D -> A/A` topology. Require Critical `0`, Important `0` before deletion.

- [ ] **Step 3: Delete exactly the two current-tree leaves with `apply_patch`**

Use one patch containing only:

```text
*** Delete File: evidence/public/v02/search/search-receipt.json
*** Delete File: evidence/public/v02/search/evidence-index.json
```

Do not delete the directory, custody, historical commit, or any other file.

- [ ] **Step 4: Verify the staged destructive scope before commit**

```powershell
git status --short --untracked-files=all
git diff --name-status
git diff --check
```

Expected exactly:

```text
D evidence/public/v02/search/evidence-index.json
D evidence/public/v02/search/search-receipt.json
```

Stage only those deletions and recheck the cached diff:

```powershell
git add -u -- evidence/public/v02/search/evidence-index.json evidence/public/v02/search/search-receipt.json
git diff --cached --name-status
git diff --cached --check
```

Obtain a second independent read-only review of the actual staged `D/D` diff and the repeated hash
evidence. Require Critical `0`, Important `0` before committing.

- [ ] **Step 5: Commit the tombstone**

```powershell
git commit -m "evidence: retire rejected temporal search freeze"
$searchSourceCommit = (git rev-parse HEAD).Trim()
```

Report immediately that the two current-tree leaves were removed and remain recoverable from
`2cb2f0b` and the unchanged external custody.

- [ ] **Step 6: Verify the clean missing-freeze source state**

```powershell
git status --porcelain=v1
git diff-tree --no-commit-id --name-status -r HEAD
Test-Path -LiteralPath 'evidence/public/v02/search/search-receipt.json'
Test-Path -LiteralPath 'evidence/public/v02/search/evidence-index.json'
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
```

Expected: clean; exactly two `D` entries in HEAD; both `Test-Path` values false; verifier emits the
fixed missing-receipt failure. Do not run unrelated commands after this point.

---

### Task 7: Create and freeze the corrected receipt/index pair

**Files:**
- Create: `evidence/public/v02/search/search-receipt.json`
- Create: `evidence/public/v02/search/evidence-index.json`
- Create outside Git, no-clobber: new digest-keyed custody JSON under
  `D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/`

**Interfaces:**
- Consumes: clean Task 6B `SEARCH_SOURCE_COMMIT`, exact 43-path source, existing no-clobber producer.
- Produces: canonical receipt/index, independent custody anchor, exact `A/A` direct-child freeze,
  `SEARCH_FREEZE_PASS`.

- [ ] **Step 1: Reconfirm the controlled interval**

```powershell
if ((git rev-parse HEAD).Trim() -ne $searchSourceCommit) { throw 'source commit drift' }
if (@(git status --porcelain=v1).Count -ne 0) { throw 'source tree dirty' }
if (Test-Path -LiteralPath 'evidence/public/v02/search/search-receipt.json') { throw 'receipt unexpectedly exists' }
if (Test-Path -LiteralPath 'evidence/public/v02/search/evidence-index.json') { throw 'index unexpectedly exists' }
if (@(git remote).Count -ne 0 -or @(git tag --points-at HEAD).Count -ne 0) { throw 'Git trust drift' }
```

- [ ] **Step 2: Run the existing no-clobber producer exactly once**

```powershell
$createdAtUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
uv run python -m mdcp.temporal.cli prepare-search-freeze --repository-root . --created-at-utc $createdAtUtc
git status --short --untracked-files=all
```

Expected: exactly two untracked canonical files. If either file existed before the call, only one
file appears, or the command fails after partial publication, stop without retry.

- [ ] **Step 3: Validate canonical bytes and identities before staging**

```powershell
$receiptPath='evidence/public/v02/search/search-receipt.json'
$indexPath='evidence/public/v02/search/evidence-index.json'
$receipt=Get-Content -Raw -LiteralPath $receiptPath | ConvertFrom-Json
$index=Get-Content -Raw -LiteralPath $indexPath | ConvertFrom-Json
if ($receipt.search_source_commit -ne $searchSourceCommit) { throw 'receipt source mismatch' }
if ($receipt.h2_status -ne 'SEALED_NOT_LOADED' -or $receipt.h2_loaded_rows -ne 0) { throw 'receipt H2 mismatch' }
if ($index.h2_status -ne 'SEALED_NOT_LOADED' -or $index.h2_loaded_rows -ne 0) { throw 'index H2 mismatch' }
if ($index.source_entries.Count -ne 43) { throw 'source count mismatch' }
$receiptSha=(Get-FileHash -Algorithm SHA256 -LiteralPath $receiptPath).Hash.ToLowerInvariant()
$indexSha=(Get-FileHash -Algorithm SHA256 -LiteralPath $indexPath).Hash.ToLowerInvariant()
if ($index.search_receipt_sha256 -ne $receiptSha) { throw 'receipt binding mismatch' }
if ($indexSha -eq 'ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d') { throw 'rejected index identity reused' }
```

Run public-evidence validation without printing paths or raw exception values:

```powershell
uv run pytest -q tests/security/temporal/test_public_evidence_boundary.py
```

- [ ] **Step 4: Publish the new custody leaf no-clobber**

```powershell
$custodyRoot='D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody'
$custodyPath=Join-Path $custodyRoot "$indexSha.search-source-custody.json"
if (Test-Path -LiteralPath $custodyPath) { throw 'custody collision' }
$custodyObject=[ordered]@{schema_version='mdcp.search-source-custody.v1';source_inventory_index_sha256=$indexSha}
$custodyBytes=[Text.Encoding]::UTF8.GetBytes(($custodyObject | ConvertTo-Json -Compress))
$stream=[IO.File]::Open($custodyPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $stream.Write($custodyBytes,0,$custodyBytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
$custodySha=(Get-FileHash -Algorithm SHA256 -LiteralPath $custodyPath).Hash.ToLowerInvariant()
```

Reopen and parse the custody file independently; require exact two keys, exact schema version, and
the new `$indexSha`. Record `$custodyPath` privately and `$custodySha` in the final report. Never add
the custody file to Git.

- [ ] **Step 5: Stage and commit exactly `A/A`**

```powershell
git add -- evidence/public/v02/search/evidence-index.json evidence/public/v02/search/search-receipt.json
$staged=@(git diff --cached --name-status)
git diff --cached --check
git commit -m "evidence: freeze corrected temporal search"
$searchFreezeCommit=(git rev-parse HEAD).Trim()
git diff-tree --no-commit-id --name-status -r HEAD
```

Require `$staged.Count -eq 2`; split each line at the first tab and require status `A` plus the exact
two-path set before committing.

- [ ] **Step 6: Verify the committed freeze and direct-child relationship**

```powershell
$parent=(git rev-parse HEAD^).Trim()
if ($parent -ne $searchSourceCommit) { throw 'freeze parent mismatch' }
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
uv run python -c "from pathlib import Path; import sys; from mdcp.temporal.search_identity import verify_search_freeze; result=verify_search_freeze(Path.cwd(),Path('evidence/public/v02/search/search-receipt.json'),Path('evidence/public/v02/search/evidence-index.json'),expected_head=sys.argv[1]); print(result.reason_codes[0]); raise SystemExit(0 if result.verdict=='PASS' else 1)" $searchFreezeCommit
```

Expected: `SEARCH_FREEZE_PASS`.

- [ ] **Step 7: Prove the no-`.git` source archive under all autocrlf modes**

Create one OS-temporary attributes profile with the exact five lines from Task 6A. For each mode
`true`, `false`, `input`:

```powershell
git -c core.autocrlf=$mode -c core.attributesFile=$profile archive --format=tar --output=$tarPath $searchSourceCommit
tar -xf $tarPath -C $extractRoot
if (Test-Path -LiteralPath (Join-Path $extractRoot '.git')) { throw 'archive contains .git' }
uv run python -m mdcp.temporal.cli verify-search-source --root $extractRoot --index evidence/public/v02/search/evidence-index.json --expected-index-sha256 $indexSha
```

Expected for each: `SEARCH_SOURCE_INVENTORY_PASS`, exactly 43 indexed regular files, no `.git`.
Require all three tar SHA-256 values identical. Preserve failed diagnostic roots; remove successful
temporary roots after recording hashes.

- [ ] **Step 8: Run all fresh completion gates**

```powershell
uv run pytest -q
uv run pytest -q tests/unit/temporal tests/integration/temporal tests/contract/temporal tests/security/temporal
uv run pytest -q tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run pytest -q tests/integration/temporal/test_search_freeze_preflight.py
uv run ruff check src/mdcp/temporal tests/unit/temporal tests/integration/temporal tests/security/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py src/mdcp/temporal/search_identity.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_runner_synthetic.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv lock --check
git diff --check
```

Run credential/private-path/publication scans with defensive regex sources excluded only from the
credential pattern match, never from protected-byte or security tests. The permitted defensive
exclusions are `tests/security/temporal/test_public_evidence_boundary.py` and
`src/mdcp/temporal/evidence.py`. Require zero findings elsewhere.

- [ ] **Step 9: Verify protected bytes and full-range allowlist**

```powershell
foreach ($entry in $protected.GetEnumerator()) {
  if (-not (Test-Path -LiteralPath $entry.Key -PathType Leaf)) { throw "protected path missing" }
  $actual=(git hash-object --path=$entry.Key -- $entry.Key).Trim()
  if ($actual -ne $entry.Value) { throw "protected blob drift" }
}
$changed=@(git diff --name-only $planEntry..HEAD)
$outside=@($changed | Where-Object { $_ -notin $allowlist })
if ($outside.Count -ne 0) { throw 'allowlist drift' }
```

Recompute v0.1/v0.2 serving identities and require the approved values. Recompute dependency lock,
approved spec, topology spec, receipt, index, custody, source inventory, source archive, and H2
identities.

- [ ] **Step 10: Obtain final independent whole-range review**

Review every commit from `$planEntry` exclusive through `$searchFreezeCommit` inclusive. The review
must inspect Task 6B's deletion and Task 7's addition separately, not only their net diff. Require:

```text
Critical: 0
Important: 0
```

Any unresolved Critical/Important produces the blocked terminal. Do not amend, delete, refreeze, or
start P2.

---

## Completion report

Report:

- plan entry, Tasks 1-5, Task 6A, Task 6B, and Task 7 commit SHAs;
- exact changed-file inventory and per-task RED -> GREEN evidence;
- fresh targeted and full test counts;
- Ruff, format, lock, diff, credential, private-path, protected-byte, and public-evidence results;
- rejected freeze/custody preservation proof;
- new `SEARCH_SOURCE_COMMIT` and `SEARCH_FREEZE_COMMIT` direct-child proof;
- old and new receipt/index/custody SHA-256 identities;
- exact 43-path inventory digest and three identical archive SHA-256 values;
- v0.1/v0.2 serving identities;
- independent review findings;
- branch, HEAD, clean status, remote count, tag count;
- H2 `SEALED_NOT_LOADED`, loaded rows `0`; and
- explicit proof that no UCI/H1/H2 rows, real authorization, model, Docker, GPU, network, remote,
  release, P2, or Wave 4 action occurred.

Successful terminal:

```text
SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED / H2_SEALED_NOT_LOADED
```

Blocked terminal:

```text
W3_FORMAL_SEAL_CLOSURE_BLOCKED / P2_FORBIDDEN / H2_SEALED_NOT_LOADED
```

Stop after either terminal. Preserve the branch, worktree, rejected evidence history, old custody,
new custody, and diagnostic roots. Do not merge or clean the worktree.

## Plan self-review checklist

- Every requirement in both approved corrective specs maps to an explicit task and gate.
- Seven tasks produce at least eight implementation commits because Task 6 has independent A/B
  boundaries.
- Task 1 removes all callback/natural capability, not only the originally reported names.
- Task 2 validates both destinations outside the repository and consumes every close result.
- Task 3 recomputes one five-file semantic chain and retains the external seal anchor.
- Task 4 exposes exactly `build_parser` and `main`.
- Task 5 tests spelling-independent capability recovery and one formal dispatch edge.
- Task 6 performs the exact three-for-three 43-path migration.
- Task 6B verifies recoverability before the only destructive action.
- Task 7 uses the unchanged no-clobber producer and creates an exact `A/A` direct child.
- No digest includes itself; receipt -> index -> external custody -> freeze is acyclic.
- No step requires natural rows, real authorization, model execution, network, dependency change,
  new path, verifier weakening, or platform expansion.
- Failure after Task 6B leaves a clean, explicit, P2-forbidden source checkpoint without automated
  rollback.
