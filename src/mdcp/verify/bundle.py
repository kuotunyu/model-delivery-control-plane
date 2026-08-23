from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, NonNegativeInt

from mdcp.common.canonical import parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import EvidenceClass, GateVerdict, ValidationVerdict
from mdcp.contracts.release import (
    BundleMember,
    FinalReleaseManifest,
    ReleaseCIBundleIndex,
    release_id,
)
from mdcp.validator.service import ValidationReceipt
from mdcp.validator.supply_chain import (
    AttestationEvidence,
    ProvenanceEvidence,
    SbomEvidence,
    ScanEvidence,
)


class BundleCheckCode(StrEnum):
    INDEX = "INDEX"
    INVENTORY = "INVENTORY"
    RELEASE_IDENTITY = "RELEASE_IDENTITY"
    VALIDATION_RECEIPT = "VALIDATION_RECEIPT"
    SUPPLY_CHAIN_SUBJECT = "SUPPLY_CHAIN_SUBJECT"
    BUNDLE_INVALID = "BUNDLE_INVALID"


CHECK_EXPLANATIONS: dict[BundleCheckCode, str] = {
    BundleCheckCode.INDEX: "bundle index is strict and internally consistent",
    BundleCheckCode.INVENTORY: "bundle members match the sealed inventory",
    BundleCheckCode.RELEASE_IDENTITY: "release identity chain is internally consistent",
    BundleCheckCode.VALIDATION_RECEIPT: "validation receipt is valid and passing",
    BundleCheckCode.SUPPLY_CHAIN_SUBJECT: "supply-chain subjects match the release subject",
    BundleCheckCode.BUNDLE_INVALID: "bundle verification failed closed",
}


class BundleVerificationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: BundleCheckCode
    verdict: GateVerdict
    explanation: str


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: GateVerdict
    evidence_class: Literal[EvidenceClass.REVIEWER_LOCALLY_RECOMPUTED] = (
        EvidenceClass.REVIEWER_LOCALLY_RECOMPUTED
    )
    source_evidence_class: EvidenceClass | None
    live_ghcr_verified: Literal[False] = False
    network_requests: NonNegativeInt = 0
    checks: tuple[BundleVerificationCheck, ...]


def _check(code: BundleCheckCode, verdict: GateVerdict) -> BundleVerificationCheck:
    return BundleVerificationCheck(
        code=code,
        verdict=verdict,
        explanation=CHECK_EXPLANATIONS[code],
    )


def _strict_model(path: Path, model_type):
    document = parse_json_bytes(path.read_bytes())
    if not isinstance(document, dict):
        raise ValueError("JSON contract must be an object")
    return model_type.model_validate(document)


def _member_media_type(path: str) -> str:
    if path == "sbom.spdx.json":
        return "application/spdx+json"
    return "application/json"


def _discover_files(root: Path) -> tuple[Path, ...]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("bundle root must be a concrete directory")
    discovered: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("bundle links are forbidden")
        if path.is_file():
            discovered.append(path)
    return tuple(discovered)


def seal_bundle(root: Path) -> ReleaseCIBundleIndex:
    manifest_path = root / "final-release-manifest.json"
    receipt_path = root / "validation-receipt.json"
    manifest = _strict_model(manifest_path, FinalReleaseManifest)
    receipt = _strict_model(receipt_path, ValidationReceipt)
    if manifest.release_id is None:
        raise ValueError("final manifest must contain its release ID")

    members: list[BundleMember] = []
    for path in _discover_files(root):
        relative = path.relative_to(root).as_posix()
        if relative == "bundle-index.json":
            continue
        payload = path.read_bytes()
        members.append(
            BundleMember(
                path=relative,
                media_type=_member_media_type(relative),
                size_bytes=len(payload),
                sha256=sha256_hex(payload),
            )
        )
    members.sort(key=lambda member: member.path)
    return ReleaseCIBundleIndex(
        evidence_class=receipt.evidence_class,
        release_id=manifest.release_id,
        final_manifest_sha256=sha256_hex(manifest_path.read_bytes()),
        validation_receipt_sha256=sha256_hex(receipt_path.read_bytes()),
        members=tuple(members),
    )


def _verify_inventory(root: Path, index: ReleaseCIBundleIndex) -> None:
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in _discover_files(root)
        if path.relative_to(root).as_posix() != "bundle-index.json"
    }
    expected_paths = {member.path for member in index.members}
    if actual_paths != expected_paths:
        raise ValueError("bundle inventory mismatch")
    for member in index.members:
        path = root / member.path
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root.resolve(strict=True)):
            raise ValueError("bundle member escaped root")
        payload = path.read_bytes()
        if len(payload) != member.size_bytes or sha256_hex(payload) != member.sha256:
            raise ValueError("bundle member identity mismatch")


def _verify_identity_chain(
    root: Path, index: ReleaseCIBundleIndex
) -> tuple[FinalReleaseManifest, ValidationReceipt]:
    manifest_path = root / "final-release-manifest.json"
    receipt_path = root / "validation-receipt.json"
    if sha256_hex(manifest_path.read_bytes()) != index.final_manifest_sha256:
        raise ValueError("manifest digest mismatch")
    if sha256_hex(receipt_path.read_bytes()) != index.validation_receipt_sha256:
        raise ValueError("receipt digest mismatch")

    manifest = _strict_model(manifest_path, FinalReleaseManifest)
    receipt = _strict_model(receipt_path, ValidationReceipt)
    if manifest.release_id is None or manifest.release_id != release_id(manifest):
        raise ValueError("release identity mismatch")
    if index.release_id != manifest.release_id:
        raise ValueError("index release identity mismatch")
    if receipt.artifact_descriptor_digest != manifest.image_descriptor_digest:
        raise ValueError("descriptor identity mismatch")
    if receipt.verdict is not ValidationVerdict.PASS or any(
        check.verdict is not ValidationVerdict.PASS for check in receipt.checks
    ):
        raise ValueError("validation receipt did not pass")
    if index.evidence_class is not receipt.evidence_class:
        raise ValueError("evidence class mismatch")
    return manifest, receipt


def _verify_supply_chain_subjects(root: Path, manifest: FinalReleaseManifest) -> None:
    files_and_digests = (
        ("sbom.spdx.json", manifest.sbom_sha256),
        ("provenance.json", manifest.provenance_sha256),
        ("attestation.json", manifest.attestation_sha256),
        ("vulnerability-scan.json", manifest.scan_receipt_sha256),
    )
    for filename, expected_digest in files_and_digests:
        if sha256_hex((root / filename).read_bytes()) != expected_digest:
            raise ValueError("supply-chain evidence digest mismatch")

    sbom = _strict_model(root / "sbom.spdx.json", SbomEvidence)
    provenance = _strict_model(root / "provenance.json", ProvenanceEvidence)
    attestation = _strict_model(root / "attestation.json", AttestationEvidence)
    scan = _strict_model(root / "vulnerability-scan.json", ScanEvidence)
    if not all(
        subject == manifest.oci
        for subject in (sbom.subject, provenance.subject, attestation.subject, scan.subject)
    ):
        raise ValueError("supply-chain subject mismatch")
    expected_repository = manifest.oci.repository.removeprefix("ghcr.io/")
    if (
        provenance.repository != expected_repository
        or attestation.repository != expected_repository
        or provenance.workflow != ".github/workflows/release-ci.yml"
        or attestation.workflow != ".github/workflows/release-ci.yml"
        or provenance.commit_sha != manifest.git_source_sha
        or attestation.commit_sha != manifest.git_source_sha
        or not attestation.verified
    ):
        raise ValueError("supply-chain trust identity mismatch")


def verify_bundle(root: Path, online: bool = False) -> VerificationResult:
    if online:
        raise ValueError("online identity re-establishment is not implemented")

    source_evidence_class: EvidenceClass | None = None
    try:
        index = _strict_model(root / "bundle-index.json", ReleaseCIBundleIndex)
        source_evidence_class = index.evidence_class
        checks = [_check(BundleCheckCode.INDEX, GateVerdict.PASS)]
        _verify_inventory(root, index)
        checks.append(_check(BundleCheckCode.INVENTORY, GateVerdict.PASS))
        manifest, _receipt = _verify_identity_chain(root, index)
        checks.extend(
            (
                _check(BundleCheckCode.RELEASE_IDENTITY, GateVerdict.PASS),
                _check(BundleCheckCode.VALIDATION_RECEIPT, GateVerdict.PASS),
            )
        )
        _verify_supply_chain_subjects(root, manifest)
        checks.append(_check(BundleCheckCode.SUPPLY_CHAIN_SUBJECT, GateVerdict.PASS))
        return VerificationResult(
            verdict=GateVerdict.PASS,
            source_evidence_class=source_evidence_class,
            checks=tuple(checks),
        )
    except (OSError, ValueError, TypeError):
        return VerificationResult(
            verdict=GateVerdict.FAIL,
            source_evidence_class=source_evidence_class,
            checks=(_check(BundleCheckCode.BUNDLE_INVALID, GateVerdict.FAIL),),
        )
