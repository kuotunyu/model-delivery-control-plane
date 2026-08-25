from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

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
    ["unknown_root", "unknown_parameter", "mutated_parameter", "mutated_categories"],
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
    else:  # pragma: no cover - parametrization is closed
        raise AssertionError("unknown mutation")

    with pytest.raises(ValueError, match="trial protocol is invalid"):
        load_trial_specs(protocol)


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
