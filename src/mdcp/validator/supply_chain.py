from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import ValidationVerdict
from mdcp.contracts.release import GitSha, OciSubject
from mdcp.validator.service import ReasonCode, ValidationCheck, make_check


class PackageEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=256)
    version: str = Field(min_length=1, max_length=128)
    license: str = Field(min_length=1, max_length=128)


class SbomEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spdx_version: Literal["SPDX-2.3"]
    subject: OciSubject
    packages: tuple[PackageEvidence, ...]


class ProvenanceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: OciSubject
    repository: str = Field(min_length=1, max_length=256)
    workflow: str = Field(min_length=1, max_length=256)
    commit_sha: GitSha
    builder: str = Field(min_length=1, max_length=512)


class AttestationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: OciSubject
    repository: str = Field(min_length=1, max_length=256)
    workflow: str = Field(min_length=1, max_length=256)
    commit_sha: GitSha
    verified: bool


class VulnerabilityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    identifier: str = Field(min_length=1, max_length=128)
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    package: str = Field(min_length=1, max_length=256)
    affected_version: str = Field(min_length=1, max_length=128)


class VulnerabilityException(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    identifier: str = Field(min_length=1, max_length=128)
    package: str = Field(min_length=1, max_length=256)
    affected_version: str = Field(min_length=1, max_length=128)
    technical_rationale: str = Field(min_length=1, max_length=1024)
    owner: str = Field(min_length=1, max_length=256)
    compensating_control: str = Field(min_length=1, max_length=1024)
    expires_on: date


class LicenseException(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    package: str = Field(min_length=1, max_length=256)
    version: str = Field(min_length=1, max_length=128)
    license: str = Field(min_length=1, max_length=128)
    technical_rationale: str = Field(min_length=1, max_length=1024)
    owner: str = Field(min_length=1, max_length=256)
    compensating_control: str = Field(min_length=1, max_length=1024)
    expires_on: date


class ScanEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: OciSubject
    generated_on: date
    vulnerabilities: tuple[VulnerabilityFinding, ...]
    vulnerability_exceptions: tuple[VulnerabilityException, ...]
    license_exceptions: tuple[LicenseException, ...]


class SupplyChainEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: OciSubject
    sbom: SbomEvidence
    provenance: ProvenanceEvidence
    attestation: AttestationEvidence
    scan: ScanEvidence


class SupplyChainPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_repository: str = Field(min_length=1, max_length=256)
    expected_workflow: str = Field(min_length=1, max_length=256)
    expected_commit: GitSha
    verification_date: date
    scan_max_age_days: int = Field(default=7, ge=1, le=7)
    exception_max_days: int = Field(default=30, ge=1, le=30)
    allowed_licenses: tuple[str, ...]


def _digest(value: object) -> str:
    return sha256_hex(canonicalize_json(value))


def _dated_exception_is_valid(
    expires_on: date, policy: SupplyChainPolicy
) -> bool:
    return (
        policy.verification_date <= expires_on
        <= policy.verification_date + timedelta(days=policy.exception_max_days)
    )


def _high_finding_is_excepted(
    finding: VulnerabilityFinding,
    evidence: ScanEvidence,
    policy: SupplyChainPolicy,
) -> bool:
    return any(
        exception.identifier == finding.identifier
        and exception.package == finding.package
        and exception.affected_version == finding.affected_version
        and _dated_exception_is_valid(exception.expires_on, policy)
        for exception in evidence.vulnerability_exceptions
    )


def _package_license_is_excepted(
    package: PackageEvidence,
    evidence: ScanEvidence,
    policy: SupplyChainPolicy,
) -> bool:
    return any(
        exception.package == package.name
        and exception.version == package.version
        and exception.license == package.license
        and _dated_exception_is_valid(exception.expires_on, policy)
        for exception in evidence.license_exceptions
    )


def verify_supply_chain(
    evidence: SupplyChainEvidence, policy: SupplyChainPolicy
) -> tuple[ValidationCheck, ...]:
    subjects = (
        evidence.sbom.subject,
        evidence.provenance.subject,
        evidence.attestation.subject,
        evidence.scan.subject,
    )
    subjects_match = all(subject == evidence.subject for subject in subjects)

    trust_matches = (
        evidence.provenance.repository == policy.expected_repository
        and evidence.attestation.repository == policy.expected_repository
        and evidence.provenance.workflow == policy.expected_workflow
        and evidence.attestation.workflow == policy.expected_workflow
        and evidence.provenance.commit_sha == policy.expected_commit
        and evidence.attestation.commit_sha == policy.expected_commit
        and evidence.attestation.verified
    )

    scan_age = policy.verification_date - evidence.scan.generated_on
    scan_is_current = timedelta(0) <= scan_age <= timedelta(
        days=policy.scan_max_age_days
    )

    failing_vulnerabilities = tuple(
        finding
        for finding in evidence.scan.vulnerabilities
        if finding.severity == "CRITICAL"
        or (
            finding.severity == "HIGH"
            and not _high_finding_is_excepted(finding, evidence.scan, policy)
        )
    )
    invalid_vulnerability_exceptions = tuple(
        exception
        for exception in evidence.scan.vulnerability_exceptions
        if not _dated_exception_is_valid(exception.expires_on, policy)
    )
    vulnerability_policy_passes = (
        not failing_vulnerabilities and not invalid_vulnerability_exceptions
    )

    failing_licenses = tuple(
        package
        for package in evidence.sbom.packages
        if package.license not in policy.allowed_licenses
        and not _package_license_is_excepted(package, evidence.scan, policy)
    )
    invalid_license_exceptions = tuple(
        exception
        for exception in evidence.scan.license_exceptions
        if not _dated_exception_is_valid(exception.expires_on, policy)
    )
    license_policy_passes = not failing_licenses and not invalid_license_exceptions

    return (
        make_check(
            ReasonCode.VAL_SUBJECT_MISMATCH,
            ValidationVerdict.PASS
            if subjects_match
            else ValidationVerdict.QUARANTINE,
            evidence_digest=_digest({"subjects_match": subjects_match}),
        ),
        make_check(
            ReasonCode.VAL_TRUST_FAILURE,
            ValidationVerdict.PASS
            if trust_matches
            else ValidationVerdict.QUARANTINE,
            evidence_digest=_digest({"trust_matches": trust_matches}),
        ),
        make_check(
            ReasonCode.VAL_SCAN_EXPIRED,
            ValidationVerdict.PASS if scan_is_current else ValidationVerdict.FAIL,
            evidence_digest=_digest(
                {
                    "generated_on": evidence.scan.generated_on.isoformat(),
                    "verification_date": policy.verification_date.isoformat(),
                    "max_age_days": policy.scan_max_age_days,
                }
            ),
        ),
        make_check(
            ReasonCode.VAL_VULNERABILITY,
            ValidationVerdict.PASS
            if vulnerability_policy_passes
            else ValidationVerdict.FAIL,
            evidence_digest=_digest(
                {
                    "failing_finding_count": len(failing_vulnerabilities),
                    "invalid_exception_count": len(
                        invalid_vulnerability_exceptions
                    ),
                }
            ),
        ),
        make_check(
            ReasonCode.VAL_LICENSE,
            ValidationVerdict.PASS if license_policy_passes else ValidationVerdict.FAIL,
            evidence_digest=_digest(
                {
                    "failing_package_count": len(failing_licenses),
                    "invalid_exception_count": len(invalid_license_exceptions),
                }
            ),
        ),
    )
