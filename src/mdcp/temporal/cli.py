"""Closed command boundary for search verification and one formal-development operation."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from mdcp.common.canonical import canonicalize_json

_THREAD_ENVIRONMENT = {
    "BLIS_NUM_THREADS": "1",
    "LOKY_MAX_CPU_COUNT": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
}
os.environ["BLIS_NUM_THREADS"] = "1"
os.environ["LOKY_MAX_CPU_COUNT"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

from mdcp.temporal import run_evidence  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    class ClosedParser(argparse.ArgumentParser):
        def error(self, message: str) -> None:
            del message
            raise ValueError("FORMAL_RUN_REQUEST_INVALID")

    parser = ClosedParser(prog="mdcp-temporal", add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run-development", add_help=False)
    run.add_argument("--expected-freeze-head", required=True)
    run.add_argument("--search-receipt", type=Path, required=True)
    run.add_argument("--evidence-index", type=Path, required=True)
    run.add_argument(
        "--authorization-env",
        choices=("MDCP_FORMAL_RUN_AUTHORIZATION",),
        required=True,
    )
    run.add_argument(
        "--consumption-root-env",
        choices=("MDCP_FORMAL_RUN_CONSUMPTION_ROOT",),
        required=True,
    )
    run.add_argument("--archive-env", choices=("MDCP_UCI_ARCHIVE",), required=True)
    run.add_argument(
        "--private-container-env",
        choices=("MDCP_V02_PRIVATE_CONTAINER",),
        required=True,
    )
    verify = commands.add_parser("verify-search-freeze", add_help=False)
    verify.add_argument("--receipt", type=Path, required=True)
    verify.add_argument("--index", type=Path, required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        parsed = build_parser().parse_args(arguments)
    except (SystemExit, ValueError):
        document = {
            "reason_code": "FORMAL_RUN_REQUEST_INVALID",
            "schema_version": "mdcp.formal-run-cli-result.v1",
            "verdict": "FAIL",
        }
        try:
            sys.stdout.buffer.write(canonicalize_json(document) + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            return 4
        return 2

    if parsed.command == "verify-search-freeze":
        from mdcp.temporal.search_identity import verify_search_freeze

        check = verify_search_freeze(Path.cwd(), parsed.receipt, parsed.index)
        document = {
            "reason_code": check.reason_codes[0],
            "schema_version": "mdcp.search-freeze-cli-result.v1",
            "verdict": check.verdict,
        }
        try:
            sys.stdout.buffer.write(canonicalize_json(document) + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            return 4
        return 0 if check.verdict == "PASS" else 2

    authorization = os.getenv("MDCP_FORMAL_RUN_AUTHORIZATION")
    consumption_root = os.getenv("MDCP_FORMAL_RUN_CONSUMPTION_ROOT")
    archive = os.getenv("MDCP_UCI_ARCHIVE")
    private_container = os.getenv("MDCP_V02_PRIVATE_CONTAINER")
    if any(
        type(value) is not str or not value
        for value in (authorization, consumption_root, archive, private_container)
    ):
        outcome = run_evidence.FormalDevelopmentOutcome(
            verdict="FAIL",
            reason_codes=("FORMAL_RUN_REQUEST_INVALID",),
            private_identity=None,
            seal_record_sha256=None,
            repository_inventory_sha256=None,
            authorization_sha256="0" * 64,
            consumption_marker_sha256=None,
            fit_count=0,
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
        )
    else:
        request = run_evidence.FormalDevelopmentRequest(
            repository_root=Path.cwd(),
            expected_freeze_head=parsed.expected_freeze_head,
            search_receipt_path=parsed.search_receipt,
            evidence_index_path=parsed.evidence_index,
            authorization_path=Path(authorization),
            consumption_root=Path(consumption_root),
            archive_path=Path(archive),
            private_container_path=Path(private_container),
        )
        outcome = run_evidence.execute_authorized_formal_development(request)
    if outcome.verdict == "PASS":
        document = {
            "repository_inventory_sha256": outcome.repository_inventory_sha256,
            "schema_version": "mdcp.formal-seal-custody.v1",
            "seal_record_sha256": outcome.seal_record_sha256,
        }
        exit_code = 0
    else:
        document = {
            "reason_code": outcome.reason_codes[0],
            "schema_version": "mdcp.formal-run-cli-result.v1",
            "verdict": outcome.verdict,
        }
        exit_code = 2 if outcome.verdict == "FAIL" else 3
    try:
        sys.stdout.buffer.write(canonicalize_json(document) + b"\n")
        sys.stdout.buffer.flush()
    except Exception:
        return 4
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
