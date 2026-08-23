from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_IMAGE_FIELDS = {
    "POSTGRES_IMAGE": "postgres_image",
    "MLFLOW_IMAGE": "mlflow_image",
    "PROMETHEUS_IMAGE": "prometheus_image",
    "GRAFANA_IMAGE": "grafana_image",
}


class Settings(BaseSettings):
    """Frozen Wave 0 settings and digest-qualified infrastructure images."""

    model_config = SettingsConfigDict(frozen=True, extra="forbid")

    predictor_cpus: Literal[1.0] = 1.0
    predictor_memory_mib: Literal[384] = 384
    memory_policy_mib: Literal[256] = 256
    admission_rate_rps: Literal[80] = 80
    max_in_flight: Literal[32] = 32

    postgres_image: str = "postgres:16.10-bookworm"
    mlflow_image: str = "ghcr.io/mlflow/mlflow:v3.3.2"
    prometheus_image: str = "prom/prometheus:v3.5.0"
    grafana_image: str = "grafana/grafana:12.1.0"

    @classmethod
    def load(cls, versions_path: Path | str = Path("constraints/versions.env")) -> Settings:
        values = _read_versions(Path(versions_path))
        missing = _IMAGE_FIELDS.keys() - values.keys()
        if missing:
            raise ValueError(f"missing image references: {', '.join(sorted(missing))}")
        for name, reference in values.items():
            if _uses_latest_tag(reference):
                raise ValueError(f"{name} uses mutable latest tag")
        return cls(**{field: values[key] for key, field in _IMAGE_FIELDS.items()})


def _read_versions(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid versions.env line {line_number}")
        key, value = line.split("=", 1)
        if key in values:
            raise ValueError(f"duplicate image key: {key}")
        values[key] = value
    return values


def _uses_latest_tag(reference: str) -> bool:
    name_and_tag = reference.split("@", 1)[0]
    return name_and_tag.rsplit("/", 1)[-1].endswith(":latest")
