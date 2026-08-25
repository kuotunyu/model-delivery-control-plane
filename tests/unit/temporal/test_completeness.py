from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pytest

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.temporal.completeness import (
    ADAPTER_REASON_CODES,
    LABEL_REASON_CODES,
    PREDICTION_REASON_CODES,
    AdapterOutcome,
    LabelOutcome,
    PredictionOutcome,
    assemble_development_pairs,
)
from mdcp.temporal.folds import SourceRowIdentity


def _identity(position: int) -> SourceRowIdentity:
    local_timestamp = f"2011-07-{position + 1:02d}T08:00:00"
    material = {
        "fold_id": "F1",
        "request_id": f"request-{position}",
        "local_timestamp": local_timestamp,
        "source_position": position,
    }
    return SourceRowIdentity(
        **material,
        identity_sha256=sha256_hex(canonicalize_json(material)),
    )


def _complete_streams(count: int = 3):
    inventory = tuple(_identity(position) for position in range(count))
    adapters = tuple(
        AdapterOutcome(
            identity=identity,
            succeeded=True,
            calendar_day=date(2011, 7, 1) + timedelta(days=position),
            groups=("weather_clear", "day_working", "demand_off_peak"),
        )
        for position, identity in enumerate(inventory)
    )
    stable = tuple(
        PredictionOutcome(identity=identity, succeeded=True, value=float(position + 10))
        for position, identity in enumerate(inventory)
    )
    candidate = tuple(
        PredictionOutcome(identity=identity, succeeded=True, value=float(position + 9))
        for position, identity in enumerate(inventory)
    )
    labels = tuple(
        LabelOutcome(identity=identity, succeeded=True, value=float(position + 11))
        for position, identity in enumerate(inventory)
    )
    return inventory, adapters, stable, candidate, labels


def test_complete_development_streams_preserve_inventory_order() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()

    receipt, rows = assemble_development_pairs(
        inventory,
        tuple(reversed(adapters)),
        (stable[1], stable[2], stable[0]),
        tuple(reversed(candidate)),
        (labels[2], labels[0], labels[1]),
    )

    assert receipt.verdict == "PASS"
    assert receipt.source_count == 3
    assert receipt.adapter_success_rate == 1.0
    assert receipt.stable_success_rate == 1.0
    assert receipt.candidate_success_rate == 1.0
    assert receipt.label_success_rate == 1.0
    assert [row.request_id for row in rows] == [
        "request-0",
        "request-1",
        "request-2",
    ]
    assert rows[0].stable_prediction == 10.0
    assert rows[0].candidate_prediction == 9.0
    assert rows[0].label == 11.0


@pytest.mark.parametrize("stream", ["adapter", "stable", "candidate"])
def test_one_missing_identity_makes_whole_trial_unknown(stream: str) -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    inputs = {
        "adapter": adapters,
        "stable": stable,
        "candidate": candidate,
    }
    inputs[stream] = inputs[stream][:-1]

    receipt, rows = assemble_development_pairs(
        inventory,
        inputs["adapter"],
        inputs["stable"],
        inputs["candidate"],
        labels,
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.source_count == 3
    layer = getattr(receipt, stream)
    assert layer.missing_count == 1
    assert layer.failure_count == 1


def test_prediction_failure_cannot_be_counted_as_missing_label() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    candidate = (
        *candidate[:-1],
        PredictionOutcome(
            identity=inventory[-1],
            succeeded=False,
            reason_code="INVALID_RESPONSE",
        ),
    )

    receipt, rows = assemble_development_pairs(inventory, adapters, stable, candidate, labels)

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.candidate_failure_count == 1
    assert receipt.candidate.reason_count("INVALID_RESPONSE") == 1
    assert receipt.label_missing_count == 0
    assert receipt.label_success_count == receipt.source_count


@pytest.mark.parametrize("stream", ["adapter", "stable", "candidate", "labels"])
def test_duplicate_expected_identity_is_not_hidden_by_set_equality(stream: str) -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    inputs = {
        "adapter": adapters,
        "stable": stable,
        "candidate": candidate,
        "labels": labels,
    }
    inputs[stream] = (*inputs[stream], inputs[stream][0])

    receipt, rows = assemble_development_pairs(
        inventory,
        inputs["adapter"],
        inputs["stable"],
        inputs["candidate"],
        inputs["labels"],
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    layer = getattr(receipt, "label" if stream == "labels" else stream)
    assert layer.duplicate_count == 1
    assert layer.success_count == 2


def test_unexpected_identity_fails_closed_even_when_all_expected_ids_are_present() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    unexpected = _identity(8)

    receipt, rows = assemble_development_pairs(
        inventory,
        adapters,
        stable,
        (*candidate, PredictionOutcome(unexpected, True, value=8.0)),
        labels,
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.candidate.unexpected_count == 1
    assert receipt.candidate_success_rate == 1.0


def test_identity_digest_spoof_is_rejected_before_pairing() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    spoofed = replace(inventory[0], request_id="another-request")

    receipt, rows = assemble_development_pairs(
        inventory,
        adapters,
        stable,
        (replace(candidate[0], identity=spoofed), *candidate[1:]),
        labels,
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.candidate.missing_count == 1
    assert receipt.candidate.unexpected_count == 1


def test_duplicate_authoritative_inventory_fails_closed() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()

    receipt, rows = assemble_development_pairs(
        (*inventory, inventory[0]), adapters, stable, candidate, labels
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.source_count == 4
    assert "SOURCE_INVENTORY_INVALID" in receipt.reason_codes


def test_noncanonical_source_timestamp_fails_closed_even_with_matching_digest() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams(1)
    material = {
        "fold_id": "F1",
        "request_id": inventory[0].request_id,
        "local_timestamp": "2011-07-01",
        "source_position": 0,
    }
    noncanonical = SourceRowIdentity(
        **material,
        identity_sha256=sha256_hex(canonicalize_json(material)),
    )

    receipt, rows = assemble_development_pairs(
        (noncanonical,),
        (replace(adapters[0], identity=noncanonical),),
        (replace(stable[0], identity=noncanonical),),
        (replace(candidate[0], identity=noncanonical),),
        (replace(labels[0], identity=noncanonical),),
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.reason_codes == ("SOURCE_INVENTORY_INVALID",)


@pytest.mark.parametrize("bad_value", [-0.01, float("inf"), float("-inf"), float("nan"), True])
@pytest.mark.parametrize("stream", ["stable", "candidate", "labels"])
def test_non_finite_negative_or_boolean_numeric_output_is_invalid(
    stream: str, bad_value: float
) -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    inputs = {"stable": stable, "candidate": candidate, "labels": labels}
    inputs[stream] = (replace(inputs[stream][0], value=bad_value), *inputs[stream][1:])

    receipt, rows = assemble_development_pairs(
        inventory,
        adapters,
        inputs["stable"],
        inputs["candidate"],
        inputs["labels"],
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    layer = getattr(receipt, "label" if stream == "labels" else stream)
    assert layer.invalid_count == 1


def test_genuine_missing_development_label_is_separate_but_still_unknown() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    labels = (
        *labels[:-1],
        LabelOutcome(
            identity=inventory[-1],
            succeeded=False,
            reason_code="MISSING_LABEL",
        ),
    )

    receipt, rows = assemble_development_pairs(inventory, adapters, stable, candidate, labels)

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.label_missing_count == 1
    assert receipt.adapter_failure_count == 0
    assert receipt.stable_failure_count == 0
    assert receipt.candidate_failure_count == 0


def test_missing_label_outcome_is_an_accounting_gap_not_genuine_label_loss() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()

    receipt, rows = assemble_development_pairs(inventory, adapters, stable, candidate, labels[:-1])

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.label.missing_count == 1
    assert receipt.label.reason_count("MISSING_IDENTITY") == 1
    assert receipt.label.reason_count("MISSING_LABEL") == 0
    assert receipt.label_missing_count == 0


def test_reason_code_inventories_are_fixed_and_unknown_codes_are_invalid() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    candidate = (
        PredictionOutcome(inventory[0], False, reason_code="ARBITRARY_EXCEPTION_TEXT"),
        *candidate[1:],
    )

    receipt, rows = assemble_development_pairs(inventory, adapters, stable, candidate, labels)

    assert rows == ()
    assert tuple(code for code, _ in receipt.adapter.reason_counts) == ADAPTER_REASON_CODES
    assert tuple(code for code, _ in receipt.stable.reason_counts) == PREDICTION_REASON_CODES
    assert tuple(code for code, _ in receipt.candidate.reason_counts) == PREDICTION_REASON_CODES
    assert tuple(code for code, _ in receipt.label.reason_counts) == LABEL_REASON_CODES
    assert receipt.candidate.invalid_count == 1
    assert receipt.candidate.reason_count("INVALID_REASON_CODE") == 1
    assert "ARBITRARY_EXCEPTION_TEXT" not in repr(receipt)


def test_unhashable_reason_code_fails_closed_without_escaping_accounting() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    malformed = PredictionOutcome(
        inventory[0],
        False,
        reason_code=["INVALID_RESPONSE"],  # type: ignore[arg-type]
    )

    receipt, rows = assemble_development_pairs(
        inventory,
        adapters,
        stable,
        (malformed, *candidate[1:]),
        labels,
    )

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.candidate.invalid_count == 1
    assert receipt.candidate.reason_count("INVALID_REASON_CODE") == 1


def test_adapter_calendar_day_must_match_the_authoritative_identity() -> None:
    inventory, adapters, stable, candidate, labels = _complete_streams()
    adapters = (
        replace(adapters[0], calendar_day=date(2011, 7, 2)),
        *adapters[1:],
    )

    receipt, rows = assemble_development_pairs(inventory, adapters, stable, candidate, labels)

    assert receipt.verdict == "UNKNOWN"
    assert rows == ()
    assert receipt.adapter.invalid_count == 1
