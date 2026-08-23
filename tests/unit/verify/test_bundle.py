from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mdcp.common.enums import EvidenceClass, GateVerdict
from mdcp.verify.bundle import seal_bundle, verify_bundle

REPOSITORY_ROOT = Path(__file__).parents[3]
VALID_BUNDLE = REPOSITORY_ROOT / "tests" / "fixtures" / "supply-chain" / "valid"


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    target = tmp_path / "bundle"
    shutil.copytree(VALID_BUNDLE, target)
    return target


def test_seal_bundle_is_sorted_and_excludes_its_own_index(bundle: Path) -> None:
    (bundle / "bundle-index.json").unlink()

    index = seal_bundle(bundle)

    paths = tuple(member.path for member in index.members)
    assert paths == tuple(sorted(paths))
    assert "bundle-index.json" not in paths
    assert index.evidence_class is EvidenceClass.SYNTHETIC_TEST


def test_valid_offline_bundle_has_bounded_claims(bundle: Path) -> None:
    result = verify_bundle(bundle, online=False)

    assert result.verdict is GateVerdict.PASS
    assert result.evidence_class is EvidenceClass.REVIEWER_LOCALLY_RECOMPUTED
    assert result.source_evidence_class is EvidenceClass.SYNTHETIC_TEST
    assert result.live_ghcr_verified is False
    assert result.network_requests == 0


@pytest.mark.parametrize(
    "mutation",
    ["modified", "omitted", "added", "renamed"],
)
def test_member_inventory_mutation_fails_closed(bundle: Path, mutation: str) -> None:
    target = bundle / "attestation.json"
    if mutation == "modified":
        target.write_bytes(target.read_bytes() + b" ")
    elif mutation == "omitted":
        target.unlink()
    elif mutation == "added":
        (bundle / "unlisted.json").write_text("{}", encoding="utf-8")
    else:
        target.rename(bundle / "renamed.json")

    result = verify_bundle(bundle, online=False)

    assert result.verdict is GateVerdict.FAIL
    assert result.live_ghcr_verified is False


def test_manifest_release_id_tamper_fails_closed(bundle: Path) -> None:
    path = bundle / "final-release-manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["release_id"] = "sha256:" + "0" * 64
    path.write_text(json.dumps(document), encoding="utf-8")

    result = verify_bundle(bundle, online=False)

    assert result.verdict is GateVerdict.FAIL


def test_online_mode_is_not_silently_claimed(bundle: Path) -> None:
    with pytest.raises(ValueError, match="not implemented"):
        verify_bundle(bundle, online=True)
