from __future__ import annotations

import pytest

from mdcp.temporal.runner import (
    EXACT_FOLD_IDS,
    EXACT_TRIAL_IDS,
    FitBudgetError,
    FitLedger,
    FitPhase,
)


def test_fit_ledger_allows_only_the_frozen_80_selection_fits() -> None:
    """A changed selection limit or extra trial must be rejected before fitting."""
    ledger = FitLedger()

    for trial_id in EXACT_TRIAL_IDS:
        for fold_id in EXACT_FOLD_IDS:
            ledger.record(FitPhase.SELECTION, trial_id, fold_id)

    assert ledger.selection_count == 80
    with pytest.raises(FitBudgetError, match="selection fits frozen at 80"):
        ledger.record(FitPhase.SELECTION, "EXTRA", "F1")


def test_fit_ledger_rejects_a_fold_order_change_before_consuming_budget() -> None:
    """A reordered fold would make the deterministic formal run non-reproducible."""
    ledger = FitLedger()

    with pytest.raises(FitBudgetError, match="frozen order"):
        ledger.record(FitPhase.SELECTION, EXACT_TRIAL_IDS[0], "F2")

    assert ledger.total_count == 0


def test_fit_ledger_allows_at_most_four_replay_and_one_final_fit() -> None:
    """A fallback replay or second final fit must not exceed the formal ceiling."""
    ledger = FitLedger()
    for trial_id in EXACT_TRIAL_IDS:
        for fold_id in EXACT_FOLD_IDS:
            ledger.record(FitPhase.SELECTION, trial_id, fold_id)
    for fold_id in EXACT_FOLD_IDS:
        ledger.record(FitPhase.REPLAY, "REC-180-L4", fold_id)
    ledger.record(FitPhase.FINAL, "REC-180-L4", "FINAL")

    assert (ledger.selection_count, ledger.replay_count, ledger.final_count) == (80, 4, 1)
    with pytest.raises(FitBudgetError, match="maximum fits frozen at 85"):
        ledger.record(FitPhase.FINAL, "REC-180-L4", "FINAL")
