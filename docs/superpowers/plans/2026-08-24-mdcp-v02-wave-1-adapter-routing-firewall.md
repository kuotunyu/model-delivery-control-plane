# MDCP v0.2 Wave 1 Adapter, Routing, and Data Firewall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the strict v2 envelope, exact temporal adapter, legacy/v2 admission policy, and
a development-only UCI path that cannot return or parse an H2 row.

**Architecture:** Extend the existing workload contract without breaking `BikeRequest` v1. A pure
adapter maps valid v2 envelopes to 18 floats; a pure admission classifier prevents partial v2 from
falling back to legacy. Formal development code consumes a new 13,003-row bounded loader, never the
legacy `DatasetPartitions.open_h2` capability.

**Tech Stack:** Pydantic v2, Python `zoneinfo`, pandas, NumPy, FastAPI, pytest, Hypothesis, existing
predictor and digest helpers.

## Global Constraints

- Entry is a clean W0 PASS commit plus the P1 owner checkpoint.
- Only complete `mdcp.bike-request.v2` envelopes are candidate eligible.
- Legacy requests have neither `schema_version` nor `event_timestamp` and are stable-only.
- Any v2 marker makes the payload v2-declared; missing/invalid fields reject it and never fall back.
- Timestamp offset is numeric, timezone is `America/New_York`, and the exact half-open domain is
  `[2011-01-01 00:00:00, 2013-01-01 00:00:00)`.
- Feature formulas and order are exact; raw timestamps and forbidden UCI columns never enter ONNX.
- Formal development input is exactly 8,645 2011 rows plus 4,358 observed-H1 rows. H2 rows loaded
  remain zero.

---

## Wave 1 entry gate

Run the W0 completion command, recompute its immutable handoff digests, verify a clean worktree, and
confirm H2 `SEALED_NOT_LOADED`/`0` before editing.

### Task 1.1: Add the strict v2 request envelope and checked-in schema

**Files:**
- Modify: `src/mdcp/contracts/workload.py`
- Create: `schemas/v2/bike-request.schema.json`
- Create: `tests/contract/workload/test_v2_request_schema.py`

**Interfaces:**
- Consumes: existing `BikeRequest`, `RequestId`, and `NormalizedFloat`.
- Produces: `BikeRequestV2`, `BikeRequestEnvelope = BikeRequest | BikeRequestV2`, and
  `BikeRequestV2.to_legacy() -> BikeRequest`.

- [ ] **Step 1: Write failing strict-envelope tests**

~~~python
def test_v2_envelope_is_strict_and_reduces_to_v1() -> None:
    request = BikeRequestV2.model_validate(VALID_V2)
    assert request.schema_version == "mdcp.bike-request.v2"
    assert "event_timestamp" not in request.to_legacy().model_dump()
    assert "schema_version" not in request.to_legacy().model_dump()

@pytest.mark.parametrize("name", ["yr", "dteday", "instant", "casual", "registered", "cnt"])
def test_v2_rejects_forbidden_fields(name: str) -> None:
    with pytest.raises(ValidationError):
        BikeRequestV2.model_validate({**VALID_V2, name: 1})
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/contract/workload/test_v2_request_schema.py -q`

Expected: FAIL importing `BikeRequestV2`.

- [ ] **Step 3: Implement the model and schema**

~~~python
class BikeRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["mdcp.bike-request.v2"]
    request_id: RequestId
    event_timestamp: Annotated[str, StringConstraints(min_length=25, max_length=35)]
    season: Literal[1, 2, 3, 4]
    mnth: Annotated[int, Field(ge=1, le=12)]
    hr: Annotated[int, Field(ge=0, le=23)]
    holiday: Literal[0, 1]
    weekday: Annotated[int, Field(ge=0, le=6)]
    workingday: Literal[0, 1]
    weathersit: Literal[1, 2, 3, 4]
    temp: NormalizedFloat
    atemp: NormalizedFloat
    hum: NormalizedFloat
    windspeed: NormalizedFloat

    def to_legacy(self) -> BikeRequest:
        return BikeRequest.model_validate(
            self.model_dump(exclude={"schema_version", "event_timestamp"})
        )
~~~

Generate `schemas/v2/bike-request.schema.json` from the model and assert byte equality with the
checked-in schema. Do not edit the v1 schema.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/workload/test_contracts.py tests/contract/workload/test_v2_request_schema.py -q`

Expected: existing v1 tests and new v2 tests PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/contracts/workload.py schemas/v2/bike-request.schema.json tests/contract/workload/test_v2_request_schema.py
git commit -m "feat: define bike request v2 envelope"
~~~

### Task 1.2: Implement strict timestamp validation and the 18-field adapter

**Files:**
- Create: `src/mdcp/temporal/adapter.py`
- Create: `tests/unit/temporal/test_adapter.py`

**Interfaces:**
- Consumes: `BikeRequestV2` and W0 constants.
- Produces: `TemporalReasonCode`, `TemporalContractError(reason_code)`,
  `TemporalFeatureVector`, and `adapt_v2(request: BikeRequestV2) -> TemporalFeatureVector`.

- [ ] **Step 1: Write domain, cross-field, and formula tests**

~~~python
def test_origin_vector_is_exact() -> None:
    vector = adapt_v2(BikeRequestV2.model_validate(ORIGIN_PAYLOAD))
    assert vector.names == TEMPORAL_FEATURE_COLUMNS
    assert vector.values[11] == 0.0
    assert vector.values[12:14] == pytest.approx((math.sin(2 * math.pi * 0 / 24), 1.0))

@pytest.mark.parametrize("stamp", [
    "2010-12-31T23:00:00-05:00",
    "2013-01-01T00:00:00-05:00",
])
def test_out_of_range_is_fixed_reason(stamp: str) -> None:
    with pytest.raises(TemporalContractError) as caught:
        adapt_v2(BikeRequestV2.model_validate({**ORIGIN_PAYLOAD, "event_timestamp": stamp}))
    assert caught.value.reason_code is TemporalReasonCode.EVENT_TIMESTAMP_OUT_OF_RANGE
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_adapter.py -q`

Expected: FAIL importing `mdcp.temporal.adapter`.

- [ ] **Step 3: Implement fail-closed normalization**

Use a full-match regex that requires `YYYY-MM-DDTHH:MM:SS±HH:MM`; `Z` and missing offsets fail.
Parse with `datetime.fromisoformat`, convert to `ZoneInfo("America/New_York")`, and require the
supplied civil coordinates/offset to equal the normalized zone coordinates so nonexistent or
ambiguous-offset misuse cannot pass. Require minute/second/microsecond zero, enforce the exact
half-open interval, and cross-check `mnth`, `hr`, and Sunday-zero `weekday`.

Compute:

~~~python
elapsed_days = (local.date() - date(2011, 1, 1)).days + request.hr / 24
values = (
    *request.to_legacy().model_dump().values(),
    elapsed_days,
    math.sin(2 * math.pi * request.hr / 24),
    math.cos(2 * math.pi * request.hr / 24),
    math.sin(2 * math.pi * request.weekday / 7),
    math.cos(2 * math.pi * request.weekday / 7),
    math.sin(2 * math.pi * elapsed_days / 365.2425),
    math.cos(2 * math.pi * elapsed_days / 365.2425),
)
~~~

The exception stores only one of `MISSING_EVENT_TIMESTAMP`, `INVALID_EVENT_TIMESTAMP`,
`EVENT_TIMESTAMP_OUT_OF_RANGE`, or `TEMPORAL_FIELD_MISMATCH` and never the raw timestamp.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_adapter.py -q`

Expected: origin/year/leap/DST/domain/mismatch tests PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/adapter.py tests/unit/temporal/test_adapter.py
git commit -m "feat: add causal temporal adapter"
~~~

### Task 1.3: Separate legacy, valid-v2, and invalid-v2 admissions

**Files:**
- Create: `src/mdcp/temporal/routing.py`
- Modify: `src/mdcp/predictor/app.py`
- Modify: `tests/contract/workload/test_predictor_api.py`
- Create: `tests/unit/temporal/test_routing.py`

**Interfaces:**
- Consumes: `BikeRequest`, `BikeRequestV2`, `ExecutionRole`, `adapt_v2`.
- Produces: `AdmissionKind` values `LEGACY_STABLE_ONLY`,
  `V2_CANDIDATE_ELIGIBLE`, `INVALID_V2`;
  `classify_envelope(payload: Mapping[str, object]) -> AdmissionDecision`; and
  `create_app(runtime, *, admission_role: ExecutionRole = ExecutionRole.STABLE)`.

- [ ] **Step 1: Write the admission truth table**

~~~python
@pytest.mark.parametrize(("payload", "kind"), [
    (VALID_V1, AdmissionKind.LEGACY_STABLE_ONLY),
    (VALID_V2, AdmissionKind.V2_CANDIDATE_ELIGIBLE),
    ({**VALID_V1, "event_timestamp": VALID_V2["event_timestamp"]}, AdmissionKind.INVALID_V2),
    ({**VALID_V1, "schema_version": "mdcp.bike-request.v2"}, AdmissionKind.INVALID_V2),
    ({**VALID_V2, "schema_version": "mdcp.bike-request.v3"}, AdmissionKind.INVALID_V2),
])
def test_admission_truth_table(payload, kind) -> None:
    assert classify_envelope(payload).kind is kind
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_routing.py tests/contract/workload/test_predictor_api.py -q`

Expected: FAIL because admission classification and `admission_role` do not exist.

- [ ] **Step 3: Implement classification before model selection**

If neither v2 marker exists, validate exact `BikeRequest`. If either marker exists, validate the
complete `BikeRequestV2` and adapter before returning candidate eligibility. A candidate-role app
rejects legacy with sanitized `LEGACY_STABLE_ONLY`; a stable-role app accepts legacy and reduces
valid v2 to the original 11 fields. Invalid v2 returns only the adapter/schema reason code. Add
separate low-cardinality counters keyed by `AdmissionKind`; do not create a shared quality counter.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_routing.py tests/contract/workload/test_predictor_api.py -q`

Expected: PASS; partial v2 never calls either runtime.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/routing.py src/mdcp/predictor/app.py tests/unit/temporal/test_routing.py tests/contract/workload/test_predictor_api.py
git commit -m "feat: enforce versioned prediction admission"
~~~

### Task 1.4: Add a bounded development-only UCI loader and H2 firewall

**Files:**
- Modify: `src/mdcp/workload/dataset.py`
- Modify: `src/mdcp/workload/splits.py`
- Create: `tests/unit/workload/test_development_loader.py`
- Create: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**
- Consumes: existing archive checksum/member validation.
- Produces: `load_uci_development_archive(path, expected_sha256) -> DataFrame`,
  `DevelopmentPartitions(train: DataFrame, h1: DataFrame)`, and
  `split_development_rows(frame) -> DevelopmentPartitions`.

- [ ] **Step 1: Write failing row-boundary and capability tests**

~~~python
def test_development_loader_stops_at_exact_row_count(fake_archive: Path) -> None:
    frame = load_uci_development_archive(fake_archive, sha256_hex(fake_archive.read_bytes()))
    assert len(frame) == 13_003
    parts = split_development_rows(frame)
    assert len(parts.train) == 8_645
    assert len(parts.h1) == 4_358
    assert not hasattr(parts, "h2")
    assert not hasattr(parts, "open_h2")
~~~

The security test parses imports under `src/mdcp/temporal` and fails if formal modules import
`split_rows`, `DatasetPartitions`, or `open_h2`.

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/workload/test_development_loader.py tests/security/temporal/test_data_firewall.py -q`

Expected: FAIL because the bounded functions/types do not exist.

- [ ] **Step 3: Implement opaque checksum plus bounded CSV parsing**

Reuse `_validate_archive_members`. Hash the archive bytes, then call
`pandas.read_csv(source, nrows=13_003)`. Validate exact columns, row count, monotonic chronology,
first timestamp `2011-01-01 00:00`, last timestamp `2012-06-30 23:00`, train/H1 counts, and canonical
row digests. Never request, iterate, parse, count, or inspect row 13,004. Keep legacy `split_rows` for
v0.1 compatibility, but make every v0.2 formal interface type-check against
`DevelopmentPartitions` only.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/workload/test_dataset.py tests/unit/workload/test_splits.py tests/unit/workload/test_development_loader.py tests/security/temporal/test_data_firewall.py -q`

Expected: PASS; fake archive spy proves the parser stops after 13,003 parsed rows.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/workload/dataset.py src/mdcp/workload/splits.py tests/unit/workload/test_development_loader.py tests/security/temporal/test_data_firewall.py
git commit -m "feat: enforce development-only data access"
~~~

### Task 1.5: Freeze v2 feature lineage and golden vectors

**Files:**
- Modify: `src/mdcp/workload/features.py`
- Create: `tests/fixtures/temporal/adapter-golden-vectors.json`
- Modify: `tests/unit/workload/test_leakage.py`
- Create: `tests/unit/temporal/test_golden_vectors.py`

**Interfaces:**
- Consumes: `TemporalFeatureVector` and existing `LeakageReceipt`.
- Produces: `temporal_feature_columns() -> tuple[str, ...]` and
  `audit_temporal_feature_lineage(frame, selected_columns=None) -> LeakageReceipt`.

- [ ] **Step 1: Write failing exact-order/leakage/vector tests**

Assert all 18 positions, formulas, float64 computation, one float32 boundary cast, and rejection of
each forbidden source. Golden cases are origin, 2011 year end, 2012 leap day, DST spring/fall edges,
all categorical boundaries, instant before lower bound, last accepted hour, and exact upper bound.
Each vector records payload, expected reason or 18 floats, and SHA-256 of float64 and float32 bytes.

~~~python
def test_temporal_lineage_is_exact() -> None:
    receipt = audit_temporal_feature_lineage(TEMPORAL_FRAME)
    assert receipt.columns == TEMPORAL_FEATURE_COLUMNS
    assert len(receipt.columns) == 18

@pytest.mark.parametrize("name", [
    "yr", "dteday", "instant", "casual", "registered", "cnt", "event_timestamp",
])
def test_temporal_lineage_rejects_forbidden_source(name: str) -> None:
    with pytest.raises(FeatureLeakageError):
        audit_temporal_feature_lineage(TEMPORAL_FRAME, (*TEMPORAL_FEATURE_COLUMNS, name))
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/workload/test_leakage.py tests/unit/temporal/test_golden_vectors.py -q`

Expected: FAIL because v2 lineage and the vector file are absent.

- [ ] **Step 3: Implement one v2 lineage path**

`audit_temporal_feature_lineage` accepts only `TEMPORAL_FEATURE_COLUMNS` in exact order. It rejects
raw `event_timestamp`/`dteday`, `yr`, target fields, future aggregates, discovered category sets, and
H2-derived preprocessing. Generate golden expected bytes with the production adapter once, review
them, then freeze the JSON; subsequent tests recompute without rewriting it.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/workload/test_leakage.py tests/unit/temporal/test_adapter.py tests/unit/temporal/test_golden_vectors.py -q`

Expected: PASS with exact digest equality.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/workload/features.py tests/fixtures/temporal/adapter-golden-vectors.json tests/unit/workload/test_leakage.py tests/unit/temporal/test_golden_vectors.py
git commit -m "test: freeze temporal feature vectors"
~~~

### Task 1.6: Bind the adapter/firewall contract into one recomputable receipt

**Files:**
- Create: `src/mdcp/temporal/contract_gate.py`
- Create: `tests/integration/temporal/test_contract_gate.py`
- Create: `schemas/v2/temporal-contract-receipt.schema.json`

**Interfaces:**
- Consumes: v2 schema, adapter vectors, development row identity, feature lineage, routing truth
  table, and public-evidence scanner.
- Produces: `TemporalContractReceipt` and
  `build_temporal_contract_receipt(repository_root, development_identity) -> TemporalContractReceipt`.

- [ ] **Step 1: Write a failing receipt recomputation test**

~~~python
def test_contract_receipt_binds_all_wave_one_identities(repo_root: Path) -> None:
    receipt = build_temporal_contract_receipt(repo_root, DEVELOPMENT_IDENTITY_FIXTURE)
    assert receipt.schema_version == "mdcp.temporal-contract-receipt.v1"
    assert receipt.feature_count == 18
    assert receipt.development_row_count == 13_003
    assert receipt.h2_loaded_rows == 0
    assert receipt.verdict == "PASS"
    assert receipt == build_temporal_contract_receipt(repo_root, DEVELOPMENT_IDENTITY_FIXTURE)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/integration/temporal/test_contract_gate.py -q`

Expected: FAIL importing `TemporalContractReceipt`.

- [ ] **Step 3: Implement digest-only receipt assembly**

The frozen model contains only logical IDs, counts, fixed reason codes, and SHA-256 values for the
schema, adapter, vectors, routing table, development rows, feature lineage, and source code. It has
`h2_status="SEALED_NOT_LOADED"`, `h2_loaded_rows=0`, and no raw row/path/exception field. Verdict is
PASS only when all named checks pass.

- [ ] **Step 4: Run GREEN and Wave 1 suite**

Run:
`uv run pytest tests/unit/workload tests/unit/temporal tests/contract/workload tests/contract/temporal tests/integration/temporal tests/security/temporal -q && uv run ruff check src/mdcp tests`

Expected: PASS with existing v1 API/fixture behavior retained.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/contract_gate.py schemas/v2/temporal-contract-receipt.schema.json tests/integration/temporal/test_contract_gate.py
git commit -m "feat: bind temporal contract evidence"
~~~

## Wave 1 completion gate

- Strict envelope/schema, adapter, routing truth table, feature lineage, golden vectors, bounded
  development loader, H2 firewall, and receipt recomputation all PASS.
- Adapter accepts only the exact research interval and emits exactly 18 ordered fields.
- Legacy/v2/invalid counters are separate; partial v2 never reaches a model.
- Formal v0.2 imports expose no H2-opening capability.
- H2 remains `SEALED_NOT_LOADED` and loaded rows `0`.

**Immutable handoff:** schema, adapter, golden-vector, routing, development-row, feature-lineage,
firewall, and contract-receipt digests.

**Owner checkpoint:** report `V02_W1_ADAPTER_FIREWALL_PASS` and stop for P1 continuation approval.
