from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from pydantic import ValidationError

from mdcp.contracts.workload import BikeRequest
from mdcp.contracts.workload_v2 import BikeRequestV2
from mdcp.temporal.adapter import TemporalContractError, TemporalFeatureVector, adapt_v2


class AdmissionKind(StrEnum):
    LEGACY_STABLE_ONLY = "LEGACY_STABLE_ONLY"
    V2_CANDIDATE_ELIGIBLE = "V2_CANDIDATE_ELIGIBLE"
    INVALID_V2 = "INVALID_V2"


@dataclass(frozen=True)
class AdmissionDecision:
    kind: AdmissionKind
    legacy_request: BikeRequest | None = None
    v2_request: BikeRequestV2 | None = None
    feature_vector: TemporalFeatureVector | None = None
    reason_code: str | None = None


def classify_envelope(payload: Mapping[str, object]) -> AdmissionDecision:
    v2_declared = "schema_version" in payload or "event_timestamp" in payload
    if not v2_declared:
        return AdmissionDecision(
            kind=AdmissionKind.LEGACY_STABLE_ONLY,
            legacy_request=BikeRequest.model_validate(payload),
        )

    if "event_timestamp" not in payload:
        return AdmissionDecision(
            kind=AdmissionKind.INVALID_V2,
            reason_code="MISSING_EVENT_TIMESTAMP",
        )
    try:
        request = BikeRequestV2.model_validate(payload)
    except ValidationError:
        return AdmissionDecision(
            kind=AdmissionKind.INVALID_V2,
            reason_code="INVALID_V2_ENVELOPE",
        )
    try:
        vector = adapt_v2(request)
    except TemporalContractError as error:
        return AdmissionDecision(
            kind=AdmissionKind.INVALID_V2,
            reason_code=error.reason_code.value,
        )
    return AdmissionDecision(
        kind=AdmissionKind.V2_CANDIDATE_ELIGIBLE,
        v2_request=request,
        feature_vector=vector,
    )
