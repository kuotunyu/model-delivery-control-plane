from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS
from mdcp.workload.features import (
    FORBIDDEN_FEATURE_COLUMNS,
    FeatureLeakageError,
    approved_feature_columns,
    audit_feature_lineage,
    audit_temporal_feature_lineage,
    select_features,
    temporal_feature_columns,
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


@pytest.fixture
def temporal_frame() -> pd.DataFrame:
    return pd.DataFrame([[float(index) for index in range(18)]], columns=TEMPORAL_FEATURE_COLUMNS)


def test_temporal_lineage_is_exact(temporal_frame: pd.DataFrame) -> None:
    receipt = audit_temporal_feature_lineage(temporal_frame)

    assert receipt.columns == TEMPORAL_FEATURE_COLUMNS
    assert temporal_feature_columns() == TEMPORAL_FEATURE_COLUMNS
    assert len(receipt.columns) == 18
    assert len(receipt.lineage_sha256) == 64


@pytest.mark.parametrize(
    "name",
    [
        "yr",
        "dteday",
        "instant",
        "casual",
        "registered",
        "cnt",
        "event_timestamp",
        "future_demand_mean",
        "target_mean_encoding",
        "row_identity_lookup",
        "discovered_category_inventory",
        "h2_scaler_mean",
    ],
)
def test_temporal_lineage_rejects_forbidden_source(
    temporal_frame: pd.DataFrame,
    name: str,
) -> None:
    with pytest.raises(FeatureLeakageError):
        audit_temporal_feature_lineage(
            temporal_frame.assign(**{name: 0.0}),
            selected_columns=(*TEMPORAL_FEATURE_COLUMNS, name),
        )


def test_temporal_lineage_rejects_reordered_or_incomplete_schema(
    temporal_frame: pd.DataFrame,
) -> None:
    reordered = (*TEMPORAL_FEATURE_COLUMNS[1:], TEMPORAL_FEATURE_COLUMNS[0])

    with pytest.raises(FeatureLeakageError, match="temporal feature contract"):
        audit_temporal_feature_lineage(temporal_frame, selected_columns=reordered)
    with pytest.raises(FeatureLeakageError, match="temporal feature contract"):
        audit_temporal_feature_lineage(temporal_frame.drop(columns=[TEMPORAL_FEATURE_COLUMNS[-1]]))
