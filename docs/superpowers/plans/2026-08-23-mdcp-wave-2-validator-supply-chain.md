# MDCP Wave 2 Validator and OCI Supply Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate untrusted release artifacts in isolation and produce the acyclic OCI-to-final-manifest-to-release-CI evidence chain required by M2.

**Architecture:** A short-lived validator stages a bounded bundle, loses network, and runs fixed identity/ONNX/supply-chain/policy checks before emitting a canonical receipt. Release CI builds and pushes the descriptor-bearing image first, obtains the OCI digest, creates SBOM/provenance/attestation/scan evidence, then derives the final release manifest and seals a canonical bundle inventory. Offline review recomputes published evidence without claiming a fresh online identity check.

**Tech Stack:** Python 3.12, Pydantic v2, ONNX, ONNX Runtime, cryptography, RFC 8785, MLflow client, Docker BuildKit, GHCR, GitHub Actions artifact attestation, SPDX, vulnerability/license scanning, pytest, and Docker Compose.

## Global Constraints

- Entry requires Wave 1 PASS and immutable descriptor/ONNX/schema/lineage digests.
- Validator is non-root, read-only, bounded, has no Docker socket/credentials, and has no network after staging.
- Workflow order is descriptor -> image push -> OCI digest -> SBOM/provenance/attestation/scan -> final manifest/release ID -> validator receipt -> sealed release-CI bundle.
- The final manifest/release ID is never baked into or used to rebuild the existing OCI subject.
- Local developer images are `dev/test` evidence only and cannot satisfy M2 production eligibility.
- Real GitHub repository creation, GHCR push, and attestation require separate owner authorizations defined in the plan index. Without them, Wave 2 remains blocked and Wave 3 cannot start.
- Completion command: `uv run pytest tests/unit/validator tests/contract/validator tests/integration/validator tests/security/validator -q` plus an owner-authorized real release-CI verification receipt.

---

### Task 2.1: Define validator results and fail-closed CLI orchestration

**Files:**
- Create: `src/mdcp/validator/cli.py`
- Create: `src/mdcp/validator/service.py`
- Create: `src/mdcp/validator/isolation.py`
- Create: `schemas/v1/validation-receipt.schema.json`
- Test: `tests/unit/validator/test_service.py`
- Test: `tests/contract/validator/test_receipt_schema.py`

**Interfaces:**
- Consumes: staged candidate root, `ArtifactDescriptor`, and `ValidationPolicy`.
- Produces: `ValidationRequest`, `ValidationCheck(code: ReasonCode, verdict: ValidationVerdict, evidence_digest: str)`, `ValidationReceipt`, `ValidatorService.validate(request: ValidationRequest) -> ValidationReceipt`, and CLI grammar `python -m mdcp.validator.cli validate --staged-root STAGED_DIRECTORY --manifest MANIFEST_PATH --output RECEIPT_PATH`.

- [ ] **Step 1: Write failing receipt/aggregation tests**

```python
def test_validator_never_turns_unknown_into_pass(service, request):
    receipt = service.validate(request, checks=[unknown_check("VAL_EVIDENCE_MISSING")])
    assert receipt.verdict == ValidationVerdict.UNKNOWN

def test_receipt_is_canonical_and_schema_valid(receipt):
    validate(instance=receipt.model_dump(mode="json"), schema=VALIDATION_SCHEMA)
    assert receipt.digest == sha256_hex(receipt.canonical_bytes_without_digest())
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/validator/test_service.py tests/contract/validator/test_receipt_schema.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'mdcp.validator'`.

- [ ] **Step 3: Implement fixed reason codes and canonical receipts**

Define ordered checks, verdict precedence `QUARANTINE > FAIL > UNKNOWN > PASS`, sanitized fixed explanations, per-check evidence digests, evidence class, resource limits, and receipt canonicalization. CLI exits 0 only for PASS, 2 for FAIL, 3 for UNKNOWN, and 4 for quarantine/trust failure.

```python
VERDICT_PRECEDENCE = {
    ValidationVerdict.PASS: 0, ValidationVerdict.UNKNOWN: 1,
    ValidationVerdict.FAIL: 2, ValidationVerdict.QUARANTINE: 3,
}
def aggregate_checks(checks: Sequence[ValidationCheck]) -> ValidationVerdict:
    return max((check.verdict for check in checks), key=VERDICT_PRECEDENCE.__getitem__)
```

- [ ] **Step 4: Verify all verdict paths**

Run: `uv run pytest tests/unit/validator/test_service.py tests/contract/validator/test_receipt_schema.py -q`

Expected: PASS/FAIL/UNKNOWN/QUARANTINE fixtures select the exact exit/verdict mapping and schema regeneration has no diff.

- [ ] **Step 5: Commit**

```powershell
git add schemas/v1/validation-receipt.schema.json src/mdcp/validator tests/unit/validator tests/contract/validator
git commit -m "feat: add fail closed validator receipts"
```

### Task 2.2: Enforce artifact, archive, and ONNX safety policy

**Files:**
- Create: `src/mdcp/validator/onnx_checks.py`
- Create: `src/mdcp/validator/identity_checks.py`
- Create: `src/mdcp/validator/policy.py`
- Create: `configs/policy/onnx-operators-v1.json`
- Create: `configs/policy/validation-v1.json`
- Test: `tests/unit/validator/test_identity_checks.py`
- Test: `tests/unit/validator/test_onnx_checks.py`
- Test: `tests/security/validator/test_archive_attacks.py`
- Test: `tests/fixtures/artifacts/adversarial/fixture-index.json`

**Interfaces:**
- Consumes: staged files, descriptor, frozen operator allowlist, byte/file/time limits.
- Produces: `validate_identity(root, descriptor) -> Sequence[ValidationCheck]`, `validate_onnx(path, policy) -> OnnxValidationResult`, and fixed codes `VAL_DIGEST_MISMATCH`, `VAL_FORBIDDEN_FORMAT`, `VAL_ONNX_OPERATOR`, `VAL_PATH_ESCAPE`, `VAL_RESOURCE_LIMIT`.

- [ ] **Step 1: Write failing adversarial tests**

```python
@pytest.mark.parametrize("fixture,code", [
    ("pickle.bin", "VAL_FORBIDDEN_FORMAT"),
    ("external-parent.onnx", "VAL_PATH_ESCAPE"),
    ("unsupported-op.onnx", "VAL_ONNX_OPERATOR"),
])
def test_adversarial_artifact_fails_closed(validate_fixture, fixture, code):
    assert code in validate_fixture(fixture).reason_codes
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/validator/test_identity_checks.py tests/unit/validator/test_onnx_checks.py tests/security/validator/test_archive_attacks.py -q`

Expected: FAIL because the safety checks are undefined.

- [ ] **Step 3: Implement bounded static and smoke checks**

Recompute descriptor/content hashes; reject pickle/joblib/marshal/executable archives, tags without digest, absolute/parent/link/duplicate archive entries, multiple model files, oversized/file-count violations, unsupported ops/opset/shapes, external-data escapes, and non-finite/negative smoke outputs. The allowlist is read-only source and cannot auto-expand from candidate input.

```python
def validate_archive(entries: Sequence[ArchiveEntry], policy: ValidationPolicy) -> None:
    normalized: set[PurePosixPath] = set()
    for entry in entries:
        path = PurePosixPath(entry.name)
        if path.is_absolute() or ".." in path.parts or entry.is_link or path in normalized:
            raise QuarantineError("unsafe archive member")
        normalized.add(path)
    enforce_file_count_and_bytes(entries, policy)
```

- [ ] **Step 4: Verify the adversarial matrix**

Run: `uv run pytest tests/unit/validator/test_identity_checks.py tests/unit/validator/test_onnx_checks.py tests/security/validator/test_archive_attacks.py -q`

Expected: every named attack maps to its fixed reason code; the stable/candidate fixtures pass; no raw path or exception string appears in receipts.

- [ ] **Step 5: Commit**

```powershell
git add configs/policy src/mdcp/validator tests/unit/validator tests/security/validator tests/fixtures/artifacts/adversarial
git commit -m "feat: enforce artifact validation policy"
```

### Task 2.3: Define supply-chain evidence and the final release identity

**Files:**
- Modify: `src/mdcp/contracts/release.py`
- Create: `src/mdcp/validator/supply_chain.py`
- Create: `schemas/v1/final-release-manifest.schema.json`
- Create: `schemas/v1/release-ci-bundle-index.schema.json`
- Create: `constraints/runtime-licenses.txt`
- Test: `tests/unit/contracts/test_final_manifest.py`
- Test: `tests/unit/validator/test_supply_chain.py`
- Test: `tests/contract/validator/test_release_schemas.py`
- Test: `tests/fixtures/supply-chain/valid/sbom.spdx.json`
- Test: `tests/fixtures/supply-chain/valid/provenance.json`
- Test: `tests/fixtures/supply-chain/valid/attestation.json`
- Test: `tests/fixtures/supply-chain/valid/vulnerability-scan.json`
- Test: `tests/fixtures/supply-chain/valid/final-release-manifest.json`
- Test: `tests/fixtures/supply-chain/valid/validation-receipt.json`
- Test: `tests/fixtures/supply-chain/valid/bundle-index.json`
- Test: `tests/fixtures/supply-chain/adversarial/fixture-index.json`

**Interfaces:**
- Consumes: OCI repository/digest, SBOM/provenance/attestation/scan documents, Wave 1 lineage/evaluation/policy digests.
- Produces: `FinalReleaseManifest`, `BundleMember`, `ReleaseCIBundleIndex`, `release_id(manifest: FinalReleaseManifest) -> str`, and `verify_supply_chain(evidence, policy) -> Sequence[ValidationCheck]`.

- [ ] **Step 1: Write failing acyclic-identity and trust tests**

```python
def test_release_id_changes_without_bake_back(manifest):
    release_id = compute_release_id(manifest)
    assert manifest.oci.digest.startswith("sha256:")
    assert "release_id" not in manifest.identity_material()
    assert manifest.image_descriptor.release_id is None
    assert release_id == sha256_hex(manifest.canonical_bytes_without_release_id())

def test_wrong_attestation_subject_is_quarantine(checker, evidence):
    evidence.attestation.subject_digest = "sha256:" + "0" * 64
    assert checker(evidence).verdict == ValidationVerdict.QUARANTINE
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/contracts/test_final_manifest.py tests/unit/validator/test_supply_chain.py tests/contract/validator/test_release_schemas.py -q`

Expected: FAIL because final manifest and supply-chain types are missing.

- [ ] **Step 3: Implement final identity and dated policy checks**

Bind every field required by spec §9.2; canonicalize without `release_id`; reject mutable OCI references, wrong repository/workflow/commit/subject, SBOM/provenance subject mismatch, critical vulnerability, unexcepted high vulnerability, unknown license, expired scan, and exceptions beyond 30 days. The bundle inventory contains path/media type/size/SHA-256 and excludes its own digest.

```python
def release_id(manifest: FinalReleaseManifest) -> str:
    fields = manifest.model_dump(mode="json", exclude={"release_id"})
    return "sha256:" + sha256_hex(canonicalize_json(fields))

class BundleMember(BaseModel):
    path: SafeRelativePath
    media_type: str
    size_bytes: NonNegativeInt
    sha256: Sha256
```

- [ ] **Step 4: Verify tamper/no-cycle/schema behavior**

Run: `uv run pytest tests/unit/contracts/test_final_manifest.py tests/unit/validator/test_supply_chain.py tests/contract/validator/test_release_schemas.py -q`

Expected: valid fixture passes; each subject/digest/license/time mutation fails with the expected trust code; rebuilding an image is absent from manifest creation; schemas regenerate without diff.

- [ ] **Step 5: Commit**

```powershell
git add constraints/runtime-licenses.txt schemas/v1 src/mdcp/contracts/release.py src/mdcp/validator/supply_chain.py tests/unit/contracts tests/unit/validator tests/contract/validator tests/fixtures/supply-chain
git commit -m "feat: define final release identity"
```

### Task 2.4: Implement sealed bundle and offline verification boundaries

**Files:**
- Create: `src/mdcp/verify/bundle.py`
- Create: `src/mdcp/verify/cli.py`
- Test: `tests/unit/verify/test_bundle.py`
- Test: `tests/contract/validator/test_evidence_labels.py`
- Test: `tests/integration/validator/test_offline_bundle.py`

**Interfaces:**
- Consumes: final manifest, validation receipt, and staged supply-chain member files.
- Produces: `seal_bundle(root: Path) -> ReleaseCIBundleIndex`, `verify_bundle(root: Path, online: bool = False) -> VerificationResult`, and CLI grammar `python -m mdcp.verify.cli bundle --root BUNDLE_DIRECTORY --offline`.

- [ ] **Step 1: Write failing inventory/tamper/claim tests**

```python
def test_offline_verifier_does_not_claim_online_identity(valid_bundle):
    result = verify_bundle(valid_bundle, online=False)
    assert result.verdict == GateVerdict.PASS
    assert result.evidence_class == EvidenceClass.REVIEWER_LOCALLY_RECOMPUTED
    assert result.live_ghcr_verified is False
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/unit/verify/test_bundle.py tests/contract/validator/test_evidence_labels.py tests/integration/validator/test_offline_bundle.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'mdcp.verify'`.

- [ ] **Step 3: Implement canonical inventory and offline verifier**

Sort member paths, reject links/traversal/duplicates/unlisted files, recompute sizes/digests/manifest release ID/receipt digest, and preserve `release_ci_verified` versus `reviewer_locally_recomputed`. Offline mode performs no DNS/HTTP/GHCR/GitHub calls and explicitly reports live identity as not re-established.

```python
def verify_bundle(root: Path, online: bool = False) -> VerificationResult:
    index = load_strict_index(root / "bundle-index.json")
    reject_unlisted_or_linked_members(root, index)
    checks = [verify_member(root, member) for member in index.members]
    checks.extend(verify_identity_chain(root, index))
    return VerificationResult(checks=checks, live_identity_reestablished=online)
```

- [ ] **Step 4: Verify offline operation and tamper failure**

Run: `uv run pytest tests/unit/verify/test_bundle.py tests/contract/validator/test_evidence_labels.py tests/integration/validator/test_offline_bundle.py -q`

Expected: valid bundle passes with offline label; modified, omitted, added, or renamed member fails; network-call sentinel remains zero.

- [ ] **Step 5: Commit**

```powershell
git add src/mdcp/verify tests/unit/verify tests/contract/validator tests/integration/validator
git commit -m "feat: verify release bundles offline"
```

### Task 2.5: Prove validator container isolation and MLflow numeric boundary

**Files:**
- Create: `docker/validator.Dockerfile`
- Test: `tests/integration/validator/test_validator_container.py`
- Test: `tests/integration/validator/test_mlflow_snapshot.py`
- Test: `tests/security/validator/test_container_boundary.py`
- Create: `docs/threat-model.md`
- Modify: `compose.feasibility.yaml`

**Interfaces:**
- Consumes: staged read-only bundle, numeric `MLflowVersionSnapshot`, validation policy.
- Produces: ephemeral Compose profile `validator`, validation receipt file, and documented trust-zone assertions.

- [ ] **Step 1: Write failing isolation assertions**

```python
def test_validator_boundary(container_inspect, network_sentinel):
    assert container_inspect.user != "0"
    assert container_inspect.read_only is True
    assert container_inspect.docker_socket_mounted is False
    assert network_sentinel.calls_after_staging == 0
```

- [ ] **Step 2: Verify red**

Run: `uv run pytest tests/integration/validator/test_validator_container.py tests/integration/validator/test_mlflow_snapshot.py tests/security/validator/test_container_boundary.py -q`

Expected: FAIL because the validator image/profile does not exist.

- [ ] **Step 3: Implement the ephemeral isolation profile**

Build as non-root, drop all capabilities, set `no-new-privileges`, read-only root, bounded tmpfs, CPU/memory/pids/time limits, staged read-only bundle, and an internal network disabled before validation. Snapshot MLflow numeric version before network loss; alias input, changed artifact URI, and digest mismatch fail closed.

```python
@dataclass(frozen=True)
class ContainerSecurity:
    user: str
    read_only: bool
    cap_drop: tuple[str, ...]
    no_new_privileges: bool
    network_mode: Literal["none"]
    memory_mib: PositiveInt
    pids_limit: PositiveInt

VALIDATOR_SECURITY = ContainerSecurity(
    user="10001:10001",
    read_only=True,
    cap_drop=("ALL",),
    no_new_privileges=True,
    network_mode="none",
    memory_mib=384,
    pids_limit=128,
)
```

- [ ] **Step 4: Verify the security and lineage boundary**

Run: `docker compose -f compose.feasibility.yaml --profile validator run --rm validator; uv run pytest tests/integration/validator tests/security/validator -q`

Expected: validator exits 0 on valid fixture and emits PASS receipt; alias/mismatch/egress/socket/root/write attempts fail their tests; container exits after one job.

- [ ] **Step 5: Commit**

```powershell
git add docker/validator.Dockerfile compose.feasibility.yaml docs/threat-model.md tests/integration/validator tests/security/validator
git commit -m "test: isolate candidate validation"
```

### Task 2.6: Build, verify, and commit the dispatchable release-CI workflow

**Files:**
- Create: `.github/workflows/release-ci.yml`
- Create: `constraints/github-actions.lock`
- Create: `scripts/release-ci-local.ps1`
- Test: `tests/publication/test_release_workflow.py`
- Modify: `docs/research/github-supply-chain-capability.md`

**Interfaces:**
- Consumes: Wave 0 official capability research, Wave 1 image context/descriptor, Wave 2 validator/sealer, and formal repository identity `kuotunyu/model-delivery-control-plane`.
- Produces: committed pinned `release-ci.yml`, full-SHA action lock, local `dev/test` runner, and workflow-order/permission tests; it performs no login, push, attestation, repository creation, or dispatch.

- [ ] **Step 1: Write failing workflow-order and permission tests**

```python
def test_release_workflow_is_pinned_and_acyclic(workflow):
    assert workflow.permissions == {"contents": "read", "packages": "write",
                                    "id-token": "write", "attestations": "write"}
    assert workflow.order == ["build_push", "supply_chain", "final_manifest", "validate", "seal"]
    assert all(ref.is_full_commit_sha for ref in workflow.action_refs)
    assert "rebuild_after_manifest" not in workflow.jobs
```

- [ ] **Step 2: Verify red locally without a remote**

Run: `uv run pytest tests/publication/test_release_workflow.py -q; pwsh ./scripts/release-ci-local.ps1 -Mode ValidateOnly`

Expected: pytest FAIL because workflow and lock are absent; PowerShell exits nonzero because the script is absent.

- [ ] **Step 3: Implement the pinned workflow and local dry-run**

Consume full action SHAs from `constraints/github-actions.lock`; use BuildKit push output digest as the sole OCI subject, attach SPDX/provenance, create GitHub artifact attestation for that digest, scan, derive final manifest, run validator, and seal bundle. Secrets use GitHub credentials/secret mounts, never build args. Local mode builds/test-validates only and labels output `dev/test`.

```python
def release_workflow_actions(lock: Mapping[str, str]) -> dict[str, str]:
    names = ("actions/checkout", "docker/build-push-action",
             "actions/attest-build-provenance", "actions/upload-artifact")
    selected = {name: lock[name] for name in names}
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in selected.values()):
        raise WorkflowPolicyError("action reference is not a full commit SHA")
    return selected
```

- [ ] **Step 4: Verify the complete local workflow contract without mutation**

Run: `uv run pytest tests/publication/test_release_workflow.py -q; pwsh ./scripts/release-ci-local.ps1 -Mode ValidateOnly`

Expected: tests pass; local verifier prints `RELEASE-CI LOCAL PASS evidence_class=dev/test mutations=0`, reports full-SHA actions and the exact five-stage order, and performs no network write.

- [ ] **Step 5: Commit the reviewed workflow before any dispatch**

```powershell
git add .github/workflows/release-ci.yml constraints/github-actions.lock scripts/release-ci-local.ps1 tests/publication/test_release_workflow.py docs/research/github-supply-chain-capability.md
git commit -m "ci: add dispatchable release supply chain"
```

### Task 2.7: Execute release-CI only after A1/A2 and seal recorded evidence

**Files:**
- Modify: `tests/publication/test_release_workflow.py`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/release-inventory.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/release-ci-verification.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/sbom.spdx.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/provenance.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/attestation.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/vulnerability-scan.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/final-release-manifest.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/validation-receipt.json`
- Test: `tests/fixtures/supply-chain/recorded-release-ci/bundle-index.json`

**Interfaces:**
- Consumes: exact clean Task 2.6 commit, owner authorization A1 for repository creation/initial exact-source push, then separate A2 for GHCR push and GitHub attestation generation.
- Produces: real immutable GHCR subject, GitHub attestation, SPDX SBOM, provenance, scan, final manifest, validator receipt, sealed bundle, sanitized recorded fixture, and `release-CI verified` receipt.

- [ ] **Step 1: Extend the test with the missing recorded-evidence assertion**

```python
def test_recorded_release_ci_is_real_and_acyclic(recorded_release_ci):
    assert recorded_release_ci.evidence_class == EvidenceClass.RELEASE_CI_VERIFIED
    assert recorded_release_ci.repository == "kuotunyu/model-delivery-control-plane"
    assert recorded_release_ci.subject.matches_digest_qualified_ghcr_ref()
    assert recorded_release_ci.attestation_verified is True
    assert recorded_release_ci.identity_chain_is_acyclic is True

def test_recorded_release_ci_is_public_safe(recorded_release_ci):
    assert recorded_release_ci.public_safety_findings == ()
```

- [ ] **Step 2: Verify red before any external action**

Run: `uv run pytest tests/publication/test_release_workflow.py::test_recorded_release_ci_is_real_and_acyclic -q`

Expected: FAIL because `tests/fixtures/supply-chain/recorded-release-ci/release-inventory.json` does not exist. No network or remote mutation occurs.

- [ ] **Step 3: Stop for A1, then A2, and acquire exact remote evidence**

First request A1. Only after A1 explicitly authorizes repository creation and the initial reviewed source push, run:

```powershell
$releaseCiCommit = (git rev-parse HEAD).Trim()
gh repo create kuotunyu/model-delivery-control-plane --public --source . --remote origin
git push --set-upstream origin main
```

Verify `git ls-remote origin refs/heads/main` resolves to `$releaseCiCommit`. Stop and request separate A2; only after A2 explicitly authorizes GHCR publication and GitHub attestation generation, run:

```powershell
gh workflow run release-ci.yml --ref main -f expected_commit=$releaseCiCommit
$releaseCiRun = gh run list --workflow release-ci.yml --branch main --event workflow_dispatch --limit 20 --json databaseId,headSha,status,conclusion | ConvertFrom-Json | Where-Object headSha -eq $releaseCiCommit | Select-Object -First 1
gh run watch $releaseCiRun.databaseId --exit-status
gh run download $releaseCiRun.databaseId --name recorded-release-ci --dir tests/fixtures/supply-chain/recorded-release-ci
```

If either authorization is absent, record `BLOCKED_EXTERNAL_AUTHORIZATION` and stop Wave 2. If the selected run's `headSha` differs, stop without accepting or relabeling its evidence.

- [ ] **Step 4: Verify green, secret safety, and evidence semantics**

Run: `uv run pytest tests/publication/test_release_workflow.py -q; uv run python -m mdcp.verify.cli bundle --root tests/fixtures/supply-chain/recorded-release-ci --offline`

Expected: tests pass; online receipt starts `RELEASE-CI PASS repository=kuotunyu/model-delivery-control-plane`, reports `attestation=verified`, and its subject matches `^ghcr.io/kuotunyu/model-delivery-control-plane@sha256:[0-9a-f]{64}$`; offline verifier reports `live_identity_reestablished=false`; scan reports `credentials=0 private_paths=0 raw_payloads=0`.

- [ ] **Step 5: Commit only the sanitized recorded fixture and assertion**

```powershell
git add tests/publication/test_release_workflow.py tests/fixtures/supply-chain/recorded-release-ci
git commit -m "test: record verified release ci evidence"
```

## Wave 2 completion checkpoint

Run: `uv run pytest tests/unit/validator tests/unit/contracts tests/unit/verify tests/contract/validator tests/integration/validator tests/security/validator tests/publication/test_release_workflow.py -q; uv run python -m mdcp.verify.cli bundle --root tests/fixtures/supply-chain/recorded-release-ci --offline; git status --short`

Expected: all local tests pass, offline verifier recomputes the recorded real release-CI bundle with the correct evidence-class limitation, real online receipt is present from the owner-authorized workflow, secrets scan is empty, and the worktree is clean. If real GHCR/attestation evidence is absent, Wave 2 is not M2-complete and Wave 3 must not start.
