"""Command-line surface for the bounded temporal runner.

Formal authorization and real bounded-development loading are deliberately out of scope for this
task.  The commands are registered now but fail closed until those later gates supply a context.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mdcp-temporal")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run-development")
    replay = commands.add_parser("replay-provisional")
    replay.add_argument("--provisional-id", required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(arguments)
    print("FORMAL_RUN_CONTEXT_REQUIRED")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
