from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[3]


def _validator_config() -> dict:
    environment = {
        **os.environ,
        "MDCP_PYTHON_IMAGE": "python:3.12.11-slim-bookworm",
        "POSTGRES_IMAGE": "postgres:17.6-bookworm",
        "MLFLOW_IMAGE": "ghcr.io/mlflow/mlflow:v3.3.2",
        "PROMETHEUS_IMAGE": "prom/prometheus:v3.5.0",
        "GRAFANA_IMAGE": "grafana/grafana:12.1.1",
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


def test_validator_has_no_egress_privilege_or_host_control_mount() -> None:
    service = _validator_config()
    sources = tuple(volume["source"].lower() for volume in service["volumes"])

    assert service["network_mode"] == "none"
    assert service["user"] == "10001:10001"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert not any(
        "docker.sock" in source or "//./pipe/docker_engine" in source
        for source in sources
    )


def test_only_output_mount_is_writable_and_tmpfs_is_bounded() -> None:
    service = _validator_config()
    volumes = {volume["target"]: volume for volume in service["volumes"]}

    assert volumes["/input"]["read_only"] is True
    assert volumes["/snapshot"]["read_only"] is True
    assert volumes["/output"].get("read_only", False) is False
    assert set(volumes) == {"/input", "/snapshot", "/output"}
    assert service["tmpfs"] == [
        "/tmp:rw,noexec,nosuid,size=64m,mode=1777"
    ]


def test_validator_image_declares_non_root_and_hard_timeout() -> None:
    dockerfile = (REPOSITORY_ROOT / "docker" / "validator.Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "USER 10001:10001" in dockerfile
    assert 'ENTRYPOINT ["timeout", "--signal=KILL", "30s"' in dockerfile
