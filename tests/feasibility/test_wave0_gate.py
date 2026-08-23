from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mdcp.feasibility.gate import (
    REQUIRED_GATES,
    FeasibilityResult,
    GateStatus,
    PublicEvidenceError,
    Wave0Gate,
    verify_report,
)

CGROUP_SUMMARY = {
    "measurement_mode": "WHOLE_LIFETIME_PEAK_UPPER_BOUND",
    "kernel": "6.6.114.1-microsoft-standard-WSL2",
    "cgroup_version": 2,
    "memory_current_bytes": 80_000_000,
    "memory_peak_bytes": 84_000_000,
    "memory_max_bytes": 384 * 1024**2,
    "cpu_max": "100000 100000",
    "candidate_cgroup_identity_digest": "b" * 64,
    "reset_capability_verdict": "UNSUPPORTED_READ_ONLY",
    "fresh_candidate": True,
}


def pass_result(name: str) -> FeasibilityResult:
    return FeasibilityResult(
        name=name,
        verdict=GateStatus.PASS,
        evidence_digest="a" * 64,
        evidence_identity=f"wave0/{name}.json",
        summary=CGROUP_SUMMARY if name in {
            "cgroup_v2",
            "scoped_memory_peak",
            "compose_resource_limits",
        } else {},
    )


def test_wave0_requires_all_named_gates() -> None:
    results = [pass_result(name) for name in REQUIRED_GATES if name != "scoped_memory_peak"]
    report = Wave0Gate.evaluate(results, generated_at=datetime(2026, 8, 24, tzinfo=UTC))

    assert report.verdict is GateStatus.FAIL
    assert report.next_wave_allowed is False
    assert len(report.results) == 8
    missing = next(result for result in report.results if result.name == "scoped_memory_peak")
    assert missing.verdict is GateStatus.UNKNOWN


def test_wave0_exact_pass_report_digest_recomputes() -> None:
    results = [pass_result(name) for name in REQUIRED_GATES]
    report = Wave0Gate.evaluate(results, generated_at=datetime(2026, 8, 24, tzinfo=UTC))

    assert report.verdict is GateStatus.PASS
    assert report.next_wave_allowed is True
    assert len(report.report_digest) == 64
    verify_report(report)


def test_public_report_rejects_absolute_host_paths() -> None:
    results = [pass_result(name) for name in REQUIRED_GATES]
    results[0] = results[0].model_copy(
        update={"evidence_identity": "C:\\Users\\reviewer\\evidence.json"}
    )

    with pytest.raises(PublicEvidenceError):
        Wave0Gate.evaluate(results, generated_at=datetime(2026, 8, 24, tzinfo=UTC))
