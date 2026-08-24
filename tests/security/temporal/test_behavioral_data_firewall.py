from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

import mdcp.temporal.firewall as firewall
from mdcp.temporal.firewall import (
    BehavioralFirewallError,
    run_behavioral_h2_firewall,
)
from mdcp.workload.dataset import load_uci_archive
from mdcp.workload.splits import DatasetPartitions, split_rows

_TESTS_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_TESTS_ROOT))
try:
    _archive_fixtures = importlib.import_module("temporal_archive_fixtures")
finally:
    sys.path.pop(0)

SYNTHETIC_METADATA = _archive_fixtures.SYNTHETIC_METADATA
ArchiveFixture = _archive_fixtures.ArchiveFixture
build_synthetic_archive = _archive_fixtures.build_synthetic_archive
synthetic_archive = _archive_fixtures.synthetic_archive

FORBIDDEN_COUNTS = {
    "load_uci_archive": 0,
    "split_rows": 0,
    "DatasetPartitions.open_h2": 0,
}


def test_synthetic_archive_recipe_is_byte_deterministic(tmp_path: Path) -> None:
    first = build_synthetic_archive(tmp_path / "first.zip")
    second = build_synthetic_archive(tmp_path / "second.zip")

    assert first.path.read_bytes() == second.path.read_bytes()
    assert first.sha256 == second.sha256
    assert first.recipe_sha256 == second.recipe_sha256
    assert SYNTHETIC_METADATA == {
        "evidence_class": "synthetic_test",
        "source_kind": "deterministic_generated",
        "uci_rows": 0,
    }


def test_behavioral_gate_stops_before_sentinel(
    synthetic_archive: ArchiveFixture,
) -> None:
    result = run_behavioral_h2_firewall(
        synthetic_archive.path,
        synthetic_archive.sha256,
        fixture_recipe_sha256=synthetic_archive.recipe_sha256,
    )
    boundary = result.body.development_boundary

    assert result.body.verdict == "PASS"
    assert len(result.behavioral_result_sha256) == 64
    assert boundary.development_row_count == 13_003
    assert boundary.train_row_count == 8_645
    assert boundary.h1_row_count == 4_358
    assert boundary.read_csv_nrows == (13_003,)
    assert boundary.forbidden_call_counts == FORBIDDEN_COUNTS
    assert boundary.h2_status == "SEALED_NOT_LOADED"
    assert boundary.h2_loaded_rows == 0


def test_behavioral_hooks_are_restored_after_success(
    synthetic_archive: ArchiveFixture,
) -> None:
    previous_read_csv = pd.read_csv
    previous_profile = sys.getprofile()

    run_behavioral_h2_firewall(
        synthetic_archive.path,
        synthetic_archive.sha256,
        fixture_recipe_sha256=synthetic_archive.recipe_sha256,
    )

    assert pd.read_csv is previous_read_csv
    assert sys.getprofile() is previous_profile


@pytest.mark.parametrize(
    "capability",
    ("load_uci_archive", "split_rows", "DatasetPartitions.open_h2"),
)
def test_behavioral_gate_denies_actual_legacy_capability_calls_and_restores_hooks(
    synthetic_archive: ArchiveFixture,
    monkeypatch: pytest.MonkeyPatch,
    capability: str,
) -> None:
    previous_read_csv = pd.read_csv
    previous_profile = sys.getprofile()

    if capability == "load_uci_archive":

        def attacking_loader(path: Path, digest: str) -> pd.DataFrame:
            return load_uci_archive(path, digest)

        monkeypatch.setattr(firewall, "load_uci_development_archive", attacking_loader)
    elif capability == "split_rows":

        def attacking_split(frame: pd.DataFrame) -> object:
            return split_rows(frame)

        monkeypatch.setattr(firewall, "split_development_rows", attacking_split)
    else:

        def attacking_open_h2(frame: pd.DataFrame) -> object:
            partitions = DatasetPartitions(train=frame, h1=frame, _h2=frame)
            return partitions.open_h2("a" * 64)

        monkeypatch.setattr(firewall, "split_development_rows", attacking_open_h2)

    with pytest.raises(BehavioralFirewallError, match="^FORBIDDEN_CAPABILITY_CALLED$"):
        run_behavioral_h2_firewall(
            synthetic_archive.path,
            synthetic_archive.sha256,
            fixture_recipe_sha256=synthetic_archive.recipe_sha256,
        )

    assert pd.read_csv is previous_read_csv
    assert sys.getprofile() is previous_profile
