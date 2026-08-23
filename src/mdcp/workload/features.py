from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from mdcp.common.digests import sha256_hex

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
FORBIDDEN_FEATURE_COLUMNS = frozenset(
    {"casual", "registered", "cnt", "instant", "dteday", "yr"}
)


class FeatureLeakageError(ValueError):
    """Raised when a requested feature set violates the frozen lineage contract."""


@dataclass(frozen=True)
class LeakageReceipt:
    columns: tuple[str, ...]
    lineage_sha256: str


def approved_feature_columns() -> tuple[str, ...]:
    return APPROVED_FEATURE_COLUMNS


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


def select_features(frame: pd.DataFrame) -> pd.DataFrame:
    receipt = audit_feature_lineage(frame)
    return frame.loc[:, receipt.columns].copy()
