from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given
from hypothesis import strategies as st

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.temporal.completeness import (
    AdapterOutcome,
    LabelOutcome,
    PredictionOutcome,
    assemble_development_pairs,
)
from mdcp.temporal.folds import SourceRowIdentity


def _identity(position: int) -> SourceRowIdentity:
    day = position // 24 + 1
    hour = position % 24
    local_timestamp = f"2011-07-{day:02d}T{hour:02d}:00:00"
    material = {
        "fold_id": "F1",
        "request_id": f"property-{position:04d}",
        "local_timestamp": local_timestamp,
        "source_position": position,
    }
    return SourceRowIdentity(
        **material,
        identity_sha256=sha256_hex(canonicalize_json(material)),
    )


def _streams(count: int):
    inventory = tuple(_identity(position) for position in range(count))
    adapters = tuple(
        AdapterOutcome(
            identity=identity,
            succeeded=True,
            calendar_day=date(2011, 7, 1) + timedelta(days=position // 24),
            groups=("weather_clear", "day_working", "demand_off_peak"),
        )
        for position, identity in enumerate(inventory)
    )
    stable = tuple(PredictionOutcome(identity, True, value=2.0) for identity in inventory)
    candidate = tuple(PredictionOutcome(identity, True, value=1.0) for identity in inventory)
    labels = tuple(LabelOutcome(identity, True, value=1.5) for identity in inventory)
    return inventory, adapters, stable, candidate, labels


@given(
    count=st.integers(min_value=1, max_value=40),
    stream=st.sampled_from(("adapter", "stable", "candidate", "labels")),
    data=st.data(),
)
def test_removing_any_identity_never_shrinks_the_authoritative_denominator(
    count: int, stream: str, data: st.DataObject
) -> None:
    inventory, adapters, stable, candidate, labels = _streams(count)
    inputs = {
        "adapter": adapters,
        "stable": stable,
        "candidate": candidate,
        "labels": labels,
    }
    removed = data.draw(st.integers(min_value=0, max_value=count - 1))
    inputs[stream] = inputs[stream][:removed] + inputs[stream][removed + 1 :]

    receipt, rows = assemble_development_pairs(
        inventory,
        inputs["adapter"],
        inputs["stable"],
        inputs["candidate"],
        inputs["labels"],
    )

    assert receipt.source_count == count
    assert receipt.verdict == "UNKNOWN"
    assert rows == ()


@given(order=st.permutations((0, 1, 2, 3, 4)))
def test_stream_order_cannot_change_authoritative_pair_order(order: list[int]) -> None:
    inventory, adapters, stable, candidate, labels = _streams(5)

    receipt, rows = assemble_development_pairs(
        inventory,
        tuple(adapters[position] for position in order),
        tuple(stable[position] for position in order),
        tuple(candidate[position] for position in order),
        tuple(labels[position] for position in order),
    )

    assert receipt.verdict == "PASS"
    assert tuple(row.request_id for row in rows) == tuple(
        identity.request_id for identity in inventory
    )


@given(
    count=st.integers(min_value=1, max_value=40),
    stream=st.sampled_from(("adapter", "stable", "candidate", "labels")),
    data=st.data(),
)
def test_duplicate_identity_never_replaces_a_unique_success(
    count: int, stream: str, data: st.DataObject
) -> None:
    inventory, adapters, stable, candidate, labels = _streams(count)
    inputs = {
        "adapter": adapters,
        "stable": stable,
        "candidate": candidate,
        "labels": labels,
    }
    duplicated = data.draw(st.integers(min_value=0, max_value=count - 1))
    inputs[stream] = (*inputs[stream], inputs[stream][duplicated])

    receipt, rows = assemble_development_pairs(
        inventory,
        inputs["adapter"],
        inputs["stable"],
        inputs["candidate"],
        inputs["labels"],
    )

    layer = getattr(receipt, "label" if stream == "labels" else stream)
    assert receipt.source_count == count
    assert layer.duplicate_count == 1
    assert layer.success_count == count - 1
    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
