from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mdcp.workload.splits import H2SealedError, split_rows

FIXTURE = Path(__file__).parents[2] / "fixtures" / "workload" / "chronology-sample.csv"


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.read_csv(FIXTURE)


def test_split_boundaries_require_explicit_h2_unlock(frame: pd.DataFrame) -> None:
    parts = split_rows(frame)

    assert parts.train.index.max() < pd.Timestamp("2012-01-01")
    assert parts.h1.index.min() >= pd.Timestamp("2012-01-01")
    assert parts.h1.index.max() <= pd.Timestamp("2012-06-30 23:59:59")
    with pytest.raises(H2SealedError, match="freeze-manifest digest"):
        parts.open_h2(None)
    h2 = parts.open_h2("a" * 64)
    assert h2.index.min() >= pd.Timestamp("2012-07-01")


def test_h2_property_never_returns_rows_without_digest(frame: pd.DataFrame) -> None:
    parts = split_rows(frame)

    with pytest.raises(H2SealedError, match="open_h2"):
        _ = parts.h2


def test_split_rejects_rows_outside_frozen_chronology(frame: pd.DataFrame) -> None:
    frame.loc[len(frame)] = {**frame.iloc[0].to_dict(), "dteday": "2010-12-31"}

    with pytest.raises(ValueError, match="outside 2011-2012"):
        split_rows(frame)
