from __future__ import annotations

import json
from pathlib import Path

from mdcp.validator.service import ValidationReceipt

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA_PATH = REPOSITORY_ROOT / "schemas" / "v1" / "validation-receipt.schema.json"


def test_checked_in_validation_receipt_schema_matches_pydantic() -> None:
    checked_in = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert checked_in == ValidationReceipt.model_json_schema()
    assert checked_in["additionalProperties"] is False


def test_real_receipt_fixture_is_schema_valid(tmp_path: Path) -> None:
    from mdcp.common.enums import EvidenceClass, ValidationVerdict
    from mdcp.validator.isolation import ValidatorResourceLimits
    from mdcp.validator.service import (
        ReasonCode,
        ValidationRequest,
        ValidatorService,
        make_check,
    )

    staged = tmp_path / "staged"
    staged.mkdir()
    request = ValidationRequest(
        request_id="schema-1",
        staged_root=staged,
        artifact_descriptor_digest="a" * 64,
        policy_sha256="b" * 64,
        evidence_class=EvidenceClass.SYNTHETIC_TEST,
        resource_limits=ValidatorResourceLimits(),
    )
    receipt = ValidatorService().validate(
        request,
        checks=[
            make_check(
                ReasonCode.VAL_OK,
                ValidationVerdict.PASS,
                evidence_digest="c" * 64,
            )
        ],
    )

    parsed = ValidationReceipt.model_validate(receipt.model_dump(mode="json"))
    assert parsed == receipt
