from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from mdcp.temporal.folds import FoldSpec, load_fold_specs, materialize_folds
from mdcp.workload.splits import DevelopmentPartitions

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

    assert [
        (
            fold.spec.train_start,
            fold.spec.train_end,
            fold.spec.validation_start,
            fold.spec.validation_end,
        )
        for fold in folds
    ] == [
        (
            pd.Timestamp("2011-01-01T00:00:00"),
            pd.Timestamp("2011-07-01T00:00:00"),
            pd.Timestamp("2011-07-01T00:00:00"),
            pd.Timestamp("2011-10-01T00:00:00"),
        ),
        (
            pd.Timestamp("2011-01-01T00:00:00"),
            pd.Timestamp("2011-10-01T00:00:00"),
            pd.Timestamp("2011-10-01T00:00:00"),
            pd.Timestamp("2012-01-01T00:00:00"),
        ),
        (
            pd.Timestamp("2011-01-01T00:00:00"),
            pd.Timestamp("2012-01-01T00:00:00"),
            pd.Timestamp("2012-01-01T00:00:00"),
            pd.Timestamp("2012-04-01T00:00:00"),
        ),
        (
            pd.Timestamp("2011-01-01T00:00:00"),
            pd.Timestamp("2012-04-01T00:00:00"),
            pd.Timestamp("2012-04-01T00:00:00"),
            pd.Timestamp("2012-07-01T00:00:00"),
        ),
    ]
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


def test_duplicate_request_identity_at_distinct_timestamps_is_rejected() -> None:
    frame = _synthetic_development_frame().copy()
    frame["request_id"] = [f"request-{position}" for position in range(len(frame))]
    frame.iloc[1, frame.columns.get_loc("request_id")] = frame.iloc[0]["request_id"]

    with pytest.raises(ValueError, match="duplicate source identity"):
        materialize_folds(frame, EXACT_FOLD_SPECS)


def test_materialization_rejects_global_non_adjacent_validation_overlap() -> None:
    overlapping_specs = (
        FoldSpec(
            "F1",
            pd.Timestamp("2011-01-01"),
            pd.Timestamp("2011-07-01"),
            pd.Timestamp("2011-07-01"),
            pd.Timestamp("2011-10-01"),
        ),
        FoldSpec(
            "F2",
            pd.Timestamp("2011-01-01"),
            pd.Timestamp("2011-10-01"),
            pd.Timestamp("2011-10-01"),
            pd.Timestamp("2012-01-01"),
        ),
        FoldSpec(
            "F3",
            pd.Timestamp("2011-01-01"),
            pd.Timestamp("2011-08-01"),
            pd.Timestamp("2011-08-01"),
            pd.Timestamp("2011-11-01"),
        ),
    )

    with pytest.raises(ValueError, match="validation intervals overlap"):
        materialize_folds(_synthetic_development_frame(), overlapping_specs)


def test_materialization_rejects_out_of_order_disjoint_fold_specs() -> None:
    out_of_order_specs = (EXACT_FOLD_SPECS[1], EXACT_FOLD_SPECS[0], *EXACT_FOLD_SPECS[2:])

    with pytest.raises(ValueError, match="fold specifications are not chronological"):
        materialize_folds(_synthetic_development_frame(), out_of_order_specs)


def test_materialization_from_development_partitions_uses_only_train_and_h1() -> None:
    frame = _synthetic_development_frame()
    partitions = DevelopmentPartitions(
        train=frame.loc[frame.index < pd.Timestamp("2012-01-01")].copy(),
        h1=frame.loc[frame.index >= pd.Timestamp("2012-01-01")].copy(),
    )

    folds = materialize_folds(partitions, EXACT_FOLD_SPECS)

    assert tuple(DevelopmentPartitions.__dataclass_fields__) == ("train", "h1")
    assert not hasattr(partitions, "h2")
    assert [len(fold.inventory) for fold in folds] == [2_208, 2_208, 2_184, 2_184]


def test_load_fold_specs_rejects_malformed_fold_mapping() -> None:
    malformed_protocol = _protocol()
    malformed_fold = dict(malformed_protocol["folds"][0])
    malformed_fold.pop("validation_end")
    malformed_protocol["folds"] = [malformed_fold, *malformed_protocol["folds"][1:]]

    with pytest.raises(ValueError, match="protocol fold is invalid"):
        load_fold_specs(malformed_protocol)


@pytest.mark.parametrize(
    ("fold_position", "field", "mutated_value"),
    [
        (0, "id", "F4"),
        (0, "validation_end", "2011-09-01T00:00:00"),
        (1, "train_start", "2011-02-01T00:00:00"),
        (3, "validation_start", "2012-05-01T00:00:00"),
    ],
)
def test_load_fold_specs_rejects_any_mutated_canonical_identity(
    fold_position: int, field: str, mutated_value: str
) -> None:
    protocol = _protocol()
    protocol["folds"][fold_position][field] = mutated_value

    with pytest.raises(ValueError, match=r"protocol fold(?: inventory)? is invalid"):
        load_fold_specs(protocol)


def test_materialization_rejects_directly_constructed_noncanonical_boundaries() -> None:
    mutated = FoldSpec(
        "F1",
        pd.Timestamp("2011-01-01"),
        pd.Timestamp("2011-07-01"),
        pd.Timestamp("2011-07-01"),
        pd.Timestamp("2011-09-01"),
    )

    with pytest.raises(ValueError, match="fold specifications are not canonical"):
        materialize_folds(
            _synthetic_development_frame(),
            (mutated, *EXACT_FOLD_SPECS[1:]),
        )


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
