from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mdcp.feasibility.stack_probe import REQUIRED_STACK_SERVICES, build_stack_document

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_full_stack_result_passes_only_under_memory_and_disk_budgets() -> None:
    per_service = {
        service: {"memory_peak_bytes": 128 * 1024**2, "memory_max_bytes": 512 * 1024**2}
        for service in REQUIRED_STACK_SERVICES
    }
    document = build_stack_document(
        {
            "measurement_mode": "CGROUP_V2_MEMORY_PEAK_SUM",
            "ready": sorted(REQUIRED_STACK_SERVICES),
            "services": per_service,
            "image_virtual_size_upper_bound_bytes": 3 * 1024**3,
            "volume_bytes": 0,
            "disk_bytes": 3 * 1024**3,
        }
    )

    assert document["gate"]["name"] == "reviewer_stack_budget"
    assert document["gate"]["verdict"] == "PASS"
    assert document["result"]["peak_bytes"] == 1024**3
    assert set(document["result"]["ready"]) == set(REQUIRED_STACK_SERVICES)


def test_full_stack_result_fails_closed_on_budget_or_missing_service() -> None:
    services = {
        service: {"memory_peak_bytes": 128 * 1024**2, "memory_max_bytes": 512 * 1024**2}
        for service in REQUIRED_STACK_SERVICES
        if service != "candidate"
    }
    document = build_stack_document(
        {
            "measurement_mode": "CGROUP_V2_MEMORY_PEAK_SUM",
            "ready": sorted(services),
            "services": services,
            "image_virtual_size_upper_bound_bytes": 5 * 1024**3,
            "volume_bytes": 0,
            "disk_bytes": 5 * 1024**3,
        }
    )

    assert document["gate"]["verdict"] == "FAIL"


def test_compose_reviewer_stack_has_exact_bounded_internal_services() -> None:
    versions = dict(
        line.split("=", 1)
        for line in (REPOSITORY_ROOT / "constraints" / "versions.env").read_text(
            encoding="utf-8"
        ).splitlines()
        if line and not line.startswith("#")
    )
    environment = os.environ.copy()
    environment.update(versions)
    environment["MDCP_PYTHON_IMAGE"] = versions["PYTHON_IMAGE"]
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "--file",
            str(REPOSITORY_ROOT / "compose.feasibility.yaml"),
            "--profile",
            "stack",
            "config",
            "--format",
            "json",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    configuration = json.loads(completed.stdout)
    services = configuration["services"]

    assert set(services) == set(REQUIRED_STACK_SERVICES)
    assert configuration["networks"]["stack"]["internal"] is True
    for service in services.values():
        assert service["networks"] == {"stack": None}
        assert "ports" not in service
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert int(service["mem_limit"]) > 0
        assert service["pids_limit"] > 0
