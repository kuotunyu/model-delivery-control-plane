"""Immutable historical facts and public-evidence privacy guards."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex

_PRIVATE_PATH_KEYS = frozenset(
    {
        "absolute_path",
        "host_path",
        "private_path",
        "source_absolute_path",
        "source_path",
    }
)
_CREDENTIAL_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization_header",
        "credential",
        "credentials",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "username",
    }
)
_RAW_EXCEPTION_KEYS = frozenset(
    {"error", "exception", "exception_message", "stack_trace", "traceback"}
)
_RAW_ENVIRONMENT_KEYS = frozenset(
    {"env", "environment", "environment_dump", "hostname", "raw_environment"}
)
_CONTAINER_ID_KEYS = frozenset({"container_id", "docker_container_id"})
_OPAQUE_PAYLOAD_KEYS = frozenset({"evidence_payload", "opaque_payload", "payload", "raw_payload"})
_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"[A-Za-z]:[\\/]"
    r"|\\\\[^\\/\s]+[\\/][^\\/\s]+"
    r"|/(?:root|home|Users|mnt|tmp|var/tmp|private|Volumes)(?=/|\s|$)"
    r")"
)
_CREDENTIAL_VALUE = re.compile(
    r"(?:"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    r"|\bBearer[ \t]+[A-Za-z0-9._~+/=-]{16,}"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,255}\b"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,255}\b"
    r"|\bhf_[A-Za-z0-9]{20,255}\b"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    r")",
    re.IGNORECASE,
)
_RAW_EXCEPTION_VALUE = re.compile(
    r"(?:"
    r"Traceback\s+\(most recent call last\):"
    r"|(?:^|[\s:;,])(?:[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception)):\s+\S"
    r")",
    re.MULTILINE,
)
_ENVIRONMENT_ASSIGNMENT_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=[^\r\n]*$", re.MULTILINE)


@dataclass(frozen=True)
class HistoricalLedger:
    """Public-safe immutable facts carried forward from v0.1 and its audits."""

    v1_h1_verdict: str
    v1_overall_point_ratio: float
    v1_overall_ucb95: float
    v1_off_peak_ucb95: float
    v1_reason_codes: tuple[str, ...]
    candidate_v2_verdict: str
    candidate_v2_overall_point_ratio: float
    candidate_v2_overall_ucb95: float
    h1_role: str
    h1_globally_blind: bool
    h2_status: str
    h2_loaded_rows: int
    preserved_evidence_class: str
    preserved_payload_file_count: int
    preserved_payload_total_bytes: int
    preserved_payload_inventory_sha256: str
    preservation_receipt_sha256: str
    final_sha256sums_sha256: str
    source_destination_byte_equivalence: str

    @classmethod
    def frozen_v02(cls) -> HistoricalLedger:
        return cls(
            v1_h1_verdict="FAIL",
            v1_overall_point_ratio=0.9941709085547193,
            v1_overall_ucb95=1.0132761747618493,
            v1_off_peak_ucb95=1.0514487756867108,
            v1_reason_codes=(
                "OVERALL_RATIO",
                "OVERALL_UCB95",
                "SUBGROUP_UCB95:demand_off_peak",
            ),
            candidate_v2_verdict="NO_ELIGIBLE_CANDIDATE",
            candidate_v2_overall_point_ratio=1.024486,
            candidate_v2_overall_ucb95=1.049456,
            h1_role="OBSERVED_DEVELOPMENT_ONLY",
            h1_globally_blind=False,
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
            preserved_evidence_class="natural_rejection_evidence",
            preserved_payload_file_count=22_236,
            preserved_payload_total_bytes=585_295_509,
            preserved_payload_inventory_sha256=(
                "fc39f69fe0fcf7ac49f60348ce3198ba04199026269eb45ec26b49865775a30f"
            ),
            preservation_receipt_sha256=(
                "bca375202663af8245f8f27496ea44e7c5cf9f7ea0aa1e76176d23deef01cc9a"
            ),
            final_sha256sums_sha256=(
                "ea26df010ba2e73aed88ed462b3843a0084356010465a055e04a5c87c70a5fad"
            ),
            source_destination_byte_equivalence="PASS",
        )

    def content_digest(self) -> str:
        document = asdict(self)
        document["v1_reason_codes"] = list(self.v1_reason_codes)
        return sha256_hex(canonicalize_json(document))


def _key_violation(key: str) -> str | None:
    normalized = key.casefold().replace("-", "_")
    if normalized in _PRIVATE_PATH_KEYS:
        return "PRIVATE_PATH"
    if normalized in _CREDENTIAL_KEYS:
        return "CREDENTIAL"
    if normalized in _RAW_EXCEPTION_KEYS:
        return "RAW_EXCEPTION"
    if normalized in _RAW_ENVIRONMENT_KEYS:
        return "RAW_ENVIRONMENT"
    if normalized in _CONTAINER_ID_KEYS:
        return "CONTAINER_ID"
    if normalized in _OPAQUE_PAYLOAD_KEYS:
        return "OPAQUE_PAYLOAD"
    return None


def public_evidence_violations(value: object) -> tuple[str, ...]:
    """Return fixed violation codes without retaining or echoing offending values."""
    violations: set[str] = set()
    active_container_ids: set[int] = set()

    def walk(current: object) -> None:
        if isinstance(current, str):
            if _ABSOLUTE_PATH.search(current):
                violations.add("PRIVATE_PATH")
            if _CREDENTIAL_VALUE.search(current):
                violations.add("CREDENTIAL")
            if _RAW_EXCEPTION_VALUE.search(current):
                violations.add("RAW_EXCEPTION")
            if len(_ENVIRONMENT_ASSIGNMENT_LINE.findall(current)) >= 2:
                violations.add("RAW_ENVIRONMENT")
            return
        if current is None or isinstance(current, bool | int | float):
            return
        if isinstance(current, bytes | bytearray):
            violations.add("OPAQUE_PAYLOAD")
            return

        container_id = id(current)
        if container_id in active_container_ids:
            violations.add("OPAQUE_PAYLOAD")
            return

        if isinstance(current, Mapping):
            active_container_ids.add(container_id)
            for key, nested in current.items():
                if not isinstance(key, str):
                    violations.add("OPAQUE_PAYLOAD")
                else:
                    if code := _key_violation(key):
                        violations.add(code)
                walk(nested)
            active_container_ids.remove(container_id)
            return
        if isinstance(current, Sequence):
            active_container_ids.add(container_id)
            for nested in current:
                walk(nested)
            active_container_ids.remove(container_id)
            return
        violations.add("OPAQUE_PAYLOAD")

    walk(value)
    return tuple(sorted(violations))
