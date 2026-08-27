# MDCP v0.2 Dedicated Formal Worker Design Amendment

**Status:** Draft for owner written-spec review
**Date:** 2026-08-27
**Repository:** `model-delivery-control-plane`
**Branch:** `codex/wave0-foundation-feasibility`
**Design entry HEAD:** `91b851c2b9f369cca3744b990b433754399989a6`
**H2 state:** `SEALED_NOT_LOADED`, loaded rows `0`

## 1. Authority and scope

The owner selected a dedicated OS worker as the replacement for the failed closure-local authority
boundary. This document is the design-only amendment for that decision. It authorizes no
implementation plan, source or test change, P2 authorization, formal development run, UCI/H1/H2
row access, model execution, Docker, GPU, network operation, remote, push, tag, Release, evidence
replacement, or Wave 4 action.

After this document is committed, implementation remains forbidden until:

1. the owner reviews and approves these written bytes;
2. a separate corrective implementation plan freezes exact task and commit boundaries;
3. that plan receives owner execution approval; and
4. every implementation task reaches its prescribed Critical `0`, Important `0` gate.

The terminal state for this design-only turn is:

```text
DEDICATED_FORMAL_WORKER_DESIGN_COMMITTED /
P2_FORBIDDEN /
H2_SEALED_NOT_LOADED /
OWNER_WRITTEN_SPEC_REVIEW_REQUIRED
```

## 2. Evidence and architectural root cause

The final-review corrective implementation committed Tasks 1-4 and stopped during Task 5. Three
separately evidenced firewall hypotheses all passed their targeted and full CPU tests, yet each
independent review found another Important callback or provenance bypass.

The counterexamples progressed through these semantic layers:

1. direct, aliased, qualified, default-bound, class-owned, registry-held, container-held, and
   factory-returned callables;
2. composite callees, executor builtins, local sort operations, expanded arguments, and control-flow
   provenance;
3. cross-function global registries, starred and pattern captures, context-manager targets,
   parameter-driven metaclasses, aliased executors, and name rebinding or builtin shadowing.

The exact uncommitted diagnostic bytes at the design entry are:

```text
6841d27e33131888e226cd94a919c2232fff0aa0cb040f29686deeb60c86d233  src/mdcp/temporal/firewall.py
a096f1db08de3158efad029883a93fb440ad7417f57d59451c5ee1bbf20c60c5  tests/security/temporal/test_data_firewall.py
0c2e48907badd8ca11e4e773aea66ee9f746fb42a8583fb571d9ac9971f93759  tests/security/temporal/test_formal_runner_firewall.py
```

Those bytes are rejected diagnostics, not accepted implementation or public evidence. They remain
uncommitted and byte-for-byte preserved during this design turn.

The common root cause is an abstraction mismatch. The implementation attempted to prove, with a
custom AST analysis, that arbitrary dynamic Python contained no path capable of invoking
caller-controlled behavior. Python name binding, descriptors, metaclasses, containers,
cross-function state, reflection, and rebinding make that a whole-language semantic analysis
problem. Adding another syntax rule does not close the model; it moves the next counterexample to a
different language feature.

This is not a conventional test failure. The latest exact bytes passed `1221` CPU tests with `7`
capability skips, but the independent review remained Critical `0`, Important `3`. Passing tests do
not override that review result.

## 3. Supersession and retained requirements

This amendment supersedes only the one-process and whole-language capability-proof portions of:

```text
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md
```

Specifically, it replaces:

- Section 1's `one process` architecture statement;
- Section 3.1's requirement that natural execution be reachable through only one in-process
  Python callable;
- Section 3.2's prohibition on a worker, process, IPC protocol, module, or schema family;
- Sections 4-5's closure-local architecture and callable boundary;
- Section 11's 19-path implementation boundary;
- Sections 12-13's closure-specific corrective tasks and AST capability proofs;
- Section 14's whole-language reachability audit; and
- Section 15's stop condition based on the mere existence of any natural-capable module attribute.

The following requirements remain authoritative without relaxation:

- one formal operation, one authorization consumption, one fit ledger, and one replay session;
- exactly four folds, 20 trials, 19 eligible candidates, 80 selection fits, at most four replay
  fits, at most one later final fit, and at most 85 total fits;
- seed `2026`, one estimator thread, the frozen temporal protocol, feature schema, thresholds,
  ranking, quality, completeness, and replay rules;
- one canonical five-file private-evidence container followed by one terminal public seal;
- Windows-only mutation, retained-handle no-clobber publication, checked-close semantics, and no
  POSIX mutation claim;
- both output leaves proven external before authorization consumption or data access;
- the closed five-file semantic recovery chain and externally anchored terminal-seal digest;
- H1 `OBSERVED_DEVELOPMENT_ONLY` and H2 `SEALED_NOT_LOADED`, loaded rows `0`;
- exact source-archive reproduction without `.git`;
- immutable v0.1/v0.2 serving identities, protected Wave 0-2 bytes, dependency lock, temporal
  protocol, natural rejection evidence, Git history, and external custody; and
- no P2, real authorization, data rows, model execution, Docker, GPU, network, remote, publication,
  or Wave 4 during corrective implementation.

The rejected-freeze topology in:

```text
docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md
```

also remains authoritative. The future correction still uses the separately reviewed `D/D`
tombstone followed immediately by one no-clobber `A/A` receipt-only freeze.

## 4. Goals and non-goals

### 4.1 Goals

- Make the OS byte boundary, not Python object reachability, the formal execution boundary.
- Ensure no callable, callback, class, pickle, code object, module object, descriptor, or other
  executable Python value can cross from supervisor to worker.
- Keep archive bytes, development rows, estimators, predictions, labels, private evidence, and fit
  state out of the supervisor process.
- Require the worker to independently verify every identity and path before consuming authorization
  or reading the archive.
- Bind the exact worker source, protocol, request, and launch profile into the formal seal chain.
- Make timeout, crash, oversized output, nonzero exit, and malformed IPC deterministic fail-closed
  states with no automatic retry.
- Replace the open-ended callback-taint proof with finite protocol, import, identity, lifecycle, and
  process-boundary proofs.
- Preserve all existing model, evidence, publication, recovery, H2, and source-archive invariants.

### 4.2 Non-goals

- This is not a hostile same-user OS sandbox. Supervisor and worker run as the same Windows user.
- It does not resist an administrator, debugger, interpreter replacement, malicious kernel,
  arbitrary process injection, or modification of already trusted source before identity checks.
- It does not claim OS-enforced network isolation. Reviewed source and static capability policy
  continue to prohibit network use; a future separate sandbox may add an OS network policy.
- It does not add a service, daemon, queue, database authority, container, VM, second worker,
  worker pool, retry controller, or distributed protocol.
- It does not add a model family, feature, threshold, dependency, platform, GPU path, or H2 path.
- It does not make the formal worker reusable after an indeterminate launch or consumed
  authorization.
- It does not redesign the already approved private-container format, five-file semantics,
  destination topology, or rejected-freeze custody topology.

## 5. Considered architectures

### 5.1 Dedicated OS worker — selected

One trusted supervisor launches one fresh, isolated Python interpreter for one formal operation.
The only cross-process input and output are bounded RFC 8785 JSON bytes. The worker constructs all
natural execution objects internally, consumes authorization, performs the bounded development
run, publishes the private container and terminal seal, emits one sanitized response, and exits.

This turns the unbounded question "can arbitrary Python recover this callback?" into finite
questions:

- are the request and response schemas exact and canonical;
- did the supervisor launch the reviewed worker with the exact profile;
- did the worker recompute the reviewed source and authorization identities;
- did it consume authorization before data or model access;
- did it publish only the closed evidence pair; and
- did the child exit and response satisfy the exact live-acceptance matrix?

### 5.2 Restricted one-process Python subset — rejected

A restricted subset could forbid globals, decorators, metaclasses, reflection, pattern captures,
dynamic calls, and caller-derived methods. It would still require a custom interpreter-like proof,
retain Python objects in one address space, and remain difficult for a reviewer to distinguish from
the failed AST approach. The complexity is not justified for one bounded formal operation.

### 5.3 Exact source identity without a process boundary — rejected

Trusting only a reviewed source hash would be simpler, but it would leave caller-controlled Python
objects in the same runtime and weaken the approved confused-authority protection. Source identity
is necessary, but not sufficient by itself.

## 6. Exact process architecture

A formal invocation contains exactly two processes:

```text
trusted CLI/controller process
  -> supervisor execute_authorized_formal_development(request)
       -> one fresh verified formal_worker.py process
            -> one fit ledger
            -> one replay session
            -> one private container
            -> one terminal public seal
       <- one canonical sanitized response
```

The supervisor:

- owns the public callable and fixed process-launch policy;
- validates the request, repository, freeze, source inventory, authorization bytes, and textual
  output boundaries without opening the archive;
- constructs and hashes one canonical worker request;
- launches the worker exactly once;
- accepts at most one bounded canonical response;
- observes timeout and process exit;
- reads no UCI row, H1 row, H2 row, model, prediction, label, or private-container payload; and
- returns `PASS` only after zero exit, exact response validation, and public terminal-seal identity
  validation.

The worker:

- starts in a fresh interpreter with no caller Python objects;
- revalidates the repository, freeze, source inventory, authorization, archive identity, and both
  output destinations independently;
- acquires and retains authoritative Windows publication handles;
- consumes authorization before importing or calling natural loaders or estimator builders;
- owns every natural row, estimator, fit, prediction, private document, and private byte;
- executes exactly one state machine, ledger, and replay session;
- publishes the private container and terminal public seal using the retained no-clobber boundary;
- emits one sanitized canonical response; and
- exits without spawning a child process.

No worker pool, reuse, reconnect, resume, or second attempt exists.

## 7. Module and callable boundary

### 7.1 Supervisor surface

`src/mdcp/temporal/run_evidence.py` retains:

```text
FormalDevelopmentRequest
FormalDevelopmentOutcome
FormalDevelopmentSeal
FormalRunConsumptionMarker
FormalSealCheck
execute_authorized_formal_development
verify_formal_development_seal
```

`execute_authorized_formal_development` becomes a supervisor. It may validate trusted bytes and
launch the fixed worker, but it cannot import or call the UCI loader, materialize development rows,
construct an estimator, fit, replay, encode natural private evidence, or publish a natural leaf.

`src/mdcp/temporal/cli.py` continues to expose exactly `build_parser` and `main`. The CLI dispatches
the supervisor once and emits only its closed sanitized result.

### 7.2 Protocol surface

`src/mdcp/temporal/formal_worker_protocol.py` contains only frozen request/response models,
canonicalization, fixed limits, fixed reason codes, and digest validation. It performs no file,
environment, clock, network, process, dataset, model, or publication operation.

### 7.3 Worker surface

`src/mdcp/temporal/formal_worker.py` is both the exact verified process target and the owner of one
process entry function named `main`.

`main`:

- accepts no Python argument;
- reads only `sys.stdin.buffer` and writes only `sys.stdout.buffer`;
- fails before authorization or data access unless the module is executing as `__main__` under an
  isolated interpreter;
- derives the repository and source roots from its own canonical script path, and rejects a request
  whose `repository_root` differs;
- never accepts a stream, callback, backend, module, registry, class, or callable parameter; and
- is never imported by the supervisor.

Directly importing the module does not execute formal work. Executing the reviewed module directly
with the exact isolated launch profile is not an authorization bypass: the worker still requires
the canonical request, exact frozen source, valid unconsumed authorization, safe destinations, and
all runtime gates.

### 7.4 Pure development state machine

`runner.py` becomes a pure deterministic state machine. It issues the next exact
`phase/trial/fold` fit request and accepts an exact typed fold result. It cannot load a path, import a
model family, consume authorization, publish bytes, or invoke a caller-supplied callable.

The worker owns the loop that materializes and fits each issued request. Synthetic tests feed
deterministic typed results into the same state machine. This preserves one tested ranking/replay
algorithm without a production callback interface or AST extraction of a bootstrap factory.

## 8. Closed worker request protocol

The supervisor sends exactly one RFC 8785 document with no BOM, newline, trailing byte, duplicate
key, non-finite number, or extra field. Maximum physical size is `65,536` bytes.

The exact top-level fields are:

```text
schema_version = "mdcp.formal-worker-request.v1"
canonicalization_version = "RFC8785"
expected_freeze_head
repository_root
search_receipt_path
evidence_index_path
authorization_path
consumption_root
archive_path
private_container_path
search_receipt_sha256
evidence_index_sha256
authorization_sha256
source_inventory_sha256
repository_inventory_sha256
formal_worker_inventory_sha256
launch_profile_sha256
```

All paths are absolute canonical Windows strings used only in private process IPC. They are never
written into public evidence, stdout outside the canonical response, an exception, or a log. The
terminal public path is absent and remains derived as `<private filename>.public.json`.

The request contains no row, label, prediction, model, private document, authorization bytes,
callable, pickle, code string, import name, environment value, timestamp, random nonce, opaque
extension, or caller-supplied evidence identity.

The SHA-256 of the complete canonical request bytes is `worker_request_sha256`. That digest is not
inside the request and therefore creates no self-hash cycle. The worker independently rereads every
referenced trusted file except the archive content and rejects any digest mismatch before
authorization consumption. Before consumption it validates only the archive's absolute canonical
path, regular non-link type, and exact frozen byte size. It opens and hashes archive content only
after the marker is durable.

## 9. Fixed Windows launch profile

The launch profile is a canonical source constant whose digest is bound into the request and
terminal seal. Its semantic values are exactly:

```text
platform                     windows
executable                    absolute current Python 3.12 interpreter
target                        absolute verified src/mdcp/temporal/formal_worker.py
arguments                     -I -B -S ABSOLUTE_VERIFIED_FORMAL_WORKER_SCRIPT
shell                         false
cwd                           verified repository root
close_fds                     true
stdin                         pipe
stdout                        pipe
stderr                        devnull
environment keys              SYSTEMROOT, WINDIR
site processing               false
project source bootstrap      script-derived repository_root/src
dependency bootstrap          interpreter-derived Lib/site-packages, direct sys.path only
response limit                65,536 bytes
wall timeout                  21,600 seconds
post-termination wait         30 seconds
automatic retry               false
worker launches per request   1
worker child processes        0
```

The supervisor verifies that the executable and target script are absolute regular non-link files,
that the target has the reviewed worker digest, and that the runtime is Python 3.12 before process
creation. `-I` disables the current directory, user site, and Python environment variables as
import-control inputs. `-B` prevents bytecode-file mutation. `-S` prevents `site`, `.pth`,
`sitecustomize`, and `usercustomize` startup execution.

The worker's standard-library-only bootstrap derives `repository_root/src` from its own verified
script path. It derives the one dependency directory as `Lib/site-packages` beneath the virtual
environment root containing the verified executable, validates both derived directories as
canonical existing non-reparse directories, and inserts them directly into `sys.path`; it never
calls `site.addsitedir` and never evaluates a `.pth` file. It then imports only the reviewed project
protocol and its lock-governed dependencies before consumption. Dataset and estimator modules stay
unimported until the durable marker. The exact dependency lock remains part of the 47-path source
identity. This controls Python startup hooks but does not claim that a malicious same-user cannot
replace trusted interpreter or installed dependency bytes; that remains outside Section 4.2's host
trust boundary. The minimal Windows environment is private and never enters evidence.

No shell command, PATH lookup, caller argument, caller environment, inherited nonstandard handle,
site startup hook, `.pth` evaluation, `PYTHONPATH`, user site, profile, worker-selected executable,
worker-selected script, or worker-selected module is allowed.

This profile does not claim an OS network sandbox or protection from a modified interpreter. Those
remain outside the same-user trusted-host boundary. Exact source inventory, dependency lock,
runtime guards, and static forbidden-import checks remain mandatory.

The supervisor never uses an unbounded `communicate`-style output collector. Its transport writes
at most `65,536` request bytes, closes stdin, drains at most `65,537` stdout bytes into a fixed
buffer, and enforces one monotonic formal deadline across input, execution, and output. The
`65,537`th byte is an overflow signal, not accepted payload; the supervisor requests termination
once, retains no more bytes, and uses only the separate fixed cleanup interval to wait for process
death. Transport-control threads, if required by the Windows implementation, carry only fixed byte
buffers and process handles and cannot execute a second formal operation.

## 10. Authorization and execution order

The exact worker lifecycle is:

1. verify isolated, no-site, no-bytecode `__main__` execution, fixed runtime version, exact script
   identity, script-derived repository/source roots, and interpreter-derived dependency root;
2. read at most `65,536` request bytes and require EOF;
3. parse, validate, recanonicalize, and hash the request;
4. verify `launch_profile_sha256` and `formal_worker_inventory_sha256`;
5. verify repository root, expected freeze commit, clean source, search receipt, evidence index,
   source inventory, and repository inventory;
6. reread and validate canonical authorization bytes, then require the exact parent-observed
   authorization digest and frozen bindings;
7. verify the archive path is absolute and identifies an approved-size regular non-link file,
   without opening its content;
8. verify `consumption_root`, private destination, and derived terminal destination are existing,
   external, distinct, absent, non-link, non-reparse, and handle-relative safe;
9. acquire and retain both publication boundaries;
10. exclusively create, write, flush, identity-check, and checked-close the one consumption marker;
11. only after the canonical marker exists, open and hash the complete archive, require the frozen
    SHA-256, then import the bounded development loader and approved estimator builders from the
    already fixed source/dependency roots;
12. parse only the first `13,003` `hour.csv` rows and prove `8,645` train plus `4,358` observed H1;
13. execute exactly 80 selection fits and either zero or four replay fits through one ledger and one
    replay session;
14. formalize the exact five private documents and closed public aggregate;
15. checkpoint `PRE_SEAL`, encode and publish the private container;
16. checkpoint `EXIT`, construct and publish the terminal public seal;
17. checked-close every retained handle;
18. emit one canonical sanitized response and flush stdout; and
19. exit `0`.

No loader import or call, archive-content read, row parse, estimator construction, fit,
private-byte construction, or private/terminal output mutation may occur before step 10 succeeds.

## 11. Closed worker response and supervisor acceptance

The worker writes exactly one canonical RFC 8785 response with maximum physical size `65,536`
bytes. It repeats the closed `FormalDevelopmentOutcome` fields and adds exactly:

```text
schema_version = "mdcp.formal-worker-response.v1"
canonicalization_version = "RFC8785"
worker_request_sha256
formal_worker_inventory_sha256
launch_profile_sha256
```

Its worker-emitted `fit_count` is always an exact integer in the existing `0..84` matrix. It
contains no path, row, label, prediction, timestamp, exception, traceback, OS status,
environment value, command line, interpreter path, private payload, or arbitrary text.

The supervisor returns live `PASS` only when all of these hold:

- exactly one process was created;
- no timeout or response-limit event occurred;
- process exit code is exactly `0`;
- stdout is exactly one canonical response and EOF;
- request, worker-inventory, and launch-profile digests equal the supervisor values;
- the response field matrix is exact;
- the returned terminal-seal digest matches the physical public leaf; and
- the sanitized public seal binds the same request, source, authorization, marker, private identity,
  repository inventory, fit count, H2 state, and development result.

A successful worker operation may still contain nested
`NO_ELIGIBLE_CANDIDATE/FAIL` or `UNKNOWN/NO_ELIGIBLE_CANDIDATE/UNKNOWN`; as before, operation `PASS`
means lifecycle and seal completion, not candidate qualification.

If the supervisor cannot authenticate a complete response, it exposes no private identity,
terminal digest, repository inventory, or asserted fit count. `FormalDevelopmentOutcome.fit_count`
therefore becomes `int | None`; `None` means that the process boundary prevented an authoritative
ledger count from being recovered. A valid worker response retains the exact known count.

## 12. Failure, timeout, and kill semantics

### 12.1 Before process creation

Request, repository, freeze, source, authorization, path, interpreter, or launch-profile failures
remain deterministic `FAIL` with no process, marker, data access, output, or retry. A `CreateProcess`
failure that returns no process handle is `FAIL/FORMAL_WORKER_LAUNCH_FAILED`.

### 12.2 After process creation

Once process creation succeeds, any of the following is terminal
`UNKNOWN/FORMAL_WORKER_PROCESS_UNKNOWN`:

- timeout;
- response exceeds `65,536` bytes;
- stdout read or EOF uncertainty;
- missing, malformed, noncanonical, extra, duplicate, or trailing response bytes;
- nonzero or unobservable exit;
- response/request/source/profile identity mismatch;
- a `PASS` response inconsistent with the public terminal leaf; or
- inability to terminate and wait for the child after a transport failure.

The supervisor requests termination once, waits once for exactly `30` seconds, and
never starts another worker. It does not infer that authorization is reusable from the absence of a
response or marker. It never deletes, overwrites, repairs, or republishes an output by path.

### 12.3 Controlled worker outcomes

When the worker emits a valid canonical response and exits `0`, the existing phase distinctions
remain authoritative:

- pre-consumption denial is `FAIL`;
- marker uncertainty is `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN`;
- post-marker execution failure is `UNKNOWN/FORMAL_RUN_EXECUTION_UNKNOWN`;
- private/seal/publication failure is `UNKNOWN/FORMAL_RUN_SEAL_UNKNOWN`; and
- complete publication is operation `PASS`.

There is no automatic retry, worker reuse, resume, fallback command, threshold substitution, second
authorization, or cleanup-based recovery.

## 13. Evidence and identity chain

The corrected trust chain is:

```text
search source commit
  -> exact 47-path source inventory
  -> search freeze commit and receipt/index
  -> owner authorization
  -> canonical worker request digest
  -> authorization consumption marker
  -> canonical private-container identity
  -> terminal public seal digest
  -> sanitized worker response accepted after zero process exit
```

`FormalDevelopmentSeal` adds these nonzero fields:

```text
worker_request_sha256
formal_worker_inventory_sha256
launch_profile_sha256
evidence_index_sha256
```

The existing authorization, marker, search, protocol, archive, source inventory, repository
inventory, private identity, exit observation, selection, result, and H2 fields remain.

The exact `formal_worker_inventory_sha256` is the SHA-256 of the RFC 8785 canonicalization of an
object with `schema_version="mdcp.formal-worker-source-inventory.v1"` and an `entries` array. Each
entry has exactly `logical_path` and `sha256`; `sha256` is computed from that path's complete
physical bytes. The array contains exactly these paths in this ASCII order:

```text
schemas/v2/formal-worker-request.schema.json
schemas/v2/formal-worker-response.schema.json
src/mdcp/temporal/formal_worker.py
src/mdcp/temporal/formal_worker_protocol.py
```

The four entries are ASCII ordered and exact, with no missing, extra, duplicate, alias, or
caller-selected path. All four are also members of the complete 47-path `SEARCH_SOURCE_PATHS`
inventory. `source_inventory_sha256` is the independently recomputed 47-entry inventory digest;
`evidence_index_sha256` is the physical digest of the canonical index that carries it.
This separates the two meanings explicitly. The rejected implementation's use of a field named
`source_inventory_sha256` for the physical index digest is not accepted by the corrected seal.

`launch_profile_sha256` is the SHA-256 of an RFC 8785 object containing every semantic value in
Section 9, using symbolic values such as `ABSOLUTE_CURRENT_PYTHON_3_12` rather than a private host
path. The implementation constant and both schemas reproduce that same object exactly.

No identity contains itself:

- the request digest is absent from the request;
- the terminal-seal digest is absent from the terminal seal;
- the source inventory excludes the generated receipt/index leaves;
- the response digest is not asserted by the response; and
- external acceptance still requires the independently retained physical terminal-seal digest.

Process death after terminal publication but before the supervisor authenticates and retains that
digest remains `UNKNOWN`. Recovery does not promote structurally valid bytes without the external
expected terminal digest.

## 14. Publication and recovery

The worker retains the approved Windows publication implementation:

- existing external parent directories;
- textual and handle-relative repository exclusion;
- no symlink, junction, reparse, short-name, ancestor, same-leaf, existing-leaf, or substitution
  ambiguity;
- private publication first and terminal public seal last;
- write, file flush, identity recheck, ancestor recheck, and checked close;
- no-clobber behavior under races; and
- no path-based deletion or overwrite after uncertainty.

The public terminal sibling remains `<private filename>.public.json`. No third evidence leaf,
process log, IPC transcript, temporary public receipt, or raw worker stderr is introduced.

The read-only verifier remains callable outside the worker and continues to validate the complete
authorization-marker-private-terminal chain, including the five-file semantic relationships and
external expected terminal digest. It additionally verifies the request, worker-inventory, and
launch-profile digests recorded in the terminal seal.

## 15. H2, data, model, and resource boundaries

- The supervisor never opens the dataset archive.
- The worker hashes the complete approved archive before parsing but parses only the first `13,003`
  rows of `hour.csv`.
- `day.csv`, row `13,004` and later, `open_h2`, `DatasetPartitions`, `split_rows`, and the legacy full
  `load_uci_archive` remain forbidden.
- H2 remains `SEALED_NOT_LOADED`, loaded rows `0` in request validation, runtime state, response,
  private evidence, public seal, recovery, and completion evidence.
- The forbidden feature set remains `yr`, `dteday`, `instant`, `casual`, `registered`, and `cnt` as
  model input.
- Estimator execution remains CPU-only, one estimator thread, with no GPU, Docker, network, paid API,
  or external service.
- Runtime time, memory, repository, fit-budget, and H2 guards execute inside the worker so their
  observations apply to the process that owns rows and models.

Corrective implementation tests use deterministic synthetic data and denial hooks only. They do
not read UCI/H1/H2 rows, create a real authorization, or execute a model. P2 is the first authorized
natural worker run.

## 16. Firewall redesign

The firewall no longer claims a sound whole-Python callback or noninterference proof. The
uncommitted Task 5 cross-language taint expansion is retired.

The corrected finite policy verifies:

- the supervisor does not import or call dataset, estimator, fit, replay, natural encoder, or
  natural publisher capabilities;
- the supervisor launches only the fixed verified script and never accepts a callable or command
  argument;
- worker request/response models contain only closed JSON-compatible primitive values;
- no pickle, marshal, eval, exec, dynamic import, reflection, code object, callback field, opaque
  extension, or arbitrary module name crosses IPC;
- direct import and call of `formal_worker.main` fails before authorization or data access;
- the worker has no subprocess, shell, network, GPU, environment-recovery, H2, legacy full-loader,
  or alternate publication path;
- the pure state machine has no file, process, data-loader, model-builder, or publication import;
- source inventory contains every worker-bound production and schema path exactly once; and
- public responses and evidence pass the existing credential/private-path/exception scanner.

Static analysis remains defense in depth over a deliberately finite import and protocol contract.
It is not treated as proof that arbitrary Python syntax cannot encode a callback.

## 17. Exact implementation file boundary

The future implementation plan may modify only these existing 19 paths:

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

It may create only these six paths:

```text
src/mdcp/temporal/formal_worker.py
src/mdcp/temporal/formal_worker_protocol.py
schemas/v2/formal-worker-request.schema.json
schemas/v2/formal-worker-response.schema.json
tests/unit/temporal/test_formal_worker_protocol.py
tests/integration/temporal/test_formal_worker_process.py
```

The exact implementation allowlist is therefore 25 paths. The two evidence paths remain forbidden
until the terminal tombstone/refreeze sequence. Any dependency, `pyproject.toml`, `uv.lock`,
`.gitattributes`, config, fixture, serving identity, preserved evidence, additional module, schema,
or test path requires another owner design stop.

## 18. Exact 47-path source inventory migration

The previously approved corrected inventory would have remained 43 paths through its documented
three-for-three normative substitution. This amendment preserves that substitution, then makes
these exact changes.

Replace:

```text
docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-final-review-corrective.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md
```

with:

```text
docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-dedicated-formal-worker-corrective.md
docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md
```

Then add:

```text
schemas/v2/formal-worker-request.schema.json
schemas/v2/formal-worker-response.schema.json
src/mdcp/temporal/formal_worker.py
src/mdcp/temporal/formal_worker_protocol.py
```

The result is exactly 47 canonically ordered source paths. The future plan must use the literal
dated filename above. Historical documents remain in Git but are not controlling
execution-identity members.

The new request/response test files are implementation tests, not execution source, and therefore
are outside `SEARCH_SOURCE_PATHS`. Generated public receipt/index leaves also remain outside the
source inventory.

All 47 paths must reproduce byte-for-byte from a source archive without `.git` under
`core.autocrlf=true`, `false`, and `input`, using only the reviewed external temporary attributes
profile. No tracked attributes or private absolute path may be required.

## 19. Migration and rejected diagnostic preservation

The future corrective plan must begin with a dedicated diagnostic-preservation task:

1. verify the three uncommitted hashes in Section 2;
2. copy those exact three bytes and a relative-path SHA-256 inventory to a new private external
   diagnostic root;
3. independently verify source/destination equivalence;
4. record that the material is rejected review evidence and not public or normative;
5. use `apply_patch`, never reset/restore/checkout/stash, to retire only the rejected uncommitted
   diagnostic hunks; and
6. preserve all four committed Task 1-4 changes append-only.

The design and plan commits may be created while those three exact working-copy diagnostics remain
present, provided only the docs path is staged. No other dirty path is allowed.

After diagnostic retirement, implementation proceeds in this order:

1. closed worker protocol and schemas;
2. pure state-machine conversion;
3. fixed supervisor launch and transport boundary;
4. worker-owned authorization, data, execution, and publication lifecycle;
5. failure, timeout, response, recovery, and public-evidence semantics;
6. finite firewall and process-boundary proofs;
7. exact 47-path identity and no-`.git` archive proof;
8. full committed-tree completion and independent review;
9. rejected-freeze `D/D` tombstone; and
10. one no-clobber `A/A` refreeze and new external custody identity.

Each source-changing task begins with a real RED, reaches targeted and full GREEN, receives an
independent Critical `0`, Important `0` review, and ends in a separate append-only commit. No task
may cross the next gate or combine the tombstone and refreeze commits.

## 20. Required RED -> GREEN proofs

The future plan must include at least these negative proofs:

### Protocol

- missing, extra, duplicate, reordered-noncanonical, invalid-type, non-finite, oversized, BOM,
  newline, trailing, invalid UTF-8, invalid path, invalid digest, self-hash, and unknown-version
  request/response mutations;
- callback-shaped strings, pickle bytes, code fields, module names, import instructions, and nested
  opaque objects rejected by schema;
- request identity recomputation and worker reread disagreement rejected before consumption.

### Process launch

- shell, PATH lookup, relative executable, changed script, changed flags, omitted `-S`, changed cwd,
  extra environment key, inherited handle, second worker, and caller-selected argument rejected;
- `.pth`, `sitecustomize`, `usercustomize`, caller-selected source root, caller-selected dependency
  root, and script/request repository disagreement rejected;
- imported `formal_worker.main` fails before authorization or data access;
- timeout, oversized stdout, partial stdout, extra stdout, nonzero exit, absent EOF, invalid response,
  and response identity mismatch return terminal `UNKNOWN` after process creation;
- process-creation failure produces deterministic pre-consumption `FAIL`;
- no automatic retry occurs under any failure.

### Formal lifecycle

- authorization, marker, destination, loader, model, fit, ledger, replay, publication, and close
  ordering;
- exactly 80 selection fits, zero or four replay fits, at most 84 Wave 3 fits, and one ledger/session;
- 81st selection, fifth replay, duplicate fit, reordered result, wrong trial/fold, and rank-two
  fallback rejected;
- loader/model denial hooks prove no access before successful marker consumption;
- legacy loader, full split, H2, row 13,004, day.csv, network, environment, entropy, subprocess,
  Docker, GPU, and dynamic import paths rejected;
- worker runtime guards measure the worker process rather than the supervisor.

### Evidence and recovery

- worker request, inventory, and launch-profile mutations rejected by terminal verification;
- all existing external-path, reparse, no-clobber, checked-close, partial-publication, five-file
  semantic mutation, and externally anchored seal tests retained;
- worker crash after marker, after private publication, after terminal publication, and before
  stdout acceptance never returns live `PASS`;
- public evidence and response scans disclose no path, command, environment, exception, credential,
  row, label, prediction, or timestamp.

### Identity and topology

- exact 47-path inventory with missing, extra, duplicate, wrong mode, wrong EOL, copied index,
  `.git`, and zero identity cases rejected;
- source archive reproduces under all three autocrlf modes;
- rejected receipt/index/custody hashes remain immutable;
- tombstone is exactly `D/D`, refreeze is exactly `A/A`, and the new freeze has the exact source
  parent and new custody identity.

## 21. Completion gates

Before creating the corrected source commit or touching the rejected evidence leaves, the committed
tree must pass:

- every task-targeted RED/GREEN suite;
- full CPU pytest regression;
- protocol, process, temporal, contract, security, behavioral H2, publication, recovery,
  source-archive, and identity suites;
- exact supervisor and worker callable/import audit;
- exact 47-path inventory and external custody proof;
- no-`.git` archive proof under all three autocrlf modes;
- Ruff check and exact changed-Python format check;
- `uv lock --check` and `git diff --check`;
- credential, private-path, public-evidence, exception, IPC, and publication-boundary scans;
- v0.1/v0.2 serving-identity and protected-byte recomputation;
- remote count `0`, no HEAD tag, H2 `SEALED_NOT_LOADED`, and H2 loaded rows `0`; and
- fresh independent whole-range review with Critical `0`, Important `0`.

The final whole-range review must examine diagnostic retirement, each process-boundary commit, the
`D/D` tombstone, and the `A/A` refreeze separately. A net diff cannot conceal either evidence
transition. Passing test counts never override an unresolved Critical or Important finding.

## 22. Stop and rollback rules

Stop without implementation expansion if:

- any path outside the exact 25-path allowlist is required;
- the 47-path source inventory cannot be exact and acyclic;
- the worker requires a callback, pickle, code string, shell, caller command, caller environment,
  second process, worker pool, restart, or retry;
- the supervisor must open archive rows, model state, or private payload;
- data/model/output access can precede durable authorization consumption;
- output destinations cannot be proven external before consumption;
- process failure can return an authenticated partial identity as `PASS`;
- protected source, dependency, protocol, threshold, fit budget, serving identity, historical
  evidence, rejected custody, or H2 state drifts;
- source archive reproduction requires tracked attribute mutation or a private path;
- any test requires real UCI/H1/H2 rows, real authorization, model execution, Docker, GPU, network,
  remote, P2, or Wave 4;
- any Critical or Important finding remains; or
- one architectural blocker survives three separately evidenced hypotheses.

There is no automated rollback. Before the evidence tombstone, failure preserves the rejected
current-tree freeze and all append-only commits. After the tombstone, failure stops at the clean
P2-forbidden no-evidence source commit. After a refreeze failure, both the tombstone and failed
freeze remain rejected history. Restoring bytes, attempting a second freeze, or changing topology
requires new owner authorization.

## 23. Terminal states

Successful corrective implementation, which is not authorized by this document, stops at:

```text
DEDICATED_FORMAL_WORKER_PASS /
SEARCH_FREEZE_PASS /
P2_FORMAL_RUN_AUTHORIZATION_REQUIRED /
H2_SEALED_NOT_LOADED
```

Any implementation or review failure stops at:

```text
DEDICATED_FORMAL_WORKER_BLOCKED /
P2_FORBIDDEN /
H2_SEALED_NOT_LOADED
```

Neither state creates or consumes a real P2 authorization. Only a later explicit owner action may
authorize the natural formal run.

## 24. Design self-review checklist

- The design contains no optional security gate or unresolved architecture alternative.
- The failed whole-language AST claim is removed rather than renamed.
- The selected process boundary is described honestly as object/memory isolation, not a hostile
  same-user sandbox or network sandbox.
- Supervisor and worker responsibilities are disjoint and independently testable.
- No executable Python value crosses IPC.
- Request, response, source, launch, authorization, publication, and recovery identities are
  closed and acyclic.
- Authorization consumption precedes every loader, archive-content, row, model, fit, private, and
  terminal-output operation; the consumption marker itself is the sole authorized mutation at that
  boundary.
- Timeout, crash, output-limit, exit, and malformed-response behavior is deterministic and never
  retries.
- The exact private-container, public-seal, no-clobber, checked-close, semantic-recovery, H2, and fit
  contracts remain unchanged except for explicit worker identity fields.
- The exact allowlist is 25 paths and the execution source inventory is exactly 47 paths.
- Current uncommitted diagnostics have exact identities and a non-Git preservation/retirement path.
- Rejected freeze bytes and custody remain immutable and recoverable.
- No P2, data, model, Docker, GPU, network, remote, publication, or Wave 4 action is authorized.
- The written-spec review gate remains mandatory before plan creation.
