from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex

REQUIRED_GATE_ORDER = (
    "cgroup_v2",
    "scoped_memory_peak",
    "compose_resource_limits",
    "load_harness",
    "rfc8785_ed25519_vectors",
    "postgres_atomic_transition",
    "reviewer_stack_budget",
    "github_supply_chain_research",
)
REQUIRED_GATES = frozenset(REQUIRED_GATE_ORDER)
CGROUP_SUMMARY_FIELDS = frozenset(
    {
        "measurement_mode",
        "kernel",
        "cgroup_version",
        "memory_current_bytes",
        "memory_peak_bytes",
        "memory_max_bytes",
        "cpu_max",
        "candidate_cgroup_identity_digest",
        "reset_capability_verdict",
        "fresh_candidate",
    }
)


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class PublicEvidenceError(ValueError):
    pass


class FeasibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    verdict: GateStatus
    evidence_digest: str
    evidence_identity: str
    summary: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("evidence digest must be lowercase SHA-256 hex")
        return value


class Wave0Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "mdcp.feasibility.wave0.v1"
    evidence_class: str = "FEASIBILITY"
    generated_at: datetime
    verdict: GateStatus
    next_wave_allowed: bool
    results: list[FeasibilityResult]
    report_digest: str

    @field_validator("report_digest")
    @classmethod
    def validate_report_digest(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("report digest must be lowercase SHA-256 hex")
        return value


def _public_payload(report: Wave0Report) -> dict[str, Any]:
    return report.model_dump(mode="json", exclude={"report_digest"})


def _validate_public_boundary(value: Any, *, key: str = "") -> None:
    forbidden_keys = {
        "container_id",
        "raw_container_id",
        "hostname",
        "secret",
        "password",
        "environment_dump",
        "raw_environment",
    }
    if key.lower() in forbidden_keys:
        raise PublicEvidenceError(f"forbidden public evidence field: {key}")
    if isinstance(value, dict):
        for nested_key, nested_value in value.items():
            _validate_public_boundary(nested_value, key=str(nested_key))
    elif isinstance(value, list):
        for nested in value:
            _validate_public_boundary(nested, key=key)
    elif isinstance(value, str) and re.search(
        r"(?i)(?:^|[\s\"'])(?:[a-z]:\\|/users/|/home/)", value
    ):
        raise PublicEvidenceError("absolute host path in public evidence")


class Wave0Gate:
    @classmethod
    def evaluate(
        cls,
        results: Sequence[FeasibilityResult],
        *,
        generated_at: datetime,
    ) -> Wave0Report:
        _validate_public_boundary([result.model_dump(mode="json") for result in results])
        names = [result.name for result in results]
        duplicate_or_extra = len(names) != len(set(names)) or not set(names) <= REQUIRED_GATES
        by_name = {result.name: result for result in results if result.name in REQUIRED_GATES}
        normalized: list[FeasibilityResult] = []
        for name in REQUIRED_GATE_ORDER:
            result = by_name.get(name)
            missing = result is None
            if result is None:
                result = FeasibilityResult(
                    name=name,
                    verdict=GateStatus.UNKNOWN,
                    evidence_digest=sha256_hex(f"missing:{name}".encode("ascii")),
                    evidence_identity=f"missing/{name}",
                )
            if name in {
                "cgroup_v2",
                "scoped_memory_peak",
                "compose_resource_limits",
            } and not missing and not set(result.summary) >= CGROUP_SUMMARY_FIELDS:
                result = result.model_copy(update={"verdict": GateStatus.FAIL})
            normalized.append(result)
        passed = not duplicate_or_extra and all(
            result.verdict is GateStatus.PASS for result in normalized
        )
        without_digest = {
            "schema_version": "mdcp.feasibility.wave0.v1",
            "evidence_class": "FEASIBILITY",
            "generated_at": generated_at,
            "verdict": GateStatus.PASS if passed else GateStatus.FAIL,
            "next_wave_allowed": passed,
            "results": [result.model_dump(mode="json") for result in normalized],
        }
        report = Wave0Report(
            **without_digest,
            report_digest=sha256_hex(canonicalize_json(_json_mode(without_digest))),
        )
        _validate_public_boundary(report.model_dump(mode="json"))
        return report


def _json_mode(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_mode(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_mode(nested) for nested in value]
    return value


def verify_report(report: Wave0Report) -> None:
    _validate_public_boundary(report.model_dump(mode="json"))
    if [result.name for result in report.results] != list(REQUIRED_GATE_ORDER):
        raise ValueError("report does not contain the exact ordered gate set")
    expected_verdict = (
        GateStatus.PASS
        if all(result.verdict is GateStatus.PASS for result in report.results)
        else GateStatus.FAIL
    )
    if report.verdict is not expected_verdict:
        raise ValueError("aggregate verdict does not match gate results")
    if report.next_wave_allowed != (report.verdict is GateStatus.PASS):
        raise ValueError("next-wave decision does not match verdict")
    expected_digest = sha256_hex(canonicalize_json(_public_payload(report)))
    if report.report_digest != expected_digest:
        raise ValueError("report digest mismatch")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _logical_identity(kind: str, path: Path) -> str:
    return f"wave0/{kind}@sha256:{_file_sha256(path)}"


def _read_document(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("evidence document must be an object")
    return value


def evaluate_research(research_path: Path) -> FeasibilityResult:
    research = research_path.read_text(encoding="utf-8")
    required_checks = (
        "Retrieved: 2026-08-24",
        "packages: write",
        "attestations: write",
        "id-token: write",
        "No remote mutation performed",
    )
    urls = re.findall(r"https://[^)\s]+", research)
    official_sources = len(urls) >= 4 and {
        urlparse(url).hostname for url in urls
    } == {"docs.github.com"}
    research_digest = _file_sha256(research_path)
    return FeasibilityResult(
        name="github_supply_chain_research",
        verdict=(
            GateStatus.PASS
            if official_sources and all(check in research for check in required_checks)
            else GateStatus.FAIL
        ),
        evidence_digest=research_digest,
        evidence_identity=(
            "docs/research/github-supply-chain-capability.md"
            f"@sha256:{research_digest}"
        ),
        summary={
            "retrieved": "2026-08-24",
            "official_source_count": len(urls),
            "remote_mutation_performed": False,
        },
    )


def assemble_results(
    *,
    cgroup_path: Path,
    load_path: Path,
    crypto_root: Path,
    atomic_path: Path,
    stack_path: Path,
    research_path: Path,
) -> list[FeasibilityResult]:
    results: list[FeasibilityResult] = []
    cgroup = _read_document(cgroup_path)
    memory_summary = {
        key: cgroup["memory_evidence"][key] for key in sorted(CGROUP_SUMMARY_FIELDS)
    }
    for gate in cgroup["gates"]:
        results.append(
            FeasibilityResult(
                **gate,
                evidence_identity=_logical_identity("cgroup-resource", cgroup_path),
                summary=memory_summary,
            )
        )

    for kind, path in (
        ("load-harness", load_path),
        ("atomic-transition", atomic_path),
        ("stack-budget", stack_path),
    ):
        document = _read_document(path)
        results.append(
            FeasibilityResult(
                **document["gate"],
                evidence_identity=_logical_identity(kind, path),
                summary=document["result"],
            )
        )

    payload = parse_json_bytes((crypto_root / "route-plan-v1.json").read_bytes())
    canonical = canonicalize_json(payload)
    canonical_hex = (crypto_root / "route-plan-v1.canonical.hex").read_text(
        encoding="ascii"
    ).strip()
    public_key = bytes.fromhex(
        (crypto_root / "route-plan-v1.public.hex").read_text(encoding="ascii").strip()
    )
    signature = bytes.fromhex(
        (crypto_root / "route-plan-v1.signature.hex").read_text(encoding="ascii").strip()
    )
    if canonical.hex() != canonical_hex:
        raise ValueError("crypto canonical vector mismatch")
    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, canonical)
    crypto_evidence = {
        "canonical_sha256": sha256_hex(canonical),
        "public_key_fingerprint": sha256_hex(public_key),
        "signature_sha256": sha256_hex(signature),
    }
    crypto_digest = sha256_hex(canonicalize_json(crypto_evidence))
    results.append(
        FeasibilityResult(
            name="rfc8785_ed25519_vectors",
            verdict=GateStatus.PASS,
            evidence_digest=crypto_digest,
            evidence_identity=f"fixtures/route-plan-v1@sha256:{crypto_digest}",
            summary=crypto_evidence,
        )
    )

    results.append(evaluate_research(research_path))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--cgroup", type=Path)
    parser.add_argument("--load", type=Path)
    parser.add_argument("--crypto-root", type=Path)
    parser.add_argument("--atomic", type=Path)
    parser.add_argument("--stack", type=Path)
    parser.add_argument("--research", type=Path)
    args = parser.parse_args()
    try:
        if args.assemble:
            required_paths = (
                args.cgroup,
                args.load,
                args.crypto_root,
                args.atomic,
                args.stack,
                args.research,
            )
            if any(path is None for path in required_paths):
                raise ValueError("assemble mode requires every evidence input")
            results = assemble_results(
                cgroup_path=args.cgroup,
                load_path=args.load,
                crypto_root=args.crypto_root,
                atomic_path=args.atomic,
                stack_path=args.stack,
                research_path=args.research,
            )
            report = Wave0Gate.evaluate(results, generated_at=datetime.now(UTC))
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(
                    report.model_dump(mode="json"),
                    indent=2,
                    ensure_ascii=True,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            report = Wave0Report.model_validate_json(args.report.read_text(encoding="utf-8"))
        verify_report(report)
    except Exception:
        print("WAVE0 FAIL")
        return 1
    passed = sum(result.verdict is GateStatus.PASS for result in report.results)
    print(f"WAVE0 {report.verdict.value} {passed}/8")
    return 0 if report.verdict is GateStatus.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
