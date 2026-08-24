from __future__ import annotations

import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd

from mdcp.common.digests import sha256_hex
from mdcp.workload.splits import (
    _canonical_rows_digest,
    _chronology,
    split_development_rows,
)

EXPECTED_ARCHIVE_MEMBERS = frozenset({"Readme.txt", "day.csv", "hour.csv"})
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
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DEVELOPMENT_ROW_COUNT = 13_003
DEVELOPMENT_START = pd.Timestamp("2011-01-01T00:00:00")
DEVELOPMENT_END = pd.Timestamp("2012-06-30T23:00:00")


class DatasetIntegrityError(ValueError):
    """Raised when downloaded workload bytes do not satisfy the frozen contract."""


def _validate_archive_members(infos: list[zipfile.ZipInfo]) -> zipfile.ZipInfo:
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise DatasetIntegrityError("duplicate archive member")

    unsafe = {
        name
        for name in names
        if PurePosixPath(name).is_absolute()
        or ".." in PurePosixPath(name).parts
        or name not in EXPECTED_ARCHIVE_MEMBERS
    }
    if unsafe or set(names) != EXPECTED_ARCHIVE_MEMBERS:
        raise DatasetIntegrityError("unsafe archive members")

    for info in infos:
        unix_type = (info.external_attr >> 16) & 0o170000
        if info.is_dir() or unix_type == stat.S_IFLNK:
            raise DatasetIntegrityError("archive members must be regular files")

    return next(info for info in infos if info.filename == "hour.csv")


def load_uci_archive(path: Path, expected_sha256: str) -> pd.DataFrame:
    """Verify and parse the approved UCI archive without extracting it to disk."""

    normalized_digest = expected_sha256.lower()
    if not SHA256_PATTERN.fullmatch(normalized_digest):
        raise DatasetIntegrityError("invalid expected archive digest")
    if sha256_hex(path.read_bytes()) != normalized_digest:
        raise DatasetIntegrityError("archive digest mismatch")

    try:
        with zipfile.ZipFile(path) as archive:
            hour_info = _validate_archive_members(archive.infolist())
            with archive.open(hour_info, "r") as source:
                frame = pd.read_csv(source)
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError) as error:
        raise DatasetIntegrityError("invalid dataset archive") from error

    if tuple(frame.columns) != EXPECTED_UCI_COLUMNS:
        raise DatasetIntegrityError("unexpected columns")
    return frame


def load_uci_development_archive(path: Path, expected_sha256: str) -> pd.DataFrame:
    """Verify the approved archive and parse only the frozen development prefix."""

    normalized_digest = expected_sha256.lower()
    if not SHA256_PATTERN.fullmatch(normalized_digest):
        raise DatasetIntegrityError("invalid expected archive digest")
    if sha256_hex(path.read_bytes()) != normalized_digest:
        raise DatasetIntegrityError("archive digest mismatch")

    try:
        with zipfile.ZipFile(path) as archive:
            hour_info = _validate_archive_members(archive.infolist())
            with archive.open(hour_info, "r") as source:
                frame = pd.read_csv(source, nrows=DEVELOPMENT_ROW_COUNT)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise DatasetIntegrityError("invalid dataset archive") from error

    if tuple(frame.columns) != EXPECTED_UCI_COLUMNS:
        raise DatasetIntegrityError("unexpected columns")
    if len(frame) != DEVELOPMENT_ROW_COUNT:
        raise DatasetIntegrityError("development row count mismatch")

    try:
        chronology = _chronology(frame)
    except ValueError as error:
        raise DatasetIntegrityError("development chronology mismatch") from error
    if (
        not chronology.is_monotonic_increasing
        or not chronology.is_unique
        or chronology[0] != DEVELOPMENT_START
        or chronology[-1] != DEVELOPMENT_END
    ):
        raise DatasetIntegrityError("development chronology mismatch")

    frame.attrs = {
        "archive_sha256": normalized_digest,
        "development_row_count": DEVELOPMENT_ROW_COUNT,
        "development_rows_sha256": _canonical_rows_digest(frame),
    }
    try:
        split_development_rows(frame)
    except ValueError as error:
        raise DatasetIntegrityError("development partition mismatch") from error
    return frame
