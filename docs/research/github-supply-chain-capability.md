# GitHub supply-chain capability research

Retrieved: 2026-08-24

## Decision

The proposed release workflow is feasible on GitHub Actions and GHCR, but Wave 0 proves only the
documented capability and permission model. It does not verify a future repository, package,
account quota, package visibility, workflow token, OCI subject, real attestation, or successful
runtime permission grant.

## Registry publication boundary

GitHub's container-publishing example uses `ghcr.io`, an image name derived from the repository,
and `GITHUB_TOKEN` for registry login. The job grants `contents: read` and `packages: write` for the
push. Package publication is therefore a distinct mutation authority controlled by the
`packages: write` permission; it is not implied by source read access.

The Container registry documentation says the namespace is the personal account or organization.
A workflow publication using `GITHUB_TOKEN` links the package to its repository automatically,
while a pre-existing unlinked package at the same namespace may prevent that token from pushing.
The future image should carry the `org.opencontainers.image.source` label and release consumers
should use the immutable `@sha256:...` reference.

Sources:

- [Publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## Attestation boundary and subject

Container attestation is a separate authority. GitHub's current example grants
`attestations: write`, `id-token: write`, `contents: read`, and `packages: write`; the latter is
required when the attestation is pushed to a container registry. The attestation's `subject-name`
is the fully-qualified image name such as `ghcr.io/<namespace>/<image>` and must not include a tag.
Its `subject-digest` is the pushed image's `sha256:HEX_DIGEST`, normally taken from the image-build
step output. This cleanly supports the approved order: push image, resolve digest, then attest that
exact subject. Publication success must not be treated as attestation success, or vice versa.

Source:

- [Using artifact attestations to establish provenance for builds](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)

## Workflow design constraints

The future release workflow should use a least-privilege job, pin third-party actions to reviewed
commit SHAs, build once, push to GHCR, capture the returned digest, and create provenance and SBOM
attestations against the tag-free subject name plus digest. A later validator must independently
verify repository/workflow identity, commit, subject name, and subject digest. Wave 0 does not select
action SHAs because no workflow is being created yet.

## Visibility, quota, and cost caveats

Container packages default to private visibility on first publication. Public-package use is free,
but private-package storage and transfer have plan allowances; exhausted allowance can block usage
when no valid payment method exists. The future repository closure must verify package visibility,
budget, retention, and account-specific policy instead of inferring them from a public-repository
plan.

Sources:

- [Introduction to GitHub Packages](https://docs.github.com/en/packages/learn-github-packages/introduction-to-github-packages)
- [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages)

## Wave 0 non-mutation statement

No remote mutation performed. This research did not authenticate, create a repository, push an
image, change package visibility, dispatch a workflow, create an attestation, inspect private
account settings, or call a mutating API.
