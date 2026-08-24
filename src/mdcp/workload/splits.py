from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from mdcp.common.digests import sha256_hex

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TRAIN_START = pd.Timestamp("2011-01-01T00:00:00")
H1_START = pd.Timestamp("2012-01-01T00:00:00")
H2_START = pd.Timestamp("2012-07-01T00:00:00")
DATASET_END = pd.Timestamp("2013-01-01T00:00:00")
DEVELOPMENT_ROW_COUNT = 13_003
TRAIN_ROW_COUNT = 8_645
H1_ROW_COUNT = 4_358


class H2SealedError(PermissionError):
    """Raised when code attempts to reveal H2 before the freeze manifest exists."""


@dataclass(frozen=True)
class DatasetPartitions:
    train: pd.DataFrame
    h1: pd.DataFrame
    _h2: pd.DataFrame = field(repr=False)

    @property
    def h2(self) -> pd.DataFrame:
        raise H2SealedError("use open_h2 with a freeze-manifest digest")

    def open_h2(self, freeze_manifest_digest: str | None) -> pd.DataFrame:
        if freeze_manifest_digest is None or not SHA256_PATTERN.fullmatch(freeze_manifest_digest):
            raise H2SealedError("a valid freeze-manifest digest is required")
        return self._h2.copy()


@dataclass(frozen=True)
class DevelopmentPartitions:
    train: pd.DataFrame
    h1: pd.DataFrame


def _chronology(frame: pd.DataFrame) -> pd.DatetimeIndex:
    required = {"dteday", "hr"}
    if not required.issubset(frame.columns):
        raise ValueError("chronology columns are missing")
    try:
        days = pd.to_datetime(frame["dteday"], format="%Y-%m-%d", errors="raise")
        hours = pd.to_timedelta(frame["hr"], unit="h")
    except (TypeError, ValueError) as error:
        raise ValueError("invalid workload chronology") from error
    return pd.DatetimeIndex(days + hours, name="observed_at")


def _canonical_rows_digest(frame: pd.DataFrame) -> str:
    digest_frame = frame.copy()
    if isinstance(digest_frame.index, pd.DatetimeIndex):
        digest_frame.insert(
            0,
            "observed_at",
            digest_frame.index.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        digest_frame = digest_frame.reset_index(drop=True)
    payload = digest_frame.to_csv(
        index=False,
        lineterminator="\n",
        float_format="%.17g",
    ).encode("utf-8")
    return sha256_hex(payload)


def split_rows(frame: pd.DataFrame) -> DatasetPartitions:
    chronology = _chronology(frame)
    if (chronology < TRAIN_START).any() or (chronology >= DATASET_END).any():
        raise ValueError("rows outside 2011-2012 frozen chronology")

    indexed = frame.drop(columns=["dteday"]).copy()
    indexed.index = chronology
    train = indexed.loc[(chronology >= TRAIN_START) & (chronology < H1_START)].copy()
    h1 = indexed.loc[(chronology >= H1_START) & (chronology < H2_START)].copy()
    h2 = indexed.loc[(chronology >= H2_START) & (chronology < DATASET_END)].copy()
    if train.empty or h1.empty or h2.empty:
        raise ValueError("all frozen chronology partitions must be non-empty")
    return DatasetPartitions(train=train, h1=h1, _h2=h2)


def split_development_rows(frame: pd.DataFrame) -> DevelopmentPartitions:
    if len(frame) != DEVELOPMENT_ROW_COUNT:
        raise ValueError("development row count mismatch")
    chronology = _chronology(frame)
    if (
        not chronology.is_monotonic_increasing
        or not chronology.is_unique
        or chronology[0] != TRAIN_START
        or chronology[-1] != H2_START - pd.Timedelta(hours=1)
        or (chronology < TRAIN_START).any()
        or (chronology >= H2_START).any()
    ):
        raise ValueError("development chronology mismatch")

    indexed = frame.drop(columns=["dteday"]).copy()
    indexed.index = chronology
    train = indexed.loc[chronology < H1_START].copy()
    h1 = indexed.loc[chronology >= H1_START].copy()
    if len(train) != TRAIN_ROW_COUNT or len(h1) != H1_ROW_COUNT:
        raise ValueError("development partition row count mismatch")

    train.attrs = {
        "row_count": len(train),
        "rows_sha256": _canonical_rows_digest(train),
    }
    h1.attrs = {
        "row_count": len(h1),
        "rows_sha256": _canonical_rows_digest(h1),
    }
    return DevelopmentPartitions(train=train, h1=h1)
