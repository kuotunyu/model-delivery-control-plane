from __future__ import annotations

import argparse
from pathlib import Path

from mdcp.common.enums import GateVerdict
from mdcp.verify.bundle import verify_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mdcp-verify")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bundle = subparsers.add_parser("bundle")
    bundle.add_argument("--root", type=Path, required=True)
    bundle.add_argument("--offline", action="store_true", required=True)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command != "bundle" or not arguments.offline:
        return 2
    result = verify_bundle(arguments.root, online=False)
    print(
        "BUNDLE"
        f" {result.verdict.value}"
        f" evidence_class={result.evidence_class.value}"
        " source_evidence_class="
        f"{result.source_evidence_class.value if result.source_evidence_class else 'unknown'}"
        f" live_ghcr_verified={str(result.live_ghcr_verified).lower()}"
        f" network_requests={result.network_requests}"
    )
    return 0 if result.verdict is GateVerdict.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
