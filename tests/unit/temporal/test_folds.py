from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from mdcp.temporal.folds import FoldSpec, load_fold_specs, materialize_folds

sys.path.insert(0, str(Path(__file__).parents[2]))


def _synthetic_development_frame() -> pd.DataFrame:
    from temporal_fixtures import synthetic_development_frame

    return synthetic_development_frame()


def _protocol() -> dict[str, object]:
    repository_root = Path(__file__).parents[3]
    return json.loads(
        (repository_root / "configs" / "workload" / "temporal-development-v2.json").read_text(
            encoding="utf-8"
        )
    )


EXACT_FOLD_SPECS = load_fold_specs(_protocol())


def test_four_folds_are_exact_and_disjoint() -> None:
    folds = materialize_folds(_synthetic_development_frame(), EXACT_FOLD_SPECS)

    assert [fold.spec.fold_id for fold in folds] == ["F1", "F2", "F3", "F4"]
    assert folds[0].train.index.min() == pd.Timestamp("2011-01-01")
    assert folds[-1].validation.index.max() < pd.Timestamp("2012-07-01")
    validation_ids = [identity.request_id for fold in folds for identity in fold.inventory]
    assert len(validation_ids) == len(set(validation_ids))
    assert all(fold.train.index.max() < fold.validation.index.min() for fold in folds)


def test_folds_use_expanding_history_and_half_open_boundaries() -> None:
    folds = materialize_folds(_synthetic_development_frame(), EXACT_FOLD_SPECS)

    assert [len(fold.train) for fold in folds] == [4_344, 6_552, 8_760, 10_944]
    assert [len(fold.validation) for fold in folds] == [2_208, 2_208, 2_184, 2_184]
    assert folds[0].validation.index.min() == pd.Timestamp("2011-07-01T00:00:00")
    assert folds[-1].validation.index.max() == pd.Timestamp("2012-06-30T23:00:00")


def test_materialization_sorts_rows_and_keeps_each_calendar_day_on_one_side() -> None:
    frame = _synthetic_development_frame().sample(frac=1.0, random_state=2026)

    folds = materialize_folds(frame, EXACT_FOLD_SPECS)

    for fold in folds:
        assert fold.train.index.is_monotonic_increasing
        assert fold.validation.index.is_monotonic_increasing
        assert set(fold.train.index.normalize()).isdisjoint(set(fold.validation.index.normalize()))


def test_duplicate_timestamp_identity_is_rejected() -> None:
    frame = _synthetic_development_frame()
    duplicate = pd.concat([frame.iloc[:1], frame])

    with pytest.raises(ValueError, match="duplicate source identity"):
        materialize_folds(duplicate, EXACT_FOLD_SPECS)


@pytest.mark.parametrize(
    ("train_end", "validation_start", "validation_end"),
    [
        ("2011-07-01T01:00:00", "2011-07-01T01:00:00", "2011-10-01T00:00:00"),
        ("2011-07-01T00:00:00", "2011-07-02T00:00:00", "2011-10-01T00:00:00"),
    ],
)
def test_fold_spec_rejects_non_midnight_or_gapped_boundaries(
    train_end: str, validation_start: str, validation_end: str
) -> None:
    with pytest.raises(ValueError):
        FoldSpec(
            fold_id="bad",
            train_start=pd.Timestamp("2011-01-01T00:00:00"),
            train_end=pd.Timestamp(train_end),
            validation_start=pd.Timestamp(validation_start),
            validation_end=pd.Timestamp(validation_end),
        )
