# Validator threat model

## Security objective

The validator treats every candidate artifact, MLflow snapshot, supply-chain document, and archive
member as untrusted. Validation may classify that staged evidence; it cannot establish that a live
GHCR subject still exists, and offline reviewer evidence cannot be relabelled as release-CI evidence.

## Trust zones and data flow

1. A networked staging step resolves exactly one numeric MLflow model version and copies the
   candidate plus its snapshot into bounded host directories. Aliases such as `champion` are not
   accepted as validation input.
2. The one-shot validator receives the artifact directory and snapshot directory as read-only bind
   mounts. The only writable bind is the exact output directory for `validation-receipt.json`.
3. The validator runs with `network_mode: none`, a read-only root filesystem, a bounded no-exec
   tmpfs, UID/GID `10001:10001`, all Linux capabilities dropped, and no-new-privileges. It has no
   Docker socket or host control-plane mount.
4. CPU, memory, process count, temporary storage, and wall-clock duration are fixed at 0.5 CPU,
   384 MiB, 128 PIDs, 64 MiB, and 30 seconds. A timeout or resource failure is not promoted to PASS.
5. The process emits one canonical receipt and exits. The caller removes the ephemeral container;
   no validator database or writable root state survives.

## Bound identities

The frozen MLflow snapshot contains a positive numeric version, run ID, immutable artifact URI, and
the ONNX, training-row, training-config, and H1 report digests. The isolated validator compares the
ONNX and H1 identities to the staged artifact descriptor. The release workflow must additionally
compare the complete frozen snapshot to the snapshot captured during staging; a changed URI or any
changed digest fails closed.

The final release manifest separately binds the numeric MLflow version and run ID to an immutable
OCI repository and digest. Its release ID is computed from RFC 8785 canonical JSON without the
`release_id` field, avoiding descriptor/image/release-ID cycles.

## Threats contained

- Parser exploitation is constrained to a non-root, capability-free, resource-bounded container.
- Path traversal, links, duplicate archive members, executable model formats, ONNX external data,
  and operators outside policy are rejected before promotion.
- Candidate code cannot access the network, Docker daemon, host paths outside the staged mounts, or
  write back into its inputs.
- Receipt explanations and verifier failures are fixed strings; raw exceptions, URLs, credentials,
  and host paths are not persisted.

## Residual boundaries

The host kernel and Docker engine remain trusted. Image build dependency retrieval occurs before
the isolated validation job and is therefore a separate supply-chain boundary. A local offline PASS
means the sealed bytes were recomputed successfully; it is not proof of current GitHub, GHCR,
attestation, vulnerability database, or network state.
