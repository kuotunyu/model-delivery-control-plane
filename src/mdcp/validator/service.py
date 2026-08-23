from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import EvidenceClass, ValidationVerdict
from mdcp.contracts.release import ArtifactDescriptor, artifact_descriptor_digest
from mdcp.validator.isolation import ValidatorResourceLimits
from mdcp.validator.policy import ValidationPolicy

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ReasonCode(StrEnum):
    VAL_OK = "VAL_OK"
    VAL_EVIDENCE_MISSING = "VAL_EVIDENCE_MISSING"
    VAL_DIGEST_MISMATCH = "VAL_DIGEST_MISMATCH"
    VAL_FORBIDDEN_FORMAT = "VAL_FORBIDDEN_FORMAT"
    VAL_ONNX_OPERATOR = "VAL_ONNX_OPERATOR"
    VAL_ONNX_INVALID = "VAL_ONNX_INVALID"
    VAL_PATH_ESCAPE = "VAL_PATH_ESCAPE"
    VAL_RESOURCE_LIMIT = "VAL_RESOURCE_LIMIT"
    VAL_IDENTITY_INVALID = "VAL_IDENTITY_INVALID"
    VAL_TRUST_FAILURE = "VAL_TRUST_FAILURE"
    VAL_SUBJECT_MISMATCH = "VAL_SUBJECT_MISMATCH"
    VAL_LICENSE = "VAL_LICENSE"
    VAL_VULNERABILITY = "VAL_VULNERABILITY"
    VAL_SCAN_EXPIRED = "VAL_SCAN_EXPIRED"
    VAL_RECEIPT_INVALID = "VAL_RECEIPT_INVALID"
    VAL_BUNDLE_TAMPER = "VAL_BUNDLE_TAMPER"


FIXED_EXPLANATIONS: dict[ReasonCode, str] = {
    ReasonCode.VAL_OK: "validation check passed",
    ReasonCode.VAL_EVIDENCE_MISSING: "required validation evidence is missing",
    ReasonCode.VAL_DIGEST_MISMATCH: "artifact digest does not match its descriptor",
    ReasonCode.VAL_FORBIDDEN_FORMAT: "artifact format is not allowed",
    ReasonCode.VAL_ONNX_OPERATOR: "ONNX graph contains an operator outside policy",
    ReasonCode.VAL_ONNX_INVALID: "ONNX graph or smoke output is invalid",
    ReasonCode.VAL_PATH_ESCAPE: "artifact member violates the staging boundary",
    ReasonCode.VAL_RESOURCE_LIMIT: "artifact exceeds a fixed validation resource limit",
    ReasonCode.VAL_IDENTITY_INVALID: "release identity material is invalid",
    ReasonCode.VAL_TRUST_FAILURE: "supply-chain trust verification failed",
    ReasonCode.VAL_SUBJECT_MISMATCH: "supply-chain evidence subject does not match",
    ReasonCode.VAL_LICENSE: "runtime license policy is not satisfied",
    ReasonCode.VAL_VULNERABILITY: "vulnerability policy is not satisfied",
    ReasonCode.VAL_SCAN_EXPIRED: "vulnerability evidence is outside its validity window",
    ReasonCode.VAL_RECEIPT_INVALID: "validation receipt identity is invalid",
    ReasonCode.VAL_BUNDLE_TAMPER: "sealed bundle inventory does not match its members",
}
CHECK_ORDER = {code: index for index, code in enumerate(ReasonCode)}
VERDICT_PRECEDENCE = {
    ValidationVerdict.PASS: 0,
    ValidationVerdict.UNKNOWN: 1,
    ValidationVerdict.FAIL: 2,
    ValidationVerdict.QUARANTINE: 3,
}


class ValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ReasonCode
    verdict: ValidationVerdict
    evidence_digest: Sha256
    explanation: str

    @model_validator(mode="after")
    def explanation_is_fixed(self) -> ValidationCheck:
        if self.explanation != FIXED_EXPLANATIONS[self.code]:
            raise ValueError("validation check must use its fixed explanation")
        return self


class ValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(min_length=1, max_length=128)
    staged_root: Path
    artifact_descriptor_digest: Sha256
    policy_sha256: Sha256
    evidence_class: EvidenceClass
    resource_limits: ValidatorResourceLimits
    descriptor: ArtifactDescriptor | None = Field(default=None, exclude=True)


class ValidationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.validation-receipt.v1"] = (
        "mdcp.validation-receipt.v1"
    )
    request_id: str = Field(min_length=1, max_length=128)
    artifact_descriptor_digest: Sha256
    policy_sha256: Sha256
    evidence_class: EvidenceClass
    resource_limits: ValidatorResourceLimits
    checks: tuple[ValidationCheck, ...]
    verdict: ValidationVerdict
    digest: Sha256

    def canonical_bytes_without_digest(self) -> bytes:
        return canonicalize_json(self.model_dump(mode="json", exclude={"digest"}))

    @model_validator(mode="after")
    def digest_matches_body(self) -> ValidationReceipt:
        if self.digest != sha256_hex(self.canonical_bytes_without_digest()):
            raise ValueError("validation receipt digest mismatch")
        return self


def make_check(
    code: ReasonCode,
    verdict: ValidationVerdict,
    *,
    evidence_digest: str,
) -> ValidationCheck:
    return ValidationCheck(
        code=code,
        verdict=verdict,
        evidence_digest=evidence_digest,
        explanation=FIXED_EXPLANATIONS[code],
    )


def aggregate_checks(checks: Sequence[ValidationCheck]) -> ValidationVerdict:
    if not checks:
        return ValidationVerdict.UNKNOWN
    return max(
        (check.verdict for check in checks),
        key=VERDICT_PRECEDENCE.__getitem__,
    )


class ValidatorService:
    def __init__(self, *, policy: ValidationPolicy | None = None) -> None:
        self.policy = policy

    @staticmethod
    def _coalesce_checks(checks: Sequence[ValidationCheck]) -> tuple[ValidationCheck, ...]:
        grouped: dict[ReasonCode, list[ValidationCheck]] = {}
        for check in checks:
            grouped.setdefault(check.code, []).append(check)
        coalesced: list[ValidationCheck] = []
        for code, same_code in grouped.items():
            verdict = max(
                (check.verdict for check in same_code),
                key=VERDICT_PRECEDENCE.__getitem__,
            )
            evidence_digest = sha256_hex(
                canonicalize_json(sorted(check.evidence_digest for check in same_code))
            )
            coalesced.append(
                make_check(code, verdict, evidence_digest=evidence_digest)
            )
        return tuple(coalesced)

    def _run_policy_checks(self, request: ValidationRequest) -> tuple[ValidationCheck, ...]:
        if self.policy is None or request.descriptor is None:
            return (
                make_check(
                    ReasonCode.VAL_EVIDENCE_MISSING,
                    ValidationVerdict.UNKNOWN,
                    evidence_digest=sha256_hex(b"missing-validator-checks"),
                ),
            )
        from mdcp.validator.identity_checks import validate_identity
        from mdcp.validator.onnx_checks import validate_onnx

        checks = list(
            validate_identity(request.staged_root, request.descriptor, self.policy)
        )
        descriptor_matches = (
            artifact_descriptor_digest(request.descriptor)
            == request.artifact_descriptor_digest
        )
        checks.append(
            make_check(
                ReasonCode.VAL_IDENTITY_INVALID,
                ValidationVerdict.PASS
                if descriptor_matches
                else ValidationVerdict.FAIL,
                evidence_digest=sha256_hex(
                    canonicalize_json({"descriptor_matches": descriptor_matches})
                ),
            )
        )
        onnx_files = tuple(request.staged_root.glob("*.onnx"))
        if len(onnx_files) == 1:
            checks.extend(validate_onnx(onnx_files[0], self.policy).checks)
        else:
            checks.append(
                make_check(
                    ReasonCode.VAL_EVIDENCE_MISSING,
                    ValidationVerdict.UNKNOWN,
                    evidence_digest=sha256_hex(b"missing-single-onnx"),
                )
            )
        return self._coalesce_checks(checks)

    def validate(
        self,
        request: ValidationRequest,
        *,
        checks: Sequence[ValidationCheck] | None = None,
    ) -> ValidationReceipt:
        selected = tuple(checks) if checks is not None else self._run_policy_checks(request)
        codes = [check.code for check in selected]
        if len(codes) != len(set(codes)):
            raise ValueError("duplicate validation check code")
        ordered = tuple(sorted(selected, key=lambda check: CHECK_ORDER[check.code]))
        body = {
            "schema_version": "mdcp.validation-receipt.v1",
            "request_id": request.request_id,
            "artifact_descriptor_digest": request.artifact_descriptor_digest,
            "policy_sha256": request.policy_sha256,
            "evidence_class": request.evidence_class,
            "resource_limits": request.resource_limits,
            "checks": ordered,
            "verdict": aggregate_checks(ordered),
        }
        digest = sha256_hex(
            canonicalize_json(
                {
                    key: value.model_dump(mode="json")
                    if isinstance(value, BaseModel)
                    else [item.model_dump(mode="json") for item in value]
                    if key == "checks"
                    else value.value
                    if isinstance(value, StrEnum)
                    else value
                    for key, value in body.items()
                }
            )
        )
        return ValidationReceipt(**body, digest=digest)
