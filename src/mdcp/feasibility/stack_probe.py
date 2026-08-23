from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex

REQUIRED_STACK_SERVICES = frozenset(
    {
        "postgres",
        "mlflow",
        "prometheus",
        "grafana",
        "control-probe",
        "router-probe",
        "stable",
        "candidate",
    }
)
MEMORY_BUDGET_BYTES = int(6.5 * 1024**3)
DISK_BUDGET_BYTES = 5 * 1024**3


class ServiceMeasurement(BaseModel):
    model_config = ConfigDict(frozen=True)

    memory_peak_bytes: int
    memory_max_bytes: int


class StackObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    measurement_mode: Literal["CGROUP_V2_MEMORY_PEAK_SUM"]
    ready: list[str]
    services: dict[str, ServiceMeasurement]
    image_virtual_size_upper_bound_bytes: int
    volume_bytes: int
    disk_bytes: int


class StackBudgetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    measurement_mode: Literal["CGROUP_V2_MEMORY_PEAK_SUM"]
    ready: list[str]
    services: dict[str, ServiceMeasurement]
    peak_bytes: int
    image_virtual_size_upper_bound_bytes: int
    volume_bytes: int
    disk_bytes: int


def build_stack_document(values: dict[str, Any]) -> dict[str, Any]:
    observation = StackObservation.model_validate(values)
    peak_bytes = sum(service.memory_peak_bytes for service in observation.services.values())
    result = StackBudgetResult(
        measurement_mode=observation.measurement_mode,
        ready=observation.ready,
        services=observation.services,
        peak_bytes=peak_bytes,
        image_virtual_size_upper_bound_bytes=observation.image_virtual_size_upper_bound_bytes,
        volume_bytes=observation.volume_bytes,
        disk_bytes=observation.disk_bytes,
    )
    exact_services = set(result.services) == REQUIRED_STACK_SERVICES
    exact_ready = set(result.ready) == REQUIRED_STACK_SERVICES
    bounded_services = all(
        0 <= service.memory_peak_bytes <= service.memory_max_bytes
        for service in result.services.values()
    )
    passed = (
        exact_services
        and exact_ready
        and bounded_services
        and result.peak_bytes <= MEMORY_BUDGET_BYTES
        and result.disk_bytes < DISK_BUDGET_BYTES
        and result.volume_bytes == 0
    )
    evidence = result.model_dump(mode="json")
    return {
        "schema_version": "mdcp.feasibility.stack.v1",
        "evidence_class": "FEASIBILITY",
        "claim_boundary": "reviewer stack feasibility; not formal reviewer-path acceptance",
        "gate": {
            "name": "reviewer_stack_budget",
            "verdict": "PASS" if passed else "FAIL",
            "evidence_digest": sha256_hex(canonicalize_json(evidence)),
        },
        "result": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        values = json.loads(args.observation.read_text(encoding="utf-8"))
        document = build_stack_document(values)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception:
        print("FEAS-STACK-FAIL")
        return 1
    result = document["result"]
    verdict = document["gate"]["verdict"]
    print(
        f"FEAS-STACK-{verdict} ready={len(result['ready'])}/8 "
        f"peak_bytes={result['peak_bytes']} disk_bytes={result['disk_bytes']}"
    )
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
