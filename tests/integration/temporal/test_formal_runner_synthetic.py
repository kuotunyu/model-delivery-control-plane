from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from mdcp.temporal.runner import (
    EXACT_FOLD_IDS,
    EXACT_TRIAL_IDS,
    ExecutionConfigurationError,
    FoldFitResult,
    FormalRunContext,
    run_selection,
)


def _synthetic_result(trial_id: str, fold_id: str, *, quality: str = "PASS") -> FoldFitResult:
    token = f"synthetic:{trial_id}:{fold_id}"
    return FoldFitResult(
        fold_id=fold_id,
        train_identity_digests=(f"{token}:train",),
        validation_identity_digests=(f"{token}:validation",),
        preprocessing_state_sha256="a" * 64,
        feature_vector_sha256="b" * 64,
        stable_prediction_digest="c" * 64,
        candidate_prediction_digest="d" * 64,
        completeness_verdict="PASS",
        quality_verdict=quality,
        metric_values={"candidate_mae": 1.0},
        receipt_sha256="e" * 64,
    )


def _context(tmp_path: Path, *, peak_bytes: int | None = 1024) -> FormalRunContext:
    outside_repository = tmp_path.parent / "private-output"
    return FormalRunContext(
        repository_root=tmp_path,
        output_root=outside_repository,
        fit_fold=lambda trial_id, fold_id: _synthetic_result(trial_id, fold_id),
        process_memory_probe=lambda: peak_bytes,
        repository_is_clean=lambda _root: True,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )


def test_runner_completes_all_folds_for_a_bad_quality_trial(tmp_path: Path) -> None:
    """An early quality failure must not silently skip the trial's remaining folds."""
    context = _context(tmp_path)
    context = replace(
        context,
        fit_fold=lambda trial_id, fold_id: _synthetic_result(
            trial_id,
            fold_id,
            quality="FAIL" if trial_id == EXACT_TRIAL_IDS[0] and fold_id == "F1" else "PASS",
        ),
    )

    receipt = run_selection(context)

    assert receipt.status == "NO_ELIGIBLE_CANDIDATE"
    assert receipt.fit_ledger.selection_count == 80
    assert [trial.trial_id for trial in receipt.trials] == list(EXACT_TRIAL_IDS)
    assert all(
        [fold.fold_id for fold in trial.fold_receipts] == list(EXACT_FOLD_IDS)
        for trial in receipt.trials
    )
    assert receipt.trials[0].quality_verdict == "FAIL"


@pytest.mark.parametrize("peak_bytes", [None, 4_294_967_297])
def test_budget_probe_failure_is_terminal_unknown(tmp_path: Path, peak_bytes: int | None) -> None:
    """An unavailable or oversized authoritative probe forbids a replacement run."""
    receipt = run_selection(_context(tmp_path, peak_bytes=peak_bytes))

    assert receipt.status == "UNKNOWN/COMPUTE_BUDGET_EXCEEDED"
    assert receipt.retry_allowed is False
    assert receipt.reason_codes == ("COMPUTE_BUDGET_EXCEEDED",)
    assert receipt.fit_ledger.total_count == 1


def test_public_receipt_separates_private_prediction_and_row_identity_material(
    tmp_path: Path,
) -> None:
    """Changing private values must not expose them in the public development receipt."""
    receipt = run_selection(_context(tmp_path))

    public_document = receipt.public_document()
    assert receipt.fit_ledger.selection_count == 80
    assert "train_identity_digests" not in repr(public_document)
    assert "stable_prediction_digest" not in repr(public_document)
    assert "candidate_prediction_digest" not in repr(public_document)
    assert public_document["selection_fit_count"] == 80


def test_runner_rejects_gpu_and_network_execution_configuration(tmp_path: Path) -> None:
    """A CUDA provider or network mode could invalidate the CPU-isolated execution contract."""
    context = _context(tmp_path)

    with pytest.raises(ExecutionConfigurationError, match="GPU providers are forbidden"):
        run_selection(replace(context, execution_providers=("CUDAExecutionProvider",)))
    with pytest.raises(
        ExecutionConfigurationError,
        match="network/socket configuration is forbidden",
    ):
        run_selection(replace(context, network_mode="bridge"))
