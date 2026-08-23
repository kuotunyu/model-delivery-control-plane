# MDCP Wave 1 Workload, Training Fixtures, and Artifact Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce leakage-safe Bike workload contracts, reproducible stable/candidate ONNX fixtures, honest H1 evidence, MLflow numeric lineage, and the pre-image artifact descriptor.

**Architecture:** Raw UCI data is developer-only input verified by checksum and never committed. One frozen feature pipeline trains deterministic Random Forest fixtures and exports ONNX; Pydantic models generate checked-in JSON schemas. The calendar-day bootstrap kernel is introduced here for H1 and reused unchanged by Wave 4 for H2.

**Tech Stack:** Python 3.12, Pydantic v2, pandas, NumPy PCG64, scikit-learn, skl2onnx, ONNX, ONNX Runtime, MLflow, pytest, Hypothesis, and RFC 8785 helpers from Wave 0.

## Global Constraints

- Entry requires `WAVE0 PASS 8/8` and the exact Wave 0 report digest recorded in the branch history.
- Approved features are exactly `season,mnth,hr,holiday,weekday,workingday,weathersit,temp,atemp,hum,windspeed`; `casual,registered,cnt,instant,dteday,yr` are rejected inputs.
- 2011 is training only; 2012 H1 is `2012-01-01..2012-06-30`; sealed H2 is `2012-07-01..2012-12-31` and cannot be opened before a freeze-manifest digest exists.
- Stable/candidate training uses one locked dependency graph, deterministic random state, `n_jobs=1`, and identical input/output contracts.
- Natural PASS/FAIL/UNKNOWN is preserved. Synthetic fixtures are a separate evidence class.
- UCI data acquisition is allowed only in the developer workflow of this wave, using the approved DOI/source/checksum contract; reviewer fixtures never invoke it.
- Completion command: `uv run pytest tests/unit/workload tests/contract/workload tests/integration/test_mlflow_lineage.py -q`.

---

### Task 1.1: Define Bike request, response, and dataset provenance contracts

**Files:**
- Create: `src/mdcp/common/enums.py`
- Create: `src/mdcp/contracts/workload.py`
- Create: `schemas/v1/bike-request.schema.json`
- Create: `schemas/v1/prediction-response.schema.json`
- Create: `configs/workload/uci-bike-sharing-v1.json`
- Test: `tests/unit/workload/test_contracts.py`
- Test: `tests/contract/workload/test_json_schemas.py`
- Test: `tests/fixtures/workload/single-row.json`

**Interfaces:**
- Consumes: RFC-8785 and digest helpers from Wave 0.
- Produces: `BikeRequest`, `PredictionResponse`, `SafeErrorResponse`, common enums `ExecutionRole`, `EvidenceClass`, `FaultProfile`, `GateVerdict(PASS, FAIL, UNKNOWN)`, `ValidationVerdict(PASS, FAIL, UNKNOWN, QUARANTINE)`, `ReleaseState`, and the versioned Bike JSON schemas.

- [ ] **Step 1: Write failing strict-schema tests**

```python
def test_bike_request_rejects_forbidden_fields(valid_request):
    for name in {"casual", "registered", "cnt", "instant", "dteday", "yr"}:
        with pytest.raises(ValidationError):
            BikeRequest.model_validate({**valid_request, name: 1})

def test_prediction_requires_runtime_identity():
    value = PredictionResponse(request_id="r-1", release_id="sha256:" + "a" * 64,
                               prediction=42.0, route_revision=7)
    assert value.prediction >= 0
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/workload/test_contracts.py tests/contract/workload/test_json_schemas.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'mdcp.contracts.workload'`.

- [ ] **Step 3: Implement strict Pydantic contracts and generated schemas**

Use `extra="forbid"`, finite bounded numeric fields, categorical domains from UCI, non-empty request IDs, release IDs matching `^sha256:[0-9a-f]{64}$`, and positive route revisions. Generate schemas from the Pydantic source and add a contract test that fails if checked-in JSON differs from regeneration.

```python
class GateVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"

class ValidationVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    QUARANTINE = "QUARANTINE"

class ReleaseState(StrEnum):
    SUBMITTED = "SUBMITTED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    SHADOW = "SHADOW"
    CANARY_10 = "CANARY_10"
    CANARY_25 = "CANARY_25"
    CANARY_50 = "CANARY_50"
    PRODUCTION = "PRODUCTION"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    ROLLED_BACK = "ROLLED_BACK"
    QUARANTINED = "QUARANTINED"

class ExecutionRole(StrEnum):
    STABLE = "stable"
    CANDIDATE = "candidate"
    SHADOW = "shadow"

class EvidenceClass(StrEnum):
    BOOTSTRAP_BASELINE = "bootstrap_baseline"
    MEASURED_WORKLOAD = "measured_workload"
    INJECTED_TEST = "injected_test"
    RELEASE_CI_VERIFIED = "release_ci_verified"
    REVIEWER_LOCALLY_RECOMPUTED = "reviewer_locally_recomputed"

class FaultProfile(StrEnum):
    NONE = "none"
    LATENCY_PLUS_30MS = "latency_plus_30ms"
    ERROR_RATE = "error_rate"
    MEMORY_PAD = "memory_pad"
    SUBGROUP_CORRUPTION = "subgroup_corruption"
    TELEMETRY_DROP = "telemetry_drop"
    DUPLICATE_CONFLICT = "duplicate_conflict"
    OUT_OF_ORDER = "out_of_order"
    STALE_ROUTE_REVISION = "stale_route_revision"

class BikeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    season: Literal[1, 2, 3, 4]
    mnth: Annotated[int, Field(ge=1, le=12)]
    hr: Annotated[int, Field(ge=0, le=23)]
    holiday: Literal[0, 1]
    weekday: Annotated[int, Field(ge=0, le=6)]
    workingday: Literal[0, 1]
    weathersit: Literal[1, 2, 3, 4]
    temp: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    atemp: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    hum: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    windspeed: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
```

- [ ] **Step 4: Verify the contracts**

Run: `uv run pytest tests/unit/workload/test_contracts.py tests/contract/workload/test_json_schemas.py -q`

Expected: `all tests passed`; six forbidden-field cases fail validation and schema regeneration has zero diff.

- [ ] **Step 5: Commit**

```powershell
git add configs/workload schemas/v1 src/mdcp/common/enums.py src/mdcp/contracts/workload.py tests/unit/workload tests/contract/workload tests/fixtures/workload
git commit -m "feat: define bike workload contracts"
```

### Task 1.2: Enforce checksum, chronology, and leakage boundaries

**Files:**
- Create: `src/mdcp/workload/dataset.py`
- Create: `src/mdcp/workload/features.py`
- Create: `src/mdcp/workload/splits.py`
- Test: `tests/unit/workload/test_dataset.py`
- Test: `tests/unit/workload/test_splits.py`
- Test: `tests/unit/workload/test_leakage.py`
- Test: `tests/fixtures/workload/chronology-sample.csv`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `BikeRequest`, dataset config, an explicit local archive path, and expected SHA-256.
- Produces: `load_uci_archive(path: Path, expected_sha256: str) -> DataFrame`, `split_rows(frame: DataFrame) -> DatasetPartitions`, `approved_feature_columns() -> tuple[str, ...]`, and `LeakageReceipt`.

- [ ] **Step 1: Write failing checksum/split/leakage tests**

```python
def test_split_boundaries(frame):
    parts = split_rows(frame)
    assert parts.train.index.max() < Timestamp("2012-01-01")
    assert parts.h1.index.max() <= Timestamp("2012-06-30 23:59:59")
    assert parts.h2.index.min() >= Timestamp("2012-07-01")

def test_feature_lineage_excludes_forbidden_columns(frame):
    receipt = audit_feature_lineage(frame)
    assert receipt.columns == approved_feature_columns()
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/workload/test_dataset.py tests/unit/workload/test_splits.py tests/unit/workload/test_leakage.py -q`

Expected: FAIL because `load_uci_archive`, `split_rows`, and `audit_feature_lineage` are undefined.

- [ ] **Step 3: Implement fail-closed data governance**

Verify the archive SHA-256 before extraction; reject links, traversal, duplicate members, and unexpected filenames. Parse `dteday` only into evaluator-side chronology, remove it before feature transformation, and require a freeze-manifest digest before any H2 loader returns rows. `.gitignore` must exclude `data/raw/`, `data/derived/`, and all downloaded archives.

```python
def load_uci_archive(path: Path, expected_sha256: str) -> pd.DataFrame:
    if sha256_hex(path.read_bytes()) != expected_sha256:
        raise DatasetIntegrityError("archive digest mismatch")
    member = require_single_regular_member(path, "hour.csv")
    frame = parse_hour_csv(member)
    if tuple(frame.columns) != EXPECTED_UCI_COLUMNS:
        raise DatasetIntegrityError("unexpected columns")
    return frame
```

- [ ] **Step 4: Verify negative and positive paths**

Run: `uv run pytest tests/unit/workload/test_dataset.py tests/unit/workload/test_splits.py tests/unit/workload/test_leakage.py -q`

Expected: checksum mismatch, traversal, forbidden columns, pre-freeze H2 access, and boundary overlap tests pass; pytest exits 0.

- [ ] **Step 5: Commit**

```powershell
git add .gitignore src/mdcp/workload tests/unit/workload tests/fixtures/workload
git commit -m "feat: enforce workload leakage boundaries"
```

### Task 1.3: Train deterministic stable and candidate fixtures

**Files:**
- Create: `configs/models/stable-v1.yaml`
- Create: `configs/models/candidate-v1.yaml`
- Create: `src/mdcp/workload/training.py`
- Create: `src/mdcp/workload/cli.py`
- Test: `tests/unit/workload/test_training.py`
- Test: `tests/integration/test_training_reproducibility.py`

**Interfaces:**
- Consumes: 2011 partition and exact YAML `ModelFixtureConfig`.
- Produces: `build_feature_pipeline() -> ColumnTransformer`, `train_fixture(config: ModelFixtureConfig, rows: DataFrame) -> Pipeline`, `TrainingReceipt`, and CLI grammar `python -m mdcp.workload.cli train --config CONFIG_PATH --data ARCHIVE_PATH --output OUTPUT_DIRECTORY`.

- [ ] **Step 1: Write failing determinism and fit-scope tests**

```python
def test_training_is_deterministic(train_rows, stable_config):
    left = train_fixture(stable_config, train_rows)
    right = train_fixture(stable_config, train_rows)
    assert left.predict(train_rows.head(32)).tobytes() == right.predict(train_rows.head(32)).tobytes()

def test_pipeline_fit_receipt_contains_only_2011(receipt):
    assert receipt.fit_max_timestamp < "2012-01-01T00:00:00Z"
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/workload/test_training.py tests/integration/test_training_reproducibility.py -q`

Expected: FAIL with `ImportError: cannot import name 'train_fixture'`.

- [ ] **Step 3: Implement the two bounded model configurations**

Use a `ColumnTransformer` shared by both releases; configure Random Forest with fixed `random_state=2026`, `n_jobs=1`, bounded tree count/depth from each reviewed YAML, and no estimator that loads code. Emit digests for configuration, preprocessing state, feature lineage, dependency lock, and training rows.

```python
def train_fixture(config: ModelFixtureConfig, rows: pd.DataFrame) -> Pipeline:
    estimator = RandomForestRegressor(
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        random_state=2026,
        n_jobs=1,
    )
    pipeline = Pipeline([("features", build_feature_pipeline()), ("model", estimator)])
    return pipeline.fit(rows.loc[:, approved_feature_columns()], rows["cnt"])
```

- [ ] **Step 4: Verify reproducibility**

Run: `uv run pytest tests/unit/workload/test_training.py tests/integration/test_training_reproducibility.py -q`

Expected: `all tests passed`; two fits per configuration produce byte-identical prediction vectors and identical training/config digests.

- [ ] **Step 5: Commit**

```powershell
git add configs/models src/mdcp/workload/training.py src/mdcp/workload/cli.py tests/unit/workload/test_training.py tests/integration/test_training_reproducibility.py
git commit -m "feat: train deterministic delivery fixtures"
```

### Task 1.4: Export ONNX and implement the common predictor contract

**Files:**
- Create: `src/mdcp/workload/onnx_export.py`
- Create: `src/mdcp/predictor/runtime.py`
- Create: `src/mdcp/predictor/app.py`
- Create: `docker/predictor.Dockerfile`
- Test: `tests/unit/workload/test_onnx_export.py`
- Test: `tests/contract/workload/test_predictor_api.py`
- Test: `tests/integration/test_onnx_parity.py`

**Interfaces:**
- Consumes: fitted pipeline, `BikeRequest`, read-only `MDCP_RELEASE_ID`, descriptor path, and ONNX path.
- Produces: `export_pipeline_onnx(pipeline, path: Path) -> OnnxReceipt`, `OnnxPredictor.predict(request: BikeRequest) -> float`, FastAPI `POST /v1/predict`, `GET /health/ready`, and a non-root predictor image.

- [ ] **Step 1: Write failing parity/API tests**

```python
def test_onnx_prediction_matches_sklearn(model_pair, h1_rows):
    native, onnx = model_pair
    assert_allclose(onnx.predict(h1_rows), native.predict(h1_rows), rtol=1e-5, atol=1e-5)

def test_predictor_rejects_nonfinite_output(client, monkeypatch):
    monkeypatch.setattr(OnnxPredictor, "predict", lambda *_: float("nan"))
    assert client.post("/v1/predict", json=VALID_REQUEST).status_code == 500
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/workload/test_onnx_export.py tests/contract/workload/test_predictor_api.py tests/integration/test_onnx_parity.py -q`

Expected: FAIL because the exporter and predictor application do not exist.

- [ ] **Step 3: Implement bounded ONNX export/runtime**

Export a single model with fixed opset and one-row tensor contract; record operator inventory, byte size, SHA-256, input/output names and shapes. Predictor loads only descriptor-bound local ONNX, accepts no runtime URL/import path, returns finite non-negative predictions, echoes read-only deployment release identity, and emits a stable sanitized error envelope.

```python
def predict(request: BikeRequest, runtime: OnnxPredictor) -> PredictionResponse:
    value = float(runtime.session.run([runtime.output_name], runtime.tensor(request))[0][0])
    if not math.isfinite(value) or value < 0:
        raise PredictionContractError("invalid model output")
    return PredictionResponse(request_id=request.request_id, release_id=runtime.release_id,
                              prediction=value, route_revision=runtime.route_revision,
                              traceparent=current_traceparent())
```

- [ ] **Step 4: Verify parity and container contract**

Run: `uv run pytest tests/unit/workload/test_onnx_export.py tests/contract/workload/test_predictor_api.py tests/integration/test_onnx_parity.py -q; docker build --file docker/predictor.Dockerfile --tag mdcp-predictor:test .`

Expected: pytest exits 0; build succeeds; Dockerfile contract test confirms non-root user, read-only-compatible paths, no download command, and one local ONNX/descriptor entry point.

- [ ] **Step 5: Commit**

```powershell
git add docker/predictor.Dockerfile src/mdcp/workload/onnx_export.py src/mdcp/predictor tests/unit/workload/test_onnx_export.py tests/contract/workload/test_predictor_api.py tests/integration/test_onnx_parity.py
git commit -m "feat: add immutable onnx predictor contract"
```

### Task 1.5: Produce H1 cluster-bootstrap evidence and MLflow numeric lineage

**Files:**
- Create: `src/mdcp/policy/cluster_bootstrap.py`
- Create: `src/mdcp/workload/evaluation.py`
- Create: `src/mdcp/workload/mlflow_lineage.py`
- Create: `configs/policy/quality-v1.json`
- Test: `tests/unit/policy/test_cluster_bootstrap.py`
- Test: `tests/unit/workload/test_evaluation.py`
- Test: `tests/integration/test_mlflow_lineage.py`
- Test: `tests/fixtures/workload/bootstrap-vector.json`

**Interfaces:**
- Consumes: paired stable/candidate predictions, labels, evaluator-only `calendar_day`, frozen subgroups, and MLflow tracking URI.
- Produces: `cluster_bootstrap_ratios(rows: Sequence[PairedQualityRow], groups: Sequence[str], resamples: int = 2000, seed: int = 2026) -> BootstrapResult`, `evaluate_h1(rows: Sequence[PairedQualityRow], policy: QualityPolicy) -> H1EvaluationReport`, and `snapshot_mlflow_version(model_name: str, version: int) -> MLflowVersionSnapshot`.

- [ ] **Step 1: Write failing frozen-vector and numeric-version tests**

```python
def test_cluster_bootstrap_vector(vector):
    result = cluster_bootstrap_ratios(vector.rows, vector.groups, 2000, 2026)
    assert result.overall.ucb95 == vector.expected_overall_ucb95
    assert result.replicate_index == 1899

def test_mlflow_snapshot_rejects_alias(client):
    with pytest.raises(ValueError, match="numeric model version required"):
        snapshot_mlflow_version("bike-demand", "champion")
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/policy/test_cluster_bootstrap.py tests/unit/workload/test_evaluation.py tests/integration/test_mlflow_lineage.py -q`

Expected: FAIL because `cluster_bootstrap_ratios` and `snapshot_mlflow_version` are undefined.

- [ ] **Step 3: Implement the frozen H1 method and lineage snapshot**

Sample sorted calendar-day indices with `Generator(PCG64(2026))`, retain every hourly row for each sampled occurrence, compute point ratios from original rows, and use nearest-rank element 1899. Mark the entire report `UNKNOWN` for any fixed subgroup below 100, empty bootstrap subgroup, or non-positive/non-finite stable MAE. Log runs/artifacts to MLflow and snapshot only integer version, run ID, immutable artifact URI, and digests; aliases remain navigation-only.

```python
def cluster_bootstrap_ratios(rows: Sequence[PairedQualityRow],
                             groups: Sequence[str],
                             resamples: int = 2000,
                             seed: int = 2026) -> BootstrapResult:
    days = np.array(sorted({row.calendar_day for row in rows}))
    rng = np.random.Generator(np.random.PCG64(seed))
    ratios = [ratios_for_sample(rows, rng.choice(days, len(days), replace=True), groups)
              for _ in range(resamples)]
    return BootstrapResult.from_ratios(ratios, ucb_index=1899)
```

- [ ] **Step 4: Verify honest PASS/FAIL/UNKNOWN outputs**

Run: `uv run pytest tests/unit/policy/test_cluster_bootstrap.py tests/unit/workload/test_evaluation.py tests/integration/test_mlflow_lineage.py -q`

Expected: vector recomputes exactly, subgroup `n=99` is whole-report `UNKNOWN`, threshold failures remain FAIL, alias input is rejected, and pytest exits 0.

- [ ] **Step 5: Commit**

```powershell
git add configs/policy src/mdcp/policy/cluster_bootstrap.py src/mdcp/workload/evaluation.py src/mdcp/workload/mlflow_lineage.py tests/unit/policy tests/unit/workload/test_evaluation.py tests/integration/test_mlflow_lineage.py tests/fixtures/workload/bootstrap-vector.json
git commit -m "feat: record h1 quality and mlflow lineage"
```

### Task 1.6: Freeze the artifact descriptor and reviewer workload fixtures

**Files:**
- Create: `src/mdcp/contracts/release.py`
- Create: `schemas/v1/artifact-descriptor.schema.json`
- Test: `tests/unit/contracts/test_artifact_descriptor.py`
- Test: `tests/contract/workload/test_descriptor_schema.py`
- Test: `tests/fixtures/artifacts/stable/artifact-descriptor.json`
- Test: `tests/fixtures/artifacts/stable/model.onnx`
- Test: `tests/fixtures/artifacts/candidate/artifact-descriptor.json`
- Test: `tests/fixtures/artifacts/candidate/model.onnx`
- Test: `tests/fixtures/workload/freeze-manifest.json`
- Test: `tests/fixtures/workload/synthetic-h1-report.json`

**Interfaces:**
- Consumes: Git SHA, ONNX receipt, workload schemas, locked predictor source/dependencies/entry point/config, split/leakage/training/H1 digests.
- Produces: `Sha256`, `OnnxMetadata`, `ArtifactDescriptor`, `artifact_descriptor_digest(descriptor: ArtifactDescriptor) -> str`, stable/candidate synthetic artifact directories, and the H2 access `freeze_manifest_digest`.

- [ ] **Step 1: Write failing identity/no-cycle tests**

```python
def test_descriptor_has_only_prebuild_identity(descriptor):
    assert descriptor.git_source_sha
    assert descriptor.onnx.sha256
    assert descriptor.schema_digest
    assert descriptor.serving_code_config_id
    assert "oci" not in descriptor.model_fields
    assert "release_id" not in descriptor.model_fields
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/contracts/test_artifact_descriptor.py tests/contract/workload/test_descriptor_schema.py -q`

Expected: FAIL because `ArtifactDescriptor` is not defined.

- [ ] **Step 3: Implement canonical descriptors and deterministic synthetic fixtures**

Define strict descriptor schema/version, canonical digest, serving-code/config identity digest over exact source/dependency/entry/config inventory, and bounded ONNX metadata. Generate synthetic stable/candidate fixtures with no UCI rows; the synthetic H1 report must encode point overall ratio 0.90, UCB95 0.95, all subgroup point/UCB ratios <=1.05, at least 100 rows per subgroup, and evidence class `synthetic_test`.

```python
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

class OnnxMetadata(BaseModel):
    sha256: Sha256
    size_bytes: PositiveInt
    opset: PositiveInt
    operators: tuple[str, ...]
    input_name: str
    output_name: str

class ArtifactDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["artifact-descriptor/v1"]
    model_sha256: Sha256
    serving_identity_sha256: Sha256
    feature_manifest_sha256: Sha256
    dependency_lock_sha256: Sha256
    onnx: OnnxMetadata
```

- [ ] **Step 4: Verify descriptor tamper detection and fixture reproducibility**

Run: `uv run pytest tests/unit/contracts/test_artifact_descriptor.py tests/contract/workload/test_descriptor_schema.py -q; uv run python -m mdcp.workload.cli verify-fixtures --root tests/fixtures/artifacts`

Expected: tests pass; changing ONNX/schema/serving inventory changes descriptor digest; verifier prints `FIXTURES PASS stable=1 candidate=1 uci_rows=0`.

- [ ] **Step 5: Commit**

```powershell
git add schemas/v1/artifact-descriptor.schema.json src/mdcp/contracts/release.py tests/unit/contracts tests/contract/workload tests/fixtures/artifacts tests/fixtures/workload
git commit -m "feat: freeze artifact descriptor identity"
```

## Wave 1 completion checkpoint

Run: `uv run pytest tests/unit/workload tests/unit/policy tests/unit/contracts tests/contract/workload tests/integration/test_training_reproducibility.py tests/integration/test_onnx_parity.py tests/integration/test_mlflow_lineage.py -q; uv run python -m mdcp.workload.cli verify-fixtures --root tests/fixtures/artifacts; git status --short`

Expected: all tests pass, fixture verification reports no UCI rows in reviewer assets, natural H1 verdict is preserved rather than forced, every digest recomputes, and the worktree is clean. Commit the Wave 1 artifact inventory/digests before beginning Wave 2.
