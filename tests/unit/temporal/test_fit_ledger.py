from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from typing import get_type_hints

import pytest

from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.temporal.completeness import AdapterOutcome, LabelOutcome, PredictionOutcome
from mdcp.temporal.evaluation import QualificationFoldDigests, QualificationResult
from mdcp.temporal.folds import SourceRowIdentity
from mdcp.temporal.runner import (
    EXACT_FOLD_IDS,
    EXACT_TRIAL_IDS,
    DevelopmentFitRequest,
    DevelopmentFoldResult,
    DevelopmentRunBundle,
    DevelopmentStateMachine,
    FitBudgetError,
    FitLedger,
    FitPhase,
    FitRecord,
)
from mdcp.temporal.selection import (
    ProvisionalWinner,
    ReplaySelectionSession,
    rank_qualified,
)
from mdcp.temporal.trials import canonical_trial_identity


def _fold_digests(trial_id: str) -> tuple[QualificationFoldDigests, ...]:
    identity = canonical_trial_identity(trial_id)
    return tuple(
        QualificationFoldDigests(
            fold_id=fold_id,
            configuration_sha256=identity.configuration_sha256,
            preprocessing_state_sha256=sha256_hex(f"{trial_id}:{fold_id}:pre".encode()),
            feature_vector_sha256=sha256_hex(f"{trial_id}:{fold_id}:features".encode()),
            prediction_vector_sha256=sha256_hex(f"{trial_id}:{fold_id}:predictions".encode()),
            metric_sha256=sha256_hex(f"{trial_id}:{fold_id}:metrics".encode()),
            receipt_sha256=sha256_hex(f"{trial_id}:{fold_id}:receipt".encode()),
        )
        for fold_id in EXACT_FOLD_IDS
    )


def _qualification(trial_id: str, *, score: float | None) -> QualificationResult:
    identity = canonical_trial_identity(trial_id)
    qualified = score is not None
    return QualificationResult(
        trial_id=trial_id,
        family_id=identity.family_id,
        configuration_sha256=identity.configuration_sha256,
        report_sha256=sha256_hex(f"{trial_id}:report".encode()),
        verdict=GateVerdict.PASS if qualified else GateVerdict.FAIL,
        qualified=qualified,
        reason_codes=() if qualified else ("POOLED_OVERALL_POINT_RATIO",),
        pooled_ucb95=score,
        worst_fold_point=score,
        worst_subgroup_ucb95=score,
        fold_digests=_fold_digests(trial_id),
    )


_QUALIFICATIONS = tuple(
    _qualification(trial_id, score=0.9 if trial_id == "STAT-A1" else None)
    for trial_id in EXACT_TRIAL_IDS[1:]
)
EXACT_RANK_ONE = rank_qualified(_QUALIFICATIONS)
assert EXACT_RANK_ONE is not None


def _selection_session() -> ReplaySelectionSession:
    return ReplaySelectionSession(_QUALIFICATIONS)


def _rank_two_provisional(session: ReplaySelectionSession) -> ProvisionalWinner:
    trial_id = "REC-180-L4"
    identity = canonical_trial_identity(trial_id)
    return ProvisionalWinner(
        trial_id=trial_id,
        family_id=identity.family_id,
        configuration_sha256=identity.configuration_sha256,
        report_sha256=sha256_hex(f"{trial_id}:report".encode()),
        pooled_ucb95=1.0,
        worst_fold_point=1.0,
        worst_subgroup_ucb95=1.0,
        ranking_key=(1.0, 1.0, 1.0, 1, trial_id),
        fold_digests=_fold_digests(trial_id),
        qualification_inventory_sha256=session.qualification_inventory_sha256,
    )


def _closed_selection(ledger: FitLedger) -> None:
    for trial_id in EXACT_TRIAL_IDS:
        for fold_id in EXACT_FOLD_IDS:
            ledger.record_selection(trial_id, fold_id)


def test_fit_ledger_allows_only_frozen_selection_then_rank_one_replay() -> None:
    ledger = FitLedger()
    _closed_selection(ledger)
    winner = ledger.bind_session(_selection_session())
    assert winner == EXACT_RANK_ONE
    for fold_id in EXACT_FOLD_IDS:
        ledger.record_replay(winner.trial_id, fold_id)

    assert ledger.selection_count == 80
    assert ledger.replay_count == 4
    assert ledger.total_count == 84
    with pytest.raises(FitBudgetError, match="^REPLAY_ALREADY_CONSUMED$"):
        ledger.record_replay(EXACT_RANK_ONE.trial_id, "F1")


def test_fit_ledger_rejects_81st_selection_without_consuming_a_record() -> None:
    ledger = FitLedger()
    _closed_selection(ledger)

    with pytest.raises(FitBudgetError, match="^SELECTION_ALREADY_CONSUMED$"):
        ledger.record_selection(EXACT_TRIAL_IDS[0], "F1")

    assert ledger.total_count == 80


@pytest.mark.parametrize(
    ("trial_id", "fold_id"),
    ((EXACT_TRIAL_IDS[0], "F2"), ("ARBITRARY", "F1")),
)
def test_fit_ledger_rejects_wrong_or_arbitrary_selection(trial_id: str, fold_id: str) -> None:
    ledger = FitLedger()

    with pytest.raises(FitBudgetError, match="^SELECTION_ORDER_INVALID$"):
        ledger.record_selection(trial_id, fold_id)

    assert ledger.records == ()


def test_fit_ledger_rejects_arbitrary_replay_target() -> None:
    ledger = FitLedger()
    _closed_selection(ledger)
    ledger.bind_session(_selection_session())

    with pytest.raises(FitBudgetError, match="^REPLAY_TARGET_INVALID$"):
        ledger.record_replay("REC-180-L4", "F1")


def test_fit_ledger_rejects_well_formed_rank_two_winner_injection() -> None:
    ledger = FitLedger()
    _closed_selection(ledger)
    session = _selection_session()

    with pytest.raises(FitBudgetError, match="^SELECTION_SESSION_INVALID$"):
        ledger.bind_session(_rank_two_provisional(session))  # type: ignore[arg-type]

    assert ledger.total_count == 80


def test_fit_ledger_rejects_duplicate_or_wrong_replay_fold() -> None:
    ledger = FitLedger()
    _closed_selection(ledger)
    ledger.bind_session(_selection_session())
    ledger.record_replay(EXACT_RANK_ONE.trial_id, "F1")

    for fold_id in ("F1", "F3"):
        with pytest.raises(FitBudgetError, match="^REPLAY_FOLD_INVALID$"):
            ledger.record_replay(EXACT_RANK_ONE.trial_id, fold_id)

    assert ledger.replay_count == 1


def test_fit_ledger_rejects_rebinding_and_fifth_replay() -> None:
    ledger = FitLedger()
    _closed_selection(ledger)
    session = _selection_session()
    ledger.bind_session(session)

    with pytest.raises(FitBudgetError, match="^SELECTION_AUTHORITY_ALREADY_BOUND$"):
        ledger.bind_session(session)

    for fold_id in EXACT_FOLD_IDS:
        ledger.record_replay(EXACT_RANK_ONE.trial_id, fold_id)
    with pytest.raises(FitBudgetError, match="^REPLAY_ALREADY_CONSUMED$"):
        ledger.record_replay(EXACT_RANK_ONE.trial_id, "F1")


def test_fit_ledger_seals_no_winner_session_against_later_mutation() -> None:
    qualifications = tuple(_qualification(trial_id, score=None) for trial_id in EXACT_TRIAL_IDS[1:])
    session = ReplaySelectionSession(qualifications)
    ledger = FitLedger()
    _closed_selection(ledger)

    assert ledger.bind_session(session) is None
    with pytest.raises(FitBudgetError, match="^SELECTION_AUTHORITY_ALREADY_BOUND$"):
        ledger.bind_session(session)
    with pytest.raises(FitBudgetError, match="^NO_PROVISIONAL_WINNER$"):
        ledger.record_replay("STAT-A1", "F1")
    with pytest.raises(FitBudgetError, match="^SELECTION_ALREADY_CONSUMED$"):
        ledger.record_selection(EXACT_TRIAL_IDS[0], "F1")


def test_wave_three_fit_ledger_has_no_final_fit_authority() -> None:
    assert tuple(FitPhase) == (FitPhase.SELECTION, FitPhase.REPLAY)
    assert not hasattr(FitLedger, "record_final")
    assert not hasattr(FitLedger, "record")
    assert not hasattr(FitLedger, "bind_provisional")


def test_typed_fit_request_and_result_are_exact_frozen_slotted_values() -> None:
    request = DevelopmentFitRequest(
        sequence=1,
        phase=FitPhase.SELECTION,
        trial_id="CTRL-01",
        fold_id="F1",
    )
    result = DevelopmentFoldResult(
        trial_id="CTRL-01",
        fold_id="F1",
        inventory=(),
        adapters=(),
        predictions=(),
        labels=(),
        contract_verdict=GateVerdict.PASS,
        preprocessing_state_sha256="1" * 64,
        feature_vector_sha256="2" * 64,
        prediction_vector_sha256="3" * 64,
        metric_sha256="4" * 64,
        receipt_sha256="5" * 64,
    )

    assert tuple(field.name for field in fields(request)) == (
        "sequence",
        "phase",
        "trial_id",
        "fold_id",
    )
    assert tuple(field.name for field in fields(result)) == (
        "trial_id",
        "fold_id",
        "inventory",
        "adapters",
        "predictions",
        "labels",
        "contract_verdict",
        "preprocessing_state_sha256",
        "feature_vector_sha256",
        "prediction_vector_sha256",
        "metric_sha256",
        "receipt_sha256",
    )
    assert get_type_hints(DevelopmentFitRequest) == {
        "sequence": int,
        "phase": FitPhase,
        "trial_id": str,
        "fold_id": str,
    }
    assert get_type_hints(DevelopmentFoldResult) == {
        "trial_id": str,
        "fold_id": str,
        "inventory": tuple[SourceRowIdentity, ...],
        "adapters": tuple[AdapterOutcome, ...],
        "predictions": tuple[PredictionOutcome, ...],
        "labels": tuple[LabelOutcome, ...],
        "contract_verdict": GateVerdict,
        "preprocessing_state_sha256": str,
        "feature_vector_sha256": str,
        "prediction_vector_sha256": str,
        "metric_sha256": str,
        "receipt_sha256": str,
    }
    assert not hasattr(request, "__dict__")
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        request.sequence = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.fold_id = "F2"  # type: ignore[misc]


def test_state_machine_has_only_the_closed_typed_transition_surface() -> None:
    assert tuple(inspect.signature(DevelopmentStateMachine).parameters) == ()
    assert tuple(inspect.signature(DevelopmentStateMachine.next_fit_request).parameters) == (
        "self",
    )
    assert tuple(inspect.signature(DevelopmentStateMachine.record_fit_result).parameters) == (
        "self",
        "request",
        "result",
    )
    assert tuple(inspect.signature(DevelopmentStateMachine.finalize).parameters) == ("self",)
    assert get_type_hints(DevelopmentStateMachine.next_fit_request) == {
        "return": DevelopmentFitRequest | None
    }
    assert get_type_hints(DevelopmentStateMachine.record_fit_result) == {
        "request": DevelopmentFitRequest,
        "result": DevelopmentFoldResult,
        "return": type(None),
    }
    assert get_type_hints(DevelopmentStateMachine.finalize) == {"return": DevelopmentRunBundle}


def test_state_machine_reserves_the_ledger_before_issuing_one_request() -> None:
    machine = DevelopmentStateMachine()

    request = machine.next_fit_request()

    assert request == DevelopmentFitRequest(1, FitPhase.SELECTION, "CTRL-01", "F1")
    assert machine._ledger.records == (FitRecord(FitPhase.SELECTION, "CTRL-01", "F1"),)
    with pytest.raises(FitBudgetError, match="^FIT_REQUEST_OUTSTANDING$"):
        machine.next_fit_request()
