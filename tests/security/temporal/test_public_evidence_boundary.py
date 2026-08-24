from __future__ import annotations

import pytest

from mdcp.temporal.evidence import public_evidence_violations


def test_public_scan_rejects_private_metadata_without_echoing_values() -> None:
    secret = "PRIVATE_PATH_SENTINEL"

    assert public_evidence_violations({"host_path": secret}) == ("PRIVATE_PATH",)
    assert public_evidence_violations({"error": "raw exception text"}) == ("RAW_EXCEPTION",)
    assert secret not in repr(public_evidence_violations({"host_path": secret}))


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ({"artifact": {"source_path": "C:/private/model.onnx"}}, ("PRIVATE_PATH",)),
        ({"username": "private-user"}, ("CREDENTIAL",)),
        ({"api_key": "not-public"}, ("CREDENTIAL",)),
        ({"traceback": "stack frame"}, ("RAW_EXCEPTION",)),
        ({"raw_environment": "NAME=value"}, ("RAW_ENVIRONMENT",)),
        ({"hostname": "private-host"}, ("RAW_ENVIRONMENT",)),
        ({"container_id": "a" * 64}, ("CONTAINER_ID",)),
        ({"payload": {"row": 1}}, ("OPAQUE_PAYLOAD",)),
    ],
)
def test_public_scan_returns_fixed_low_cardinality_codes(
    document: object, expected: tuple[str, ...]
) -> None:
    assert public_evidence_violations(document) == expected


def test_public_scan_is_recursive_sorted_unique_and_allows_sanitized_aggregates() -> None:
    assert public_evidence_violations(
        {
            "nested": [
                {"error": "first"},
                {"host_path": "C:/private/one"},
                {"error": "second"},
            ]
        }
    ) == ("PRIVATE_PATH", "RAW_EXCEPTION")
    assert public_evidence_violations(
        {
            "evidence_class": "synthetic_test",
            "inventory_sha256": "a" * 64,
            "reason_codes": ["OVERALL_UCB95"],
            "metrics": {"point_ratio": 0.97, "row_count": 2400},
        }
    ) == ()
