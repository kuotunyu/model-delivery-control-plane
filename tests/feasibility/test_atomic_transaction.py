from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from mdcp.feasibility.transaction_probe import AtomicTransitionProbe

REPOSITORY_ROOT = Path(__file__).parents[2]


@pytest.fixture
def probe() -> AtomicTransitionProbe:
    dsn = os.environ.get("MDCP_ATOMIC_DSN")
    if not dsn:
        pytest.skip("formal PostgreSQL profile supplies MDCP_ATOMIC_DSN")
    fixture_root = Path(
        os.environ.get(
            "MDCP_CRYPTO_FIXTURE_ROOT",
            REPOSITORY_ROOT / "tests" / "fixtures" / "crypto",
        )
    )
    sql_path = Path(
        os.environ.get(
            "MDCP_ATOMIC_SQL_PATH",
            REPOSITORY_ROOT / "tests" / "feasibility" / "sql" / "atomic_transition_probe.sql",
        )
    )
    return AtomicTransitionProbe(dsn=dsn, fixture_root=fixture_root, sql_path=sql_path)


@pytest.mark.parametrize("fault", ["route_plan_insert", "before_commit"])
def test_injected_failure_rolls_back_every_visible_row(
    probe: AtomicTransitionProbe, fault: str
) -> None:
    result = probe.run(inject_failure_at=fault)

    assert result.visible_row_counts == {
        "environment": 0,
        "release": 0,
        "route_plan": 0,
        "audit": 0,
    }
    assert result.split_state == 0


def test_success_commits_one_consistent_revision(probe: AtomicTransitionProbe) -> None:
    result = probe.run(inject_failure_at=None)

    assert result.visible_row_counts == {
        "environment": 1,
        "release": 1,
        "route_plan": 1,
        "audit": 1,
    }
    assert result.revisions == {
        "environment": 1,
        "release": 1,
        "route_plan": 1,
        "audit": 1,
    }
    assert result.split_state == 0
    assert len(result.payload_digest) == 64


def test_compose_atomic_probe_is_internal_and_evidence_scoped(tmp_path: Path) -> None:
    versions = dict(
        line.split("=", 1)
        for line in (REPOSITORY_ROOT / "constraints" / "versions.env").read_text(
            encoding="utf-8"
        ).splitlines()
        if line and not line.startswith("#")
    )
    environment = os.environ.copy()
    environment.update(
        {
            "MDCP_PYTHON_IMAGE": versions["PYTHON_IMAGE"],
            "POSTGRES_IMAGE": versions["POSTGRES_IMAGE"],
            "MDCP_ATOMIC_EVIDENCE_DIR": str(tmp_path),
        }
    )
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "--file",
            str(REPOSITORY_ROOT / "compose.feasibility.yaml"),
            "--profile",
            "atomic",
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
    database = configuration["services"]["postgres-atomic"]
    transaction = configuration["services"]["atomic-probe"]

    assert configuration["networks"]["atomic"]["internal"] is True
    for service in (database, transaction):
        assert service["networks"] == {"atomic": None}
        assert "ports" not in service
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]
    assert transaction["depends_on"] == {
        "postgres-atomic": {"condition": "service_healthy", "required": True}
    }
    assert transaction["volumes"] == [
        {
            "type": "bind",
            "source": str(tmp_path),
            "target": "/evidence",
            "bind": {"create_host_path": False},
        }
    ]
    assert all("docker.sock" not in volume["target"] for volume in transaction["volumes"])
