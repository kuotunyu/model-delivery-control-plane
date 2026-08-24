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
    assert (
        public_evidence_violations(
            {
                "evidence_class": "synthetic_test",
                "inventory_sha256": "a" * 64,
                "reason_codes": ["OVERALL_UCB95"],
                "metrics": {"point_ratio": 0.97, "row_count": 2400},
            }
        )
        == ()
    )


@pytest.mark.parametrize(
    "private_path",
    [
        r"prefix C:\Users\reviewer\private\model.onnx suffix",
        "prefix C:/Users/reviewer/private/model.onnx suffix",
        r"prefix \\private-host\share\model.onnx suffix",
        "prefix /root/private/model.onnx suffix",
        "prefix /home/reviewer/model.onnx suffix",
        "prefix /Users/reviewer/model.onnx suffix",
        "prefix /mnt/private/model.onnx suffix",
        "prefix /tmp/private/model.onnx suffix",
        "prefix /var/tmp/private/model.onnx suffix",
        "prefix /private/model.onnx suffix",
        "prefix /Volumes/private/model.onnx suffix",
    ],
)
def test_public_scan_rejects_embedded_absolute_private_paths(private_path: str) -> None:
    result = public_evidence_violations({"note": private_path})

    assert result == ("PRIVATE_PATH",)
    assert private_path not in repr(result)


@pytest.mark.parametrize(
    "raw_exception",
    [
        "Traceback (most recent call last):\n  synthetic frame\nValueError: redacted",
        "request failed with InvalidResponseError: redacted",
        "unhandled RuntimeException: redacted",
        "ConnectTimeout: redacted",
        "ReadTimeout: redacted",
        "InvalidResponse: redacted",
    ],
)
def test_public_scan_rejects_raw_exceptions_under_arbitrary_keys(raw_exception: str) -> None:
    result = public_evidence_violations({"message": raw_exception})

    assert result == ("RAW_EXCEPTION",)
    assert raw_exception not in repr(result)


@pytest.mark.parametrize(
    "credential",
    [
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN ENCRYPTED PRIVATE KEY-----",
        "Bearer abc",
        "Bearer " + "a" * 32,
        "ghp_" + "A" * 36,
        "github_pat_" + "A" * 22 + "_" + "B" * 59,
        "hf_" + "a" * 34,
        "AKIA" + "A1" * 8,
    ],
)
def test_public_scan_rejects_common_credential_shapes(credential: str) -> None:
    result = public_evidence_violations({"note": credential})

    assert result == ("CREDENTIAL",)
    assert credential not in repr(result)


def test_public_scan_distinguishes_environment_dumps_from_research_assignments() -> None:
    assert public_evidence_violations({"note": "MODEL=rf\nTHREADS=1"}) == ("RAW_ENVIRONMENT",)
    assert public_evidence_violations({"note": "RATIO=0.97"}) == ()


def test_public_scan_allows_sanitized_error_class_labels_without_raw_messages() -> None:
    assert (
        public_evidence_violations(
            {
                "error_classes": [
                    "ConnectError",
                    "ConnectTimeout",
                    "ReadTimeout",
                    "ProtocolError",
                    "InvalidResponse",
                    "Other",
                ]
            }
        )
        == ()
    )
