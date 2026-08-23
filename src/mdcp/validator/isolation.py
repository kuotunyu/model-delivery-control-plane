from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ValidatorResourceLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cpu_cores: float = Field(default=0.5, gt=0, le=1.0)
    memory_mib: int = Field(default=384, ge=64, le=384)
    pids_limit: int = Field(default=128, ge=16, le=128)
    timeout_seconds: int = Field(default=30, ge=1, le=60)
    tmpfs_mib: int = Field(default=64, ge=16, le=128)
