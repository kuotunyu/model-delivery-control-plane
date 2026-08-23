from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mdcp.validator.isolation import VALIDATOR_SECURITY

REPOSITORY_ROOT = Path(__file__).parents[3]


def _compose_config() -> dict:
    environment = {
        **os.environ,
        "MDCP_PYTHON_IMAGE": "python:3.12.11-slim-bookworm",
        "POSTGRES_IMAGE": "postgres:17.6-bookworm",
        "MLFLOW_IMAGE": "ghcr.io/mlflow/mlflow:v3.3.2",
        "PROMETHEUS_IMAGE": "prom/prometheus:v3.5.0",
        "GRAFANA_IMAGE": "grafana/grafana:12.1.1",
        "MDCP_VALIDATOR_INPUT_DIR": str(
            REPOSITORY_ROOT / "tests" / "fixtures" / "artifacts" / "stable"
        ),
        "MDCP_VALIDATOR_SNAPSHOT_DIR": str(
            REPOSITORY_ROOT / "tests" / "fixtures" / "validator"
        ),
        "MDCP_VALIDATOR_OUTPUT_DIR": str(REPOSITORY_ROOT / "runtime"),
    }
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(REPOSITORY_ROOT / "compose.feasibility.yaml"),
            "--profile",
            "validator",
            "config",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    return json.loads(completed.stdout)["services"]["validator"]


def test_validator_compose_profile_matches_resource_contract() -> None:
    service = _compose_config()

    assert service["profiles"] == ["validator"]
    assert service["user"] == VALIDATOR_SECURITY.user
    assert service["read_only"] is VALIDATOR_SECURITY.read_only
    assert service["network_mode"] == VALIDATOR_SECURITY.network_mode
    assert service["cpus"] == VALIDATOR_SECURITY.cpu_cores
    assert int(service["mem_limit"]) == VALIDATOR_SECURITY.memory_mib * 1024 * 1024
    assert service["pids_limit"] == VALIDATOR_SECURITY.pids_limit
    assert service["restart"] == "no"
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
