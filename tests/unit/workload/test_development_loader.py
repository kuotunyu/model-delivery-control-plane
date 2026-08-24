from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

import mdcp.workload.dataset as dataset_module
from mdcp.workload.dataset import (
    EXPECTED_UCI_COLUMNS,
    DatasetIntegrityError,
    load_uci_development_archive,
)
from mdcp.workload.splits import split_development_rows

DEVELOPMENT_ROWS = 13_003
TRAIN_ROWS = 8_645
H1_ROWS = 4_358


def _development_timestamps() -> list[pd.Timestamp]:
    train = list(pd.date_range("2011-01-01", "2011-12-31 23:00", freq="h"))
    h1 = list(pd.date_range("2012-01-01", "2012-06-30 23:00", freq="h"))
    del train[100:215]
    del h1[100:110]
    assert len(train) == TRAIN_ROWS
    assert len(h1) == H1_ROWS
    return train + h1


def _row(index: int, timestamp: pd.Timestamp) -> list[object]:
    return [
        index,
        timestamp.strftime("%Y-%m-%d"),
        1,
        int(timestamp.year == 2012),
        timestamp.month,
        timestamp.hour,
        0,
        timestamp.weekday(),
        int(timestamp.weekday() < 5),
        1,
        0.24,
        0.2879,
        0.81,
        0.0,
        3,
        13,
        16,
    ]


def _hour_csv(
    timestamps: list[pd.Timestamp],
    *,
    append_tail_sentinel: bool = True,
) -> bytes:
    rows = [_row(index, timestamp) for index, timestamp in enumerate(timestamps, 1)]
    if append_tail_sentinel:
        rows.append(_row(DEVELOPMENT_ROWS + 1, pd.Timestamp("2012-07-01")))
    frame = pd.DataFrame(rows, columns=EXPECTED_UCI_COLUMNS)
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _archive(tmp_path: Path, hour_csv: bytes) -> tuple[Path, str]:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("Readme.txt", b"fixture")
        archive.writestr("day.csv", b"must not be parsed")
        archive.writestr("hour.csv", hour_csv)
    content = stream.getvalue()
    path = tmp_path / "bike-sharing-dataset.zip"
    path.write_bytes(content)
    return path, hashlib.sha256(content).hexdigest()


def test_development_loader_stops_at_exact_row_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamps = _development_timestamps()
    path, digest = _archive(tmp_path, _hour_csv(timestamps))
    observed_nrows: list[int | None] = []
    real_read_csv = pd.read_csv

    def recording_read_csv(*args: object, **kwargs: object) -> pd.DataFrame:
        observed_nrows.append(kwargs.get("nrows"))
        return real_read_csv(*args, **kwargs)

    monkeypatch.setattr(dataset_module.pd, "read_csv", recording_read_csv)

    frame = load_uci_development_archive(path, digest)
    parts = split_development_rows(frame)

    assert observed_nrows == [DEVELOPMENT_ROWS]
    assert len(frame) == DEVELOPMENT_ROWS
    assert int(frame["instant"].max()) == DEVELOPMENT_ROWS
    assert len(parts.train) == TRAIN_ROWS
    assert len(parts.h1) == H1_ROWS
    assert not hasattr(parts, "h2")
    assert not hasattr(parts, "open_h2")
    assert frame.attrs["archive_sha256"] == digest
    assert frame.attrs["development_row_count"] == DEVELOPMENT_ROWS
    assert len(frame.attrs["development_rows_sha256"]) == 64
    assert len(parts.train.attrs["rows_sha256"]) == 64
    assert len(parts.h1.attrs["rows_sha256"]) == 64


def test_development_row_digests_are_canonical_and_repeatable(tmp_path: Path) -> None:
    path, digest = _archive(tmp_path, _hour_csv(_development_timestamps()))

    first = load_uci_development_archive(path, digest)
    second = load_uci_development_archive(path, digest.upper())
    first_parts = split_development_rows(first)
    second_parts = split_development_rows(second)

    assert first.attrs["development_rows_sha256"] == second.attrs["development_rows_sha256"]
    assert first_parts.train.attrs["rows_sha256"] == second_parts.train.attrs["rows_sha256"]
    assert first_parts.h1.attrs["rows_sha256"] == second_parts.h1.attrs["rows_sha256"]


def test_development_loader_rejects_short_input(tmp_path: Path) -> None:
    timestamps = _development_timestamps()[:-1]
    path, digest = _archive(
        tmp_path,
        _hour_csv(timestamps, append_tail_sentinel=False),
    )

    with pytest.raises(DatasetIntegrityError, match="development row count mismatch"):
        load_uci_development_archive(path, digest)


def test_development_loader_rejects_non_monotonic_chronology(tmp_path: Path) -> None:
    timestamps = _development_timestamps()
    timestamps[500], timestamps[501] = timestamps[501], timestamps[500]
    path, digest = _archive(tmp_path, _hour_csv(timestamps))

    with pytest.raises(DatasetIntegrityError, match="development chronology mismatch"):
        load_uci_development_archive(path, digest)


@pytest.mark.parametrize(
    ("position", "replacement"),
    [
        (0, pd.Timestamp("2011-01-01 01:00")),
        (-1, pd.Timestamp("2012-06-30 22:00")),
    ],
)
def test_development_loader_rejects_wrong_boundary(
    tmp_path: Path,
    position: int,
    replacement: pd.Timestamp,
) -> None:
    timestamps = _development_timestamps()
    timestamps[position] = replacement
    path, digest = _archive(tmp_path, _hour_csv(timestamps))

    with pytest.raises(DatasetIntegrityError, match="development chronology mismatch"):
        load_uci_development_archive(path, digest)
