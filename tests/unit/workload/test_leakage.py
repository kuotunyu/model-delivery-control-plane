from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mdcp.workload.features import (
    FORBIDDEN_FEATURE_COLUMNS,
    FeatureLeakageError,
    approved_feature_columns,
    audit_feature_lineage,
    select_features,
)

FIXTURE = Path(__file__).parents[2] / "fixtures" / "workload" / "chronology-sample.csv"


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.read_csv(FIXTURE)


def test_feature_lineage_excludes_forbidden_columns(frame: pd.DataFrame) -> None:
    receipt = audit_feature_lineage(frame)

    assert receipt.columns == approved_feature_columns()
    assert not set(receipt.columns).intersection(FORBIDDEN_FEATURE_COLUMNS)
    assert tuple(select_features(frame).columns) == approved_feature_columns()


@pytest.mark.parametrize("name", sorted(FORBIDDEN_FEATURE_COLUMNS))
def test_explicit_feature_selection_rejects_leakage(frame: pd.DataFrame, name: str) -> None:
    with pytest.raises(FeatureLeakageError, match="forbidden feature"):
        audit_feature_lineage(frame, selected_columns=(*approved_feature_columns(), name))


def test_feature_lineage_requires_every_approved_column(frame: pd.DataFrame) -> None:
    with pytest.raises(FeatureLeakageError, match="approved feature contract"):
        audit_feature_lineage(frame.drop(columns=["hum"]))
