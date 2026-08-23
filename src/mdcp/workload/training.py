from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.workload.features import approved_feature_columns, audit_feature_lineage

REPOSITORY_ROOT = Path(__file__).parents[3]


class ModelFixtureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.model-fixture.v1"]
    name: Literal["stable-v1", "candidate-v1"]
    n_estimators: int = Field(ge=1, le=128)
    max_depth: int = Field(ge=1, le=32)
    min_samples_leaf: int = Field(ge=1, le=64)
    random_state: Literal[2026]
    n_jobs: Literal[1]


class TrainingReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.training-receipt.v1"] = "mdcp.training-receipt.v1"
    model_name: str
    row_count: int
    fit_min_timestamp: str
    fit_max_timestamp: str
    config_sha256: str
    preprocessing_sha256: str
    feature_lineage_sha256: str
    dependency_lock_sha256: str
    training_rows_sha256: str


def load_model_config(path: Path) -> ModelFixtureConfig:
    return ModelFixtureConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_feature_pipeline() -> ColumnTransformer:
    return ColumnTransformer(
        [("approved", "passthrough", list(approved_feature_columns()))],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def _validate_training_rows(rows: pd.DataFrame) -> None:
    if rows.empty or not isinstance(rows.index, pd.DatetimeIndex):
        raise ValueError("training rows require a non-empty DatetimeIndex")
    if not rows.index.is_monotonic_increasing:
        raise ValueError("training rows must be in chronological order")
    if rows.index.min() < pd.Timestamp("2011-01-01") or rows.index.max() >= pd.Timestamp(
        "2012-01-01"
    ):
        raise ValueError("only the 2011 training partition may be fitted")
    if "cnt" not in rows.columns:
        raise ValueError("training target is missing")
    audit_feature_lineage(rows)


def _timestamp(value: pd.Timestamp) -> str:
    return value.isoformat(timespec="seconds") + "Z"


def _training_rows_digest(rows: pd.DataFrame) -> str:
    digest_frame = rows.loc[:, (*approved_feature_columns(), "cnt")].copy()
    digest_frame.insert(0, "observed_at", rows.index.strftime("%Y-%m-%dT%H:%M:%S"))
    payload = digest_frame.to_csv(
        index=False,
        lineterminator="\n",
        float_format="%.17g",
    ).encode("utf-8")
    return sha256_hex(payload)


def create_training_receipt(
    config: ModelFixtureConfig,
    rows: pd.DataFrame,
) -> TrainingReceipt:
    _validate_training_rows(rows)
    lineage = audit_feature_lineage(rows)
    preprocessing_contract = {
        "kind": "column-transformer-passthrough",
        "columns": list(lineage.columns),
        "remainder": "drop",
    }
    return TrainingReceipt(
        model_name=config.name,
        row_count=len(rows),
        fit_min_timestamp=_timestamp(rows.index.min()),
        fit_max_timestamp=_timestamp(rows.index.max()),
        config_sha256=sha256_hex(canonicalize_json(config.model_dump(mode="json"))),
        preprocessing_sha256=sha256_hex(canonicalize_json(preprocessing_contract)),
        feature_lineage_sha256=lineage.lineage_sha256,
        dependency_lock_sha256=sha256_hex((REPOSITORY_ROOT / "uv.lock").read_bytes()),
        training_rows_sha256=_training_rows_digest(rows),
    )


def train_fixture(config: ModelFixtureConfig, rows: pd.DataFrame) -> Pipeline:
    _validate_training_rows(rows)
    estimator = RandomForestRegressor(
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        min_samples_leaf=config.min_samples_leaf,
        random_state=config.random_state,
        n_jobs=config.n_jobs,
    )
    pipeline = Pipeline(
        [
            ("features", build_feature_pipeline()),
            ("model", estimator),
        ]
    )
    return pipeline.fit(rows, rows["cnt"])
