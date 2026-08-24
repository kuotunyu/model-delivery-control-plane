from __future__ import annotations

import importlib
import os
import random
import socket
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS

REPOSITORY_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

_temporal_fixtures = importlib.import_module("tests.temporal_fixtures")
synthetic_development_frame = _temporal_fixtures.synthetic_development_frame
synthetic_v2_payload = _temporal_fixtures.synthetic_v2_payload


def test_synthetic_rows_stop_before_h2_and_keep_target_out_of_model_schema() -> None:
    rows = synthetic_development_frame()

    assert rows.attrs == {
        "evidence_class": "synthetic_test",
        "source_kind": "deterministic_generated",
        "uci_rows": 0,
    }
    assert rows.index.min() == pd.Timestamp("2011-01-01 00:00:00")
    assert rows.index.max() == pd.Timestamp("2012-06-30 23:00:00")
    assert rows.index.max() < pd.Timestamp("2012-07-01 00:00:00")
    assert rows.index.is_monotonic_increasing
    assert len(rows.index.unique()) == len(rows)
    assert tuple(rows.columns) == (*TEMPORAL_FEATURE_COLUMNS[:11], "cnt")
    assert "cnt" not in TEMPORAL_FEATURE_COLUMNS
    assert not {"yr", "dteday", "instant", "casual", "registered"}.intersection(rows.columns)


def test_synthetic_rows_and_payloads_are_reproducible() -> None:
    first = synthetic_development_frame()
    second = synthetic_development_frame()

    pd.testing.assert_frame_equal(first, second, check_exact=True)
    assert first.attrs == second.attrs
    assert synthetic_v2_payload(datetime(2011, 1, 1), "origin") == {
        "schema_version": "mdcp.bike-request.v2",
        "request_id": "origin",
        "event_timestamp": "2011-01-01T00:00:00-05:00",
        **first.iloc[0].drop(labels="cnt").to_dict(),
    }
    assert (
        synthetic_v2_payload(datetime(2011, 7, 1), "summer")["event_timestamp"]
        == "2011-07-01T00:00:00-04:00"
    )


@pytest.mark.parametrize(
    ("local_time", "expected_offset"),
    [
        (datetime(2011, 3, 13, 1), "-05:00"),
        (datetime(2011, 3, 13, 3), "-04:00"),
        (datetime(2011, 7, 1, 12), "-04:00"),
        (datetime(2011, 11, 6, 0), "-04:00"),
        (datetime(2011, 11, 6, 2), "-05:00"),
    ],
)
def test_synthetic_payload_uses_round_trip_safe_new_york_offsets(
    local_time: datetime, expected_offset: str
) -> None:
    encoded = synthetic_v2_payload(local_time, "dst-vector")["event_timestamp"]
    assert isinstance(encoded, str)
    localized = datetime.fromisoformat(encoded)
    round_tripped = localized.astimezone(UTC).astimezone(ZoneInfo("America/New_York"))

    assert encoded.endswith(expected_offset)
    assert round_tripped.replace(tzinfo=None) == local_time
    assert round_tripped.utcoffset() == localized.utcoffset()


@pytest.mark.parametrize(
    "invalid_local_time",
    [datetime(2011, 3, 13, 2), datetime(2011, 11, 6, 1)],
)
def test_synthetic_payload_rejects_nonexistent_or_ambiguous_new_york_time(
    invalid_local_time: datetime,
) -> None:
    with pytest.raises(ValueError, match="synthetic timestamp is nonexistent or ambiguous"):
        synthetic_v2_payload(invalid_local_time, "invalid-dst-vector")


def test_generator_uses_no_external_or_nondeterministic_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("forbidden capability used")

    class ForbiddenEnvironment(dict[str, str]):
        def __getitem__(self, key: str) -> str:
            raise AssertionError(f"environment read: {key}")

        def get(self, key: str, default: str | None = None) -> str | None:
            raise AssertionError(f"environment read: {key}")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(random, "random", forbidden)
    monkeypatch.setattr(os, "urandom", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(os, "environ", ForbiddenEnvironment())

    rows = synthetic_development_frame()
    payload = synthetic_v2_payload(datetime(2012, 6, 30, 23), "last")

    assert rows.attrs["uci_rows"] == 0
    assert payload["request_id"] == "last"
