# MDCP v0.2 Formal Seal Final-Review Corrective Design

Status: owner approved

Date: 2026-08-26

Repository: `model-delivery-control-plane`

Branch: `codex/wave0-foundation-feasibility`

Rejected freeze checkpoint: `2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598`

## 1. Purpose and authority boundary

This amendment corrects the final independent review of the closure-owned formal-seal
implementation. The review verdict was Critical `1`, Important `3`, Minor `1`, so the existing
freeze is not eligible for P2 authorization even though its mechanical freeze, source-archive,
identity, and test gates passed.

This document does not authorize implementation, P2, a real authorization, dataset access, model
execution, or publication. A separate owner-approved implementation plan is required after written
approval of this specification.

The correction preserves the approved architecture:

- one process, one fit ledger, one replay session, and one formal operation;
- one canonical private-evidence container followed by one terminal public seal;
- Windows-only mutation with retained handles and no POSIX mutation claim;
- exactly four folds, 20 trials, 19 eligible candidates, 80 selection fits, at most four replay
  fits, and at most one final fit;
- H2 `SEALED_NOT_LOADED`, H2 loaded rows `0`;
- append-only Git history and no remote, push, tag, Release, or Wave 4 activity.

## 2. Review findings being corrected

The implementation must close all five findings as capability defects, not merely rename the
reported symbols.

1. Module-level runner attributes can compose natural archive loading, model construction, and the
   80+4 engine without authorization consumption. The affected surface includes, but is not limited
   to, `_FormalDevelopmentInputs`, `_DevelopmentExecutionPlan`, `_execute_fit`,
   `_run_development_core`, `_build_formal_execution_plan`, `_load_formal_execution_state`, and
   `_fit_formal_fold`.
2. The formal private destination is not independently required to be outside the repository. An
   ignored in-repository destination can evade the clean-tree check.
3. Recovery accepts a structurally valid but semantically inconsistent five-file private chain.
   Winner, qualification, replay documents, and replay digests are insufficiently cross-bound.
4. `cli.py` exposes `_emit_check`, although the approved callable surface is exactly
   `build_parser` and `main`.
5. Several preflight, marker, and error paths ignore the boolean result of checked handle closure.

## 3. Goals and non-goals

### 3.1 Goals

- Make the formal natural execution capability reachable only through
  `execute_authorized_formal_development`.
- Reject every module-level, aliased, default-bound, class-owned, registered, or factory-returned
  path that can load natural data, construct or fit a model, invoke an attacker-supplied fit
  callback, consume authorization, or publish formal evidence.
- Validate both members of the publication pair as external to the repository before authorization
  consumption or loader access.
- Make recovery a semantic verification of one closed five-file chain, not a collection of
  independently well-shaped documents.
- Restore the exact CLI callable surface.
- Check every close result and preserve deterministic PASS/FAIL/UNKNOWN behavior.
- Produce a new append-only source identity and a new receipt-only freeze only after independent
  Critical `0` and Important `0` review.

### 3.2 Non-goals

- No P2 formal development run or real formal authorization.
- No UCI, H1, or H2 row access; no model fit, inference, ONNX, MLflow, Docker, GPU, or network use.
- No new dependency, process, worker, IPC protocol, module, schema family, data source, feature,
  threshold, fit budget, or platform support.
- No modification of v0.1/v0.2 serving identities, protected Wave 0-2 evidence, dependency lock,
  approved temporal protocol, historical plans, or historical commits.
- No attempt to make an underscore-prefixed name an authority boundary.

## 4. Selected architecture

### 4.1 Option A: closure-local formal engine — selected

The bootstrap factory in `run_evidence.py` constructs the sole formal operation during module
initialization and is then deleted from the module namespace. Every object with natural execution
power lives inside that operation's closure:

- formal input state;
- lazy protocol/archive loader;
- fold and trial materialization;
- estimator construction and fit adapter;
- the one-shot 80+4 state machine;
- authorization consumption and retained publication handles;
- natural private-container encoder; and
- terminal public-seal publisher.

The isolated synthetic harness extracts and compiles the bootstrap factory's AST with deterministic
generated bindings. It exercises the same nested state machine without leaving the factory or any
natural-capable helper in production module state.

`runner.py` retains only records and pure transformations that cannot load an archive, construct or
fit a model, accept an execution callback, consume authorization, or write a destination. Any
callback-taking execution helper is moved into the deleted bootstrap factory. This rule applies by
capability, regardless of the helper's spelling or underscore prefix.

### 4.2 Option B: module-private token or sentinel — rejected

A private token, renamed helper, call-stack check, or default-bound sentinel remains reachable or
forgeable through Python introspection. It repeats the confused-authority design and is outside this
threat model.

### 4.3 Option C: dedicated OS worker — deferred

A dedicated worker would provide a stronger memory boundary, but it changes the approved
one-process lifecycle and introduces process launch, IPC, worker identity, source inventory, and
operational policy. It requires a separate future design and is not part of this correction.

## 5. Exact authority and callable boundary

The exact post-initialization formal callable/type surface remains:

```text
src/mdcp/temporal/cli.py:
  build_parser
  main

src/mdcp/temporal/run_evidence.py:
  FormalDevelopmentRequest
  FormalDevelopmentOutcome
  FormalDevelopmentSeal
  FormalRunConsumptionMarker
  FormalSealCheck
  execute_authorized_formal_development
  verify_formal_development_seal

src/mdcp/temporal/search_identity.py:
  FormalRunAuthorization

src/mdcp/temporal/runner.py:
  no natural-capable or callback-taking formal callable/type
```

Existing synthetic-only and pure verification surfaces are not reclassified as formal mutation
authority, but they must fail the reachability audit if they expose any of these capabilities:

- authorization parse, validation, claim, or consumption;
- natural archive or row loading;
- estimator construction, fit, replay, or final fit;
- invocation of a caller-provided execution callback;
- natural private-container construction;
- destination acquisition or publication; or
- a returned object, alias, default, class attribute, registry, or container that reaches one of the
  above.

The production bootstrap factory and its dependency tuple are deleted immediately after binding
the two intended operations. Closure-cell introspection and pre-initialization monkeypatching remain
outside the previously approved threat model. Named module attributes, aliases, defaults, keyword
defaults, bound methods, class attributes, registries, factory results, and values returned from
allowed public test calls remain inside the threat model.

`cli.py` contains no `_emit_check` or separately named command handler. `main` performs fixed
sanitized JSON emission inline and dispatches `execute_authorized_formal_development` exactly once
for `run-development`.

## 6. External paired-destination boundary

Before authorization consumption, marker acquisition, archive access, output creation, or model
construction, the operation validates all of the following:

1. `repository_root` is the expected clean repository and freeze identity.
2. `consumption_root` is an existing trusted directory outside the repository.
3. `private_container_path` is an absolute canonical leaf whose existing parent is outside the
   repository.
4. The derived terminal path is the same parent's child named
   `<private filename>.public.json`.
5. The private and terminal paths are distinct, both leaves are absent, and neither may be selected
   independently by the caller.
6. Every Windows ancestor is opened and retained without symlink, junction, reparse, identity, or
   path-boundary ambiguity.
7. Both destination handles pass the existing no-clobber and handle-relative preflight.

An ignored repository path such as `<repository>/runtime/...` is invalid even when `git status` is
clean. Textual prefix checks are insufficient by themselves; the existing canonical path and
handle-relative ancestor checks remain mandatory. POSIX and other platforms return
`PUBLICATION_UNSUPPORTED` before mutation.

## 7. Checked-close semantics

Every close helper returns a boolean and every caller consumes that result. A close failure cannot
be discarded in an exception handler or cleanup suffix.

| Phase | Close failure outcome | Authorization retry |
| --- | --- | --- |
| destination preflight, before marker attempt | `FAIL/FORMAL_RUN_DESTINATION_INVALID` with fit count `0` | no retry in the same process |
| marker attempt with no owned handle and a proven absent leaf | existing deterministic marker matrix result | only the already-approved sole pre-create retry row |
| marker attempt after an owned or possibly owned handle exists | `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN` | forbidden |
| private publication or cleanup after consumption | existing terminal `UNKNOWN` publication reason | forbidden |
| terminal public-seal publication | `UNKNOWN/FORMAL_RUN_SEAL_UNKNOWN` | forbidden |
| read-only recovery handle close | recovery never returns `PASS`; fixed sanitized `FAIL` or `UNKNOWN` according to the existing trust matrix | not applicable |

The operation never deletes by a caller-provided path to recover from an uncertain close. Owned
partial cleanup remains handle-relative. Public outcomes never contain a handle, path, exception,
environment value, or raw OS status.

## 8. Closed five-file semantic chain

The canonical private container still contains exactly:

```text
provisional-winner.json
qualification-report.json
ranking-report.json
replay-report.json
trial-summary.json
```

Recovery first verifies canonical encoding, exact filenames, no missing/extra/duplicate entries,
per-file physical SHA-256, private inventory identity, private container identity, terminal seal,
and the externally supplied terminal-seal digest. It then verifies the following semantic chain.

### 8.1 Qualification and winner

- Qualification contains the exact 19 eligible trial IDs and exact four fold IDs in canonical
  order.
- Each fold document is canonicalized and hashed. Its recomputed digests must equal the associated
  fold-digest object field by field.
- The qualification inventory digest is recomputed from those exact ordered trial/fold identities.
- A provisional winner, when present, must match exactly one eligible qualification entry on
  `trial_id`, `family_id`, configuration identity, report identity, closed metrics, ranking key,
  ordered fold digests, and qualification inventory identity.
- No standalone winner value may substitute for the corresponding qualification value.

### 8.2 Ranking and trial summary

- Ranking references the same qualification inventory and exact eligible trial set.
- Its ordering is recomputed from the approved ranking rule rather than trusted as supplied.
- Status, reason codes, winner presence, and winner identity agree with qualification and terminal
  seal state.
- Trial summary contains the exact 20 trials, fixed family/configuration identities, and exact fit
  counts. It agrees with ranking and qualification; it cannot introduce a second candidate or a
  different winner.

### 8.3 Replay

- No-winner replay is exactly `replay_trial_id=null`, empty folds, and empty digests.
- Winner replay identifies the same winner and contains exactly four canonical fold documents and
  four fold-digest objects in the approved fold order.
- Each replay document is canonicalized and its configuration, preprocessing, feature-vector,
  prediction-vector, metric, and receipt identities are recomputed or derived from the exact
  document fields.
- Each recomputed value equals the corresponding replay-digest value at the same fold position.
- Replay verdict, selection status, reason codes, fit count, qualification identity, private
  identity, and terminal seal all agree.

A mutation test must coordinate changes to payload fields, winner fields, replay documents,
replay-digest objects, per-file hashes, and private-container hashes. The verifier must still reject
the result when its semantic relationships differ. If an attacker also changes terminal bytes, the
externally retained terminal-seal digest must reject it.

## 9. Immutable evidence and append-only migration

The following rejected checkpoint remains immutable:

- freeze commit: `2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598`;
- receipt SHA-256:
  `7bf1f01f5883c563639152b8eda6fbff8ab1171c85a5865e21ee0303afdbdc94`;
- evidence-index SHA-256:
  `ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d`;
- custody SHA-256:
  `38fc225f45fc2a282be339c8d6974154bd90a94af93132ed2132ca5c9b04bf9f`.

No amend, rebase, reset, squash, cherry-pick, deletion, or history rewrite may alter that evidence.
Its Git commit and external custody record remain the rejected historical proof.

The corrective migration is append-only:

1. commit this design amendment;
2. record owner written approval in a new docs-only commit;
3. create and independently review a new corrective implementation plan;
4. execute each corrective task with RED -> GREEN, independent review, and a scoped commit;
5. run all fresh completion gates from the committed tree;
6. create a new `SEARCH_SOURCE_COMMIT` only after Critical `0` and Important `0`;
7. generate new canonical receipt/index bytes from that source commit;
8. independently validate and preserve the new index digest under a new no-clobber custody identity;
9. create a new receipt-only direct-child freeze commit; and
10. rerun the freeze, source-archive, identity, protected-byte, and independent whole-range review
    gates.

The two canonical evidence paths may receive new bytes only in step 9. Their old bytes remain
immutable in `2cb2f0b` and its external custody. The new freeze never claims the old source identity.

## 10. Source-archive reproducibility

The current source inventory contains a deliberate mixed line-ending profile. A successful
diagnostic proved byte-identical `git archive` extraction without `.git` by using an external
temporary attributes profile that forces LF generally and CRLF only for:

```text
src/mdcp/temporal/firewall.py
src/mdcp/temporal/run_evidence.py
src/mdcp/temporal/runner.py
src/mdcp/temporal/search_identity.py
```

The implementation plan must reproduce this profile from literal reviewed content in a new OS
temporary directory. It must not depend on a private absolute path, modify `.gitattributes`, or
change the 19-path implementation allowlist. The archive must be regenerated under
`core.autocrlf=true`, `false`, and `input`; all three archives must have identical bytes and pass the
external retained-index verifier with no `.git` directory.

## 11. Implementation file boundary

The future corrective plan may modify only the existing 19 implementation paths:

```text
src/mdcp/temporal/runner.py
src/mdcp/temporal/cli.py
src/mdcp/temporal/runtime_guards.py
src/mdcp/temporal/run_evidence.py
src/mdcp/temporal/firewall.py
src/mdcp/temporal/search_identity.py
schemas/v2/development-result-index.schema.json
schemas/v2/formal-run-authorization.schema.json
tests/unit/temporal/test_fit_ledger.py
tests/unit/temporal/test_runtime_guards.py
tests/unit/temporal/test_run_evidence.py
tests/integration/temporal/test_formal_runner_synthetic.py
tests/integration/temporal/test_search_freeze_preflight.py
tests/security/temporal/test_data_firewall.py
tests/security/temporal/test_formal_runner_firewall.py
tests/security/temporal/test_formal_run_authorization.py
tests/security/temporal/test_public_evidence_boundary.py
evidence/public/v02/search/search-receipt.json
evidence/public/v02/search/evidence-index.json
```

The final two evidence paths remain forbidden until the terminal freeze task. A new production or
test module, private-container schema, dependency change, `.gitattributes`, protocol change, or path
outside this list requires a new owner stop.

## 12. Corrective task boundaries

The future implementation plan must preserve these independently reviewable commits:

1. Remove every module-reachable callback/natural execution capability and place the one-shot
   engine inside the deleted bootstrap factory.
2. Enforce the external private/public destination boundary and checked-close matrix.
3. Close the winner/qualification/ranking/trial-summary/replay semantic chain.
4. Restore the exact CLI callable surface.
5. Run an independent capability audit and correct only defects within the same approved boundary.
6. Recompute the 43-path source identity and prove source-archive reproducibility without `.git`.
7. Create the new receipt/index/custody identities and receipt-only freeze commit.

Every production change begins with a real failing test that demonstrates the reviewed defect. A
test that merely changes the expected whitelist to bless an existing callable is not a valid RED.
Every task receives an independent read-only review and may commit only at Critical `0`, Important
`0` for that task.

## 13. Required RED -> GREEN proofs

The corrective plan must include concrete negative tests for:

- direct, alias, qualified, default-bound, class-owned, registry-held, and returned-object access to
  all removed runner capabilities;
- a renamed or newly introduced callback-taking helper;
- an isolated synthetic factory that proves 80 selection fits, four replay fits, the 85-fit ceiling,
  one ledger, one replay session, and one guard lifecycle without natural data;
- repository-root, repository-child, ignored repository-child, symlink, junction, existing leaf,
  same-leaf pair, and indeterminate ancestor/destination states;
- every checked-close failure before marker, during marker, after private publication, and during
  terminal publication;
- winner values inconsistent with the selected qualification;
- reordered, missing, extra, or duplicate qualification/replay folds;
- replay documents inconsistent with their replay-digest objects;
- coordinated five-file and internal-digest mutation;
- terminal-seal mutation with an unchanged external expected seal digest;
- any callable in `cli.py` other than `build_parser` and `main`;
- stdout write/flush failure without raw exception disclosure;
- H2 loader, legacy full loader, `split_rows`, `DatasetPartitions.open_h2`, environment, network,
  clock, entropy, or private-path bypass; and
- source archives with `.git`, wrong EOL bytes, missing/extra/duplicate paths, zero index identity, or
  an index copied from the archive instead of external custody.

## 14. Completion and review gates

After all corrective commits, fresh committed-tree verification requires:

- task-targeted RED/GREEN suites;
- full CPU pytest regression;
- temporal, contract, security, behavioral H2, publication, recovery, source-archive, and identity
  suites;
- exact callable/capability reachability audit;
- exact 43-path source inventory and external custody proof;
- no-`.git` archive recomputation under all three `core.autocrlf` modes;
- Ruff check and exact changed-Python format check;
- `uv lock --check` and `git diff --check`;
- credential, private-path, public-evidence, and publication-boundary scans;
- exact protected-byte verification;
- clean worktree, remote count `0`, no HEAD tag, H2 `SEALED_NOT_LOADED`, and H2 loaded rows `0`; and
- a fresh independent whole-range review with Critical `0` and Important `0`.

No passing test count overrides an unresolved review finding.

## 15. Failure and rollback rules

Stop at a clean append-only checkpoint if:

- an implementation path outside the 19-path allowlist is required;
- a protected identity, dependency, protocol, quality threshold, fit budget, or historical evidence
  drifts;
- a natural-capable or callback-taking module attribute remains reachable;
- an output destination cannot be proven external before authorization consumption;
- the recovery chain cannot reject coordinated semantic mutation;
- the source archive cannot be reproduced without modifying repository attributes;
- any Critical or Important review finding remains;
- one blocker survives three separately evidenced hypotheses; or
- any test requires UCI/H1/H2 rows, a real authorization, model execution, Docker, GPU, network,
  remote, publication, P2, or Wave 4.

Do not amend or delete a failed corrective commit. Preserve diagnostics, append the next scoped
correction only when it remains within the approved plan, and never regenerate or overwrite the
rejected `2cb2f0b` custody evidence.

## 16. Terminal states

Successful correction stops at:

```text
SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED / H2_SEALED_NOT_LOADED
```

Blocked correction stops at:

```text
W3_FORMAL_SEAL_CLOSURE_BLOCKED / P2_FORBIDDEN / H2_SEALED_NOT_LOADED
```

Neither state authorizes P2. Only a later explicit owner authorization may create or consume a real
formal-run authorization.

## 17. Design self-review checklist

- No placeholder, incomplete section, optional security gate, or unresolved alternative remains.
- The design removes capability, not merely a reported function name.
- The exact callable boundary is consistent with the approved closure threat model.
- Both output leaves are proven external before authorization consumption.
- Every close result has a deterministic fail-closed consequence.
- Recovery binds semantics across all five private files and the externally anchored terminal seal.
- No digest includes itself and no trust anchor is learned solely from the object being verified.
- Mixed-EOL source-archive reproduction requires no tracked attribute change or private path.
- Existing rejected freeze bytes, custody, protected identities, H2 state, and Git history remain
  immutable.
- The 19-path implementation boundary, review gates, stop conditions, and terminal states are exact.
