from __future__ import annotations

from datetime import date, timedelta

from mdcp.common.enums import ValidationVerdict
from mdcp.contracts.release import OciSubject
from mdcp.validator.service import ReasonCode
from mdcp.validator.supply_chain import (
    AttestationEvidence,
    LicenseException,
    PackageEvidence,
    ProvenanceEvidence,
    SbomEvidence,
    ScanEvidence,
    SupplyChainEvidence,
    SupplyChainPolicy,
    VulnerabilityException,
    VulnerabilityFinding,
    verify_supply_chain,
)

SUBJECT = OciSubject(
    repository="ghcr.io/kuotunyu/model-delivery-control-plane",
    digest="sha256:" + "a" * 64,
)


def _policy() -> SupplyChainPolicy:
    return SupplyChainPolicy(
        expected_repository="kuotunyu/model-delivery-control-plane",
        expected_workflow=".github/workflows/release-ci.yml",
        expected_commit="b" * 40,
        verification_date=date(2026, 8, 24),
        scan_max_age_days=7,
        exception_max_days=30,
        allowed_licenses=(
            "Apache-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
            "MIT",
            "MPL-2.0",
            "PSF-2.0",
        ),
    )


def _evidence() -> SupplyChainEvidence:
    return SupplyChainEvidence(
        subject=SUBJECT,
        sbom=SbomEvidence(
            spdx_version="SPDX-2.3",
            subject=SUBJECT,
            packages=(PackageEvidence(name="onnxruntime", version="1.22.1", license="MIT"),),
        ),
        provenance=ProvenanceEvidence(
            subject=SUBJECT,
            repository="kuotunyu/model-delivery-control-plane",
            workflow=".github/workflows/release-ci.yml",
            commit_sha="b" * 40,
            builder="https://github.com/actions/runner",
        ),
        attestation=AttestationEvidence(
            subject=SUBJECT,
            repository="kuotunyu/model-delivery-control-plane",
            workflow=".github/workflows/release-ci.yml",
            commit_sha="b" * 40,
            verified=True,
        ),
        scan=ScanEvidence(
            subject=SUBJECT,
            generated_on=date(2026, 8, 24),
            vulnerabilities=(),
            vulnerability_exceptions=(),
            license_exceptions=(),
        ),
    )


def _verdict(checks, code: ReasonCode) -> ValidationVerdict:
    return next(check.verdict for check in checks if check.code is code)


def test_valid_supply_chain_evidence_passes_every_policy_check() -> None:
    checks = verify_supply_chain(_evidence(), _policy())

    assert all(check.verdict is ValidationVerdict.PASS for check in checks)


def test_wrong_attestation_subject_is_quarantine() -> None:
    evidence = _evidence()
    wrong_subject = SUBJECT.model_copy(update={"digest": "sha256:" + "0" * 64})
    evidence = evidence.model_copy(
        update={"attestation": evidence.attestation.model_copy(update={"subject": wrong_subject})}
    )

    checks = verify_supply_chain(evidence, _policy())

    assert _verdict(checks, ReasonCode.VAL_SUBJECT_MISMATCH) is ValidationVerdict.QUARANTINE


def test_wrong_repository_workflow_or_commit_is_quarantine() -> None:
    evidence = _evidence()
    evidence = evidence.model_copy(
        update={
            "attestation": evidence.attestation.model_copy(
                update={"repository": "attacker/repo", "workflow": "evil.yml"}
            )
        }
    )

    checks = verify_supply_chain(evidence, _policy())

    assert _verdict(checks, ReasonCode.VAL_TRUST_FAILURE) is ValidationVerdict.QUARANTINE


def test_critical_and_unexcepted_high_vulnerabilities_fail() -> None:
    for severity in ("CRITICAL", "HIGH"):
        evidence = _evidence()
        finding = VulnerabilityFinding(
            identifier="CVE-2026-0001",
            severity=severity,
            package="onnxruntime",
            affected_version="1.22.1",
        )
        evidence = evidence.model_copy(
            update={"scan": evidence.scan.model_copy(update={"vulnerabilities": (finding,)})}
        )

        checks = verify_supply_chain(evidence, _policy())

        assert _verdict(checks, ReasonCode.VAL_VULNERABILITY) is ValidationVerdict.FAIL


def test_high_vulnerability_requires_matching_unexpired_complete_exception() -> None:
    evidence = _evidence()
    finding = VulnerabilityFinding(
        identifier="CVE-2026-0001",
        severity="HIGH",
        package="onnxruntime",
        affected_version="1.22.1",
    )
    exception = VulnerabilityException(
        identifier=finding.identifier,
        package=finding.package,
        affected_version=finding.affected_version,
        technical_rationale="The vulnerable code path is not reachable.",
        owner="release-owner",
        compensating_control="The isolated validator rejects the affected input.",
        expires_on=_policy().verification_date + timedelta(days=30),
    )
    scan = evidence.scan.model_copy(
        update={
            "vulnerabilities": (finding,),
            "vulnerability_exceptions": (exception,),
        }
    )

    checks = verify_supply_chain(evidence.model_copy(update={"scan": scan}), _policy())

    assert _verdict(checks, ReasonCode.VAL_VULNERABILITY) is ValidationVerdict.PASS


def test_exception_beyond_thirty_days_fails() -> None:
    evidence = _evidence()
    exception = VulnerabilityException(
        identifier="CVE-2026-0001",
        package="onnxruntime",
        affected_version="1.22.1",
        technical_rationale="The vulnerable code path is not reachable.",
        owner="release-owner",
        compensating_control="The isolated validator rejects the affected input.",
        expires_on=_policy().verification_date + timedelta(days=31),
    )
    scan = evidence.scan.model_copy(update={"vulnerability_exceptions": (exception,)})

    checks = verify_supply_chain(evidence.model_copy(update={"scan": scan}), _policy())

    assert _verdict(checks, ReasonCode.VAL_VULNERABILITY) is ValidationVerdict.FAIL


def test_unknown_runtime_license_fails() -> None:
    evidence = _evidence()
    sbom = evidence.sbom.model_copy(
        update={
            "packages": (
                PackageEvidence(name="mystery", version="1.0", license="NOASSERTION"),
            )
        }
    )

    checks = verify_supply_chain(evidence.model_copy(update={"sbom": sbom}), _policy())

    assert _verdict(checks, ReasonCode.VAL_LICENSE) is ValidationVerdict.FAIL


def test_unknown_runtime_license_can_use_matching_dated_exception() -> None:
    evidence = _evidence()
    package = PackageEvidence(name="mystery", version="1.0", license="NOASSERTION")
    sbom = evidence.sbom.model_copy(update={"packages": (package,)})
    exception = LicenseException(
        package=package.name,
        version=package.version,
        license=package.license,
        technical_rationale="Upstream has not classified this generated metadata.",
        owner="release-owner",
        compensating_control="Distribution remains disabled pending classification.",
        expires_on=_policy().verification_date + timedelta(days=7),
    )
    scan = evidence.scan.model_copy(update={"license_exceptions": (exception,)})

    checks = verify_supply_chain(
        evidence.model_copy(update={"sbom": sbom, "scan": scan}), _policy()
    )

    assert _verdict(checks, ReasonCode.VAL_LICENSE) is ValidationVerdict.PASS


def test_expired_scan_fails() -> None:
    evidence = _evidence()
    old_scan = evidence.scan.model_copy(update={"generated_on": date(2026, 8, 16)})

    checks = verify_supply_chain(evidence.model_copy(update={"scan": old_scan}), _policy())

    assert _verdict(checks, ReasonCode.VAL_SCAN_EXPIRED) is ValidationVerdict.FAIL
