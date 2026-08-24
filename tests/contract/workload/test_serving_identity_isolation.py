from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from mdcp.contracts.release import (
    SERVING_PATHS,
    serving_inventory_digest,
    serving_inventory_from_root,
)
from mdcp.workload.reviewer_fixtures import verify_reviewer_fixtures

REPOSITORY_ROOT = Path(__file__).parents[3]
FROZEN_V1_WORKLOAD_BLOB = "33f174528e691f1f5ff2590c2c641d75669d5196"
FROZEN_V1_APP_BLOB = "9fdee53bead221f0698d2e4a52407a4901c37649"
FROZEN_V1_SERVING_IDENTITY = "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"


def git_blob_id(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def test_current_v1_bytes_and_identity_are_frozen() -> None:
    assert git_blob_id((REPOSITORY_ROOT / "src/mdcp/contracts/workload.py").read_bytes()) == (
        FROZEN_V1_WORKLOAD_BLOB
    )
    assert git_blob_id((REPOSITORY_ROOT / "src/mdcp/predictor/app.py").read_bytes()) == (
        FROZEN_V1_APP_BLOB
    )
    assert serving_inventory_digest(serving_inventory_from_root(REPOSITORY_ROOT)) == (
        FROZEN_V1_SERVING_IDENTITY
    )


def test_v1_identity_recomputes_without_git(tmp_path: Path) -> None:
    archive_root = tmp_path / "source-archive"
    for relative_path in SERVING_PATHS:
        destination = archive_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative_path, destination)

    assert not (archive_root / ".git").exists()
    assert serving_inventory_digest(serving_inventory_from_root(archive_root)) == (
        FROZEN_V1_SERVING_IDENTITY
    )


def test_unchanged_reviewer_descriptors_verify_against_current_tree() -> None:
    receipt = verify_reviewer_fixtures(REPOSITORY_ROOT / "tests/fixtures/artifacts")

    assert receipt.stable == 1
    assert receipt.candidate == 1
    assert receipt.uci_rows == 0
