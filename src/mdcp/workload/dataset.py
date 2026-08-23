from __future__ import annotations

import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd

from mdcp.common.digests import sha256_hex

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
