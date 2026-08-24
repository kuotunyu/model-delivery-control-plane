from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS, TEMPORAL_SCHEMA_ID

APPROVED_FEATURE_COLUMNS = (
    "season",
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
)
FORBIDDEN_FEATURE_COLUMNS = frozenset({"casual", "registered", "cnt", "instant", "dteday", "yr"})
TEMPORAL_FORBIDDEN_SOURCE_COLUMNS = FORBIDDEN_FEATURE_COLUMNS | {
    "event_timestamp",
    "future_demand_mean",
    "target_mean_encoding",
    "row_identity_lookup",
    "discovered_category_inventory",
    "h2_scaler_mean",
}


class FeatureLeakageError(ValueError):
    """Raised when a requested feature set violates the frozen lineage contract."""


@dataclass(frozen=True)
class LeakageReceipt:
    columns: tuple[str, ...]
    lineage_sha256: str


def approved_feature_columns() -> tuple[str, ...]:
    return APPROVED_FEATURE_COLUMNS


def temporal_feature_columns() -> tuple[str, ...]:
    return TEMPORAL_FEATURE_COLUMNS


def audit_feature_lineage(
    frame: pd.DataFrame,
    *,
    selected_columns: Iterable[str] | None = None,
) -> LeakageReceipt:
    selected = tuple(selected_columns or APPROVED_FEATURE_COLUMNS)
    forbidden = set(selected).intersection(FORBIDDEN_FEATURE_COLUMNS)
    if forbidden:
        raise FeatureLeakageError("forbidden feature requested")
    if selected != APPROVED_FEATURE_COLUMNS or not set(APPROVED_FEATURE_COLUMNS).issubset(
        frame.columns
    ):
        raise FeatureLeakageError("feature selection differs from approved feature contract")
    digest = sha256_hex(("\n".join(selected) + "\n").encode("utf-8"))
    return LeakageReceipt(columns=selected, lineage_sha256=digest)


def audit_temporal_feature_lineage(
    frame: pd.DataFrame,
    *,
    selected_columns: Iterable[str] | None = None,
) -> LeakageReceipt:
    selected = tuple(selected_columns) if selected_columns is not None else TEMPORAL_FEATURE_COLUMNS
    if set(selected).intersection(TEMPORAL_FORBIDDEN_SOURCE_COLUMNS):
        raise FeatureLeakageError("forbidden temporal feature source")
    if selected != TEMPORAL_FEATURE_COLUMNS or not set(TEMPORAL_FEATURE_COLUMNS).issubset(
        frame.columns
    ):
        raise FeatureLeakageError("feature selection differs from temporal feature contract")

    lineage_contract = {
        "schema_id": TEMPORAL_SCHEMA_ID,
        "columns": list(selected),
        "arithmetic": "float64",
        "boundary_cast": "float32_once",
        "raw_timestamp_model_input": False,
        "category_domains": {
            "season": [1, 2, 3, 4],
            "mnth": list(range(1, 13)),
            "hr": list(range(24)),
            "holiday": [0, 1],
            "weekday": list(range(7)),
            "workingday": [0, 1],
            "weathersit": [1, 2, 3, 4],
        },
        "category_source": "fixed_specification",
        "h2_derived_preprocessing": False,
    }
    return LeakageReceipt(
        columns=selected,
        lineage_sha256=sha256_hex(canonicalize_json(lineage_contract)),
    )


def select_features(frame: pd.DataFrame) -> pd.DataFrame:
    receipt = audit_feature_lineage(frame)
    return frame.loc[:, receipt.columns].copy()
