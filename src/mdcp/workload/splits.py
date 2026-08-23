from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TRAIN_START = pd.Timestamp("2011-01-01T00:00:00")
H1_START = pd.Timestamp("2012-01-01T00:00:00")
H2_START = pd.Timestamp("2012-07-01T00:00:00")
DATASET_END = pd.Timestamp("2013-01-01T00:00:00")


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
        if freeze_manifest_digest is None or not SHA256_PATTERN.fullmatch(
            freeze_manifest_digest
        ):
            raise H2SealedError("a valid freeze-manifest digest is required")
        return self._h2.copy()


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
