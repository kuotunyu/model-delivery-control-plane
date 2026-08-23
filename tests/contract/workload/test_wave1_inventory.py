from __future__ import annotations

import json
import re
from pathlib import Path

from mdcp.common.digests import sha256_hex
from mdcp.contracts.release import ArtifactDescriptor, artifact_descriptor_digest
from mdcp.workload.reviewer_fixtures import verify_reviewer_fixtures

REPOSITORY_ROOT = Path(__file__).parents[3]
REPORT_PATH = REPOSITORY_ROOT / "evidence" / "public" / "wave1" / "workload-identity-report.json"


def test_wave1_public_inventory_recomputes_checked_in_identities() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    wave0 = REPOSITORY_ROOT / "evidence" / "public" / "feasibility" / "wave0-report.json"
    freeze = REPOSITORY_ROOT / "tests" / "fixtures" / "workload" / "freeze-manifest.json"
    reviewer = verify_reviewer_fixtures(REPOSITORY_ROOT / "tests" / "fixtures" / "artifacts")

    assert report["status"] == "COMPLETE"
    assert report["wave0_entry"]["verdict"] == "PASS"
    assert report["wave0_entry"]["passed_gates"] == 8
    assert report["wave0_entry"]["aggregate_report_sha256"] == sha256_hex(wave0.read_bytes())
    assert report["freeze_boundary"] == {
        "manifest_sha256": sha256_hex(freeze.read_bytes()),
        "h2_status": "SEALED_NOT_OPENED",
    }
    assert report["reviewer_fixtures"]["stable_descriptor_digest"] == (
        reviewer.descriptor_digests["stable"]
    )
    assert report["reviewer_fixtures"]["candidate_descriptor_digest"] == (
        reviewer.descriptor_digests["candidate"]
    )


def test_wave1_inventory_preserves_honest_h1_and_no_host_paths() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    report = json.loads(text)

    assert report["natural_h1"]["verdict"] == "FAIL"
    assert report["natural_h1"]["natural_candidate_promotion_eligible"] is False
    assert report["reviewer_fixtures"]["evidence_class"] == "synthetic_test"
    assert report["dataset"]["raw_data_committed"] is False
    assert report["remote_mutation_performed"] is False
    assert "file:///" not in text
    assert not re.search(r"[A-Za-z]:[\\/]", text)


def test_reviewer_descriptor_files_match_canonical_inventory() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    for role in ("stable", "candidate"):
        path = (
            REPOSITORY_ROOT
            / "tests"
            / "fixtures"
            / "artifacts"
            / role
            / "artifact-descriptor.json"
        )
        descriptor = ArtifactDescriptor.model_validate_json(path.read_text(encoding="utf-8"))
        assert report["reviewer_fixtures"][f"{role}_descriptor_digest"] == (
            artifact_descriptor_digest(descriptor)
        )
