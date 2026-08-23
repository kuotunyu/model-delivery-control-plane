from __future__ import annotations

from mdcp.common.enums import EvidenceClass
from mdcp.verify.bundle import VerificationResult


def test_offline_result_contract_separates_source_from_recomputed_evidence() -> None:
    fields = VerificationResult.model_fields

    assert "source_evidence_class" in fields
    assert "evidence_class" in fields
    assert "live_ghcr_verified" in fields
    assert "network_requests" in fields
    assert EvidenceClass.RELEASE_CI_VERIFIED != EvidenceClass.REVIEWER_LOCALLY_RECOMPUTED
