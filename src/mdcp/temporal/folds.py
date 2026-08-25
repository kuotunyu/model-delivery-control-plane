"""Exact rolling development folds and private in-memory row identities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.workload.splits import DevelopmentPartitions


@dataclass(frozen=True)
class FoldSpec:
    """One contiguous, half-open training and validation interval."""

    fold_id: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp

    def __post_init__(self) -> None:
        boundaries = tuple(
            pd.Timestamp(value)
            for value in (
                self.train_start,
                self.train_end,
                self.validation_start,
                self.validation_end,
            )
        )
        if not self.fold_id or any(boundary.tz is not None for boundary in boundaries):
            raise ValueError("invalid fold specification")
        if any(
            boundary.hour
            or boundary.minute
            or boundary.second
            or boundary.microsecond
            or boundary.nanosecond
            for boundary in boundaries
        ):
            raise ValueError("fold boundaries must be exact local midnights")
        train_start, train_end, validation_start, validation_end = boundaries
        if not train_start < train_end == validation_start < validation_end:
            raise ValueError("fold intervals must be contiguous and non-empty")
        object.__setattr__(self, "train_start", train_start)
        object.__setattr__(self, "train_end", train_end)
        object.__setattr__(self, "validation_start", validation_start)
        object.__setattr__(self, "validation_end", validation_end)


_CANONICAL_FOLD_SPECS = (
    FoldSpec(
        "F1",
        pd.Timestamp("2011-01-01T00:00:00"),
        pd.Timestamp("2011-07-01T00:00:00"),
        pd.Timestamp("2011-07-01T00:00:00"),
        pd.Timestamp("2011-10-01T00:00:00"),
    ),
    FoldSpec(
        "F2",
        pd.Timestamp("2011-01-01T00:00:00"),
        pd.Timestamp("2011-10-01T00:00:00"),
        pd.Timestamp("2011-10-01T00:00:00"),
        pd.Timestamp("2012-01-01T00:00:00"),
    ),
    FoldSpec(
        "F3",
        pd.Timestamp("2011-01-01T00:00:00"),
        pd.Timestamp("2012-01-01T00:00:00"),
        pd.Timestamp("2012-01-01T00:00:00"),
        pd.Timestamp("2012-04-01T00:00:00"),
    ),
    FoldSpec(
        "F4",
        pd.Timestamp("2011-01-01T00:00:00"),
        pd.Timestamp("2012-04-01T00:00:00"),
        pd.Timestamp("2012-04-01T00:00:00"),
        pd.Timestamp("2012-07-01T00:00:00"),
    ),
)


@dataclass(frozen=True)
class SourceRowIdentity:
    """An in-memory validation-row identity bound to its canonical digest."""

    fold_id: str
    request_id: str
    local_timestamp: str
    source_position: int
    identity_sha256: str


@dataclass(frozen=True)
class FoldRows:
    """Sorted row views and aggregate public-safe identifiers for one fold."""

    spec: FoldSpec
    train: pd.DataFrame
    validation: pd.DataFrame
    inventory: tuple[SourceRowIdentity, ...]
    training_rows_sha256: str
    validation_rows_sha256: str
    inventory_sha256: str

    @property
    def training_row_count(self) -> int:
        return len(self.train)

    @property
    def validation_row_count(self) -> int:
        return len(self.validation)


@dataclass(frozen=True)
class _OrderedSourceRow:
    timestamp: pd.Timestamp
    request_id: str
    source_position: int


def load_fold_specs(protocol: Mapping[str, Any]) -> tuple[FoldSpec, ...]:
    """Load the declared fold inventory without deriving dates from input rows."""
    raw_folds = protocol.get("folds")
    if not isinstance(raw_folds, Sequence) or isinstance(raw_folds, str | bytes):
        raise ValueError("protocol folds are invalid")

    specs: list[FoldSpec] = []
    for raw_fold in raw_folds:
        if not isinstance(raw_fold, Mapping) or set(raw_fold) != {
            "id",
            "train_start",
            "train_end",
            "validation_start",
            "validation_end",
        }:
            raise ValueError("protocol fold is invalid")
        try:
            specs.append(
                FoldSpec(
                    fold_id=str(raw_fold["id"]),
                    train_start=pd.Timestamp(raw_fold["train_start"]),
                    train_end=pd.Timestamp(raw_fold["train_end"]),
                    validation_start=pd.Timestamp(raw_fold["validation_start"]),
                    validation_end=pd.Timestamp(raw_fold["validation_end"]),
                )
            )
        except (TypeError, ValueError) as error:
            raise ValueError("protocol fold is invalid") from error

    if tuple(specs) != _CANONICAL_FOLD_SPECS:
        raise ValueError("protocol fold inventory is invalid")
    return tuple(specs)


def materialize_folds(
    rows: pd.DataFrame | DevelopmentPartitions, specs: Sequence[FoldSpec]
) -> tuple[FoldRows, ...]:
    """Materialize sorted, half-open fold views from development-only rows."""
    _validate_materialization_specs(specs)
    source = _development_source(rows)
    ordered_rows = _ordered_source_rows(source)
    _reject_duplicate_identities(ordered_rows)
    ordered_index = pd.DatetimeIndex(
        [row.timestamp for row in ordered_rows], name=source.index.name
    )
    ordered = source.iloc[[row.source_position for row in ordered_rows]].copy()
    ordered.index = ordered_index

    folds: list[FoldRows] = []
    for spec in specs:
        train_mask = (ordered.index >= spec.train_start) & (ordered.index < spec.train_end)
        validation_mask = (ordered.index >= spec.validation_start) & (
            ordered.index < spec.validation_end
        )
        train = ordered.loc[train_mask].copy()
        validation = ordered.loc[validation_mask].copy()
        _require_non_empty_fold(train, validation)
        _prove_whole_day_grouping(train, validation)
        validation_rows = [
            row
            for row in ordered_rows
            if spec.validation_start <= row.timestamp < spec.validation_end
        ]
        inventory = tuple(_identity_for(spec.fold_id, row) for row in validation_rows)
        folds.append(
            FoldRows(
                spec=spec,
                train=train,
                validation=validation,
                inventory=inventory,
                training_rows_sha256=_row_set_digest(
                    row
                    for row in ordered_rows
                    if spec.train_start <= row.timestamp < spec.train_end
                ),
                validation_rows_sha256=_row_set_digest(validation_rows),
                inventory_sha256=sha256_hex(
                    canonicalize_json([identity.identity_sha256 for identity in inventory])
                ),
            )
        )
    return tuple(folds)


def _development_source(rows: pd.DataFrame | DevelopmentPartitions) -> pd.DataFrame:
    if isinstance(rows, DevelopmentPartitions):
        source = pd.concat((rows.train, rows.h1), copy=True)
    elif isinstance(rows, pd.DataFrame):
        source = rows.copy()
    else:
        raise ValueError("development rows are invalid")
    if not isinstance(source.index, pd.DatetimeIndex) or source.index.tz is not None:
        raise ValueError("development chronology is invalid")
    return source


def _validate_materialization_specs(specs: Sequence[FoldSpec]) -> None:
    if not all(isinstance(spec, FoldSpec) for spec in specs):
        raise ValueError("fold specifications are invalid")
    chronological = tuple(sorted(specs, key=lambda spec: spec.validation_start))
    if any(
        later.validation_start < earlier.validation_end
        for earlier, later in zip(chronological, chronological[1:], strict=False)
    ):
        raise ValueError("validation intervals overlap")
    if tuple(specs) != chronological:
        raise ValueError("fold specifications are not chronological")
    if tuple(specs) != _CANONICAL_FOLD_SPECS:
        raise ValueError("fold specifications are not canonical")


def is_frozen_validation_timestamp(fold_id: str, timestamp: object) -> bool:
    """Return whether a naive timestamp is inside its exact approved fold interval."""
    if type(fold_id) is not str:
        return False
    matching = tuple(spec for spec in _CANONICAL_FOLD_SPECS if spec.fold_id == fold_id)
    if len(matching) != 1:
        return False
    try:
        local = pd.Timestamp(timestamp)
    except (TypeError, ValueError):
        return False
    if local.tz is not None:
        return False
    spec = matching[0]
    return bool(spec.validation_start <= local < spec.validation_end)


def _ordered_source_rows(source: pd.DataFrame) -> list[_OrderedSourceRow]:
    ordered: list[_OrderedSourceRow] = []
    request_ids = source.get("request_id")
    for source_position, timestamp in enumerate(source.index):
        local_timestamp = pd.Timestamp(timestamp)
        request_id = (
            f"development-{source_position}"
            if request_ids is None
            else str(request_ids.iloc[source_position])
        )
        if not request_id:
            raise ValueError("source request identity is invalid")
        ordered.append(
            _OrderedSourceRow(
                timestamp=local_timestamp,
                request_id=request_id,
                source_position=source_position,
            )
        )
    return sorted(
        ordered,
        key=lambda row: (row.timestamp.normalize(), row.timestamp.hour, row.source_position),
    )


def _reject_duplicate_identities(rows: Sequence[_OrderedSourceRow]) -> None:
    timestamps = [row.timestamp for row in rows]
    request_ids = [row.request_id for row in rows]
    if len(timestamps) != len(set(timestamps)) or len(request_ids) != len(set(request_ids)):
        raise ValueError("duplicate source identity")


def _require_non_empty_fold(train: pd.DataFrame, validation: pd.DataFrame) -> None:
    if train.empty or validation.empty:
        raise ValueError("fold rows are incomplete")


def _prove_whole_day_grouping(train: pd.DataFrame, validation: pd.DataFrame) -> None:
    train_days = set(train.index.normalize())
    validation_days = set(validation.index.normalize())
    if train_days.intersection(validation_days):
        raise ValueError("calendar day crosses a fold boundary")


def _identity_for(fold_id: str, row: _OrderedSourceRow) -> SourceRowIdentity:
    material = {
        "fold_id": fold_id,
        "request_id": row.request_id,
        "local_timestamp": row.timestamp.isoformat(timespec="seconds"),
        "source_position": row.source_position,
    }
    return SourceRowIdentity(
        fold_id=fold_id,
        request_id=row.request_id,
        local_timestamp=material["local_timestamp"],
        source_position=row.source_position,
        identity_sha256=sha256_hex(canonicalize_json(material)),
    )


def _row_set_digest(rows: Iterable[_OrderedSourceRow]) -> str:
    return sha256_hex(
        canonicalize_json(
            [
                {
                    "local_timestamp": row.timestamp.isoformat(timespec="seconds"),
                    "request_id": row.request_id,
                    "source_position": row.source_position,
                }
                for row in rows
            ]
        )
    )
