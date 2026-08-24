# MDCP v0.2 Serving Identity Isolation Design Amendment

- Status: `APPROVED / APPROACH_A_LOCKED / CORRECTIVE_IMPLEMENTATION_PLANNING_AUTHORIZED`
- Date: 2026-08-25
- Applies to: `2026-08-24-mdcp-v02-temporal-retraining-design.md`
- Wave 1 entry commit: `f68ee1ddff91569311cc925c6b8bb0b180d016d0`
- Amendment base commit: `f28108cfc1474411d501e152b60a60c0673c999d`
- v0.1 serving identity: `d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`
- H2 status: `SEALED_NOT_LOADED`
- H2 loaded rows: `0`
- Owner-approved content commit: `da2fd65619edd0b69df415f5c126364791e2ee03`
- Owner-approved content SHA-256: `5fcbf1a8314f8e25cdbfd460f7ec202410a498deace6e853006250cb9509e33a`
- Scope of this approval commit: approval metadata and corrective implementation planning only

The terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. This amendment records the
owner-locked version-separated v1/v2 serving-identity design. Its approval authorizes a corrective
implementation plan only; it authorizes no source, schema, test, fixture, evidence, model, dataset,
deployment, or external mutation.

## 1. Purpose and normative relationship

Wave 1 Tasks 1.1 and 1.3 changed two files in the frozen v0.1 `SERVING_PATHS` inventory:

- `src/mdcp/contracts/workload.py`;
- `src/mdcp/predictor/app.py`.

The changes were functionally backward compatible, but v0.1 serving identity is a byte identity,
not an API-compatibility claim. Current-tree recomputation therefore changed the identity and made
the immutable v0.1 reviewer descriptors fail verification. Rewriting those descriptors would
rewrite historical evidence; verifying them from an earlier Git commit would make verification
depend on repository history.

This amendment resolves the conflict by permanently separating v1 and v2 modules, entry points,
and inventories. It supplements the approved v0.2 temporal-retraining specification and supersedes
only its implicit assumption that v1 and v2 may share mutable serving modules. All dataset roles,
features, model protocol, thresholds, H2 rules, and historical verdicts in the approved specification
remain unchanged.

The current Wave 1 implementation plan remains an historical execution record and MUST NOT be edited
in this amendment. A separately authorized plan revision is required before implementation resumes.

## 2. Locked decision and rejected alternatives

The owner-selected design is **Approach A: version-separated v1/v2 serving identity**. No further
architecture choice remains open in this amendment.

### 2.1 Rejected: verify v1 bytes from historical Git objects

A verifier MUST NOT obtain v1 serving bytes from an earlier commit, branch, tag, reflog, object
database, or `git show`. That approach fails for source archives, shallow clones, vendored source,
and reviewer bundles without `.git`. It also permits the current source tree to diverge from the
bytes a reviewer believes it is executing.

The two required Git blob IDs in Section 3 are migration-time assertions only. Final v1 verification
MUST hash the current source-tree files and MUST work when `.git` is absent.

### 2.2 Rejected: rewrite v0.1 descriptors or evidence

Existing v0.1 descriptors, reviewer fixtures, reports, natural-rejection evidence, and public
inventories MUST NOT be regenerated, patched, reinterpreted, or relabeled to accept new serving
bytes. Their frozen identity is an historical fact.

### 2.3 Rejected: mutable shared serving modules

The v2 contract MUST NOT be restored to `workload.py` or `app.py` through conditional imports,
runtime monkeypatching, mutable aliases, test-order side effects, or inventory exclusions. A v2
entry point MUST NOT masquerade as `mdcp.predictor.app:app`.

## 3. Permanent v0.1 boundary

### 3.1 Immutable identity

The v0.1 serving identity remains exactly:

`d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209`

The current `SERVING_PATHS`, `SERVING_ENVIRONMENT`, entry point
`mdcp.predictor.app:app`, inventory serialization, and digest algorithm retain their existing v0.1
meaning. Every current `SERVING_PATHS` file becomes a permanently frozen v1 boundary.

A future v2 change that requires modifying any current `SERVING_PATHS` file MUST stop for a new
owner design review. This includes `pyproject.toml`, `uv.lock`, v1 schemas, predictor runtime,
Dockerfile, and the two modules identified below. Backward-compatible source edits are still byte
changes and are not exempt.

### 3.2 Required current-tree restoration

A future authorized implementation MUST use append-only commits to restore these exact Wave 1 entry
blobs:

| Logical path | Required Git blob ID |
|---|---|
| `src/mdcp/contracts/workload.py` | `33f174528e691f1f5ff2590c2c641d75669d5196` |
| `src/mdcp/predictor/app.py` | `9fdee53bead221f0698d2e4a52407a4901c37649` |

The restoration MUST NOT amend, rebase, squash, delete, or replace existing Tasks 1.1–1.5 commits.
After restoration:

- `git hash-object` of each current file MUST equal the required blob ID during migration review;
- v0.1 schemas and tests MUST still match the restored source;
- current-tree `serving_inventory_from_root` MUST recompute the frozen v0.1 identity;
- the existing v0.1 descriptor and reviewer verifier MUST pass without modification;
- a source-archive copy with no `.git` directory MUST recompute the same identity from its files.

The Git blob checks prove exact restoration during development. They MUST NOT become a runtime or
reviewer dependency.

### 3.3 Frozen v1 semantics

`src/mdcp/contracts/workload.py` retains only the v1 workload contract present in its required blob.
`src/mdcp/predictor/app.py` retains the v1 predictor behavior and v1 entry point present in its
required blob. v1 does not acquire v2 envelope admission, temporal adaptation, or candidate routing.

## 4. Independent v2 module and entry-point boundary

The v2 workload and predictor MUST live under new versioned modules:

| Responsibility | Required module or artifact |
|---|---|
| Frozen v1 request | `src/mdcp/contracts/workload.py` |
| v2 request and union envelope | `src/mdcp/contracts/workload_v2.py` |
| Frozen v1 predictor | `src/mdcp/predictor/app.py` |
| v2 admission predictor | `src/mdcp/predictor/app_v2.py` |
| v1 entry point | `mdcp.predictor.app:app` |
| v2 entry point | `mdcp.predictor.app_v2:app` |
| v2 request schema | `schemas/v2/bike-request.schema.json` |

`BikeRequestV2` and `BikeRequestEnvelope` MUST be defined only in `workload_v2.py`.
`BikeRequestEnvelope` MUST reference the frozen `BikeRequest` type imported from `workload.py`; this
is an explicit frozen dependency, not a shared mutable identity. `BikeRequestV2.to_legacy()` returns
the frozen v1 `BikeRequest` without changing v1 source bytes.

The temporal adapter, routing code, v2 schemas, v2 API tests, golden-vector verifier, and contract
gate MUST import the v2 type from `workload_v2.py`. v1 tests and consumers continue importing only
`workload.py` and `app.py`.

`app_v2.py` owns version classification and the three-way admission truth table. It may reduce a
valid v2 envelope to the frozen 11-field `BikeRequest` for the stable comparator. It MUST reject a
legacy request on a candidate-only role and MUST reject any partial or invalid v2 declaration before
runtime selection. None of this behavior is injected into `app.py`.

## 5. Versioned v2 serving inventory

### 5.1 Inventory model

The v2 contract uses a new schema version and a new inventory implementation, isolated from v1.
The implementation MUST reside in `src/mdcp/contracts/serving_identity_v2.py`; it MUST NOT alter
the meaning or output of the existing v1 inventory functions.

The canonical v2 inventory body contains:

- `schema_version`, fixed to `mdcp.v2-serving-inventory.v1`;
- `entry_point`, fixed to `mdcp.predictor.app_v2:app`;
- the exact, ASCII-sorted tuple of logical inventory entries;
- for every entry, one safe repository-relative POSIX path and the SHA-256 of its current raw bytes.

`inventory_sha256` is the RFC 8785 digest of that body and is stored beside the body in the parent
receipt. It is not a field inside the bytes it hashes.

The receipt MUST contain both the complete logical path-to-SHA-256 inventory and its aggregate
digest. A map alone is insufficient because it cannot demonstrate duplicate rejection; validation
occurs on an ordered list before constructing any map.

### 5.2 Closed path set

`V2_SERVING_PATHS` is the exact set below for the Wave 1 contract identity:

1. `pyproject.toml`
2. `schemas/v2/bike-request.schema.json`
3. `schemas/v2/temporal-contract-receipt.schema.json`
4. `src/mdcp/common/canonical.py`
5. `src/mdcp/common/digests.py`
6. `src/mdcp/common/enums.py`
7. `src/mdcp/contracts/serving_identity_v2.py`
8. `src/mdcp/contracts/workload.py`
9. `src/mdcp/contracts/workload_v2.py`
10. `src/mdcp/predictor/app_v2.py`
11. `src/mdcp/predictor/runtime.py`
12. `src/mdcp/temporal/adapter.py`
13. `src/mdcp/temporal/constants.py`
14. `src/mdcp/temporal/contract_gate.py`
15. `src/mdcp/temporal/evidence.py`
16. `src/mdcp/temporal/firewall.py`
17. `src/mdcp/temporal/golden_vectors.py`
18. `src/mdcp/temporal/routing.py`
19. `src/mdcp/workload/dataset.py`
20. `src/mdcp/workload/features.py`
21. `src/mdcp/workload/splits.py`
22. `tests/fixtures/temporal/adapter-golden-vectors.json`
23. `uv.lock`

The list deliberately includes frozen v1 dependencies used by v2, such as `workload.py`,
`runtime.py`, `pyproject.toml`, and `uv.lock`. They remain frozen v1 bytes while also being explicit
inputs to the independent v2 digest. This does not merge the two inventory identities.

An inventory MUST fail closed for a missing path, extra declared entry, duplicate path, unknown
path, unsafe path, wrong ordering, unreadable file, or digest mismatch. “Extra” means an entry in the
declared v2 inventory that is not in this allowlist; unrelated repository documentation is not an
inventory entry. Adding or removing an allowlisted path requires a new inventory schema version and
owner review.

### 5.3 Reproducibility and identity cycles

Both v1 and v2 inventories MUST recompute from a current source archive with no `.git`, network,
registry, environment-specific absolute path, or Git command. Logical paths are relative to the
declared repository root and are the only paths serialized.

`contract_gate.py`, the receipt schema, and the golden manifest may be inventory inputs because the
receipt hashes their source bytes. The receipt MUST NOT contain its own serialized bytes, its own
content digest as an input to that digest, its commit SHA, or a future commit SHA. A receipt may have
an external digest calculated after serialization, but that external digest is not a field inside
the same receipt. This keeps the identity graph acyclic.

## 6. H2 firewall: static and behavioral proof

### 6.1 Static capability firewall

The formal v2 import roots are `workload_v2.py`, `app_v2.py`, and every module under
`src/mdcp/temporal` that participates in adaptation, routing, verification, or receipt assembly.
Static verification MUST resolve all of these forms:

- direct `from ... import ...` names;
- `import module` and `import package.module`;
- aliases on either import form;
- `from package import module` followed by qualified access;
- qualified attribute chains;
- dynamic imports through `importlib` or `__import__`.

Formal v2 code MUST NOT obtain or invoke these legacy capabilities:

- `load_uci_archive`;
- `DatasetPartitions`;
- `split_rows`;
- `open_h2`;
- a module alias that exposes any of those capabilities;
- another loader, iterator, split, or accessor capable of returning rows at or after
  `2012-07-01 00:00` before unseal.

Direct imports of the narrow `load_uci_development_archive`, `DevelopmentPartitions`, and
`split_development_rows` names are permitted. Importing their containing modules as qualified
objects is forbidden because it also exposes the legacy full-data API.

The static checker MUST build a normalized import/alias table before inspecting name and attribute
use. Text matching alone is insufficient. Syntax it cannot resolve fails closed; it is not silently
classified as safe.

### 6.2 Behavioral firewall

Static verification is necessary but not sufficient. The production development-only path MUST be
executed under denial hooks that wrap the actual legacy capabilities. The behavioral gate MUST prove:

- `load_uci_archive` call count is `0`;
- `split_rows` call count is `0`;
- `DatasetPartitions.open_h2` call count is `0`;
- the bounded loader is called with an exact `nrows=13_003` boundary;
- exactly `13,003` rows enter development partitioning;
- train rows equal `8,645`;
- H1 rows equal `4,358`;
- no returned value exposes `h2` or `open_h2`;
- H2 state remains `SEALED_NOT_LOADED` and loaded rows remain `0`.

The reviewer proof uses a deterministic generated archive containing exactly 13,003 valid
development rows followed by a distinct row-13,004 sentinel. It has
`evidence_class=synthetic_test`, `source_kind=deterministic_generated`, and `uci_rows=0`. The same
production bounded loader and splitter are used; test-only substitute loaders are forbidden. The
sentinel MUST NOT be returned, counted, hashed into development identity, or exposed in an error.

The local Wave 1 integration gate MUST also run the bounded production path on the approved archive
and bind its already-authorized 13,003-row development identity. The no-GPU reviewer fast path uses
the deterministic sentinel fixture and verifies the same production functions. Both modes MUST pass
`nrows=13_003` and MUST NOT inspect, count, preview, or parse a later row.

### 6.3 Behavioral receipt binding

The behavioral firewall returns a public-safe result containing only:

- fixed logical check IDs and verdict;
- deterministic fixture recipe digest;
- row counts and forbidden-capability call counts;
- H2 status and loaded-row count;
- static-firewall implementation digest;
- behavioral-firewall implementation digest;
- bounded-loader and development-split implementation digests;
- the identity material needed to compute an aggregate behavioral-result digest.

It contains no raw row, timestamp, archive path, exception, environment value, or sentinel value.
Task 1.6 MUST execute this verification and bind the result. Hashing firewall source or test files
without executing the behavioral gate cannot produce `PASS`. The behavioral body excludes its
`behavioral_result_sha256`; the parent receipt stores that SHA-256 beside the body, so it does not
hash itself.

## 7. Closed golden-vector inventory

The golden manifest has exactly 14 cases in this exact order:

1. `origin`
2. `year_end_category_maxima`
3. `leap_day`
4. `spring_before`
5. `spring_after`
6. `fall_edt`
7. `fall_est`
8. `malformed_timestamp`
9. `nonexistent_local_time`
10. `wrong_ambiguous_offset`
11. `cross_field_mismatch`
12. `before_lower_bound`
13. `last_accepted_hour`
14. `exact_upper_bound`

The manifest and verifier MUST reject a missing, extra, duplicate, renamed, or reordered case. Each
case is an RFC 8785-canonical object with an exact `id` and exact v2 payload. Accepted cases contain
the exact ordered 18-value float64 result plus little-endian float64 and one-time float32-cast
SHA-256 values. Rejected cases contain exactly one fixed expected reason and MUST NOT contain a
feature vector or float digest.

For each case, `case_sha256` binds the complete canonical case body excluding only that digest field.
The manifest records the ordered `(id, case_sha256)` inventory and an aggregate
`case_inventory_sha256`. The outer manifest raw-byte digest is separately bound by the v2 serving
inventory. The verifier MUST recompute the production adapter result, per-case digest, ordered
inventory digest, exact feature columns, temporal schema ID, float contract, and exact case count
before Task 1.6 can report `PASS`.

## 8. Task amendments required before implementation resumes

This document does not edit the implementation plan. A future owner-approved plan revision MUST
make these semantic changes:

### 8.1 Task 1.1 correction

- Move `BikeRequestV2` and `BikeRequestEnvelope` to `workload_v2.py`.
- Update only v2 consumers and v2 tests to import the new module.
- Keep the generated v2 schema bound to `BikeRequestV2` in the new module.
- Restore `workload.py` to required blob `33f174528e691f1f5ff2590c2c641d75669d5196` in a new
  append-only scoped commit.
- Prove v1 tests and the v1 schema are unchanged.

### 8.2 Task 1.3 correction

- Move v2 admission application behavior to `app_v2.py`.
- Keep classification in the versioned temporal routing layer.
- Update v2 API tests to instantiate the explicit v2 app.
- Restore `app.py` to required blob `9fdee53bead221f0698d2e4a52407a4901c37649` in a new
  append-only scoped commit.
- Prove the v1 entry point and current-tree v1 identity are restored.

### 8.3 Task 1.4 firewall hardening

- Replace direct-symbol-only scanning with normalized import, alias, qualified-access, and dynamic-
  import analysis.
- Add the production behavioral firewall and denial hooks described in Section 6.
- Keep all real H2 rows inaccessible.

### 8.4 Task 1.5 golden hardening

- Freeze the exact 14-case ordered inventory and per-case identities in Section 7.
- Add negative mutations for missing, extra, duplicate, reordered, payload-mutated, reason-mutated,
  float-mutated, and digest-mutated cases.

### 8.5 Task 1.6 replacement

- Introduce the independent v2 serving-inventory contract.
- Bind the complete v2 path inventory, static and behavioral firewall result, closed golden
  inventory, development identity, feature lineage, routing truth table, and public-evidence check.
- Include all source surfaces named in Sections 5–7, including `workload_v2.py`, `app_v2.py`, and
  `contract_gate.py` itself.
- Refuse `PASS` when a named check was merely hashed rather than executed.
- Keep receipt assembly acyclic and source-archive reproducible.

### 8.6 Wave 1 completion gate correction

Completion requires all of the following in one clean source state:

- required v1 blobs and frozen v1 serving identity recompute from the current tree;
- existing v0.1 descriptors, fixtures, reports, and evidence remain byte-identical;
- v1 API and reviewer verification pass without historical Git access;
- v2 types and entry point exist only in versioned modules;
- exact v2 inventory validation and source-archive recomputation pass;
- static and behavioral H2 firewall checks pass;
- the exact golden inventory passes;
- the rebuilt Task 1.6 receipt passes publication-boundary validation;
- H2 remains `SEALED_NOT_LOADED`, loaded rows `0`;
- Critical findings equal `0` and Important findings equal `0`.

## 9. Append-only migration order

After this amendment and a revised implementation plan receive separate owner approval, migration
MUST occur in this order:

1. Reconfirm branch, expected parent, protected evidence, v1 identity, H2 state, and the three
   untracked-draft identities in Section 11.
2. Add RED tests for the v2 request-module boundary, then create `workload_v2.py`, redirect v2-only
   imports, and restore `workload.py` in a new append-only correction commit.
3. Add RED tests for distinct entry points, then create `app_v2.py`, redirect v2-only API tests, and
   restore `app.py` in a new append-only correction commit.
4. Prove both v1 required blobs and frozen v1 serving identity before touching Task 1.6 drafts.
5. Add and pass RED/GREEN hardening for the static and behavioral H2 firewall.
6. Add and pass RED/GREEN hardening for the closed golden inventory.
7. Add the v2 inventory contract and its negative mutation tests.
8. Revise the three preserved Task 1.6 drafts in place under their approved task, then commit the
   complete Task 1.6 scope only after its targeted and Wave 1 completion gates pass.
9. Run the complete CPU regression, security/publication scans, source-archive recomputation, and
   independent review. Stop at Wave 1; Wave 2 remains separately gated.

No migration step may amend, rebase, squash, reset, or delete an existing commit. A correction after
a committed error is another forward commit with its own evidence.

## 10. RED/GREEN verification strategy

The revised plan MUST require real observed failures before implementation:

| Boundary | Required RED | Required GREEN |
|---|---|---|
| v1 blob restoration | current files have non-required blob IDs and v1 inventory mismatch | both required blobs and `d81af556...` recompute |
| v2 request module | v2 imports fail when removed from `workload.py` | v2 imports only `workload_v2.py`; v1 bytes unchanged |
| v2 predictor module | explicit v2 entry point is absent | v1 and v2 entry points pass separate truth tables |
| inventory closure | missing/extra/duplicate/unknown/reordered entries are accepted | every mutation fails and exact inventory recomputes |
| source archive | verifier depends on `.git` or Git history | v1 and v2 identities recompute with `.git` absent |
| static H2 firewall | alias/qualified/full-loader adversarial modules evade detection | every forbidden import/access form fails closed |
| behavioral H2 firewall | a forbidden-capability spy is called or row 13,004 enters the result | all forbidden counts are zero and counts are 13,003/8,645/4,358 |
| golden closure | missing/extra/duplicate/reordered or mutated cases pass | exact 14-case inventory and every digest recompute |
| receipt completeness | omitted source or hash-only firewall can produce `PASS` | all named checks execute and complete inventory is bound |
| identity cycle | receipt requires its own digest or future commit SHA | repeated assembly is identical and acyclic |

Tests use deterministic generated fixtures unless the approved 13,003-row development prefix is
explicitly required. No test in this correction may load a true H2 row, fit a model, export ONNX,
start Docker, use GPU, or access a network.

## 11. Preserved untracked Task 1.6 drafts

At this amendment's base, these three paths are intentionally untracked and MUST remain unmodified,
uncommitted, and undeleted by the docs-only amendment:

| Path | Bytes | SHA-256 at amendment preflight |
|---|---:|---|
| `schemas/v2/temporal-contract-receipt.schema.json` | 4,356 | `5901faeebf1f471a33ab32e67cf9dca0094699d893bbe72f576abe7a3cb358d7` |
| `src/mdcp/temporal/contract_gate.py` | 10,526 | `fb356c0d9bb41adfa7bc092a46833e2bc6fc69ce81179481af3c6c71240a6293` |
| `tests/integration/temporal/test_contract_gate.py` | 3,264 | `1170b869fb85c2e8ea5da580900734bd45eb08f9b43019f40c95010197b9a485` |

These bytes are a blocked implementation draft, not normative source and not PASS evidence. This
amendment preserves their identity only to prove that the docs-only turn did not alter them.

A future approved implementation plan MUST revise these same paths in place after the v1/v2 module
split, firewall hardening, and golden closure have observed RED tests. It MUST NOT first commit the
current draft as accepted evidence. The final Task 1.6 commit must contain the reviewed replacement
and must not claim continuity with the provisional receipt digest.

## 12. Failure, rollback, and stop conditions

Implementation MUST stop without Wave 2 if any of these occurs:

- either restored v1 file differs from its required blob;
- current-tree v1 identity differs from `d81af556...`;
- a v0.1 descriptor, fixture, report, evidence file, or `SERVING_PATHS` definition would need change;
- v1 verification requires Git history or `.git`;
- a v2 inventory path set is incomplete, ambiguous, cyclic, or environment-dependent;
- a formal v2 path can reach a legacy full-data or H2 capability;
- any forbidden behavioral-firewall call count is nonzero;
- parsed development rows, train rows, or H1 rows differ from 13,003/8,645/4,358;
- H2 state changes or loaded rows exceeds `0`;
- golden cases are missing, extra, duplicated, reordered, or fail recomputation;
- Task 1.6 can report `PASS` without executing every named check;
- a fix requires dependency-lock, original-spec, original-plan, or evidence mutation outside a newly
  approved scope;
- Critical or Important independent-review findings remain.

Rollback is forward-only. No reset, rebase, amend, history rewrite, evidence deletion, or draft
deletion is permitted. A failed migration retains its commits and evidence, restores a valid state
only through a separately reviewed append-only correction, and keeps H2 sealed.

## 13. Amendment approval and terminal state

This written amendment passed final owner written-spec review after it was checked for:

- unresolved placeholders or open architecture choices: none;
- identity cycles: none; source inputs are hashed before receipt serialization and the receipt does
  not contain its own digest or future commit identity;
- v0.1 evidence mutation: forbidden throughout;
- source-archive reproducibility: both identities use current relative files and require no Git;
- H2 bypass: direct, aliased, qualified, dynamic, and behavioral capability paths are covered;
- golden-case completeness: exact 14 IDs, count, ordering, content, and digests are closed;
- scope drift: approval authorizes only docs-only corrective implementation planning.

The terminal state for this approval commit is:

`DESIGN_AMENDMENT_APPROVED / V01_IDENTITY_PRESERVED / H2_SEALED / CORRECTIVE_IMPLEMENTATION_PLANNING_AUTHORIZED`

Corrective implementation planning is authorized. Implementation, model execution, H2 access,
Docker/GPU actions, Wave 2, and external publication remain forbidden until separately authorized.
