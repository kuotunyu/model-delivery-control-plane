from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from mdcp.contracts.workload import BikeRequest
from mdcp.contracts.workload_v2 import BikeRequestV2
from mdcp.temporal.adapter import TemporalFeatureVector
from mdcp.temporal.routing import AdmissionKind, classify_envelope

VALID_V1 = {
    "request_id": "routing-v1",
    "season": 1,
    "mnth": 1,
    "hr": 0,
    "holiday": 0,
    "weekday": 6,
    "workingday": 0,
    "weathersit": 1,
    "temp": 0.24,
    "atemp": 0.2879,
    "hum": 0.81,
    "windspeed": 0.0,
}
VALID_V2 = {
    **VALID_V1,
    "request_id": "routing-v2",
    "schema_version": "mdcp.bike-request.v2",
    "event_timestamp": "2011-01-01T00:00:00-05:00",
}


@pytest.mark.parametrize(
    ("payload", "kind"),
    [
        (VALID_V1, AdmissionKind.LEGACY_STABLE_ONLY),
        (VALID_V2, AdmissionKind.V2_CANDIDATE_ELIGIBLE),
        (
            {**VALID_V1, "event_timestamp": VALID_V2["event_timestamp"]},
            AdmissionKind.INVALID_V2,
        ),
        (
            {**VALID_V1, "schema_version": "mdcp.bike-request.v2"},
            AdmissionKind.INVALID_V2,
        ),
        (
            {**VALID_V2, "schema_version": "mdcp.bike-request.v3"},
            AdmissionKind.INVALID_V2,
        ),
    ],
)
def test_admission_truth_table(payload: dict[str, object], kind: AdmissionKind) -> None:
    assert classify_envelope(payload).kind is kind


def test_legacy_and_v2_decisions_expose_only_their_own_typed_inputs() -> None:
    legacy = classify_envelope(VALID_V1)
    candidate = classify_envelope(VALID_V2)

    assert isinstance(legacy.legacy_request, BikeRequest)
    assert legacy.v2_request is None
    assert legacy.feature_vector is None
    assert isinstance(candidate.v2_request, BikeRequestV2)
    assert isinstance(candidate.feature_vector, TemporalFeatureVector)
    assert candidate.legacy_request is None
    assert candidate.reason_code is None


@pytest.mark.parametrize(
    ("payload", "reason_code"),
    [
        ({**VALID_V1, "schema_version": "mdcp.bike-request.v2"}, "MISSING_EVENT_TIMESTAMP"),
        ({**VALID_V1, "event_timestamp": VALID_V2["event_timestamp"]}, "INVALID_V2_ENVELOPE"),
        ({**VALID_V2, "schema_version": "mdcp.bike-request.v3"}, "INVALID_V2_ENVELOPE"),
        (
            {
                **VALID_V2,
                "event_timestamp": "2011-03-13T02:00:00-05:00",
                "mnth": 3,
                "hr": 2,
                "weekday": 0,
            },
            "INVALID_EVENT_TIMESTAMP",
        ),
    ],
)
def test_declared_invalid_v2_is_sanitized_and_never_reclassified_as_legacy(
    payload: dict[str, object], reason_code: str
) -> None:
    decision = classify_envelope(payload)

    assert decision.kind is AdmissionKind.INVALID_V2
    assert decision.reason_code == reason_code
    assert decision.legacy_request is None
    assert decision.v2_request is None
    assert decision.feature_vector is None
    assert repr(payload) not in repr(decision)


def test_invalid_unmarked_legacy_payload_remains_a_legacy_validation_error() -> None:
    invalid = deepcopy(VALID_V1)
    invalid["cnt"] = 99

    with pytest.raises(ValidationError):
        classify_envelope(invalid)
