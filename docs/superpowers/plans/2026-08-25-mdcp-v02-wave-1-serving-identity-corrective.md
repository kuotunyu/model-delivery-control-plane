# MDCP v0.2 Wave 1 Serving Identity Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Use superpowers:test-driven-development for every RED/GREEN cycle,
> superpowers:systematic-debugging for any unexpected failure, superpowers:requesting-code-review
> for the independent review, and superpowers:verification-before-completion before every commit and
> completion claim. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the partially implemented v0.2 Wave 1 so frozen v0.1 bytes and identity are
restored while v2 request handling, serving, evidence, and verification use independent versioned
modules and a complete source-archive-recomputable identity.

**Architecture:** Restore the two mutated v1 modules byte-for-byte and move their v2 responsibilities
to `workload_v2.py` and `app_v2.py`. Build an independent v2 serving inventory, AST-based static H2
capability firewall, executed behavioral H2 firewall, and closed 14-case golden inventory. Only after
those foundations pass may the three preserved Task 1.6 drafts be replaced with a receipt that binds
executed checks rather than selected test-file hashes.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pandas, NumPy, RFC 8785 canonical JSON, pytest,
Ruff, and the existing `uv.lock`. CPU only; no dependency change, model execution, ONNX, MLflow,
Docker, GPU, network, or real H2 access.

## Global Constraints

- Normative base specification:
  `docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md`.
- Normative corrective amendment:
  `docs/superpowers/specs/2026-08-25-mdcp-v02-serving-identity-isolation-design.md` at owner-approved
  content commit `da2fd65619edd0b69df415f5c126364791e2ee03`, approved content SHA-256
  `5fcbf1a8314f8e25cdbfd460f7ec202410a498deace6e853006250cb9509e33a`, and approval commit
  `45bd5e21b41c1cc05ab84462ec1400cf1d28c6d2`.
- The historical plan
  `docs/superpowers/plans/2026-08-24-mdcp-v02-wave-1-adapter-routing-firewall.md` is immutable. It is an
  execution record, not the plan to resume.
- Existing Tasks 1.1–1.5 commits remain in history. Every correction is append-only; no reset,
  checkout restoration, rebase, amend, squash, cherry-pick, or history rewrite is allowed.
- The v0.1 serving identity remains
  `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`.
- `src/mdcp/contracts/workload.py` must end at Git blob
  `33f174528e691f1f5ff2590c2c641d75669d5196`.
- `src/mdcp/predictor/app.py` must end at Git blob
  `9fdee53bead221f0698d2e4a52407a4901c37649`.
- Git blob IDs are migration assertions only. Runtime and reviewer verification must use current
  source-tree bytes and must work without `.git`.
- Existing v0.1 descriptors, fixtures, reports, public evidence, `SERVING_PATHS`,
  `SERVING_ENVIRONMENT`, v1 schemas, `pyproject.toml`, `uv.lock`, Dockerfiles, and predictor runtime
  are immutable.
- v1 entry point remains `mdcp.predictor.app:app`; v2 entry point is
  `mdcp.predictor.app_v2:app`.
- H2 remains `SEALED_NOT_LOADED`; loaded rows remain `0`. No command may parse, preview, count,
  return, hash, or infer a real row at or after `2012-07-01 00:00`.
- The only natural data operation is the separately authorized local completion gate over the
  approved 13,003-row development prefix: 8,645 train rows plus 4,358 observed-H1 rows. Whole-file
  archive hashing is allowed; `day.csv` and later `hour.csv` rows are not.
- The no-data reviewer fast path uses a deterministic generated archive with 13,003 development
  rows and a distinct row-13,004 sentinel. Its metadata is exactly
  `evidence_class=synthetic_test`, `source_kind=deterministic_generated`, and `uci_rows=0`.
- No test fixture may read a clock, environment value, random device, network, UCI file, or H2 row
  while generating the synthetic archive.
- The exact v2 model feature contract remains 18 ordered fields. `yr`, `dteday`, `instant`,
  `casual`, `registered`, `cnt`, and raw timestamps never enter the model feature vector.
- The exact golden case order is:
  `origin`, `year_end_category_maxima`, `leap_day`, `spring_before`, `spring_after`, `fall_edt`,
  `fall_est`, `malformed_timestamp`, `nonexistent_local_time`, `wrong_ambiguous_offset`,
  `cross_field_mismatch`, `before_lower_bound`, `last_accepted_hour`, `exact_upper_bound`.
- Public receipt material contains only relative logical paths, fixed IDs, counts, verdicts, and
  digests. It contains no absolute path, raw timestamp, raw row, sentinel value, exception,
  environment value, credential, username, hostname, or opaque payload.
- Commits use `kuotunyu <61350295+kuotunyu@users.noreply.github.com>` as both author and committer.
- Wave 2 is forbidden even after every Wave 1 gate passes.

---

## Relationship to the historical Wave 1 tasks

This plan supersedes only the remaining implementation instructions for the partially executed
Wave 1. It does not edit, erase, or relabel the historical plan or its commits.

| Historical scope | Corrective owner |
|---|---|
| Task 1.1 shared workload module | Corrective Task 1 |
| Task 1.2 adapter imports | Corrective Task 1, behavior otherwise unchanged |
| Task 1.3 shared predictor module | Corrective Task 2 |
| Task 1.4 direct-symbol-only firewall | Corrective Tasks 3–4 |
| Task 1.5 open golden set | Corrective Task 5 |
| Task 1.6 provisional untracked drafts | Corrective Task 7, after Task 6 |
| Wave 1 completion gate | Final gate in this plan |

There are exactly **7 corrective implementation tasks**. The entry preflight and final independent
review are gates, not commits and not additional tasks.

## Exact critical path

The path is strictly serial:

`entry/draft preservation -> Task 1 v2 request split + v1 workload restore -> Task 2 v2 predictor
split + v1 app/identity restore -> Task 3 static H2 firewall -> Task 4 behavioral H2 firewall ->
Task 5 closed golden inventory -> Task 6 independent v2 serving inventory/source archive -> Task 7
replace Task 1.6 drafts -> full CPU/security/publication/source-archive gates -> independent review ->
V02_W1_ADAPTER_FIREWALL_PASS / WAVE2_NOT_STARTED`

No task may run in parallel. Task 7 must not begin until Tasks 1–6 are committed and their targeted
gates pass.

## Exact implementation file allowlist

Only the following paths may change during future execution. A need for any other path is an
immediate stop for owner review.

| Action | Path | Responsibility |
|---|---|---|
| Restore | `src/mdcp/contracts/workload.py` | Exact frozen v1 request/response blob |
| Create | `src/mdcp/contracts/workload_v2.py` | `BikeRequestV2` and `BikeRequestEnvelope` only |
| Restore | `src/mdcp/predictor/app.py` | Exact frozen v1 predictor blob and v1 entry point |
| Create | `src/mdcp/predictor/app_v2.py` | v2 admission predictor and v2 entry point |
| Create | `src/mdcp/contracts/serving_identity_v2.py` | Closed v2 inventory and digest contract |
| Modify | `src/mdcp/temporal/adapter.py` | Import `BikeRequestV2` from versioned module |
| Modify | `src/mdcp/temporal/routing.py` | Import v2 contract from versioned module |
| Create | `src/mdcp/temporal/firewall.py` | Static and behavioral H2 firewall implementation |
| Create | `src/mdcp/temporal/golden_vectors.py` | Closed golden manifest verifier |
| Modify | `tests/contract/workload/test_v2_request_schema.py` | Versioned request-module tests |
| Modify | `tests/contract/workload/test_predictor_api.py` | v1-only API tests |
| Create | `tests/contract/workload/test_predictor_api_v2.py` | v2-only API/admission tests |
| Create | `tests/contract/workload/test_serving_identity_isolation.py` | v1 blobs, identity, descriptors, archive proof |
| Create | `tests/contract/workload/test_serving_identity_v2.py` | v2 inventory closure and archive proof |
| Modify | `tests/unit/temporal/test_adapter.py` | Versioned request import only |
| Modify | `tests/unit/temporal/test_routing.py` | Versioned request import only |
| Modify | `tests/security/temporal/test_data_firewall.py` | Static adversarial capability tests |
| Create | `tests/security/temporal/test_behavioral_data_firewall.py` | Executed denial-hook and sentinel tests |
| Create | `tests/temporal_archive_fixtures.py` | Deterministic synthetic 13,004-row archive recipe |
| Modify | `tests/fixtures/temporal/adapter-golden-vectors.json` | Exact 14-case closed inventory/digests |
| Modify | `tests/unit/temporal/test_golden_vectors.py` | Closed inventory and mutation tests |
| Modify last | `schemas/v2/temporal-contract-receipt.schema.json` | Final public receipt schema |
| Modify last | `src/mdcp/temporal/contract_gate.py` | Executed aggregate contract gate |
| Modify last | `tests/integration/temporal/test_contract_gate.py` | Reviewer/natural receipt recomputation |

Read-only inputs include `src/mdcp/contracts/release.py`, `src/mdcp/temporal/evidence.py`,
`src/mdcp/workload/dataset.py`, `src/mdcp/workload/features.py`, `src/mdcp/workload/splits.py`,
`schemas/v2/bike-request.schema.json`, `pyproject.toml`, and `uv.lock`. Their inclusion in a v2
inventory does not authorize editing them.

## Entry and preservation gate

- [ ] **Record the owner-authorized entry identity**

The execution authorization must name the exact branch, registered worktree, 40-hex entry HEAD, and
this plan commit. Transcribe that literal entry SHA into `$ownerEntrySha`; do not derive the expected
value from the worktree being checked. If the authorization omits it, stop.

- [ ] **Verify Git and H2 invariants without repairing them**

~~~powershell
$actualHead = git rev-parse HEAD
$actualBranch = git branch --show-current
$actualRemoteCount = @(git remote).Count
if ($actualHead -ne $ownerEntrySha) { throw "unexpected entry HEAD" }
if ($actualBranch -ne "codex/wave0-foundation-feasibility") { throw "unexpected branch" }
if ($actualRemoteCount -ne 0) { throw "remote must remain absent" }
uv run pytest tests/contract/temporal/test_historical_ledger.py -q
~~~

Expected: the exact owner entry, expected branch, zero remotes, H2 `SEALED_NOT_LOADED`, and loaded
rows `0`. Any mismatch stops without reset, stash, rebase, checkout, or cleanup.

- [ ] **Bind the required Git author and committer for the execution session**

~~~powershell
$env:GIT_AUTHOR_NAME = "kuotunyu"
$env:GIT_AUTHOR_EMAIL = "61350295+kuotunyu@users.noreply.github.com"
$env:GIT_COMMITTER_NAME = "kuotunyu"
$env:GIT_COMMITTER_EMAIL = "61350295+kuotunyu@users.noreply.github.com"
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
~~~

Expected: both identities begin with
`kuotunyu <61350295+kuotunyu@users.noreply.github.com>`. Remove these four task-scoped environment
values after the final Git/H2 check.

- [ ] **Verify the only dirty paths are the three preserved drafts**

Expected `git status --short --untracked-files=all`, in exact ASCII path order:

~~~text
?? schemas/v2/temporal-contract-receipt.schema.json
?? src/mdcp/temporal/contract_gate.py
?? tests/integration/temporal/test_contract_gate.py
~~~

- [ ] **Verify the draft identities before any implementation**

~~~powershell
Get-FileHash schemas/v2/temporal-contract-receipt.schema.json -Algorithm SHA256
Get-FileHash src/mdcp/temporal/contract_gate.py -Algorithm SHA256
Get-FileHash tests/integration/temporal/test_contract_gate.py -Algorithm SHA256
~~~

Expected, in the same order:

~~~text
5901faeebf1f471a33ab32e67cf9dca0094699d893bbe72f576abe7a3cb358d7
fb356c0d9bb41adfa7bc092a46833e2bc6fc69ce81179481af3c6c71240a6293
1170b869fb85c2e8ea5da580900734bd45eb08f9b43019f40c95010197b9a485
~~~

Compare all 64 characters emitted by `Get-FileHash`. A mismatch blocks execution. The drafts remain
byte-identical through Task 6.

- [ ] **Freeze protected tracked bytes for the final comparison**

Record a SHA-256 inventory outside Git for:

- all `evidence/**` files;
- all existing `tests/fixtures/artifacts/**` files;
- `src/mdcp/contracts/release.py` and every current `SERVING_PATHS` file except the two explicitly
  restored targets;
- `schemas/v1/**`, `docs/superpowers/specs/**`, every pre-existing plan, `pyproject.toml`, and
  `uv.lock`.

The inventory contains relative path, byte size, and SHA-256. It must match at the completion gate.

---

### Task 1: Correct Task 1.1 with a versioned v2 request module

**Files:**

- Create: `src/mdcp/contracts/workload_v2.py`
- Restore: `src/mdcp/contracts/workload.py`
- Modify: `src/mdcp/temporal/adapter.py`
- Modify: `src/mdcp/temporal/routing.py`
- Modify: `tests/contract/workload/test_v2_request_schema.py`
- Modify: `tests/unit/temporal/test_adapter.py`
- Modify: `tests/unit/temporal/test_routing.py`
- Modify: `tests/unit/temporal/test_golden_vectors.py` (import only)

**Interfaces:**

- Consumes frozen `BikeRequest`, `RequestId`, and `NormalizedFloat` from `workload.py`.
- Produces `BikeRequestV2`, `BikeRequestEnvelope = BikeRequest | BikeRequestV2`, and
  `BikeRequestV2.to_legacy() -> BikeRequest` from `workload_v2.py`.
- Leaves `schemas/v2/bike-request.schema.json` byte-identical.

- [ ] **Step 1: Write the module-boundary RED tests and redirect v2 test imports**

~~~python
from mdcp.contracts import workload as workload_v1
from mdcp.contracts.workload import BikeRequest
from mdcp.contracts.workload_v2 import BikeRequestEnvelope, BikeRequestV2


def test_v1_and_v2_request_modules_are_disjoint() -> None:
    assert BikeRequest.__module__ == "mdcp.contracts.workload"
    assert BikeRequestV2.__module__ == "mdcp.contracts.workload_v2"
    assert not hasattr(workload_v1, "BikeRequestV2")
    assert not hasattr(workload_v1, "BikeRequestEnvelope")
~~~

Update `adapter.py`, `routing.py`, and their tests to import `BikeRequestV2` from
`mdcp.contracts.workload_v2`. Do not touch either predictor module in this task.

- [ ] **Step 2: Run RED**

Run:

`uv run pytest tests/contract/workload/test_v2_request_schema.py tests/unit/temporal/test_adapter.py tests/unit/temporal/test_routing.py tests/unit/temporal/test_golden_vectors.py -q`

Expected: collection fails because `mdcp.contracts.workload_v2` does not exist. Preserve the actual
failure output; do not weaken the assertions.

- [ ] **Step 3: Create the v2 module and restore exact v1 bytes**

`workload_v2.py` defines the existing strict v2 model and union. It imports only the frozen v1
symbols it consumes:

~~~python
from mdcp.contracts.workload import BikeRequest, NormalizedFloat, RequestId


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


BikeRequestEnvelope = BikeRequest | BikeRequestV2
~~~

Move, rather than alias, the v2 definitions. Remove them and their now-unused imports from
`workload.py` until its bytes produce the required Git blob. Do not obtain v1 runtime bytes from Git;
the historical blob is only the migration comparison.

- [ ] **Step 4: Verify GREEN, exact blob, unchanged schema, and unchanged drafts**

Run each command separately:

~~~powershell
uv run pytest tests/unit/workload/test_contracts.py tests/contract/workload/test_v2_request_schema.py tests/unit/temporal/test_adapter.py tests/unit/temporal/test_routing.py tests/unit/temporal/test_golden_vectors.py -q
git hash-object src/mdcp/contracts/workload.py
git diff --exit-code $ownerEntrySha -- schemas/v2/bike-request.schema.json
Get-FileHash schemas/v2/temporal-contract-receipt.schema.json -Algorithm SHA256
Get-FileHash src/mdcp/temporal/contract_gate.py -Algorithm SHA256
Get-FileHash tests/integration/temporal/test_contract_gate.py -Algorithm SHA256
~~~

Expected: tests PASS; workload blob is
`33f174528e691f1f5ff2590c2c641d75669d5196`; the v2 schema has no diff; draft digests remain the
three entry values.

- [ ] **Step 5: Commit the scoped correction**

~~~powershell
git add src/mdcp/contracts/workload.py src/mdcp/contracts/workload_v2.py src/mdcp/temporal/adapter.py src/mdcp/temporal/routing.py tests/contract/workload/test_v2_request_schema.py tests/unit/temporal/test_adapter.py tests/unit/temporal/test_routing.py tests/unit/temporal/test_golden_vectors.py
git commit -m "fix: isolate the v2 workload contract"
~~~

---

### Task 2: Correct Task 1.3 with a versioned v2 predictor

**Files:**

- Create: `src/mdcp/predictor/app_v2.py`
- Restore: `src/mdcp/predictor/app.py`
- Modify: `tests/contract/workload/test_predictor_api.py`
- Create: `tests/contract/workload/test_predictor_api_v2.py`
- Create: `tests/contract/workload/test_serving_identity_isolation.py`

**Interfaces:**

- v1 continues to expose `mdcp.predictor.app:create_app` and `mdcp.predictor.app:app` only.
- v2 exposes `mdcp.predictor.app_v2:create_app` and `mdcp.predictor.app_v2:app`.
- `app_v2.py` owns `admission_role`, routing, v2 counters, and stable reduction. It must not import
  implementation helpers from `app.py`, because `app.py` is not in `V2_SERVING_PATHS`.

- [ ] **Step 1: Split v1/v2 tests and write RED identity assertions**

Keep the historical v1 request/response/error tests in `test_predictor_api.py`. Move every partial-v2,
role, routing, and temporal-vector assertion to `test_predictor_api_v2.py` and import the v2 app
explicitly.

~~~python
from mdcp.predictor.app import app as v1_app
from mdcp.predictor.app import create_app as create_v1_app
from mdcp.predictor.app_v2 import app as v2_app
from mdcp.predictor.app_v2 import create_app as create_v2_app


def test_entry_points_are_explicit_and_distinct() -> None:
    assert v1_app is not v2_app
    assert create_v1_app.__module__ == "mdcp.predictor.app"
    assert create_v2_app.__module__ == "mdcp.predictor.app_v2"
~~~

In `test_serving_identity_isolation.py`, calculate Git blob IDs without invoking Git:

~~~python
def git_blob_id(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def test_current_v1_bytes_and_identity_are_frozen(repo_root: Path) -> None:
    assert git_blob_id((repo_root / "src/mdcp/contracts/workload.py").read_bytes()) == (
        "33f174528e691f1f5ff2590c2c641d75669d5196"
    )
    assert git_blob_id((repo_root / "src/mdcp/predictor/app.py").read_bytes()) == (
        "9fdee53bead221f0698d2e4a52407a4901c37649"
    )
    assert serving_inventory_digest(serving_inventory_from_root(repo_root)) == (
        "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"
    )
~~~

Also copy the exact current `SERVING_PATHS` bytes into `tmp_path / "source-archive"`, assert there is
no `.git`, recompute the same v1 identity from that root, and run `verify_reviewer_fixtures` against
the unchanged checked-in descriptors.

- [ ] **Step 2: Run RED**

Run:

`uv run pytest tests/contract/workload/test_predictor_api.py tests/contract/workload/test_predictor_api_v2.py tests/contract/workload/test_serving_identity_isolation.py -q`

Expected: FAIL because `app_v2.py` is absent, `app.py` still owns v2 behavior, its blob is wrong, and
current-tree v1 identity does not equal the frozen value.

- [ ] **Step 3: Create the independent v2 app and restore v1 app bytes**

Move the existing admission-aware implementation to `app_v2.py`. Define its error helper and route
locally so it has no dependency on `app.py`:

~~~python
def _error(status_code: int, error_code: str, request_id: str | None = None) -> JSONResponse:
    body = SafeErrorResponse(request_id=request_id, error_code=error_code)
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def create_app(
    runtime: PredictorRuntime,
    *,
    admission_role: ExecutionRole = ExecutionRole.STABLE,
) -> FastAPI:
    application = FastAPI(title="MDCP v2 immutable ONNX predictor", docs_url=None, redoc_url=None)
    application.state.admission_counts = {kind: 0 for kind in AdmissionKind}

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        del request, error
        return _error(422, "INVALID_REQUEST")

    @application.exception_handler(Exception)
    async def internal_error(request: Request, error: Exception) -> JSONResponse:
        del request, error
        return _error(500, "INTERNAL_ERROR")

    @application.get("/health/ready")
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @application.post("/v1/predict", response_model=PredictionResponse)
    async def predict(payload: dict[str, object]) -> PredictionResponse | JSONResponse:
        try:
            decision = classify_envelope(payload)
        except ValidationError:
            return _error(422, "INVALID_REQUEST")
        application.state.admission_counts[decision.kind] += 1
        if decision.kind is AdmissionKind.INVALID_V2:
            return _error(422, decision.reason_code or "INVALID_V2_ENVELOPE")
        if decision.kind is AdmissionKind.LEGACY_STABLE_ONLY:
            if admission_role is not ExecutionRole.STABLE:
                return _error(422, AdmissionKind.LEGACY_STABLE_ONLY.value)
            if decision.legacy_request is None:
                return _error(422, "INVALID_REQUEST")
            runtime_request = decision.legacy_request
            request_id = decision.legacy_request.request_id
        else:
            if decision.v2_request is None:
                return _error(422, "INVALID_V2_ENVELOPE")
            request_id = decision.v2_request.request_id
            if admission_role is ExecutionRole.STABLE:
                runtime_request = decision.v2_request.to_legacy()
            else:
                if decision.feature_vector is None:
                    return _error(422, "INVALID_V2_ENVELOPE")
                runtime_request = decision.feature_vector
        try:
            value = runtime.predict(runtime_request)
            if not math.isfinite(value) or value < 0:
                raise PredictionContractError("invalid model output")
        except PredictionContractError:
            return _error(500, "INVALID_MODEL_OUTPUT", request_id)
        return PredictionResponse(
            request_id=request_id,
            release_id=runtime.release_id,
            prediction=value,
            route_revision=runtime.route_revision,
        )

    return application


def runtime_from_environment() -> OnnxPredictor:
    descriptor_path = Path(os.environ["MDCP_DESCRIPTOR_PATH"])
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    onnx_metadata = descriptor.get("onnx", descriptor)
    expected_sha256 = onnx_metadata.get("sha256") or onnx_metadata["onnx_sha256"]
    return OnnxPredictor(
        onnx_path=Path(os.environ["MDCP_ONNX_PATH"]),
        expected_sha256=expected_sha256,
        release_id=os.environ["MDCP_RELEASE_ID"],
        route_revision=int(os.environ["MDCP_ROUTE_REVISION"]),
    )


app = create_app(runtime_from_environment()) if os.getenv("MDCP_ONNX_PATH") else FastAPI()
~~~

Legacy is stable-only, partial/invalid v2 is rejected before runtime selection, stable reduces valid
v2 to `BikeRequest`, candidate receives only `TemporalFeatureVector`, and counters are keyed by
`AdmissionKind`. Do not import `_error`, `create_app`, or `app` from v1.

Remove all v2 imports, role arguments, counters, and routing from `app.py` until its Git blob is exact.

- [ ] **Step 4: Run GREEN and both identity modes**

Run separately:

~~~powershell
uv run pytest tests/contract/workload/test_predictor_api.py tests/contract/workload/test_predictor_api_v2.py tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_wave1_inventory.py -q
git hash-object src/mdcp/contracts/workload.py
git hash-object src/mdcp/predictor/app.py
uv run python -c "from pathlib import Path; from mdcp.contracts.release import serving_inventory_digest, serving_inventory_from_root; print(serving_inventory_digest(serving_inventory_from_root(Path.cwd())))"
~~~

Expected: both API suites PASS; blob IDs equal the two locked IDs; the printed current-tree v1
identity is `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`; existing descriptors
verify without edits; source-archive recomputation passes without `.git`.

- [ ] **Step 5: Commit the scoped correction**

~~~powershell
git add src/mdcp/predictor/app.py src/mdcp/predictor/app_v2.py tests/contract/workload/test_predictor_api.py tests/contract/workload/test_predictor_api_v2.py tests/contract/workload/test_serving_identity_isolation.py
git commit -m "fix: isolate the v2 predictor entry point"
~~~

Before Task 3, recheck the three draft hashes. Any change blocks execution.

---

### Task 3: Replace the direct-symbol scan with a static capability firewall

**Files:**

- Create: `src/mdcp/temporal/firewall.py`
- Modify: `tests/security/temporal/test_data_firewall.py`

**Interfaces:**

- Produces `FORMAL_V2_FIXED_PATHS`, `FORMAL_TEMPORAL_PACKAGE_ROOT`, `StaticFirewallResult`,
  `StaticFirewallError(reason_code)`, and
  `audit_static_h2_firewall(repository_root, *, formal_paths=None)`.
- The default discovery is deterministic and fail-closed:

~~~python
FORMAL_V2_FIXED_PATHS = (
    "src/mdcp/contracts/workload_v2.py",
    "src/mdcp/predictor/app_v2.py",
)
FORMAL_TEMPORAL_PACKAGE_ROOT = "src/mdcp/temporal"
~~~

With `formal_paths=None`, scan both fixed paths plus every ASCII-sorted `*.py` file directly under
`src/mdcp/temporal`. This includes new participating modules automatically when Tasks 5 and 7 add
them and prevents an unlisted temporal module from bypassing the firewall. Tests may pass explicit
temporary logical paths only to exercise adversarial syntax. A missing fixed path, missing package
root, syntax error, unresolved dynamic import, or unsafe import form fails closed.

- [ ] **Step 1: Write adversarial RED tests**

Create temporary modules covering every form below and require one fixed reason code without echoing
source text or private paths:

~~~python
FORBIDDEN_MODULES = {
    "direct": "from mdcp.workload.dataset import load_uci_archive",
    "from_alias": "from mdcp.workload.splits import split_rows as narrow",
    "module": "import mdcp.workload.dataset\ntarget = mdcp.workload.dataset.load_uci_archive",
    "module_alias": "import mdcp.workload.splits as parts\ntarget = parts.split_rows",
    "package_member": "from mdcp.workload import splits as parts\nparts.DatasetPartitions",
    "dynamic_literal": "import importlib\nimportlib.import_module('mdcp.workload.dataset')",
    "dunder_import": "__import__('mdcp.workload.splits')",
    "dynamic_unknown": "import importlib\nimportlib.import_module(name)",
}
~~~

Add allowed cases for direct imports of only `load_uci_development_archive`,
`DevelopmentPartitions`, and `split_development_rows`. Add forbidden qualified access to
`DatasetPartitions`, `open_h2`, `load_uci_archive`, and `split_rows`, including aliases.

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/security/temporal/test_data_firewall.py -q`

Expected: the old test-local name collector accepts at least module aliases, qualified access, and
dynamic imports; production `audit_static_h2_firewall` is absent.

- [ ] **Step 3: Implement normalized AST analysis**

Build an import table before checking use:

~~~python
@dataclass(frozen=True)
class ImportBinding:
    local_name: str
    qualified_name: str


@dataclass(frozen=True)
class StaticFirewallResult:
    schema_version: Literal["mdcp.static-h2-firewall.v1"]
    verdict: Literal["PASS"]
    checked_paths: tuple[str, ...]
    implementation_sha256: Sha256
~~~

Resolve `Import`, `ImportFrom`, aliases, attribute chains, `importlib.import_module`, and
`__import__`. Permit only the three narrow direct symbols. Importing `mdcp.workload.dataset` or
`mdcp.workload.splits` as a module is forbidden because the module exposes the legacy API. Reject
computed dynamic import arguments as unresolved. Results serialize relative logical paths only.

- [ ] **Step 4: Run GREEN and scan the real formal source set**

Run:

`uv run pytest tests/security/temporal/test_data_firewall.py tests/unit/workload/test_development_loader.py -q`

Expected: every adversarial module fails closed, narrow direct imports pass, the real formal source
set passes, and `DevelopmentPartitions` exposes only `train` and `h1`.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/firewall.py tests/security/temporal/test_data_firewall.py
git commit -m "security: close temporal import capability paths"
~~~

---

### Task 4: Execute a behavioral H2 firewall under denial hooks

**Files:**

- Modify: `src/mdcp/temporal/firewall.py`
- Create: `tests/temporal_archive_fixtures.py`
- Create: `tests/security/temporal/test_behavioral_data_firewall.py`

**Interfaces:**

- Produces `DevelopmentBoundaryResult`, `BehavioralFirewallResult`,
  `run_development_boundary(archive_path, expected_sha256) -> DevelopmentBoundaryResult`, and
  `run_behavioral_h2_firewall(archive_path, expected_sha256, *, fixture_recipe_sha256) ->
  BehavioralFirewallResult`.
- The function calls the production `load_uci_development_archive` and
  `split_development_rows`; it never substitutes a test loader.
- It installs a scoped `pandas.read_csv` spy to require exactly one call with `nrows=13_003`, plus a
  scoped Python call-profile denial hook for actual calls to `load_uci_archive`, `split_rows`, and
  `DatasetPartitions.open_h2`. Hooks are always restored in `finally`.

- [ ] **Step 1: Create the deterministic archive recipe and RED tests**

`tests/temporal_archive_fixtures.py` creates exactly 13,004 chronological hourly rows beginning at
2011-01-01, with the final row at the H2 boundary. It writes `Readme.txt`, `day.csv`, and `hour.csv`
using fixed ZIP member timestamps and permissions. It uses no environment, clock, random, network,
or external file.

~~~python
SYNTHETIC_METADATA = {
    "evidence_class": "synthetic_test",
    "source_kind": "deterministic_generated",
    "uci_rows": 0,
}


def test_behavioral_gate_stops_before_sentinel(synthetic_archive: ArchiveFixture) -> None:
    result = run_behavioral_h2_firewall(
        synthetic_archive.path,
        synthetic_archive.sha256,
        fixture_recipe_sha256=synthetic_archive.recipe_sha256,
    )
    boundary = result.body.development_boundary
    assert boundary.development_row_count == 13_003
    assert boundary.train_row_count == 8_645
    assert boundary.h1_row_count == 4_358
    assert boundary.read_csv_nrows == (13_003,)
    assert boundary.forbidden_call_counts == {
        "load_uci_archive": 0,
        "split_rows": 0,
        "DatasetPartitions.open_h2": 0,
    }
    assert boundary.h2_status == "SEALED_NOT_LOADED"
    assert boundary.h2_loaded_rows == 0
~~~

Monkeypatch the imported narrow loader/splitter, one test at a time, so it attempts each actual
legacy capability. Each attempt must raise `BehavioralFirewallError("FORBIDDEN_CAPABILITY_CALLED")`
before the legacy body returns. Assert hook restoration after success and failure.

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/security/temporal/test_behavioral_data_firewall.py -q`

Expected: FAIL importing `BehavioralFirewallResult` and `run_behavioral_h2_firewall`.

- [ ] **Step 3: Implement the scoped spies and public-safe result**

~~~python
@dataclass(frozen=True)
class DevelopmentBoundaryResult:
    schema_version: Literal["mdcp.development-boundary.v1"]
    verdict: Literal["PASS"]
    archive_sha256: Sha256
    development_row_count: Literal[13_003]
    development_rows_sha256: Sha256
    train_row_count: Literal[8_645]
    train_rows_sha256: Sha256
    h1_row_count: Literal[4_358]
    h1_rows_sha256: Sha256
    read_csv_nrows: tuple[Literal[13_003]]
    forbidden_call_counts: Mapping[str, Literal[0]]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]


@dataclass(frozen=True)
class BehavioralFirewallBody:
    schema_version: Literal["mdcp.behavioral-h2-firewall.v1"]
    verdict: Literal["PASS"]
    fixture_recipe_sha256: Sha256
    development_boundary: DevelopmentBoundaryResult
    static_firewall_implementation_sha256: Sha256
    behavioral_firewall_implementation_sha256: Sha256
    bounded_loader_implementation_sha256: Sha256
    development_split_implementation_sha256: Sha256


@dataclass(frozen=True)
class BehavioralFirewallResult:
    body: BehavioralFirewallBody
    behavioral_result_sha256: Sha256
~~~

Compute `behavioral_result_sha256` over the RFC 8785 `body`; the digest is a sibling and is not in
the bytes it hashes. Do not include the
archive path, raw row, timestamp, sentinel, exception, environment, or raw function object. On any
count, row boundary, partition count, or hook-restoration mismatch, raise a fixed sanitized error and
produce no PASS result. `run_development_boundary` performs the same scoped read spy, denial hook,
row accounting, and partition accounting but omits synthetic recipe metadata; it is the natural
13,003-row integration surface. `run_behavioral_h2_firewall` calls that exact function and adds the
deterministic reviewer recipe identity, so the reviewer and natural modes cannot drift into separate
loaders.

- [ ] **Step 4: Run GREEN**

Run:

`uv run pytest tests/security/temporal/test_behavioral_data_firewall.py tests/unit/workload/test_development_loader.py tests/security/temporal/test_data_firewall.py -q`

Expected: synthetic sentinel is never returned or hashed into the development identity; all three
forbidden counts are zero on the production development path; adversarial calls fail closed.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/firewall.py tests/temporal_archive_fixtures.py tests/security/temporal/test_behavioral_data_firewall.py
git commit -m "security: execute the behavioral H2 firewall"
~~~

---

### Task 5: Close the exact 14-case golden-vector inventory

**Files:**

- Create: `src/mdcp/temporal/golden_vectors.py`
- Modify: `tests/fixtures/temporal/adapter-golden-vectors.json`
- Modify: `tests/unit/temporal/test_golden_vectors.py`

**Interfaces:**

- Produces `GOLDEN_CASE_IDS`, `GoldenInventoryResult`, and
  `verify_golden_vector_manifest(path) -> GoldenInventoryResult`.
- Preserves every approved payload, expected result/reason, float64 digest, and float32 digest. It
  adds per-case and aggregate inventory identities; it does not regenerate expected values.

- [ ] **Step 1: Write RED closed-set and mutation tests**

~~~python
EXPECTED_CASE_IDS = (
    "origin", "year_end_category_maxima", "leap_day", "spring_before", "spring_after",
    "fall_edt", "fall_est", "malformed_timestamp", "nonexistent_local_time",
    "wrong_ambiguous_offset", "cross_field_mismatch", "before_lower_bound",
    "last_accepted_hour", "exact_upper_bound",
)


def test_manifest_is_exact_ordered_inventory() -> None:
    result = verify_golden_vector_manifest(GOLDEN_VECTORS)
    assert result.case_ids == EXPECTED_CASE_IDS
    assert result.case_count == 14
~~~

For copies under `tmp_path`, require rejection of missing, extra, duplicate, renamed, reordered,
payload-mutated, expected-reason-mutated, float64-mutated, float32-digest-mutated,
`case_sha256`-mutated, and aggregate-inventory-digest-mutated manifests. Accepted cases must have
exactly payload/result/float digests; rejected cases must have exactly payload/reason and no vector
or float digest.

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/unit/temporal/test_golden_vectors.py -q`

Expected: the existing set-based test accepts reorder and lacks per-case/aggregate identities;
`golden_vectors.py` is absent.

- [ ] **Step 3: Implement canonical case and inventory digests**

For each case, compute:

~~~python
case_sha256 = sha256_hex(canonicalize_json(case_body_without_case_sha256))
case_inventory = tuple(
    {"id": case["id"], "case_sha256": case["case_sha256"]} for case in vectors
)
case_inventory_sha256 = sha256_hex(canonicalize_json(case_inventory))
~~~

The manifest key set, exact case key sets, feature columns, temporal schema ID, float contract, case
order, case count, production adapter output, and all digests are validated before returning PASS.
Error messages contain only fixed reason codes.

- [ ] **Step 4: Run GREEN**

Run:

`uv run pytest tests/unit/temporal/test_golden_vectors.py tests/unit/temporal/test_adapter.py tests/security/temporal/test_public_evidence_boundary.py -q`

Expected: exact 14-case inventory recomputes; every mutation fails; public scanner accepts only the
sanitized result fields.

- [ ] **Step 5: Commit**

~~~powershell
git add src/mdcp/temporal/golden_vectors.py tests/fixtures/temporal/adapter-golden-vectors.json tests/unit/temporal/test_golden_vectors.py
git commit -m "test: close the temporal golden inventory"
~~~

---

### Task 6: Add the independent v2 serving inventory and archive proof

**Files:**

- Create: `src/mdcp/contracts/serving_identity_v2.py`
- Create: `tests/contract/workload/test_serving_identity_v2.py`

**Interfaces:**

- Produces `V2_SERVING_PATHS`, `V2InventoryEntry`, `V2ServingInventoryBody`,
  `V2ServingInventoryResult`, `build_v2_serving_inventory(repository_root, declared_paths)`, and
  `verify_v2_serving_inventory(repository_root, declared_result)`.
- Does not import, mutate, wrap, or reinterpret v1 `ServingInventory`.

- [ ] **Step 1: Write RED exact-inventory tests**

The required tuple is the exact ASCII-sorted set from amendment §5.2:

~~~python
V2_SERVING_PATHS = (
    "pyproject.toml",
    "schemas/v2/bike-request.schema.json",
    "schemas/v2/temporal-contract-receipt.schema.json",
    "src/mdcp/common/canonical.py",
    "src/mdcp/common/digests.py",
    "src/mdcp/common/enums.py",
    "src/mdcp/contracts/serving_identity_v2.py",
    "src/mdcp/contracts/workload.py",
    "src/mdcp/contracts/workload_v2.py",
    "src/mdcp/predictor/app_v2.py",
    "src/mdcp/predictor/runtime.py",
    "src/mdcp/temporal/adapter.py",
    "src/mdcp/temporal/constants.py",
    "src/mdcp/temporal/contract_gate.py",
    "src/mdcp/temporal/evidence.py",
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/golden_vectors.py",
    "src/mdcp/temporal/routing.py",
    "src/mdcp/workload/dataset.py",
    "src/mdcp/workload/features.py",
    "src/mdcp/workload/splits.py",
    "tests/fixtures/temporal/adapter-golden-vectors.json",
    "uv.lock",
)
~~~

Require fixed `schema_version="mdcp.v2-serving-inventory.v1"`, fixed
`entry_point="mdcp.predictor.app_v2:app"`, exact order, safe POSIX relative paths, and one raw-byte
SHA-256 per path. Mutation tests cover missing, extra, duplicate, unknown, reordered, unsafe,
unreadable, and wrong-digest entries.

- [ ] **Step 2: Run RED**

Run: `uv run pytest tests/contract/workload/test_serving_identity_v2.py -q`

Expected: FAIL importing `mdcp.contracts.serving_identity_v2`.

- [ ] **Step 3: Implement the acyclic inventory**

~~~python
class V2ServingInventoryBody(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["mdcp.v2-serving-inventory.v1"]
    entry_point: Literal["mdcp.predictor.app_v2:app"]
    entries: tuple[V2InventoryEntry, ...]


class V2ServingInventoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    body: V2ServingInventoryBody
    inventory_sha256: Sha256
~~~

Validate the ordered input list before constructing a map. Compute `inventory_sha256` only over the
RFC 8785 body. The body does not contain the digest, receipt bytes, Git SHA, future commit identity,
absolute root, or environment value.

- [ ] **Step 4: Prove current-tree and source-archive recomputation**

The test copies the repository to `tmp_path / "source-archive"` while excluding `.git`, `.worktrees`,
virtual environments, caches, and runtime/data directories. It launches the current Python
interpreter with the copied `src` first on `sys.path`, an empty command-search path, and no Git
command. From the copied source, it recomputes:

- v1 identity `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`;
- the same v2 body and aggregate digest as the current tree;
- both explicit entry points.

Run:

`uv run pytest tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py -q`

Expected: PASS with `.git` absent and all inventory mutation cases rejected.

- [ ] **Step 5: Verify drafts are still unchanged, then commit**

Recompute the three locked draft SHA-256 values. Only if all three still match:

~~~powershell
git add src/mdcp/contracts/serving_identity_v2.py tests/contract/workload/test_serving_identity_v2.py
git commit -m "feat: define the v2 serving inventory"
~~~

---

### Task 7: Replace the preserved Task 1.6 drafts and close Wave 1

**Files:**

- Modify: `schemas/v2/temporal-contract-receipt.schema.json`
- Modify: `src/mdcp/temporal/contract_gate.py`
- Modify: `tests/integration/temporal/test_contract_gate.py`

These are the only files in this task. At its start, verify their original three SHA-256 values one
last time. They are then intentionally replaced in place; do not commit the provisional bytes first.

**Interfaces:**

- Produces `DevelopmentIdentity`, `TemporalContractReceipt`, and
  `build_temporal_contract_receipt(repository_root, *, reviewer_archive_path,
  reviewer_archive_sha256, reviewer_recipe_sha256, development_archive_path,
  development_archive_sha256, expected_development_identity) -> TemporalContractReceipt`.
- The builder executes schema equality, routing truth table, feature-lineage audit, static firewall,
  behavioral firewall, golden verifier, v1 identity, v2 inventory, and public-evidence validation.
  Hashing a checker without calling it cannot yield PASS. `.git`-free source-archive recomputation
  remains a separate mandatory integration gate because a current-tree receipt cannot truthfully
  claim that its own root lacks `.git`.

- [ ] **Step 1: Rewrite the integration tests first and observe RED**

The final receipt has an exact ordered check tuple:

~~~python
CHECK_IDS = (
    "V1_SERVING_IDENTITY",
    "V2_REQUEST_SCHEMA",
    "V2_ENTRY_POINT",
    "V2_SERVING_INVENTORY",
    "ROUTING_TRUTH_TABLE",
    "DEVELOPMENT_BOUNDARY",
    "FEATURE_LINEAGE",
    "STATIC_H2_FIREWALL",
    "BEHAVIORAL_H2_FIREWALL",
    "GOLDEN_VECTOR_INVENTORY",
    "PUBLIC_EVIDENCE",
)
~~~

Tests require:

- the complete ordered v2 logical path/SHA-256 inventory and its digest;
- fixed v1 identity and explicit v1/v2 entry points;
- exact request and receipt schema bytes;
- exact 14-case IDs/count/inventory digest and outer manifest digest;
- exact routing result digest and 18-field lineage digest;
- static result digest and executed behavioral body/result digest;
- forbidden call counts all zero and row counts 13,003/8,645/4,358;
- H2 `SEALED_NOT_LOADED` and loaded rows `0`;
- repeated assembly byte equality without a receipt self-digest or commit SHA;
- schema rejects missing, extra, duplicate, reordered, or unknown inventory paths;
- spies prove every named checker is called exactly once;
- forcing any checker to raise prevents PASS;
- `public_evidence_violations(receipt.model_dump(mode="json")) == ()`;
- no serialized raw archive path, timestamp, row, exception, environment, sentinel, or credential.

Run: `uv run pytest tests/integration/temporal/test_contract_gate.py -q`

Expected: FAIL because the preserved draft imports v2 from `workload.py`, accepts a precomputed
development identity without executing the bounded path, has only eight checks, hashes a firewall
test, and lacks the closed v2 inventory.

- [ ] **Step 2: Implement the final acyclic receipt model and builder**

Keep `schema_version="mdcp.temporal-contract-receipt.v1"`; the provisional draft was never committed
or published. Replace partial `source_code_sha256` and test-file hashes with the exact v2 serving
inventory and executed result identities.

~~~python
ExactCheckIds = tuple[
    Literal["V1_SERVING_IDENTITY"],
    Literal["V2_REQUEST_SCHEMA"],
    Literal["V2_ENTRY_POINT"],
    Literal["V2_SERVING_INVENTORY"],
    Literal["ROUTING_TRUTH_TABLE"],
    Literal["DEVELOPMENT_BOUNDARY"],
    Literal["FEATURE_LINEAGE"],
    Literal["STATIC_H2_FIREWALL"],
    Literal["BEHAVIORAL_H2_FIREWALL"],
    Literal["GOLDEN_VECTOR_INVENTORY"],
    Literal["PUBLIC_EVIDENCE"],
]
ExactGoldenCaseIds = tuple[
    Literal["origin"],
    Literal["year_end_category_maxima"],
    Literal["leap_day"],
    Literal["spring_before"],
    Literal["spring_after"],
    Literal["fall_edt"],
    Literal["fall_est"],
    Literal["malformed_timestamp"],
    Literal["nonexistent_local_time"],
    Literal["wrong_ambiguous_offset"],
    Literal["cross_field_mismatch"],
    Literal["before_lower_bound"],
    Literal["last_accepted_hour"],
    Literal["exact_upper_bound"],
]


class TemporalContractReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["mdcp.temporal-contract-receipt.v1"]
    verdict: Literal["PASS"]
    check_ids: ExactCheckIds
    v1_serving_identity: Literal[
        "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"
    ]
    v1_entry_point: Literal["mdcp.predictor.app:app"]
    v2_entry_point: Literal["mdcp.predictor.app_v2:app"]
    v2_serving_inventory: V2ServingInventoryBody
    v2_serving_inventory_sha256: Sha256
    request_schema_sha256: Sha256
    receipt_schema_sha256: Sha256
    temporal_schema_id: Literal["mdcp.temporal-features.v0.2"]
    feature_count: Literal[18]
    archive_sha256: Sha256
    development_row_count: Literal[13_003]
    development_rows_sha256: Sha256
    train_row_count: Literal[8_645]
    train_rows_sha256: Sha256
    h1_row_count: Literal[4_358]
    h1_rows_sha256: Sha256
    development_identity_sha256: Sha256
    routing_truth_table_sha256: Sha256
    feature_lineage_sha256: Sha256
    static_firewall_result_sha256: Sha256
    golden_case_ids: ExactGoldenCaseIds
    golden_case_count: Literal[14]
    golden_case_inventory_sha256: Sha256
    golden_manifest_sha256: Sha256
    behavioral_firewall: BehavioralFirewallBody
    behavioral_result_sha256: Sha256
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
~~~

The receipt does not contain its own serialized SHA-256. `receipt_schema_sha256` may hash the schema
file because the schema does not embed that digest. The v2 inventory may hash `contract_gate.py`, the
schema, and golden manifest because none embeds the resulting inventory digest in its own source.

Execute `run_behavioral_h2_firewall` on the deterministic reviewer archive and bind its recipe/result
identities. Execute `run_development_boundary` on the separately supplied development archive,
derive its identity from the returned production partitions, and compare it to the caller's expected
identity. Treat that expected identity as an equality assertion, not evidence sufficient to skip
execution. In reviewer-fast-path tests, the deterministic archive fills both archive roles; in the
formal local gate, the reviewer role remains deterministic and the development role is the approved
natural 13,003-row prefix.

- [ ] **Step 3: Run reviewer-fast-path GREEN**

Run:

`uv run pytest tests/integration/temporal/test_contract_gate.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_behavioral_data_firewall.py tests/unit/temporal/test_golden_vectors.py tests/contract/workload/test_serving_identity_v2.py -q`

Expected: synthetic reviewer fixture PASS, no GPU and no UCI access, all named checks executed, H2
zero, exact inventory and receipt schema equality.

- [ ] **Step 4: Run the separately authorized natural development-prefix gate**

Before parsing, verify only this archive identity:

~~~text
D:/model-delivery-control-plane-runtime/wave1/data/raw/bike-sharing-dataset.zip
size: 279992 bytes
SHA-256: b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401
~~~

The integration test reads the path through `MDCP_UCI_ARCHIVE` only when
`MDCP_REQUIRE_NATURAL_GATE=1`; without that flag it runs the synthetic reviewer path and marks the
natural integration case skipped. The formal completion command sets both values and requires the
named natural test to report one PASS and zero skips. The path is never serialized.

~~~powershell
$env:MDCP_REQUIRE_NATURAL_GATE = "1"
$env:MDCP_UCI_ARCHIVE = "D:/model-delivery-control-plane-runtime/wave1/data/raw/bike-sharing-dataset.zip"
uv run pytest tests/integration/temporal/test_contract_gate.py::test_approved_development_prefix_receipt_recomputes -q -rs
Remove-Item Env:MDCP_REQUIRE_NATURAL_GATE
Remove-Item Env:MDCP_UCI_ARCHIVE
~~~

Expected: archive size/digest exact; bounded reader called once with `nrows=13_003`; 13,003/8,645/
4,358 rows; forbidden capability counts zero; H2 loaded rows zero. Any skip, failure, later-row read,
or identity mismatch blocks the task.

- [ ] **Step 5: Run the complete Wave 1 gate before committing the drafts**

Run every command separately:

~~~powershell
uv run pytest tests/unit/workload tests/unit/temporal tests/contract/workload tests/contract/temporal tests/integration/temporal tests/security/temporal -q
uv run pytest tests/contract/workload/test_predictor_api.py tests/contract/workload/test_predictor_api_v2.py -q
uv run pytest tests/security/temporal tests/security/validator tests/publication -q
uv run pytest -q
uv run ruff check src/mdcp tests
uv run ruff format --check src/mdcp/contracts/workload_v2.py src/mdcp/contracts/serving_identity_v2.py src/mdcp/predictor/app_v2.py src/mdcp/temporal/adapter.py src/mdcp/temporal/routing.py src/mdcp/temporal/firewall.py src/mdcp/temporal/golden_vectors.py src/mdcp/temporal/contract_gate.py tests/contract/workload/test_v2_request_schema.py tests/contract/workload/test_predictor_api.py tests/contract/workload/test_predictor_api_v2.py tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_adapter.py tests/unit/temporal/test_routing.py tests/unit/temporal/test_golden_vectors.py tests/security/temporal/test_data_firewall.py tests/security/temporal/test_behavioral_data_firewall.py tests/temporal_archive_fixtures.py tests/integration/temporal/test_contract_gate.py
uv lock --check
git diff --check
~~~

Expected: all executable tests PASS; reviewer-only run may have only the explicitly documented
natural-prefix skip; the required natural command has zero skips; Ruff, lock, and diff checks exit 0.

- [ ] **Step 6: Commit the final Task 1.6 replacement**

~~~powershell
git add schemas/v2/temporal-contract-receipt.schema.json src/mdcp/temporal/contract_gate.py tests/integration/temporal/test_contract_gate.py
git commit -m "feat: bind the isolated Wave 1 contract"
~~~

The commit must contain exactly those three paths. This is the first commit that tracks them.

---

## Plan authoring self-review

| Review invariant | Result |
|---|---|
| Amendment §§3–4 v1/v2 module and entry-point isolation | Covered by Tasks 1–2 |
| Required v1 blobs and frozen current-tree identity | Covered by Tasks 1–2 and completion gate |
| v1 and v2 recomputation with `.git` absent | Covered by Tasks 2 and 6 |
| Amendment §5 exact 23-path v2 inventory and mutation closure | Covered by Task 6 |
| Inventory and receipt identity graph has no self-hash or future-commit cycle | Covered by Tasks 6–7 |
| Amendment §6 static direct/alias/qualified/dynamic import coverage | Covered by Task 3 |
| Behavioral denial hooks, `nrows=13_003`, counts 13,003/8,645/4,358, H2 zero | Covered by Task 4 and Task 7 natural gate |
| Amendment §7 exact ordered 14-case inventory and all content/digest mutations | Covered by Task 5 |
| Task 1.6 cannot PASS from hashes without executing named checks | Covered by Task 7 checker spies and forced failures |
| Three provisional drafts remain byte-identical through Task 6 and are committed only in Task 7 | Enforced by entry and per-task digest gates |
| Historical v0.1 evidence, old plan, dependency lock, specs, and non-target v1 bytes remain immutable | Enforced by allowlist and protected-byte inventory |
| Full CPU, security, publication, natural-prefix, source-archive, and independent-review gates | Covered by Task 7 and completion gate |
| Placeholder, unresolved architecture choice, type-name drift, or unowned implementation path | None |
| Wave 2 authorization or executable Wave 2 step | None; explicitly forbidden |

The plan has one owner per created path, an explicit commit boundary for each of seven tasks, and no
implementation command that fits a model, loads real H2, exports ONNX, starts Docker/GPU, uses a
network, or publishes externally.

---

## Wave 1 completion and independent-review gate

- [ ] **Re-run fresh verification from the committed tree**

Repeat Task 7 Step 5 after the commit, including the required natural-prefix command with its two
temporary environment values. Prior output is not completion evidence.

- [ ] **Recompute both identities from current tree and a `.git`-free source archive**

Required current-tree and archive results:

- v1 workload blob `33f174528e691f1f5ff2590c2c641d75669d5196`;
- v1 app blob `9fdee53bead221f0698d2e4a52407a4901c37649`;
- v1 serving identity `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`;
- exact v2 path inventory and identical v2 inventory digest in both modes;
- v1 and v2 entry points remain distinct;
- no verifier calls Git or requires `.git`.

- [ ] **Compare protected bytes to the entry inventory**

The preflight and completion inventories for protected evidence, v0.1 artifacts, non-target
`SERVING_PATHS`, v1 schemas, old specs/plans, `pyproject.toml`, and `uv.lock` must be byte-identical.
The historical Wave 1 plan must have no diff. The only former drafts are now tracked in the final
Task 7 commit; no historical evidence was regenerated.

- [ ] **Run public-evidence and credential/private-path audit**

~~~powershell
uv run pytest tests/security/temporal/test_public_evidence_boundary.py tests/publication -q
git grep -n -I -E "(BEGIN (RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY|ghp_[A-Za-z0-9]{36}|github_pat_|hf_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|Bearer[[:space:]]+[A-Za-z0-9._-]{20,})" -- schemas/v2 src/mdcp tests ":!tests/security/temporal/test_public_evidence_boundary.py"
~~~

Expected: tests PASS and grep returns no credential-shaped secret in production, schemas, fixtures,
or non-adversarial tests. The excluded security test intentionally contains inert pattern examples;
its own assertions prove that such values are rejected and never echoed.

- [ ] **Obtain an independent read-only code review**

The reviewer examines the owner-authorized entry-to-final diff, approved amendment, this plan,
source-archive tests, receipt schema, and all failure boundaries. The review explicitly checks:

- Critical findings: `0`;
- Important findings: `0`;
- no v1 `SERVING_PATHS` drift or evidence mutation;
- no v2 import/entry-point ambiguity;
- no H2 import, alias, qualified, dynamic, or behavioral bypass;
- exact golden case completeness and digest closure;
- exact v2 inventory closure and no identity cycle;
- no hash-only substitute for executed Task 1.6 checks;
- no private/publication leakage and no file outside the allowlist.

Any Critical or Important finding blocks completion. A correction remains append-only, stays within
the exact allowlist, repeats its RED/GREEN evidence, then reruns the entire completion gate and a new
independent review. A required out-of-allowlist change stops for owner review.

- [ ] **Verify final Git/H2 state and stop**

Required final state:

- branch is the owner-authorized branch;
- working tree is clean;
- remote count is zero;
- no tag, push, PR, merge, Release, model, ONNX, MLflow, Docker, GPU, network, H2, or Wave 2 action;
- H2 is `SEALED_NOT_LOADED`, loaded rows `0`;
- all seven planned commits exist in order, plus only explicitly required append-only review fixes;
- completion receipt and identities recompute from committed current-tree bytes.

After recording the final commit identities, remove the four task-scoped Git identity variables:

~~~powershell
Remove-Item Env:GIT_AUTHOR_NAME
Remove-Item Env:GIT_AUTHOR_EMAIL
Remove-Item Env:GIT_COMMITTER_NAME
Remove-Item Env:GIT_COMMITTER_EMAIL
~~~

Success terminal state:

`V02_W1_ADAPTER_FIREWALL_PASS / WAVE2_NOT_STARTED / H2_SEALED_NOT_LOADED`

Failure terminal state:

`V02_W1_CORRECTIVE_BLOCKED / WAVE2_FORBIDDEN / H2_SEALED_NOT_LOADED`

Even on PASS, stop and wait for a new owner Wave 2 authorization.
