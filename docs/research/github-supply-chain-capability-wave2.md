# GitHub supply-chain capability: Wave 2 pin review

Retrieved: 2026-08-24

This appendix is separate from `github-supply-chain-capability.md` because the Wave 0 aggregate
report binds that earlier document's exact SHA-256. Updating the bound evidence in place would make
the accepted 8/8 report stale.

## Reviewed action pins

The following immutable official release tags were resolved read-only to full Git commit SHAs:

| Action | Release | Full commit SHA |
|---|---:|---|
| `actions/checkout` | v6.0.2 | `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| `docker/setup-buildx-action` | v4.2.0 | `bb05f3f5519dd87d3ba754cc423b652a5edd6d2c` |
| `docker/build-push-action` | v7.2.0 | `f9f3042f7e2789586610d6e8b85c8f03e5195baf` |
| `actions/attest-build-provenance` | v4.1.0 | `a2bbfa25375fe432b6a289bc6b6cd05ecd0c4c32` |
| `actions/upload-artifact` | v7.0.1 | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |

The machine-readable copies are in `constraints/github-actions.lock`. Tag resolution did not
authenticate, create or mutate a repository, or dispatch a workflow. The official repositories
reviewed were `github.com/actions/checkout`, `github.com/docker/build-push-action`,
`github.com/docker/setup-buildx-action`, `github.com/actions/attest-build-provenance`, and
`github.com/actions/upload-artifact`.

## Scanner boundary

The scan path does not use `anchore/scan-action`. A 2026 open issue documents that the action can
retrieve an installation script from an unpinned branch when the tool cache is empty. Instead, the
workflow references the official non-root Syft v1.51.0 and Grype v0.117.0 images by multi-platform
manifest digest. This pins the scanner executable distribution, while the dated vulnerability DB
remains intentionally time-varying evidence and is covered by the seven-day scan window.

The reviewed official package locations were `github.com/anchore/syft/pkgs/container/syft` and
`github.com/anchore/grype/pkgs/container/grype`; the installer risk record was
`github.com/anchore/scan-action/issues/632`.

## Local-ready claim boundary

The committed workflow uses a least-privilege job, pins every action to a reviewed commit SHA,
builds once, captures the BuildKit push digest, and uses that exact digest as the attestation and
final-manifest OCI subject. No final manifest or release ID is baked back into the image.

Before registry login or any package mutation, it verifies the formal repository, exact requested
commit, natural-H1 eligibility, descriptor Git binding, and reviewed final-manifest input. The
current natural H1 result is `FAIL` and the candidate is `INELIGIBLE_H1_FAIL`, so the workflow stops
before login or push. Synthetic reviewer PASS evidence cannot satisfy this check.

`scripts/release-ci-local.ps1 -Mode ValidateOnly` checks pins, permissions, stage order, digest flow,
and local tests. It has no remote login, push, attestation, repository creation, or workflow dispatch
capability and labels its result `dev/test`.
