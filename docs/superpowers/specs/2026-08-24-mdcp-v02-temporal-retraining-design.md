# Model Delivery Control Plane v0.2 Temporal Retraining Design Specification

- Status: `APPROVED / APPROACH_A / IMPLEMENTATION_PLANNING_AUTHORIZED`
- Date: 2026-08-24
- v0.1 base SHA: `46c2baa6b96323624106acb7cc0772ae2bc1608a`
- Historical verdict: `NO_ELIGIBLE_CANDIDATE`
- H1 role: `OBSERVED_DEVELOPMENT_ONLY`
- H2 status: `SEALED_NOT_LOADED`
- H2 loaded rows at this specification's creation: `0`
- Approach: A — causal time-aware temporal retraining
- Scope of this commit: additive design specification only

Preserved natural-rejection evidence is identified logically by:

- evidence class: `natural_rejection_evidence`;
- payload file count: `22,236`;
- payload total bytes: `585,295,509`;
- payload inventory SHA-256:
  `fc39f69fe0fcf7ac49f60348ce3198ba04199026269eb45ec26b49865775a30f`;
- preservation-receipt SHA-256:
  `bca375202663af8245f8f27496ea44e7c5cf9f7ea0aa1e76176d23deef01cc9a`;
- `FINAL-SHA256SUMS` SHA-256:
  `ea26df010ba2e73aed88ed462b3843a0084356010465a055e04a5c87c70a5fad`;
- source/destination byte equivalence: `PASS`.

The evidence payload remains private and external to Git. This specification records only its
logical identity and public-safe digests; it does not incorporate, relocate, enumerate, or publish
the 22,236 payload files. Private absolute paths are environment metadata and are not public claims.

## 1. Purpose and normative relationship

This document defines a preregistered v0.2 protocol for asking one narrow question:

> Can causal, prediction-time-available calendar information and temporal retraining produce one
> candidate that passes an unchanged, single-use natural H2 confirmatory gate?

This is an additive protocol, not a correction to historical evidence. The approved v0.1 design in
`2026-08-23-model-delivery-control-plane-design.md` remains normative for the control plane unless
this document explicitly defines a v0.2-only workload extension. Existing v0.1 plans are historical
implementation records and are not silently amended by this specification.

The terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. This design authorizes no
implementation, implementation plan, model run, H2 access, container run, external mutation, or
publication. The next gate is owner review of the written specification.

## 2. Historical ledger: facts that cannot be rewritten

Four objects MUST remain distinct in every report, manifest, dashboard, and portfolio claim:

1. the v0.1 historical protocol;
2. v0.1 Candidate-v1 and Candidate-v2 natural-rejection evidence;
3. this v0.2 temporal retraining protocol; and
4. a future v0.2 confirmatory result, if the protocol ever reaches H2.

### 2.1 v0.1 protocol and Candidate-v1

v0.1 trained on 2011, treated 2012 H1 as its natural offline eligibility set, and reserved 2012 H2.
Candidate-v1's natural H1 result is permanently `FAIL`:

- overall point ratio: `0.9941709085547193`;
- overall one-sided UCB95: `1.0132761747618493`;
- off-peak subgroup UCB95: `1.0514487756867108`;
- reason codes: `OVERALL_RATIO`, `OVERALL_UCB95`, and
  `SUBGROUP_UCB95:demand_off_peak`.

That result MUST NOT be relabeled as a pilot, smoke result, or PASS. Wave 1 MUST NOT be described as
having naturally succeeded.

### 2.2 Candidate-v2 feasibility audit

The CPU-only Candidate-v2 audit ended `NO_ELIGIBLE_CANDIDATE`. Its single preregistered H1 candidate
failed with:

- overall point ratio: `1.024486`;
- overall one-sided UCB95: `1.049456`.

H1 aggregate information had already been observed before that audit, so Candidate-v2 H1 was not
globally blind. The preserved rejection evidence identified in this document's header is immutable
historical evidence. It MUST NOT be modified, deleted, replaced by synthetic evidence, or used to
claim a successful natural candidate.

### 2.3 Current truth

At this specification's base SHA:

- Wave 0 remains `PASS 8/8`;
- v0.1 natural H1 remains `FAIL`;
- Wave 2 Tasks 2.1–2.6 provide useful local engineering artifacts, but no formal candidate is
  eligible and Task 2.7 was not executed;
- H1 has been observed and cannot be a blind or confirmatory gate again;
- H2 remains `SEALED_NOT_LOADED`, with zero rows loaded;
- no eligible natural promotion candidate exists.

No future v0.2 outcome may revise any item in this ledger.

## 3. Dataset roles and trust boundary

The UCI Bike Sharing archive identity remains:

- dataset ID: `275`;
- DOI: `10.24432/C5W894`;
- license: CC BY 4.0;
- archive SHA-256:
  `b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401`;
- target: `cnt`.

v0.2 assigns the chronology these roles:

| Interval | Half-open boundary | v0.2 role | Permitted use |
|---|---|---|---|
| 2011 | `[2011-01-01 00:00, 2012-01-01 00:00)` | development | training, rolling validation, preprocessing fit, selection |
| 2012 H1 | `[2012-01-01 00:00, 2012-07-01 00:00)` | observed development extension | diagnosis, rolling validation, training, calibration, feature-contract evaluation |
| 2012 H2 | `[2012-07-01 00:00, 2013-01-01 00:00)` | sealed single-use confirmatory set | one owner-authorized confirmatory evaluation after every precondition passes |

All boundaries use the fixed local civil-time semantics in Section 4. H1 MUST be called
`observed development extension`, never `holdout`, `blind gate`, or `confirmatory set`.

### 3.1 H2 pre-unseal prohibition

Before the v0.2 candidate is frozen and separately authorized for unseal, no process may:

- load H2 features or labels;
- perform stable or candidate inference on H2;
- preview H2 rows or fields;
- explore H2 schema or subgroup distributions;
- compute H2 aggregates, calibration constants, encoders, scalers, or tuning statistics;
- use H2 to add, remove, rank, or retry a candidate.

Only already-recorded dataset identity, split boundaries, seal metadata, and an already-known row
count MAY be referenced. The formal protocol SHOULD not recompute even the row count before unseal;
it MUST NOT enumerate or parse H2 merely to restate existing metadata. Any attempted access before
authorization is a release-blocking `H2_PREMATURE_ACCESS` event and leaves candidate eligibility
`UNKNOWN`.

## 4. Causal temporal feature contract

### 4.1 Prediction-time source contract

The v0.2 outer request is a versioned evaluation envelope containing:

- `schema_version`, fixed to `mdcp.bike-request.v2`;
- `request_id`;
- `event_timestamp`;
- the existing model fields `season,mnth,hr,holiday,weekday,workingday,weathersit,temp,atemp,hum,`
  `windspeed`.

`event_timestamp` MUST be a strict RFC 3339 timestamp with an explicit numeric UTC offset. It is
request metadata consumed by a trusted temporal adapter; its raw string is never an ONNX/model
input. For historical training, the equivalent source is strict `dteday` plus integer `hr`.

The operational calendar is pinned to the IANA zone `America/New_York`, matching the Washington,
D.C. workload. Serving converts the supplied instant to that zone using the dependency-locked
timezone database. Training interprets `dteday + hr` as the corresponding local civil date/hour.
Feature derivation uses local civil coordinates, not elapsed UTC seconds, so daylight-saving
transitions do not create a one-hour trend discontinuity.

The fixed origin is local civil `2011-01-01 00:00:00` in `America/New_York`. The one and only
accepted local-time domain is the half-open research interval
`[2011-01-01 00:00:00, 2013-01-01 00:00:00)`. A normalized local time before the lower bound, or at
or after `2013-01-01 00:00:00`, MUST fail with `EVENT_TIMESTAMP_OUT_OF_RANGE`. Minute, second, and
fractional-second components MUST all be zero after timezone normalization. The normalized local
month, hour, and weekday MUST equal `mnth`, `hr`, and `weekday`; weekday uses Sunday=`0` through
Saturday=`6`. `season`, `holiday`, and `workingday` remain supplied, validated request facts because
they require the dataset's declared calendar semantics rather than a target-derived lookup.

This timestamp range is a dataset-bounded research and portfolio contract. It provides no serving,
extrapolation, or forecasting guarantee outside the 2011–2012 UCI chronology and MUST NOT be
presented as a general long-term forecasting API.

Missing, malformed, out-of-range, nonexistent local time, or cross-field mismatch MUST fail closed
before inference with a fixed sanitized reason code:

- `MISSING_EVENT_TIMESTAMP`;
- `INVALID_EVENT_TIMESTAMP`;
- `EVENT_TIMESTAMP_OUT_OF_RANGE`;
- `TEMPORAL_FIELD_MISMATCH`.

No imputation, host-time fallback, current-time fallback, locale inference, or timezone guessing is
permitted. In ordinary serving, an invalid declared-v2 envelope is rejected and counted separately.
In development or H2 evaluation, the authoritative source-row inventory is fixed before adaptation;
an adapter failure remains accounted against that inventory and makes the whole trial or H2 gate
`UNKNOWN`. It MUST NOT be deleted to create a smaller quality denominator.

### 4.2 Unique model feature schema

The temporal adapter emits exactly 18 numeric model fields in this order:

| Position | Field | Definition at prediction time | Source/constant |
|---:|---|---|---|
| 1 | `season` | validated input in `{1,2,3,4}` | request |
| 2 | `mnth` | validated local month in `[1,12]` | request + timestamp cross-check |
| 3 | `hr` | validated local hour in `[0,23]` | request + timestamp cross-check |
| 4 | `holiday` | validated input in `{0,1}` | request |
| 5 | `weekday` | Sunday=`0` … Saturday=`6` | request + timestamp cross-check |
| 6 | `workingday` | validated input in `{0,1}` | request |
| 7 | `weathersit` | validated input in `{1,2,3,4}` | request |
| 8 | `temp` | finite normalized input in `[0,1]` | request |
| 9 | `atemp` | finite normalized input in `[0,1]` | request |
| 10 | `hum` | finite normalized input in `[0,1]` | request |
| 11 | `windspeed` | finite normalized input in `[0,1]` | request |
| 12 | `elapsed_days` | `(local_date - 2011-01-01).days + hr / 24` | fixed origin |
| 13 | `hour_sin` | `sin(2*pi*hr/24)` | fixed `pi`, period 24 |
| 14 | `hour_cos` | `cos(2*pi*hr/24)` | fixed `pi`, period 24 |
| 15 | `weekday_sin` | `sin(2*pi*weekday/7)` | fixed `pi`, period 7 |
| 16 | `weekday_cos` | `cos(2*pi*weekday/7)` | fixed `pi`, period 7 |
| 17 | `annual_sin` | `sin(2*pi*elapsed_days/365.2425)` | fixed Gregorian mean year |
| 18 | `annual_cos` | `cos(2*pi*elapsed_days/365.2425)` | fixed Gregorian mean year |

All arithmetic is performed in float64 by the adapter and cast once to float32 at the ONNX
boundary. The transform schema, constants, field order, timezone identifier, timezone-data version,
and float-cast rule form canonical identity `mdcp.temporal-features.v0.2` and MUST be SHA-256 bound
into every development receipt and final manifest.

The seven categorical inputs have fixed, specification-defined domains. A family that one-hot
encodes them MUST use the full fixed category sets rather than categories discovered from H1 or H2.
Any scaler or learned preprocessing state MUST fit only the current fold's training window; the
final scaler MUST fit only 2011 plus H1.

### 4.3 Leakage analysis

Every permitted field is available when a request is made. `elapsed_days` is a monotonic function of
the request timestamp and fixed origin; the cyclic fields use only fixed mathematical constants.
None uses a label, prediction, future observation, demand aggregate, or H2-derived constant.

The following remain forbidden as model inputs or preprocessing sources:

- `cnt`, `casual`, and `registered`;
- `instant`;
- future labels or future demand statistics;
- target-derived aggregates, encodings, calibrations, or lookup tables;
- any scaler, encoder, category inventory, calibration, or constant computed from H2;
- raw `dteday` or raw `event_timestamp` passed to the model;
- `yr` as a categorical dataset-answer shortcut;
- a row-identity/date lookup capable of recovering a target;
- H2-specific feature logic or tuning.

The target `cnt` is available only to training and evaluation code after the feature tensor is
materialized. Evaluator-only `calendar_day` and subgroup membership are not model inputs.

### 4.4 ONNX and serving representation

The v0.2 candidate ONNX contract has 18 named `float32` inputs, each shaped `[N,1]`, in the exact
order in Section 4.2, and one finite non-negative `float32` prediction output shaped `[N,1]`.
`event_timestamp` is not an ONNX input. The model artifact MUST include or be bound to a
non-negative clipping postprocessor so native and ONNX behavior are identical.

The public serving operation remains single-row `POST /v1/predict` only within the accepted research
interval in Section 4.1. Routing classifies envelopes before model selection:

- an exact legacy v1 request with no `schema_version` and no `event_timestamp` may use only the
  stable-v1 adapter and stable-only route;
- only a complete `mdcp.bike-request.v2` envelope that passes every temporal/schema check is
  candidate-eligible;
- a declared or partial v2 envelope that is missing or fails any required field is rejected and is
  neither a legacy admission nor a candidate admission.

A valid v0.2 request adapter produces the candidate's 18 inputs. For the stable comparator, the same
v2 envelope is reduced to the original 11 v0.1 fields and evaluated by the frozen v0.1 feature
contract. The adapter split is descriptor-selected and hash-bound; it MUST NOT be selected by a
mutable alias. Candidate serving outside the accepted interval is unsupported and fails closed; it
is not a long-range extrapolation surface.

Legacy stable-only admissions, valid v2 candidate-eligible admissions, and rejected/invalid v2
envelopes MUST use separate counters, evidence windows, and reports. Legacy traffic MUST NOT enter a
v2 candidate quality denominator, and candidate-eligible traffic MUST NOT be diluted by legacy
stable-only traffic.

Training and serving MUST call the same versioned temporal-adapter function. Golden parity vectors
MUST cover the origin, year boundary, leap day, daylight-saving spring/fall boundaries, all category
edges, and invalid/mismatched timestamps. Boundary vectors MUST prove the lower bound is accepted,
the instant immediately before the upper bound is accepted, and both an instant before the lower
bound and exact `2013-01-01 00:00:00` local time are rejected as
`EVENT_TIMESTAMP_OUT_OF_RANGE`. The native feature-vector digest, candidate native prediction
digest, and ONNX Runtime prediction digest MUST recompute under the locked dependency graph. No H2
row may be used for these vectors.

### 4.5 Denominator-preserving completeness contract

Every development fold and the single H2 run begins with an immutable inventory of authoritative
source-row identities determined solely by the frozen chronology. Three completeness layers are
accounted independently:

1. **Adapter completeness is 100%.** Every authoritative source row MUST produce exactly one valid
   `mdcp.bike-request.v2` evaluation envelope. Adapter success plus adapter failure must equal the
   fixed source-row count. Any rejection, timestamp mismatch, missing envelope, duplicate envelope,
   schema failure, or accounting gap makes the entire trial or H2 gate `UNKNOWN`; the row cannot be
   dropped and evaluation cannot continue to a quality PASS.
2. **Prediction completeness is 100%.** Every adapter-valid evaluation envelope MUST produce
   exactly one stable and one candidate prediction, each finite and non-negative. Stable/candidate
   success, failure, missing, and duplicate counts are retained against the adapter-valid inventory.
   Any missing, duplicate, invalid, or unaccounted prediction makes the entire trial or H2 gate
   `UNKNOWN`; the pair cannot be removed to shrink the denominator.
3. **Label completeness is separate.** Development folds require the archive's label for every
   adapter- and prediction-complete row. H2 alone retains the delayed-label policy: overall label
   completeness at least 99.5% and every fixed subgroup at least 99.0%. Only a genuinely absent label
   may use that policy. Adapter or prediction failure MUST NOT be labeled, counted, or reason-coded
   as a missing label.

Quality ratios and the paired bootstrap run only after adapter and prediction completeness both
equal 100%, using the remaining paired labeled rows. Label-completeness denominators are the fixed
adapter-valid, prediction-complete source rows overall and within each predeclared subgroup. Receipts
MUST expose source, adapter, stable-prediction, candidate-prediction, and label counts plus fixed
failure reason codes; aggregate equality alone does not hide duplicate or missing identities.

## 5. Rolling-origin development protocol

The formal development run uses exactly four expanding-window folds:

| Fold | Training interval | Validation interval | Validation label |
|---|---|---|---|
| F1 | `[2011-01-01 00:00, 2011-07-01 00:00)` | `[2011-07-01 00:00, 2011-10-01 00:00)` | 2011 Q3 |
| F2 | `[2011-01-01 00:00, 2011-10-01 00:00)` | `[2011-10-01 00:00, 2012-01-01 00:00)` | 2011 Q4 |
| F3 | `[2011-01-01 00:00, 2012-01-01 00:00)` | `[2012-01-01 00:00, 2012-04-01 00:00)` | 2012 Q1 |
| F4 | `[2011-01-01 00:00, 2012-04-01 00:00)` | `[2012-04-01 00:00, 2012-07-01 00:00)` | 2012 Q2 |

Intervals are half-open. A fold's maximum training timestamp MUST be earlier than its minimum
validation timestamp. Validation intervals are mutually disjoint; earlier validation periods may
enter later expanding training windows only after their chronological time has passed. No random
row split, shuffled cross-validation, or future-to-past fit is permitted.

Every source calendar day is indivisible: all rows from one date belong to one side of a boundary
and to one bootstrap cluster. Rows are sorted by `(local_date, hr, original stable source order)`;
duplicate timestamp/request identities fail closed. The formal run MUST bind, per fold:

- inclusive minimum and maximum timestamps and half-open declared boundaries;
- training and validation row counts;
- canonical training-row and validation-row SHA-256 identities;
- label and feature-column lineage digests;
- fitted preprocessing-state digest;
- stable-control config/prediction digest;
- candidate config/prediction digest;
- policy/statistical-code digest.

Scalers, encoders, imputers, calibrators, and model parameters fit only that fold's training rows.
Validation labels never enter fitting. H2 is not imported, enumerated, or inferred.

### 5.1 Baseline identities

Each development fold uses a **fold-specific development baseline**: the frozen stable-v1 Random
Forest configuration (`32` trees, depth `8`, minimum leaf `4`, seed `2026`, `n_jobs=1`) retrained on
that fold's full expanding training interval and restricted to the original 11 features. Its purpose
is a fair, same-information development comparison; it is not a new production stable artifact.

The **final frozen production stable comparator** remains the v0.1 stable artifact:

- stable config SHA-256:
  `ece4b3fe40754b247e9dcd2dac3bcbd6081a669d7dafabee127c2e92a7042078`;
- feature-manifest SHA-256:
  `7d0ca4846110b893d6154a84c6ced73401f687ca4d4f6fc791b893e0398c41dd`;
- ONNX SHA-256:
  `49d8375e37c1652a417d646b0af53abf4a9252a6e06019addce619a6838e2866`;
- artifact-descriptor digest:
  `ff4b50e4f8ca1cea066c0d114c9fa1d019e407d5bd0ede68f0c460a2efaed2a8`.

The **final v0.2 candidate artifact** does not exist until ranking names one provisional winner, that
provisional winner passes exact replay and becomes the sole final development winner, it is refit on
2011 plus H1, and it completes Section 8. None of these three identities may be conflated.

## 6. Finite candidate protocol

### 6.1 Formal search source, freeze, and receipt identity

Before the first formal development fit, search identity MUST be frozen in two acyclic stages:

1. **`SEARCH_SOURCE_COMMIT`** is a clean commit containing the approved specification, complete
   implementation, dependency lock, exact trial and fold tables, ranking rule, feature/training/
   selection/evaluation code, statistical code, and every other byte capable of affecting the
   development run. It does not contain the formal search receipt.
2. **`SEARCH_FREEZE_COMMIT`** has `SEARCH_SOURCE_COMMIT` as its exact parent. Its diff may only add
   the RFC-8785 canonical frozen search receipt and explicitly approved immutable evidence-index
   files. The receipt binds `SEARCH_SOURCE_COMMIT`, this spec digest, dependency-lock digest,
   dataset/development identities, feature schema, exact trial/fold/ranking identities, seeds,
   compute ceiling, quality-policy identity, statistical-code identity, and an assertion that H2 is
   sealed. It MUST NOT contain its own `SEARCH_FREEZE_COMMIT` SHA.

The formal development run MUST start from a clean checkout at exactly `SEARCH_FREEZE_COMMIT` and
fail closed unless preflight proves all of the following:

- its single parent equals the receipt-bound `SEARCH_SOURCE_COMMIT`;
- the parent-to-freeze diff contains only the allowlisted receipt/evidence-index additions;
- no prediction, temporal-adapter, feature, preprocessing, training, selection, ranking,
  evaluation, policy, or statistical-code byte changed between the two commits;
- the receipt, spec, dependency lock, trial/fold/ranking tables, policies, and source-tree identities
  recompute; and
- H2 remains `SEALED_NOT_LOADED` with zero loaded rows.

Placeholder SHAs, post-run SHA backfill, commit amendment, receipt regeneration, or any self-hash
cycle are forbidden. A byte change to a bound input requires a new protocol version and new
two-stage search freeze; it cannot continue the same formal run.

The formal run has exactly 20 trials: one ineligible control and 19 promotion-eligible candidates.
No family, hyperparameter, seed, feature, fold, or trial may be added after any formal development
score is observed.

### 6.2 Exact trial table

All stochastic estimators use `random_state=2026`; all estimator, BLAS, OpenMP, and joblib thread
counts are `1`; bootstrap uses `PCG64(2026)`. Non-stochastic Ridge trials have no model RNG and are
still bound to the global execution seed `2026` for the surrounding pipeline.

| Family / IDs | Count | Training rows | Model inputs | Exact configurations | Final-eligible |
|---|---:|---|---|---|---|
| `CTRL-01` | 1 | full expanding fold | original fields 1–11 | Random Forest: trees=`32`, depth=`8`, leaf=`4`, `max_features=1.0`, bootstrap=`true` | no |
| `REC-{180,270,365}-L{4,12}` | 6 | trailing `180`, `270`, or `365` complete calendar days ending at validation start | fields 1–11 and bounded cyclic fields 13–18; field 12 excluded | Random Forest: trees=`64`, depth=`8`, leaf in `{4,12}`, `max_features=1.0`, bootstrap=`true` | yes |
| `STAT-A{0.1,1,10,100,1000}` | 5 | full expanding fold | all 18 fields | Ridge: alpha in `{0.1,1,10,100,1000}`, solver=`lsqr`, fit intercept=`true`, tolerance=`1e-8`, max iterations=`10000`; fixed one-hot categoricals and training-only standardization | yes |
| `NL-E{64,128}-R{0.03,0.07}-D{2,3}` | 8 | full expanding fold | fields 1–11 and bounded cyclic fields 13–18; field 12 excluded | Gradient Boosting: estimators in `{64,128}`, learning rate in `{0.03,0.07}`, tree depth in `{2,3}`, minimum leaf=`8`, loss=`squared_error`, subsample=`1.0`, max features=`None` | yes |

For a recency trial, the training start is exactly
`max(2011-01-01, validation_start - window_days)` and the end is `validation_start`, both local
midnight boundaries. It never draws an equal row count across the boundary or pads from the future.

Family preprocessing is unique and fixed:

- `CTRL` passes original fields 1–11 through exactly as stable-v1 does;
- `REC` and `NL` pass their declared raw numeric inputs without learned scaling or category
  discovery;
- `STAT` one-hot encodes fields 1–7 with the full fixed category sets
  `{1..4}`, `{1..12}`, `{0..23}`, `{0,1}`, `{0..6}`, `{0,1}`, and `{1..4}` respectively, then
  standardizes fields 8–18 with training-window mean and population standard deviation (`ddof=0`);
  a zero-variance continuous column is invalid rather than silently assigned another transform;
- every family fits the untransformed `cnt` target and applies the same final `max(0, prediction)`
  contract in native and ONNX execution.

Ridge is the time-aware statistical/extrapolating family: its standardized `elapsed_days`
coefficient can extend beyond the training maximum only within the accepted research interval while
bounded calendar terms model periodicity.
The nonlinear family deliberately excludes unbounded `elapsed_days`. It sees only bounded raw
calendar domains and sine/cosine cycles, so H2 values remain within previously defined feature
ranges; a tree is never asked to extrapolate an unseen monotonic time coordinate. The recency family
tests conservative adaptation without claiming explicit long-range extrapolation. `CTRL-01` detects
pipeline or evaluator drift and can never become the H2 candidate.

All three eligible families are designed for deterministic CPU inference, bounded size, reliable
scikit-learn-to-ONNX conversion, and the single-row serving contract. Converter support MUST be
proved on synthetic/development inputs before a trial can be final-eligible. An operator allowlist
for v0.2 MUST be hand-reviewed and frozen before the formal run; it MUST NOT auto-expand by reading
candidate graphs.

### 6.3 Early invalidation and compute ceiling

A trial is invalidated immediately, with a fixed reason code, only for a contract failure:

- forbidden feature lineage or H2 access;
- wrong fold or recency boundary;
- input/schema mismatch;
- fit/conversion failure under the locked dependency graph;
- non-finite or negative post-contract prediction;
- adapter rejection, missing/duplicate evaluation envelope, or incomplete source-row accounting;
- duplicate/missing/invalid stable or candidate prediction, or incomplete paired accounting;
- insufficient subgroup rows or invalid stable denominator;
- nondeterministic prediction/receipt identity.

Poor quality alone is not an early-stop condition; every contract-valid trial MUST complete all four
folds so the full trial summary cannot hide later-fold regressions. An invalid trial is not replaced.

The formal CPU ceiling is:

- `20 trials * 4 folds = 80` selection fits, including the reused control fit per fold;
- exactly four additional fits for the provisional winner's deterministic fold replay;
- at most one final refit after the development gate passes;
- maximum total: `85` fits;
- one trial at a time, one process, one estimator thread, no GPU;
- maximum resident-memory budget: `4 GiB` for the development process;
- maximum formal-run wall clock: `6 hours` on the recorded reviewer/developer CPU profile.

Budget exhaustion makes the run `UNKNOWN/COMPUTE_BUDGET_EXCEEDED`; it does not authorize parallel
search, fewer folds, a larger search, relaxed thresholds, or an H2 look.

### 6.4 Development-only ranking

Selection has one mandatory order and MUST NOT be short-circuited:

1. all 20 trials complete the formal run subject only to Section 6.3 contract invalidation;
2. the 19 final-eligible trials are evaluated against every **qualification** condition in Section
   7.3 except provisional-winner replay;
3. only qualified trials enter the following lexicographic ranking;
4. rank one becomes the sole **provisional winner**;
5. only that provisional winner receives the four-fold exact replay;
6. replay PASS promotes it to the sole **final development winner**.

The ranking key remains the lexicographic minimum of:

1. pooled out-of-fold overall UCB95;
2. worst of the four fold overall point ratios;
3. worst pooled fixed-subgroup UCB95;
4. static complexity class: `STAT` before `REC` before `NL`;
5. exact ASCII trial ID.

The rank uses only 2011 plus observed H1 development rows. `CTRL-01` is excluded. If no eligible trial
qualifies, the result is `NO_ELIGIBLE_CANDIDATE`; no provisional or final winner exists, no final
candidate is trained, and H2 remains sealed.

If the provisional winner's replay is `FAIL` or `UNKNOWN`, the entire selection result is
`UNKNOWN/NO_ELIGIBLE_CANDIDATE`. The provisional winner is not final-eligible, and the protocol MUST
NOT select rank two, rerank, change a tie-break, tune a parameter, rerun the search, or construct a
fallback candidate. H2 remains sealed.

## 7. Development gate

### 7.1 Paired metrics and fixed subgroups

Each candidate is compared to the fold-specific baseline on identical validation rows. Stable and
candidate errors and ratios retain the v0.1 formulas:

```text
stable_error_i    = abs(stable_prediction_i - label_i)
candidate_error_i = abs(candidate_prediction_i - label_i)
R_g               = sum(candidate_error_i in g) / sum(stable_error_i in g)
```

The fold's authoritative validation-row set is fixed before the temporal adapter runs. Adapter
completeness and stable/candidate prediction completeness MUST each equal 100% under Section 4.5;
any failure makes the entire trial `UNKNOWN` before ratios or bootstrap are evaluated. Development
labels MUST also be present for 100% of those rows. No failed or missing adapter/prediction identity
may be removed from the declared fold count or disguised as label loss.

The fixed subgroups remain exactly:

- `weather_clear`: `weathersit=1`;
- `weather_mist`: `weathersit=2`;
- `weather_adverse`: `weathersit in {3,4}`;
- `day_non_working`: `workingday=0`;
- `day_working`: `workingday=1`;
- `demand_peak`: `hr in {7,8,9,16,17,18}`;
- `demand_off_peak`: every other hour.

Membership uses request fields only and overlaps by design. Every fixed subgroup MUST appear in
every fold and in the pooled report. Each must have at least 100 paired labeled rows per fold and in
the pooled set. Any deficiency makes the trial `UNKNOWN`; no subgroup may be dropped or merged.

### 7.2 Frozen bootstrap

Every fold and the pooled out-of-fold set use the same paired calendar-day cluster bootstrap:

1. sort distinct validation calendar days;
2. use `numpy.random.Generator(PCG64(2026))`;
3. for each replicate, sample the same number of days with replacement and retain every hourly pair
   for each sampled occurrence;
4. compute overall and subgroup ratios from those sampled paired errors;
5. run exactly `2,000` replicates;
6. sort ratios ascending and take zero-based element `1,899`, equivalent to
   `ceil(0.95 * 2000) - 1`, as the one-sided UCB95.

The pooled bootstrap operates on the union of the four mutually disjoint validation intervals;
each source date is still one cluster. Point ratios use original unresampled rows. Empty sampled
subgroups, non-positive stable error, non-finite errors/ratios, or a changed RNG/count/quantile make
the entire trial `UNKNOWN`.

### 7.3 Qualification and final development PASS

The development gate intentionally keeps the confirmatory quality thresholds unchanged. This is
not a response to Candidate-v2's failure and does not claim family-wise confirmatory coverage after
19-candidate selection. H2 remains the sole confirmatory test.

A final-eligible trial **qualifies for ranking** only if all conditions hold:

1. all four folds have 100% adapter, stable-prediction, candidate-prediction, and development-label
   completeness with exact identity accounting; every prediction is paired, finite, non-negative,
   and policy-matched;
2. every fixed subgroup has `n >= 100` in every fold and pooled;
3. pooled overall point ratio `<= 0.97`;
4. pooled overall one-sided UCB95 `<= 0.97`;
5. every pooled subgroup point ratio `<= 1.05`;
6. every pooled subgroup one-sided UCB95 `<= 1.05`;
7. every fold overall point ratio `<= 1.05`;
8. at least three of four fold overall point ratios `<= 1.00`;
9. all fold-level overall/subgroup point ratios and UCB95 values are reported even where they are
   not separate threshold tests;
10. feature-lineage, timestamp, chronology, no-H2-access, and train-only preprocessing audits PASS;
11. training/serving temporal-schema golden vectors and family converter contract PASS;
12. all development artifacts and reports have exact SHA-256 identities and no private path or raw
    environment data.

Conditions 7–8 forbid a single-fold-only win without inventing a looser confidence threshold for a
quarter-sized fold. Fold bootstrap distributions remain mandatory diagnostics; the unchanged
0.97/1.05 UCB gates are applied once to the preregistered pooled out-of-fold selection set and later
once to H2 as the confirmatory set.

After ranking, the provisional winner MUST be fitted again on each of the same four training windows
with the same source, data, configuration, dependency, seed, and thread settings. Replay PASS
requires exact reproduction of configuration, preprocessing-state, feature-vector,
prediction-vector, metric, and receipt digests for all four folds. Only then does the overall
development gate PASS and the provisional winner become the unique final development winner.

For qualification, any threshold failure is `FAIL`; missing, invalid, statistically insufficient,
or budget-exceeded evidence is `UNKNOWN`. For provisional-winner replay, either `FAIL` or `UNKNOWN`
makes the entire selection `UNKNOWN/NO_ELIGIBLE_CANDIDATE`. None permits final-candidate
construction, fallback selection, or H2 access.

## 8. Final training, deployment feasibility, and freeze

### 8.1 Final refit

Only the unique final development winner produced by Section 6.4 after replay PASS may be refit. The
final development interval is exactly
`[2011-01-01 00:00, 2012-07-01 00:00)`, containing 2011 plus observed H1 and no H2.

The final development winner's preregistered family, hyperparameters, seed, feature subset,
preprocessing, and recency rule are unchanged. A `REC` winner uses its exact trailing window ending
at `2012-07-01 00:00`; a `STAT` or `NL` winner uses the full final development interval. There is no
post-selection calibration unless calibration was already part of that winning trial's exact
pipeline. There is no second candidate, rank-two fallback, reranking, or replay-triggered search
retry.

### 8.2 Pre-H2 deployment feasibility

Before H2 authorization, the exact final candidate bytes MUST pass tests using only development or
synthetic inputs:

- ONNX export under the frozen converter/opset/operator policy;
- native versus ONNX Runtime prediction parity with `rtol=1e-5` and `atol=1e-5`, with maximum
  absolute error recorded;
- temporal schema validation and training/serving golden-vector parity;
- deterministic replay and validator-receipt recomputation;
- artifact-descriptor, archive, operator, graph, finite-output, and 64 MiB ONNX limits;
- non-root, read-only, capability-dropped, no-new-privileges container boundary with no Docker
  socket or external candidate network;
- exactly 1.0 CPU, 384 MiB hard memory, and authoritative Linux cgroup v2 `memory.peak <= 256 MiB`
  using one v0.1-approved measurement mode—never RSS, `psutil`, Docker UI, `docker stats`, or a host
  estimate as authoritative evidence;
- at least 200 excluded warm-ups per predictor, then exactly 2,000 single-row requests at 80
  admissions/second and at most 32 in flight, with zero errors and nearest-rank p95 `<= 25 ms`;
- local immutable image/artifact identity, SBOM, provenance, vulnerability/license policy, and
  offline-verifiable supply-chain bundle;
- CPU-only reviewer recomputation with no H2, GPU, paid API, or external publication.

These tests prove deployability and evidence recomputability only. They MUST NOT be described as H2
quality, natural promotion, production readiness, or proof that temporal features improve
generalization. A feasibility `FAIL` or `UNKNOWN` blocks freeze/unseal; it does not permit threshold
or candidate changes.

### 8.3 Immutable freeze manifest

After the exact final candidate and all pre-H2 feasibility evidence exist, one RFC-8785 canonical
v0.2 freeze manifest MUST bind:

- manifest/schema/canonicalization versions;
- this approved design-spec digest;
- `SEARCH_SOURCE_COMMIT`, `SEARCH_FREEZE_COMMIT`, the frozen search-receipt digest, and proof that
  their parent/diff/code-identity preflight passed;
- exact clean **candidate source commit** and dependency-lock digest; this is the commit containing
  every byte capable of affecting candidate/stable prediction or gate behavior, immediately before
  the freeze manifest is added;
- frozen search-receipt and complete 20-trial-summary digests;
- four fold boundaries, train/validation identities, policy/statistical-code hashes, and selected
  development report/replay digests;
- dataset DOI/archive digest and exact 2011+H1 development-row identities;
- `mdcp.temporal-features.v0.2` schema, constants, timezone dependency, feature subset, fitted
  preprocessing-state digest, leakage receipt, and golden-vector receipt;
- selected trial ID, family, exact parameters, seeds, training boundary, training receipt, and
  MLflow run ID, immutable artifact URI, and numeric model-version lineage;
- candidate native artifact, ONNX bytes, size, opset, operator inventory, schema, descriptor, image,
  SBOM, provenance, scan, validation, parity, latency, load, and cgroup-memory evidence digests;
- the frozen production stable comparator identities from Section 5.1;
- evaluator, subgroup, quality-policy, cluster-bootstrap, and reason-code identities;
- H2 seal identity: archive digest, logical H2 interval, v0.1 freeze-manifest digest
  `f64004507703c342a0e116b6867185cdabee1a16870ed52f4d3ca16e0719dad7`, and state
  `SEALED_NOT_LOADED`; the historical v0.1 string `SEALED_NOT_OPENED` is an earlier spelling of this
  same never-loaded state, not evidence of an opening;
- `h2_loaded_rows=0` at freeze;
- `h2_unseal_authorized=false` and `one_shot_consumed=false`.

The manifest MUST avoid a Git self-reference cycle. It binds the candidate source commit, then is
added by one subsequent **freeze commit** whose diff from that parent contains only the manifest and
approved immutable evidence indexes. The freeze commit SHA cannot appear inside its own manifest;
the later owner authorization receipt binds both the freeze-manifest digest and freeze commit SHA.
H2 preflight requires a clean worktree at exactly that freeze commit, verifies its parent is the
bound candidate source commit, and rejects any additional prediction/gate-affecting diff.

Candidate freeze means no byte affecting features, preprocessing, prediction, stable comparison,
evaluation, thresholds, subgroups, or evidence interpretation may change. A later owner
authorization is a separate immutable authorization receipt; it does not edit or regenerate the
manifest.

Any digest mismatch, dirty source, unbound artifact, changed dependency, missing parity/feasibility
receipt, or inconsistent H2 state fails closed and requires a new protocol version without opening
H2.

## 9. H2 single-use confirmatory contract

### 9.1 Preconditions

H2 may transition out of `SEALED_NOT_LOADED` only when all are true:

1. this design is approved;
2. a separately reviewed implementation plan is approved;
3. implementation and its tests are complete;
4. the development gate PASSes;
5. one final candidate is frozen;
6. the freeze manifest is committed at the exact clean freeze commit whose parent is the manifest's
   bound candidate source commit;
7. candidate artifact/ONNX and stable comparator identities are locked;
8. every pre-H2 deployment-feasibility gate PASSes;
9. all manifest and receipt digests recompute;
10. the owner gives a new, explicit H2-unseal authorization bound to that manifest digest.

This design and its commit do not satisfy condition 10.

### 9.2 One-shot state machine

The minimal H2 ledger is:

```text
SEALED_NOT_LOADED
  -> AUTHORIZED_FOR_SINGLE_USE
  -> UNSEALED_EVALUATION_IN_PROGRESS
  -> CONSUMED_PASS | CONSUMED_FAIL | CONSUMED_UNKNOWN
```

The authorization transition is append-only and binds the exact manifest, source, candidate,
stable, evaluator, policy, and H2 seal identities. Starting the H2 loader atomically consumes the
one-shot token before any row is returned. Crash, partial output, identity mismatch, or missing
evidence after consumption yields `CONSUMED_UNKNOWN`; it does not restore the token.

Read-only recomputation of metrics from the immutable, already-produced paired evidence bundle is
allowed after consumption and MUST reproduce its digest. It is not permission to reload H2, rerun
model inference, change predictions, or form another candidate.

### 9.3 Confirmatory execution and gate

The evaluator loads H2 exactly once and performs stable and candidate inference on the same rows.
It MUST NOT retrain, recalibrate, alter a feature, modify a threshold/subgroup, add a trial, or select
a replacement candidate.

The H2 authoritative source-row inventory is sealed before adaptation. Every row MUST produce one
valid v2 evaluation envelope and exactly one finite non-negative stable prediction plus exactly one
finite non-negative candidate prediction. Adapter completeness and both prediction completeness
rates MUST each be 100%; any failure, duplicate, missing identity, schema error, or accounting gap
makes the entire H2 gate `UNKNOWN` and cannot be removed from the denominator. Only genuinely missing
labels may use the label-completeness allowances below.

The confirmatory gate retains the frozen v0.1 policy:

- adapter successes equal 100% of authoritative H2 source rows;
- unique finite non-negative stable and candidate prediction pairs equal 100% of adapter-valid rows;
- at least 2,000 valid paired predictions overall before label filtering;
- overall label completeness at least 99.5%;
- label completeness at least 99.0% within every fixed subgroup;
- every fixed subgroup has at least 100 paired labeled rows, otherwise whole-gate `UNKNOWN`;
- overall point ratio `<= 0.97`;
- overall one-sided UCB95 `<= 0.97`;
- every fixed subgroup point ratio `<= 1.05`;
- every fixed subgroup one-sided UCB95 `<= 1.05`;
- exactly 2,000 paired calendar-day cluster replicates using `PCG64(2026)` and nearest-rank index
  `1,899`;
- finite non-negative outputs, positive finite stable denominators, complete identities, and
  deterministic recomputation.

Results have exactly these consequences:

- `PASS`: the artifact becomes a **natural promotion candidate** and may enter the Wave 3 natural
  path only after its separate wave prerequisites and authorizations pass;
- `FAIL`: the candidate is `REJECTED`, the terminal model status remains
  `NO_ELIGIBLE_CANDIDATE`, and H2 cannot be used for tuning;
- `UNKNOWN`: promotion is forbidden, the terminal model status remains
  `NO_ELIGIBLE_CANDIDATE`, and the complete reason/evidence is preserved.

After `FAIL` or `UNKNOWN`, further research requires new, previously unobserved data and a newly
versioned preregistered protocol. H2 can never again be a confirmatory set.

## 10. Minimal milestone and Wave integration

v0.2 does not redesign the delivery control plane. It inserts one temporal eligibility track before
the existing natural Wave 3 path:

| Milestone/state | Entry | PASS output | FAIL/UNKNOWN output |
|---|---|---|---|
| `T0_TEMPORAL_PROTOCOL_APPROVED` | written-spec owner approval | implementation planning may be separately authorized | remain design-only |
| `T1_TEMPORAL_DEVELOPMENT` | approved implementation plan and complete implementation | one replay-verified final development winner and complete trial evidence | `NO_ELIGIBLE_CANDIDATE`; H2 sealed |
| `T2_CANDIDATE_FREEZE_FEASIBILITY` | T1 PASS | immutable manifest and pre-H2 feasibility PASS | `NO_ELIGIBLE_CANDIDATE`; H2 sealed |
| `T3_H2_CONFIRMATORY` | T2 PASS plus separate owner unseal authorization | `NATURAL_PROMOTION_CANDIDATE` | `NO_ELIGIBLE_CANDIDATE`; H2 consumed |

State transitions are:

```text
NO_ELIGIBLE_CANDIDATE
  -> V02_DEVELOPMENT_AUTHORIZED
  -> V02_DEVELOPMENT_PASS
  -> V02_CANDIDATE_FROZEN
  -> H2_AUTHORIZED_FOR_SINGLE_USE
  -> NATURAL_PROMOTION_CANDIDATE | NO_ELIGIBLE_CANDIDATE
```

`H2_AUTHORIZED_FOR_SINGLE_USE` is the model-eligibility view of the H2 ledger's
`AUTHORIZED_FOR_SINGLE_USE` state; it does not create a second authorization state.

`FAIL` or `UNKNOWN` at any intermediate gate returns/stays at `NO_ELIGIBLE_CANDIDATE` while
preserving the new evidence and the most advanced honest milestone.

The existing Waves retain these meanings:

- Wave 0 `PASS 8/8` remains valid and is not rerun or relabeled;
- v0.1 Wave 1 natural `FAIL` remains valid and is never converted to PASS;
- Wave 2 local engineering artifacts may be reused only after their candidate/schema/identity
  bindings are regenerated for v0.2; their existence does not make a candidate eligible;
- Wave 3 remains forbidden until `T3_H2_CONFIRMATORY=PASS` and the original Wave 2/external entry
  gates are actually satisfied;
- synthetic control-plane and rollback fixtures remain valid only as `synthetic_test` evidence and
  never replace natural eligibility.

## 11. Evidence, security, and test requirements

### 11.1 Required evidence classes

Every artifact MUST declare one of these non-interchangeable roles:

- historical v0.1 natural rejection;
- v0.2 development/selection evidence;
- pre-H2 synthetic or deployment-feasibility evidence;
- v0.2 H2 single-use natural confirmatory evidence;
- later control-plane synthetic failure evidence.

Development or synthetic PASS cannot be presented as H2 or natural promotion PASS. Natural failure
evidence is a successful demonstration of fail-closed governance, not evidence that the entire
control plane failed.

### 11.2 Security boundary

- Raw UCI data, H2 rows, labels, development predictions, model artifacts, runtime databases, and
  private evidence remain Git-external unless a later approved publication policy explicitly names
  a sanitized aggregate.
- Repository docs and public reports contain no credential, username, hostname, absolute private
  path, raw environment dump, container ID, or opaque evidence payload.
- Dataset and candidate input are untrusted. Archive traversal, links, duplicate members, unexpected
  files, executable model formats, mutable image references, unsafe ONNX external data, and
  non-allowlisted operators fail closed.
- Training code has read-only development-data access and no H2 capability. The H2 loader is a
  separate capability guarded by manifest identity and the one-shot authorization ledger.
- Model selection has no network, paid API, GPU, Docker socket, or write access to repository
  history. External publication remains a separately authorized boundary.
- Logs and receipts contain bounded metrics, logical identities, digests, and fixed reason codes;
  they do not contain raw exceptions, features, labels, timestamps tied to individual users, or
  private paths.
- Stable-only legacy-v1 traffic, valid v2 candidate-eligible traffic, and invalid-v2 rejections use
  distinct low-cardinality accounting. No window or receipt may merge their admissions,
  completeness, predictions, or quality denominators.

### 11.3 Required test layers for a future implementation

A future implementation plan must map every requirement to tests and digest-bearing evidence:

1. strict envelope-version/timestamp/timezone/cross-field validation, exact half-open domain
   `[2011-01-01 00:00:00, 2013-01-01 00:00:00)`, legacy stable-only routing, v2 candidate
   eligibility, and fail-closed reason codes;
2. exact 18-field feature order/formulas and golden vectors, including DST/leap/year boundaries and
   both accepted/rejected timestamp-domain edges;
3. forbidden-feature and target-lineage property tests;
4. exact fold-boundary, no-overlap, expanding-history, whole-calendar-day, and no-H2-import tests;
5. exact 20-trial inventory, parameters, seeds, ranking, fit-count, and budget tests;
6. training-only preprocessing and recency-window boundary tests;
7. immutable source-row inventory; 100% adapter/stable-prediction/candidate-prediction accounting;
   label-only missingness policy; denominator-preserving paired metrics/bootstrap; subgroup
   completeness; and `UNKNOWN` properties;
8. qualification-before-ranking, provisional-winner-only replay, replay failure without rank-two
   fallback, cross-fold stability, no-single-fold-win, and tie-break tests;
9. final-refit lineage and manifest tamper/dirty-source/fail-closed tests;
10. ONNX parity/operator/schema, container isolation, load, cgroup-memory, and reviewer tests using no
    H2;
11. H2 permission/state/concurrency tests proving one token, consume-before-read, and no reset after
    crash;
12. confirmatory PASS/FAIL/UNKNOWN fixtures, adapter/prediction failures that cannot masquerade as
    missing labels, and proof that no result can spawn a second candidate;
13. claim/private-path/raw-data/evidence-payload leakage scans;
14. state/Wave dependency tests proving Wave 3 cannot start before natural H2 PASS.

Synthetic H2-shaped fixtures MAY test machinery but MUST contain no UCI H2 row and MUST be labeled
`synthetic_test`.

## 12. Research and public-claim ceiling

Before an actual H2 PASS, permitted claims are limited to:

- v0.1 correctly rejected a cross-year regression candidate under its frozen gate;
- v0.1 rejection evidence was preserved with the digests in this specification;
- v0.2 is a preregistered causal temporal retraining protocol;
- H1 is observed development data and not a blind holdout;
- H2 remains sealed and has not been loaded;
- whether an eligible candidate exists remains unknown.

The project MUST NOT claim:

- dataset shift has been solved;
- a production-ready model exists;
- H2 has passed or has been previewed;
- temporal features necessarily improve generalization;
- natural promotion has succeeded;
- H1 remains blind or confirmatory;
- v0.1 Wave 1 naturally passed;
- a current eligible candidate exists;
- a negative model result means the control plane failed.

Even after a future H2 PASS, claims remain bounded to this fixed dataset, chronology, feature
contract, comparator, policy, artifact, local resource profile, and accepted local-time interval
`[2011-01-01 00:00:00, 2013-01-01 00:00:00)`. No result establishes a general long-term forecasting
API or support for later timestamps.

## 13. Written-spec acceptance and stop point

This document passed final owner written-spec review after a fresh self-review confirmed:

- no placeholder or unresolved choice;
- no contradiction between historical and v0.2 roles;
- acyclic `SEARCH_SOURCE_COMMIT -> SEARCH_FREEZE_COMMIT` identity with exact-parent and allowlisted
  diff verification;
- qualification before ranking, one provisional winner, replay before final-winner status, and no
  rank-two fallback;
- exact, causal, non-overlapping fold dates;
- one unique feature schema with no target/future leakage;
- the sole accepted timestamp domain is `[2011-01-01 00:00:00, 2013-01-01 00:00:00)`;
- exactly 20 formal trials and at most 85 fits;
- unchanged 0.97/1.05, subgroup, bootstrap, seed, replicate, and minimum-sample rules;
- 100% adapter and stable/candidate prediction completeness before label-only missingness handling;
- distinct legacy stable-only, valid-v2 candidate-eligible, and invalid-v2 accounting;
- one replay-verified final development winner and one H2 candidate;
- freeze and H2 one-shot transitions fail closed;
- Wave 3 cannot start before H2 PASS;
- no private path or opaque payload is present;
- no implementation command, H2 access, model run, Docker/GPU action, or external publication is
  authorized by this spec; only implementation planning is authorized.

The terminal state for this commit is:

`DESIGN_SPEC_APPROVED / H2_SEALED / IMPLEMENTATION_PLANNING_AUTHORIZED`

Implementation planning is authorized. Implementation work, formal search, H2 access, model runs,
Docker/GPU actions, Wave 3, and external publication still require their separately declared gates.
