from __future__ import annotations

import builtins
import datetime as datetime_module
import io
import os
import random
import secrets
import socket
import sys
import time
import types
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS

REPOSITORY_ROOT = Path(__file__).parents[3]
TEMPORAL_FIXTURE_PATH = REPOSITORY_ROOT / "tests" / "temporal_fixtures.py"


class _ForbiddenEnvironment:
    def _reject(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("IMPORT_CAPABILITY_ENVIRONMENT")

    __getitem__ = _reject
    get = _reject
    __iter__ = _reject
    __len__ = _reject
    keys = _reject
    items = _reject
    values = _reject
    copy = _reject


class _ForbiddenDateTime(datetime):
    @classmethod
    def now(cls, *_args: object, **_kwargs: object) -> datetime:
        raise AssertionError("IMPORT_CAPABILITY_CLOCK")

    @classmethod
    def today(cls) -> datetime:
        raise AssertionError("IMPORT_CAPABILITY_CLOCK")

    @classmethod
    def utcnow(cls) -> datetime:
        raise AssertionError("IMPORT_CAPABILITY_CLOCK")


def _blocked(capability: str) -> object:
    def reject(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(f"IMPORT_CAPABILITY_{capability}")

    return reject


def _load_fixture_module_under_import_firewall(path: Path) -> types.ModuleType:
    source = path.read_bytes()
    code = compile(source, str(path), "exec")
    module = types.ModuleType("_isolated_temporal_fixture")
    module.__file__ = str(path)
    module.__package__ = ""

    with pytest.MonkeyPatch.context() as firewall:
        filesystem = _blocked("FILESYSTEM")
        firewall.setattr(builtins, "open", filesystem)
        firewall.setattr(io, "open", filesystem)
        firewall.setattr(Path, "open", filesystem)

        network = _blocked("NETWORK")
        firewall.setattr(socket, "socket", network)
        firewall.setattr(socket, "create_connection", network)
        firewall.setattr(socket, "getaddrinfo", network)

        environment = _blocked("ENVIRONMENT")
        firewall.setattr(os, "getenv", environment)
        firewall.setattr(os, "environ", _ForbiddenEnvironment())
        if hasattr(os, "getenvb"):
            firewall.setattr(os, "getenvb", environment)
        if hasattr(os, "environb"):
            firewall.setattr(os, "environb", _ForbiddenEnvironment())

        clock = _blocked("CLOCK")
        for name in (
            "monotonic",
            "monotonic_ns",
            "perf_counter",
            "perf_counter_ns",
            "process_time",
            "process_time_ns",
            "sleep",
            "time",
            "time_ns",
        ):
            firewall.setattr(time, name, clock)
        firewall.setattr(datetime_module, "datetime", _ForbiddenDateTime)

        entropy = _blocked("ENTROPY")
        firewall.setattr(os, "urandom", entropy)
        for name in ("token_bytes", "token_hex", "token_urlsafe"):
            firewall.setattr(secrets, name, entropy)
        for name in (
            "choice",
            "choices",
            "getrandbits",
            "randint",
            "random",
            "randrange",
            "sample",
            "seed",
            "uniform",
        ):
            firewall.setattr(random, name, entropy)

        exec(code, module.__dict__)

    return module


def test_temporal_fixture_is_not_imported_before_import_firewall() -> None:
    assert "tests.temporal_fixtures" not in sys.modules
    module = _load_fixture_module_under_import_firewall(TEMPORAL_FIXTURE_PATH)

    assert callable(module.synthetic_development_frame)
    assert callable(module.synthetic_v2_payload)
    assert "tests.temporal_fixtures" not in sys.modules


@pytest.mark.parametrize(
    ("capability", "module_body"),
    [
        ("FILESYSTEM", "from pathlib import Path\nPath(__file__).read_bytes()"),
        ("NETWORK", "import socket\nsocket.socket().close()"),
        ("ENVIRONMENT", "import os\nos.getenv('PATH')"),
        ("CLOCK", "import time\ntime.time()"),
        ("ENTROPY", "import random\nrandom.random()"),
        ("ENTROPY", "import os\nos.urandom(1)"),
    ],
)
def test_import_firewall_rejects_malicious_fixture_module_bodies(
    tmp_path: Path, capability: str, module_body: str
) -> None:
    fixture_path = tmp_path / f"malicious_{capability.casefold()}.py"
    fixture_path.write_text(module_body, encoding="utf-8")

    with pytest.raises(AssertionError, match=f"IMPORT_CAPABILITY_{capability}"):
        _load_fixture_module_under_import_firewall(fixture_path)


def test_synthetic_rows_stop_before_h2_and_keep_target_out_of_model_schema() -> None:
    fixtures = _load_fixture_module_under_import_firewall(TEMPORAL_FIXTURE_PATH)
    rows = fixtures.synthetic_development_frame()

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
    fixtures = _load_fixture_module_under_import_firewall(TEMPORAL_FIXTURE_PATH)
    synthetic_development_frame = fixtures.synthetic_development_frame
    synthetic_v2_payload = fixtures.synthetic_v2_payload
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
    synthetic_v2_payload = _load_fixture_module_under_import_firewall(
        TEMPORAL_FIXTURE_PATH
    ).synthetic_v2_payload
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
    synthetic_v2_payload = _load_fixture_module_under_import_firewall(
        TEMPORAL_FIXTURE_PATH
    ).synthetic_v2_payload
    with pytest.raises(ValueError, match="synthetic timestamp is nonexistent or ambiguous"):
        synthetic_v2_payload(invalid_local_time, "invalid-dst-vector")


def test_generator_uses_no_external_or_nondeterministic_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixtures = _load_fixture_module_under_import_firewall(TEMPORAL_FIXTURE_PATH)
    synthetic_development_frame = fixtures.synthetic_development_frame
    synthetic_v2_payload = fixtures.synthetic_v2_payload

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
