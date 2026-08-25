from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from mdcp.contracts.workload import BikeRequest
from mdcp.contracts.workload_v2 import BikeRequestV2
from mdcp.temporal.constants import (
    DOMAIN_END_LOCAL,
    DOMAIN_START_LOCAL,
    TEMPORAL_FEATURE_COLUMNS,
    TIMEZONE_NAME,
)

_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}")
_ELAPSED_ORIGIN = date(2011, 1, 1)


class TemporalReasonCode(StrEnum):
    MISSING_EVENT_TIMESTAMP = "MISSING_EVENT_TIMESTAMP"
    INVALID_EVENT_TIMESTAMP = "INVALID_EVENT_TIMESTAMP"
    EVENT_TIMESTAMP_OUT_OF_RANGE = "EVENT_TIMESTAMP_OUT_OF_RANGE"
    TEMPORAL_FIELD_MISMATCH = "TEMPORAL_FIELD_MISMATCH"


class TemporalContractError(ValueError):
    """A sanitized temporal-contract failure containing only a fixed reason code."""

    def __init__(self, reason_code: TemporalReasonCode) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code.value)


@dataclass(frozen=True)
class TemporalFeatureVector:
    names: tuple[str, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.names != TEMPORAL_FEATURE_COLUMNS or len(self.values) != len(self.names):
            raise ValueError("invalid temporal feature schema")
        if not all(math.isfinite(value) for value in self.values):
            raise ValueError("temporal feature values must be finite")


def _normalize_timestamp(raw: str) -> datetime:
    if not _TIMESTAMP_PATTERN.fullmatch(raw):
        raise TemporalContractError(TemporalReasonCode.INVALID_EVENT_TIMESTAMP)
    try:
        supplied = datetime.fromisoformat(raw)
        normalized = supplied.astimezone(ZoneInfo(TIMEZONE_NAME))
    except (OverflowError, ValueError):
        raise TemporalContractError(TemporalReasonCode.INVALID_EVENT_TIMESTAMP) from None

    if (
        normalized.replace(tzinfo=None) != supplied.replace(tzinfo=None)
        or normalized.utcoffset() != supplied.utcoffset()
    ):
        raise TemporalContractError(TemporalReasonCode.INVALID_EVENT_TIMESTAMP)
    if normalized.minute or normalized.second or normalized.microsecond:
        raise TemporalContractError(TemporalReasonCode.INVALID_EVENT_TIMESTAMP)
    return normalized


def adapt_local_v2(request: BikeRequest, local_civil: datetime) -> TemporalFeatureVector:
    """Apply the shared v0.2 feature contract to one trusted local civil hour."""
    if (
        type(local_civil) is not datetime
        or local_civil.tzinfo is not None
        or local_civil.minute
        or local_civil.second
        or local_civil.microsecond
    ):
        raise TemporalContractError(TemporalReasonCode.INVALID_EVENT_TIMESTAMP)
    if not DOMAIN_START_LOCAL <= local_civil < DOMAIN_END_LOCAL:
        raise TemporalContractError(TemporalReasonCode.EVENT_TIMESTAMP_OUT_OF_RANGE)

    sunday_zero_weekday = (local_civil.weekday() + 1) % 7
    if (local_civil.month, local_civil.hour, sunday_zero_weekday) != (
        request.mnth,
        request.hr,
        request.weekday,
    ):
        raise TemporalContractError(TemporalReasonCode.TEMPORAL_FIELD_MISMATCH)

    elapsed_days = (local_civil.date() - _ELAPSED_ORIGIN).days + request.hr / 24
    legacy_values = request.model_dump(mode="python")
    values = (
        *(float(legacy_values[name]) for name in TEMPORAL_FEATURE_COLUMNS[:11]),
        float(elapsed_days),
        math.sin(2 * math.pi * request.hr / 24),
        math.cos(2 * math.pi * request.hr / 24),
        math.sin(2 * math.pi * request.weekday / 7),
        math.cos(2 * math.pi * request.weekday / 7),
        math.sin(2 * math.pi * elapsed_days / 365.2425),
        math.cos(2 * math.pi * elapsed_days / 365.2425),
    )
    return TemporalFeatureVector(names=TEMPORAL_FEATURE_COLUMNS, values=values)


def adapt_v2(request: BikeRequestV2) -> TemporalFeatureVector:
    local = _normalize_timestamp(request.event_timestamp)
    return adapt_local_v2(request.to_legacy(), local.replace(tzinfo=None))
