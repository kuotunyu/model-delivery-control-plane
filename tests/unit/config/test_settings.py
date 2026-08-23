import json
import logging

import pytest

from mdcp.config.logging import JsonFormatter
from mdcp.config.settings import Settings


def test_frozen_performance_defaults() -> None:
    settings = Settings()

    assert settings.predictor_cpus == 1.0
    assert settings.predictor_memory_mib == 384
    assert settings.memory_policy_mib == 256
    assert settings.admission_rate_rps == 80
    assert settings.max_in_flight == 32


def test_load_rejects_mutable_latest_image(tmp_path) -> None:
    versions = tmp_path / "versions.env"
    versions.write_text(
        "POSTGRES_IMAGE=postgres:latest\n"
        "MLFLOW_IMAGE=ghcr.io/mlflow/mlflow:v3.3.2\n"
        "PROMETHEUS_IMAGE=prom/prometheus:v3.5.0\n"
        "GRAFANA_IMAGE=grafana/grafana:12.1.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="mutable latest tag"):
        Settings.load(versions)


def test_json_formatter_redacts_nested_sensitive_values() -> None:
    record = logging.LogRecord(
        name="mdcp",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg={"event": "probe", "token": "abc", "nested": {"private_key": "xyz"}},
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload == {
        "event": "probe",
        "level": "INFO",
        "logger": "mdcp",
        "nested": {"private_key": "[REDACTED]"},
        "token": "[REDACTED]",
    }
