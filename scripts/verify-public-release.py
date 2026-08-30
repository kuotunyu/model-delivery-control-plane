from __future__ import annotations

import argparse
import re
import stat
import subprocess
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.evidence import public_evidence_violations

FORMAL_CLOSURE_COMMIT = "b1bb0d80cd40e6f39372c0a45892500cc9530712"
FORMAL_CLOSURE_PARENT = "407f68b63c06a17ef54d5ec17722ef1f801b1689"
CORRECTION_COMMIT = "bfe517819ec2163d700519fc427dbe8bb8071258"
SEARCH_RECEIPT_SHA256 = "5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63"
SEARCH_INDEX_SHA256 = "2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205"
READINESS_PATH = "evidence/public/portfolio/local-release-readiness.json"
SCHEMA_PATH = "schemas/portfolio/local-release-readiness.schema.json"
PUBLIC_SURFACE_PATHS = (
    ".github/workflows/portfolio-ci.yml",
    "LICENSE",
    "README.md",
    "docs/architecture.md",
    "docs/reviewer/quickstart.md",
    "docs/reviewer/release-evidence.md",
    "schemas/portfolio/local-release-readiness.schema.json",
    "scripts/reviewer-demo.py",
    "scripts/reviewer-fast-path.ps1",
    "scripts/verify-public-release.py",
)
PUBLIC_MARKDOWN_PATHS = (
    "README.md",
    "docs/architecture.md",
    "docs/reviewer/quickstart.md",
    "docs/reviewer/release-evidence.md",
)
EXPECTED_COMMITS = (
    (
        "1ba0fecc4980ca488a24eb5e19ba3bb080e1a509",
        "504c3058f2b90c04d0f989c2aa6aab37d314b088",
        "D",
    ),
    (
        "915083225e6c2013f06758d29aa4032b54768ccb",
        "1ba0fecc4980ca488a24eb5e19ba3bb080e1a509",
        "A",
    ),
    (
        "bfe517819ec2163d700519fc427dbe8bb8071258",
        "915083225e6c2013f06758d29aa4032b54768ccb",
        "M",
    ),
    (
        "407f68b63c06a17ef54d5ec17722ef1f801b1689",
        "bfe517819ec2163d700519fc427dbe8bb8071258",
        "D",
    ),
    (
        "b1bb0d80cd40e6f39372c0a45892500cc9530712",
        "407f68b63c06a17ef54d5ec17722ef1f801b1689",
        "A",
    ),
)
EVIDENCE_PATHS = (
    "evidence/public/v02/search/evidence-index.json",
    "evidence/public/v02/search/search-receipt.json",
)
CORRECTION_PATHS = (
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/runtime_guards.py",
    "tests/security/temporal/test_data_firewall.py",
    "tests/unit/temporal/test_run_evidence.py",
)
_MARKDOWN_LINK_TARGET = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)")

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
CommitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
PortfolioCiRunUrl = Annotated[
    str,
    StringConstraints(
        pattern=(
            r"^https://github\.com/kuotunyu/model-delivery-control-plane/"
            r"actions/runs/[1-9][0-9]*$"
        )
    ),
]


class PublicReleaseError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicSurfaceEntry(ClosedModel):
    logical_path: str
    byte_size: Annotated[int, Field(ge=0)]
    sha256: Sha256


class TechnicalClosureVerification(ClosedModel):
    full_suite_passed: Literal[1546]
    full_suite_skipped: Literal[7]
    review_critical: Literal[0]
    review_important: Literal[0]
    review_minor: Literal[0]


class ClaimExecution(ClosedModel):
    remote_release_executed: Literal[False]
    push_executed: Literal[True]
    portfolio_ci_executed: Literal[True]
    portfolio_ci_passed: Literal[False]
    tag_created: Literal[False]
    production_deployed: Literal[False]
    kubernetes_production_ready: Literal[False]
    h2_executed: Literal[False]
    cv_workload_implemented: Literal[False]
    llm_workload_implemented: Literal[False]


class LocalReleaseReadiness(ClosedModel):
    schema_version: Literal["mdcp.local-release-readiness.v1.1"]
    canonicalization_version: Literal["RFC8785"]
    evidence_class: Literal["github_private_staging_corrective_readiness"]
    publication_status: Literal["public"]
    formal_closure_commit: Literal["b1bb0d80cd40e6f39372c0a45892500cc9530712"]
    formal_closure_parent: Literal["407f68b63c06a17ef54d5ec17722ef1f801b1689"]
    correction_commit: Literal["bfe517819ec2163d700519fc427dbe8bb8071258"]
    search_receipt_sha256: Literal[
        "5c0dc214281af3191ecfef0bd95e4d0ff99e3cc6c710d894a1f0b4a3465b7d63"
    ]
    search_index_sha256: Literal["2f630aa428fb539efb24904fd308f83fdf9458a46df6aa0cb7099a28ece4b205"]
    source_inventory_sha256: Literal[
        "cf2880259d9e82eae2291bb51fb041be0bf5f24a77f750565e8fe0227c1b539b"
    ]
    formal_worker_inventory_sha256: Literal[
        "ebac7f1b61024e532f6cba9c3eb4cded12ad1972fb5a5a660a40c9bfd16a43d3"
    ]
    v1_serving_identity: Literal["d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"]
    v2_serving_identity: Literal["198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea"]
    static_firewall_sha256: Literal[
        "e443596f27911614a5387975c424554d4dd9906b56d8bc330b2887bc113a5de1"
    ]
    portfolio_ci_commit: CommitSha
    portfolio_ci_run_url: PortfolioCiRunUrl
    portfolio_ci_conclusion: Literal["failure"]
    public_surface_entries: tuple[PublicSurfaceEntry, ...]
    public_surface_inventory_sha256: Sha256
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]
    technical_closure_verification: TechnicalClosureVerification
    reviewer_entrypoint: Literal["scripts/reviewer-fast-path.ps1"]
    claim_ceiling: Literal["mdcp.private-staging-corrective-claim-ceiling.v1"]
    claim_execution: ClaimExecution

    @model_validator(mode="after")
    def exact_public_surface(self) -> LocalReleaseReadiness:
        paths = tuple(entry.logical_path for entry in self.public_surface_entries)
        if paths != PUBLIC_SURFACE_PATHS:
            raise ValueError("PUBLIC_RELEASE_SLICE_INVENTORY_INVALID")
        expected = sha256_hex(
            canonicalize_json(
                [entry.model_dump(mode="json") for entry in self.public_surface_entries]
            )
        )
        if self.public_surface_inventory_sha256 != expected:
            raise ValueError("PUBLIC_RELEASE_SLICE_INVENTORY_INVALID")
        return self


def parse_readiness_bytes(raw: bytes) -> LocalReleaseReadiness:
    try:
        parsed = parse_json_bytes(raw)
        model = LocalReleaseReadiness.model_validate(parsed)
        if canonicalize_json(model.model_dump(mode="json")) != raw:
            raise ValueError("readiness bytes are not canonical")
        return model
    except Exception:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID") from None


def _git(root: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ("git", "--no-replace-objects", *arguments),
            cwd=root,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID") from None
    if completed.returncode != 0:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")
    return completed.stdout


def _normalize_logical_path(logical_path: str, *, base: PurePosixPath | None = None) -> str:
    if not logical_path or "\\" in logical_path or "\x00" in logical_path:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
    candidate = PurePosixPath(logical_path)
    if candidate.is_absolute():
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")

    components = list(base.parts) if base is not None else []
    for component in candidate.parts:
        if component == "..":
            if not components:
                raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
            components.pop()
        elif component != ".":
            if ":" in component:
                raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
            components.append(component)
    if not components:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
    return PurePosixPath(*components).as_posix()


def _read_regular(root: Path, logical_path: str) -> bytes:
    normalized = _normalize_logical_path(logical_path)
    if normalized != logical_path:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
    try:
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise PublicReleaseError("PUBLIC_RELEASE_SLICE_FILE_INVALID")
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        target = root
        parts = PurePosixPath(normalized).parts
        for index, component in enumerate(parts):
            target /= component
            info = target.lstat()
            reparse = getattr(info, "st_file_attributes", 0) & reparse_flag
            if stat.S_ISLNK(info.st_mode) or reparse:
                raise PublicReleaseError("PUBLIC_RELEASE_SLICE_FILE_INVALID")
            final_component = index == len(parts) - 1
            if final_component and not stat.S_ISREG(info.st_mode):
                raise PublicReleaseError("PUBLIC_RELEASE_SLICE_FILE_INVALID")
            if not final_component and not stat.S_ISDIR(info.st_mode):
                raise PublicReleaseError("PUBLIC_RELEASE_SLICE_FILE_INVALID")
        return target.read_bytes()
    except PublicReleaseError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_FILE_INVALID") from None


def build_public_surface_inventory(root: Path) -> tuple[PublicSurfaceEntry, ...]:
    return tuple(
        PublicSurfaceEntry(
            logical_path=path,
            byte_size=len(raw := _read_regular(root, path)),
            sha256=sha256_hex(raw),
        )
        for path in PUBLIC_SURFACE_PATHS
    )


def load_readiness(root: Path) -> LocalReleaseReadiness:
    return parse_readiness_bytes(_read_regular(root, READINESS_PATH))


def _resolved_link_path(root: Path, document: str, link: str) -> str:
    try:
        logical_path = _normalize_logical_path(link, base=PurePosixPath(document).parent)
        _read_regular(root, logical_path)
    except PublicReleaseError:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_LINK_INVALID") from None
    return logical_path


def verify_document_links(root: Path) -> None:
    for document in PUBLIC_MARKDOWN_PATHS:
        try:
            text = _read_regular(root, document).decode("utf-8", errors="strict")
        except (PublicReleaseError, UnicodeError):
            raise PublicReleaseError("PUBLIC_RELEASE_SLICE_LINK_INVALID") from None
        for match in _MARKDOWN_LINK_TARGET.finditer(text):
            target = match.group(1)
            folded = target.casefold()
            if (
                folded.startswith("http://")
                or folded.startswith("https://")
                or folded.startswith("mailto:")
                or target.startswith("#")
            ):
                continue
            logical_target = target.split("#", 1)[0]
            if logical_target:
                _resolved_link_path(root, document, logical_target)


def _git_text(root: Path, *arguments: str) -> str:
    try:
        return _git(root, *arguments).decode("utf-8", errors="strict").strip()
    except PublicReleaseError:
        raise
    except UnicodeError:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID") from None


def _required_object(raw: bytes) -> dict[str, object]:
    try:
        value = parse_json_bytes(raw)
    except Exception:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID") from None
    if not isinstance(value, dict):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")
    return value


def verify_git_closure(root: Path, readiness: LocalReleaseReadiness) -> None:
    for commit, parent, status in EXPECTED_COMMITS:
        if _git_text(root, "show", "-s", "--format=%P", commit) != parent:
            raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")
        paths = CORRECTION_PATHS if status == "M" else EVIDENCE_PATHS
        expected = tuple(f"{status}\t{path}" for path in paths)
        actual = tuple(
            line
            for line in _git_text(
                root,
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                commit,
            ).splitlines()
            if line
        )
        if actual != expected:
            raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")

    _git(root, "merge-base", "--is-ancestor", FORMAL_CLOSURE_COMMIT, "HEAD")

    index_path, receipt_path = EVIDENCE_PATHS
    index_raw = _git(root, "cat-file", "blob", f"{FORMAL_CLOSURE_COMMIT}:{index_path}")
    receipt_raw = _git(root, "cat-file", "blob", f"{FORMAL_CLOSURE_COMMIT}:{receipt_path}")
    if sha256_hex(index_raw) != readiness.search_index_sha256:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")
    if sha256_hex(receipt_raw) != readiness.search_receipt_sha256:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")

    index = _required_object(index_raw)
    receipt = _required_object(receipt_raw)
    if (
        index.get("search_receipt_sha256") != SEARCH_RECEIPT_SHA256
        or index.get("h2_status") != readiness.h2_status
        or index.get("h2_loaded_rows") != readiness.h2_loaded_rows
        or receipt.get("search_source_commit") != FORMAL_CLOSURE_PARENT
        or receipt.get("h2_status") != readiness.h2_status
        or receipt.get("h2_loaded_rows") != readiness.h2_loaded_rows
    ):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_GIT_INVALID")


def verify_public_release(root: Path) -> LocalReleaseReadiness:
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID") from None
    if not root.is_dir():
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_PATH_INVALID")
    readiness = load_readiness(root)
    if public_evidence_violations(readiness.model_dump(mode="json")):
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_DISCLOSURE")
    if build_public_surface_inventory(root) != readiness.public_surface_entries:
        raise PublicReleaseError("PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH")
    verify_document_links(root)
    verify_git_closure(root, readiness)
    return readiness


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    verify_public_release(arguments.repository_root)
    print("PUBLIC_RELEASE_SLICE_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicReleaseError as error:
        print(f"PUBLIC_RELEASE_SLICE_FAIL reason_code={error.reason_code}")
        raise SystemExit(1) from None
