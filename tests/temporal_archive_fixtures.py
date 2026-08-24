from __future__ import annotations

import csv
import hashlib
import io
import json
import stat
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pytest

SYNTHETIC_METADATA = {
    "evidence_class": "synthetic_test",
    "source_kind": "deterministic_generated",
    "uci_rows": 0,
}
EXPECTED_UCI_COLUMNS = (
    "instant",
    "dteday",
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
    "casual",
    "registered",
    "cnt",
)
TRAIN_ROWS = 8_645
H1_ROWS = 4_358
DEVELOPMENT_ROWS = 13_003
TOTAL_ROWS = 13_004
_RECIPE = {
    "schema_version": "mdcp.synthetic-temporal-archive-recipe.v1",
    **SYNTHETIC_METADATA,
    "members": ["Readme.txt", "day.csv", "hour.csv"],
    "development_rows": DEVELOPMENT_ROWS,
    "train_rows": TRAIN_ROWS,
    "h1_rows": H1_ROWS,
    "h2_sentinel_rows": 1,
    "removed_2011_slice": [100, 215],
    "removed_h1_slice": [100, 110],
    "zip_timestamp": "1980-01-01T00:00:00",
    "zip_mode": "0644",
}
RECIPE_SHA256 = hashlib.sha256(
    json.dumps(_RECIPE, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


@dataclass(frozen=True)
class ArchiveFixture:
    path: Path
    sha256: str
    recipe_sha256: str


def _timestamps() -> tuple[datetime, ...]:
    train = [datetime(2011, 1, 1) + timedelta(hours=index) for index in range(365 * 24)]
    h1 = [datetime(2012, 1, 1) + timedelta(hours=index) for index in range(182 * 24)]
    del train[100:215]
    del h1[100:110]
    timestamps = (*train, *h1, datetime(2012, 7, 1))
    assert len(train) == TRAIN_ROWS
    assert len(h1) == H1_ROWS
    assert len(timestamps) == TOTAL_ROWS
    return timestamps


def _hour_csv() -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(EXPECTED_UCI_COLUMNS)
    for instant, timestamp in enumerate(_timestamps(), start=1):
        writer.writerow(
            (
                instant,
                timestamp.strftime("%Y-%m-%d"),
                1,
                int(timestamp.year == 2012),
                timestamp.month,
                timestamp.hour,
                0,
                timestamp.weekday(),
                int(timestamp.weekday() < 5),
                1,
                "0.24",
                "0.2879",
                "0.81",
                "0.0",
                3,
                13,
                16,
            )
        )
    return stream.getvalue().encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def build_synthetic_archive(path: Path) -> ArchiveFixture:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(_zip_info("Readme.txt"), b"deterministic synthetic fixture\n")
        archive.writestr(_zip_info("day.csv"), b"must-not-be-parsed\n")
        archive.writestr(_zip_info("hour.csv"), _hour_csv())
    content = stream.getvalue()
    path.write_bytes(content)
    return ArchiveFixture(
        path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        recipe_sha256=RECIPE_SHA256,
    )


@pytest.fixture
def synthetic_archive(tmp_path: Path) -> ArchiveFixture:
    return build_synthetic_archive(tmp_path / "synthetic-bike-sharing.zip")
