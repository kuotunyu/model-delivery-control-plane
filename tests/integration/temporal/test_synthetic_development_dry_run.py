from __future__ import annotations

from datetime import date

import pandas as pd

from mdcp.common.enums import GateVerdict
from mdcp.temporal.completeness import (
    AdapterOutcome,
    LabelOutcome,
    PredictionOutcome,
    assemble_development_pairs,
)
from mdcp.temporal.evaluation import (
    FoldQualificationContext,
    QualificationContext,
    QualificationEvidence,
    evaluate_pooled,
    qualify_trial,
)
from mdcp.temporal.folds import FoldSpec, materialize_folds
from mdcp.temporal.selection import (
    ReplayFoldDigests,
    ReplayResult,
    ReplaySelectionSession,
    finalize_selection,
    rank_qualified,
)

FINAL_TRIAL_FAMILIES = {
    "REC-180-L4": "REC",
    "REC-180-L12": "REC",
    "REC-270-L4": "REC",
    "REC-270-L12": "REC",
    "REC-365-L4": "REC",
    "REC-365-L12": "REC",
    "STAT-A0.1": "STAT",
    "STAT-A1": "STAT",
    "STAT-A10": "STAT",
    "STAT-A100": "STAT",
    "STAT-A1000": "STAT",
    "NL-E64-R0.03-D2": "NL",
    "NL-E64-R0.03-D3": "NL",
    "NL-E64-R0.07-D2": "NL",
    "NL-E64-R0.07-D3": "NL",
    "NL-E128-R0.03-D2": "NL",
    "NL-E128-R0.03-D3": "NL",
    "NL-E128-R0.07-D2": "NL",
    "NL-E128-R0.07-D3": "NL",
}


FOLD_SPECS = (
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
        pd.Timestamp("2012-01-01"),
        pd.Timestamp("2012-01-01"),
        pd.Timestamp("2012-04-01"),
    ),
    FoldSpec(
        "F4",
        pd.Timestamp("2011-01-01"),
        pd.Timestamp("2012-04-01"),
        pd.Timestamp("2012-04-01"),
        pd.Timestamp("2012-07-01"),
    ),
)


def _generated_source() -> pd.DataFrame:
    timestamps = list(pd.date_range("2011-01-01", periods=24, freq="h"))
    for start in ("2011-07-01", "2011-10-01", "2012-01-01", "2012-04-01"):
        timestamps.extend(pd.date_range(start, periods=300, freq="h"))
    frame = pd.DataFrame(
        {"request_id": [f"synthetic-{position:04d}" for position in range(len(timestamps))]},
        index=pd.DatetimeIndex(timestamps, name="event_timestamp"),
    )
    frame.attrs = {
        "evidence_class": "synthetic_test",
        "source_kind": "deterministic_generated",
        "uci_rows": 0,
    }
    return frame


def _fold_context(fold) -> tuple[FoldQualificationContext, object]:
    adapters = []
    stable = []
    candidate = []
    labels = []
    weather = ("weather_clear", "weather_mist", "weather_adverse")
    for position, identity in enumerate(fold.inventory):
        local_day = date.fromisoformat(identity.local_timestamp[:10])
        groups = (
            weather[position % 3],
            "day_non_working" if position % 2 == 0 else "day_working",
            "demand_off_peak" if position % 2 == 0 else "demand_peak",
        )
        adapters.append(
            AdapterOutcome(identity=identity, succeeded=True, calendar_day=local_day, groups=groups)
        )
        stable.append(PredictionOutcome(identity=identity, succeeded=True, value=10.0))
        candidate.append(PredictionOutcome(identity=identity, succeeded=True, value=9.0))
        labels.append(LabelOutcome(identity=identity, succeeded=True, value=0.0))
    receipt, pairs = assemble_development_pairs(fold.inventory, adapters, stable, candidate, labels)
    return (
        FoldQualificationContext(
            fold_id=fold.spec.fold_id,
            inventory=fold.inventory,
            paired_rows=pairs,
        ),
        receipt,
    )


def test_generated_four_fold_dry_run_reaches_sole_replay_selection_without_formal_fits() -> None:
    source = _generated_source()
    folds = materialize_folds(source, FOLD_SPECS)
    contexts_and_receipts = tuple(_fold_context(fold) for fold in folds)
    context = QualificationContext(folds=tuple(item[0] for item in contexts_and_receipts))
    completeness = {
        fold.spec.fold_id: item[1] for fold, item in zip(folds, contexts_and_receipts, strict=True)
    }
    report = evaluate_pooled(
        context,
        completeness,
        QualificationEvidence(
            lineage=GateVerdict.PASS,
            converter=GateVerdict.PASS,
            evidence=GateVerdict.PASS,
            budget=GateVerdict.PASS,
        ),
    )
    qualifications = tuple(
        qualify_trial(report, context, trial_id=trial_id, family_id=family_id)
        for trial_id, family_id in FINAL_TRIAL_FAMILIES.items()
    )
    provisional = rank_qualified(qualifications)
    assert provisional is not None
    fold_digests = tuple(
        ReplayFoldDigests(
            fold_id=fold.spec.fold_id,
            verdict=GateVerdict.PASS,
            configuration_sha256="a" * 64,
            preprocessing_state_sha256="b" * 64,
            feature_vector_sha256="c" * 64,
            prediction_vector_sha256="d" * 64,
            metric_sha256="e" * 64,
            receipt_sha256="f" * 64,
        )
        for fold in folds
    )
    session = ReplaySelectionSession(qualifications, fold_digests)
    decision = finalize_selection(
        session,
        provisional,
        ReplayResult(
            trial_id=provisional.trial_id,
            family_id=provisional.family_id,
            ranking_key=provisional.ranking_key,
            qualification_inventory_sha256=provisional.qualification_inventory_sha256,
            session_sha256=session.session_sha256,
            verdict=GateVerdict.PASS,
            digests=fold_digests,
        ),
    )
    synthetic_receipt = {
        "evidence_class": source.attrs["evidence_class"],
        "source_kind": source.attrs["source_kind"],
        "uci_rows": source.attrs["uci_rows"],
        "fold_count": len(folds),
        "formal_fit_count": 0,
        "synthetic_fits_excluded_from_formal_ledger": True,
        "selection_status": decision.status,
    }

    assert [fold.spec.fold_id for fold in folds] == ["F1", "F2", "F3", "F4"]
    assert [len(fold.inventory) for fold in folds] == [300, 300, 300, 300]
    assert report.pooled_row_count == 1_200
    assert all(result.qualified for result in qualifications)
    assert decision.status == "PASS"
    assert decision.final_winner is not None
    assert synthetic_receipt == {
        "evidence_class": "synthetic_test",
        "source_kind": "deterministic_generated",
        "uci_rows": 0,
        "fold_count": 4,
        "formal_fit_count": 0,
        "synthetic_fits_excluded_from_formal_ledger": True,
        "selection_status": "PASS",
    }
