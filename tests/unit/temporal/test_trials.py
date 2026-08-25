from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

from mdcp.temporal.constants import TEMPORAL_FEATURE_COLUMNS
from mdcp.temporal.folds import FoldRows, load_fold_specs, materialize_folds
from mdcp.temporal.trials import (
    TrialFamily,
    TrialSpec,
    build_estimator,
    load_trial_specs,
    training_rows_for_trial,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
PROTOCOL = json.loads(
    (REPOSITORY_ROOT / "configs" / "workload" / "temporal-development-v2.json").read_text(
        encoding="utf-8"
    )
)


def _synthetic_development_frame() -> pd.DataFrame:
    import sys

    sys.path.insert(0, str(Path(__file__).parents[2]))
    from temporal_fixtures import synthetic_development_frame

    return synthetic_development_frame()


@pytest.fixture
def f4() -> FoldRows:
    return materialize_folds(_synthetic_development_frame(), load_fold_specs(PROTOCOL))[-1]


@pytest.fixture
def specs() -> tuple[TrialSpec, ...]:
    return load_trial_specs(PROTOCOL)


def _spec(specs: tuple[TrialSpec, ...], trial_id: str) -> TrialSpec:
    return next(spec for spec in specs if spec.trial_id == trial_id)


def test_exact_trial_inventory(specs: tuple[TrialSpec, ...]) -> None:
    assert len(specs) == 20
    assert sum(spec.final_eligible for spec in specs) == 19
    assert [spec.trial_id for spec in specs] == PROTOCOL["trial_ids"]
    assert [spec.family for spec in specs] == [
        TrialFamily.CTRL,
        *([TrialFamily.REC] * 6),
        *([TrialFamily.STAT] * 5),
        *([TrialFamily.NL] * 8),
    ]
    assert all(spec.random_state in (None, 2026) for spec in specs)
    assert all(spec.estimator_threads == 1 for spec in specs)


def test_trial_specs_freeze_every_family_configuration(
    specs: tuple[TrialSpec, ...],
) -> None:
    by_id = {spec.trial_id: spec for spec in specs}

    assert by_id["CTRL-01"].feature_positions == tuple(range(1, 12))
    assert by_id["CTRL-01"].model_parameters == {
        "bootstrap": True,
        "max_depth": 8,
        "max_features": 1.0,
        "min_samples_leaf": 4,
        "n_estimators": 32,
        "n_jobs": 1,
        "random_state": 2026,
    }
    assert {
        (spec.recency_days, spec.model_parameters["min_samples_leaf"])
        for spec in specs
        if spec.family is TrialFamily.REC
    } == {(180, 4), (180, 12), (270, 4), (270, 12), (365, 4), (365, 12)}
    assert all(12 not in spec.feature_positions for spec in specs if spec.family is TrialFamily.REC)
    assert {
        spec.model_parameters["alpha"] for spec in specs if spec.family is TrialFamily.STAT
    } == {0.1, 1, 10, 100, 1000}
    assert {
        (
            spec.model_parameters["n_estimators"],
            spec.model_parameters["learning_rate"],
            spec.model_parameters["max_depth"],
        )
        for spec in specs
        if spec.family is TrialFamily.NL
    } == {
        (64, 0.03, 2),
        (64, 0.03, 3),
        (64, 0.07, 2),
        (64, 0.07, 3),
        (128, 0.03, 2),
        (128, 0.03, 3),
        (128, 0.07, 2),
        (128, 0.07, 3),
    }
    assert all(12 not in spec.feature_positions for spec in specs if spec.family is TrialFamily.NL)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_root",
        "unknown_parameter",
        "mutated_parameter",
        "mutated_categories",
        "int_for_bool",
        "bool_for_int",
        "int_for_float",
    ],
)
def test_trial_protocol_is_fail_closed_for_unknown_or_mutated_values(mutation: str) -> None:
    protocol = deepcopy(PROTOCOL)
    if mutation == "unknown_root":
        protocol["unapproved"] = True
    elif mutation == "unknown_parameter":
        protocol["families"][0]["parameters"]["unapproved"] = [1]
    elif mutation == "mutated_parameter":
        protocol["families"][1]["parameters"]["n_estimators"] = [65]
    elif mutation == "mutated_categories":
        protocol["families"][2]["preprocessing"]["fixed_categorical_domains"][2] = [0, 1]
    elif mutation == "int_for_bool":
        protocol["families"][0]["parameters"]["bootstrap"] = [1]
    elif mutation == "bool_for_int":
        protocol["families"][0]["parameters"]["n_jobs"] = [True]
    elif mutation == "int_for_float":
        protocol["families"][0]["parameters"]["max_features"] = [1]
    else:  # pragma: no cover - parametrization is closed
        raise AssertionError("unknown mutation")

    with pytest.raises(ValueError, match="trial protocol is invalid"):
        load_trial_specs(protocol)


@pytest.mark.parametrize("api", ["build", "rows"])
@pytest.mark.parametrize("mutation", ["replace", "construct"])
def test_public_trial_boundaries_reject_mutated_specs(
    api: str,
    mutation: str,
    specs: tuple[TrialSpec, ...],
    f4: FoldRows,
) -> None:
    original = _spec(specs, "REC-180-L4")
    if mutation == "replace":
        mutated = replace(original, recency_days=181)
    elif mutation == "construct":
        mutated = TrialSpec(
            trial_id=original.trial_id,
            family=original.family,
            final_eligible=original.final_eligible,
            training_mode=original.training_mode,
            recency_days=original.recency_days,
            feature_positions=original.feature_positions,
            model_kind=original.model_kind,
            model_parameters=MappingProxyType({**original.model_parameters, "min_samples_leaf": 5}),
            preprocessing=original.preprocessing,
            random_state=original.random_state,
            estimator_threads=original.estimator_threads,
        )
    else:  # pragma: no cover - parametrization is closed
        raise AssertionError("unknown mutation")

    with pytest.raises(ValueError, match="trial specification is invalid"):
        if api == "build":
            build_estimator(mutated)
        elif api == "rows":
            training_rows_for_trial(mutated, f4)
        else:  # pragma: no cover - parametrization is closed
            raise AssertionError("unknown API")


def test_recency_never_pads_from_future(specs: tuple[TrialSpec, ...], f4: FoldRows) -> None:
    rows = training_rows_for_trial(_spec(specs, "REC-180-L4"), f4)

    assert rows.index.min() == pd.Timestamp("2011-10-04")
    assert rows.index.max() < pd.Timestamp("2012-04-01")
    assert rows.index.max() == pd.Timestamp("2012-03-31T23:00:00")
    assert len(rows) == 180 * 24


def test_training_rows_materialize_only_declared_features_and_raw_target(
    specs: tuple[TrialSpec, ...], f4: FoldRows
) -> None:
    rows = training_rows_for_trial(_spec(specs, "NL-E64-R0.03-D2"), f4)

    assert tuple(rows.columns) == (
        *(TEMPORAL_FEATURE_COLUMNS[position - 1] for position in range(1, 12)),
        *(TEMPORAL_FEATURE_COLUMNS[position - 1] for position in range(13, 19)),
        "cnt",
    )
    assert "elapsed_days" not in rows
    assert rows["cnt"].equals(f4.train.loc[rows.index, "cnt"])
    assert rows.index.max() < f4.spec.validation_start


def test_training_rows_fail_closed_on_timestamp_field_mismatch(
    specs: tuple[TrialSpec, ...], f4: FoldRows
) -> None:
    source = f4.train.copy()
    first_position = source.columns.get_loc("mnth")
    source.iloc[0, first_position] = 12 if source.index[0].month != 12 else 11
    mismatched_fold = replace(f4, train=source)

    with pytest.raises(ValueError, match="TEMPORAL_FIELD_MISMATCH"):
        training_rows_for_trial(_spec(specs, "NL-E64-R0.03-D2"), mismatched_fold)


def test_recency_rows_exclude_field_twelve_in_exact_declared_order(
    specs: tuple[TrialSpec, ...], f4: FoldRows
) -> None:
    rows = training_rows_for_trial(_spec(specs, "REC-270-L12"), f4)

    assert tuple(rows.columns) == (
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
        "hour_sin",
        "hour_cos",
        "weekday_sin",
        "weekday_cos",
        "annual_sin",
        "annual_cos",
        "cnt",
    )
    assert "elapsed_days" not in rows


def test_every_recency_trial_has_only_its_exact_declared_parameters(
    specs: tuple[TrialSpec, ...],
) -> None:
    for spec in specs:
        if spec.family is TrialFamily.REC:
            assert spec.model_parameters == {
                "n_estimators": 64,
                "max_depth": 8,
                "min_samples_leaf": 4 if spec.trial_id.endswith("L4") else 12,
                "max_features": 1.0,
                "bootstrap": True,
                "random_state": 2026,
                "n_jobs": 1,
            }


def test_factory_builds_exact_estimators_and_a_pipeline(
    specs: tuple[TrialSpec, ...],
) -> None:
    control = build_estimator(_spec(specs, "CTRL-01"))
    recency = build_estimator(_spec(specs, "REC-180-L12"))
    stat = build_estimator(_spec(specs, "STAT-A10"))
    nonlinear = build_estimator(_spec(specs, "NL-E128-R0.07-D3"))

    assert all(isinstance(value, Pipeline) for value in (control, recency, stat, nonlinear))
    assert control.named_steps["model"].get_params(deep=False) == {
        **control.named_steps["model"].get_params(deep=False),
        "n_estimators": 32,
        "max_depth": 8,
        "min_samples_leaf": 4,
        "max_features": 1.0,
        "bootstrap": True,
        "random_state": 2026,
        "n_jobs": 1,
    }
    assert isinstance(control.named_steps["model"], RandomForestRegressor)
    assert isinstance(recency.named_steps["model"], RandomForestRegressor)
    assert recency.named_steps["model"].min_samples_leaf == 12
    assert isinstance(stat.named_steps["model"], Ridge)
    assert stat.named_steps["model"].get_params(deep=False) == {
        **stat.named_steps["model"].get_params(deep=False),
        "alpha": 10,
        "solver": "lsqr",
        "fit_intercept": True,
        "tol": 1e-8,
        "max_iter": 10_000,
    }
    assert isinstance(nonlinear.named_steps["model"], GradientBoostingRegressor)
    assert nonlinear.named_steps["model"].get_params(deep=False) == {
        **nonlinear.named_steps["model"].get_params(deep=False),
        "n_estimators": 128,
        "learning_rate": 0.07,
        "max_depth": 3,
        "min_samples_leaf": 8,
        "loss": "squared_error",
        "subsample": 1.0,
        "max_features": None,
        "random_state": 2026,
    }


def test_native_factory_predictions_are_finite_and_non_negative(
    specs: tuple[TrialSpec, ...], f4: FoldRows
) -> None:
    spec = _spec(specs, "STAT-A1")
    rows = training_rows_for_trial(spec, f4)
    estimator = build_estimator(spec).fit(rows, rows["cnt"])
    probe = rows.drop(columns="cnt").tail(16).copy()
    probe.loc[:, "elapsed_days"] += 1_000_000

    predictions = estimator.predict(probe)

    assert np.isfinite(predictions).all()
    assert (predictions >= 0).all()


def test_native_clipping_equals_maximum_of_a_negative_raw_prediction() -> None:
    positions = np.arange(8, dtype=float)
    features = pd.DataFrame(
        {
            "season": [1, 2, 3, 4, 1, 2, 3, 4],
            "mnth": np.arange(1, 9),
            "hr": np.arange(8),
            "holiday": [0, 1] * 4,
            "weekday": np.arange(8) % 7,
            "workingday": [1, 0] * 4,
            "weathersit": [1, 2, 3, 4, 1, 2, 3, 4],
            **{
                column: positions + offset
                for offset, column in enumerate(TEMPORAL_FEATURE_COLUMNS[7:], start=1)
            },
        }
    )
    target = 20 + positions
    spec = _spec(load_trial_specs(PROTOCOL), "STAT-A1")
    estimator = build_estimator(spec).fit(features, target)
    probe = features.head(1).copy()
    probe.loc[:, TEMPORAL_FEATURE_COLUMNS[7:]] = -1_000_000.0

    raw = estimator.predict_raw(probe)
    clipped = estimator.predict(probe)

    assert raw[0] < 0
    np.testing.assert_array_equal(clipped, np.maximum(0.0, raw))
    assert clipped[0] == 0.0
    assert not np.array_equal(clipped, raw)
