# MDCP v0.2 Rejected-Freeze Topology Design

Status: owner approved

Date: 2026-08-27

Repository: `model-delivery-control-plane`

Branch: `codex/wave0-foundation-feasibility`

Amends:
`docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md`

## 1. Purpose and authority boundary

This amendment defines the only approved Git topology for replacing the rejected search freeze
without weakening the existing add-only freeze verifier. It resolves a planning-time contradiction
between three facts:

1. the rejected freeze commit already tracks the two canonical public search evidence paths;
2. the next corrected freeze must be an append-only descendant on the same branch; and
3. `_has_exact_allowlisted_additions` accepts a freeze child only when both canonical paths have Git
   status `A` relative to its sole parent.

This document authorizes no deletion, implementation, P2 execution, dataset access, model
execution, or evidence regeneration. After this committed document receives owner written approval,
a separate corrective implementation plan must specify the exact tombstone and refreeze commands.

For this topology only, this amendment supersedes the earlier statements that the two evidence
paths may not change before Task 7 and may receive new bytes only at the terminal freeze. The sole
earlier mutation is the exact Task 6B `D/D` tombstone defined here; it writes no replacement content.
Every other requirement of the approved final-review corrective design remains authoritative.

## 2. Proven topology contradiction

The rejected freeze checkpoint is:

```text
2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598
```

It added exactly:

```text
A evidence/public/v02/search/evidence-index.json
A evidence/public/v02/search/search-receipt.json
```

Both paths remain tracked at the approved corrective-spec commit. A direct child that writes new
bytes to either tracked path produces Git status `M`, not `A`. The existing verifier requires:

```python
len(entries) == 2
and all(status == "A" for status, _ in entries)
and {path for _, path in entries} == ALLOWLISTED_FREEZE_PATHS
```

Therefore a same-branch refreeze cannot pass while the rejected files remain present in the new
source parent. Changing receipt content, timestamp, digest, or source inventory cannot alter this
Git fact.

## 3. Selected topology: same-branch rejected-freeze tombstone

The corrected sequence remains on `codex/wave0-foundation-feasibility` and uses append-only commits:

```text
2cb2f0b  rejected freeze: canonical paths added
   |
   +-- docs approval and corrective implementation commits
         |
         +-- Task 6A: corrected source-inventory implementation commit
               |
               +-- Task 6B: rejected-freeze tombstone commit
                     D evidence-index.json
                     D search-receipt.json
                     becomes new SEARCH_SOURCE_COMMIT
                     |
                     +-- Task 7: corrected freeze commit
                           A evidence-index.json
                           A search-receipt.json
```

Task 6B removes exactly the two rejected canonical paths from the current tree. It does not delete
their Git history or external custody. Task 7 then invokes the existing no-clobber producer against
an absent destination pair, so its direct-child diff is again exactly `A/A`.

The Task 6B tombstone commit is the new `SEARCH_SOURCE_COMMIT`. The corrected receipt records that
exact commit. The corrected freeze commit has exactly one parent, that parent equals the receipt's
source commit, and its diff contains only the two `A` entries.

## 4. Why the alternatives remain rejected

### 4.1 Accept modified paths in the verifier

Allowing `M` would permit a freeze operation to replace an existing publication and would weaken
the reviewed no-clobber invariant. It is rejected.

### 4.2 Create versioned evidence paths

New paths require schema, CLI, verifier, public inventory, and allowlist changes. That expansion is
not necessary for one rejected local freeze and is rejected for v0.2.

### 4.3 Start from a pre-freeze branch or worktree

Branching from the old source commit avoids a tombstone but abandons the approved single branch and
worktree, requires replaying normative and implementation commits, and creates two competing
lineages. It is rejected.

### 4.4 Overwrite the tracked files manually

Manual replacement produces `M/M`, cannot pass the unchanged verifier, and obscures the
no-clobber transition. It is rejected.

## 5. Immutable rejected evidence

Before Task 6B, the controller must independently confirm all of these identities:

- rejected freeze commit:
  `2cb2f0bb67662bc9ba7ffb63503a55f7e3eec598`;
- rejected receipt SHA-256:
  `7bf1f01f5883c563639152b8eda6fbff8ab1171c85a5865e21ee0303afdbdc94`;
- rejected evidence-index SHA-256:
  `ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d`;
- external custody SHA-256:
  `38fc225f45fc2a282be339c8d6974154bd90a94af93132ed2132ca5c9b04bf9f`;
- external custody leaf:
  `ac113b545dbb91252f7dafc780d1afd60105523b982719b571706ec115fb612d.search-source-custody.json`.

The controller must verify the working-tree bytes equal both the expected SHA-256 values and the
exact blobs stored at `2cb2f0b`. The external custody leaf must exist as a regular no-clobber file
with the expected digest.

Task 6B changes only current-tree membership. The rejected bytes remain recoverable through the
immutable ancestor commit and remain independently anchored by external custody. No amend, reset,
rebase, squash, filter, garbage-collection manipulation, tag movement, or history rewrite is
allowed. The external rejected custody leaf is never deleted, renamed, overwritten, or reused.

## 6. Tombstone preconditions and exact mutation

Task 6B may begin only after Tasks 1-5 and Task 6A are committed, freshly verified, and independently
reviewed at Critical `0`, Important `0`. Immediately before the tombstone:

- branch is `codex/wave0-foundation-feasibility`;
- working tree and index are clean;
- remote count is `0` and HEAD has no tag;
- H2 is `SEALED_NOT_LOADED`, loaded rows `0`;
- the protected-byte inventory passes;
- the two rejected files are regular tracked `100644` leaves;
- their physical bytes and `2cb2f0b` blobs match the frozen identities in Section 5;
- the external custody identity passes;
- no replacement receipt/index bytes have been generated; and
- no real authorization, UCI/H1/H2 row, model, Docker, GPU, network, remote, or publication action
  has occurred.

The mutation is exactly the removal of:

```text
evidence/public/v02/search/evidence-index.json
evidence/public/v02/search/search-receipt.json
```

The staged diff must be exactly two status-`D` entries and no other path. The commit author and
committer are `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`. The commit message is fixed by
the implementation plan and must identify the rejected-freeze retirement, not claim evidence loss.

After the commit, the controller reports that the two current-tree leaves were removed and that
they remain recoverable from `2cb2f0b` and external custody. This is a deliberate, owner-approved,
recoverable destructive action; it is not cleanup.

## 7. Controlled no-evidence interval

Task 6B creates an intentional source state in which the canonical public search evidence paths are
absent. During this interval:

- no command other than the approved Task 7 preflight, no-clobber freeze producer, verifier, and
  read-only validation commands may run;
- no implementation edit, formatting change, test correction, data access, model action, or other
  commit is allowed;
- the missing-freeze result is expected and does not authorize P2;
- a Task 7 failure leaves the branch at the clean tombstone source commit; and
- the controller must not restore old bytes, retry with modified thresholds, or manufacture new
  bytes without a new approved plan step.

Task 7 must follow immediately in the same authorized execution session. If the controller cannot
continue safely, it stops at the clean tombstone source commit and reports that public freeze is
absent and P2 is forbidden.

## 8. Task 7 refreeze and custody

Task 7 uses the existing `prepare-search-freeze` operation. Because both canonical leaves are
absent, its existing no-clobber checks remain authoritative. It must:

1. observe the expected missing-freeze RED at the Task 6B source commit;
2. generate the canonical receipt/index pair once;
3. require receipt `search_source_commit` to equal Task 6B HEAD;
4. require H2 `SEALED_NOT_LOADED`, loaded rows `0` in both documents;
5. validate the exact source inventory and all bound digests;
6. compute the physical index SHA-256 independently;
7. create a new external custody leaf named from that new digest, with no-clobber publication;
8. verify the custody bytes and digest independently;
9. stage exactly the two status-`A` canonical files;
10. commit them as the sole receipt-only direct child; and
11. require `SEARCH_FREEZE_PASS` from the committed tree.

The new custody leaf must not reuse the rejected index digest or rejected custody path. A partial
receipt/index publication is a hard stop; neither old evidence nor a second generated pair may be
used as fallback.

## 9. Exact 43-path source inventory migration

The corrected source inventory remains exactly 43 paths. It binds the currently controlling
normative documents through this exact three-for-three substitution.

Remove from `SEARCH_SOURCE_PATHS`:

```text
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-formal-seal-closure-corrective.md
docs/superpowers/plans/2026-08-26-mdcp-v02-wave-3-private-evidence-container-corrective.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-closure-design.md
```

Add in canonical ASCII order:

```text
docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-final-review-corrective.md
docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md
docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md
```

The historical files remain in Git unchanged; only membership in the current 43-path execution
identity changes. The private-container design remains in the inventory because it is still a
foundational normative source. The new plan supersedes both older corrective plans.

The evidence paths are not members of `SEARCH_SOURCE_PATHS`. Their absence in Task 6B therefore
does not create a source-inventory omission. They remain the only two allowlisted freeze-child
paths.

## 10. Task and commit accounting

The corrective implementation still contains seven tasks. Task 6 has two independently reviewed
append-only commit boundaries:

- Task 6A: update the exact 43-path source contract, tests, and archive proof;
- Task 6B: delete exactly the two rejected evidence leaves and establish the new
  `SEARCH_SOURCE_COMMIT`.

Task 7 creates the new freeze commit. The seven tasks therefore produce at least eight commits,
plus the preceding docs-only design approval and plan commits. Commit count is not a security
shortcut: each production task retains RED -> GREEN and independent review gates, and Task 6B has
its own destructive-action preflight and review.

## 11. Recovery and rollback semantics

There is no automated rollback.

- Before Task 6B, failure leaves the rejected files present and stops cleanly.
- After Task 6B but before a valid Task 7 commit, failure leaves the canonical paths absent and P2
  forbidden.
- After Task 7 commit, any verifier or review failure preserves both Task 6B and Task 7 commits as
  rejected history; it does not rewrite them.
- Restoration of the old rejected files, creation of a second freeze attempt, or a new topology
  requires explicit owner authorization.

The old bytes can be inspected read-only with `git show` at `2cb2f0b`, but implementation commands
must not use checkout, reset, restore, or path extraction to repopulate the working tree.

## 12. Verification and review gates

The future plan must include exact gates for:

- rejected working-tree bytes versus expected SHA-256 and `2cb2f0b` blobs;
- external rejected custody existence and SHA-256;
- Task 6B staged and committed `D/D` diff with no third path;
- missing canonical leaves at the new source commit;
- Task 7 pre-generation missing-freeze RED;
- no-clobber generation of exactly two leaves;
- Task 7 staged and committed `A/A` diff with no third path;
- sole-parent equality between freeze commit and receipt source commit;
- new receipt, index, inventory, and custody digest recomputation;
- exact 43-path three-for-three source membership;
- no-`.git` source archive reproduction under `core.autocrlf=true`, `false`, and `input`;
- protected-byte, credential, private-path, public-evidence, H2, Ruff, lock, diff, and full CPU gates;
- clean worktree, remote count `0`, and no HEAD tag; and
- independent whole-range review with Critical `0`, Important `0`.

The final independent review range starts at the future plan entry commit and ends at the new freeze
commit. It must explicitly review both the Task 6B deletion and Task 7 addition rather than treating
them as canceling diffs.

## 13. Stop conditions

Stop before Task 6B if any rejected evidence or custody identity differs, an unreviewed change
exists, or another path would need deletion.

Stop at Task 6B if the staged diff is not exactly two `D` entries, the commit would not remain
recoverable, or the source inventory depends on either evidence path.

Stop at Task 7 if the producer observes an existing leaf, emits a partial pair, creates a digest
equal to the rejected identity, requires overwrite, produces anything other than two `A` entries,
or fails any custody/freeze verifier.

Always stop for scope expansion, protected identity drift, dependency or protocol change, a real
authorization, UCI/H1/H2 row access, model execution, Docker, GPU, network, remote, push, merge,
tag, Release, Wave 4, or any unresolved Critical/Important finding.

## 14. Terminal states

Successful correction remains:

```text
SEARCH_FREEZE_PASS / P2_FORMAL_RUN_AUTHORIZATION_REQUIRED / H2_SEALED_NOT_LOADED
```

Any failure after the tombstone is:

```text
W3_FORMAL_SEAL_CLOSURE_BLOCKED / P2_FORBIDDEN / H2_SEALED_NOT_LOADED
```

The absence or presence of a search freeze never grants P2 by itself.

## 15. Design self-review checklist

- The Git `A/M/D` contradiction is resolved without changing the verifier.
- The destructive action is exact, delayed, recoverable, and separately reviewed.
- Rejected bytes and external custody remain immutable.
- The no-evidence interval permits no unrelated work.
- The new source commit and freeze parent relationship contains no identity cycle.
- The new custody name is derived from the new index and cannot overwrite the rejected custody.
- Exact source inventory size remains 43 through the specified three-for-three substitution.
- Historical normative files remain present even when superseded in the execution inventory.
- The existing 19-path implementation allowlist is not expanded.
- P2, H2, data, model, network, and publication restrictions remain unchanged.
