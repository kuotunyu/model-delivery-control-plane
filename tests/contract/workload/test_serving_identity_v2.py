from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mdcp.contracts.release import (
    serving_inventory_digest,
    serving_inventory_from_root,
)
from mdcp.contracts.serving_identity_v2 import (
    V2_SERVING_PATHS,
    V2ServingIdentityError,
    build_v2_serving_inventory,
    verify_v2_serving_inventory,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
FROZEN_V1_SERVING_IDENTITY = "d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209"
EXPECTED_V2_PATHS = (
    "pyproject.toml",
    "schemas/v2/bike-request.schema.json",
    "schemas/v2/temporal-contract-receipt.schema.json",
    "src/mdcp/common/canonical.py",
    "src/mdcp/common/digests.py",
    "src/mdcp/common/enums.py",
    "src/mdcp/contracts/serving_identity_v2.py",
    "src/mdcp/contracts/workload.py",
    "src/mdcp/contracts/workload_v2.py",
    "src/mdcp/predictor/app_v2.py",
    "src/mdcp/predictor/runtime.py",
    "src/mdcp/temporal/adapter.py",
    "src/mdcp/temporal/constants.py",
    "src/mdcp/temporal/contract_gate.py",
    "src/mdcp/temporal/evidence.py",
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/golden_vectors.py",
    "src/mdcp/temporal/routing.py",
    "src/mdcp/workload/dataset.py",
    "src/mdcp/workload/features.py",
    "src/mdcp/workload/splits.py",
    "tests/fixtures/temporal/adapter-golden-vectors.json",
    "uv.lock",
)


def _source_archive(tmp_path: Path) -> Path:
    archive_root = tmp_path / "source-archive"
    shutil.copytree(
        REPOSITORY_ROOT,
        archive_root,
        ignore=shutil.ignore_patterns(
            ".git",
            ".worktrees",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            "runtime",
            "data",
        ),
    )
    return archive_root


def test_v2_inventory_is_exact_ordered_closed_set() -> None:
    result = build_v2_serving_inventory(REPOSITORY_ROOT, V2_SERVING_PATHS)

    assert V2_SERVING_PATHS == EXPECTED_V2_PATHS
    assert tuple(sorted(V2_SERVING_PATHS)) == V2_SERVING_PATHS
    assert len(V2_SERVING_PATHS) == 23
    assert result.body.schema_version == "mdcp.v2-serving-inventory.v1"
    assert result.body.entry_point == "mdcp.predictor.app_v2:app"
    assert tuple(entry.path for entry in result.body.entries) == EXPECTED_V2_PATHS
    assert len(result.inventory_sha256) == 64
    assert verify_v2_serving_inventory(REPOSITORY_ROOT, result) == result


@pytest.mark.parametrize(
    "mutation",
    ("missing", "extra", "duplicate", "unknown", "reordered", "unsafe"),
)
def test_declared_path_mutations_fail_closed(mutation: str) -> None:
    paths = list(V2_SERVING_PATHS)
    if mutation == "missing":
        paths.pop()
    elif mutation == "extra":
        paths.append("src/mdcp/extra.py")
    elif mutation == "duplicate":
        paths[-1] = paths[0]
    elif mutation == "unknown":
        paths[-1] = "src/mdcp/unknown.py"
    elif mutation == "reordered":
        paths[0], paths[1] = paths[1], paths[0]
    else:
        paths[-1] = "../private.txt"

    with pytest.raises(
        V2ServingIdentityError,
        match="^V2_SERVING_INVENTORY_INVALID$",
    ):
        build_v2_serving_inventory(REPOSITORY_ROOT, tuple(paths))


def test_unreadable_inventory_member_fails_closed(tmp_path: Path) -> None:
    archive_root = _source_archive(tmp_path)
    blocked_path = archive_root / V2_SERVING_PATHS[-1]
    blocked_path.unlink()
    blocked_path.mkdir()

    with pytest.raises(
        V2ServingIdentityError,
        match="^V2_SERVING_INVENTORY_INVALID$",
    ):
        build_v2_serving_inventory(archive_root, V2_SERVING_PATHS)


@pytest.mark.parametrize("mutation", ("wrong_digest", "missing", "duplicate", "reordered"))
def test_declared_result_mutations_fail_closed(mutation: str) -> None:
    result = build_v2_serving_inventory(REPOSITORY_ROOT, V2_SERVING_PATHS)
    entries = list(result.body.entries)
    if mutation == "wrong_digest":
        entries[0] = entries[0].model_copy(update={"sha256": "0" * 64})
    elif mutation == "missing":
        entries.pop()
    elif mutation == "duplicate":
        entries[-1] = entries[0]
    else:
        entries[0], entries[1] = entries[1], entries[0]
    mutated_body = result.body.model_copy(update={"entries": tuple(entries)})
    mutated = result.model_copy(update={"body": mutated_body})

    with pytest.raises(
        V2ServingIdentityError,
        match="^V2_SERVING_INVENTORY_INVALID$",
    ):
        verify_v2_serving_inventory(REPOSITORY_ROOT, mutated)


def test_v1_and_v2_recompute_from_git_free_source_archive(tmp_path: Path) -> None:
    current_v2 = build_v2_serving_inventory(REPOSITORY_ROOT, V2_SERVING_PATHS)
    archive_root = _source_archive(tmp_path)
    assert not (archive_root / ".git").exists()
    assert not (archive_root / ".worktrees").exists()

    script = """
import json
import sys
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root / 'src'))
from mdcp.contracts.release import serving_inventory_digest, serving_inventory_from_root
from mdcp.contracts.serving_identity_v2 import V2_SERVING_PATHS, build_v2_serving_inventory
from mdcp.predictor.app import create_app as create_v1_app
from mdcp.predictor.app_v2 import create_app as create_v2_app

v2 = build_v2_serving_inventory(root, V2_SERVING_PATHS)
print(json.dumps({
    'git_absent': not (root / '.git').exists(),
    'v1': serving_inventory_digest(serving_inventory_from_root(root)),
    'v2': v2.inventory_sha256,
    'v1_entry_module': create_v1_app.__module__,
    'v2_entry_module': create_v2_app.__module__,
}, sort_keys=True))
"""
    environment = os.environ.copy()
    environment["PATH"] = ""
    environment.pop("PYTHONPATH", None)
    for name in tuple(environment):
        if name.startswith("MDCP_"):
            environment.pop(name)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=archive_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads(completed.stdout)

    assert evidence == {
        "git_absent": True,
        "v1": FROZEN_V1_SERVING_IDENTITY,
        "v2": current_v2.inventory_sha256,
        "v1_entry_module": "mdcp.predictor.app",
        "v2_entry_module": "mdcp.predictor.app_v2",
    }
    assert serving_inventory_digest(serving_inventory_from_root(archive_root)) == (
        FROZEN_V1_SERVING_IDENTITY
    )
    assert (
        build_v2_serving_inventory(archive_root, V2_SERVING_PATHS).inventory_sha256
        == current_v2.inventory_sha256
    )
