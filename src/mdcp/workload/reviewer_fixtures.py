from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
from pydantic import BaseModel, ConfigDict

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import EvidenceClass, GateVerdict
from mdcp.contracts.release import (
    ArtifactDescriptor,
    OnnxMetadata,
    artifact_descriptor_digest,
    serving_inventory_digest,
    serving_inventory_from_root,
)
from mdcp.policy.cluster_bootstrap import PairedQualityRow
from mdcp.workload.evaluation import QualityPolicy, evaluate_h1
from mdcp.workload.features import approved_feature_columns

FixtureRole = Literal["stable", "candidate"]
REPOSITORY_ROOT = Path(__file__).parents[3]
SYNTHETIC_GROUPS = (
    "weather_clear",
    "weather_mist",
    "weather_adverse",
    "day_non_working",
    "day_working",
    "demand_peak",
    "demand_off_peak",
)


class FixtureVerificationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stable: int
    candidate: int
    uci_rows: int
    descriptor_digests: dict[str, str]


def _schema_contract_digest(repository_root: Path) -> str:
    schemas = {
        "bike_request": json.loads(
            (repository_root / "schemas/v1/bike-request.schema.json").read_text(
                encoding="utf-8"
            )
        ),
        "prediction_response": json.loads(
            (repository_root / "schemas/v1/prediction-response.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    }
    return sha256_hex(canonicalize_json(schemas))


def _feature_manifest_digest() -> str:
    return sha256_hex(("\n".join(approved_feature_columns()) + "\n").encode("utf-8"))


def build_reviewer_descriptor(
    role: FixtureRole,
    *,
    git_source_sha: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> ArtifactDescriptor:
    content = synthetic_fixture_onnx_bytes(role)
    model = onnx.load_model_from_string(content)
    freeze_manifest = json.loads(
        (repository_root / "tests/fixtures/workload/freeze-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    synthetic_report_path = (
        repository_root / "tests/fixtures/workload/synthetic-h1-report.json"
    )
    training_recipe = {
        "schema_version": "mdcp.synthetic-training-receipt.v1",
        "role": role,
        "data_kind": "deterministic_generated",
        "recipe": "analytic-linear-weights-v1",
        "uci_rows": 0,
    }
    return ArtifactDescriptor(
        schema_version="artifact-descriptor/v1",
        model_name=role,
        evidence_class=EvidenceClass.SYNTHETIC_TEST,
        training_data_kind="deterministic_generated",
        git_source_sha=git_source_sha,
        model_sha256=sha256_hex(content),
        schema_digest=_schema_contract_digest(repository_root),
        serving_code_config_id=serving_inventory_digest(
            serving_inventory_from_root(repository_root)
        ),
        feature_manifest_sha256=_feature_manifest_digest(),
        dependency_lock_sha256=sha256_hex((repository_root / "uv.lock").read_bytes()),
        split_manifest_sha256=sha256_hex(canonicalize_json(freeze_manifest["split"])),
        training_receipt_sha256=sha256_hex(canonicalize_json(training_recipe)),
        h1_report_sha256=sha256_hex(synthetic_report_path.read_bytes()),
        onnx=OnnxMetadata(
            sha256=sha256_hex(content),
            size_bytes=len(content),
            opset=next(item.version for item in model.opset_import if item.domain == ""),
            operators=tuple(sorted({node.op_type for node in model.graph.node})),
            input_names=tuple(value.name for value in model.graph.input),
            output_name=model.graph.output[0].name,
        ),
    )


def generate_reviewer_fixtures(root: Path, *, git_source_sha: str) -> None:
    for role in ("stable", "candidate"):
        directory = root / role
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "model.onnx").write_bytes(synthetic_fixture_onnx_bytes(role))
        descriptor = build_reviewer_descriptor(role, git_source_sha=git_source_sha)
        (directory / "artifact-descriptor.json").write_text(
            json.dumps(descriptor.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def synthetic_fixture_onnx_bytes(role: FixtureRole) -> bytes:
    inputs = [
        helper.make_tensor_value_info(name, TensorProto.FLOAT, [None, 1])
        for name in approved_feature_columns()
    ]
    output = helper.make_tensor_value_info("prediction", TensorProto.FLOAT, [None, 1])
    scale = 1.0 if role == "stable" else 0.9
    weights = np.asarray(
        [2.0, 1.0, 3.0, -1.0, 0.5, 1.0, -2.0, 4.0, 4.0, -3.0, -1.0],
        dtype=np.float32,
    ).reshape(11, 1)
    weights *= scale
    bias = np.asarray([10.0 if role == "stable" else 11.0], dtype=np.float32)
    initializers = [
        numpy_helper.from_array(weights, name="weights"),
        numpy_helper.from_array(bias, name="bias"),
    ]
    nodes = [
        helper.make_node(
            "Concat",
            list(approved_feature_columns()),
            ["features"],
            axis=1,
            name="feature_concat",
        ),
        helper.make_node("MatMul", ["features", "weights"], ["linear"], name="linear"),
        helper.make_node("Add", ["linear", "bias"], ["biased"], name="bias"),
        helper.make_node("Relu", ["biased"], ["prediction"], name="nonnegative"),
    ]
    graph = helper.make_graph(
        nodes,
        f"mdcp-reviewer-{role}",
        inputs,
        [output],
        initializer=initializers,
    )
    model = helper.make_model(
        graph,
        producer_name="mdcp-deterministic-reviewer-fixture",
        opset_imports=[helper.make_opsetid("", 18)],
        ir_version=10,
    )
    onnx.checker.check_model(model)
    return model.SerializeToString()


def synthetic_h1_rows() -> tuple[PairedQualityRow, ...]:
    day_count = 100
    z_values = np.linspace(-1.0, 1.0, day_count, dtype=np.float64)
    probe_rng = np.random.Generator(np.random.PCG64(2026))
    sampled_days = probe_rng.integers(0, day_count, size=(2000, day_count))
    probe_ucb = float(np.sort(z_values[sampled_days].mean(axis=1))[1899])
    scale = 0.05 / probe_ucb
    day_ratios = 0.9 + scale * z_values
    start = date(2012, 1, 1)
    rows: list[PairedQualityRow] = []
    for day_index, ratio in enumerate(day_ratios):
        for hour in range(24):
            candidate_error = 10.0 * ratio
            rows.append(
                PairedQualityRow(
                    request_id=f"synthetic-{day_index:03d}-{hour:02d}",
                    calendar_day=start + timedelta(days=day_index),
                    stable_prediction=90.0,
                    candidate_prediction=100.0 - candidate_error,
                    label=100.0,
                    groups=SYNTHETIC_GROUPS,
                )
            )
    return tuple(rows)


def synthetic_h1_report_document() -> dict[str, object]:
    policy = QualityPolicy(
        schema_version="mdcp.quality-policy.v1",
        overall_max_ratio=0.97,
        subgroup_max_ratio=1.05,
        minimum_subgroup_rows=100,
        resamples=2000,
        seed=2026,
        subgroup_names=SYNTHETIC_GROUPS,
    )
    report = evaluate_h1(
        synthetic_h1_rows(),
        policy,
        evidence_class=EvidenceClass.SYNTHETIC_TEST,
    )
    if report.verdict is not GateVerdict.PASS or report.bootstrap.overall is None:
        raise AssertionError("deterministic synthetic H1 fixture must pass")

    def metric_document(name: str | None = None) -> dict[str, float | int]:
        metric = (
            report.bootstrap.overall
            if name is None
            else report.bootstrap.subgroups[name]
        )
        return {
            "point_ratio": round(metric.point_ratio, 2),
            "ucb95": round(metric.ucb95, 2),
            "row_count": metric.row_count,
        }

    return {
        "schema_version": "mdcp.synthetic-h1-report.v1",
        "verdict": report.verdict.value,
        "evidence_class": report.evidence_class.value,
        "paired_row_count": report.paired_row_count,
        "bootstrap": {
            "resamples": report.bootstrap.resamples,
            "seed": report.bootstrap.seed,
            "replicate_index": report.bootstrap.replicate_index,
        },
        "overall": metric_document(),
        "subgroups": {group: metric_document(group) for group in SYNTHETIC_GROUPS},
    }


def verify_reviewer_fixtures(root: Path) -> FixtureVerificationReceipt:
    descriptor_digests: dict[str, str] = {}
    expected_serving_identity = serving_inventory_digest(
        serving_inventory_from_root(REPOSITORY_ROOT)
    )
    for role in ("stable", "candidate"):
        directory = root / role
        actual_files = {path.name for path in directory.iterdir() if path.is_file()}
        if actual_files != {"artifact-descriptor.json", "model.onnx"}:
            raise ValueError(f"unexpected reviewer files for {role}")
        content = (directory / "model.onnx").read_bytes()
        if content != synthetic_fixture_onnx_bytes(role):
            raise ValueError(f"reviewer ONNX is not deterministic for {role}")
        descriptor = ArtifactDescriptor.model_validate_json(
            (directory / "artifact-descriptor.json").read_text(encoding="utf-8")
        )
        model = onnx.load_model_from_string(content)
        operators = tuple(sorted({node.op_type for node in model.graph.node}))
        opset = next(item.version for item in model.opset_import if item.domain == "")
        if descriptor.onnx.sha256 != sha256_hex(content):
            raise ValueError(f"reviewer ONNX digest mismatch for {role}")
        if descriptor.onnx.size_bytes != len(content):
            raise ValueError(f"reviewer ONNX size mismatch for {role}")
        if descriptor.onnx.operators != operators or descriptor.onnx.opset != opset:
            raise ValueError(f"reviewer ONNX inventory mismatch for {role}")
        if descriptor.onnx.input_names != approved_feature_columns():
            raise ValueError(f"reviewer input contract mismatch for {role}")
        if descriptor.serving_code_config_id != expected_serving_identity:
            raise ValueError(f"reviewer serving identity mismatch for {role}")
        expected_descriptor = build_reviewer_descriptor(
            role,
            git_source_sha=descriptor.git_source_sha,
        )
        if descriptor != expected_descriptor:
            raise ValueError(f"reviewer descriptor is not reproducible for {role}")
        descriptor_digests[role] = artifact_descriptor_digest(descriptor)

    forbidden_assets = tuple(root.rglob("*.csv")) + tuple(root.rglob("*.zip"))
    if forbidden_assets:
        raise ValueError("reviewer fixtures contain dataset files")
    synthetic_report = json.loads(
        (REPOSITORY_ROOT / "tests/fixtures/workload/synthetic-h1-report.json").read_text(
            encoding="utf-8"
        )
    )
    if synthetic_report != synthetic_h1_report_document():
        raise ValueError("synthetic H1 report does not recompute from its zero-UCI recipe")
    return FixtureVerificationReceipt(
        stable=1,
        candidate=1,
        uci_rows=0,
        descriptor_digests=descriptor_digests,
    )
