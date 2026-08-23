from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from mdcp.feasibility.cgroup import (
    CgroupObservation,
    ResetCapabilityVerdict,
    build_probe_result,
    read_cgroup_v2,
)


def observe_exact_files(root: Path) -> dict[str, int | str]:
    files = read_cgroup_v2(root)
    return files.model_dump(mode="json")


def build_resource_document(
    observation: CgroupObservation,
    reset_capability: ResetCapabilityVerdict,
) -> dict[str, Any]:
    result = build_probe_result(observation, reset_capability)
    memory_evidence = result.model_dump(mode="json")
    cgroup_verdict = "PASS" if observation.cgroup_version == 2 else "UNKNOWN"
    resource_verdict = (
        "PASS"
        if observation.memory_max_bytes == 384 * 1024 * 1024
        and observation.cpu_max == "100000 100000"
        else "UNKNOWN"
    )
    gates = [
        _gate("cgroup_v2", cgroup_verdict, {"cgroup_version": observation.cgroup_version}),
        _gate(
            "scoped_memory_peak",
            result.verdict,
            {
                "measurement_mode": memory_evidence["measurement_mode"],
                "candidate_cgroup_identity_digest": result.candidate_cgroup_identity_digest,
                "evidence_digest": result.evidence_digest,
            },
        ),
        _gate(
            "compose_resource_limits",
            resource_verdict,
            {
                "memory_max_bytes": observation.memory_max_bytes,
                "cpu_max": observation.cpu_max,
            },
        ),
    ]
    return {
        "schema_version": "mdcp.feasibility.cgroup-resource.v1",
        "evidence_class": "FEASIBILITY",
        "gates": gates,
        "memory_evidence": memory_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--reset-capability", type=Path, required=True)
    parser.add_argument("--candidate-identity", required=True)
    parser.add_argument("--route-revision", type=int, required=True)
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    raw = json.loads(args.observation.read_text(encoding="utf-8"))
    reset = json.loads(args.reset_capability.read_text(encoding="utf-8"))
    observation = CgroupObservation(
        kernel=raw["kernel"],
        cgroup_version=raw["cgroup_version"],
        memory_current_bytes=raw.get("memory_current_bytes"),
        memory_peak_bytes=raw.get("memory_peak_bytes"),
        memory_max_bytes=raw.get("memory_max_bytes"),
        cpu_max=raw.get("cpu_max"),
        candidate_container_identity=args.candidate_identity,
        route_revision=args.route_revision,
        window_id=args.window_id,
        fresh_candidate=raw["fresh_candidate"],
        captured_phases=frozenset(raw["captured_phases"]),
        docker_socket_present=raw["docker_socket_present"],
    )
    document = build_resource_document(
        observation,
        ResetCapabilityVerdict(reset["reset_capability_verdict"]),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = document["memory_evidence"]
    print(
        "FEAS-CGROUP-"
        f"{result['verdict']} measurement_mode={result['measurement_mode']} "
        f"peak_bytes={result['memory_peak_bytes']} "
        f"evidence_digest={result['evidence_digest']}"
    )
    return 0 if all(gate["verdict"] == "PASS" for gate in document["gates"]) else 1


def _gate(name: str, verdict: str, evidence: dict[str, Any]) -> dict[str, Any]:
    canonical = json.dumps(evidence, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return {
        "name": name,
        "verdict": verdict,
        "evidence_digest": hashlib.sha256(canonical.encode("ascii")).hexdigest(),
    }


if __name__ == "__main__":
    raise SystemExit(main())
