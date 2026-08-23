from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from mdcp.common.enums import EvidenceClass, ValidationVerdict
from mdcp.validator.cli import exit_code_for
from mdcp.validator.isolation import ValidatorResourceLimits
from mdcp.validator.service import (
    ReasonCode,
    ValidationCheck,
    ValidationRequest,
    ValidatorService,
    aggregate_checks,
    make_check,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def validation_request(tmp_path: Path) -> ValidationRequest:
    staged = tmp_path / "staged"
    staged.mkdir()
    return ValidationRequest(
        request_id="validation-1",
        staged_root=staged,
        artifact_descriptor_digest=_digest("descriptor"),
        policy_sha256=_digest("policy"),
        evidence_class=EvidenceClass.SYNTHETIC_TEST,
        resource_limits=ValidatorResourceLimits(),
    )


@pytest.mark.parametrize(
    ("verdicts", "expected"),
    [
        ([ValidationVerdict.PASS], ValidationVerdict.PASS),
        ([ValidationVerdict.PASS, ValidationVerdict.UNKNOWN], ValidationVerdict.UNKNOWN),
        ([ValidationVerdict.UNKNOWN, ValidationVerdict.FAIL], ValidationVerdict.FAIL),
        ([ValidationVerdict.FAIL, ValidationVerdict.QUARANTINE], ValidationVerdict.QUARANTINE),
    ],
)
def test_aggregate_checks_is_fail_closed(
    verdicts: list[ValidationVerdict], expected: ValidationVerdict
) -> None:
    checks = [
        make_check(ReasonCode.VAL_OK, verdict, evidence_digest=_digest(str(index)))
        for index, verdict in enumerate(verdicts)
    ]

    assert aggregate_checks(checks) is expected


def test_validator_never_turns_unknown_into_pass(
    validation_request: ValidationRequest,
) -> None:
    receipt = ValidatorService().validate(
        validation_request,
        checks=[
            make_check(
                ReasonCode.VAL_EVIDENCE_MISSING,
                ValidationVerdict.UNKNOWN,
                evidence_digest=_digest("missing"),
            )
        ],
    )

    assert receipt.verdict is ValidationVerdict.UNKNOWN
    assert receipt.checks[0].explanation == "required validation evidence is missing"


def test_receipt_digest_covers_canonical_body(
    validation_request: ValidationRequest,
) -> None:
    receipt = ValidatorService().validate(
        validation_request,
        checks=[
            make_check(
                ReasonCode.VAL_OK,
                ValidationVerdict.PASS,
                evidence_digest=_digest("ok"),
            )
        ],
    )

    assert receipt.digest == hashlib.sha256(
        receipt.canonical_bytes_without_digest()
    ).hexdigest()
    with pytest.raises(ValidationError, match="receipt digest mismatch"):
        receipt.__class__.model_validate(
            {**receipt.model_dump(mode="json"), "digest": "0" * 64}
        )


def test_receipt_orders_checks_and_rejects_duplicate_reason_codes(
    validation_request: ValidationRequest,
) -> None:
    receipt = ValidatorService().validate(
        validation_request,
        checks=[
            make_check(
                ReasonCode.VAL_RESOURCE_LIMIT,
                ValidationVerdict.FAIL,
                evidence_digest=_digest("limit"),
            ),
            make_check(
                ReasonCode.VAL_DIGEST_MISMATCH,
                ValidationVerdict.FAIL,
                evidence_digest=_digest("digest"),
            ),
        ],
    )
    assert [check.code for check in receipt.checks] == [
        ReasonCode.VAL_DIGEST_MISMATCH,
        ReasonCode.VAL_RESOURCE_LIMIT,
    ]

    duplicate = make_check(
        ReasonCode.VAL_OK,
        ValidationVerdict.PASS,
        evidence_digest=_digest("duplicate"),
    )
    with pytest.raises(ValueError, match="duplicate validation check code"):
        ValidatorService().validate(
            validation_request,
            checks=[duplicate, duplicate],
        )


def test_fixed_explanation_cannot_leak_exception_or_path() -> None:
    with pytest.raises(ValidationError, match="fixed explanation"):
        ValidationCheck(
            code=ReasonCode.VAL_DIGEST_MISMATCH,
            verdict=ValidationVerdict.FAIL,
            evidence_digest=_digest("bad"),
            explanation="C:\\secret\\model.onnx hash failed: raw exception",
        )


@pytest.mark.parametrize(
    ("verdict", "exit_code"),
    [
        (ValidationVerdict.PASS, 0),
        (ValidationVerdict.FAIL, 2),
        (ValidationVerdict.UNKNOWN, 3),
        (ValidationVerdict.QUARANTINE, 4),
    ],
)
def test_cli_exit_mapping_is_fixed(
    verdict: ValidationVerdict,
    exit_code: int,
) -> None:
    assert exit_code_for(verdict) == exit_code
