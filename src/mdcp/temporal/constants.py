"""Immutable constants for the MDCP v0.2 temporal protocol."""

from datetime import datetime

TEMPORAL_SCHEMA_ID = "mdcp.temporal-features.v0.2"
TIMEZONE_NAME = "America/New_York"
DOMAIN_START_LOCAL = datetime(2011, 1, 1)
DOMAIN_END_LOCAL = datetime(2013, 1, 1)
TEMPORAL_FEATURE_COLUMNS = (
    "season",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
    "elapsed_days",
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "annual_sin",
    "annual_cos",
)
SUBGROUP_NAMES = (
    "weather_clear",
    "weather_mist",
    "weather_adverse",
    "day_non_working",
    "day_working",
    "demand_peak",
    "demand_off_peak",
)
BOOTSTRAP_RESAMPLES = 2_000
BOOTSTRAP_SEED = 2026
BOOTSTRAP_INDEX = 1_899
MAX_FORMAL_FITS = 85
