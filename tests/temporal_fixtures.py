"""Deterministic generated rows for temporal protocol tests only."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from mdcp.temporal.constants import DOMAIN_START_LOCAL, TEMPORAL_FEATURE_COLUMNS, TIMEZONE_NAME

SYNTHETIC_END_LOCAL = datetime(2012, 7, 1)
SYNTHETIC_EVIDENCE_ATTRS = {
    "evidence_class": "synthetic_test",
    "source_kind": "deterministic_generated",
    "uci_rows": 0,
}


def _bounded(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 8)


def _row_values(local: datetime) -> dict[str, int | float]:
    day_of_year = local.timetuple().tm_yday
    weekday = (local.weekday() + 1) % 7
    holiday = int(day_of_year % 97 == 0)
    workingday = int(weekday not in (0, 6) and holiday == 0)
    annual_phase = 2 * math.pi * (day_of_year - 1) / 365.2425
    daily_phase = 2 * math.pi * local.hour / 24
    temp = _bounded(0.5 + 0.3 * math.sin(annual_phase) + 0.08 * math.sin(daily_phase))
    atemp = _bounded(0.05 + 0.9 * temp)
    hum = _bounded(0.55 + 0.25 * math.cos(annual_phase) - 0.1 * math.sin(daily_phase))
    windspeed = _bounded(((day_of_year * 7 + local.hour * 17) % 101) / 100)
    weathersit = (day_of_year + local.hour) % 4 + 1
    cnt = max(
        0,
        round(35 + 45 * temp + 12 * workingday + 18 * math.sin(daily_phase) - 6 * (weathersit - 1)),
    )
    return {
        "season": (local.month % 12) // 3 + 1,
        "mnth": local.month,
        "hr": local.hour,
        "holiday": holiday,
        "weekday": weekday,
        "workingday": workingday,
        "weathersit": weathersit,
        "temp": temp,
        "atemp": atemp,
        "hum": hum,
        "windspeed": windspeed,
        "cnt": cnt,
    }


def synthetic_development_frame() -> pd.DataFrame:
    """Return arithmetic-only hourly rows that end before the H2 boundary."""
    hour_count = int((SYNTHETIC_END_LOCAL - DOMAIN_START_LOCAL).total_seconds() // 3_600)
    timestamps = [DOMAIN_START_LOCAL + timedelta(hours=offset) for offset in range(hour_count)]
    rows = pd.DataFrame((_row_values(timestamp) for timestamp in timestamps), index=timestamps)
    rows.index = pd.DatetimeIndex(rows.index, name="event_timestamp")
    rows = rows.loc[:, (*TEMPORAL_FEATURE_COLUMNS[:11], "cnt")]
    rows.attrs = SYNTHETIC_EVIDENCE_ATTRS.copy()
    return rows


def _localize_new_york(local: datetime) -> datetime:
    zone = ZoneInfo(TIMEZONE_NAME)
    valid: dict[datetime, datetime] = {}

    for fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=fold)
        round_tripped = candidate.astimezone(UTC).astimezone(zone)
        if round_tripped.replace(tzinfo=None) == local and round_tripped.fold == fold:
            valid[candidate.astimezone(UTC)] = candidate

    if len(valid) != 1:
        raise ValueError("synthetic timestamp is nonexistent or ambiguous in America/New_York")
    return next(iter(valid.values()))


def synthetic_v2_payload(timestamp: datetime, request_id: str) -> dict[str, object]:
    """Build one deterministic v2 envelope without a target or external lookup."""
    if timestamp.tzinfo is not None:
        raise ValueError("synthetic timestamp must be naive local civil time")
    if timestamp.minute or timestamp.second or timestamp.microsecond:
        raise ValueError("synthetic timestamp must be aligned to an hour")
    if not DOMAIN_START_LOCAL <= timestamp < SYNTHETIC_END_LOCAL:
        raise ValueError("synthetic timestamp is outside the development interval")
    if not request_id:
        raise ValueError("request_id must not be empty")

    values = _row_values(timestamp)
    values.pop("cnt")
    localized = _localize_new_york(timestamp)
    return {
        "schema_version": "mdcp.bike-request.v2",
        "request_id": request_id,
        "event_timestamp": localized.isoformat(timespec="seconds"),
        **values,
    }
