# MDCP v0.2 Wave 0 Temporal Foundation and Test Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze v0.2 constants, the exact finite development protocol, synthetic-only fixtures,
and public evidence guards without loading data or fitting a model.

**Architecture:** Add a small `mdcp.temporal` package whose first wave contains only immutable
constants and evidence-boundary helpers. The exact protocol is data, validated from one JSON file;
test fixtures are deterministic generated rows and contain no UCI payload.

**Tech Stack:** Python 3.12 standard library, Pydantic v2, pandas/NumPy already locked, pytest,
Hypothesis, RFC 8785 helpers already present.

## Global Constraints

- Entry requires a new owner approval bound to the exact plan-suite commit. Plan approval alone is
  not execution approval.
- H2 is `SEALED_NOT_LOADED` and loaded rows stay `0`.
- No UCI archive is opened, no model is fitted, and no ONNX/Docker/GPU/network command runs.
- Timezone is `America/New_York` and the sole domain is
  `[2011-01-01 00:00:00, 2013-01-01 00:00:00)`.
- Exactly 18 model fields, four folds, 20 trials, 19 eligible trials, seed 2026, 2,000 replicates,
  index 1,899, and at most 85 fits are frozen.
- Existing v0.1 evidence and code remain untouched except where a later task names an exact Modify
  path.

---

## Wave 0 entry gate

- Clean branch at the owner-approved plans commit.
- Owner record explicitly says `WAVE_0_IMPLEMENTATION_AUTHORIZED`.
- `git remote` and `git tag --points-at HEAD` are empty.
- Private preservation receipt reports `SEALED_NOT_LOADED` and `h2_rows_loaded=0`.

### Task 0.1: Freeze temporal constants in one dependency-free module

**Files:**
- Create: `src/mdcp/temporal/__init__.py`
- Create: `src/mdcp/temporal/constants.py`
- Create: `tests/unit/temporal/test_constants.py`

**Interfaces:**
- Consumes: no repository module beyond Python `datetime`.
- Produces: `TEMPORAL_SCHEMA_ID: str`, `TIMEZONE_NAME: str`,
  `DOMAIN_START_LOCAL: datetime`, `DOMAIN_END_LOCAL: datetime`,
  `TEMPORAL_FEATURE_COLUMNS: tuple[str, ...]`, `SUBGROUP_NAMES: tuple[str, ...]`,
  `BOOTSTRAP_RESAMPLES: int`, `BOOTSTRAP_SEED: int`, `BOOTSTRAP_INDEX: int`,
  `MAX_FORMAL_FITS: int`.

- [ ] **Step 1: Write the failing constants contract**

~~~python
from mdcp.temporal.constants import (
    BOOTSTRAP_INDEX, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED,
    DOMAIN_END_LOCAL, DOMAIN_START_LOCAL, MAX_FORMAL_FITS,
    SUBGROUP_NAMES, TEMPORAL_FEATURE_COLUMNS, TIMEZONE_NAME,
)

def test_v02_constants_are_exact() -> None:
    assert TIMEZONE_NAME == "America/New_York"
    assert DOMAIN_START_LOCAL.isoformat() == "2011-01-01T00:00:00"
    assert DOMAIN_END_LOCAL.isoformat() == "2013-01-01T00:00:00"
    assert len(TEMPORAL_FEATURE_COLUMNS) == 18
    assert TEMPORAL_FEATURE_COLUMNS[11:] == (
        "elapsed_days", "hour_sin", "hour_cos", "weekday_sin",
        "weekday_cos", "annual_sin", "annual_cos",
    )
    assert SUBGROUP_NAMES == (
        "weather_clear", "weather_mist", "weather_adverse",
        "day_non_working", "day_working", "demand_peak", "demand_off_peak",
    )
    assert (BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, BOOTSTRAP_INDEX) == (2000, 2026, 1899)
    assert MAX_FORMAL_FITS == 85
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_constants.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'mdcp.temporal'`.

- [ ] **Step 3: Implement the exact constants**

~~~python
from datetime import datetime

TEMPORAL_SCHEMA_ID = "mdcp.temporal-features.v0.2"
TIMEZONE_NAME = "America/New_York"
DOMAIN_START_LOCAL = datetime(2011, 1, 1)
DOMAIN_END_LOCAL = datetime(2013, 1, 1)
TEMPORAL_FEATURE_COLUMNS = (
    "season", "mnth", "hr", "holiday", "weekday", "workingday", "weathersit",
    "temp", "atemp", "hum", "windspeed", "elapsed_days", "hour_sin", "hour_cos",
    "weekday_sin", "weekday_cos", "annual_sin", "annual_cos",
)
SUBGROUP_NAMES = (
    "weather_clear", "weather_mist", "weather_adverse",
    "day_non_working", "day_working", "demand_peak", "demand_off_peak",
)
BOOTSTRAP_RESAMPLES = 2_000
BOOTSTRAP_SEED = 2026
BOOTSTRAP_INDEX = 1_899
MAX_FORMAL_FITS = 85
~~~

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_constants.py -q && uv run ruff check src/mdcp/temporal tests/unit/temporal`

Expected: PASS with no lint findings.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/__init__.py src/mdcp/temporal/constants.py tests/unit/temporal/test_constants.py
git commit -m "feat: freeze v0.2 temporal constants"
~~~

### Task 0.2: Encode and validate the exact folds, trials, and quality policy

**Files:**
- Create: `configs/workload/temporal-development-v2.json`
- Create: `schemas/v2/temporal-development.schema.json`
- Create: `tests/contract/temporal/test_development_config.py`

**Interfaces:**
- Consumes: constants from Task 0.1.
- Produces: canonical protocol fields `folds`, `trial_ids`, `families`, `quality`,
  `execution`; protocol content digest computed with `canonicalize_json`.

- [ ] **Step 1: Write a failing schema/inventory test**

~~~python
def test_protocol_has_exact_inventory(protocol: dict[str, object]) -> None:
    assert protocol["schema_version"] == "mdcp.temporal-development.v0.2"
    assert [fold["id"] for fold in protocol["folds"]] == ["F1", "F2", "F3", "F4"]
    assert len(protocol["trial_ids"]) == 20
    assert protocol["trial_ids"][0] == "CTRL-01"
    assert len(set(protocol["trial_ids"])) == 20
    assert sum(family["eligible_count"] for family in protocol["families"]) == 19
    assert protocol["execution"] == {
        "seed": 2026, "estimator_threads": 1, "selection_fits": 80,
        "replay_fits": 4, "final_fits": 1, "maximum_fits": 85,
        "peak_resident_memory_bytes": 4_294_967_296,
        "wall_clock_seconds": 21_600,
    }
    assert protocol["quality"]["overall_max_ratio"] == 0.97
    assert protocol["quality"]["subgroup_max_ratio"] == 1.05
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/contract/temporal/test_development_config.py -q`

Expected: FAIL because `configs/workload/temporal-development-v2.json` does not exist.

- [ ] **Step 3: Write the canonical protocol and strict schema**

The JSON lists these exact IDs, in order:

~~~json
[
  "CTRL-01",
  "REC-180-L4", "REC-180-L12", "REC-270-L4", "REC-270-L12",
  "REC-365-L4", "REC-365-L12",
  "STAT-A0.1", "STAT-A1", "STAT-A10", "STAT-A100", "STAT-A1000",
  "NL-E64-R0.03-D2", "NL-E64-R0.03-D3",
  "NL-E64-R0.07-D2", "NL-E64-R0.07-D3",
  "NL-E128-R0.03-D2", "NL-E128-R0.03-D3",
  "NL-E128-R0.07-D2", "NL-E128-R0.07-D3"
]
~~~

The four fold objects use exactly:

~~~json
[
  {"id":"F1","train_start":"2011-01-01T00:00:00","train_end":"2011-07-01T00:00:00","validation_start":"2011-07-01T00:00:00","validation_end":"2011-10-01T00:00:00"},
  {"id":"F2","train_start":"2011-01-01T00:00:00","train_end":"2011-10-01T00:00:00","validation_start":"2011-10-01T00:00:00","validation_end":"2012-01-01T00:00:00"},
  {"id":"F3","train_start":"2011-01-01T00:00:00","train_end":"2012-01-01T00:00:00","validation_start":"2012-01-01T00:00:00","validation_end":"2012-04-01T00:00:00"},
  {"id":"F4","train_start":"2011-01-01T00:00:00","train_end":"2012-04-01T00:00:00","validation_start":"2012-04-01T00:00:00","validation_end":"2012-07-01T00:00:00"}
]
~~~

Family objects encode the approved CTRL 1, REC 6, STAT 5, and NL 8 Cartesian products verbatim,
including feature subsets, recency windows, `random_state=2026`, `n_jobs=1`, Ridge `lsqr`
`tol=1e-8`/`max_iter=10000`, and Gradient Boosting `min_samples_leaf=8`,
`loss=squared_error`, `subsample=1.0`, `max_features=null`. The schema sets
`additionalProperties=false` recursively and fixes the quality values
`0.97`/`1.05`/`100`/`2000`/`2026`/`1899`, plus the execution ceilings
`4_294_967_296` peak resident bytes and `21_600` monotonic seconds.

- [ ] **Step 4: Run GREEN and canonical digest stability**

Run: `uv run pytest tests/contract/temporal/test_development_config.py -q`

Expected: PASS; serializing through RFC 8785 twice yields identical SHA-256.

- [ ] **Step 5: Commit**

~~~powershell
git add configs/workload/temporal-development-v2.json schemas/v2/temporal-development.schema.json tests/contract/temporal/test_development_config.py
git commit -m "feat: freeze v0.2 development protocol"
~~~

### Task 0.3: Build deterministic synthetic development fixtures

**Files:**
- Create: `tests/temporal_fixtures.py`
- Create: `tests/unit/temporal/test_fixture_firewall.py`

**Interfaces:**
- Consumes: Task 0.1 constants.
- Produces: `synthetic_development_frame() -> pandas.DataFrame` and
  `synthetic_v2_payload(timestamp: datetime, request_id: str) -> dict[str, object]`.

- [ ] **Step 1: Write the fixture-boundary test**

~~~python
def test_synthetic_rows_stop_before_h2() -> None:
    rows = synthetic_development_frame()
    assert rows.attrs == {
        "evidence_class": "synthetic_test",
        "source_kind": "deterministic_generated",
        "uci_rows": 0,
    }
    assert rows.index.min() == pd.Timestamp("2011-01-01 00:00:00")
    assert rows.index.max() < pd.Timestamp("2012-07-01 00:00:00")
    assert len(rows.index.unique()) == len(rows)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_fixture_firewall.py -q`

Expected: FAIL because `tests.temporal_fixtures` is absent.

- [ ] **Step 3: Implement the minimum deterministic generator**

Generate hourly rows from `2011-01-01` through `2012-06-30 23:00` with arithmetic-only weather,
working-day, normalized numeric, and `cnt` label values. Set the three exact `DataFrame.attrs` above.
Do not read any file, network resource, clock, random device, or environment variable. The payload
factory emits `schema_version="mdcp.bike-request.v2"` and an RFC 3339 timestamp with the correct
New York numeric offset.

- [ ] **Step 4: Run GREEN**

Run: `uv run pytest tests/unit/temporal/test_fixture_firewall.py -q`

Expected: PASS and `uci_rows == 0`.

- [ ] **Step 5: Commit**

~~~powershell
git add tests/temporal_fixtures.py tests/unit/temporal/test_fixture_firewall.py
git commit -m "test: add synthetic temporal development fixtures"
~~~

### Task 0.4: Freeze historical and public evidence boundaries

**Files:**
- Create: `src/mdcp/temporal/evidence.py`
- Create: `tests/contract/temporal/test_historical_ledger.py`
- Create: `tests/security/temporal/test_public_evidence_boundary.py`

**Interfaces:**
- Consumes: `canonicalize_json(value) -> bytes` and `sha256_hex(data) -> str`.
- Produces: `HistoricalLedger` and
  `public_evidence_violations(value: object) -> tuple[str, ...]`.

- [ ] **Step 1: Write failing ledger and privacy tests**

~~~python
def test_historical_ledger_cannot_rewrite_failures() -> None:
    ledger = HistoricalLedger.frozen_v02()
    assert ledger.v1_h1_verdict == "FAIL"
    assert ledger.candidate_v2_verdict == "NO_ELIGIBLE_CANDIDATE"
    assert ledger.h1_role == "OBSERVED_DEVELOPMENT_ONLY"
    assert ledger.h2_status == "SEALED_NOT_LOADED"
    assert ledger.h2_loaded_rows == 0

def test_public_scan_rejects_private_metadata() -> None:
    assert public_evidence_violations({"host_path": "PRIVATE_PATH_SENTINEL"}) == ("PRIVATE_PATH",)
    assert public_evidence_violations({"error": "raw exception text"}) == ("RAW_EXCEPTION",)
~~~

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/contract/temporal/test_historical_ledger.py tests/security/temporal/test_public_evidence_boundary.py -q`

Expected: FAIL importing `mdcp.temporal.evidence`.

- [ ] **Step 3: Implement immutable facts and fixed violations**

`HistoricalLedger.frozen_v02()` embeds the published Candidate-v1 ratios and the logical
preservation inventory digest from approved spec `2, never the private absolute source path.
`public_evidence_violations` walks keys/strings and returns sorted unique codes from
`PRIVATE_PATH`, `CREDENTIAL`, `RAW_EXCEPTION`, `RAW_ENVIRONMENT`, `CONTAINER_ID`,
`OPAQUE_PAYLOAD`. It never returns the offending value.

- [ ] **Step 4: Run GREEN and the Wave 0 gate**

Run:
`uv run pytest tests/unit/temporal tests/contract/temporal tests/security/temporal -q && uv run ruff check src/mdcp/temporal tests/temporal_fixtures.py tests/unit/temporal tests/contract/temporal tests/security/temporal`

Expected: all tests PASS; no UCI/model/ONNX/Docker command is invoked.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/evidence.py tests/contract/temporal/test_historical_ledger.py tests/security/temporal/test_public_evidence_boundary.py
git commit -m "feat: enforce v0.2 evidence boundaries"
~~~

## Wave 0 completion gate

- All four task GREEN commands and full `tests/unit/temporal tests/contract/temporal
  tests/security/temporal` suite PASS.
- Protocol schema validates exactly 4 folds, 20 trials, 19 eligible, and 85 maximum fits.
- Synthetic fixtures report `uci_rows=0` and end before `2012-07-01`.
- Git diff from wave entry contains only named files; dependency lock is unchanged.
- H2 remains `SEALED_NOT_LOADED` with zero loaded rows.

**Immutable handoff:** constants/config/schema/test-helper/evidence-boundary digests plus clean Wave 0
commit.

**Owner checkpoint:** report `V02_W0_FOUNDATION_PASS` and stop. Continuing to Wave 1 requires the
owner checkpoint named P1 in the index.
