from __future__ import annotations

import errno
import hashlib
import json
import os
import platform
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

MIB = 1024 * 1024
EXPECTED_MEMORY_MAX_BYTES = 384 * MIB
EXPECTED_CPU_MAX = "100000 100000"
MEMORY_POLICY_BYTES = 256 * MIB
WHOLE_LIFETIME_PHASES = frozenset(
    {"container_start", "model_load", "warmup", "scenario_end"}
)


class MeasurementMode(StrEnum):
    FD_LOCAL_POST_WARMUP_PEAK = "FD_LOCAL_POST_WARMUP_PEAK"
    WHOLE_LIFETIME_PEAK_UPPER_BOUND = "WHOLE_LIFETIME_PEAK_UPPER_BOUND"


class ResetCapabilityVerdict(StrEnum):
    SUPPORTED_SAME_FD = "SUPPORTED_SAME_FD"
    UNSUPPORTED_READ_ONLY = "UNSUPPORTED_READ_ONLY"
    PROOF_FAILED = "PROOF_FAILED"


class EvidenceUnavailable(RuntimeError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class CgroupFiles(BaseModel):
    model_config = ConfigDict(frozen=True)

    memory_current_bytes: int
    memory_peak_bytes: int
    memory_max_bytes: int
    cpu_max: str


class CgroupObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    kernel: str
    cgroup_version: int
    memory_current_bytes: int | None
    memory_peak_bytes: int | None
    memory_max_bytes: int | None
    cpu_max: str | None
    candidate_container_identity: str
    route_revision: int | None
    window_id: str
    fresh_candidate: bool
    captured_phases: frozenset[str]
    docker_socket_present: bool


class CgroupProbeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    verdict: str
    reason_code: str
    measurement_mode: MeasurementMode | None
    kernel: str
    cgroup_version: int
    memory_current_bytes: int | None
    memory_peak_bytes: int | None
    memory_max_bytes: int | None
    cpu_max: str | None
    candidate_cgroup_identity_digest: str
    reset_capability_verdict: ResetCapabilityVerdict
    fresh_candidate: bool
    captured_phases: frozenset[str]
    docker_socket_present: bool
    route_revision: int | None
    window_id: str
    evidence_digest: str


def read_int_same_fd(fd: int) -> int:
    os.lseek(fd, 0, os.SEEK_SET)
    return int(os.read(fd, 64).decode("ascii").strip())


def prove_fd_local_reset(
    peak: Path, allocate: Callable[[], None]
) -> tuple[int, int, int]:
    try:
        fd = os.open(peak, os.O_RDWR)
    except OSError as error:
        if error.errno in {errno.EACCES, errno.EPERM, errno.EROFS}:
            raise EvidenceUnavailable("RESET_UNSUPPORTED_READ_ONLY") from error
        raise EvidenceUnavailable("MEMORY_PEAK_UNREADABLE") from error
    try:
        before = read_int_same_fd(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, b"0")
        reset_value = read_int_same_fd(fd)
        allocate()
        increased = read_int_same_fd(fd)
    except (OSError, UnicodeError, ValueError) as error:
        raise EvidenceUnavailable("SAME_FD_PROOF_MISSING") from error
    finally:
        os.close(fd)
    if not (reset_value <= before and increased > reset_value):
        raise EvidenceUnavailable("SAME_FD_PROOF_MISSING")
    return before, reset_value, increased


def read_cgroup_v2(root: Path) -> CgroupFiles:
    required = ("memory.current", "memory.peak", "memory.max", "cpu.max")
    if not all((root / name).is_file() for name in required):
        raise EvidenceUnavailable("MEMORY_PEAK_UNREADABLE")
    try:
        current = _read_int(root / "memory.current")
        peak = _read_int(root / "memory.peak")
        maximum = _read_int(root / "memory.max")
        cpu_max = (root / "cpu.max").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError, ValueError) as error:
        raise EvidenceUnavailable("MEMORY_PEAK_UNREADABLE") from error
    return CgroupFiles(
        memory_current_bytes=current,
        memory_peak_bytes=peak,
        memory_max_bytes=maximum,
        cpu_max=cpu_max,
    )


def read_resource_limits(root: Path) -> tuple[int, str]:
    files = read_cgroup_v2(root)
    return files.memory_max_bytes, files.cpu_max


def build_probe_result(
    observation: CgroupObservation,
    reset_capability: ResetCapabilityVerdict,
) -> CgroupProbeResult:
    identity_digest = _sha256(observation.candidate_container_identity.encode("utf-8"))
    mode = _mode_for(reset_capability)
    verdict, reason = _verdict(observation, reset_capability, mode)
    payload = {
        "verdict": verdict,
        "reason_code": reason,
        "measurement_mode": mode.value if mode else None,
        "kernel": observation.kernel,
        "cgroup_version": observation.cgroup_version,
        "memory_current_bytes": observation.memory_current_bytes,
        "memory_peak_bytes": observation.memory_peak_bytes,
        "memory_max_bytes": observation.memory_max_bytes,
        "cpu_max": observation.cpu_max,
        "candidate_cgroup_identity_digest": identity_digest,
        "reset_capability_verdict": reset_capability.value,
        "fresh_candidate": observation.fresh_candidate,
        "captured_phases": sorted(observation.captured_phases),
        "docker_socket_present": observation.docker_socket_present,
        "route_revision": observation.route_revision,
        "window_id": observation.window_id,
    }
    evidence_digest = _sha256(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
            "ascii"
        )
    )
    return CgroupProbeResult(**payload, evidence_digest=evidence_digest)


def observation_from_root(
    root: Path,
    *,
    candidate_container_identity: str,
    route_revision: int,
    window_id: str,
    fresh_candidate: bool,
    captured_phases: frozenset[str],
) -> CgroupObservation:
    files = read_cgroup_v2(root)
    return CgroupObservation(
        kernel=platform.release(),
        cgroup_version=2 if Path("/sys/fs/cgroup/cgroup.controllers").is_file() else 1,
        memory_current_bytes=files.memory_current_bytes,
        memory_peak_bytes=files.memory_peak_bytes,
        memory_max_bytes=files.memory_max_bytes,
        cpu_max=files.cpu_max,
        candidate_container_identity=candidate_container_identity,
        route_revision=route_revision,
        window_id=window_id,
        fresh_candidate=fresh_candidate,
        captured_phases=captured_phases,
        docker_socket_present=Path("/var/run/docker.sock").exists(),
    )


def _mode_for(reset_capability: ResetCapabilityVerdict) -> MeasurementMode | None:
    if reset_capability is ResetCapabilityVerdict.SUPPORTED_SAME_FD:
        return MeasurementMode.FD_LOCAL_POST_WARMUP_PEAK
    if reset_capability is ResetCapabilityVerdict.UNSUPPORTED_READ_ONLY:
        return MeasurementMode.WHOLE_LIFETIME_PEAK_UPPER_BOUND
    return None


def _verdict(
    observation: CgroupObservation,
    reset_capability: ResetCapabilityVerdict,
    mode: MeasurementMode | None,
) -> tuple[str, str]:
    if observation.memory_peak_bytes is None:
        return "UNKNOWN", "MEMORY_PEAK_UNREADABLE"
    if not observation.candidate_container_identity:
        return "UNKNOWN", "CANDIDATE_CGROUP_UNBOUND"
    if (
        observation.memory_max_bytes != EXPECTED_MEMORY_MAX_BYTES
        or observation.cpu_max != EXPECTED_CPU_MAX
        or observation.cgroup_version != 2
    ):
        return "UNKNOWN", "RESOURCE_LIMIT_MISMATCH"
    if reset_capability is ResetCapabilityVerdict.PROOF_FAILED or mode is None:
        return "UNKNOWN", "SAME_FD_PROOF_MISSING"
    if mode is MeasurementMode.WHOLE_LIFETIME_PEAK_UPPER_BOUND and (
        not observation.fresh_candidate
        or observation.captured_phases != WHOLE_LIFETIME_PHASES
    ):
        return "UNKNOWN", "WHOLE_LIFETIME_NOT_FRESH"
    if observation.route_revision is None or not observation.window_id:
        return "UNKNOWN", "EVIDENCE_IDENTITY_UNBOUND"
    if observation.memory_peak_bytes > MEMORY_POLICY_BYTES:
        return "FAIL", "MEMORY_POLICY_EXCEEDED"
    return "PASS", "AUTHORITATIVE_MEMORY_PEAK"


def _read_int(path: Path) -> int:
    return int(path.read_text(encoding="ascii").strip())


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
