# MDCP v0.2 Wave 2 Rolling Development Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement exact rolling folds, 20 bounded trial factories, converter qualification,
denominator-preserving accounting, frozen statistics, and cycle-free selection without running the
formal development search.

**Architecture:** Pure modules turn W1 development rows into immutable row inventories, fold views,
trial pipelines, completeness receipts, quality reports, and selection decisions. The existing
`cluster_bootstrap_ratios` kernel is reused rather than forked. Integration uses only deterministic
synthetic development rows.

**Tech Stack:** pandas, NumPy, scikit-learn RandomForest/Ridge/GradientBoosting, ONNX/skl2onnx,
Pydantic v2, existing validator/bootstrap helpers, pytest, Hypothesis.

## Global Constraints

- Entry requires W1 PASS and owner continuation approval.
- This wave may fit tiny deterministic synthetic models for converter tests; it may not execute the
  natural 20-trial development run or evaluate actual H1 rows.
- Folds, families, parameters, features, seeds, thread count, thresholds, bootstrap, subgroups, and
  fit ceiling are loaded from the W0 canonical protocol and cannot be inferred from results.
- Adapter and both prediction streams require 100% identity completeness; development labels also
  require 100%.
- Poor quality completes all four folds. Only contract invalidity may invalidate early.
- No H2 capability, network, GPU, paid API, Docker socket, or Git-history write is present.

---

## Wave 2 entry gate

Recompute the W1 contract receipt and verify its H2 firewall, 18-field schema, 13,003-row logical
development identity, and separate admission counters before creating any development module.

### Task 2.1: Materialize four rolling folds and authoritative row inventories

**Files:**
- Create: `src/mdcp/temporal/folds.py`
- Create: `tests/unit/temporal/test_folds.py`

**Interfaces:**
- Consumes: `DevelopmentPartitions`, protocol `folds`, `adapt_v2`.
- Produces: `FoldSpec`, `SourceRowIdentity`, `FoldRows`,
  `load_fold_specs(protocol) -> tuple[FoldSpec, ...]`, and
  `materialize_folds(rows, specs) -> tuple[FoldRows, ...]`.

- [ ] **Step 1: Write failing chronology and identity tests**

~~~python
def test_four_folds_are_exact_and_disjoint() -> None:
    folds = materialize_folds(synthetic_development_frame(), EXACT_FOLD_SPECS)
    assert [fold.spec.fold_id for fold in folds] == ["F1", "F2", "F3", "F4"]
    assert folds[0].train.index.min() == pd.Timestamp("2011-01-01")
    assert folds[-1].validation.index.max() < pd.Timestamp("2012-07-01")
    validation_ids = [identity.request_id for fold in folds for identity in fold.inventory]
    assert len(validation_ids) == len(set(validation_ids))
    assert all(fold.train.index.max() < fold.validation.index.min() for fold in folds)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_folds.py -q`

Expected: FAIL importing `mdcp.temporal.folds`.

- [ ] **Step 3: Implement half-open whole-day folds**

`FoldSpec` validates exact midnight boundaries and `train_end == validation_start`.
`materialize_folds` sorts by `(local_date, hr, original stable source order)`, rejects duplicate
timestamp/request identities, selects half-open intervals, proves every calendar day belongs wholly
to one side, and creates one `SourceRowIdentity` per validation row before adaptation. Identity
material is `fold_id/request_id/local timestamp/source position` canonicalized and SHA-256 bound;
receipts retain only aggregate hashes/counts.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_folds.py -q`

Expected: PASS for exact dates, no overlap, expanding history, whole-day grouping, and duplicate
rejection.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/folds.py tests/unit/temporal/test_folds.py
git commit -m "feat: add exact rolling development folds"
~~~

### Task 2.2: Implement the exact control and 19 candidate factories

**Files:**
- Create: `src/mdcp/temporal/trials.py`
- Create: `tests/unit/temporal/test_trials.py`
- Create: `tests/unit/temporal/test_preprocessing.py`

**Interfaces:**
- Consumes: canonical protocol, `FoldRows`, v1/v2 feature columns.
- Produces: `TrialFamily`, `TrialSpec`,
  `load_trial_specs(protocol) -> tuple[TrialSpec, ...]`,
  `training_rows_for_trial(spec, fold) -> DataFrame`, and
  `build_estimator(spec) -> sklearn.pipeline.Pipeline`.

- [ ] **Step 1: Write failing exact-inventory/factory tests**

~~~python
def test_exact_trial_inventory() -> None:
    specs = load_trial_specs(PROTOCOL)
    assert len(specs) == 20
    assert sum(spec.final_eligible for spec in specs) == 19
    assert specs[0].trial_id == "CTRL-01"
    assert all(spec.random_state in (None, 2026) for spec in specs)
    assert all(spec.estimator_threads == 1 for spec in specs)

def test_recency_never_pads_from_future(f4: FoldRows) -> None:
    rows = training_rows_for_trial(spec("REC-180-L4"), f4)
    assert rows.index.min() == pd.Timestamp("2011-10-03")
    assert rows.index.max() < pd.Timestamp("2012-04-01")
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_trials.py tests/unit/temporal/test_preprocessing.py -q`

Expected: FAIL importing `TrialSpec`.

- [ ] **Step 3: Implement the four exact families**

- `CTRL-01`: original fields 1–11, full expanding train, Random Forest 32 trees, depth 8,
  leaf 4, `max_features=1.0`, bootstrap true, seed 2026, one job, not eligible.
- `REC`: fields 1–11 plus 13–18, field 12 excluded; exact trailing 180/270/365 complete days;
  Random Forest 64 trees, depth 8, leaf 4/12, `max_features=1.0`, bootstrap true.
- `STAT`: all 18 fields; fixed categories
  `{1..4},{1..12},{0..23},{0,1},{0..6},{0,1},{1..4}`; fields 8–18 standardized with
  training mean/population standard deviation; Ridge alpha 0.1/1/10/100/1000, `lsqr`,
  intercept true, `tol=1e-8`, `max_iter=10000`.
- `NL`: fields 1–11 plus 13–18; Gradient Boosting estimators 64/128, rate 0.03/0.07,
  depth 2/3, leaf 8, squared error, subsample 1.0, max features None, seed 2026.

Every family fits raw `cnt` only after features are materialized and applies
`max(0, prediction)` identically in native/ONNX paths. Zero-variance STAT continuous input is a
fixed contract error, not silently scaled.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_trials.py tests/unit/temporal/test_preprocessing.py -q`

Expected: PASS; config mutation, discovered categories, field 12 in REC/NL, and future padding fail.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/trials.py tests/unit/temporal/test_trials.py tests/unit/temporal/test_preprocessing.py
git commit -m "feat: implement bounded temporal trial families"
~~~

### Task 2.3: Qualify family conversion and freeze the v2 operator policy

**Files:**
- Create: `configs/policy/onnx-operators-v2.json`
- Create: `configs/policy/validation-v2.json`
- Modify: `src/mdcp/validator/onnx_checks.py`
- Create: `tests/integration/temporal/test_family_converter_contract.py`
- Modify: `tests/unit/validator/test_onnx_checks.py`

**Interfaces:**
- Consumes: `build_estimator`, synthetic rows, existing `validate_onnx`.
- Produces: `validate_onnx(path, policy, expected_inputs=None) -> OnnxValidationResult` and the
  hand-reviewed sorted v2 operator allowlist.

- [ ] **Step 1: Write failing converter/input-policy tests**

For one exact representative per CTRL/REC/STAT/NL family, fit on deterministic synthetic
development rows, export twice, and assert deterministic graph bytes, 18 or declared subset input
names/shapes, finite non-negative outputs, opset 18, and native/ORT parity. Pass a reordered input
list and assert `VAL_ONNX_INVALID`.

~~~python
@pytest.mark.parametrize("trial_id", [
    "CTRL-01", "REC-180-L4", "STAT-A1", "NL-E64-R0.03-D2",
])
def test_family_converter_is_deterministic_and_allowlisted(trial_id, tmp_path) -> None:
    first = convert_synthetic_trial(trial_id, tmp_path / "first.onnx")
    second = convert_synthetic_trial(trial_id, tmp_path / "second.onnx")
    assert first.onnx_sha256 == second.onnx_sha256
    assert set(first.operators) <= set(V2_OPERATOR_ALLOWLIST)
    assert first.parity_allclose is True
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/integration/temporal/test_family_converter_contract.py tests/unit/validator/test_onnx_checks.py -q`

Expected: FAIL because v2 policies and `expected_inputs` enforcement are absent.

- [ ] **Step 3: Freeze the reviewed converter boundary**

The v2 operator file is sorted and contains only:

~~~json
[
  "Add", "ArrayFeatureExtractor", "Cast", "Concat", "Identity",
  "LinearRegressor", "MatMul", "OneHotEncoder", "Relu", "Reshape",
  "Scaler", "TreeEnsembleRegressor"
]
~~~

The validation file retains the v1 64 MiB/4,096-node/opset 13–18 limits and provides all 18 smoke
inputs. Extend `validate_onnx` to compare actual input names/order/shapes to the caller-supplied
expected inventory. The test records observed operators per family and fails if the union is not a
subset of the reviewed list; code may never auto-add an observed operator.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/integration/temporal/test_family_converter_contract.py tests/unit/validator/test_onnx_checks.py -q`

Expected: PASS for all families with zero unreviewed operators.

- [ ] **Step 5: Commit**

~~~powershell
git add configs/policy/onnx-operators-v2.json configs/policy/validation-v2.json src/mdcp/validator/onnx_checks.py tests/integration/temporal/test_family_converter_contract.py tests/unit/validator/test_onnx_checks.py
git commit -m "feat: freeze temporal onnx policy"
~~~

### Task 2.4: Enforce denominator-preserving completeness

**Files:**
- Create: `src/mdcp/temporal/completeness.py`
- Create: `tests/unit/temporal/test_completeness.py`
- Create: `tests/property/temporal/test_completeness_properties.py`

**Interfaces:**
- Consumes: `SourceRowIdentity`, adapter outcomes, stable/candidate outcomes, labels.
- Produces: `AdapterOutcome`, `PredictionOutcome`, `LabelOutcome`,
  `CompletenessReceipt`, and
  `assemble_development_pairs(inventory, adapters, stable, candidate, labels)
  -> tuple[CompletenessReceipt, tuple[PairedQualityRow, ...]]`.

- [ ] **Step 1: Write failing missing/duplicate/masquerade properties**

~~~python
@pytest.mark.parametrize("stream", ["adapter", "stable", "candidate"])
def test_one_missing_identity_makes_whole_trial_unknown(stream: str) -> None:
    receipt, rows = assemble_with_one_missing(stream)
    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.source_count == 240

def test_prediction_failure_cannot_be_counted_as_missing_label() -> None:
    receipt, _ = assemble_with_candidate_failure(reason="INVALID_RESPONSE")
    assert receipt.candidate_failure_count == 1
    assert receipt.label_missing_count == 0
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_completeness.py tests/property/temporal/test_completeness_properties.py -q`

Expected: FAIL importing `CompletenessReceipt`.

- [ ] **Step 3: Implement identity-first accounting**

Validate exact set equality and uniqueness against the immutable source inventory before calculating
any metric. Record successes, failures, missing IDs, duplicate IDs, invalid outputs, and fixed
reason-code counts separately for adapter, stable, candidate, and labels. Development requires
adapter/stable/candidate/label rates all exactly 1.0. Any adapter/prediction problem returns
`UNKNOWN` and an empty pair tuple; it is never converted to label missingness. Values must be finite
and non-negative.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_completeness.py tests/property/temporal/test_completeness_properties.py -q`

Expected: PASS across generated missing/duplicate/order/failure cases; no property shrinks source
count.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/completeness.py tests/unit/temporal/test_completeness.py tests/property/temporal/test_completeness_properties.py
git commit -m "feat: preserve temporal quality denominators"
~~~

### Task 2.5: Implement fold/pooled metrics and qualification

**Files:**
- Create: `src/mdcp/temporal/evaluation.py`
- Create: `tests/unit/temporal/test_evaluation_v2.py`
- Create: `tests/property/temporal/test_quality_properties.py`

**Interfaces:**
- Consumes: complete `PairedQualityRow` sets, W0 quality policy, existing
  `cluster_bootstrap_ratios`.
- Produces: `FoldQualityReport`, `DevelopmentQualityReport`, `QualificationResult`,
  `evaluate_fold`, `evaluate_pooled`, and `qualify_trial`.

- [ ] **Step 1: Write failing threshold/cross-fold tests**

~~~python
def test_qualification_requires_all_frozen_conditions() -> None:
    result = qualify_trial(report_with(
        pooled_point=0.96, pooled_ucb=0.97,
        subgroup_points=all_values(1.05), subgroup_ucbs=all_values(1.05),
        fold_points=(0.99, 1.00, 0.98, 1.04),
    ))
    assert result.qualified is True

def test_one_fold_only_win_does_not_qualify() -> None:
    result = qualify_trial(report_with(fold_points=(0.80, 1.01, 1.02, 1.03)))
    assert result.qualified is False
    assert "FOLD_STABILITY" in result.reason_codes
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_evaluation_v2.py tests/property/temporal/test_quality_properties.py -q`

Expected: FAIL importing `qualify_trial`.

- [ ] **Step 3: Implement unchanged statistics and gates**

Call the existing bootstrap with seven exact groups, 2,000 replicates, seed 2026, index 1,899.
Report overall and every subgroup point/UCB/`n` per fold and pooled. Qualification requires:
100% development accounting; every subgroup `n>=100` per fold and pooled; pooled overall
point/UCB `<=0.97`; pooled subgroup point/UCB `<=1.05`; every fold overall point `<=1.05`;
at least three fold overall points `<=1.00`; and all lineage/converter/evidence checks PASS.
Threshold failure is FAIL; missing/invalid/insufficient/budget evidence is UNKNOWN.

- [ ] **Step 4: Run GREEN and bootstrap regression**

Run: `uv run pytest tests/unit/policy/test_cluster_bootstrap.py tests/unit/temporal/test_evaluation_v2.py tests/property/temporal/test_quality_properties.py -q`

Expected: PASS; the existing bootstrap vector remains byte-for-byte reproducible.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/evaluation.py tests/unit/temporal/test_evaluation_v2.py tests/property/temporal/test_quality_properties.py
git commit -m "feat: implement temporal development quality gate"
~~~

### Task 2.6: Implement qualification-first ranking and sole replay decisions

**Files:**
- Create: `src/mdcp/temporal/selection.py`
- Create: `tests/unit/temporal/test_selection.py`
- Create: `tests/integration/temporal/test_synthetic_development_dry_run.py`

**Interfaces:**
- Consumes: 19 `QualificationResult` values and later one `ReplayResult`.
- Produces: `RankedTrial`, `ProvisionalWinner`, `ReplayResult`, `SelectionDecision`,
  `rank_qualified(results) -> ProvisionalWinner | None`, and
  `finalize_selection(provisional, replay) -> SelectionDecision`.

- [ ] **Step 1: Write failing order/tie/fallback tests**

~~~python
def test_ranking_uses_exact_lexicographic_key() -> None:
    provisional = rank_qualified(QUALIFIED_RESULTS)
    assert provisional.trial_id == expected_min_by(
        "pooled_ucb95", "worst_fold_point", "worst_subgroup_ucb95",
        family_order=("STAT", "REC", "NL"), "ascii_trial_id",
    )

@pytest.mark.parametrize("verdict", ["FAIL", "UNKNOWN"])
def test_replay_failure_has_no_rank_two_fallback(verdict: str) -> None:
    decision = finalize_selection(PROVISIONAL, ReplayResult(verdict=verdict, digests=()))
    assert decision.status == "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
    assert decision.final_winner is None
    assert decision.retry_allowed is False
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_selection.py tests/integration/temporal/test_synthetic_development_dry_run.py -q`

Expected: FAIL importing `rank_qualified`.

- [ ] **Step 3: Implement the acyclic selection reducer**

Filter final-eligible trials by `qualified is True` before ranking. Exclude `CTRL-01`. Rank by pooled
UCB95, worst fold point, worst subgroup UCB95, static family order STAT/REC/NL, then ASCII ID.
Return exactly one provisional winner. `finalize_selection` accepts a replay for that same ID only;
PASS creates one final winner, while FAIL/UNKNOWN creates the terminal no-eligible decision.
Reject a second replay, different ID, rerank request, altered tie key, or fallback list.

- [ ] **Step 4: Run GREEN and synthetic dry run**

Run:
`uv run pytest tests/unit/temporal tests/property/temporal tests/integration/temporal/test_synthetic_development_dry_run.py -q`

Expected: PASS; dry run exercises four folds and selection on generated data but is labeled
`synthetic_test` and does not count toward the 85 formal fits.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/selection.py tests/unit/temporal/test_selection.py tests/integration/temporal/test_synthetic_development_dry_run.py
git commit -m "feat: enforce replay-gated temporal selection"
~~~

## Wave 2 completion gate

- Exact fold/trial/family/preprocessing/operator/completeness/statistics/selection tests PASS.
- Trial inventory is 20/19; synthetic converter fits are labeled and excluded from the formal ledger.
- Existing bootstrap code and v1 tests still PASS.
- No natural H1 evaluation, formal fit, real H2 access, repository receipt, or external publication
  occurred.

**Immutable handoff:** fold/trial/operator-policy/statistical/completeness/ranking code and digest
inventory plus the synthetic dry-run receipt.

**Owner checkpoint:** report `V02_W2_PROTOCOL_PASS` and stop for P1 continuation approval. W3 code
may be implemented only after approval; the formal run has its own P2 approval.
