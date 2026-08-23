from __future__ import annotations

import json
from pathlib import Path

from mdcp.contracts.release import ArtifactDescriptor

REPOSITORY_ROOT = Path(__file__).parents[3]


def test_checked_in_descriptor_schema_matches_pydantic_source() -> None:
    checked_in = json.loads(
        (
            REPOSITORY_ROOT / "schemas" / "v1" / "artifact-descriptor.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert checked_in == ArtifactDescriptor.model_json_schema()
    assert checked_in["additionalProperties"] is False
    assert "oci" not in checked_in["properties"]
    assert "release_id" not in checked_in["properties"]


def test_freeze_manifest_binds_policy_before_h2_access() -> None:
    manifest = json.loads(
        (
            REPOSITORY_ROOT / "tests" / "fixtures" / "workload" / "freeze-manifest.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest["schema_version"] == "mdcp.freeze-manifest.v1"
    assert manifest["h2_status"] == "SEALED_NOT_OPENED"
    assert len(manifest["quality_policy_sha256"]) == 64
    assert manifest["h1_verdict"] in {"PASS", "FAIL", "UNKNOWN"}


def test_synthetic_h1_report_is_explicit_non_natural_pass() -> None:
    report = json.loads(
        (
            REPOSITORY_ROOT
            / "tests"
            / "fixtures"
            / "workload"
            / "synthetic-h1-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["evidence_class"] == "synthetic_test"
    assert report["verdict"] == "PASS"
    assert report["overall"] == {"point_ratio": 0.9, "ucb95": 0.95, "row_count": 2400}
    assert all(
        metric["point_ratio"] <= 1.05
        and metric["ucb95"] <= 1.05
        and metric["row_count"] >= 100
        for metric in report["subgroups"].values()
    )
