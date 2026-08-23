from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from mdcp.common.digests import sha256_hex
from mdcp.common.enums import EvidenceClass, ValidationVerdict
from mdcp.contracts.release import ArtifactDescriptor, artifact_descriptor_digest
from mdcp.validator.isolation import ValidatorResourceLimits
from mdcp.validator.service import ValidationRequest, ValidatorService

EXIT_CODES = {
    ValidationVerdict.PASS: 0,
    ValidationVerdict.FAIL: 2,
    ValidationVerdict.UNKNOWN: 3,
    ValidationVerdict.QUARANTINE: 4,
}


def exit_code_for(verdict: ValidationVerdict) -> int:
    return EXIT_CODES[verdict]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a staged MDCP release")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--staged-root", required=True, type=Path)
    validate.add_argument("--manifest", required=True, type=Path)
    validate.add_argument("--output", required=True, type=Path)
    validate.add_argument("--policy", type=Path)
    return parser


def _validate(args: argparse.Namespace) -> int:
    descriptor = ArtifactDescriptor.model_validate_json(
        args.manifest.read_text(encoding="utf-8")
    )
    policy_digest = (
        sha256_hex(args.policy.read_bytes())
        if args.policy is not None and args.policy.is_file()
        else sha256_hex(b"missing-validation-policy")
    )
    request = ValidationRequest(
        request_id="validator-cli",
        staged_root=args.staged_root.resolve(strict=True),
        artifact_descriptor_digest=artifact_descriptor_digest(descriptor),
        policy_sha256=policy_digest,
        evidence_class=EvidenceClass.SYNTHETIC_TEST,
        resource_limits=ValidatorResourceLimits(),
    )
    receipt = ValidatorService().validate(request)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return exit_code_for(receipt.verdict)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        return _validate(args)
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
