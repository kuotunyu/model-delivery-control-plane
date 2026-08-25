# MDCP v0.2 Single Canonical Private-Evidence Container Amendment

**Status:** OWNER APPROVED — CORRECTIVE IMPLEMENTATION PLANNING AUTHORIZED

**Date:** 2026-08-26

**Applies to:** Wave 3 corrective Task 2 and the private-evidence portions of Tasks 4, 6, and 7

**Supersedes:** only the directory/staging-tree publication mechanism described by the approved
Wave 3 execution-boundary corrective design and plan

**Does not authorize:** UCI/H1/H2 row access, model execution, Docker, GPU, network, remote
operations, P2 consumption or formal execution, Wave 4, threshold changes, or protected-evidence
mutation

## 1. Decision

MDCP SHALL publish one run's private evidence as one canonical regular file at the exact
no-clobber destination. The file is a deterministic RFC 8785 JSON container holding a closed,
ordered inventory of logical private files. The entire container byte sequence is built and
validated in memory before the destination is touched.

The destination is no longer a directory. There is no staging directory, descendant file tree,
or final directory rename. Publication performs one create-new operation under a caller-created,
trusted parent, writes only through the returned invocation-owned handle, flushes that handle, and
flushes the parent directory where the platform supports it. A second publication cannot replace,
merge with, or append to an existing destination.

This decision removes the unresolved Windows interval in which descendant handles had to be
closed before a staging-root rename. It keeps the public identity deliberately narrow and makes the
private artifact independently verifiable from a source archive without Git history. Publication
in v0.2 is supported only on the authoritative Windows host; POSIX reviewers can build and verify
container bytes but cannot publish them.

## 2. Triggering evidence and append-only boundary

The directory-based Task 2 implementation remains in append-only history through commit
`90282ac6f753c7241a2e058f505de77976d210fe`. Its tests pass, but independent review correctly found
that closing child handles before renaming the staging root permits a same-user concurrent move of
a sealed descendant. A later identity mismatch detects the event but cannot prove that private
bytes were never moved outside the staging boundary.

Three separately evidenced directory-locking hypotheses failed to establish a cross-platform
proof: temporary-root ACL confinement, root-directory oplocks, and descendant oplocks. The project
therefore stops extending the directory design. No existing commit is amended, rebased, reset, or
deleted. This amendment and its implementation are append-only corrections.

## 3. Preserved normative contracts

This amendment SHALL NOT alter or reinterpret:

- the approved v0.2 temporal development protocol, folds, trials, features, thresholds, seed,
  bootstrap, chronology, fit budgets, or subgroup definitions;
- v0.1/v0.2 serving identities or any protected-byte inventory;
- the bounded development interface or H2 `SEALED_NOT_LOADED`, loaded rows `0`;
- the one-process, one-authorization, one-ledger, one-replay-session formal lifecycle;
- the public result schema or public-evidence sanitization boundary;
- `PrivateBundleIdentity`, whose exact public fields remain `file_count`, `total_bytes`,
  `inventory_sha256`, and `manifest_sha256`; or
- the acyclic `SEARCH_SOURCE_COMMIT -> SEARCH_FREEZE_COMMIT` construction.

The historical Wave 3 plans and design remain unmodified execution records. A new corrective plan
shall supersede only the affected publication steps and then resume the already-approved Tasks
3–7 serially.

## 4. Canonical container contract

### 4.1 Physical and logical identity

The physical artifact is exactly one regular file. Logical private files exist only as entries in
the container; no entry is materialized beside the container during publication.

The top-level document has exactly these fields in its schema:

```text
schema_version            = "mdcp.private-evidence-container.v1"
canonicalization_version  = "RFC8785"
evidence_class            = "synthetic_test" | "natural_development"
file_count                = non-negative JSON integer, never boolean
total_bytes               = non-negative JSON integer, never boolean
entries                   = closed ordered array of 1..128 entry objects
inventory_sha256          = lowercase SHA-256
manifest_sha256           = lowercase SHA-256
```

Each entry has exactly:

```text
logical_path              = canonical relative POSIX logical path
byte_size                 = non-negative JSON integer, never boolean
sha256                    = lowercase SHA-256 of decoded payload bytes
payload_base64            = RFC 4648 canonical base64 with required padding
```

Entries are strictly sorted by ASCII byte order of `logical_path`. A path is at most 240 ASCII
characters, each segment is 1..64 characters from `[A-Za-z0-9._-]`, and the complete path must
match the existing canonical POSIX relative-path rules. Empty, absolute, non-ASCII,
backslash-containing, dot-segment, duplicate, Windows device/stream/normalization-alias, or
non-canonical logical paths fail closed. Unknown or duplicate JSON keys fail closed. Payload base64
must decode with strict alphabet/padding validation and re-encode to the identical string. Every
decoded payload must already be canonical JSON under the existing parser and RFC 8785 canonicalizer.

### 4.2 Digest layers and cycle avoidance

Digest construction is fixed and acyclic:

1. For every entry, `sha256 = SHA256(decoded payload)` and `byte_size = len(decoded payload)`.
2. `inventory_core` is the RFC 8785 array of entry metadata containing only `logical_path`,
   `byte_size`, and `sha256`, in the same closed order. It excludes `payload_base64`.
3. `inventory_sha256 = SHA256(RFC8785(inventory_core))`.
4. `manifest_core` is the RFC 8785 object containing `schema_version`,
   `canonicalization_version`, `evidence_class`, `file_count`, `total_bytes`, and
   `inventory_sha256`. It excludes `entries`, payloads, and `manifest_sha256`.
5. `manifest_sha256 = SHA256(RFC8785(manifest_core))`.
6. The final container document includes both digests and entries, and its physical bytes are the
   RFC 8785 canonicalization of that final document.

Neither digest hashes itself. `total_bytes` is the sum of decoded payload sizes, not the container
size. `PrivateBundleIdentity` is derived from the validated digest layers and never includes the
container path, payload, absolute host metadata, timestamp, environment, or exception text.

### 4.3 Closed verification

The encoded container is limited to 512 MiB, each decoded payload to 128 MiB, and the decoded
aggregate to 384 MiB. These fixed bounds leave headroom beneath the existing 4 GiB authoritative
process-memory gate while accommodating the five approved natural logical outputs. The natural
formal wrapper additionally requires exactly the five Task 6 logical names; the generic synthetic
writer permits 1..128 closed test entries.

The verifier accepts only a regular non-link file and validates, in this order:

1. bounded file size before allocation;
2. strict JSON parsing with duplicate-key rejection;
3. exact top-level and nested field sets and literal versions;
4. RFC 8785 byte equality for the full document;
5. closed logical-path ordering and uniqueness;
6. strict base64 representation and decoded-payload canonicality;
7. every payload size and digest;
8. exact count and aggregate byte total;
9. inventory and manifest digest recomputation; and
10. synthetic/formal evidence-class authority.

Any mismatch returns only a fixed failure code. Errors never echo a path, payload, credential,
exception, or untrusted value. There is no permissive extraction mode and no unknown entry type.

## 5. Atomic no-clobber publication

### 5.1 Common preconditions

The caller supplies one exact drive-local Windows destination whose parent already exists. UNC,
device, volume-alias, relative, empty, or aliased destinations fail before mutation. Starting from
the drive root, the writer opens the root once with `CreateFileW(OPEN_EXISTING,
FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_BACKUP_SEMANTICS)` and then opens every descendant component
strictly handle-relative through the previously verified parent. Every directory handle omits
`FILE_SHARE_DELETE` and remains open through final-file close; every component must be a directory,
must not have `FILE_ATTRIBUTE_REPARSE_POINT`, and must remain on the root volume identity. This
rejects symlinks, junctions, mount points, component substitution, ancestor rename, and cross-volume
traversal during publication. An existing destination of any type or a missing component fails
closed. All container bytes and public identity fields are computed before the first create attempt.

The write path never calls `mkdir`, never creates a staging name, never performs rename/replace,
never follows a destination link, and never reopens the destination by absolute path to write.

### 5.2 Windows

Windows publication uses only the ancestor chain above and exactly one handle-relative
`ntdll!NtCreateFile` for the non-directory destination child. There is no alternate `CreateFileW`,
path-based open, or fallback for final creation. Its object attributes set `RootDirectory` to the
retained trusted-parent handle and contain only the validated single child name. It uses:

- create disposition `FILE_CREATE`/`CREATE_NEW`;
- no replace, overwrite, append-to-existing, or open-existing fallback;
- write, synchronize, read-attributes, and delete authority needed only for this invocation;
- write-through/synchronous semantics; and
- share mode `0`, preventing another open for read, write, delete, or rename while the owned handle
  is live.

The implementation writes the complete prebuilt bytes through that handle, requires full writes,
flushes the file buffers, rechecks the file identity and all retained ancestor-handle identities,
and only then closes the file handle and returns PASS. The ancestor handles stay live until after
the final handle closes. Because the artifact is one file, there is no child-handle-close followed
by root-rename interval. After successful close, same-user access to the trusted external evidence
root is part of the host trust boundary; every later consumer must still verify the canonical
container and bound public identity before use.

### 5.3 POSIX and other platforms

v0.2 does not claim that normal POSIX file descriptors can prevent same-user rename/unlink of an
already named file or safely delete that name by descriptor after a replacement race. Therefore
every non-Windows publication call returns `PUBLICATION_UNSUPPORTED` before opening or creating any
destination or temporary path. It must not fall back to `open`, `openat`, `O_TMPFILE`, `linkat`,
`rename`, an advisory lock, or best-effort checks.

The pure container builder, parser, digest verifier, public verifier, and source-archive proof remain
cross-platform and perform no publication. Adding a POSIX publisher requires a separate owner-
approved design with an exact supported kernel/filesystem primitive and threat boundary.

### 5.4 Failure and owned partials

Before successful flush and identity verification, the Windows file handle is the sole ownership
proof. On a handled write, flush, or identity failure, the implementation calls
`SetFileInformationByHandle(FileDispositionInfo)` only on that invocation-owned, share-mode-zero
handle before closing it. It never deletes by path and never opens a name for cleanup.

If owned deletion succeeds, the destination is absent. If Windows cannot prove deletion, the
partial file remains a quarantined, no-clobber failure artifact and the call returns only
`PUBLICATION_FAILED`; it is never reported as a valid bundle and never reused or overwritten.
Retry requires a new destination under later authority. Process death has the same terminal
interpretation: a consumed formal permit plus an incomplete/non-verifying destination is
authoritative `UNKNOWN`, not permission to reuse the path.

## 6. Public/private and authorization boundaries

Task 2 continues to export only `write_synthetic_bundle_no_clobber`, which requires the exact
runtime type and `evidence_class="synthetic_test"`. A natural bundle passed through this API fails
with `FORMAL_RUN_PERMIT_REQUIRED` before filesystem mutation.

The later Task 4 formal wrapper may call the same internal container builder/publisher only while
holding the exact, already-consumed, in-memory `FormalRunPermit`. It accepts no serialized permit,
boolean override, evidence-class string, alternate writer callback, or caller-provided digest.
Implementation tests use deterministic generated payloads and denial spies only. They do not open
UCI, H1, or H2 and do not perform a model fit.

Public search-freeze documents include only the four-field `PrivateBundleIdentity` where the
approved schema requires it. They never include `payload_base64`, decoded content, private logical
paths, the physical destination, or a container-byte dump.

## 7. Corrective impact by task

### 7.1 Corrected Task 2

`run_evidence.py` replaces the directory/staging-tree code with the single-container builder,
verifier, and handle-bound publisher. The public-result schema is unchanged. Unit and security
tests change their success assertion from a directory tree to one verifying regular file and add
adversarial coverage for coordinated digest mutation, duplicate/extra fields, malformed base64,
destination aliases, ancestor substitution, create races, short writes, flush failure, owned
cleanup, second publication, and sanitized errors. Both platform branches require GREEN tests for
their respective contract: Windows must publish and verify the file; POSIX must
return `PUBLICATION_UNSUPPORTED` without mutation. Pure build/verify tests have no platform skip.
Windows capability skips may cover only an adversarial fixture such as creating a junction, never
the base publication contract.

### 7.2 Task 3

The one-ledger runner receives `PrivateRunBundle` as before. It is unaware of physical container
layout and does not gain file authority. No Task 3 selection or fit behavior changes.

### 7.3 Task 4

The single trusted CLI creates a new exact private-container destination name only after consuming
P2, then passes its in-memory permit to the formal wrapper. CLI and writer reject directory-valued
destinations. Formal publication uses the same verified container primitive; no separate natural
writer implementation is allowed.

### 7.4 Tasks 5 and 6

Boundary proofs deny staging directories, multi-file publication, path reopen, rename/replace,
writer injection, and direct natural publication. The final source inventory binds the container
builder, verifier, platform primitives, schemas, security tests, this amendment, and the exact
corrective plan
`docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md`. The
amended source inventory contains exactly 41 ASCII-ordered paths: the prior exact 39 plus this
amendment and that corrective plan, inserted in their respective `specs/` and `plans/` ordering.
Missing, extra, duplicate, reordered, or unknown paths fail closed. Private-output inventory
identities describe logical entries inside the container, not a physical directory tree.

The exact 41-path inventory is:

```text
configs/workload/temporal-development-v2.json
configs/workload/uci-bike-sharing-v1.json
docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md
docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md
docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md
docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md
docs/superpowers/specs/2026-08-26-mdcp-v02-private-evidence-container-design.md
pyproject.toml
schemas/v2/bike-request.schema.json
schemas/v2/development-result-index.schema.json
schemas/v2/formal-run-authorization.schema.json
schemas/v2/search-receipt.schema.json
schemas/v2/temporal-contract-receipt.schema.json
schemas/v2/temporal-development.schema.json
src/mdcp/common/canonical.py
src/mdcp/common/digests.py
src/mdcp/common/enums.py
src/mdcp/contracts/workload.py
src/mdcp/contracts/workload_v2.py
src/mdcp/policy/cluster_bootstrap.py
src/mdcp/temporal/adapter.py
src/mdcp/temporal/cli.py
src/mdcp/temporal/completeness.py
src/mdcp/temporal/constants.py
src/mdcp/temporal/contract_gate.py
src/mdcp/temporal/evaluation.py
src/mdcp/temporal/evidence.py
src/mdcp/temporal/firewall.py
src/mdcp/temporal/folds.py
src/mdcp/temporal/golden_vectors.py
src/mdcp/temporal/run_evidence.py
src/mdcp/temporal/runner.py
src/mdcp/temporal/runtime_guards.py
src/mdcp/temporal/search_identity.py
src/mdcp/temporal/selection.py
src/mdcp/temporal/trials.py
src/mdcp/workload/dataset.py
src/mdcp/workload/splits.py
tests/fixtures/temporal/adapter-golden-vectors.json
uv.lock
```

### 7.5 Task 7

Search freeze still adds only the two approved canonical public JSON files. The final freeze
preflight must recompute both the four-field private identity contract and the exact corrected
41-path source inventory from a source archive without `.git`. It performs no private publication
and no formal run.

## 8. Implementation scope and migration order

The corrective implementation remains within the approved 19-path Wave 3 allowlist. The immediate
Task 2 correction may modify only:

```text
src/mdcp/temporal/run_evidence.py
schemas/v2/development-result-index.schema.json
tests/unit/temporal/test_run_evidence.py
tests/security/temporal/test_public_evidence_boundary.py
src/mdcp/temporal/firewall.py
tests/security/temporal/test_data_firewall.py
```

The result-index schema may change only if needed to express the already-approved public identity;
the private container has no public schema file and is validated by an exact internal model to
avoid expanding scope. If a checked-in private-container schema becomes necessary, implementation
must stop for owner review.

Migration is strictly append-only and serial:

1. commit this design amendment;
2. pass self-review and independent design review with Critical `0`, Important `0`;
3. commit and independently approve a new corrective implementation plan;
4. write container RED tests, observe the intended failures, replace the directory behavior, and
   pass focused/full Task 2 gates;
5. obtain independent Task 2 review with Critical `0`, Important `0`;
6. resume historical Tasks 3–6 serially under the new plan; and
7. create Task 7 freeze files last, run all fresh completion gates, obtain whole-branch independent
   review, and stop before P2.

## 9. RED-to-GREEN proof obligations

The corrective plan shall include observable REDs for at least:

- successful destinations being regular container files rather than directories;
- identical bundle input producing identical canonical bytes and identities;
- exact four-field public identity with no private material;
- missing/extra/duplicate/reordered entries and coordinated payload/digest mutation;
- noncanonical JSON/base64, non-finite or boolean numeric coercion, and Windows aliases;
- existing destination, second publication, linked/reparse ancestor, and destination create race;
- short write, write failure, flush failure, identity substitution, and sanitized failure text;
- natural evidence without the exact permit;
- exact Windows `NtCreateFile` handle-relative create-new with share mode `0`, retained no-delete
  ancestor handles, and no rename/staging/path-open fallback;
- unconditional pre-mutation `PUBLICATION_UNSUPPORTED` on POSIX and other platforms;
- source-archive recomputation without `.git`; and
- H2 `SEALED_NOT_LOADED`, loaded rows `0` throughout.

GREEN requires targeted tests, Wave 0–2 regressions, the entire CPU suite, static/behavioral H2
firewalls, publication/adversarial tests, public-evidence and credential/private-path scans, source-
archive identity recomputation, Ruff check/format, lock check, `git diff --check`, protected-byte
verification, and independent review with Critical `0`, Important `0`.

## 10. Failure and stop conditions

Implementation stops clean without scope expansion if:

- a correction requires a path outside the approved allowlist or a new dependency/schema;
- any protected identity or prior evidence byte changes;
- Windows needs weaker no-clobber, no-follow, handle-relative, exclusive-share, full-write, or
  flush semantics, or a non-Windows publisher would be required;
- UCI/H1/H2 rows, model execution, Docker, GPU, network, remote operations, or P2 are needed;
- the same blocker survives three separately evidenced hypotheses;
- any Critical or Important review finding remains unresolved; or
- any source-archive, full-suite, security, publication, identity, or H2 gate remains red.

No threshold, inventory, test, security boundary, or formal-run rule may be relaxed. Rollback is a
new append-only correction or a clean blocked checkpoint, never history rewrite or evidence
deletion.

## 11. Self-review checklist and terminal state

Before implementation planning, review this amendment for:

- placeholders, ambiguous normative verbs, or dependence on Git history;
- digest/self-hash cycles or caller-supplied identity material;
- path alias, duplicate-key, base64, short-write, flush, cleanup, and process-death gaps;
- a Windows handle-close interval that permits undetected substitution, or any accidental POSIX
  publication path;
- public leakage of private logical paths, payloads, absolute paths, exceptions, or environment;
- a natural-evidence path that bypasses the consumed permit;
- source-archive or final-inventory incompleteness;
- mutation of v0.1/v0.2 identities, historical evidence, or H2 state; and
- scope drift into P2 execution, model research, deployment, or Wave 4.

The owner standing authorization permits implementation only after both the amendment and the new
plan pass self-review and independent review with Critical `0`, Important `0`. Successful execution
stops at:

```text
SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED /
H2_SEALED_NOT_LOADED
```
