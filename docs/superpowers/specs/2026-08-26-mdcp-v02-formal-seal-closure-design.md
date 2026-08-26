# MDCP v0.2 Formal Seal Closure Design Amendment

**Status:** Owner-approved written specification
**Date:** 2026-08-26
**Repository:** `model-delivery-control-plane`
**Applies after:** `3c0fcddd7fded5f62d3f731864ff423f815fff16`
**H2 state:** `SEALED_NOT_LOADED`, loaded rows `0`

## 1. Purpose

This amendment replaces the failed caller-visible formal-permit design with one closure-owned
formal operation. It closes the reviewed race in which a caller holding a valid permit could wait
for the permit to enter `SEALING`, invoke a named natural-capable container builder with an
attacker-supplied bundle, and publish those bytes before the trusted executor completed its seal.

The correction remains design-only until this document receives owner written-spec approval and a
separate corrective implementation plan is written and reviewed. It does not authorize a formal
development run, P2, UCI/H1/H2 row access, model execution, Docker, GPU, network, external
publication, or Wave 4.

## 2. Evidence and root cause

Task 4 stopped without a commit after four independent reviews. The last review was Critical `1`,
Important `0`, Minor `1`. The preserved private diagnostic is not repository evidence and remains
outside Git.

Three successive implementation hypotheses failed for the same authority boundary:

1. a caller-visible permit plus a named claim function and natural writer allowed direct natural
   publication;
2. removing those names left an alternate permit-domain factory and a generic natural builder plus
   raw publisher composition; and
3. deleting the factory and gating the builder on a `SEALING` state left a deterministic race while
   the caller still held the permit.

The root cause is architectural: a caller-visible object cannot both authorize execution and become
the observable capability for natural encoding or publication. Adding another state, lock, token,
or renamed underscore helper preserves that confused authority and creates another composition
surface.

## 3. Locked decisions

### 3.1 One named natural operation

Production exposes exactly one natural-development mutation operation from
`src/mdcp/temporal/run_evidence.py`:

```python
def execute_authorized_formal_development(
    request: FormalDevelopmentRequest,
) -> FormalDevelopmentOutcome:
    ...
```

There is no caller-visible `FormalRunPermit`, permit factory, claim function, activation function,
seal token, natural builder, natural writer, natural publisher callback, or separately callable
durable-consumption operation.

`FormalDevelopmentRequest` is an exact frozen value object containing only paths and the expected
freeze commit:

```python
@dataclass(frozen=True, slots=True)
class FormalDevelopmentRequest:
    repository_root: Path
    expected_freeze_head: str
    search_receipt_path: Path
    evidence_index_path: Path
    authorization_path: Path
    consumption_root: Path
    archive_path: Path
    private_container_path: Path
```

The request contains path locators but no caller-supplied archive bytes or digest, protocol digest,
receipt digest, source-inventory digest, private identity, public identity, or evidence digest.
Production recomputes every digest from checked bytes and the verified freeze documents.

`FormalDevelopmentOutcome` is this exact frozen result:

```python
@dataclass(frozen=True, slots=True)
class FormalDevelopmentOutcome:
    verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    private_identity: PrivateBundleIdentity | None
    seal_record_sha256: str | None
    repository_inventory_sha256: str | None
    authorization_sha256: str
    consumption_marker_sha256: str | None
    fit_count: int
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
```

Only `PASS` contains a private identity and terminal seal-record digest. `FAIL` is restricted to
pre-consumption denial and has no artifact identity. `UNKNOWN` must not present a partial identity
as successful. The result contains no path, raw row, label, prediction, timestamp, exception,
environment, authorization content, or opaque capability. The all-zero SHA-256 value below means
that no structurally valid canonical authorization was accepted; it is never a valid identity.

The exact reason-code sets are closed:

```text
PASS:    ()
FAIL:    FORMAL_RUN_REQUEST_INVALID
         SEARCH_FREEZE_INVALID
         FORMAL_RUN_AUTHORIZATION_INVALID
         FORMAL_RUN_AUTHORIZATION_MISMATCH
         FORMAL_RUN_REPOSITORY_INVALID
         FORMAL_RUN_CONSUMPTION_ROOT_INVALID
         FORMAL_RUN_DESTINATION_INVALID
         FORMAL_RUN_AUTHORIZATION_CONSUMED
         FORMAL_RUN_CONSUMPTION_FAILED
         PUBLICATION_UNSUPPORTED
UNKNOWN: FORMAL_RUN_CONSUMPTION_UNKNOWN
         FORMAL_RUN_EXECUTION_UNKNOWN
         FORMAL_RUN_SEAL_UNKNOWN
```

`FAIL` and `UNKNOWN` contain exactly one reason code. Validation order is request type, platform,
repository/freeze/receipt, canonical authorization parse and binding, then consumption-root and
paired-destination validation. `authorization_sha256` is the digest of canonical authorization
bytes only after structural parsing succeeds; every earlier result uses `"0" * 64`.

Outcome population is closed and field-by-field exact. `A` means the nonzero digest of the
structurally valid canonical authorization; `M` means the nonzero digest of the canonical marker
successfully established by this invocation. Every `None` below is literal `None`:

| Verdict / exact reason | authorization | marker | private | seal | repository inventory | fit count |
| --- | --- | --- | --- | --- | --- | ---: |
| `FAIL/FORMAL_RUN_REQUEST_INVALID` | zero | `None` | `None` | `None` | `None` | `0` |
| `FAIL/PUBLICATION_UNSUPPORTED` | zero | `None` | `None` | `None` | `None` | `0` |
| `FAIL/FORMAL_RUN_REPOSITORY_INVALID` | zero | `None` | `None` | `None` | `None` | `0` |
| `FAIL/SEARCH_FREEZE_INVALID` | zero | `None` | `None` | `None` | `None` | `0` |
| `FAIL/FORMAL_RUN_AUTHORIZATION_INVALID` | zero | `None` | `None` | `None` | `None` | `0` |
| `FAIL/FORMAL_RUN_AUTHORIZATION_MISMATCH` | `A` | `None` | `None` | `None` | `None` | `0` |
| `FAIL/FORMAL_RUN_CONSUMPTION_ROOT_INVALID` | `A` | `None` | `None` | `None` | `None` | `0` |
| `FAIL/FORMAL_RUN_DESTINATION_INVALID` | `A` | `None` | `None` | `None` | `None` | `0` |
| `FAIL/FORMAL_RUN_AUTHORIZATION_CONSUMED` | `A` | `None` | `None` | `None` | `None` | `0` |
| `FAIL/FORMAL_RUN_CONSUMPTION_FAILED` | `A` | `None` | `None` | `None` | `None` | `0` |
| `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN` | `A` | `None` | `None` | `None` | `None` | `0` |
| `UNKNOWN/FORMAL_RUN_EXECUTION_UNKNOWN` | `A` | `M` | `None` | `None` | `None` | `0..84` |
| `UNKNOWN/FORMAL_RUN_SEAL_UNKNOWN` | `A` | `M` | `None` | `None` | `None` | `80` or `84` |
| `PASS/()` | `A` | `M` | verified identity | nonzero digest | nonzero `R` | `80` or `84` |

`fit_count` is the number of ledger-recorded started fits. A failed individual fit is counted once
its exact ledger slot has been reserved. No non-`PASS` outcome exposes a partial private or seal
identity, repository inventory, or seal digest, and an uncertain marker never receives `M`.

The operation/result matrix is exact:

| Operation verdict | `development_result.status` | `selection_status` | Fit count | Accepted terminal seal |
| --- | --- | --- | ---: | --- |
| `PASS` | `PASS` | `PASS` | `84` | yes |
| `PASS` | `FAIL` | `NO_ELIGIBLE_CANDIDATE` | `80` | yes |
| `PASS` | `UNKNOWN` | `UNKNOWN/NO_ELIGIBLE_CANDIDATE` before replay | `80` | yes |
| `PASS` | `UNKNOWN` | `UNKNOWN/NO_ELIGIBLE_CANDIDATE` after replay failure | `84` | yes |
| `FAIL` | absent | absent | `0` | no |
| `UNKNOWN` | absent from acceptance | absent from acceptance | `0..84` | no |

Operation `PASS` means the authorized lifecycle and terminal seal completed; it does not claim that
a candidate qualified. A naturally sealed `NO_ELIGIBLE_CANDIDATE` result is therefore an operation
`PASS` with a nested public `FAIL`, not an infrastructure failure.

### 3.2 Consume and execute are indivisible

The single operation performs the following ordered lifecycle without returning control or an
intermediate capability:

1. validate exact request types and the expected freeze commit;
2. verify the canonical search receipt and evidence index against the current clean repository;
3. derive the exact receipt, archive, protocol, source-inventory, and freeze identities;
4. validate canonical owner authorization bytes against those derived identities;
5. validate both derived output destinations and retain their trusted Windows ancestor handles;
6. exclusively create, write, and file-flush the one consumption marker;
7. construct production runtime guards internally;
8. load only the bounded development prefix;
9. execute the one ledger and one replay session within the frozen fit budget;
10. formalize the exact typed five-file natural bundle and closed aggregate result;
11. build the private bytes and `PrivateBundleIdentity` inside the operation's lexical closure;
12. checkpoint `PRE_SEAL` exactly once;
13. publish the private container no-clobber;
14. checkpoint `EXIT` exactly once and derive its sanitized observation digest;
15. build the terminal public seal record from the authorization, marker, private, result, and
    `EXIT` identities;
16. publish the deterministic public sibling no-clobber as the final acceptance mutation; and
17. return the closed outcome.

The authorization marker handle is acquired before loader import/call, model construction, fit, or
output creation. Every failure after that acquisition is terminal `UNKNOWN`; neither authorization
nor destinations may be reused.

Reason boundaries are exact: uncertainty while establishing the marker is
`FORMAL_RUN_CONSUMPTION_UNKNOWN`; after a canonical marker exists and before an exact 80/84-fit
natural result has been formalized it is `FORMAL_RUN_EXECUTION_UNKNOWN`; from private-byte
construction, `PRE_SEAL`, either publication, `EXIT`, terminal-record construction, or checked
public close it is `FORMAL_RUN_SEAL_UNKNOWN`. These phases do not overlap and the first failing phase
wins.

### 3.3 No named natural encoder or writer

The module-level private-container API remains synthetic-only. Its public function is still
`write_synthetic_bundle_no_clobber`, and it accepts only the exact `synthetic_test` runtime type.
The module-level canonical builder fails closed for `natural_development` under every argument,
including a forged object, prior permit-shaped object, callback, token, or boolean override.

Natural encoding and paired publication are lexical locals of the single formal operation. They are
not assigned to a module attribute, returned from a factory, stored on a caller-visible object,
registered in a mutable table, or accepted as callbacks. Initialization factories used to bind
low-level primitives are consumed exactly once during module initialization and their names are
deleted before the module becomes usable.

The raw Windows byte-publication function is also lexical-closure state. After module
initialization, no module attribute, alias, default argument, registry value, class attribute, or
factory return exposes it. `write_synthetic_bundle_no_clobber` captures a synthetic-only wrapper;
`execute_authorized_formal_development` captures the complete formal operation. Neither returns the
raw function or accepts a replacement.

A file becomes accepted formal natural evidence only when the read-only verifier validates the
complete authorization-marker-private-terminal-record chain. No module-level helper accepts a
natural bundle, arbitrary bytes plus a natural evidence class, or a caller-created seal identity.

The natural private inventory is exactly this ASCII-ordered tuple, with no missing, extra,
duplicate, alias, or caller-selected name:

```text
provisional-winner.json
qualification-report.json
ranking-report.json
replay-report.json
trial-summary.json
```

### 3.4 Deterministic paired output and terminal record

The private destination is the exact `private_container_path`. The public destination is derived as
the same trusted parent's child named `<private filename>.public.json`. The caller cannot supply or
override it.

Both final leaves must be absent, their parent must already exist outside the repository, and the
complete textual and handle-relative Windows ancestor checks from the canonical-container design
must pass before authorization consumption or loader access. POSIX and other platforms return
`PUBLICATION_UNSUPPORTED` before mutation and make no publication claim.

Private bytes are computed before the first output create. Private publication occurs first. The
operation then performs its final `EXIT` guard and builds the public sibling as this exact terminal
record:

```python
class FormalDevelopmentSeal(BaseModel):
    schema_version: Literal["mdcp.formal-development-seal.v1"]
    canonicalization_version: Literal["RFC8785"]
    terminal_state: Literal["SEALED"]
    authorization_sha256: Sha256
    consumption_marker_sha256: Sha256
    search_freeze_commit: GitCommit
    search_receipt_sha256: Sha256
    source_inventory_sha256: Sha256
    protocol_sha256: Sha256
    repository_inventory_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]
    private_identity: PrivateBundleIdentity
    exit_observation_sha256: Sha256
    fit_count: Literal[80, 84]
    selection_status: Literal[
        "PASS", "NO_ELIGIBLE_CANDIDATE", "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
    ]
    h1_role: Literal["OBSERVED_DEVELOPMENT_ONLY"]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    development_result: PublicDevelopmentResult
```

`selection_status` and `development_result.status` must be exactly `PASS/PASS`,
`NO_ELIGIBLE_CANDIDATE/FAIL`, or `UNKNOWN/NO_ELIGIBLE_CANDIDATE` paired with `UNKNOWN`. The last
pair permits fit count `80` for terminal invalidation before replay and `84` for a completed replay
whose verdict or exact evidence failed. Every nested object forbids extra fields. The development
result must have `evidence_class="natural_development"`; all SHA-256 identity fields and every field
of `PrivateBundleIdentity` must be nonzero. Content-derived identities are independently
recomputable. `repository_inventory_sha256` is independently computed and retained by the invoking
controller before process launch, then compared with the runtime observation; it is an externally
anchored assertion, not self-authenticating merely because it appears inside the seal.
The terminal record does not contain its own digest. Its
physical RFC 8785 byte digest is `seal_record_sha256` in the returned outcome and is a required
trusted input to later offline acceptance. `development_result` retains its existing exact closed
aggregate model; no raw row, label, prediction, timestamp, path, exception, or environment value is
added.

The public sibling is the final acceptance mutation. If it is absent or invalid, recovery returns
`UNKNOWN`, even when the private container is valid. The live operation returns `PASS` only after
its full bytes are written, flushed, handle-identity checked, and successfully closed. Recovery may
return `PASS` only when the caller also supplies the trusted `expected_seal_record_sha256` recorded
from that successful outcome. Process death before that digest is recorded remains `UNKNOWN`, even
if later inspection finds structurally valid bytes. A public-seal failure leaves the consumed
authorization and any owned private artifact as terminal `UNKNOWN`; it does not delete by path,
retry, overwrite, or report success.

### 3.5 Exact `EXIT` observation and seal-only suffix

`EXIT` is the final runtime-guard checkpoint. It must return a typed `RuntimeObservation` with
`verdict="PASS"`, `reason_codes=()`, a nonzero `repository_inventory_sha256` equal to the guard's
initial inventory, an integer `elapsed_ns` within `0..21600000000000`, and an integer
`peak_process_bytes` within `0..4294967296`. The raw elapsed and memory values are not public.

The `exit_observation_sha256` preimage is exactly the RFC 8785 canonicalization of this sanitized
JSON object, using the successful observation and already-bound identities:

```json
{
  "elapsed_within_budget": true,
  "max_elapsed_ns": 21600000000000,
  "max_peak_process_bytes": 4294967296,
  "memory_within_budget": true,
  "reason_codes": [],
  "repository_inventory_sha256": "<exact nonzero lowercase SHA-256>",
  "schema_version": "mdcp.formal-exit-observation.v1",
  "search_freeze_commit": "<exact 40-lowercase-hex commit>",
  "stage": "EXIT",
  "verdict": "PASS"
}
```

The terminal seal repeats `repository_inventory_sha256`. The offline verifier reconstructs the
object above from the seal and frozen constants, hashes its canonical bytes, and requires equality
with `exit_observation_sha256`; an opaque, zero, or non-recomputable observation digest fails.

A successful `EXIT` closes the loader, model, fit-ledger, replay-session, repository-read, and
runtime-budget guard lifecycle. Only this bounded deterministic seal-only suffix may follow:

1. construct the sanitized object above from the successful in-memory observation;
2. canonicalize and hash it;
3. construct and canonicalize `FormalDevelopmentSeal` from immutable in-memory identities;
4. write, flush, identity-check, and checked-close the already-preflighted public leaf through the
   already-captured closure-local publisher; and
5. return the closed outcome.

The suffix may not import or invoke a loader, estimator, fit, replay, repository/Git operation,
authorization parser, archive reader, environment reader, clock, memory probe, caller callback, or
caller-selected destination. Its only filesystem mutation is the retained-handle publication of
the already-computed public bytes. Source drift after `EXIT` therefore cannot influence seal bytes;
a write/flush/identity/close failure remains `FORMAL_RUN_SEAL_UNKNOWN`. Live `PASS` still requires
the checked close and an externally retained returned seal digest.

## 4. Explicit threat boundary

The design defends against:

- ordinary Python import and direct or alias calls to every named module attribute, including
  underscore-prefixed attributes;
- concurrent callers and repeated, reordered, or partially failed calls within one initialized
  trusted process;
- cross-process reuse while the no-clobber marker leaf remains established;
- forged dataclasses, subclasses, serialized objects, booleans, callbacks, writers, loaders,
  digests, bundles, and result objects;
- dynamic import forms already governed by the static firewall;
- filesystem aliases, links, junctions, reparse ancestors, path substitution, existing leaves,
  short writes, flush failures, and no-clobber races; and
- repository, deadline, memory, source-inventory, bounded-loader, or H2 firewall drift.

The design does not claim resistance to a malicious actor who can attach a debugger, use `ctypes`
to modify process memory, introspect closure cells deliberately, monkeypatch trusted modules before
startup, replace the Python interpreter, or exercise same-user host administration authority. Those
capabilities are inside the trusted-process/host boundary. Resisting them requires a separately
approved OS-process isolation and cryptographic signing design.

The design also does not claim code-only cross-process reuse resistance after an indeterminate
marker create that returned no handle and left no durable leaf. That storage-failure state is
`UNKNOWN`; the owner-side P2 controller must stop and never launch the same authorization again.
Autonomous restart after that state requires a separately approved durable authority service.

This boundary is stronger than treating underscore functions as trusted, but intentionally narrower
than claiming hostile-code isolation inside one CPython process.

## 5. Identity binding

The operation verifies and binds:

- current clean HEAD equals `expected_freeze_head`;
- remote count and HEAD tag count remain zero;
- the search receipt and evidence index are canonical and mutually consistent;
- the receipt digest equals the authorization's exact receipt digest;
- `dataset_archive_sha256` equals the approved frozen archive identity
  `b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401`;
- the actual archive bytes equal that identity before row parsing;
- `dataset_contract_sha256` equals the actual canonical protocol-file digest;
- the protocol, fold, trial, ranking, quality, statistical, adapter, schema, lock, and source
  inventories recompute from current bytes; and
- the formal output contains exactly the approved five ASCII-ordered logical names.

No archive, protocol, receipt, source-inventory, private, public, or evidence identity is accepted
from a CLI digest flag. The required `--expected-freeze-head` is the separately named expected Git
commit, and `run-development` has no `--archive-sha256` or `--protocol-sha256` argument.

The persisted identity chain is acyclic:

```text
canonical authorization bytes
  -> consumption marker (authorization/freeze/receipt/protocol/archive identities)
  -> private container identity
  -> terminal public seal (marker + private + aggregate + EXIT + repository assertion)
  -> externally recorded terminal-seal and independently precomputed repository digests
```

The read-only recovery API is exact:

```python
def verify_formal_development_seal(
    consumption_marker_path: Path,
    private_container_path: Path,
    terminal_seal_path: Path,
    *,
    expected_authorization_sha256: str,
    expected_search_receipt_sha256: str,
    expected_source_inventory_sha256: str,
    expected_repository_inventory_sha256: str,
    expected_seal_record_sha256: str,
) -> FormalSealCheck:
    ...
```

The result model is frozen and exact:

```python
@dataclass(frozen=True, slots=True)
class FormalSealCheck:
    verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    reason_codes: tuple[str, ...]
    private_identity: PrivateBundleIdentity | None
    seal_record_sha256: str | None
    repository_inventory_sha256: str | None
    fit_count: Literal[0, 80, 84]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
```

Its reason-code sets are closed:

```text
PASS:    ()
FAIL:    FORMAL_SEAL_REQUEST_INVALID
         FORMAL_SEAL_CHAIN_ABSENT
         FORMAL_SEAL_CHAIN_INVALID
         FORMAL_SEAL_TRUST_MISMATCH
UNKNOWN: FORMAL_SEAL_INSPECTION_UNKNOWN
         FORMAL_SEAL_CONSUMPTION_UNKNOWN
         FORMAL_SEAL_INCOMPLETE
         FORMAL_SEAL_UNANCHORED
```

`FAIL` and `UNKNOWN` contain exactly one reason. Every non-`PASS` result has
`private_identity=None`, `seal_record_sha256=None`, `repository_inventory_sha256=None`, and
`fit_count=0`. Only a fully anchored `PASS` returns the verified four-field identity, actual nonzero
seal-record digest, externally matched repository-inventory digest, and seal fit count.

All five expected digests must be exact 64-character lowercase SHA-256 strings. Authorization,
receipt, source-inventory, and repository-inventory expectations must also be nonzero. The all-zero
value is permitted only for `expected_seal_record_sha256`, where it explicitly means that no
successful live outcome digest was retained out of band. Recovery precedence and results are
exhaustive:

| First applicable observed state | Result |
| --- | --- |
| wrong argument type, non-distinct/noncanonical path, invalid expected digest, or zero authorization/receipt/source/repository expectation | `FAIL/FORMAL_SEAL_REQUEST_INVALID` |
| any required stat/open/read/close or retained-identity inspection is indeterminate | `UNKNOWN/FORMAL_SEAL_INSPECTION_UNKNOWN` |
| marker, private, and terminal leaves are all absent | `FAIL/FORMAL_SEAL_CHAIN_ABSENT` |
| marker is absent while either artifact leaf exists | `FAIL/FORMAL_SEAL_CHAIN_INVALID` |
| marker leaf exists but is partial, noncanonical, malformed, or fails its own identity constraints | `UNKNOWN/FORMAL_SEAL_CONSUMPTION_UNKNOWN` |
| marker is valid but private or terminal is absent, partial, noncanonical, malformed, or individually unverifiable | `UNKNOWN/FORMAL_SEAL_INCOMPLETE` |
| all three objects are individually valid but any internal marker/private/seal/EXIT/fit/status/H2 cross-binding differs | `FAIL/FORMAL_SEAL_CHAIN_INVALID` |
| internally valid chain differs from a nonzero expected authorization, receipt, source-inventory, repository-inventory, or seal digest | `FAIL/FORMAL_SEAL_TRUST_MISMATCH` |
| internally valid chain matches authorization/receipt/source/repository expectations but expected seal digest is all zero | `UNKNOWN/FORMAL_SEAL_UNANCHORED` |
| internally valid chain matches all five nonzero expectations | `PASS/()` |

Within each row, more specific earlier rows take precedence. The verifier parses bounded bytes,
recomputes the private inventory and manifest, reconstructs the sanitized `EXIT` preimage, and hashes
the physical terminal bytes independently. It performs no mutation, recovery write, cleanup,
resume, model load, or row access. It never treats a digest found only inside the artifacts under
review as its own trust anchor.

## 6. CLI boundary

At corrected Task 4 completion, the command tuple remains exactly:

```text
run-development
verify-search-freeze
```

`run-development` constructs the exact request internally from fixed command arguments and fixed
environment-variable names. It sets all seven approved CPU thread environment values to `1` before
any estimator-bearing import. It never exposes a replay command, permit command, consume-only
command, natural writer, arbitrary output callback, or caller-supplied archive, protocol, private,
public, or evidence digest. The expected freeze commit is an identity assertion, not one of those
content-digest injection points.

The exact Task 4 `run-development` argument surface is:

```text
--expected-freeze-head <40-lowercase-hex>
--search-receipt <path>
--evidence-index <path>
--authorization-env MDCP_FORMAL_RUN_AUTHORIZATION
--consumption-root-env MDCP_FORMAL_RUN_CONSUMPTION_ROOT
--archive-env MDCP_UCI_ARCHIVE
--private-container-env MDCP_V02_PRIVATE_CONTAINER
```

The four environment-variable options accept only the literal names shown. Their values are read
once and are never copied into public output or error text.

### 6.1 Exact stdout custody contract

The recognized `run-development` command emits no logs. On operation `PASS`, stdout is exactly the
RFC 8785 canonical bytes of the following object followed by one ASCII LF, stderr is empty, stdout
is explicitly flushed, and the process exits `0`:

```json
{
  "repository_inventory_sha256": "<R>",
  "schema_version": "mdcp.formal-seal-custody.v1",
  "seal_record_sha256": "<S>"
}
```

`R` and `S` must equal the two nonzero digests in the returned `FormalDevelopmentOutcome`. On
operation `FAIL` or `UNKNOWN`, stdout is exactly one RFC 8785 canonical object plus LF with keys
`reason_code`, `schema_version="mdcp.formal-run-cli-result.v1"`, and `verdict`; stderr is empty and
the exit code is respectively `2` or `3`. The reason is the outcome's sole fixed reason code. Parser
or invocation rejection uses the same `FAIL` object with `FORMAL_RUN_REQUEST_INVALID`; it never
prints argparse usage, supplied arguments, paths, or environment values.

If writing or flushing the PASS custody line fails, the process returns `4` where platform state
permits and makes no success claim. A pipe may already contain a prefix, so the parent must reject
anything other than exactly one complete canonical line, EOF, empty stderr, and exit `0`. It must
also reject any extra stdout/stderr byte.

The invoking P2 controller, not repository code, owns out-of-band custody. Immediately before child
launch it independently computes `R` from the clean expected HEAD using the frozen tracked-path/NUL
inventory algorithm, retains that expected value, and captures stdout/stderr through dedicated
pipes. After an exact exit-`0` line, it independently hashes the checked terminal-seal file to obtain
`S`, requires both values to match the line, and writes that exact line no-clobber into an
owner-approved, precreated private external custody root as
`<S>.formal-seal-custody.json`. The file bytes are exactly the canonical stdout object without the
trailing LF; its final leaf must be absent and publication is no-clobber. Only after checked
persistence does the controller retain `R` and `S` as recovery trust anchors. Missing/partial
output, digest disagreement, or unknown custody persistence requires
`expected_seal_record_sha256="0" * 64` and therefore `UNKNOWN/FORMAL_SEAL_UNANCHORED`; an
operation-level PASS alone is not evidence acceptance.

Task 6 may later add only the three already-approved read-only/freeze commands. No Task 4 code may
invoke the formal command during implementation or tests.

The later `verify-search-source` command requires
`--expected-index-sha256 <64-lowercase-hex>`. Without that out-of-band trust anchor it may report
internal structure only and must not claim source authenticity or coordinated-mutation detection.
The corrective plan must require the owner-side controller to independently validate and hash the
canonical 43-path index bytes emitted no-clobber by `prepare-search-freeze` from the clean committed
`SEARCH_SOURCE_COMMIT`, then persist this exact RFC 8785 object no-clobber as
`<I>.search-source-custody.json` under the same precreated private custody root before the freeze
child is accepted:

```json
{
  "schema_version": "mdcp.search-source-custody.v1",
  "source_inventory_index_sha256": "<I>"
}
```

The controller later supplies that retained nonzero `I` to `verify-search-source`. A digest copied
only from the index or source archive during verification is not a trust anchor; absent checked
external custody, verification remains internal-consistency-only.

## 7. Static and behavioral firewall

The static firewall fixes the exact imports, attributes, environment keys, Git calls, and file
operations required by the single operation. It additionally fails if production exposes any named
callable whose normalized name indicates a formal permit, claim, activation, natural builder,
natural writer, natural publisher, or seal-authority surface outside
`execute_authorized_formal_development`.

The exact new post-initialization formal callable/type surface is:

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
  (no new public formal callable)
```

`build_parser` only constructs the exact parser. `main` is the allowed string-argument CLI
dispatcher; it constructs `FormalDevelopmentRequest`, invokes
`execute_authorized_formal_development` once for `run-development`, emits only the closed custody
record in Section 6.1, maps the outcome to its fixed exit code, and returns no artifact, authority,
writer, or callback. There is no separately named run handler. The first five `run_evidence.py`
entries are exact frozen models and expose no mutation method. Its two functions are the sole Python
natural mutation and read-only verification operations.

Runtime and AST audits reject a raw publisher or natural codec reachable through a module name,
alias, function default/keyword default, registry/container, class attribute, extra factory result,
or returned object. They also enumerate every named callable on `cli.py`, `run_evidence.py`,
`search_identity.py`, and `runner.py`, fail on an unexpected addition, and assert that no allowed
callable except `main` dispatches the sole `execute_authorized_formal_development` operation.

Task 4 does not claim a live successful-natural race test: such a test would require the P2 owner
authorization, approved archive, natural encoder, and formal destinations that this implementation
wave is forbidden to exercise. The prior `SEALING` race is instead closed by an exact structural
reachability invariant at post-initialization module state. Starting from every named module
attribute and recursively traversing aliases, bound methods, defaults, keyword defaults,
class-owned attributes, registered containers, allowed factory return values, and values returned
by public test calls, the audit must find:

- no `FormalRunPermit` or other caller-visible intermediate authority;
- no separately callable authorization consumption transition;
- no natural bundle encoder, raw-byte publisher, or paired natural writer;
- no function that accepts both attacker-supplied natural content and an output destination; and
- exactly one edge from the CLI dispatcher to the closure-owned formal operation.

The deliberately excluded closure-cell introspection and pre-startup monkeypatch capabilities in
Section 4 are not smuggled back into this audit. Under the stated named-attribute boundary, the
absence of any caller-held state or callable at `SEALING` makes the reviewed scheduling race
unrepresentable rather than merely timing-dependent.

Behavioral tests use deterministic generated objects only. Concurrent callers possess synthetic
inputs and all importable module names, but no authorization, archive, natural bundle, or formal
destination. They prove only the behavioral properties available inside that scope: one synthetic
execution plan is consumed once under concurrency, its one ledger permits at most 80 selection plus
four replay fits, and no call reaches a legacy loader, `split_rows`, or `open_h2`. Permit absence,
natural-byte unavailability, formal-pair publication denial, and the old `SEALING` race are the
structural reachability assertions above, not mislabeled successful-natural behavioral tests.

The deterministic composition harness exists only in
`tests/integration/temporal/test_formal_runner_synthetic.py`. It accepts an exact test-only synthetic
input type with deterministic generated folds, forces `evidence_class="synthetic_test"`, calls the
same pure ledger/session core and the public synthetic writer, and returns only a synthetic typed
result and synthetic `PrivateBundleIdentity`. It has no authorization, archive, natural bundle,
public terminal-record, raw-bytes, writer, callback, loader, or formal destination field.

This harness is not an instantiation of the formal authorization/seal state machine and cannot emit
`natural_development` or a `FormalDevelopmentSeal`. Tests never load UCI/H1/H2 rows, build an
estimator, execute a real formal authorization, or publish outside a fresh temporary root.
Successful natural closure execution remains P2-gated; Task 4 tests prove denial order, exact
structural reachability, rejected-call concurrency, and pure ledger/session components without
claiming successful-natural behavioral execution.

## 8. Error and recovery semantics

All public errors are fixed reason codes. They never echo a path, authorization ID, digest supplied
by an attacker, payload, raw exception, environment value, hostname, or credential-shaped string.

The marker leaf is `<authorization-sha256>.consumed.json` under the precreated trusted consumption
root. Its canonical document is exact:

```python
class FormalRunConsumptionMarker(BaseModel):
    schema_version: Literal["mdcp.formal-run-consumption.v1"]
    canonicalization_version: Literal["RFC8785"]
    consumed: Literal[True]
    authorization_sha256: Sha256
    search_freeze_commit: GitCommit
    search_receipt_sha256: Sha256
    protocol_sha256: Sha256
    dataset_archive_sha256: Literal[
        "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
    ]
```

Every field is derived from verified bytes; the authorization's private identifier is not copied.
The marker uses the same closure-owned Windows `NtCreateFile(FILE_CREATE)` no-clobber primitive and
retained trusted ancestor chain as the final artifacts.

The wrapper initializes the output handle to the invalid sentinel, records `create_entered=False`,
sets it to `True` immediately before the single synchronous `NtCreateFile` call, and retains the raw
`NTSTATUS`, returned handle value, and `IO_STATUS_BLOCK`. It never infers syscall completion from a
later path lookup. The closed precedence matrix is:

| Create entered | returned status | owned valid handle | handle-relative final-leaf state | Result and retry rule |
| --- | --- | --- | --- | --- |
| no | absent | no | absent | `FAIL/FORMAL_RUN_CONSUMPTION_FAILED`; the only retryable case, because the wrapper proves no create syscall began |
| no | absent | no | present | `FAIL/FORMAL_RUN_AUTHORIZATION_CONSUMED`; never retry |
| yes | exact `STATUS_OBJECT_NAME_COLLISION` | no | absent, present, or indeterminate | `FAIL/FORMAL_RUN_AUTHORIZATION_CONSUMED`; collision itself is authoritative and permanently denies retry |
| yes | returned `STATUS_SUCCESS (0x00000000)`, `IO_STATUS_BLOCK.Status == STATUS_SUCCESS`, and `IO_STATUS_BLOCK.Information == FILE_CREATED (0x00000002)` | non-null and non-invalid | present through the returned handle | authority is irreversibly consumed; continue marker write through that handle |
| yes | any status | yes but not the exact success row | any | `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN`; checked-close the owned handle where possible and never retry |
| yes | success, informational, warning, pending, missing, unrecognized, or wrapper-exception status | no | any | `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN`; never retry |
| yes | non-collision error status | no | present or indeterminate | `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN`; never retry |
| yes | non-collision error status | no | absent | `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN`; absence does not prove that no create transition occurred, so never retry |

No returned `NTSTATUS` other than the exact success and collision rows is treated as conclusive
evidence that authority remains reusable. In particular, a concurrent collision after preflight is
consumed even if a later observation races back to absent, while an unrelated leaf appearing after
an error never converts the result to success. `FORMAL_RUN_CONSUMPTION_FAILED` is reserved for a
closed local preparation failure with `create_entered=False` and handle-relative absence proved
through the retained parent.

An indeterminate no-leaf result cannot provide durable local revocation when the storage primitive
itself did not establish an owned leaf. It is therefore a hard `UNKNOWN` stop: the operation and CLI
never retry it and the in-process closure permanently rejects that authorization digest. Across a
fresh process, enforcement belongs to the owner-side controller stop rule stated in Section 4; the
implementation must not claim crash-persistent local denial for that storage-failure case.

After the exact success row, any short write, file flush, handle-identity recheck, or checked close
failure returns `UNKNOWN/FORMAL_RUN_CONSUMPTION_UNKNOWN`; the owned marker or partial marker is
retained and its name permanently denies retry. Full write, `FlushFileBuffers`, identity recheck,
and successful checked close establish the canonical marker digest used by the terminal record.

Windows provides no claimed portable parent-directory flush in this design. Durability claims are
limited to the write-through synchronous file handle, successful file flush, retained ancestor
identity checks, and checked handle close. The absence of a claimed parent flush is explicit and is
covered by the same-user trusted-host boundary.

After marker-handle acquisition, every exception maps to terminal `UNKNOWN`. Runtime guards still
execute their one ordered terminal sequence where platform state permits. No exception path restores
authority, reuses output names, deletes a marker or unowned path, or presents a partial pair as
valid.

Recovery inspection verifies the marker, private container, and terminal seal through the exact API
in Section 5. It is read-only and cannot resume or complete the run. A valid marker without a valid
terminal seal is always `UNKNOWN`; a valid terminal seal with any chain mismatch is `FAIL` and is
never accepted as natural evidence.

## 9. Migration and file scope

Clean Task 3 HEAD `3c0fcddd7fded5f62d3f731864ff423f815fff16` is the immutable migration
baseline. The actual implementation entry must be the clean, owner-reviewed corrective-plan commit
descended append-only from that baseline and containing both this approved amendment and its
corrective plan. The preserved blocked Task 4 payload is diagnostic reference only; it is never
applied wholesale and never becomes formal evidence.

Task 2R and Task 3 commits remain immutable. The historical corrective plan remains unchanged.
Implementation stays within the existing 19-path allowlist. This amendment expands corrected Task 4
from nine to exactly eleven of those already-approved paths so the terminal public schema and
low-level publication regressions are reviewable in scope:

```text
schemas/v2/development-result-index.schema.json
schemas/v2/formal-run-authorization.schema.json
src/mdcp/temporal/cli.py
src/mdcp/temporal/firewall.py
src/mdcp/temporal/run_evidence.py
src/mdcp/temporal/runner.py
src/mdcp/temporal/search_identity.py
tests/integration/temporal/test_formal_runner_synthetic.py
tests/security/temporal/test_data_firewall.py
tests/security/temporal/test_formal_run_authorization.py
tests/unit/temporal/test_run_evidence.py
```

`schemas/v2/development-result-index.schema.json` retains the exact existing
`PublicDevelopmentResult` as a closed nested definition and changes its top level to the exact
`FormalDevelopmentSeal`. Synthetic public-result validation continues against the nested definition;
natural acceptance requires the top-level terminal seal. No v0.1 or prior public evidence bytes are
regenerated or reinterpreted.

No dependency, lock, approved historical evidence, serving identity, dataset state, H1/H2 state,
model, ONNX, Docker, deployment, or Wave 4 path may change.

## 10. Source inventory amendment

The prior exact 41-path search-source inventory is superseded by an exact 43-path inventory. The
only additions are this amendment and its future corrective plan, inserted in ASCII order:

```text
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-formal-seal-closure-corrective.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-closure-design.md
```

The future plan must list all 43 logical paths explicitly. Source-archive verification recomputes
the inventory without `.git` and rejects missing, extra, duplicate, unknown, non-ASCII-ordered, or
internally inconsistent content. Authenticity additionally requires the caller's trusted
`expected-index-sha256`; verification first hashes the canonical index bytes and rejects a mismatch
before trusting any digest inside that index. It does not claim that membership alone detects a
coordinated source-plus-index mutation and does not use Git history as evidence. Task 7 still adds
only the two approved canonical public search-freeze JSON documents.

The inventory remains acyclic:

```text
SEARCH_SOURCE_COMMIT -> SEARCH_FREEZE_COMMIT
```

The source commit contains all 43 source paths but no freeze JSON. Its child adds only the two freeze
JSON files, whose identities never hash themselves.

## 11. TDD and review gates

Corrected Task 4 begins with real RED tests for:

- absence of caller-visible permit, factory, claim, activation, consume-only, natural builder,
  natural writer, and seal-authority surfaces;
- absence of a reachable raw publisher through module names, aliases, defaults, registries, class
  attributes, factory returns, or returned objects;
- the structural reachability regression derived from the prior deterministic `SEALING` race;
- exact archive/protocol/receipt derivation rather than caller digest injection;
- concurrent rejected formal calls and one-time synthetic-plan execution;
- full paired-destination preflight before consumption and load;
- every row of the exact `NTSTATUS`/handle/leaf matrix, including concurrent collision,
  no-handle/leaf-present, no-handle/leaf-absent uncertainty, and the sole pre-create retry case;
- private-first/public-second terminal partial failure;
- exact authorization-marker-private-terminal-record cross-binding and every read-only recovery
  truth-table row;
- the complete outcome-field and operation/development-status/80-or-84-fit matrices;
- exact sanitized `EXIT` preimage reconstruction and rejection of work outside the seal-only suffix;
- exact PASS/FAIL/UNKNOWN stdout bytes, output-failure handling, and unanchored recovery when private
  custody is absent;
- external precomputation and matching of the full repository inventory;
- one guard lifecycle and one ledger/session; and
- static plus behavioral H2 denial.

Task 4 GREEN requires its targeted suites, Task 2R/3 regressions, complete CPU suite, Ruff
check/format, `uv lock --check`, `git diff --check`, credential/private-path/publication scans,
protected-byte verification, and a fresh independent review with Critical `0` and Important `0`.
It does not implement or test `verify-search-source`, 43-path index custody, or no-`.git` source
recomputation.

Corrected Task 6 begins separate RED tests for the exact 43-path inventory, rejection of a missing,
zero, malformed, or mismatched `--expected-index-sha256`, and no-`.git` internal recomputation.
Corrected Task 7 adds the integration RED/GREEN proof that `prepare-search-freeze` emits the exact
index from the clean source commit, the owner-side controller independently validates and hashes
those bytes, the private `<I>.search-source-custody.json` publication is no-clobber, and the retained
`I` is the value later accepted by `verify-search-source`. Task 6/7 GREEN and the final completion
gate, not Task 4, require the source-archive and index-custody proofs.

Each corrective task uses append-only commits with
`kuotunyu <61350295+kuotunyu@users.noreply.github.com>`. No amend, rebase, squash, reset, stash,
history rewrite, remote, push, merge, tag, Release, or external publication is allowed.

## 12. Stop conditions

Stop at a clean checkpoint if implementation requires:

- returning any formal permit or intermediate natural-seal authority to the caller;
- a reachable module-level natural builder, writer, raw publisher, or publisher callback;
- accepting a formal pair without the externally trusted terminal-seal and source-index digests;
- weakening the stated named-attribute/concurrency threat boundary;
- adding an implementation path outside the existing 19-path allowlist;
- modifying the approved protocol, quality gates, protected identities, dependency lock, or
  historical evidence;
- UCI/H1/H2 row access, a real authorization, model execution, Docker, GPU, network, P2, or Wave 4;
- claiming POSIX mutation support; or
- proceeding with any unresolved Critical or Important review finding.

Successful implementation still stops at:

```text
SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED / H2_SEALED_NOT_LOADED
```

## 13. Rejected alternatives

### 13.1 Separate OS worker

A dedicated worker process would provide a stronger memory/capability boundary, but it violates the
approved one-process, one-ledger lifecycle and requires new process-launch, IPC, source-inventory,
firewall, and operational policy. It remains a future owner-reviewed option, not this correction.

### 13.2 Trust underscore-prefixed APIs

Treating module-private names as trusted would make the blocked patch appear sufficient, but it does
not satisfy the reviewed direct-import and concurrency boundary. This alternative is rejected.

### 13.3 Add another permit state or secret token

Another state, lock, renamed function, or token still exposes intermediate authority to a caller
that already holds the permit. This repeats the failed architecture and is rejected.

## 14. Self-review checklist

Before written-spec approval, verify:

- no placeholder, ambiguous normative verb, or unspecified interface remains;
- no caller-visible permit or natural-authority cycle remains;
- natural encoding, raw publication, and accepted publication are one closure-owned operation;
- the terminal seal binds authorization, marker, private identity, aggregate result, and `EXIT`;
- marker uncertainty and retry denial are exact;
- indeterminate no-leaf restart resistance is explicitly outside the code-only threat claim;
- the threat boundary is explicit and does not overclaim hostile-code isolation;
- the five private logical paths and paired destination rule are closed;
- archive, protocol, receipt, source, private, and public identities are acyclic;
- offline authenticity requires external terminal-seal and source-index digests;
- runtime repository identity requires the controller's independently precomputed external digest;
- corrected Task 4 uses exactly eleven paths inside the unchanged global 19-path allowlist;
- the exact source inventory is 43, not 41;
- source-archive recomputation does not require `.git`;
- the blocked patch is diagnostic only;
- H2 remains sealed with loaded rows `0`; and
- no scope drift reaches P2, models, Docker, GPU, network, deployment, or Wave 4.
