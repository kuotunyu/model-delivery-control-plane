from __future__ import annotations

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import ValidationVerdict
from mdcp.contracts.release import ArtifactDescriptor
from mdcp.validator.service import ReasonCode, ValidationCheck, make_check
from mdcp.workload.mlflow_lineage import MLflowVersionSnapshot


def compare_mlflow_snapshots(
    expected: MLflowVersionSnapshot,
    observed: MLflowVersionSnapshot,
) -> None:
    if expected.model_dump(mode="json") != observed.model_dump(mode="json"):
        raise ValueError("MLflow snapshot identity mismatch")


def validate_snapshot_against_descriptor(
    snapshot: MLflowVersionSnapshot,
    descriptor: ArtifactDescriptor,
) -> ValidationCheck:
    checks = {
        "onnx_digest_matches": snapshot.onnx_sha256 == descriptor.onnx.sha256,
        "h1_digest_matches": snapshot.h1_report_sha256 == descriptor.h1_report_sha256,
        "numeric_version": isinstance(snapshot.version, int)
        and not isinstance(snapshot.version, bool)
        and snapshot.version > 0,
        "run_bound_source": snapshot.run_id in snapshot.artifact_uri.replace("\\", "/"),
    }
    passes = all(checks.values())
    return make_check(
        ReasonCode.VAL_MLFLOW_LINEAGE,
        ValidationVerdict.PASS if passes else ValidationVerdict.FAIL,
        evidence_digest=sha256_hex(canonicalize_json(checks)),
    )
