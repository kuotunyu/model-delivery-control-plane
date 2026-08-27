# MDCP v0.2 Wave 3 Dedicated Formal Worker Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rejected one-process callback-reachability proof with one fixed Windows Python worker whose only cross-process values are bounded canonical JSON bytes, then refreeze the exact 47-path search source without running P2.

**Architecture:** A Git-capable trusted supervisor performs full repository pre/post checks and launches one fresh, no-site, no-PATH Python 3.12 worker. The worker independently verifies its exact source, consumes one authorization before any archive or model access, owns the pure 80+0/4 state machine and publication lifecycle, and returns one bounded sanitized response; source identity is finalized through the separately reviewed `D/D` tombstone followed by one `A/A` receipt-only freeze.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Ruff, uv, RFC 8785 canonical JSON, SHA-256, Git, Windows retained-handle publication, PowerShell 7.

## Global Constraints

- Work only in the single Git-registered worktree whose branch and HEAD exactly match the future owner execution authorization. Discover it with `git worktree list --porcelain`; do not trust a manually typed worktree path.
- Before implementation, independently hash this plan and the approved design at `docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md`; require the exact owner-approved bytes.
- The implementation is strictly serial: Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7 -> Task 8 -> Task 9 -> Task 10A -> Task 10B. Do not parallelize tasks or cross a failed gate.
- Task 1 is an external diagnostic-preservation and working-copy-retirement task with no Git commit. Tasks 2-8 each end in one independent append-only commit. Task 9 is a fresh committed-tree review with no commit. Tasks 10A and 10B are separate append-only evidence commits.
- Every production behavior begins with a real RED test that fails for the expected missing behavior, then the minimum GREEN implementation. A syntax, collection, dependency, or unrelated failure is not acceptable RED evidence.
- Every source-changing task runs its targeted suite, full CPU pytest, Ruff check, exact changed-Python format check, `uv lock --check`, and `git diff --check`, then receives independent Critical `0`, Important `0` review before commit.
- Use only deterministic synthetic data and denial hooks. Do not open or hash the real UCI archive, read H1/H2 rows, create or consume a real authorization, execute an estimator, run ONNX/MLflow/Docker/GPU, use network, or start P2/Wave 4.
- H2 remains `SEALED_NOT_LOADED`, loaded rows `0`. `day.csv`, `hour.csv` row 13,004 and later, `open_h2`, `DatasetPartitions`, `split_rows`, and legacy `load_uci_archive` remain forbidden.
- Preserve exactly four folds, 20 trials, 19 eligible candidates, 80 selection fits, zero or four replay fits, at most one later final fit, at most 85 total fits, seed `2026`, and one estimator thread. Corrective tasks may exercise only synthetic 80+0/4 Wave 3 behavior.
- Preserve Windows-only mutation, retained-handle no-clobber publication, checked-close semantics, external destinations, the five-file private container, and one terminal public seal. Make no POSIX mutation claim.
- Preserve v0.1 serving identity `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`, v0.2 serving identity `afa14abec0951a117ce1bd729bbd04fd3d645cf530022257df209559af85d7d1`, `uv.lock` SHA-256 `781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae`, protected Wave 0-2 bytes, temporal protocol, natural rejection evidence, rejected freeze history, and external custody.
- Preserve rejected freeze commit `2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598`, search receipt SHA-256 `7bf1f01f5883c563639152b8eda6fbff8ab1171c85a5865e21ee0303afdbdc94`, evidence index SHA-256 `ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d`, and custody SHA-256 `38fc225f45fc2a282be339c8d6974154bd90a94af93132ed2132ca5c9b04bf9f` at `D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d.search-source-custody.json`.
- Configure author and committer for every commit as `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`. Do not amend, rebase, squash, reset, restore, checkout files, stash, cherry-pick, rewrite history, create a remote, push, merge, tag, or Release.
- Stop if a required change is outside the exact 25-path allowlist, a protected identity drifts, source inventory cannot be exactly 47 and acyclic, a task/review gate fails, the worker needs a callback or second process, any data/model access can precede the marker, any Critical/Important finding remains, or one architectural blocker survives three separately evidenced hypotheses.
- Before Task 10A, failure preserves the rejected freeze and all append-only commits. After Task 10A, failure stops at the clean P2-forbidden no-evidence source commit. A failed Task 10B remains rejected history; no automated rollback or second freeze is allowed.

---

## Approved identities and exact boundaries

### Three rejected uncommitted diagnostics at plan authoring entry

```text
6841d27e33131888e226cd94a919c2232fff0aa0cb040f29686deeb60c86d233  src/mdcp/temporal/firewall.py
a096f1db08de3158efad029883a93fb440ad7417f57d59451c5ee1bbf20c60c5  tests/security/temporal/test_data_firewall.py
0c2e48907badd8ca11e4e773aea66ee9f746fb42a8583fb571d9ac9971f93759  tests/security/temporal/test_formal_runner_firewall.py
```

These working-copy bytes are rejected diagnostic evidence, not accepted implementation. Task 1 copies them byte-for-byte to a new private Git-external root and retires only their uncommitted hunks with `apply_patch`.

### Exact 25-path implementation allowlist

```text
schemas/v2/development-result-index.schema.json
schemas/v2/formal-run-authorization.schema.json
schemas/v2/formal-worker-request.schema.json
schemas/v2/formal-worker-response.schema.json
src/mdcp/temporal/cli.py
src/mdcp/temporal/firewall.py
src/mdcp/temporal/formal_worker.py
src/mdcp/temporal/formal_worker_protocol.py
src/mdcp/temporal/run_evidence.py
src/mdcp/temporal/runner.py
src/mdcp/temporal/runtime_guards.py
src/mdcp/temporal/search_identity.py
tests/integration/temporal/test_formal_runner_synthetic.py
tests/integration/temporal/test_formal_worker_process.py
tests/integration/temporal/test_search_freeze_preflight.py
tests/security/temporal/test_data_firewall.py
tests/security/temporal/test_formal_run_authorization.py
tests/security/temporal/test_formal_runner_firewall.py
tests/security/temporal/test_public_evidence_boundary.py
tests/unit/temporal/test_fit_ledger.py
tests/unit/temporal/test_formal_worker_protocol.py
tests/unit/temporal/test_run_evidence.py
tests/unit/temporal/test_runtime_guards.py
evidence/public/v02/search/evidence-index.json
evidence/public/v02/search/search-receipt.json
```

The two evidence leaves are forbidden until Tasks 10A/10B. No dependency, `pyproject.toml`, `uv.lock`, `.gitattributes`, config, fixture, serving identity, preserved evidence, extra module, schema, or test may change.

### File responsibility map

- `formal_worker_protocol.py`: frozen closed request/response, authorization, search-receipt, source-entry, and evidence-index models; canonical byte parsing/encoding; the authoritative source-path tuple; fixed limits/reason codes; exact four-path worker inventory; and symbolic launch-profile digest. It performs no I/O, environment, clock, process, dataset, model, or publication action.
- Request/response schemas: independent exact JSON Schema representations of the protocol models, including closed nested objects, finite enumerations, canonical path/digest constraints, and exact field sets.
- `runner.py`: pure deterministic state machine that issues typed fit requests and accepts typed fold results; no path, file, loader, estimator, process, publication, or caller callback capability.
- `run_evidence.py`: supervisor, public outcome/seal models, publication and recovery primitives, synthetic writer/verifier, and fixed private process transport. It never imports or invokes natural data/model capabilities.
- `formal_worker.py`: standard-library-only bootstrap plus one no-argument `main`, fixed lifecycle, natural loader/model ownership after marker consumption, private/public publication, one canonical stdout response, and no child process.
- `runtime_guards.py`: worker-local time, process-memory, fit-budget, H2, and 47-path source checkpoints; supervisor-side Git/repository checks remain separate.
- `cli.py`: exactly `build_parser` and `main`; one dispatch into the fixed supervisor, sanitized output only.
- `firewall.py`: finite import/call/protocol/process policy; no whole-language soundness claim.
- `search_identity.py`: Git-backed inventory construction and search freeze; imports/re-exports the protocol-owned authorization/search/index types and authoritative source-path tuple instead of defining a second meaning.
- `development-result-index.schema.json`: terminal seal fields and closed recovery identity.
- `formal-run-authorization.schema.json`: compatibility with the single protocol-owned authorization meaning only; no new authorization semantics.
- Tests: independently lock protocol, state machine, process transport, lifecycle order, H2/firewall, publication/recovery, public boundary, exact inventory, and source-archive behavior.

### Fixed process constants

```text
request/response physical maximum  65,536 bytes
stdout overflow probe              65,537 bytes
wall timeout                       21,600 seconds
post-termination wait              30 seconds
automatic retry                    false
worker launches per request        1
worker child processes             0
```

The launch-profile semantic object contains exactly: Windows platform; absolute current Python 3.12 interpreter; absolute verified `src/mdcp/temporal/formal_worker.py`; arguments `-I -B -S ABSOLUTE_VERIFIED_FORMAL_WORKER_SCRIPT`; `shell=false`; verified repository-root cwd; `close_fds=true`; stdin/stdout pipes; stderr devnull; environment keys `SYSTEMROOT,WINDIR`; site processing false; script-derived `repository_root/src`; interpreter-derived `Lib/site-packages` inserted directly; the limits above; no retry; one worker; zero worker children.

## Entry preflight

- [ ] **Step 1: Locate exactly one authorized registered worktree**

Run from the repository root supplied by the owner:

```powershell
$ErrorActionPreference = 'Stop'
$expectedBranch = 'refs/heads/codex/wave0-foundation-feasibility'
if ($null -eq $authorizedPlanCommit -or $authorizedPlanCommit -notmatch '^[0-9a-f]{40}$') {
  throw 'OWNER_AUTHORIZED_PLAN_COMMIT_REQUIRED'
}
$expectedHead = $authorizedPlanCommit
$records = @(git worktree list --porcelain)
$matches = @()
for ($i = 0; $i -lt $records.Count; $i++) {
  if ($records[$i] -like 'worktree *') {
    $candidate = $records[$i].Substring(9)
    $candidateHead = $records[$i + 1].Substring(5)
    $candidateBranch = $records[$i + 2].Substring(7)
    if ($candidateHead -eq $expectedHead -and $candidateBranch -eq $expectedBranch) { $matches += $candidate }
  }
}
if ($matches.Count -ne 1) { throw 'AUTHORIZED_WORKTREE_NOT_UNIQUE' }
$worktree = $matches[0]
Set-Location -LiteralPath $worktree
```

The controller must set `$authorizedPlanCommit` from the exact future owner execution authorization
before running this block. Do not infer it from current HEAD and do not edit this committed plan to
inject its own commit hash.

- [ ] **Step 2: Verify immutable entry state**

```powershell
if ((git branch --show-current) -ne 'codex/wave0-foundation-feasibility') { throw 'BRANCH_MISMATCH' }
if ((git rev-parse HEAD) -ne $expectedHead) { throw 'HEAD_MISMATCH' }
if (@(git remote).Count -ne 0) { throw 'REMOTE_DRIFT' }
if (@(git tag --points-at HEAD).Count -ne 0) { throw 'HEAD_TAG_DRIFT' }
$expectedDirty = @(
  ' M src/mdcp/temporal/firewall.py',
  ' M tests/security/temporal/test_data_firewall.py',
  ' M tests/security/temporal/test_formal_runner_firewall.py'
)
$actualDirty = @(git status --porcelain=v1 -uall)
if ((Compare-Object $expectedDirty $actualDirty).Count -ne 0) { throw 'ENTRY_DIRTY_SET_MISMATCH' }
```

- [ ] **Step 3: Verify approved design, plan, diagnostics, H2, lock, and rejected evidence**

```powershell
$expected = [ordered]@{
  'docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md' = '8824978d9e0a56895d79429b924b6853715b4ea302e093cb1da9de26970fdf2c'
  'src/mdcp/temporal/firewall.py' = '6841d27e33131888e226cd94a919c2232fff0aa0cb040f29686deeb60c86d233'
  'tests/security/temporal/test_data_firewall.py' = 'a096f1db08de3158efad029883a93fb440ad7417f57d59451c5ee1bbf20c60c5'
  'tests/security/temporal/test_formal_runner_firewall.py' = '0c2e48907badd8ca11e4e773aea66ee9f746fb42a8583fb571d9ac9971f93759'
  'uv.lock' = '781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae'
  'evidence/public/v02/search/search-receipt.json' = '7bf1f01f5883c563639152b8eda6fbff8ab1171c85a5865e21ee0303afdbdc94'
  'evidence/public/v02/search/evidence-index.json' = 'ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d'
}
foreach ($entry in $expected.GetEnumerator()) {
  $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Key).Hash.ToLowerInvariant()
  if ($actual -ne $entry.Value) { throw "ENTRY_HASH_MISMATCH: $($entry.Key)" }
}
$receipt = Get-Content -Raw -LiteralPath 'evidence/public/v02/search/search-receipt.json' | ConvertFrom-Json
$index = Get-Content -Raw -LiteralPath 'evidence/public/v02/search/evidence-index.json' | ConvertFrom-Json
if ($receipt.h2_status -ne 'SEALED_NOT_LOADED' -or $receipt.h2_loaded_rows -ne 0) { throw 'H2_RECEIPT_DRIFT' }
if ($index.h2_status -ne 'SEALED_NOT_LOADED' -or $index.h2_loaded_rows -ne 0) { throw 'H2_INDEX_DRIFT' }
$custody = 'D:/model-delivery-control-plane-runtime/evidence/search-freeze-custody/ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d.search-source-custody.json'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $custody).Hash.ToLowerInvariant() -ne '38fc225f45fc2a282be339c8d6974154bd90a94af93132ed2132ca5c9b04bf9f') { throw 'REJECTED_CUSTODY_DRIFT' }
```

- [ ] **Step 4: Freeze the execution allowlist and protected Git blob map in controller memory**

Set `$planEntry = $expectedHead`, define `$allowlist` as the exact 25 paths above, enumerate every tracked path at `$planEntry`, and store `git rev-parse "$planEntry`:$path"` for every path outside the allowlist. Do not serialize repository absolute paths. Recompute this map before each commit and at completion.

---

### Task 1: Preserve and retire the rejected Task 5 diagnostics

**Files:**
- Preserve externally: the exact three dirty files listed above
- Retire working-copy hunks: `src/mdcp/temporal/firewall.py`
- Retire working-copy hunks: `tests/security/temporal/test_data_firewall.py`
- Retire working-copy hunks: `tests/security/temporal/test_formal_runner_firewall.py`

**Interfaces:**
- Consumes: exact entry working bytes and their three approved SHA-256 values.
- Produces: a new private external diagnostic package and a clean worktree at unchanged HEAD.

- [ ] **Step 1: Create a new non-existing private preservation root**

Choose a new leaf under `D:/model-delivery-control-plane-runtime/evidence/rejected-diagnostics/` using the entry HEAD prefix and UTC creation time. Require the leaf not to exist. Create only that external leaf and its `payload` directory. Record the source as private environment metadata and mark the evidence class `rejected_review_diagnostic` and publication approval `false`.

- [ ] **Step 2: Copy the three bytes and build two independent inventories**

Copy, never move, the three working files into `payload` under their exact relative paths. Compute source and destination inventories independently with fields `relative_path`, `byte_size`, and lowercase `sha256`. Require exactly three unique ASCII-ordered paths, equal counts, equal total bytes, equal path sets, equal sizes, and equal per-file hashes.

- [ ] **Step 3: Publish private preservation metadata without a self-hash cycle**

Create `payload-SHA256SUMS`, then canonical `preservation-receipt.json` containing entry HEAD, three source diagnostic hashes, destination identity, UTC preservation time, counts/bytes, inventory digest, `rejected_review_diagnostic`, `private_external_evidence`, and `not_approved_for_publication`. Create `FINAL-SHA256SUMS` over payload sums plus receipt; it excludes itself. Verify every digest after close.

- [ ] **Step 4: Retire only the rejected hunks with apply_patch**

Run `git diff HEAD -- src/mdcp/temporal/firewall.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py` to identify the exact diagnostic hunks. Apply their inverse manually through `apply_patch`; do not invoke `git restore`, `git checkout`, reset, stash, or any generated file rewrite. Verify each file now has the Git blob identity from `$planEntry`, `git diff --check` passes, status is clean, HEAD is unchanged, and the external payload remains equivalent to the pre-retirement hashes.

- [ ] **Step 5: Record Task 1 review gate**

Obtain independent read-only review of the external inventory metadata and the before/after Git evidence. Require Critical `0`, Important `0`. Task 1 creates no Git commit.

---

### Task 2: Define the closed worker protocol and schemas

**Files:**
- Create: `src/mdcp/temporal/formal_worker_protocol.py`
- Create: `schemas/v2/formal-worker-request.schema.json`
- Create: `schemas/v2/formal-worker-response.schema.json`
- Create: `tests/unit/temporal/test_formal_worker_protocol.py`
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: RFC 8785 helpers, SHA-256 helpers, existing authorization/search bindings, approved design field sets.
- Produces: `FormalWorkerRequest`, `FormalWorkerResponse`, `FormalWorkerSourceEntry`, `FormalRunAuthorization`, `SearchReceipt`, `SearchSourceEntry`, `SearchEvidenceIndex`, canonical parse/encode functions, the current exact 43-path `SEARCH_SOURCE_PATHS`, `FORMAL_WORKER_SOURCE_PATHS`, `FORMAL_WORKER_SOURCE_INVENTORY_SCHEMA_VERSION`, `LAUNCH_PROFILE`, and fixed protocol limits/reason codes.

- [ ] **Step 1: Add exact RED protocol tests**

Create table-driven tests that first fail because the module and schemas do not exist. Lock these constants and shapes:

```python
MAX_WORKER_MESSAGE_BYTES = 65_536
WORKER_STDOUT_PROBE_BYTES = 65_537
FORMAL_WORKER_TIMEOUT_SECONDS = 21_600
FORMAL_WORKER_TERMINATION_WAIT_SECONDS = 30
FORMAL_WORKER_SOURCE_PATHS = (
    "schemas/v2/formal-worker-request.schema.json",
    "schemas/v2/formal-worker-response.schema.json",
    "src/mdcp/temporal/formal_worker.py",
    "src/mdcp/temporal/formal_worker_protocol.py",
)
```

Assert the request has exactly these 17 fields:

```text
schema_version
canonicalization_version
expected_freeze_head
repository_root
search_receipt_path
evidence_index_path
authorization_path
consumption_root
archive_path
private_container_path
search_receipt_sha256
evidence_index_sha256
authorization_sha256
source_inventory_sha256
repository_inventory_sha256
formal_worker_inventory_sha256
launch_profile_sha256
```

Assert the response has exactly
these 15 fields: `schema_version`, `canonicalization_version`, `verdict`, `reason_codes`,
`private_identity`, `seal_record_sha256`, `repository_inventory_sha256`,
`authorization_sha256`, `consumption_marker_sha256`, `fit_count`, `h2_status`,
`h2_loaded_rows`, `worker_request_sha256`, `formal_worker_inventory_sha256`, and
`launch_profile_sha256`. Assert `fit_count` is an actual integer `0..84`, never bool; all SHA fields
are 64 lowercase hex and nonzero where required.

Lock controlled worker response reasons to the pre-consumption failures
`FORMAL_RUN_REQUEST_INVALID`, `SEARCH_FREEZE_INVALID`, `FORMAL_RUN_AUTHORIZATION_INVALID`,
`FORMAL_RUN_AUTHORIZATION_MISMATCH`, `FORMAL_RUN_REPOSITORY_INVALID`,
`FORMAL_RUN_CONSUMPTION_ROOT_INVALID`, `FORMAL_RUN_DESTINATION_INVALID`,
`FORMAL_RUN_AUTHORIZATION_CONSUMED`, `FORMAL_RUN_CONSUMPTION_FAILED`, and
`PUBLICATION_UNSUPPORTED`, plus the post-consumption reasons `FORMAL_RUN_CONSUMPTION_UNKNOWN`,
`FORMAL_RUN_EXECUTION_UNKNOWN`, and `FORMAL_RUN_SEAL_UNKNOWN`. Lock
`FORMAL_WORKER_LAUNCH_FAILED` to supervisor pre-process failure and
`FORMAL_WORKER_PROCESS_UNKNOWN` to supervisor post-process uncertainty; neither may be emitted as
an invented worker success. `PASS` has an empty reason tuple.

- [ ] **Step 2: Add adversarial RED byte/schema cases**

Parametrize missing, extra, duplicate, reordered-noncanonical, invalid type, bool-for-int, non-finite, oversized, BOM, newline, trailing byte, invalid UTF-8, relative/noncanonical path, invalid digest, zero identity, unknown version, and request self-hash mutations. Add callback-shaped strings, pickle/base64 fields, code fields, module/import names, environment objects, nested opaque objects, and unknown reason codes. Require fixed reason codes only; errors never echo supplied values.

- [ ] **Step 3: Observe Task 2 RED**

```powershell
uv run pytest -q tests/unit/temporal/test_formal_worker_protocol.py tests/security/temporal/test_formal_run_authorization.py -k "formal_worker or protocol_owned_authorization"
```

Expected: import/schema/closed-model failures caused by the absent protocol implementation.

- [ ] **Step 4: Implement the minimum pure protocol**

Use frozen Pydantic models with `extra="forbid"` at every level. Parse raw bytes with duplicate-key/non-finite rejection, require byte-for-byte RFC 8785 recanonicalization, and cap before parsing. Encode only validated model dumps. Define the symbolic launch-profile object exactly from the approved design and hash its canonical bytes. Define the exact four-entry worker inventory shape and digest helper without opening files.

Move the authoritative process-free `FormalRunAuthorization`, `SearchReceipt`, `SearchSourceEntry`,
and `SearchEvidenceIndex` definitions plus the current exact 43-path `SEARCH_SOURCE_PATHS` into this
module. In `search_identity.py`, import and re-export those same objects; retain only Git/file-backed
inventory and freeze functions there. Do not duplicate fields, validators, path tuples, or inventory
digest semantics. Task 8 will perform the approved 43-to-47 source-path migration in the
protocol-owned tuple after all four new source/schema paths exist. The protocol module imports no
file operations, `os`, `time`, `random`, `secrets`, `socket`, `subprocess`, data, model, or
publication code.

- [ ] **Step 5: Run Task 2 GREEN and whole-tree gates**

```powershell
uv run pytest -q tests/unit/temporal/test_formal_worker_protocol.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py
uv run pytest -q
uv run ruff check src/mdcp/temporal/formal_worker_protocol.py src/mdcp/temporal/search_identity.py tests/unit/temporal/test_formal_worker_protocol.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py
uv run ruff format --check src/mdcp/temporal/formal_worker_protocol.py src/mdcp/temporal/search_identity.py tests/unit/temporal/test_formal_worker_protocol.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py
uv lock --check
git diff --check
```

- [ ] **Step 6: Review and commit Task 2**

Require independent Critical `0`, Important `0`, stage only allowlisted Task 2 paths, verify staged diff, then commit:

```powershell
git commit -m "feat: define closed formal worker protocol"
```

---

### Task 3: Convert the runner to a pure deterministic state machine

**Files:**
- Modify: `src/mdcp/temporal/runner.py`
- Modify: `tests/unit/temporal/test_fit_ledger.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `src/mdcp/temporal/runtime_guards.py`
- Modify: `tests/unit/temporal/test_runtime_guards.py`

**Interfaces:**
- Consumes: frozen trials/folds/ranking/replay policy and existing ledger/result value types.
- Produces: `DevelopmentFitRequest`, `DevelopmentFoldResult`, `DevelopmentStateMachine.next_fit_request()`, `record_fit_result()`, and `finalize()` with no callable capability.

- [ ] **Step 1: Add RED state-machine contract tests**

Lock this surface:

```python
@dataclass(frozen=True, slots=True)
class DevelopmentFitRequest:
    sequence: int
    phase: FitPhase
    trial_id: str
    fold_id: str

@dataclass(frozen=True, slots=True)
class DevelopmentFoldResult:
    trial_id: str
    fold_id: str
    inventory: tuple[SourceRowIdentity, ...]
    adapters: tuple[AdapterOutcome, ...]
    predictions: tuple[PredictionOutcome, ...]
    labels: tuple[LabelOutcome, ...]
    contract_verdict: GateVerdict
    preprocessing_state_sha256: str
    feature_vector_sha256: str
    prediction_vector_sha256: str
    metric_sha256: str
    receipt_sha256: str
```

`DevelopmentStateMachine.next_fit_request()` returns `DevelopmentFitRequest | None`;
`record_fit_result(request: DevelopmentFitRequest, result: DevelopmentFoldResult)` returns `None`;
and `finalize()` returns `DevelopmentRunBundle`. Do not add an opaque payload. Tests must prove:
exact 80 selection order, rank-one only, zero replay on no eligible candidate, exactly four replay
folds for one winner, one outstanding request, ledger reservation on issue, and one-shot finalize.

- [ ] **Step 2: Add adversarial RED transitions**

Reject the 81st selection request, fifth replay, duplicate result, result before issue, stale/reordered request, wrong sequence/trial/fold/phase, rank-two fallback, second state machine/ledger/replay session, non-finite metrics, and result after finalize. Static tests reject parameters/defaults/attributes containing callbacks, paths, files, loaders, estimator builders, modules, registries, or publication functions.

- [ ] **Step 3: Observe Task 3 RED**

```powershell
uv run pytest -q tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py -k "state_machine or typed_fit_request or pure_runner"
```

Expected: missing state-machine surface and remaining callback-owned execution path failures.

- [ ] **Step 4: Implement the minimum pure state machine**

Move only deterministic sequencing, result acceptance, ranking, qualification, and replay selection into `DevelopmentStateMachine`. Ledger the issued operation before returning it. Keep exactly one outstanding immutable request. The worker, not the state machine, will materialize data and execute fits. Synthetic tests feed typed deterministic results directly. Delete the production callback/factory/executor interface rather than renaming it.

- [ ] **Step 5: Run Task 3 GREEN and whole-tree gates**

```powershell
uv run pytest -q tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py
uv run pytest -q
uv run ruff check src/mdcp/temporal/runner.py src/mdcp/temporal/runtime_guards.py tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/runtime_guards.py tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/integration/temporal/test_formal_runner_synthetic.py tests/security/temporal/test_formal_runner_firewall.py
uv lock --check
git diff --check
```

- [ ] **Step 6: Review and commit Task 3**

Require independent Critical `0`, Important `0`, then commit only the Task 3 diff:

```powershell
git commit -m "refactor: make temporal development a pure state machine"
```

---

### Task 4: Implement the fixed supervisor process transport

**Files:**
- Modify: `src/mdcp/temporal/run_evidence.py`
- Create: `src/mdcp/temporal/formal_worker.py`
- Create: `tests/integration/temporal/test_formal_worker_process.py`
- Modify: `tests/unit/temporal/test_run_evidence.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `src/mdcp/temporal/cli.py`

**Interfaces:**
- Consumes: Task 2 protocol/profile and Task 3 state-machine types.
- Produces: fixed `execute_authorized_formal_development(request: FormalDevelopmentRequest) -> FormalDevelopmentOutcome`, private fixed-launch helper, and a fail-closed `formal_worker.main()` bootstrap target.

- [ ] **Step 1: Add RED supervisor-launch tests**

Use a fake process boundary only behind the supervisor's private fixed helper; the public callable accepts no executable, module, command, environment, Popen factory, stream, callback, backend, or worker count. Assert the supervisor validates exact request/source/auth/destination identities, full Git HEAD/clean/repository inventory, verified absolute Python 3.12 executable, verified absolute worker script, and launch-profile digest before process creation.

Assert the only launch is equivalent to:

```python
[
    ABSOLUTE_CURRENT_PYTHON_3_12,
    "-I",
    "-B",
    "-S",
    ABSOLUTE_VERIFIED_FORMAL_WORKER_SCRIPT,
]
```

with `shell=False`, cwd verified repository root, `close_fds=True`, stdin/stdout pipes, stderr devnull, and environment containing exactly `SYSTEMROOT` and `WINDIR`.

- [ ] **Step 2: Add RED transport and failure matrix**

Prove request cap/EOF, 65,537-byte stdout overflow detection, one monotonic 21,600-second deadline, one termination request, one 30-second post-termination wait, and zero retry. Cover shell/PATH/relative executable/changed script/flag omission/changed cwd/extra env/inherited handle/second worker/caller argument; process creation failure; timeout; partial/extra/oversized stdout; stdout read/EOF uncertainty; malformed/noncanonical response; nonzero/unobservable exit; response identity mismatch; public leaf mismatch; and supervisor post-exit HEAD/clean/repository drift.

Expected outcomes:

```text
before process creation: FAIL / FORMAL_WORKER_LAUNCH_FAILED (for CreateProcess failure)
after process creation:  UNKNOWN / FORMAL_WORKER_PROCESS_UNKNOWN
```

After unauthenticated process failure, `fit_count`, private identity, terminal digest, and repository inventory are `None`/absent.

- [ ] **Step 3: Observe Task 4 RED**

```powershell
uv run pytest -q tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_formal_runner_firewall.py -k "worker_process or launch_profile or bounded_transport or post_exit_git"
```

Expected: supervisor still owns in-process natural execution and no fixed process transport exists.

- [ ] **Step 4: Implement the supervisor and fail-closed bootstrap**

Make `FormalDevelopmentOutcome.fit_count` `int | None`. Construct canonical `FormalWorkerRequest`, hash it outside the request, and implement the exact one-process transport without unbounded `communicate()`. Git/process imports stay function-local and supervisor-only. Repeat HEAD, clean state, and full repository inventory after child exit before live acceptance.

Create `formal_worker.py` with a standard-library-only bootstrap that validates `__main__`, `sys.flags.isolated`, `sys.flags.no_site`, `sys.dont_write_bytecode`, Python 3.12, script canonicality, derived repository/source and venv `Lib/site-packages`, then directly inserts only those two directories into `sys.path`. It never calls `site.addsitedir`. At this task it must fail closed with a canonical controlled response before authorization/data access; direct import or direct call performs no formal work.

- [ ] **Step 5: Run Task 4 GREEN and whole-tree gates**

```powershell
uv run pytest -q tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run pytest -q
uv run ruff check src/mdcp/temporal/run_evidence.py src/mdcp/temporal/formal_worker.py src/mdcp/temporal/cli.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run ruff format --check src/mdcp/temporal/run_evidence.py src/mdcp/temporal/formal_worker.py src/mdcp/temporal/cli.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

- [ ] **Step 6: Review and commit Task 4**

Require independent Critical `0`, Important `0`, then commit:

```powershell
git commit -m "feat: isolate formal execution behind fixed worker transport"
```

---

### Task 5: Move authorization, data, execution, and publication into the worker

**Files:**
- Modify: `src/mdcp/temporal/formal_worker.py`
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `src/mdcp/temporal/runtime_guards.py`
- Modify: `tests/integration/temporal/test_formal_worker_process.py`
- Modify: `tests/integration/temporal/test_formal_runner_synthetic.py`
- Modify: `tests/unit/temporal/test_runtime_guards.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Modify: `tests/security/temporal/test_formal_runner_firewall.py`

**Interfaces:**
- Consumes: closed request, fixed bootstrap, pure state machine, existing bounded loader/model builders, authorization marker, runtime guards, private-container/public-seal publisher.
- Produces: the complete single-worker lifecycle and sanitized canonical response, with no natural data/model object in the supervisor.

- [ ] **Step 1: Add RED lifecycle-order tests**

Use temporary synthetic identities, an exact-size wrong-digest fake archive, and denial spies. Do not use the real archive or model. Require the worker to complete, in order: bootstrap; request parse/hash; worker/profile/source/freeze binding; authorization reread; archive path/type/size only; destination proof; retained handles; durable marker; then archive open/hash; only then loader/model imports; state-machine fits; private publication; terminal publication; checked close; response/flush/exit.

Prove no loader import/call, archive-content read, row parse, estimator construction, fit, private-byte construction, or output mutation occurs before marker success. Prove request/source/auth reread disagreement fails before consumption. The fake archive denial is expected immediately after the durable synthetic marker and before parsing/model execution.

- [ ] **Step 2: Add RED execution-budget and worker-guard cases**

Use synthetic typed fold results to prove one ledger/session, exact 80+0 or 80+4 fits, never 81/fifth/duplicate/reordered/wrong trial/fold/rank-two fallback, seed 2026, one estimator thread, and worker-local wall-time/memory/source/H2 checkpoints. Every checkpoint rereads all 47 source files as regular non-link/non-reparse bytes and compares the canonical source digest; it does not invoke Git.

- [ ] **Step 3: Add RED forbidden-capability denial cases**

Prove the worker has no `PATH`, subprocess/Git, shell, network/socket, GPU, Docker, environment recovery, entropy/random device, dynamic import, legacy loader/full split/H2/day.csv/row-13,004 path, alternate publisher, child process, worker pool, retry, or caller-supplied command/callback. Prove `shutil.which("git") is None` in the fixed environment and that project, NumPy, and scikit-learn imports succeed only after the reviewed direct bootstrap.

- [ ] **Step 4: Observe Task 5 RED**

```powershell
uv run pytest -q tests/integration/temporal/test_formal_worker_process.py tests/integration/temporal/test_formal_runner_synthetic.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py -k "worker_lifecycle or marker_before_access or worker_runtime_guard or forbidden_worker_capability"
```

Expected: bootstrap stops before the lifecycle and natural ownership still exists outside the worker.

- [ ] **Step 5: Implement the worker-owned lifecycle**

Move the existing approved natural execution assembly out of any `run_evidence.py` closure and into the worker after marker durability. Keep data/model imports local to that post-marker branch. Iterate `DevelopmentStateMachine.next_fit_request()`, materialize/fit internally, and call `record_fit_result()` with typed values. Publish exactly the existing five private documents and one derived terminal sibling. Emit only a validated `FormalWorkerResponse`; sanitize controlled failures and suppress stderr.

The supervisor retains only public models, fixed process transport, synthetic evidence helper, and read-only verifier. It never reads archive/private payload or owns rows, estimators, predictions, labels, or natural evidence bytes.

- [ ] **Step 6: Run Task 5 GREEN and whole-tree gates**

```powershell
uv run pytest -q tests/integration/temporal/test_formal_worker_process.py tests/integration/temporal/test_formal_runner_synthetic.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run pytest -q
uv run ruff check src/mdcp/temporal/formal_worker.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runtime_guards.py tests/integration/temporal/test_formal_worker_process.py tests/integration/temporal/test_formal_runner_synthetic.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv run ruff format --check src/mdcp/temporal/formal_worker.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/runtime_guards.py tests/integration/temporal/test_formal_worker_process.py tests/integration/temporal/test_formal_runner_synthetic.py tests/unit/temporal/test_runtime_guards.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

- [ ] **Step 7: Review and commit Task 5**

Require independent Critical `0`, Important `0`, then commit:

```powershell
git commit -m "feat: execute formal lifecycle inside dedicated worker"
```

---

### Task 6: Close failure, seal, recovery, and public-evidence semantics

**Files:**
- Modify: `src/mdcp/temporal/run_evidence.py`
- Modify: `schemas/v2/development-result-index.schema.json`
- Modify: `tests/unit/temporal/test_run_evidence.py`
- Modify: `tests/integration/temporal/test_formal_worker_process.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`

**Interfaces:**
- Consumes: accepted canonical worker response, physical terminal leaf, existing five-file recovery chain, external terminal digest.
- Produces: corrected `FormalDevelopmentSeal` and read-only recovery with separate request/worker/profile/source/index identities.

- [ ] **Step 1: Add RED seal and schema identity tests**

Require these new nonzero 64-lowercase-hex fields in both model and closed schema:

```text
worker_request_sha256
formal_worker_inventory_sha256
launch_profile_sha256
evidence_index_sha256
```

Require `source_inventory_sha256` to equal the canonical 47-entry inventory digest and `evidence_index_sha256` to equal the physical canonical index digest. Add coordinated mutation tests proving the rejected swapped meaning cannot pass. Require the exact four-entry worker inventory and symbolic launch profile to reproduce their digests independently.

- [ ] **Step 2: Add RED publication/crash/recovery matrix**

Cover crash after marker, during execution, after private publication, after terminal publication, before stdout, after stdout before observed zero exit, and supervisor post-exit Git drift. Live acceptance must never return `PASS` without zero exit, exact response, physical terminal equality, and stable supervisor pre/post repository observations. Death after terminal publication remains `UNKNOWN` and the physical seal remains externally unanchored.

Recovery must verify authorization -> marker -> five private files -> canonical private identity -> terminal seal -> external terminal digest, plus request, four-path worker inventory, launch profile, source inventory, repository binding, evidence index, fit count, H2, and development result. It never promotes a structurally valid terminal leaf without the externally retained expected terminal digest.

- [ ] **Step 3: Add RED disclosure cases**

Mutate responses, seals, controlled errors, and recovery outputs with path, command, environment, exception/traceback, credential, row, label, prediction, or raw timestamp shapes. Require the public evidence scanner to reject them and failure APIs to emit fixed reason codes without echoing values. No IPC transcript, stderr, process log, third evidence leaf, or temporary public receipt may be published.

- [ ] **Step 4: Observe Task 6 RED**

```powershell
uv run pytest -q tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py -k "worker_request_sha256 or evidence_index_sha256 or crash_matrix or terminal_anchor or public_worker_response"
```

Expected: missing seal fields, old source/index aliasing, or incomplete response/recovery validation.

- [ ] **Step 5: Implement the minimum closed chain**

Extend the models/schema and canonical verifiers. Construct seal fields only from independently verified physical/canonical inputs. On any post-process uncertainty, return sanitized `UNKNOWN` with `fit_count=None` and no private/terminal/repository identity. Retain existing Windows no-clobber/checked-close behavior unchanged.

- [ ] **Step 6: Run Task 6 GREEN and whole-tree gates**

```powershell
uv run pytest -q tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py
uv run pytest -q
uv run ruff check src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py
uv run ruff format --check src/mdcp/temporal/run_evidence.py tests/unit/temporal/test_run_evidence.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

- [ ] **Step 7: Review and commit Task 6**

Require independent Critical `0`, Important `0`, then commit:

```powershell
git commit -m "security: bind worker process into formal seal recovery"
```

---

### Task 7: Replace whole-language reachability with a finite process firewall

**Files:**
- Modify: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`
- Modify: `tests/security/temporal/test_formal_runner_firewall.py`
- Modify: `tests/security/temporal/test_formal_run_authorization.py`
- Modify: `tests/integration/temporal/test_formal_worker_process.py`

**Interfaces:**
- Consumes: fixed supervisor, pure protocol/state machine, dedicated worker, exact launch/lifecycle.
- Produces: finite source/import/call/protocol/process policy with no claim over arbitrary Python semantics.

- [ ] **Step 1: Add RED exact-boundary tests**

Lock exact public callables: `cli.py` exposes only `build_parser` and `main`; `formal_worker.py` exposes one process entry named `main`; protocol exposes only value/canonicalization helpers; runner exposes no natural execution capability. Assert supervisor cannot import/call dataset, estimator, fit, replay, natural encoder, or natural publisher; worker cannot import/call subprocess, Git, shell, socket/network, GPU, Docker, environment recovery, H2/full loader, alternate publisher, or supervisor/CLI/search identity.

- [ ] **Step 2: Add RED IPC and launch non-bypass cases**

Prove request/response annotations and nested models admit only JSON primitives/closed models. Reject callable/class/module/code/pickle/import/opaque values. Prove direct import/call of worker `main` fails before marker/data; only the exact `-I -B -S` launch reaches pre-consumption verification; no caller-selected executable/script/module/cwd/env/handle/stream/process factory crosses the public API.

- [ ] **Step 3: Retire the rejected proof claims**

Delete tests and production rules whose requirement is to prove spelling-independent reachability across arbitrary dynamic Python. Retain narrowly finite AST/source audits for exact imports, calls, definitions, signatures, and known module edges. Add comments and test names that explicitly state defense-in-depth finite policy, not whole-language soundness.

- [ ] **Step 4: Observe Task 7 RED**

```powershell
uv run pytest -q tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_worker_process.py -k "dedicated_worker or finite_process_boundary or no_executable_value_ipc"
```

Expected: old rejected diagnostic rules remain and exact process/module policy is incomplete.

- [ ] **Step 5: Implement the finite firewall**

Replace open-ended taint/capability recovery with exact module-specific allow/deny tables and direct AST facts. Keep dynamic relative imports fail closed. Require exact worker source paths, exact supervisor fixed-launch call edge, exact worker no-subprocess closure, pure runner imports, protocol primitive fields, and public scanner results. Ensure defensive credential regex sources are excluded only from credential grep, never from protected-byte or security tests.

- [ ] **Step 6: Run Task 7 GREEN and whole-tree gates**

```powershell
uv run pytest -q tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
uv run pytest -q
uv run ruff check src/mdcp/temporal/firewall.py src/mdcp/temporal/cli.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
uv run ruff format --check src/mdcp/temporal/firewall.py src/mdcp/temporal/cli.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

- [ ] **Step 7: Review and commit Task 7**

Require independent Critical `0`, Important `0`, including explicit confirmation that no whole-language proof claim remains, then commit:

```powershell
git commit -m "security: enforce finite formal worker boundary"
```

---

### Task 8: Bind the exact 47-path source identity and source archive

**Files:**
- Modify: `src/mdcp/temporal/formal_worker_protocol.py`
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `tests/unit/temporal/test_formal_worker_protocol.py`
- Modify: `tests/integration/temporal/test_search_freeze_preflight.py`
- Modify: `tests/security/temporal/test_public_evidence_boundary.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: committed Tasks 2-7, approved dedicated-worker spec, this plan, four worker source/schema files.
- Produces: exact ASCII-ordered 47-path `SEARCH_SOURCE_PATHS`, independent inventory tests, and byte-identical no-`.git` source-archive proof.

- [ ] **Step 1: Add the independent exact 47-path RED constant**

Lock this complete independent tuple in the integration test:

```text
configs/workload/temporal-development-v2.json
configs/workload/uci-bike-sharing-v1.json
docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md
docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md
docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-dedicated-formal-worker-corrective.md
docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md
docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md
docs/superpowers/specs/2026-08-26-mdcp-v02-private-evidence-container-design.md
docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md
docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md
pyproject.toml
schemas/v2/bike-request.schema.json
schemas/v2/development-result-index.schema.json
schemas/v2/formal-run-authorization.schema.json
schemas/v2/formal-worker-request.schema.json
schemas/v2/formal-worker-response.schema.json
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
src/mdcp/temporal/formal_worker.py
src/mdcp/temporal/formal_worker_protocol.py
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

This is the prior approved 43-path three-for-three substitution with the following deterministic
migration. Replace:

```text
docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-final-review-corrective.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md
```

with:

```text
docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-dedicated-formal-worker-corrective.md
docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md
```

Then add exactly:

```text
schemas/v2/formal-worker-request.schema.json
schemas/v2/formal-worker-response.schema.json
src/mdcp/temporal/formal_worker.py
src/mdcp/temporal/formal_worker_protocol.py
```

Assert the independent tuple is ASCII ordered, contains exactly 47 unique paths, contains all four `FORMAL_WORKER_SOURCE_PATHS`, excludes the two implementation tests and generated evidence leaves, and equals production `SEARCH_SOURCE_PATHS`.

- [ ] **Step 2: Add RED identity mutations**

Reject missing, extra, duplicate, alias, wrong mode, wrong EOL, unknown substitution, copied index, `.git` dependency, zero digest, source/index digest alias, worker-inventory mismatch, launch-profile mismatch, and omission of either current design/plan. Require all 47 paths to be regular non-link/non-reparse files and every indexed logical path to be exact.

- [ ] **Step 3: Observe Task 8 RED**

```powershell
uv run pytest -q tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py -k "exact_ascii_ordered_47 or dedicated_worker_source or source_archive"
```

Expected: production still has the transitional 43-path inventory and lacks the dedicated-worker files/current documents.

- [ ] **Step 4: Implement the exact source migration**

Change only the protocol-owned tuple and directly related exact-count text/validation;
`search_identity.py` must continue importing and re-exporting the same tuple. Keep generated
receipt/index out of the source inventory. Keep tests outside the source inventory. Do not alter
historical documents.

- [ ] **Step 5: Prove source archive behavior with an external attributes profile**

Create the profile only under a new OS temporary root with exact contents:

```text
* text eol=lf
src/mdcp/temporal/firewall.py text eol=crlf
src/mdcp/temporal/run_evidence.py text eol=crlf
src/mdcp/temporal/runner.py text eol=crlf
src/mdcp/temporal/search_identity.py text eol=crlf
```

For `core.autocrlf=true`, `false`, and `input`, archive a temporary committed fixture, extract without `.git`, and require identical tar SHA-256 plus 47/47 source verifier equality. Do not create or modify tracked attributes. The two new Python files and both new schemas remain LF through the leading rule.

- [ ] **Step 6: Run Task 8 GREEN and all pre-source-commit gates**

```powershell
uv run pytest -q tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run pytest -q
uv run pytest -q tests/unit/temporal tests/integration/temporal tests/contract/temporal tests/security/temporal
uv run ruff check src/mdcp/temporal tests/unit/temporal tests/integration/temporal tests/security/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py src/mdcp/temporal/search_identity.py src/mdcp/temporal/formal_worker.py src/mdcp/temporal/formal_worker_protocol.py tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/unit/temporal/test_run_evidence.py tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_runner_synthetic.py tests/integration/temporal/test_formal_worker_process.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

Recompute protected blobs, both serving identities, H2 state, rejected evidence/custody hashes, remote `0`, and no HEAD tag. Run credential/private-path/publication scans; exclude only `tests/security/temporal/test_public_evidence_boundary.py` and `src/mdcp/temporal/evidence.py` from credential-pattern grep because they contain defensive patterns, never from tests or protected inventory.

- [ ] **Step 7: Review and commit Task 8**

Require independent Critical `0`, Important `0` across Tasks 1-8 and exact 47-path/source-archive proof. Stage only Task 8 allowlisted paths and commit:

```powershell
git commit -m "feat: bind dedicated worker search source"
```

This committed HEAD is the corrected source candidate, but it is not yet `SEARCH_SOURCE_COMMIT` because the rejected receipt/index remain tracked.

---

### Task 9: Fresh committed-tree completion review

**Files:**
- No modifications

**Interfaces:**
- Consumes: clean committed Tasks 2-8 and Task 1 private diagnostic preservation identity.
- Produces: approval to enter the destructive evidence topology only if every gate is fresh and Critical/Important are zero.

- [ ] **Step 1: Verify exact clean committed tree**

Require status clean, branch unchanged, remote `0`, no HEAD tag, only 25 allowlisted paths changed from `$planEntry`, all protected blobs identical, dependency lock identical, both serving identities identical, H2 `SEALED_NOT_LOADED`/`0`, rejected receipt/index/custody hashes identical, and Task 1 external diagnostic inventory valid.

- [ ] **Step 2: Run every fresh completion suite**

```powershell
uv run pytest -q
uv run pytest -q tests/unit/temporal tests/integration/temporal tests/contract/temporal tests/security/temporal
uv run pytest -q tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_worker_process.py
uv run pytest -q tests/integration/temporal/test_formal_runner_synthetic.py tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py
uv run pytest -q tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py tests/security/temporal/test_data_firewall.py
uv run pytest -q tests/integration/temporal/test_search_freeze_preflight.py
uv run ruff check src/mdcp/temporal tests/unit/temporal tests/integration/temporal tests/security/temporal
uv run ruff format --check src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py src/mdcp/temporal/runtime_guards.py src/mdcp/temporal/run_evidence.py src/mdcp/temporal/firewall.py src/mdcp/temporal/search_identity.py src/mdcp/temporal/formal_worker.py src/mdcp/temporal/formal_worker_protocol.py tests/unit/temporal/test_fit_ledger.py tests/unit/temporal/test_runtime_guards.py tests/unit/temporal/test_run_evidence.py tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_runner_synthetic.py tests/integration/temporal/test_formal_worker_process.py tests/integration/temporal/test_search_freeze_preflight.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_formal_runner_firewall.py tests/security/temporal/test_formal_run_authorization.py tests/security/temporal/test_public_evidence_boundary.py
uv lock --check
git diff --check
```

- [ ] **Step 3: Run process and identity audits**

Prove exactly one fixed worker launch, no retry, worker no PATH/subprocess/Git, supervisor pre/post Git ownership, 65,536/65,537 byte limits, 21,600/30-second timings, exact four worker sources, exact 47 search sources, source/index digest separation, no `.git` archive under all three autocrlf modes, closed five-file recovery, checked-close/no-clobber behavior, and no public disclosure.

- [ ] **Step 4: Obtain whole-range independent review**

Review Task 1 preservation/retirement and every Task 2-8 commit separately, then review their aggregate. Require Critical `0`, Important `0`; passing tests do not override a finding. Do not enter Task 10A otherwise.

---

### Task 10A: Commit the exact rejected-freeze `D/D` tombstone

**Files:**
- Delete from current tree: `evidence/public/v02/search/search-receipt.json`
- Delete from current tree: `evidence/public/v02/search/evidence-index.json`

**Interfaces:**
- Consumes: Task 9-approved clean source candidate and immutable rejected receipt/index/custody.
- Produces: a clean direct source commit with exactly two `D` entries and no current-tree public search freeze.

- [ ] **Step 1: Repeat all destructive-entry invariants**

Recompute the exact rejected hashes, custody, H2, protected blobs, 25-path range allowlist, clean state, remote `0`, no tag, and Task 9 review. Verify both evidence blobs are recoverable from `2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598` and current HEAD. If any differs, stop.

- [ ] **Step 2: Obtain pre-deletion review**

An independent reviewer must approve the exact two targets, historical recoverability, custody, direct-child topology, and no automatic rollback. Require Critical `0`, Important `0`.

- [ ] **Step 3: Delete only the two evidence leaves with apply_patch**

Use `apply_patch` to delete exactly the two tracked files. Do not use `Remove-Item`, Git restore/checkout, or path-generated deletion. Require `git diff --name-status` equals exactly:

```text
D evidence/public/v02/search/evidence-index.json
D evidence/public/v02/search/search-receipt.json
```

- [ ] **Step 4: Review staged tombstone and commit**

Stage only the two deletions, run `git diff --cached --check`, independently review the actual staged `D/D` diff Critical `0`, Important `0`, and commit:

```powershell
git commit -m "evidence: retire rejected dedicated worker freeze"
```

Require `git diff-tree --no-commit-id --name-status -r HEAD` is exactly the two `D` entries. This HEAD is `SEARCH_SOURCE_COMMIT`. Working tree must be clean. No P2 authorization exists.

---

### Task 10B: Create the single no-clobber `A/A` search refreeze

**Files:**
- Create once: `evidence/public/v02/search/search-receipt.json`
- Create once: `evidence/public/v02/search/evidence-index.json`

**Interfaces:**
- Consumes: exact clean Task 10A `SEARCH_SOURCE_COMMIT`, exact 47-path source, unchanged no-clobber freeze producer.
- Produces: canonical `A/A` direct-child freeze, new external custody identity, and terminal `SEARCH_FREEZE_PASS` without P2.

- [ ] **Step 1: Verify the exact source parent and absent destinations**

Require HEAD equals Task 10A, status clean, both evidence leaves absent, their parent safe, source count 47, source files regular/mode `100644`, remote `0`, no tag, protected identities unchanged, H2 sealed/0, and rejected custody still unchanged. Choose a new custody leaf whose destination does not exist.

- [ ] **Step 2: Run the existing freeze producer exactly once**

Invoke the approved `prepare-search-freeze` CLI once with a controller-provided UTC time and no alternate source/data inputs. This operation reads only source and frozen metadata; it must not open UCI/H1/H2 or create/consume formal authorization. Require exactly two new regular non-link files and no other worktree change.

- [ ] **Step 3: Independently verify and stage the pair**

Recompute canonical receipt/index bytes, their SHA-256 values, exact 47-entry inventory/digest, source commit equal Task 10A, H2 sealed/0, immutable frozen bindings, and no public violations. Stage both files and require:

```text
A evidence/public/v02/search/evidence-index.json
A evidence/public/v02/search/search-receipt.json
```

- [ ] **Step 4: Create new external custody before the commit**

Write one no-clobber external custody document binding source commit, receipt digest, index digest, 47-entry inventory digest, exact source/archive proof identities, H2 state, and `private_external_evidence/not_approved_for_publication`. Hash and independently reopen it. Do not place a private absolute path in public evidence.

- [ ] **Step 5: Review and commit the refreeze**

Obtain independent Critical `0`, Important `0` review of actual staged `A/A` bytes and new custody. Commit:

```powershell
git commit -m "evidence: freeze dedicated formal worker source"
```

Require the freeze commit is the direct child of Task 10A and its diff-tree is exactly two `A` entries.

- [ ] **Step 6: Verify live freeze and source archive**

Run `verify-search-freeze` with expected HEAD equal the new freeze commit and require `SEARCH_FREEZE_PASS`. Build source archives for `core.autocrlf=true`, `false`, and `input` with the exact external five-line attributes profile; require identical tar SHA-256, no `.git`, exact 47/47 inventory, and `SEARCH_SOURCE_INVENTORY_PASS` against the new externally anchored index digest.

- [ ] **Step 7: Run all final fresh gates**

Repeat every Task 9 test, Ruff, format, lock, diff, credential/private-path/publication, protected-byte, serving-identity, process, recovery, H2, source-archive, remote/tag, and custody gate from the committed tree. Require status clean.

- [ ] **Step 8: Obtain final independent review**

The reviewer must inspect Task 1, Tasks 2-8, Task 10A `D/D`, and Task 10B `A/A` separately, not only the net diff. Require Critical `0`, Important `0`, confirm no UCI/H1/H2/model/P2 action occurred, and confirm exact terminal state.

---

## Completion report

Report:

- owner-authorized plan entry and plan/design SHA-256;
- Task 1 private diagnostic preservation root, inventory digest, receipt/final-sums digests, source/destination equivalence, and clean retirement evidence;
- Tasks 2-8, Task 10A, and Task 10B commit SHAs and exact per-commit changed-file inventory;
- every real RED reason and targeted GREEN result;
- full CPU, protocol, process, temporal, contract, security, behavioral H2, publication, recovery, source-archive, identity, Ruff, format, lock, diff, credential, and private-path results;
- exact launch-profile, worker request/response schema, four-path worker inventory, 47-path source inventory, repository inventory, search receipt/index, and new custody digests;
- exact 80+0/4 synthetic state-machine counts and confirmation that no real fit/model/data run occurred;
- v0.1/v0.2 serving identities, `uv.lock`, protected-byte, rejected evidence, and rejected custody preservation;
- source-archive SHA-256 for all three autocrlf modes and no-`.git` result;
- supervisor pre/post Git ownership and worker no-PATH/no-subprocess proof;
- H2 `SEALED_NOT_LOADED`, loaded rows `0`;
- final branch, HEAD, parent topology, remote count `0`, no tag, and clean worktree;
- independent review Critical `0`, Important `0`; and
- P2 authorization absent, P2 formal run not started, Wave 4 not started.

Successful terminal state:

```text
DEDICATED_FORMAL_WORKER_PASS /
SEARCH_FREEZE_PASS /
P2_FORMAL_RUN_AUTHORIZATION_REQUIRED /
H2_SEALED_NOT_LOADED
```

Blocked terminal state:

```text
DEDICATED_FORMAL_WORKER_BLOCKED /
P2_FORBIDDEN /
H2_SEALED_NOT_LOADED
```

## Plan self-review checklist

- The plan is implementation-only and does not authorize P2, real authorization, data rows, model execution, Docker, GPU, network, remote, publication outside the two approved public search leaves, or Wave 4.
- The exact implementation allowlist is 25 paths; only the two evidence leaves may change in Tasks 10A/10B.
- The source inventory migration results in exactly 47 ASCII-ordered paths and excludes tests plus generated evidence leaves.
- The exact four worker source/schema paths are present once in both the worker and search inventories.
- Request, response, worker inventory, source inventory, repository inventory, index, authorization, marker, private container, terminal seal, and external anchors are acyclic; no identity contains itself.
- The supervisor alone observes Git HEAD/index/clean/full repository state, before and after the child; the worker claims only byte-level 47-path source observations.
- The worker inherits no PATH, imports no subprocess, launches no child, receives no callable, and is not described as a hostile same-user or OS network sandbox.
- Authorization marker durability precedes archive-content read, data/model import, row parse, estimator construction, fit, private bytes, and output publication.
- The pure state machine has exact 80+0/4 Wave 3 behavior and no I/O/model/process/publication interface.
- Timeout, crash, output overflow, malformed response, nonzero exit, and post-exit Git drift are deterministic, never retry, and never expose an unauthenticated fit count or terminal identity.
- Source and physical index digests have distinct meanings; the rejected alias is explicitly tested.
- Existing five-file semantics, external destinations, retained-handle no-clobber, checked close, physical terminal anchor, and recovery `UNKNOWN` rules remain.
- The three rejected diagnostic working bytes are externally preserved before their hunks are retired; no Git history rewrite occurs.
- Every source-changing task has an actual RED, targeted/full GREEN, independent Critical `0`/Important `0`, and one append-only commit.
- Task 9 gates the only destructive transition; Task 10A and Task 10B are separate `D/D` and `A/A` commits with no rollback or second attempt.
- Source archives reproduce without `.git` under `core.autocrlf=true`, `false`, and `input` using only the exact external five-line attributes profile.
- Rejected receipt/index/custody and all protected identities remain recoverable and unchanged.
- The final success point requires owner P2 authorization and does not begin P2.
