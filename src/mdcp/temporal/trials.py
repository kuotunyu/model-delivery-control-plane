"""Closed temporal trial inventory, feature materialization, and sklearn factories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.utils.validation import check_array, check_is_fitted

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.contracts.workload import BikeRequest
from mdcp.temporal.adapter import adapt_local_v2
from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS
from mdcp.temporal.folds import FoldRows


class TrialFamily(StrEnum):
    """The four predeclared model-family identifiers."""

    CTRL = "CTRL"
    REC = "REC"
    STAT = "STAT"
    NL = "NL"


@dataclass(frozen=True)
class PreprocessingSpec:
    """The fixed preprocessing contract for one trial family."""

    categorical_positions: tuple[int, ...]
    fixed_categorical_domains: tuple[tuple[int, ...], ...]
    standardized_positions: tuple[int, ...]
    standardization_ddof: int | None
    zero_variance_policy: str | None


@dataclass(frozen=True)
class TrialSpec:
    """One immutable control or candidate configuration."""

    trial_id: str
    family: TrialFamily
    final_eligible: bool
    training_mode: Literal["full_expanding_fold", "trailing_complete_calendar_days"]
    recency_days: int | None
    feature_positions: tuple[int, ...]
    model_kind: str
    model_parameters: Mapping[str, object]
    preprocessing: PreprocessingSpec
    random_state: int | None
    estimator_threads: int


@dataclass(frozen=True, slots=True)
class TrialIdentity:
    """Public-safe identity of one exact canonical trial configuration."""

    trial_id: str
    family_id: str
    configuration_sha256: str


class _PopulationStandardScaler(BaseEstimator, TransformerMixin):
    """A train-only ddof=0 scaler that fails rather than masking zero variance."""

    def fit(self, X: object, y: object = None) -> _PopulationStandardScaler:
        values = check_array(X, dtype=float, ensure_all_finite=True)
        self.mean_ = np.mean(values, axis=0)
        self.scale_ = np.std(values, axis=0, ddof=0)
        if np.any(self.scale_ == 0):
            raise ValueError("zero-variance STAT continuous feature")
        self.n_features_in_ = values.shape[1]
        return self

    def transform(self, X: object) -> np.ndarray:
        check_is_fitted(self, ("mean_", "scale_", "n_features_in_"))
        values = check_array(X, dtype=float, ensure_all_finite=True)
        if values.shape[1] != self.n_features_in_:
            raise ValueError("STAT continuous feature shape is invalid")
        return (values - self.mean_) / self.scale_


class _NonNegativePipeline(Pipeline):
    """Pipeline whose native prediction contract is exactly ``max(0, prediction)``."""

    def predict_raw(self, X: object, **params: object) -> np.ndarray:
        """Return the pre-clipping sklearn prediction for converter qualification only."""
        return np.asarray(super().predict(X, **params), dtype=float)

    def predict(self, X: object, **params: object) -> np.ndarray:
        return np.maximum(0.0, self.predict_raw(X, **params))


_CATEGORIES = (
    (1, 2, 3, 4),
    tuple(range(1, 13)),
    tuple(range(24)),
    (0, 1),
    tuple(range(7)),
    (0, 1),
    (1, 2, 3, 4),
)
_FULL_FEATURE_POSITIONS = tuple(range(1, 19))
_BASE_FEATURE_POSITIONS = tuple(range(1, 12))
_BOUNDED_FEATURE_POSITIONS = (*_BASE_FEATURE_POSITIONS, *range(13, 19))

# This is deliberately independent from the JSON file.  Trial factories accept only the
# published protocol, rather than accepting a compatible-looking reconfiguration.
_CANONICAL_PROTOCOL: dict[str, object] = {
    "schema_version": "mdcp.temporal-development.v0.2",
    "folds": [
        {
            "id": "F1",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2011-07-01T00:00:00",
            "validation_start": "2011-07-01T00:00:00",
            "validation_end": "2011-10-01T00:00:00",
        },
        {
            "id": "F2",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2011-10-01T00:00:00",
            "validation_start": "2011-10-01T00:00:00",
            "validation_end": "2012-01-01T00:00:00",
        },
        {
            "id": "F3",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2012-01-01T00:00:00",
            "validation_start": "2012-01-01T00:00:00",
            "validation_end": "2012-04-01T00:00:00",
        },
        {
            "id": "F4",
            "train_start": "2011-01-01T00:00:00",
            "train_end": "2012-04-01T00:00:00",
            "validation_start": "2012-04-01T00:00:00",
            "validation_end": "2012-07-01T00:00:00",
        },
    ],
    "trial_ids": [
        "CTRL-01",
        "REC-180-L4",
        "REC-180-L12",
        "REC-270-L4",
        "REC-270-L12",
        "REC-365-L4",
        "REC-365-L12",
        "STAT-A0.1",
        "STAT-A1",
        "STAT-A10",
        "STAT-A100",
        "STAT-A1000",
        "NL-E64-R0.03-D2",
        "NL-E64-R0.03-D3",
        "NL-E64-R0.07-D2",
        "NL-E64-R0.07-D3",
        "NL-E128-R0.03-D2",
        "NL-E128-R0.03-D3",
        "NL-E128-R0.07-D2",
        "NL-E128-R0.07-D3",
    ],
    "model_feature_schema": list(TEMPORAL_FEATURE_COLUMNS),
    "families": [
        {
            "family_id": "CTRL",
            "trial_count": 1,
            "eligible_count": 0,
            "training_mode": "full_expanding_fold",
            "recency_days": [],
            "feature_positions": list(_BASE_FEATURE_POSITIONS),
            "model_kind": "random_forest_regressor",
            "parameters": {
                "bootstrap": [True],
                "max_depth": [8],
                "max_features": [1.0],
                "min_samples_leaf": [4],
                "n_estimators": [32],
                "n_jobs": [1],
                "random_state": [2026],
            },
            "preprocessing": {
                "categorical_positions": [],
                "fixed_categorical_domains": [],
                "standardization_ddof": None,
                "standardized_positions": [],
                "zero_variance_policy": None,
            },
        },
        {
            "family_id": "REC",
            "trial_count": 6,
            "eligible_count": 6,
            "training_mode": "trailing_complete_calendar_days",
            "recency_days": [180, 270, 365],
            "feature_positions": list(_BOUNDED_FEATURE_POSITIONS),
            "model_kind": "random_forest_regressor",
            "parameters": {
                "bootstrap": [True],
                "max_depth": [8],
                "max_features": [1.0],
                "min_samples_leaf": [4, 12],
                "n_estimators": [64],
                "n_jobs": [1],
                "random_state": [2026],
            },
            "preprocessing": {
                "categorical_positions": [],
                "fixed_categorical_domains": [],
                "standardization_ddof": None,
                "standardized_positions": [],
                "zero_variance_policy": None,
            },
        },
        {
            "family_id": "STAT",
            "trial_count": 5,
            "eligible_count": 5,
            "training_mode": "full_expanding_fold",
            "recency_days": [],
            "feature_positions": list(_FULL_FEATURE_POSITIONS),
            "model_kind": "ridge_regressor",
            "parameters": {
                "alpha": [0.1, 1, 10, 100, 1000],
                "fit_intercept": [True],
                "max_iter": [10000],
                "solver": ["lsqr"],
                "tol": [1e-8],
            },
            "preprocessing": {
                "categorical_positions": list(range(1, 8)),
                "fixed_categorical_domains": [list(domain) for domain in _CATEGORIES],
                "standardization_ddof": 0,
                "standardized_positions": list(range(8, 19)),
                "zero_variance_policy": "invalid",
            },
        },
        {
            "family_id": "NL",
            "trial_count": 8,
            "eligible_count": 8,
            "training_mode": "full_expanding_fold",
            "recency_days": [],
            "feature_positions": list(_BOUNDED_FEATURE_POSITIONS),
            "model_kind": "gradient_boosting_regressor",
            "parameters": {
                "learning_rate": [0.03, 0.07],
                "loss": ["squared_error"],
                "max_depth": [2, 3],
                "max_features": [None],
                "min_samples_leaf": [8],
                "n_estimators": [64, 128],
                "random_state": [2026],
                "subsample": [1.0],
            },
            "preprocessing": {
                "categorical_positions": [],
                "fixed_categorical_domains": [],
                "standardization_ddof": None,
                "standardized_positions": [],
                "zero_variance_policy": None,
            },
        },
    ],
    "quality": {
        "overall_max_ratio": 0.97,
        "subgroup_max_ratio": 1.05,
        "subgroup_names": [
            "weather_clear",
            "weather_mist",
            "weather_adverse",
            "day_non_working",
            "day_working",
            "demand_peak",
            "demand_off_peak",
        ],
        "min_subgroup_rows": 100,
        "bootstrap": {
            "cluster": "calendar_day",
            "index": 1899,
            "paired": True,
            "resamples": 2000,
            "rng": "PCG64",
            "seed": 2026,
        },
        "completeness": {
            "adapter": 1.0,
            "candidate_prediction": 1.0,
            "development_label": 1.0,
            "stable_prediction": 1.0,
        },
        "cross_fold": {"fold_overall_max_ratio": 1.05, "minimum_folds_at_or_below_one": 3},
    },
    "execution": {
        "seed": 2026,
        "estimator_threads": 1,
        "selection_fits": 80,
        "replay_fits": 4,
        "final_fits": 1,
        "maximum_fits": 85,
        "peak_resident_memory_bytes": 4_294_967_296,
        "wall_clock_seconds": 21_600,
    },
}


def _preprocessing_for(family: TrialFamily) -> PreprocessingSpec:
    if family is TrialFamily.STAT:
        return PreprocessingSpec(
            categorical_positions=tuple(range(1, 8)),
            fixed_categorical_domains=_CATEGORIES,
            standardized_positions=tuple(range(8, 19)),
            standardization_ddof=0,
            zero_variance_policy="invalid",
        )
    return PreprocessingSpec((), (), (), None, None)


def _specification(
    trial_id: str,
    family: TrialFamily,
    *,
    final_eligible: bool,
    training_mode: Literal["full_expanding_fold", "trailing_complete_calendar_days"],
    recency_days: int | None,
    feature_positions: tuple[int, ...],
    model_kind: str,
    parameters: Mapping[str, object],
) -> TrialSpec:
    return TrialSpec(
        trial_id=trial_id,
        family=family,
        final_eligible=final_eligible,
        training_mode=training_mode,
        recency_days=recency_days,
        feature_positions=feature_positions,
        model_kind=model_kind,
        model_parameters=MappingProxyType(dict(parameters)),
        preprocessing=_preprocessing_for(family),
        random_state=(
            parameters.get("random_state")
            if isinstance(parameters.get("random_state"), int)
            else None
        ),
        estimator_threads=int(parameters.get("n_jobs", 1)),
    )


def _canonical_trial_specs() -> tuple[TrialSpec, ...]:
    specs = [
        _specification(
            "CTRL-01",
            TrialFamily.CTRL,
            final_eligible=False,
            training_mode="full_expanding_fold",
            recency_days=None,
            feature_positions=_BASE_FEATURE_POSITIONS,
            model_kind="random_forest_regressor",
            parameters={
                "n_estimators": 32,
                "max_depth": 8,
                "min_samples_leaf": 4,
                "max_features": 1.0,
                "bootstrap": True,
                "random_state": 2026,
                "n_jobs": 1,
            },
        )
    ]
    for days in (180, 270, 365):
        for leaf in (4, 12):
            specs.append(
                _specification(
                    f"REC-{days}-L{leaf}",
                    TrialFamily.REC,
                    final_eligible=True,
                    training_mode="trailing_complete_calendar_days",
                    recency_days=days,
                    feature_positions=_BOUNDED_FEATURE_POSITIONS,
                    model_kind="random_forest_regressor",
                    parameters={
                        "n_estimators": 64,
                        "max_depth": 8,
                        "min_samples_leaf": leaf,
                        "max_features": 1.0,
                        "bootstrap": True,
                        "random_state": 2026,
                        "n_jobs": 1,
                    },
                )
            )
    for alpha, label in ((0.1, "0.1"), (1, "1"), (10, "10"), (100, "100"), (1000, "1000")):
        specs.append(
            _specification(
                f"STAT-A{label}",
                TrialFamily.STAT,
                final_eligible=True,
                training_mode="full_expanding_fold",
                recency_days=None,
                feature_positions=_FULL_FEATURE_POSITIONS,
                model_kind="ridge_regressor",
                parameters={
                    "alpha": alpha,
                    "solver": "lsqr",
                    "fit_intercept": True,
                    "tol": 1e-8,
                    "max_iter": 10_000,
                },
            )
        )
    for estimators in (64, 128):
        for rate in (0.03, 0.07):
            for depth in (2, 3):
                specs.append(
                    _specification(
                        f"NL-E{estimators}-R{rate:.2f}-D{depth}",
                        TrialFamily.NL,
                        final_eligible=True,
                        training_mode="full_expanding_fold",
                        recency_days=None,
                        feature_positions=_BOUNDED_FEATURE_POSITIONS,
                        model_kind="gradient_boosting_regressor",
                        parameters={
                            "n_estimators": estimators,
                            "learning_rate": rate,
                            "max_depth": depth,
                            "min_samples_leaf": 8,
                            "loss": "squared_error",
                            "subsample": 1.0,
                            "max_features": None,
                            "random_state": 2026,
                        },
                    )
                )
    return tuple(specs)


def _exact_value(expected: object, actual: object) -> bool:
    """Compare protocol/spec values without Python's bool/int or int/float coercion."""
    if isinstance(expected, Mapping):
        return (
            isinstance(actual, Mapping)
            and set(expected) == set(actual)
            and all(_exact_value(expected[key], actual[key]) for key in expected)
        )
    if isinstance(expected, list | tuple):
        return (
            type(actual) is type(expected)
            and len(actual) == len(expected)
            and all(_exact_value(left, right) for left, right in zip(expected, actual, strict=True))
        )
    return type(actual) is type(expected) and actual == expected


_CANONICAL_TRIAL_SPECS = _canonical_trial_specs()


def _is_canonical_trial_spec(spec: object) -> bool:
    return any(spec is candidate for candidate in _CANONICAL_TRIAL_SPECS)


def _trial_configuration_material(spec: TrialSpec) -> dict[str, object]:
    return {
        "trial_id": spec.trial_id,
        "family_id": spec.family.value,
        "final_eligible": spec.final_eligible,
        "training_mode": spec.training_mode,
        "recency_days": spec.recency_days,
        "feature_positions": list(spec.feature_positions),
        "model_kind": spec.model_kind,
        "model_parameters": dict(spec.model_parameters),
        "preprocessing": {
            "categorical_positions": list(spec.preprocessing.categorical_positions),
            "fixed_categorical_domains": [
                list(domain) for domain in spec.preprocessing.fixed_categorical_domains
            ],
            "standardized_positions": list(spec.preprocessing.standardized_positions),
            "standardization_ddof": spec.preprocessing.standardization_ddof,
            "zero_variance_policy": spec.preprocessing.zero_variance_policy,
        },
        "random_state": spec.random_state,
        "estimator_threads": spec.estimator_threads,
        "model_feature_schema": list(TEMPORAL_FEATURE_COLUMNS),
    }


def trial_identity(spec: TrialSpec) -> TrialIdentity:
    """Return the immutable configuration identity for one canonical trial object."""
    if not _is_canonical_trial_spec(spec):
        raise ValueError("trial specification is invalid")
    return TrialIdentity(
        trial_id=spec.trial_id,
        family_id=spec.family.value,
        configuration_sha256=sha256_hex(canonicalize_json(_trial_configuration_material(spec))),
    )


def canonical_trial_identity(trial_id: str) -> TrialIdentity:
    """Resolve one exact declared trial ID to its immutable configuration identity."""
    matching = tuple(spec for spec in _CANONICAL_TRIAL_SPECS if spec.trial_id == trial_id)
    if len(matching) != 1:
        raise ValueError("trial identity is invalid")
    return trial_identity(matching[0])


def is_canonical_trial_identity(identity: object) -> bool:
    """Fail closed unless an identity equals the canonical declaration for its trial ID."""
    if type(identity) is not TrialIdentity or type(identity.trial_id) is not str:
        return False
    try:
        return identity == canonical_trial_identity(identity.trial_id)
    except ValueError:
        return False


def load_trial_specs(protocol: Mapping[str, Any]) -> tuple[TrialSpec, ...]:
    """Return the published 20-trial inventory only for the exact canonical protocol."""
    if not isinstance(protocol, Mapping) or not _exact_value(_CANONICAL_PROTOCOL, protocol):
        raise ValueError("trial protocol is invalid")
    return _CANONICAL_TRIAL_SPECS


def _feature_names(spec: TrialSpec) -> tuple[str, ...]:
    if not spec.feature_positions or any(
        position < 1 or position > len(TEMPORAL_FEATURE_COLUMNS)
        for position in spec.feature_positions
    ):
        raise ValueError("trial feature positions are invalid")
    return tuple(TEMPORAL_FEATURE_COLUMNS[position - 1] for position in spec.feature_positions)


def _materialize_features(rows: pd.DataFrame) -> pd.DataFrame:
    required = {*TEMPORAL_FEATURE_COLUMNS[:11], "cnt"}
    if (
        rows.empty
        or not isinstance(rows.index, pd.DatetimeIndex)
        or rows.index.tz is not None
        or not rows.index.is_monotonic_increasing
        or not required.issubset(rows.columns)
    ):
        raise ValueError("training rows are invalid")
    if not all(np.isfinite(rows[column].to_numpy(dtype=float)).all() for column in required):
        raise ValueError("training rows are invalid")

    vectors = []
    for position, (timestamp, row) in enumerate(rows.iterrows()):
        request = BikeRequest.model_validate(
            {
                "request_id": f"development-{position}",
                **{name: row[name] for name in TEMPORAL_FEATURE_COLUMNS[:11]},
            }
        )
        vectors.append(adapt_local_v2(request, timestamp.to_pydatetime()))
    materialized = pd.DataFrame(
        [vector.values for vector in vectors],
        columns=TEMPORAL_FEATURE_COLUMNS,
        index=rows.index,
    )
    materialized["cnt"] = rows["cnt"].to_numpy(copy=True)
    return materialized.loc[:, (*TEMPORAL_FEATURE_COLUMNS, "cnt")]


def training_rows_for_trial(spec: TrialSpec, fold: FoldRows) -> pd.DataFrame:
    """Materialize the declared feature subset from a fold's causally available training rows."""
    if not _is_canonical_trial_spec(spec):
        raise ValueError("trial specification is invalid")
    if not isinstance(fold, FoldRows):
        raise ValueError("trial training inputs are invalid")
    if spec.training_mode == "full_expanding_fold":
        source = fold.train
    elif spec.training_mode == "trailing_complete_calendar_days" and spec.recency_days is not None:
        start = max(
            pd.Timestamp("2011-01-01T00:00:00"),
            fold.spec.validation_start - pd.Timedelta(days=spec.recency_days),
        )
        source = fold.train.loc[
            (fold.train.index >= start) & (fold.train.index < fold.spec.validation_start)
        ]
    else:
        raise ValueError("trial training mode is invalid")
    if source.empty or source.index.max() >= fold.spec.validation_start:
        raise ValueError("trial training boundary is invalid")

    materialized = _materialize_features(source)
    return materialized.loc[:, (*_feature_names(spec), "cnt")].copy()


def _preprocessor(spec: TrialSpec) -> ColumnTransformer:
    features = _feature_names(spec)
    if spec.family is TrialFamily.STAT:
        categorical = features[:7]
        continuous = features[7:]
        return ColumnTransformer(
            [
                (
                    "categorical",
                    OneHotEncoder(
                        categories=[list(domain) for domain in _CATEGORIES],
                        handle_unknown="error",
                        sparse_output=False,
                    ),
                    list(categorical),
                ),
                ("continuous", _PopulationStandardScaler(), list(continuous)),
            ],
            remainder="drop",
            sparse_threshold=0.0,
            verbose_feature_names_out=False,
        )
    return ColumnTransformer(
        [("features", "passthrough", list(features))],
        remainder="drop",
        sparse_threshold=0.0,
        verbose_feature_names_out=False,
    )


def build_estimator(spec: TrialSpec) -> Pipeline:
    """Build the exact deterministic sklearn pipeline for one declared trial."""
    if not _is_canonical_trial_spec(spec):
        raise ValueError("trial specification is invalid")
    parameters = dict(spec.model_parameters)
    if spec.family in (TrialFamily.CTRL, TrialFamily.REC):
        model = RandomForestRegressor(**parameters)
    elif spec.family is TrialFamily.STAT:
        model = Ridge(**parameters)
    elif spec.family is TrialFamily.NL:
        model = GradientBoostingRegressor(**parameters)
    else:  # pragma: no cover - TrialFamily is closed
        raise ValueError("trial family is invalid")
    return _NonNegativePipeline([("preprocess", _preprocessor(spec)), ("model", model)])
