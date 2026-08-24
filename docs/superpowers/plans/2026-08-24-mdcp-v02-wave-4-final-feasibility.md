# MDCP v0.2 Wave 4 Final Refit, ONNX, and Deployment Feasibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refit the sole replay-verified winner once on 2011+observed-H1, export and validate its
exact ONNX artifact, and prove CPU serving/resource feasibility without touching H2.

**Architecture:** The selected immutable `TrialSpec` drives a one-fit finalizer. Existing ONNX,
predictor, validator, load-probe, cgroup, MLflow, and offline-bundle code is extended locally rather
than replaced. All measured model bytes and private receipts remain outside Git; only sanitized
indexes are committed.

**Tech Stack:** scikit-learn, pandas/NumPy, skl2onnx/ONNX Runtime, MLflow local store, FastAPI,
Docker Compose, existing validator and cgroup/load probes, pytest.

## Global Constraints

- Entry requires W3 replay PASS, exactly one final development winner, and P3 owner authorization.
- Final fit count is exactly one; cumulative maximum becomes 85.
- Final training interval is exactly `[2011-01-01 00:00, 2012-07-01 00:00)`.
- REC uses its exact trailing window ending `2012-07-01`; STAT/NL use the full interval.
- No parameter, feature, preprocessing, recency, calibration, seed, or candidate changes.
- ONNX parity is `rtol=1e-5`/`atol=1e-5`; ONNX size limit is 64 MiB.
- Serving gate remains 1.0 CPU, 384 MiB hard limit, cgroup peak `<=256 MiB`, 200 warmups,
  2,000 requests, 80 admissions/s, 32 in flight, zero errors, nearest-rank p95 `<=25 ms`.
- H2 remains sealed/unloaded; all feasibility inputs are development or synthetic.

---

## Wave 4 entry gate

Verify W3 result-index/private bundle equivalence, source/freeze preflight, 80+4 fit ledger,
provisional/replay digest equality, clean Git state, and exact P3 authorization. Any mismatch stops
before the final fit.

### Task 4.1: Refit the sole winner once and bind final lineage

**Files:**
- Create: `src/mdcp/temporal/finalize.py`
- Modify: `src/mdcp/temporal/cli.py`
- Create: `tests/unit/temporal/test_finalize.py`
- Create: `tests/integration/temporal/test_final_refit_synthetic.py`

**Interfaces:**
- Consumes: `SelectionDecision.final_winner`, `TrialSpec`, 13,003 development rows, `FitLedger`.
- Produces: `FinalTrainingReceipt` and
  `refit_final_winner(winner, development_rows, ledger) -> tuple[Pipeline, FinalTrainingReceipt]`;
  CLI command `refit-final` writes native model/receipt only to the private external root.

- [ ] **Step 1: Write failing lineage/budget tests**

~~~python
def test_final_refit_uses_winner_and_one_fit_only() -> None:
    model, receipt = refit_final_winner(WINNER, synthetic_development_frame(), LEDGER_AT_84)
    assert receipt.trial_id == WINNER.trial_id
    assert receipt.fit_count == 1
    assert receipt.cumulative_fit_count == 85
    assert receipt.training_end == "2012-07-01T00:00:00"

def test_non_replay_verified_candidate_is_rejected() -> None:
    with pytest.raises(FinalizationError, match="FINAL_WINNER_REQUIRED"):
        refit_final_winner(PROVISIONAL_ONLY, ROWS, LEDGER_AT_84)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_finalize.py tests/integration/temporal/test_final_refit_synthetic.py -q`

Expected: FAIL importing `refit_final_winner`.

- [ ] **Step 3: Implement one immutable refit**

Verify the selection/replay/config/source/dependency digests first. Derive REC start as
`2012-07-01 - {180,270,365} complete days`; otherwise select every development row. Reuse
`build_estimator` without mutation, record exact training row/preprocessing/config/feature/source
digests, and consume the final fit-ledger slot before `Pipeline.fit`. Reject a second call or any
ledger count other than 84.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_finalize.py tests/integration/temporal/test_final_refit_synthetic.py -q`

Expected: PASS; synthetic finalizer is deterministic and no H2-capable type is imported.

- [ ] **Step 5: Commit, verify clean source, and execute the one authorized final fit**

~~~powershell
git add src/mdcp/temporal/finalize.py src/mdcp/temporal/cli.py tests/unit/temporal/test_finalize.py tests/integration/temporal/test_final_refit_synthetic.py
git commit -m "feat: add replay-bound final refit"
uv run python -m mdcp.temporal.cli refit-final --archive-env MDCP_UCI_ARCHIVE --selection-receipt-env MDCP_V02_SELECTION_RECEIPT --private-output-env MDCP_V02_EVIDENCE_ROOT
~~~

Expected: clean committed source before execution; `FINAL_REFIT_PASS fits=85`; one external native
model and canonical final-training receipt. The authorization/fit ledger prevents a second call.

### Task 4.2: Export exact 18-input ONNX and prove native/runtime parity

**Files:**
- Modify: `src/mdcp/workload/onnx_export.py`
- Modify: `src/mdcp/predictor/runtime.py`
- Modify: `src/mdcp/temporal/cli.py`
- Modify: `tests/unit/workload/test_onnx_export.py`
- Modify: `tests/integration/test_onnx_parity.py`
- Create: `tests/integration/temporal/test_final_onnx_parity.py`

**Interfaces:**
- Consumes: final pipeline, W2 operator policy, temporal feature names/vectors.
- Produces: `export_temporal_pipeline_onnx(pipeline, path, input_names) -> OnnxReceipt`,
  `TemporalOnnxPredictor`, `ParityReceipt`, and CLI command `export-final-onnx`.

- [ ] **Step 1: Write failing schema/parity/tamper tests**

~~~python
def test_temporal_onnx_has_exact_named_inputs(final_pipeline, tmp_path) -> None:
    receipt = export_temporal_pipeline_onnx(
        final_pipeline, tmp_path / "model.onnx", TEMPORAL_FEATURE_COLUMNS
    )
    assert receipt.input_names == TEMPORAL_FEATURE_COLUMNS
    assert receipt.input_shapes == ((None, 1),) * 18
    assert receipt.output_shape == (None, 1)
    assert receipt.byte_size <= 64 * 1024 * 1024

def test_native_and_ort_are_within_frozen_tolerance(parity) -> None:
    assert parity.rtol == parity.atol == 1e-5
    assert parity.allclose is True
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/integration/temporal/test_final_onnx_parity.py -q`

Expected: FAIL because temporal export/runtime classes do not exist.

- [ ] **Step 3: Extend, do not fork, existing export/runtime**

Parameterize the existing exporter input names; keep opset 18 and deterministic doc-string cleanup.
`TemporalOnnxPredictor` binds model digest, expected 18-name inventory, CPU provider only, adapter
schema digest, and non-negative output contract. Compare final native/ORT predictions across all W1
golden vectors and a deterministic development sample; record max absolute error and digests.
Reordered inputs, graph tamper, unexpected provider, negative/non-finite output, or tolerance failure
is blocking.

- [ ] **Step 4: Run GREEN with v1 regressions**

Run:
`uv run pytest tests/unit/workload/test_onnx_export.py tests/integration/test_onnx_parity.py tests/integration/temporal/test_final_onnx_parity.py -q`

Expected: v1 and v2 parity suites PASS.

- [ ] **Step 5: Commit and export the exact external final artifact once**

~~~powershell
git add src/mdcp/workload/onnx_export.py src/mdcp/predictor/runtime.py src/mdcp/temporal/cli.py tests/unit/workload/test_onnx_export.py tests/integration/test_onnx_parity.py tests/integration/temporal/test_final_onnx_parity.py
git commit -m "feat: export temporal candidate onnx"
uv run python -m mdcp.temporal.cli export-final-onnx --native-model-env MDCP_V02_NATIVE_MODEL --final-receipt-env MDCP_V02_FINAL_TRAINING_RECEIPT --operator-policy configs/policy/onnx-operators-v2.json --private-output-env MDCP_V02_EVIDENCE_ROOT
~~~

Expected: `FINAL_ONNX_PASS` with ONNX/parity digests, size, opset, operators, exact 18-input schema,
and maximum absolute error in the external receipt.

### Task 4.3: Bind v2 descriptor, MLflow numeric lineage, and validator evidence

**Files:**
- Modify: `src/mdcp/contracts/release.py`
- Modify: `src/mdcp/workload/mlflow_lineage.py`
- Modify: `src/mdcp/validator/service.py`
- Modify: `src/mdcp/temporal/cli.py`
- Create: `schemas/v2/temporal-artifact-descriptor.schema.json`
- Create: `tests/unit/contracts/test_temporal_artifact_descriptor.py`
- Create: `tests/integration/temporal/test_temporal_mlflow_lineage.py`
- Create: `tests/integration/validator/test_temporal_artifact.py`

**Interfaces:**
- Consumes: final training, ONNX, parity, contract, search, and development receipts.
- Produces: `TemporalArtifactDescriptor`, `TemporalMLflowVersionSnapshot`,
  `record_temporal_mlflow_version(...)`, existing `ValidatorService` checks over v2 inventory, and
  CLI command `register-final-artifact`.

- [ ] **Step 1: Write failing identity-chain tests**

~~~python
def test_descriptor_binds_temporal_identity_chain(descriptor) -> None:
    assert descriptor.schema_version == "artifact-descriptor/v2"
    assert descriptor.onnx.sha256 == descriptor.model_sha256
    assert descriptor.temporal_schema_id == "mdcp.temporal-features.v0.2"
    assert descriptor.search_receipt_sha256 == SEARCH_RECEIPT_DIGEST
    assert descriptor.replay_receipt_sha256 == REPLAY_DIGEST
    assert descriptor.h2_loaded_rows == 0
~~~

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/unit/contracts/test_temporal_artifact_descriptor.py tests/integration/temporal/test_temporal_mlflow_lineage.py tests/integration/validator/test_temporal_artifact.py -q`

Expected: FAIL because v2 descriptor/lineage types are absent.

- [ ] **Step 3: Extend versioned contracts**

Keep `ArtifactDescriptor` v1 unchanged. The v2 descriptor adds selected trial/config, search source/
freeze/receipt, fold/trial summary, final training, temporal schema/adapter/golden-vector,
preprocessing, parity, operator-policy, and development-report digests. MLflow tags bind those
digests to one numeric version and run-local immutable artifact URI. Validator checks exact 18
inputs, reviewed operators, max graph/size, finite output, and all descriptor digests. No alias or
`latest` is accepted.

- [ ] **Step 4: Run GREEN**

Run:
`uv run pytest tests/unit/contracts/test_artifact_descriptor.py tests/unit/contracts/test_temporal_artifact_descriptor.py tests/integration/temporal/test_temporal_mlflow_lineage.py tests/integration/validator/test_temporal_artifact.py -q`

Expected: PASS; each tampered link fails closed.

- [ ] **Step 5: Commit and register/validate the exact external bytes**

~~~powershell
git add src/mdcp/contracts/release.py src/mdcp/workload/mlflow_lineage.py src/mdcp/validator/service.py src/mdcp/temporal/cli.py schemas/v2/temporal-artifact-descriptor.schema.json tests/unit/contracts/test_temporal_artifact_descriptor.py tests/integration/temporal/test_temporal_mlflow_lineage.py tests/integration/validator/test_temporal_artifact.py
git commit -m "feat: bind temporal artifact lineage"
uv run python -m mdcp.temporal.cli register-final-artifact --private-output-env MDCP_V02_EVIDENCE_ROOT --tracking-root-env MDCP_V02_MLFLOW_ROOT --validation-policy configs/policy/validation-v2.json --operator-policy configs/policy/onnx-operators-v2.json
~~~

Expected: `TEMPORAL_ARTIFACT_PASS` with one numeric MLflow version, run-bound immutable URI,
descriptor digest, and validator receipt for the same ONNX bytes.

### Task 4.4: Prove isolated CPU, load, latency, and cgroup memory feasibility

**Files:**
- Create: `src/mdcp/temporal/feasibility.py`
- Create: `compose.temporal-feasibility.yaml`
- Modify: `docker/predictor.Dockerfile`
- Create: `tests/contract/temporal/test_feasibility_compose.py`
- Create: `tests/integration/temporal/test_temporal_load_gate.py`
- Create: `tests/integration/temporal/test_temporal_cgroup_gate.py`

**Interfaces:**
- Consumes: final external artifact/descriptor, existing `run_load` and cgroup measurement modes.
- Produces: `TemporalFeasibilityReceipt` and `evaluate_temporal_feasibility(...)`.

- [ ] **Step 1: Write failing topology/threshold tests**

Assert candidate and generator share one `internal: true` network; no host port; both non-root,
read-only, `cap_drop ALL`, no-new-privileges, bounded CPU/memory/pids/tmpfs, no Docker socket;
generator starts after predictor health and has only the exact evidence-directory write mount.
Assert the gate constants are 200 warmups, 2,000 requests, 80 rps, 32 in flight, zero errors,
25,000 microseconds, 1 CPU, 384 MiB hard, 256 MiB cgroup policy.

~~~python
def test_temporal_compose_is_internal_and_bounded(compose_config) -> None:
    candidate = compose_config["services"]["candidate"]
    generator = compose_config["services"]["load-generator"]
    assert candidate["networks"] == generator["networks"] == ["temporal-load"]
    assert compose_config["networks"]["temporal-load"]["internal"] is True
    assert "ports" not in candidate
    assert candidate["cpus"] == 1.0 and candidate["mem_limit"] == "384m"
    assert generator["depends_on"]["candidate"]["condition"] == "service_healthy"
~~~

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/contract/temporal/test_feasibility_compose.py tests/integration/temporal/test_temporal_load_gate.py tests/integration/temporal/test_temporal_cgroup_gate.py -q`

Expected: FAIL because the temporal profile and receipt do not exist.

- [ ] **Step 3: Implement the constrained profile**

Reuse the predictor Dockerfile with versioned descriptor/runtime selection. The load generator posts
one valid v2 golden payload to `http://candidate:8080/v1/predict` over the internal network with
connection reuse. Reuse `run_load` and sanitized error classes. Reuse cgroup v2
`FD_LOCAL_POST_WARMUP_PEAK` or `WHOLE_LIFETIME_PEAK_UPPER_BOUND` exactly; RSS, psutil, Docker UI,
`docker stats`, and host estimates cannot satisfy the receipt. Receipt binds artifact/image/
container-cgroup/route/window identities and every raw measurement digest.

- [ ] **Step 4: Run GREEN, then the owner-authorized Compose gate**

Unit/contract GREEN:
`uv run pytest tests/contract/temporal/test_feasibility_compose.py tests/integration/temporal/test_temporal_load_gate.py tests/integration/temporal/test_temporal_cgroup_gate.py -q`

After those pass, run the exact Compose profile from a fresh candidate container with the external
artifact read-only and external evidence directory writable. Expected measured result: all original
load/memory thresholds PASS. Any FAIL/UNKNOWN is preserved and blocks W5.

Expected: PASS for topology/threshold tests and for the separately measured, sanitized Compose gate;
the predictor and generator are then completely removed.

- [ ] **Step 5: Commit source and measured sanitized index separately**

~~~powershell
git add src/mdcp/temporal/feasibility.py compose.temporal-feasibility.yaml docker/predictor.Dockerfile tests/contract/temporal/test_feasibility_compose.py tests/integration/temporal/test_temporal_load_gate.py tests/integration/temporal/test_temporal_cgroup_gate.py
git commit -m "feat: add temporal deployment feasibility gate"
~~~

Measured payload remains external; its digest is registered in Task 4.5.

### Task 4.5: Seal offline-verifiable feasibility and reviewer evidence

**Files:**
- Create: `src/mdcp/temporal/reviewer.py`
- Create: `schemas/v2/temporal-feasibility-receipt.schema.json`
- Create: `evidence/public/v02/feasibility/result-index.json`
- Create: `docs/reviewer/v02-final-feasibility.md`
- Create: `tests/integration/temporal/test_offline_feasibility_bundle.py`
- Create: `tests/security/temporal/test_feasibility_claims.py`

**Interfaces:**
- Consumes: final artifact/descriptor, local image digest, SBOM/provenance/scan, validator/parity/
  load/cgroup receipts, existing offline bundle verifier.
- Produces: `verify_temporal_feasibility_bundle(root) -> TemporalFeasibilityReceipt` and a
  CPU-only reviewer command.

- [ ] **Step 1: Write failing complete-bundle and claim tests**

Require every §8.2-required digest, exact artifact subject equality, public-safe index, CPU-only/no-H2 claim,
and rejection of missing/tampered SBOM, provenance, scan, validator, parity, load, or cgroup member.

~~~python
@pytest.mark.parametrize("member", [
    "sbom", "provenance", "scan", "validation", "parity", "load", "cgroup",
])
def test_offline_bundle_fails_when_required_member_is_missing(bundle_root, member) -> None:
    remove_logical_member(bundle_root, member)
    receipt = verify_temporal_feasibility_bundle(bundle_root)
    assert receipt.verdict != "PASS"
    assert "EVIDENCE_MISSING" in receipt.reason_codes
~~~

- [ ] **Step 2: Run RED**

Run:
`uv run pytest tests/integration/temporal/test_offline_feasibility_bundle.py tests/security/temporal/test_feasibility_claims.py -q`

Expected: FAIL because reviewer verifier/schema/index are absent.

- [ ] **Step 3: Implement local immutable supply-chain verification**

Reuse `seal_bundle`/`verify_bundle` and validator policy. Generate local image identity, SPDX SBOM,
provenance, vulnerability/license receipt, and member inventory without GHCR, GitHub attestation,
remote, or external publication. The reviewer doc uses checked-in synthetic fixtures and digest
indexes; it does not require UCI, model fitting, H2, GPU, or paid API. Claims say deployment
feasibility only, never H2/promotion/production readiness.

- [ ] **Step 4: Run GREEN and full Wave 4 verification**

Run:
`uv run pytest tests/unit tests/contract tests/integration/temporal tests/integration/validator tests/security/temporal -q && uv run ruff check src/mdcp tests`

Expected: PASS; external measured bundle and public result-index inventories are byte-equivalent by
digest.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/reviewer.py schemas/v2/temporal-feasibility-receipt.schema.json evidence/public/v02/feasibility/result-index.json docs/reviewer/v02-final-feasibility.md tests/integration/temporal/test_offline_feasibility_bundle.py tests/security/temporal/test_feasibility_claims.py
git commit -m "docs: record temporal feasibility evidence"
~~~

Clean the Compose project and verify no container/volume/network remains.

## Wave 4 completion gate

- Fit ledger equals 85 exactly.
- Final lineage, ONNX parity/operator/schema/size, MLflow, descriptor, validator, isolated image,
  load, authoritative cgroup memory, local supply-chain, offline bundle, and claim tests PASS.
- Any measured FAIL/UNKNOWN blocks candidate freeze without another model or changed threshold.
- H2 remains `SEALED_NOT_LOADED`/`0`.

**Immutable handoff:** final model/artifact/lineage/parity/feasibility/bundle digests and exact clean
candidate source precursor.

**Owner checkpoint:** report `V02_W4_FEASIBILITY_PASS` and stop. P4 owner review is required before
any candidate freeze manifest or freeze commit is created.
