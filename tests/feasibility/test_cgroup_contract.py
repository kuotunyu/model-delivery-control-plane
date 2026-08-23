from __future__ import annotations

import errno
import os

import pytest

from mdcp.feasibility.cgroup import (
    CgroupObservation,
    EvidenceUnavailable,
    MeasurementMode,
    ResetCapabilityVerdict,
    build_probe_result,
    prove_fd_local_reset,
)
from mdcp.feasibility.resource_probe import build_resource_document, observe_exact_files

EXPECTED_PHASES = frozenset({"container_start", "model_load", "warmup", "scenario_end"})


def _valid_observation() -> CgroupObservation:
    return CgroupObservation(
        kernel="6.6.114.1-microsoft-standard-WSL2",
        cgroup_version=2,
        memory_current_bytes=64 * 1024 * 1024,
        memory_peak_bytes=128 * 1024 * 1024,
        memory_max_bytes=384 * 1024 * 1024,
        cpu_max="100000 100000",
        candidate_container_identity="candidate-runtime-identity",
        route_revision=1,
        window_id="wave0-cgroup-window",
        fresh_candidate=True,
        captured_phases=EXPECTED_PHASES,
        docker_socket_present=False,
    )


def test_read_only_peak_selects_fresh_whole_lifetime_mode() -> None:
    result = build_probe_result(
        _valid_observation(), ResetCapabilityVerdict.UNSUPPORTED_READ_ONLY
    )

    assert result.verdict == "PASS"
    assert result.measurement_mode is MeasurementMode.WHOLE_LIFETIME_PEAK_UPPER_BOUND
    assert result.reset_capability_verdict is ResetCapabilityVerdict.UNSUPPORTED_READ_ONLY
    assert result.fresh_candidate is True
    assert result.captured_phases == EXPECTED_PHASES
    assert len(result.candidate_cgroup_identity_digest) == 64
    assert len(result.evidence_digest) == 64


def test_same_fd_proof_selects_post_warmup_mode() -> None:
    result = build_probe_result(_valid_observation(), ResetCapabilityVerdict.SUPPORTED_SAME_FD)

    assert result.verdict == "PASS"
    assert result.measurement_mode is MeasurementMode.FD_LOCAL_POST_WARMUP_PEAK


def test_claimed_reset_without_same_fd_proof_is_unknown() -> None:
    result = build_probe_result(_valid_observation(), ResetCapabilityVerdict.PROOF_FAILED)

    assert result.verdict == "UNKNOWN"
    assert result.reason_code == "SAME_FD_PROOF_MISSING"


def test_peak_above_policy_threshold_is_fail() -> None:
    observation = _valid_observation().model_copy(
        update={"memory_peak_bytes": 256 * 1024 * 1024 + 1}
    )

    result = build_probe_result(observation, ResetCapabilityVerdict.UNSUPPORTED_READ_ONLY)

    assert result.verdict == "FAIL"
    assert result.reason_code == "MEMORY_POLICY_EXCEEDED"


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"memory_max_bytes": 256 * 1024 * 1024}, "RESOURCE_LIMIT_MISMATCH"),
        ({"cpu_max": "max 100000"}, "RESOURCE_LIMIT_MISMATCH"),
        ({"candidate_container_identity": ""}, "CANDIDATE_CGROUP_UNBOUND"),
        ({"fresh_candidate": False}, "WHOLE_LIFETIME_NOT_FRESH"),
        ({"window_id": ""}, "EVIDENCE_IDENTITY_UNBOUND"),
    ],
)
def test_enumerated_evidence_failures_are_unknown(change: dict[str, object], reason: str) -> None:
    observation = _valid_observation().model_copy(update=change)

    result = build_probe_result(observation, ResetCapabilityVerdict.UNSUPPORTED_READ_ONLY)

    assert result.verdict == "UNKNOWN"
    assert result.reason_code == reason


def test_same_fd_reset_proof_opens_peak_once(tmp_path, monkeypatch) -> None:
    peak = tmp_path / "memory.peak"
    peak.write_text("8\n", encoding="ascii")
    real_open = os.open
    open_count = 0

    def counted_open(path, flags):
        nonlocal open_count
        open_count += 1
        return real_open(path, flags)

    def allocation() -> None:
        peak.write_text("16\n", encoding="ascii")

    monkeypatch.setattr(os, "open", counted_open)
    proof = prove_fd_local_reset(peak, allocation)

    assert proof == (8, 0, 16)
    assert open_count == 1


def test_unwritable_reset_capability_is_explicit(monkeypatch, tmp_path) -> None:
    peak = tmp_path / "memory.peak"
    peak.write_text("8192\n", encoding="ascii")

    def denied_open(path, flags):
        raise OSError(errno.EROFS, "read-only file system")

    monkeypatch.setattr(os, "open", denied_open)

    with pytest.raises(EvidenceUnavailable) as error:
        prove_fd_local_reset(peak, lambda: None)

    assert error.value.reason_code == "RESET_UNSUPPORTED_READ_ONLY"


def test_exact_file_observer_reads_only_declared_cgroup_values(tmp_path) -> None:
    values = {
        "memory.current": "67108864\n",
        "memory.peak": "134217728\n",
        "memory.max": "402653184\n",
        "cpu.max": "100000 100000\n",
    }
    for name, value in values.items():
        (tmp_path / name).write_text(value, encoding="ascii")

    observed = observe_exact_files(tmp_path)

    assert observed == {
        "memory_current_bytes": 67_108_864,
        "memory_peak_bytes": 134_217_728,
        "memory_max_bytes": 402_653_184,
        "cpu_max": "100000 100000",
    }


def test_resource_document_exposes_three_sanitized_gate_results() -> None:
    document = build_resource_document(
        observation=_valid_observation(),
        reset_capability=ResetCapabilityVerdict.UNSUPPORTED_READ_ONLY,
    )

    assert [gate["name"] for gate in document["gates"]] == [
        "cgroup_v2",
        "scoped_memory_peak",
        "compose_resource_limits",
    ]
    assert all(gate["verdict"] == "PASS" for gate in document["gates"])
    assert document["memory_evidence"]["measurement_mode"] == (
        "WHOLE_LIFETIME_PEAK_UPPER_BOUND"
    )
    assert "candidate-runtime-identity" not in str(document)
