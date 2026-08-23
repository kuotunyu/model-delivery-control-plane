from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from mdcp.common.enums import EvidenceClass, GateVerdict
from mdcp.policy.cluster_bootstrap import (
    BootstrapResult,
    PairedQualityRow,
    cluster_bootstrap_ratios,
)


class QualityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.quality-policy.v1"]
    overall_max_ratio: float = Field(gt=0)
    subgroup_max_ratio: float = Field(gt=0)
    minimum_subgroup_rows: int = Field(ge=100)
    resamples: Literal[2000]
    seed: Literal[2026]
    subgroup_names: tuple[str, ...]


class H1EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.h1-evaluation.v1"] = "mdcp.h1-evaluation.v1"
    verdict: GateVerdict
    evidence_class: EvidenceClass
    reason_codes: tuple[str, ...]
    paired_row_count: int
    bootstrap: BootstrapResult


def paired_rows_from_frame(
    frame: pd.DataFrame,
    stable_predictions: Sequence[float],
    candidate_predictions: Sequence[float],
) -> tuple[PairedQualityRow, ...]:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("H1 evaluator requires a DatetimeIndex")
    if len(frame) != len(stable_predictions) or len(frame) != len(candidate_predictions):
        raise ValueError("paired prediction lengths differ")
    required = {"weathersit", "workingday", "hr", "cnt"}
    if not required.issubset(frame.columns):
        raise ValueError("H1 evaluator columns are missing")

    rows: list[PairedQualityRow] = []
    for position, ((timestamp, values), stable, candidate) in enumerate(
        zip(frame.iterrows(), stable_predictions, candidate_predictions, strict=True)
    ):
        weather = int(values["weathersit"])
        groups = [
            "weather_clear"
            if weather == 1
            else "weather_mist"
            if weather == 2
            else "weather_adverse",
            "day_working" if int(values["workingday"]) == 1 else "day_non_working",
            "demand_peak"
            if int(values["hr"]) in {7, 8, 9, 16, 17, 18}
            else "demand_off_peak",
        ]
        rows.append(
            PairedQualityRow(
                request_id=f"h1-{position:06d}",
                calendar_day=timestamp.date(),
                stable_prediction=float(stable),
                candidate_prediction=float(candidate),
                label=float(values["cnt"]),
                groups=tuple(groups),
            )
        )
    return tuple(rows)


def evaluate_h1(
    rows: Sequence[PairedQualityRow],
    policy: QualityPolicy,
    *,
    evidence_class: EvidenceClass = EvidenceClass.MEASURED_WORKLOAD,
) -> H1EvaluationReport:
    counts = {
        group: sum(group in row.groups for row in rows) for group in policy.subgroup_names
    }
    insufficient = tuple(
        f"INSUFFICIENT_SUBGROUP_ROWS:{group}"
        for group in policy.subgroup_names
        if counts[group] < policy.minimum_subgroup_rows
    )
    if insufficient:
        bootstrap = BootstrapResult(
            valid=False,
            reason_code="INSUFFICIENT_SUBGROUP_ROWS",
            resamples=policy.resamples,
            seed=policy.seed,
            replicate_index=1899,
        )
        return H1EvaluationReport(
            verdict=GateVerdict.UNKNOWN,
            evidence_class=evidence_class,
            reason_codes=insufficient,
            paired_row_count=len(rows),
            bootstrap=bootstrap,
        )

    bootstrap = cluster_bootstrap_ratios(
        rows,
        policy.subgroup_names,
        policy.resamples,
        policy.seed,
    )
    if not bootstrap.valid or bootstrap.overall is None:
        return H1EvaluationReport(
            verdict=GateVerdict.UNKNOWN,
            evidence_class=evidence_class,
            reason_codes=(bootstrap.reason_code or "INVALID_BOOTSTRAP",),
            paired_row_count=len(rows),
            bootstrap=bootstrap,
        )

    reasons: list[str] = []
    if bootstrap.overall.point_ratio > policy.overall_max_ratio:
        reasons.append("OVERALL_RATIO")
    if bootstrap.overall.ucb95 > policy.overall_max_ratio:
        reasons.append("OVERALL_UCB95")
    for group, metric in bootstrap.subgroups.items():
        if metric.point_ratio > policy.subgroup_max_ratio:
            reasons.append(f"SUBGROUP_RATIO:{group}")
        if metric.ucb95 > policy.subgroup_max_ratio:
            reasons.append(f"SUBGROUP_UCB95:{group}")

    return H1EvaluationReport(
        verdict=GateVerdict.FAIL if reasons else GateVerdict.PASS,
        evidence_class=evidence_class,
        reason_codes=tuple(reasons),
        paired_row_count=len(rows),
        bootstrap=bootstrap,
    )
