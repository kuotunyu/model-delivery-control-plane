from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from types import ModuleType

BASELINE_INVALID = "MDCP_REVIEWER_DEMO_BASELINE_INVALID"
CASE_INVALID = "MDCP_REVIEWER_DEMO_CASE_INVALID"
STATE_CHANGED = "MDCP_REVIEWER_DEMO_STATE_CHANGED"
INTERNAL = "MDCP_REVIEWER_DEMO_INTERNAL"
SUCCESS_LINES = (
    "MDCP_DEMO_PASS case=baseline",
    "MDCP_DEMO_REJECT case=remote_release_claim reason=PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID",
    "MDCP_DEMO_REJECT case=public_surface_tamper reason=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH",
    "MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0",
)


class DemoFailure(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ClosedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise DemoFailure(INTERNAL)


def _load_verifier() -> ModuleType:
    path = Path(__file__).with_name("verify-public-release.py")
    spec = importlib.util.spec_from_file_location("mdcp_reviewer_demo_verifier", path)
    if spec is None or spec.loader is None:
        raise DemoFailure(INTERNAL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    original_dont_write_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except Exception:
        raise DemoFailure(INTERNAL) from None
    finally:
        sys.dont_write_bytecode = original_dont_write_bytecode
    return module


def _repository_state(verifier: ModuleType, root: Path) -> bytes:
    return verifier._git(root, "status", "--porcelain=v1", "--untracked-files=all")


def _expect_rejection(
    verifier: ModuleType,
    operation: Callable[[], object],
    expected_reason: str,
) -> None:
    try:
        operation()
    except verifier.PublicReleaseError as error:
        if error.reason_code != expected_reason:
            raise DemoFailure(CASE_INVALID) from None
        return
    except DemoFailure:
        raise
    except Exception:
        raise DemoFailure(INTERNAL) from None
    raise DemoFailure(CASE_INVALID)


def _copy_public_fixture(verifier: ModuleType, root: Path, destination: Path) -> None:
    for logical_path in (*verifier.PUBLIC_SURFACE_PATHS, verifier.READINESS_PATH):
        raw = verifier._read_regular(root, logical_path)
        target = destination.joinpath(*PurePosixPath(logical_path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def _run_cases(verifier: ModuleType, root: Path) -> tuple[str, ...]:
    try:
        readiness = verifier.verify_public_release(root)
    except verifier.PublicReleaseError:
        raise DemoFailure(BASELINE_INVALID) from None

    document = readiness.model_dump(mode="json")
    claim_execution = dict(document["claim_execution"])
    claim_execution["remote_release_executed"] = True
    document["claim_execution"] = claim_execution
    false_claim = verifier.canonicalize_json(document)
    _expect_rejection(
        verifier,
        lambda: verifier.parse_readiness_bytes(false_claim),
        "PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID",
    )

    try:
        with tempfile.TemporaryDirectory(prefix="mdcp-reviewer-demo-") as raw_directory:
            temporary_root = Path(raw_directory)
            _copy_public_fixture(verifier, root, temporary_root)
            readme = temporary_root / "README.md"
            readme.write_bytes(readme.read_bytes() + b"\n<!-- mdcp reviewer demo tamper -->\n")
            _expect_rejection(
                verifier,
                lambda: verifier.verify_public_release(temporary_root),
                "PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH",
            )
    except DemoFailure:
        raise
    except verifier.PublicReleaseError:
        raise DemoFailure(CASE_INVALID) from None
    except Exception:
        raise DemoFailure(INTERNAL) from None

    return SUCCESS_LINES


def run_demo(repository_root: Path) -> tuple[str, ...]:
    verifier = _load_verifier()
    try:
        before = _repository_state(verifier, repository_root)
    except Exception:
        raise DemoFailure(INTERNAL) from None

    failure: DemoFailure | None = None
    lines: tuple[str, ...] = ()
    try:
        lines = _run_cases(verifier, repository_root)
    except DemoFailure as error:
        failure = error
    except Exception:
        failure = DemoFailure(INTERNAL)

    try:
        after = _repository_state(verifier, repository_root)
    except Exception:
        raise DemoFailure(STATE_CHANGED) from None
    if after != before:
        raise DemoFailure(STATE_CHANGED)
    if failure is not None:
        raise failure
    return lines


def _write_error(reason: str) -> None:
    terminal = f"MDCP_REVIEWER_DEMO_FAIL reason={reason}\n"
    if sys.stderr is sys.__stderr__:
        sys.stderr.buffer.write(terminal.encode("utf-8"))
        return
    print(terminal, file=sys.stderr, end="")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = ClosedArgumentParser(add_help=False)
        parser.add_argument("--repository-root", type=Path, default=Path.cwd())
        arguments = parser.parse_args(argv)
        lines = run_demo(arguments.repository_root)
    except DemoFailure as error:
        _write_error(error.reason)
        return 1
    except Exception:
        _write_error(INTERNAL)
        return 1

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
