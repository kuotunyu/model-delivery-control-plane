from mdcp.temporal.constants import (
    BOOTSTRAP_INDEX,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    DOMAIN_END_LOCAL,
    DOMAIN_START_LOCAL,
    MAX_FORMAL_FITS,
    SUBGROUP_NAMES,
    TEMPORAL_FEATURE_COLUMNS,
    TEMPORAL_SCHEMA_ID,
    TIMEZONE_NAME,
)


def test_v02_constants_are_exact() -> None:
    assert TEMPORAL_SCHEMA_ID == "mdcp.temporal-features.v0.2"
    assert TIMEZONE_NAME == "America/New_York"
    assert DOMAIN_START_LOCAL.isoformat() == "2011-01-01T00:00:00"
    assert DOMAIN_END_LOCAL.isoformat() == "2013-01-01T00:00:00"
    assert TEMPORAL_FEATURE_COLUMNS == (
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
    assert SUBGROUP_NAMES == (
        "weather_clear",
        "weather_mist",
        "weather_adverse",
        "day_non_working",
        "day_working",
        "demand_peak",
        "demand_off_peak",
    )
    assert (BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, BOOTSTRAP_INDEX) == (2000, 2026, 1899)
    assert MAX_FORMAL_FITS == 85
