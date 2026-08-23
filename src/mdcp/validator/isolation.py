from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ValidatorResourceLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cpu_cores: float = Field(default=0.5, gt=0, le=1.0)
    memory_mib: int = Field(default=384, ge=64, le=384)
    pids_limit: int = Field(default=128, ge=16, le=128)
    timeout_seconds: int = Field(default=30, ge=1, le=60)
    tmpfs_mib: int = Field(default=64, ge=16, le=128)


@dataclass(frozen=True)
class ContainerSecurity:
    user: str
    read_only: bool
    cap_drop: tuple[str, ...]
    no_new_privileges: bool
    network_mode: Literal["none"]
    cpu_cores: float
    memory_mib: int
    pids_limit: int
    timeout_seconds: int
    tmpfs_mib: int


VALIDATOR_SECURITY = ContainerSecurity(
    user="10001:10001",
    read_only=True,
    cap_drop=("ALL",),
    no_new_privileges=True,
    network_mode="none",
    cpu_cores=0.5,
    memory_mib=384,
    pids_limit=128,
    timeout_seconds=30,
    tmpfs_mib=64,
)
