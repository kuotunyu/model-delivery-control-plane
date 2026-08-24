# MDCP v0.2 Wave 3 Search Freeze and Formal Development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an acyclic search identity, execute at most one owner-authorized 20-trial natural
development run, and either produce one replay-verified winner or preserve a terminal rejection.

**Architecture:** Search-affecting code is completed in a clean `SEARCH_SOURCE_COMMIT`. A child
`SEARCH_FREEZE_COMMIT` adds only a canonical receipt and approved evidence index. Formal execution
runs read-only at that freeze, writes private evidence outside Git, and exposes one sanitized
digest-only result index after execution.

**Tech Stack:** Existing temporal modules, scikit-learn CPU execution, RFC 8785/SHA-256, Pydantic,
subprocess read-only Git inspection, pytest, PowerShell orchestration.

## Global Constraints

- Entry requires W2 PASS and owner continuation approval.
- Formal execution additionally requires P2 owner approval bound to exact
  `SEARCH_FREEZE_COMMIT` and search-receipt digest.
- The receipt binds `SEARCH_SOURCE_COMMIT` and never contains its own freeze SHA.
- Parent-to-freeze diff is exactly two allowlisted JSON additions; no code/config/lock byte changes.
- Exactly 20×4 selection fits run at most once. Only rank-one provisional replay may add four fits.
- No second formal run, rank-two fallback, changed trial/seed/threshold, or result-driven edit.
- Repository is read-only during fitting. Private outputs are outside Git. H2 remains inaccessible.

---

## Wave 3 entry gate

Recompute all W2 handoff digests; run the complete W0–W2 tests; verify clean Git state and H2
`SEALED_NOT_LOADED`/`0`. A failing entry check blocks search-source construction.

### Task 3.1: Define search receipt and exact-parent preflight

**Files:**
- Create: `src/mdcp/temporal/search_identity.py`
- Create: `schemas/v2/search-receipt.schema.json`
- Create: `tests/unit/temporal/test_search_identity.py`
- Create: `tests/integration/temporal/test_search_freeze_preflight.py`

**Interfaces:**
- Consumes: canonical/digest helpers and read-only Git commands.
- Produces: `SearchReceipt`, `SearchFreezeCheck`,
  `build_search_receipt(inputs: SearchIdentityInputs) -> SearchReceipt`, and
  `verify_search_freeze(repository_root, receipt_path, evidence_index_path)
  -> SearchFreezeCheck`.

- [ ] **Step 1: Write failing acyclic/preflight tests**

~~~python
def test_receipt_has_source_but_no_freeze_sha() -> None:
    fields = set(SearchReceipt.model_fields)
    assert "search_source_commit" in fields
    assert "search_freeze_commit" not in fields

def test_preflight_rejects_code_change_between_source_and_freeze(git_fixture: Path) -> None:
    source, freeze = fixture_with_extra_change(git_fixture, "src/mdcp/temporal/trials.py")
    result = verify_search_freeze(git_fixture, RECEIPT, INDEX)
    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_FREEZE_DIFF_NOT_ALLOWLISTED",)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_search_identity.py tests/integration/temporal/test_search_freeze_preflight.py -q`

Expected: FAIL importing `SearchReceipt`.

- [ ] **Step 3: Implement canonical identity fields**

`SearchReceipt` has exactly: schema/canonicalization versions, `search_source_commit`,
approved-spec digest, dependency-lock digest, dataset contract/archive/development-row digests,
temporal schema/adapter/golden-vector digests, exact fold/trial/ranking/quality/statistical-code
digests, seed 2026, estimator threads 1, selection/replay/final/maximum fit limits
80/4/1/85, `h1_role="OBSERVED_DEVELOPMENT_ONLY"`,
`h2_status="SEALED_NOT_LOADED"`, `h2_loaded_rows=0`, and UTC creation time. It excludes
`search_freeze_commit` and private paths.

Preflight verifies: clean current checkout; HEAD has one parent; parent equals receipt source;
changed paths equal exactly
`evidence/public/v02/search/search-receipt.json` and
`evidence/public/v02/search/evidence-index.json`; all bound digests recompute; no executable/config/
lock/spec bytes differ; H2 state is sealed/zero.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_search_identity.py tests/integration/temporal/test_search_freeze_preflight.py -q`

Expected: PASS for valid child commit; wrong parent, placeholder SHA, self-SHA, extra path, dirty tree,
and changed code each fail with one sanitized code.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/search_identity.py schemas/v2/search-receipt.schema.json tests/unit/temporal/test_search_identity.py tests/integration/temporal/test_search_freeze_preflight.py
git commit -m "feat: add acyclic search identity"
~~~

### Task 3.2: Build the bounded formal runner and fit ledger

**Files:**
- Create: `src/mdcp/temporal/runner.py`
- Create: `src/mdcp/temporal/cli.py`
- Create: `tests/unit/temporal/test_fit_ledger.py`
- Create: `tests/integration/temporal/test_formal_runner_synthetic.py`

**Interfaces:**
- Consumes: folds/trials/completeness/evaluation/selection/search-preflight and bounded development
  loader.
- Produces: `FitPhase`, `FitLedger`, `TrialRunReceipt`,
  `DevelopmentRunReceipt`, `run_selection(context) -> DevelopmentRunReceipt`,
  `replay_provisional(context, provisional_id) -> ReplayResult`, and CLI commands
  `run-development`/`replay-provisional`.

- [ ] **Step 1: Write failing fit-budget/order tests**

~~~python
def test_fit_ledger_allows_only_80_plus_4_plus_1() -> None:
    ledger = FitLedger()
    for trial in EXACT_TRIAL_IDS:
        for fold in ("F1", "F2", "F3", "F4"):
            ledger.record(FitPhase.SELECTION, trial, fold)
    assert ledger.selection_count == 80
    with pytest.raises(FitBudgetError, match="selection fits frozen at 80"):
        ledger.record(FitPhase.SELECTION, "EXTRA", "F1")

def test_runner_completes_bad_quality_trials() -> None:
    receipt = run_selection(SYNTHETIC_CONTEXT_WITH_BAD_FIRST_FOLD)
    assert all(len(trial.fold_receipts) == 4 for trial in receipt.trials if trial.contract_valid)

def test_budget_exhaustion_is_terminal_unknown() -> None:
    receipt = run_selection(context_with_budget_probe(peak_bytes=4_294_967_297))
    assert receipt.status == "UNKNOWN/COMPUTE_BUDGET_EXCEEDED"
    assert receipt.retry_allowed is False
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py -q`

Expected: FAIL importing `FitLedger`.

- [ ] **Step 3: Implement serial deterministic execution**

Set BLAS/OpenMP/joblib thread variables to `1` before estimator import; reject GPU providers and
network/socket configuration. Iterate the exact trial IDs then F1–F4. For each fit, bind train/
validation identities, config, preprocessing, feature vectors, stable/candidate predictions,
completeness, metrics, and receipt digests. Contract invalidity records a fixed code and no
replacement; poor quality still completes four folds. The output root must resolve outside the
repository and the repository must be clean/read-only. Private receipts contain row identities and
predictions; the public model returns only counts/metrics/digests.

Use `time.monotonic_ns()` for the six-hour deadline. Read the operating system's process
high-water mark after every fit (Windows `GetProcessMemoryInfo.PeakWorkingSetSize`; Linux
`/proc/self/status:VmHWM`) through an injected probe. A missing authoritative probe, elapsed time
over `21_600` seconds, or peak resident bytes over `4_294_967_296` terminates the one run as
`UNKNOWN/COMPUTE_BUDGET_EXCEEDED`; it never starts a replacement fit or authorizes a rerun.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py -q`

Expected: PASS with 80 synthetic selection fits and no replay/final fit until requested.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/runner.py src/mdcp/temporal/cli.py tests/unit/temporal/test_fit_ledger.py tests/integration/temporal/test_formal_runner_synthetic.py
git commit -m "feat: add bounded temporal development runner"
~~~

### Task 3.3: Require an exact external owner authorization for formal execution

**Files:**
- Modify: `src/mdcp/temporal/search_identity.py`
- Modify: `src/mdcp/temporal/cli.py`
- Create: `schemas/v2/formal-run-authorization.schema.json`
- Create: `tests/security/temporal/test_formal_run_authorization.py`

**Interfaces:**
- Consumes: a private external `FormalRunAuthorization` supplied by the owner.
- Produces: `verify_formal_run_authorization(receipt, search_freeze_commit,
  search_receipt_sha256) -> AuthorizationCheck`.

- [ ] **Step 1: Write failing absent/mismatch/reuse tests**

~~~python
def test_formal_run_refuses_missing_authorization() -> None:
    result = cli(["run-development", "--search-receipt", str(RECEIPT)])
    assert result.exit_code == 3
    assert result.stdout == "FORMAL_RUN_NOT_AUTHORIZED\n"

def test_authorization_binds_one_freeze_and_is_single_start() -> None:
    guard = authorization_guard(AUTHORIZATION)
    guard.consume_start(EXACT_FREEZE, EXACT_RECEIPT_DIGEST)
    with pytest.raises(AuthorizationError, match="FORMAL_RUN_AUTHORIZATION_CONSUMED"):
        guard.consume_start(EXACT_FREEZE, EXACT_RECEIPT_DIGEST)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/security/temporal/test_formal_run_authorization.py -q`

Expected: FAIL because the CLI can start without the P2 receipt.

- [ ] **Step 3: Implement the external gate**

The private authorization schema contains exact search-freeze commit, receipt digest, protocol
digest, authorization ID, `authorized_action="ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN"`, UTC time, and
`consumed=false`. Atomic consume occurs before the bounded development loader opens. It is
Git-external, never logged raw, and cannot authorize replay of another candidate or H2.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/security/temporal/test_formal_run_authorization.py -q`

Expected: missing, wrong, dirty, reused, or differently bound authorization fails before any fit.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/search_identity.py src/mdcp/temporal/cli.py schemas/v2/formal-run-authorization.schema.json tests/security/temporal/test_formal_run_authorization.py
git commit -m "feat: gate formal temporal execution"
~~~

### Task 3.4: Create SEARCH_SOURCE_COMMIT and the receipt-only freeze child

**Files:**
- Create: `evidence/public/v02/search/search-receipt.json`
- Create: `evidence/public/v02/search/evidence-index.json`
- Test: `tests/integration/temporal/test_search_freeze_preflight.py`

**Interfaces:**
- Consumes: clean Task 3.3 HEAD and every W0–W3 bound digest.
- Produces: exact `SEARCH_SOURCE_COMMIT`, exact child `SEARCH_FREEZE_COMMIT`, and receipt digest.

- [ ] **Step 1: Run RED preflight before receipt/freeze**

~~~powershell
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
~~~

Expected: nonzero with only `SEARCH_RECEIPT_MISSING`; no fit starts.

- [ ] **Step 2: Freeze the clean source identity**

Run the complete W0–W3 source tests and `git diff --check`. Require clean status, then set
`SEARCH_SOURCE_COMMIT` to the full 40-character current HEAD. Do not create an empty/placeholder
commit and do not amend it.

- [ ] **Step 3: Generate the two canonical allowlisted files**

Use `build_search_receipt` with recomputed values. The evidence index lists logical private outputs
`trial-summary.json`, `qualification-report.json`, `ranking-report.json`,
`provisional-winner.json`, and `replay-report.json` with schema/evidence class, but no private path
or pre-run output digest. Verify RFC 8785 bytes and both JSON schemas.

- [ ] **Step 4: Commit the freeze and run GREEN**

~~~powershell
git add evidence/public/v02/search/search-receipt.json evidence/public/v02/search/evidence-index.json
git commit -m "chore: freeze v0.2 development search"
uv run python -m mdcp.temporal.cli verify-search-freeze --receipt evidence/public/v02/search/search-receipt.json --index evidence/public/v02/search/evidence-index.json
~~~

Expected: `SEARCH_FREEZE_PASS`; HEAD has exactly one parent equal to `SEARCH_SOURCE_COMMIT` and its
two-file diff contains no changed source/config/lock/spec byte.

- [ ] **Step 5: Record the P2 checkpoint without changing Git**

Report full source/freeze SHAs and receipt digest. Stop until the owner supplies the external
P2 authorization. Do not amend, backfill, regenerate, or add another file to the freeze commit.

### Task 3.5: Execute once, replay only the provisional winner, and preserve the result

**Files:**
- Create: `evidence/public/v02/development/result-index.json` (only after the owner-authorized execution)
- Test: `tests/security/temporal/test_public_evidence_boundary.py`
- External only: private run directory named by the authorization ID

**Interfaces:**
- Consumes: exact clean `SEARCH_FREEZE_COMMIT`, P2 authorization, bounded UCI development loader.
- Produces: 20-trial summary, qualification/ranking receipt, zero or one provisional winner,
  zero or one replay, terminal `SelectionDecision`, and sanitized public result index.

- [ ] **Step 1: Prove RED while P2 authorization is absent**

Run the exact future command without `--authorization`:

~~~powershell
uv run python -m mdcp.temporal.cli run-development --archive-env MDCP_UCI_ARCHIVE --private-output-env MDCP_V02_EVIDENCE_ROOT --search-receipt evidence/public/v02/search/search-receipt.json
~~~

Expected: exit 3, `FORMAL_RUN_NOT_AUTHORIZED`, fit ledger count 0, no output directory.

- [ ] **Step 2: Consume P2 and execute exactly 80 selection fits**

After owner authorization, run the same command with
`--authorization-env MDCP_FORMAL_RUN_AUTHORIZATION`. Expected outcomes are:

- no qualified trial: `NO_ELIGIBLE_CANDIDATE`, 80 fits, no replay, preserve and stop;
- one or more qualified trials: one provisional winner and no final winner yet;
- any contract/budget `UNKNOWN`: preserve complete reason evidence and stop.

The command is never rerun after its authorization is consumed.

- [ ] **Step 3: Replay only the bound provisional winner**

If and only if Step 2 produced one provisional winner, run:

`uv run python -m mdcp.temporal.cli replay-provisional --private-output-env MDCP_V02_EVIDENCE_ROOT --search-receipt evidence/public/v02/search/search-receipt.json --provisional-receipt-env MDCP_V02_PROVISIONAL_RECEIPT`

Expected: exactly four new fits for the same trial/config/folds. Digest equality PASS yields one
final development winner. FAIL/UNKNOWN yields `UNKNOWN/NO_ELIGIBLE_CANDIDATE`. No command accepts a
rank-two ID or search retry.

- [ ] **Step 4: Run GREEN by building and verifying the sanitized result index**

Create `result-index.json` from aggregate metrics, reason codes, fit counts, terminal status, and
private bundle inventory digest. It contains no row, prediction, label, private path, raw exception,
or H2 fact beyond sealed/zero. Run:

`uv run pytest tests/security/temporal/test_public_evidence_boundary.py -q && uv run python -m mdcp.temporal.cli verify-development-result --index evidence/public/v02/development/result-index.json`

Expected: PASS and fit count is 80 or 84, never another value.

- [ ] **Step 5: Commit the sanitized index and stop on non-PASS**

~~~powershell
git add evidence/public/v02/development/result-index.json
git commit -m "docs: record v0.2 development result"
~~~

If terminal status is not one replay-verified final winner, stop the entire suite with preserved
evidence. A development PASS still is not H2 or promotion evidence.

## Wave 3 completion gate

- Search source/freeze preflight PASSes and remains acyclic.
- Exactly one owner-authorized formal selection run occurred.
- Fit ledger is 80 with no winner, or 84 with exactly one replay target.
- Result is either a single replay-verified final development winner or terminal preserved
  `NO_ELIGIBLE_CANDIDATE`. No fallback exists.
- H2 remains `SEALED_NOT_LOADED`/`0`.

**Immutable handoff on PASS:** source/freeze/receipt identities, complete external trial evidence,
sanitized result-index digest, selected trial/config, and replay digests.

**Owner checkpoint:** before any final refit, report W3 evidence and obtain P3. A terminal rejection
ends work; it does not enter W4.
