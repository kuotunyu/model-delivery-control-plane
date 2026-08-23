from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mdcp.common.enums import ValidationVerdict
from mdcp.contracts.release import ArtifactDescriptor, artifact_descriptor_digest
from mdcp.validator.identity_checks import validate_identity
from mdcp.validator.isolation import ValidatorResourceLimits
from mdcp.validator.policy import ValidationPolicy
from mdcp.validator.service import ReasonCode, ValidationRequest, ValidatorService

REPOSITORY_ROOT = Path(__file__).parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "artifacts"


@pytest.fixture
def policy() -> ValidationPolicy:
    return ValidationPolicy.model_validate_json(
        (REPOSITORY_ROOT / "configs" / "policy" / "validation-v1.json").read_text(
            encoding="utf-8"
        )
    )


@pytest.mark.parametrize("role", ["stable", "candidate"])
def test_checked_in_reviewer_artifact_identity_passes(
    role: str,
    policy: ValidationPolicy,
) -> None:
    root = FIXTURE_ROOT / role
    descriptor = ArtifactDescriptor.model_validate_json(
        (root / "artifact-descriptor.json").read_text(encoding="utf-8")
    )

    checks = validate_identity(root, descriptor, policy)

    assert {check.code: check.verdict for check in checks} == {
        ReasonCode.VAL_DIGEST_MISMATCH: ValidationVerdict.PASS,
        ReasonCode.VAL_FORBIDDEN_FORMAT: ValidationVerdict.PASS,
        ReasonCode.VAL_PATH_ESCAPE: ValidationVerdict.PASS,
        ReasonCode.VAL_RESOURCE_LIMIT: ValidationVerdict.PASS,
    }


def test_model_tamper_fails_digest_without_leaking_path(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    root = tmp_path / "candidate"
    shutil.copytree(FIXTURE_ROOT / "candidate", root)
    descriptor = ArtifactDescriptor.model_validate_json(
        (root / "artifact-descriptor.json").read_text(encoding="utf-8")
    )
    (root / "model.onnx").write_bytes((root / "model.onnx").read_bytes() + b"tamper")

    checks = validate_identity(root, descriptor, policy)
    digest_check = next(check for check in checks if check.code is ReasonCode.VAL_DIGEST_MISMATCH)

    assert digest_check.verdict is ValidationVerdict.FAIL
    serialized = json.dumps([check.model_dump(mode="json") for check in checks])
    assert str(tmp_path) not in serialized
    assert "tamper" not in serialized


@pytest.mark.parametrize("filename", ["model.pkl", "weights.joblib", "payload.exe"])
def test_forbidden_runtime_formats_quarantine(
    tmp_path: Path,
    policy: ValidationPolicy,
    filename: str,
) -> None:
    root = tmp_path / "stable"
    shutil.copytree(FIXTURE_ROOT / "stable", root)
    descriptor = ArtifactDescriptor.model_validate_json(
        (root / "artifact-descriptor.json").read_text(encoding="utf-8")
    )
    (root / filename).write_bytes(b"not executable in validator")

    checks = validate_identity(root, descriptor, policy)

    assert next(
        check for check in checks if check.code is ReasonCode.VAL_FORBIDDEN_FORMAT
    ).verdict is ValidationVerdict.QUARANTINE


def test_multiple_onnx_files_are_quarantined(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    root = tmp_path / "stable"
    shutil.copytree(FIXTURE_ROOT / "stable", root)
    descriptor = ArtifactDescriptor.model_validate_json(
        (root / "artifact-descriptor.json").read_text(encoding="utf-8")
    )
    shutil.copy2(root / "model.onnx", root / "second.onnx")

    checks = validate_identity(root, descriptor, policy)

    assert next(
        check for check in checks if check.code is ReasonCode.VAL_FORBIDDEN_FORMAT
    ).verdict is ValidationVerdict.QUARANTINE


def test_validator_service_runs_real_identity_and_onnx_checks(
    policy: ValidationPolicy,
) -> None:
    root = FIXTURE_ROOT / "stable"
    descriptor = ArtifactDescriptor.model_validate_json(
        (root / "artifact-descriptor.json").read_text(encoding="utf-8")
    )
    request = ValidationRequest(
        request_id="real-checks",
        staged_root=root,
        artifact_descriptor_digest=artifact_descriptor_digest(descriptor),
        policy_sha256="8" * 64,
        evidence_class="synthetic_test",
        resource_limits=ValidatorResourceLimits(),
        descriptor=descriptor,
    )

    receipt = ValidatorService(policy=policy).validate(request)

    assert receipt.verdict is ValidationVerdict.PASS
    assert {check.code for check in receipt.checks} == {
        ReasonCode.VAL_OK,
        ReasonCode.VAL_DIGEST_MISMATCH,
        ReasonCode.VAL_FORBIDDEN_FORMAT,
        ReasonCode.VAL_PATH_ESCAPE,
        ReasonCode.VAL_RESOURCE_LIMIT,
        ReasonCode.VAL_IDENTITY_INVALID,
    }
