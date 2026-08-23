from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class PairedQualityRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(min_length=1, max_length=128)
    calendar_day: date
    stable_prediction: float = Field(ge=0, allow_inf_nan=False)
    candidate_prediction: float = Field(ge=0, allow_inf_nan=False)
    label: float = Field(ge=0, allow_inf_nan=False)
    groups: tuple[str, ...]


class RatioMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    row_count: int
    stable_mae: float
    candidate_mae: float
    point_ratio: float
    ucb95: float


class BootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    reason_code: str | None = None
    overall: RatioMetric | None = None
    subgroups: dict[str, RatioMetric] = Field(default_factory=dict)
    resamples: int
    seed: int
    replicate_index: int


def _invalid(reason_code: str, *, resamples: int, seed: int) -> BootstrapResult:
    return BootstrapResult(
        valid=False,
        reason_code=reason_code,
        resamples=resamples,
        seed=seed,
        replicate_index=math.ceil(0.95 * resamples) - 1,
    )


def cluster_bootstrap_ratios(
    rows: Sequence[PairedQualityRow],
    groups: Sequence[str],
    resamples: int = 2000,
    seed: int = 2026,
) -> BootstrapResult:
    """Apply the frozen paired calendar-day cluster bootstrap from spec section 13.5."""

    if resamples != 2000 or seed != 2026:
        raise ValueError("bootstrap resamples and seed are frozen at 2000 and 2026")
    if not rows:
        return _invalid("EMPTY_PAIRED_SET", resamples=resamples, seed=seed)
    request_ids = [row.request_id for row in rows]
    if len(request_ids) != len(set(request_ids)):
        return _invalid("DUPLICATE_REQUEST_ID", resamples=resamples, seed=seed)

    group_names = tuple(groups)
    if len(group_names) != len(set(group_names)) or any(not group for group in group_names):
        raise ValueError("bootstrap group names must be unique and non-empty")

    days = np.array(sorted({row.calendar_day for row in rows}), dtype=object)
    day_positions = {day: index for index, day in enumerate(days)}
    row_days = np.asarray([day_positions[row.calendar_day] for row in rows], dtype=np.int64)
    stable_errors = np.asarray(
        [abs(row.stable_prediction - row.label) for row in rows], dtype=np.float64
    )
    candidate_errors = np.asarray(
        [abs(row.candidate_prediction - row.label) for row in rows], dtype=np.float64
    )
    if not np.isfinite(stable_errors).all() or not np.isfinite(candidate_errors).all():
        return _invalid("NONFINITE_ERROR", resamples=resamples, seed=seed)

    rng = np.random.Generator(np.random.PCG64(seed))
    sampled_days = rng.integers(0, len(days), size=(resamples, len(days)))
    replicate_index = math.ceil(0.95 * resamples) - 1

    def metric(mask: np.ndarray, name: str) -> RatioMetric | BootstrapResult:
        row_count = int(mask.sum())
        if row_count == 0:
            return _invalid(f"EMPTY_SUBGROUP:{name}", resamples=resamples, seed=seed)
        stable_sum = float(stable_errors[mask].sum())
        candidate_sum = float(candidate_errors[mask].sum())
        if not math.isfinite(stable_sum) or stable_sum <= 0:
            return _invalid("NONPOSITIVE_STABLE_MAE", resamples=resamples, seed=seed)

        stable_by_day = np.bincount(
            row_days[mask], weights=stable_errors[mask], minlength=len(days)
        )
        candidate_by_day = np.bincount(
            row_days[mask], weights=candidate_errors[mask], minlength=len(days)
        )
        count_by_day = np.bincount(row_days[mask], minlength=len(days))
        sampled_count = count_by_day[sampled_days].sum(axis=1)
        sampled_stable = stable_by_day[sampled_days].sum(axis=1)
        sampled_candidate = candidate_by_day[sampled_days].sum(axis=1)
        if (sampled_count == 0).any():
            return _invalid(
                f"EMPTY_BOOTSTRAP_SUBGROUP:{name}", resamples=resamples, seed=seed
            )
        if (sampled_stable <= 0).any() or not np.isfinite(sampled_stable).all():
            return _invalid("NONPOSITIVE_STABLE_MAE", resamples=resamples, seed=seed)
        ratios = sampled_candidate / sampled_stable
        if not np.isfinite(ratios).all():
            return _invalid("NONFINITE_RATIO", resamples=resamples, seed=seed)
        return RatioMetric(
            row_count=row_count,
            stable_mae=stable_sum / row_count,
            candidate_mae=candidate_sum / row_count,
            point_ratio=candidate_sum / stable_sum,
            ucb95=float(np.sort(ratios)[replicate_index]),
        )

    overall = metric(np.ones(len(rows), dtype=bool), "overall")
    if isinstance(overall, BootstrapResult):
        return overall

    subgroup_metrics: dict[str, RatioMetric] = {}
    for group in group_names:
        mask = np.asarray([group in row.groups for row in rows], dtype=bool)
        result = metric(mask, group)
        if isinstance(result, BootstrapResult):
            return result
        subgroup_metrics[group] = result

    return BootstrapResult(
        valid=True,
        overall=overall,
        subgroups=subgroup_metrics,
        resamples=resamples,
        seed=seed,
        replicate_index=replicate_index,
    )
