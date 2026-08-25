from __future__ import annotations

from dataclasses import replace

import pytest

from mdcp.common.enums import GateVerdict
from mdcp.temporal.evaluation import QualificationResult
from mdcp.temporal.selection import (
    ReplayFoldDigests,
    ReplayResult,
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


def _result(
    trial_id: str,
    *,
    family_id: str | None = None,
    verdict: GateVerdict = GateVerdict.PASS,
    qualified: bool = True,
    pooled_ucb95: float | None = 0.90,
    worst_fold_point: float | None = 0.90,
    worst_subgroup_ucb95: float | None = 0.90,
) -> QualificationResult:
    return QualificationResult(
        trial_id=trial_id,
        family_id=family_id or FINAL_TRIAL_FAMILIES[trial_id],
        verdict=verdict,
        qualified=qualified,
        reason_codes=() if verdict is GateVerdict.PASS else ("NOT_QUALIFIED",),
        pooled_ucb95=pooled_ucb95,
        worst_fold_point=worst_fold_point,
        worst_subgroup_ucb95=worst_subgroup_ucb95,
    )


def _inventory(
    replacements: dict[str, QualificationResult] | None = None,
) -> tuple[QualificationResult, ...]:
    replacements = replacements or {}
    return tuple(replacements.get(trial_id, _result(trial_id)) for trial_id in FINAL_TRIAL_FAMILIES)


def _digests(verdict: GateVerdict = GateVerdict.PASS) -> tuple[ReplayFoldDigests, ...]:
    fields = ("a", "b", "c", "d", "e", "f")
    return tuple(
        ReplayFoldDigests(
            fold_id=fold_id,
            verdict=verdict,
            configuration_sha256=fields[0] * 64,
            preprocessing_state_sha256=fields[1] * 64,
            feature_vector_sha256=fields[2] * 64,
            prediction_vector_sha256=fields[3] * 64,
            metric_sha256=fields[4] * 64,
            receipt_sha256=fields[5] * 64,
        )
        for fold_id in ("F1", "F2", "F3", "F4")
    )


def _replay(provisional, *, verdict: GateVerdict = GateVerdict.PASS, digests=None):
    return ReplayResult(
        trial_id=provisional.trial_id,
        family_id=provisional.family_id,
        ranking_key=provisional.ranking_key,
        verdict=verdict,
        digests=_digests() if digests is None else digests,
    )


def test_ranking_uses_exact_lexicographic_key() -> None:
    replacements = {
        "STAT-A10": _result(
            "STAT-A10",
            pooled_ucb95=0.80,
            worst_fold_point=0.84,
            worst_subgroup_ucb95=0.88,
        ),
        "REC-180-L4": _result(
            "REC-180-L4",
            pooled_ucb95=0.80,
            worst_fold_point=0.83,
            worst_subgroup_ucb95=0.89,
        ),
        "NL-E64-R0.03-D2": _result(
            "NL-E64-R0.03-D2",
            pooled_ucb95=0.80,
            worst_fold_point=0.83,
            worst_subgroup_ucb95=0.87,
        ),
    }

    provisional = rank_qualified(tuple(reversed(_inventory(replacements))))

    assert provisional is not None
    assert provisional.trial_id == "NL-E64-R0.03-D2"
    assert provisional.ranking_key == (
        0.80,
        0.83,
        0.87,
        2,
        "NL-E64-R0.03-D2",
    )


def test_exact_tie_uses_stat_then_ascii_trial_id() -> None:
    provisional = rank_qualified(_inventory())

    assert provisional is not None
    assert provisional.trial_id == "STAT-A0.1"
    assert provisional.family_id == "STAT"


def test_only_pass_and_qualified_results_are_ranked() -> None:
    excluded = _result(
        "STAT-A0.1",
        verdict=GateVerdict.FAIL,
        qualified=False,
        pooled_ucb95=0.01,
        worst_fold_point=0.01,
        worst_subgroup_ucb95=0.01,
    )

    provisional = rank_qualified(_inventory({"STAT-A0.1": excluded}))

    assert provisional is not None
    assert provisional.trial_id == "STAT-A1"


def test_no_qualified_trial_is_terminal_without_a_winner() -> None:
    results = tuple(
        _result(
            trial_id,
            verdict=GateVerdict.FAIL,
            qualified=False,
            pooled_ucb95=1.01,
            worst_fold_point=1.01,
            worst_subgroup_ucb95=1.01,
        )
        for trial_id in FINAL_TRIAL_FAMILIES
    )

    assert rank_qualified(results) is None
    decision = finalize_selection(None, None)
    assert decision.status == "NO_ELIGIBLE_CANDIDATE"
    assert decision.final_winner is None
    assert decision.retry_allowed is False


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate", "control"])
def test_ranking_rejects_noncanonical_final_eligible_inventory(mutation: str) -> None:
    results = list(_inventory())
    if mutation == "missing":
        results.pop()
    elif mutation == "extra":
        results.append(replace(results[-1], trial_id="UNKNOWN-01"))
    elif mutation == "duplicate":
        results[-1] = results[0]
    elif mutation == "control":
        results[-1] = QualificationResult(
            trial_id="CTRL-01",
            family_id="CTRL",
            verdict=GateVerdict.PASS,
            qualified=True,
            reason_codes=(),
            pooled_ucb95=0.80,
            worst_fold_point=0.80,
            worst_subgroup_ucb95=0.80,
        )

    with pytest.raises(ValueError, match="qualification inventory"):
        rank_qualified(tuple(results))


def test_ranking_rejects_family_mismatch() -> None:
    changed = replace(_result("STAT-A0.1"), family_id="REC")

    with pytest.raises(ValueError, match="qualification inventory"):
        rank_qualified(_inventory({"STAT-A0.1": changed}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pooled_ucb95", True),
        ("pooled_ucb95", 1),
        ("pooled_ucb95", float("nan")),
        ("worst_fold_point", float("inf")),
        ("worst_subgroup_ucb95", -0.01),
        ("qualified", 1),
        ("verdict", "PASS"),
        ("reason_codes", []),
    ],
)
def test_ranking_rejects_type_confusion_or_invalid_numbers(field: str, value: object) -> None:
    changed = replace(_result("STAT-A0.1"), **{field: value})

    with pytest.raises(ValueError, match="qualification result"):
        rank_qualified(_inventory({"STAT-A0.1": changed}))


@pytest.mark.parametrize(
    ("verdict", "qualified"),
    [(GateVerdict.FAIL, True), (GateVerdict.UNKNOWN, True), (GateVerdict.PASS, False)],
)
def test_qualified_flag_and_verdict_cannot_disagree(verdict: GateVerdict, qualified: bool) -> None:
    changed = _result("STAT-A0.1", verdict=verdict, qualified=qualified)

    with pytest.raises(ValueError, match="qualification result"):
        rank_qualified(_inventory({"STAT-A0.1": changed}))


def test_unhashable_trial_id_fails_closed_as_invalid_result() -> None:
    changed = replace(_result("STAT-A0.1"), trial_id=[])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="qualification result"):
        rank_qualified(_inventory({"STAT-A0.1": changed}))


@pytest.mark.parametrize("mutation", ["missing_reason", "partial_metrics"])
def test_nonpass_result_has_complete_reason_and_metric_shape(mutation: str) -> None:
    changed = _result(
        "STAT-A0.1",
        verdict=GateVerdict.UNKNOWN,
        qualified=False,
        pooled_ucb95=None,
        worst_fold_point=None,
        worst_subgroup_ucb95=None,
    )
    if mutation == "missing_reason":
        changed = replace(changed, reason_codes=())
    elif mutation == "partial_metrics":
        changed = replace(changed, pooled_ucb95=0.90)

    with pytest.raises(ValueError, match="qualification result"):
        rank_qualified(_inventory({"STAT-A0.1": changed}))


def test_pass_replay_promotes_the_sole_provisional_winner() -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None

    decision = finalize_selection(provisional, _replay(provisional))

    assert decision.status == "PASS"
    assert decision.final_winner == provisional
    assert decision.retry_allowed is False


@pytest.mark.parametrize("verdict", [GateVerdict.FAIL, GateVerdict.UNKNOWN])
def test_replay_failure_has_no_rank_two_fallback(verdict: GateVerdict) -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None

    decision = finalize_selection(provisional, _replay(provisional, verdict=verdict))

    assert decision.status == "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
    assert decision.final_winner is None
    assert decision.retry_allowed is False


@pytest.mark.parametrize("mutation", ["different_id", "different_family", "altered_key"])
def test_replay_must_bind_the_same_sole_ranked_trial(mutation: str) -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None
    replay = _replay(provisional)
    if mutation == "different_id":
        replay = replace(replay, trial_id="STAT-A1")
    elif mutation == "different_family":
        replay = replace(replay, family_id="REC")
    elif mutation == "altered_key":
        replay = replace(replay, ranking_key=(0.01, *replay.ranking_key[1:]))

    with pytest.raises(ValueError, match="replay identity"):
        finalize_selection(provisional, replay)


def test_replay_ranking_key_rejects_bool_for_family_rank() -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None
    replay = _replay(provisional)
    confused_key = (*replay.ranking_key[:3], False, replay.ranking_key[4])

    with pytest.raises(ValueError, match="replay identity"):
        finalize_selection(provisional, replace(replay, ranking_key=confused_key))


def test_unhashable_replay_trial_id_fails_closed_as_invalid_identity() -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None

    with pytest.raises(ValueError, match="replay identity"):
        finalize_selection(
            provisional,
            replace(_replay(provisional), trial_id=[]),  # type: ignore[arg-type]
        )


def test_forged_provisional_inventory_digest_cannot_be_promoted() -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None
    forged = replace(provisional, qualification_inventory_sha256="A" * 64)

    with pytest.raises(ValueError, match="provisional winner"):
        finalize_selection(forged, _replay(forged))


def test_forged_provisional_numeric_bool_cannot_equal_a_float_key() -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None
    forged_key = (*provisional.ranking_key[:2], 0.0, *provisional.ranking_key[3:])
    forged = replace(provisional, worst_subgroup_ucb95=False, ranking_key=forged_key)

    with pytest.raises(ValueError, match="provisional winner"):
        finalize_selection(forged, _replay(forged))


def test_replay_rejects_a_list_or_second_result() -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None
    replay = _replay(provisional)

    with pytest.raises(ValueError, match="one replay"):
        finalize_selection(provisional, [replay, replay])  # type: ignore[arg-type]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "uppercase", "short"])
def test_replay_requires_exact_four_fold_lowercase_digest_inventory(mutation: str) -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None
    digests = list(_digests())
    if mutation == "missing":
        digests.pop()
    elif mutation == "duplicate":
        digests[-1] = digests[0]
    elif mutation == "unknown":
        digests[-1] = replace(digests[-1], fold_id="F5")
    elif mutation == "uppercase":
        digests[0] = replace(digests[0], configuration_sha256="A" * 64)
    elif mutation == "short":
        digests[0] = replace(digests[0], receipt_sha256="f" * 63)

    with pytest.raises(ValueError, match="replay digest inventory"):
        finalize_selection(provisional, _replay(provisional, digests=tuple(digests)))


def test_top_level_pass_cannot_hide_a_nonpass_fold_replay() -> None:
    provisional = rank_qualified(_inventory())
    assert provisional is not None
    digests = list(_digests())
    digests[-1] = replace(digests[-1], verdict=GateVerdict.FAIL)

    decision = finalize_selection(provisional, _replay(provisional, digests=tuple(digests)))

    assert decision.status == "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
    assert decision.final_winner is None
    assert decision.retry_allowed is False
