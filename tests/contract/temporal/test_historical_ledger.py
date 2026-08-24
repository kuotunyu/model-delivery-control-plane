from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict

import pytest

from mdcp.temporal.evidence import HistoricalLedger


def test_historical_ledger_cannot_rewrite_failures() -> None:
    ledger = HistoricalLedger.frozen_v02()

    assert ledger.v1_h1_verdict == "FAIL"
    assert ledger.v1_overall_point_ratio == 0.9941709085547193
    assert ledger.v1_overall_ucb95 == 1.0132761747618493
    assert ledger.v1_off_peak_ucb95 == 1.0514487756867108
    assert ledger.v1_reason_codes == (
        "OVERALL_RATIO",
        "OVERALL_UCB95",
        "SUBGROUP_UCB95:demand_off_peak",
    )
    assert ledger.candidate_v2_verdict == "NO_ELIGIBLE_CANDIDATE"
    assert ledger.candidate_v2_overall_point_ratio == 1.024486
    assert ledger.candidate_v2_overall_ucb95 == 1.049456
    assert ledger.h1_role == "OBSERVED_DEVELOPMENT_ONLY"
    assert ledger.h1_globally_blind is False
    assert ledger.h2_status == "SEALED_NOT_LOADED"
    assert ledger.h2_loaded_rows == 0

    with pytest.raises(FrozenInstanceError):
        ledger.v1_h1_verdict = "PASS"  # type: ignore[misc]


def test_historical_ledger_binds_only_public_safe_preservation_identity() -> None:
    ledger = HistoricalLedger.frozen_v02()
    document = asdict(ledger)

    assert ledger.preserved_evidence_class == "natural_rejection_evidence"
    assert ledger.preserved_payload_file_count == 22_236
    assert ledger.preserved_payload_total_bytes == 585_295_509
    assert (
        ledger.preserved_payload_inventory_sha256
        == "fc39f69fe0fcf7ac49f60348ce3198ba04199026269eb45ec26b49865775a30f"
    )
    assert (
        ledger.preservation_receipt_sha256
        == "bca375202663af8245f8f27496ea44e7c5cf9f7ea0aa1e76176d23deef01cc9a"
    )
    assert (
        ledger.final_sha256sums_sha256
        == "ea26df010ba2e73aed88ed462b3843a0084356010465a055e04a5c87c70a5fad"
    )
    assert ledger.source_destination_byte_equivalence == "PASS"
    assert all("path" not in key for key in document)
    assert len(ledger.content_digest()) == 64
    assert ledger.content_digest() == HistoricalLedger.frozen_v02().content_digest()
