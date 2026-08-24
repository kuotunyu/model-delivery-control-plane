from __future__ import annotations

import math

import pytest

from mdcp.contracts.workload import BikeRequestV2
from mdcp.temporal.adapter import (
    TemporalContractError,
    TemporalReasonCode,
    adapt_v2,
)
from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS

ORIGIN_PAYLOAD = {
    "schema_version": "mdcp.bike-request.v2",
    "request_id": "origin",
    "event_timestamp": "2011-01-01T00:00:00-05:00",
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


def _request(stamp: str, **updates: object) -> BikeRequestV2:
    return BikeRequestV2.model_validate({**ORIGIN_PAYLOAD, "event_timestamp": stamp, **updates})


def test_origin_vector_is_exact_and_contains_only_ordered_model_fields() -> None:
    vector = adapt_v2(BikeRequestV2.model_validate(ORIGIN_PAYLOAD))

    assert vector.names == TEMPORAL_FEATURE_COLUMNS
    assert len(vector.values) == 18
    assert vector.values[:12] == (
        1.0,
        1.0,
        0.0,
        0.0,
        6.0,
        0.0,
        1.0,
        0.24,
        0.2879,
        0.81,
        0.0,
        0.0,
    )
    assert vector.values[12:] == pytest.approx((0.0, 1.0, -0.7818314825, 0.6234898019, 0.0, 1.0))
    assert not {
        "event_timestamp",
        "yr",
        "dteday",
        "instant",
        "casual",
        "registered",
        "cnt",
    }.intersection(vector.names)


@pytest.mark.parametrize(
    ("stamp", "updates", "expected_elapsed_days"),
    [
        (
            "2011-12-31T23:00:00-05:00",
            {"mnth": 12, "hr": 23, "weekday": 6},
            364.0 + 23.0 / 24.0,
        ),
        (
            "2012-02-29T12:00:00-05:00",
            {"mnth": 2, "hr": 12, "weekday": 3},
            424.5,
        ),
    ],
)
def test_elapsed_days_uses_local_civil_calendar(
    stamp: str, updates: dict[str, object], expected_elapsed_days: float
) -> None:
    vector = adapt_v2(_request(stamp, **updates))

    assert vector.values[11] == expected_elapsed_days
    assert vector.values[12] == pytest.approx(math.sin(2 * math.pi * updates["hr"] / 24))
    assert vector.values[17] == pytest.approx(
        math.cos(2 * math.pi * expected_elapsed_days / 365.2425)
    )


@pytest.mark.parametrize(
    ("stamp", "updates"),
    [
        ("2011-03-13T01:00:00-05:00", {"mnth": 3, "hr": 1, "weekday": 0}),
        ("2011-03-13T03:00:00-04:00", {"mnth": 3, "hr": 3, "weekday": 0}),
        ("2011-11-06T01:00:00-04:00", {"mnth": 11, "hr": 1, "weekday": 0}),
        ("2011-11-06T01:00:00-05:00", {"mnth": 11, "hr": 1, "weekday": 0}),
    ],
)
def test_valid_new_york_dst_offsets_round_trip(stamp: str, updates: dict[str, object]) -> None:
    vector = adapt_v2(_request(stamp, **updates))

    assert vector.names == TEMPORAL_FEATURE_COLUMNS


@pytest.mark.parametrize(
    ("stamp", "updates"),
    [
        ("2011-03-13T02:00:00-05:00", {"mnth": 3, "hr": 2, "weekday": 0}),
        ("2011-03-13T02:00:00-04:00", {"mnth": 3, "hr": 2, "weekday": 0}),
        ("2011-11-06T01:00:00-06:00", {"mnth": 11, "hr": 1, "weekday": 0}),
    ],
)
def test_nonexistent_or_wrong_ambiguous_offset_fails_closed(
    stamp: str, updates: dict[str, object]
) -> None:
    with pytest.raises(TemporalContractError) as caught:
        adapt_v2(_request(stamp, **updates))

    assert caught.value.reason_code is TemporalReasonCode.INVALID_EVENT_TIMESTAMP
    assert stamp not in str(caught.value)
    assert stamp not in repr(caught.value)


@pytest.mark.parametrize(
    ("stamp", "updates"),
    [
        ("2010-12-31T23:00:00-05:00", {"mnth": 12, "hr": 23, "weekday": 5}),
        ("2013-01-01T00:00:00-05:00", {"mnth": 1, "hr": 0, "weekday": 2}),
    ],
)
def test_out_of_range_is_fixed_reason(stamp: str, updates: dict[str, object]) -> None:
    with pytest.raises(TemporalContractError) as caught:
        adapt_v2(_request(stamp, **updates))

    assert caught.value.reason_code is TemporalReasonCode.EVENT_TIMESTAMP_OUT_OF_RANGE
    assert stamp not in str(caught.value)


@pytest.mark.parametrize(
    ("stamp", "updates", "reason"),
    [
        (
            "2011-01-01T00:30:00-05:00",
            {},
            TemporalReasonCode.INVALID_EVENT_TIMESTAMP,
        ),
        (
            "2011-01-01T00:00:01-05:00",
            {},
            TemporalReasonCode.INVALID_EVENT_TIMESTAMP,
        ),
        (
            "2011-01-01 00:00:00-05:00",
            {},
            TemporalReasonCode.INVALID_EVENT_TIMESTAMP,
        ),
        (
            "2011-01-01T00:00:00-04:00",
            {},
            TemporalReasonCode.INVALID_EVENT_TIMESTAMP,
        ),
        (
            "2011-01-01T00:00:00-05:00",
            {"mnth": 2},
            TemporalReasonCode.TEMPORAL_FIELD_MISMATCH,
        ),
        (
            "2011-01-01T00:00:00-05:00",
            {"hr": 1},
            TemporalReasonCode.TEMPORAL_FIELD_MISMATCH,
        ),
        (
            "2011-01-01T00:00:00-05:00",
            {"weekday": 5},
            TemporalReasonCode.TEMPORAL_FIELD_MISMATCH,
        ),
    ],
)
def test_invalid_timestamp_or_cross_field_mismatch_has_fixed_reason(
    stamp: str,
    updates: dict[str, object],
    reason: TemporalReasonCode,
) -> None:
    with pytest.raises(TemporalContractError) as caught:
        adapt_v2(_request(stamp, **updates))

    assert caught.value.reason_code is reason
    assert caught.value.args == (reason.value,)
