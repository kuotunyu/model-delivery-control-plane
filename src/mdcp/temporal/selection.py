"""Qualification-first ranking and sole-replay temporal selection."""

from __future__ import annotations

import math
from dataclasses import dataclass
from threading import Lock
from typing import Literal
from weakref import WeakKeyDictionary

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.temporal.evaluation import QualificationResult

type RankingKey = tuple[float, float, float, int, str]

_FINAL_ELIGIBLE_FAMILIES = {
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
_FAMILY_ORDER = {"STAT": 0, "REC": 1, "NL": 2}
_FOLD_IDS = ("F1", "F2", "F3", "F4")
_SHA256_ALPHABET = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class RankedTrial:
    """One qualified trial reduced to the frozen lexicographic key."""

    trial_id: str
    family_id: str
    pooled_ucb95: float
    worst_fold_point: float
    worst_subgroup_ucb95: float
    ranking_key: RankingKey


@dataclass(frozen=True, slots=True)
class ProvisionalWinner(RankedTrial):
    """The sole rank-one trial, bound to the complete qualification inventory."""

    qualification_inventory_sha256: str


@dataclass(frozen=True, slots=True)
class ReplayFoldDigests:
    """Required exact-replay evidence for one frozen development fold."""

    fold_id: str
    verdict: GateVerdict
    configuration_sha256: str
    preprocessing_state_sha256: str
    feature_vector_sha256: str
    prediction_vector_sha256: str
    metric_sha256: str
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """One and only one replay result for the sole provisional winner."""

    trial_id: str
    family_id: str
    ranking_key: RankingKey
    qualification_inventory_sha256: str
    session_sha256: str
    verdict: GateVerdict
    digests: tuple[ReplayFoldDigests, ...]


@dataclass(frozen=True, slots=True)
class SelectionDecision:
    """Terminal selection decision; retries and fallback are never permitted."""

    status: Literal["PASS", "NO_ELIGIBLE_CANDIDATE", "UNKNOWN/NO_ELIGIBLE_CANDIDATE"]
    provisional_winner: ProvisionalWinner | None
    final_winner: ProvisionalWinner | None
    retry_allowed: Literal[False]
    reason_codes: tuple[str, ...]


def _valid_metric(value: object, *, required: bool) -> bool:
    if value is None:
        return not required
    return type(value) is float and math.isfinite(value) and value >= 0.0


def _valid_qualification(result: object) -> bool:
    if type(result) is not QualificationResult:
        return False
    if type(result.trial_id) is not str or type(result.family_id) is not str:
        return False
    expected_family = _FINAL_ELIGIBLE_FAMILIES.get(result.trial_id)
    if expected_family is None:
        return False
    if result.family_id != expected_family or type(result.verdict) is not GateVerdict:
        return False
    if type(result.qualified) is not bool:
        return False
    if type(result.reason_codes) is not tuple or any(
        type(reason) is not str or not reason for reason in result.reason_codes
    ):
        return False
    if len(result.reason_codes) != len(set(result.reason_codes)):
        return False
    if result.qualified is not (result.verdict is GateVerdict.PASS):
        return False
    if (result.verdict is GateVerdict.PASS) is bool(result.reason_codes):
        return False
    required = result.qualified is True
    metrics = (
        result.pooled_ucb95,
        result.worst_fold_point,
        result.worst_subgroup_ucb95,
    )
    if (
        not required
        and any(value is None for value in metrics)
        and not all(value is None for value in metrics)
    ):
        return False
    return all(_valid_metric(value, required=required) for value in metrics)


def _qualification_inventory_digest(results: tuple[QualificationResult, ...]) -> str:
    material = [
        {
            "trial_id": result.trial_id,
            "family_id": result.family_id,
            "verdict": result.verdict.value,
            "qualified": result.qualified,
            "reason_codes": list(result.reason_codes),
            "pooled_ucb95": result.pooled_ucb95,
            "worst_fold_point": result.worst_fold_point,
            "worst_subgroup_ucb95": result.worst_subgroup_ucb95,
        }
        for result in sorted(results, key=lambda item: item.trial_id)
    ]
    return sha256_hex(canonicalize_json(material))


def _ranking_key(result: QualificationResult) -> RankingKey:
    if not all(
        type(value) is float
        for value in (
            result.pooled_ucb95,
            result.worst_fold_point,
            result.worst_subgroup_ucb95,
        )
    ):
        raise ValueError("qualified result metrics are invalid")
    return (
        result.pooled_ucb95,
        result.worst_fold_point,
        result.worst_subgroup_ucb95,
        _FAMILY_ORDER[result.family_id],
        result.trial_id,
    )


def rank_qualified(results: tuple[QualificationResult, ...]) -> ProvisionalWinner | None:
    """Validate the closed 19-trial inventory, then select its sole qualified rank one."""
    if type(results) is not tuple or len(results) != len(_FINAL_ELIGIBLE_FAMILIES):
        raise ValueError("qualification inventory is invalid")
    if any(
        type(result) is not QualificationResult or type(result.trial_id) is not str
        for result in results
    ):
        raise ValueError("qualification result is invalid")
    trial_ids = tuple(result.trial_id for result in results)
    if len(set(trial_ids)) != len(trial_ids) or set(trial_ids) != set(_FINAL_ELIGIBLE_FAMILIES):
        raise ValueError("qualification inventory is invalid")
    for result in results:
        if not _valid_qualification(result):
            if (
                type(result) is QualificationResult
                and result.trial_id in _FINAL_ELIGIBLE_FAMILIES
                and result.family_id != _FINAL_ELIGIBLE_FAMILIES[result.trial_id]
            ):
                raise ValueError("qualification inventory is invalid")
            raise ValueError("qualification result is invalid")

    qualified = tuple(
        result
        for result in results
        if result.qualified is True and result.verdict is GateVerdict.PASS
    )
    if not qualified:
        return None

    ranked = tuple(
        RankedTrial(
            trial_id=result.trial_id,
            family_id=result.family_id,
            pooled_ucb95=result.pooled_ucb95,
            worst_fold_point=result.worst_fold_point,
            worst_subgroup_ucb95=result.worst_subgroup_ucb95,
            ranking_key=_ranking_key(result),
        )
        for result in qualified
    )
    first = min(ranked, key=lambda result: result.ranking_key)
    return ProvisionalWinner(
        trial_id=first.trial_id,
        family_id=first.family_id,
        pooled_ucb95=first.pooled_ucb95,
        worst_fold_point=first.worst_fold_point,
        worst_subgroup_ucb95=first.worst_subgroup_ucb95,
        ranking_key=first.ranking_key,
        qualification_inventory_sha256=_qualification_inventory_digest(results),
    )


def _valid_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and set(value).issubset(_SHA256_ALPHABET)


def _valid_ranking_key(
    key: object,
    *,
    trial_id: str,
    family_id: str,
    metrics: tuple[float, float, float] | None = None,
) -> bool:
    if type(trial_id) is not str or type(family_id) is not str:
        return False
    if type(key) is not tuple or len(key) != 5:
        return False
    if not all(_valid_metric(value, required=True) for value in key[:3]):
        return False
    if type(key[3]) is not int or type(key[4]) is not str:
        return False
    expected_family = _FINAL_ELIGIBLE_FAMILIES.get(trial_id)
    if expected_family != family_id or key[3] != _FAMILY_ORDER[family_id] or key[4] != trial_id:
        return False
    return metrics is None or key[:3] == metrics


def _valid_provisional(provisional: object) -> bool:
    if type(provisional) is not ProvisionalWinner:
        return False
    if type(provisional.trial_id) is not str or type(provisional.family_id) is not str:
        return False
    metrics = (
        provisional.pooled_ucb95,
        provisional.worst_fold_point,
        provisional.worst_subgroup_ucb95,
    )
    return (
        all(_valid_metric(value, required=True) for value in metrics)
        and _valid_ranking_key(
            provisional.ranking_key,
            trial_id=provisional.trial_id,
            family_id=provisional.family_id,
            metrics=metrics,
        )
        and _valid_sha256(provisional.qualification_inventory_sha256)
    )


def _valid_replay_digests(digests: object) -> bool:
    if type(digests) is not tuple or len(digests) != len(_FOLD_IDS):
        return False
    if (
        tuple(digest.fold_id if type(digest) is ReplayFoldDigests else None for digest in digests)
        != _FOLD_IDS
    ):
        return False
    for digest in digests:
        if type(digest) is not ReplayFoldDigests or type(digest.verdict) is not GateVerdict:
            return False
        if not all(
            _valid_sha256(value)
            for value in (
                digest.configuration_sha256,
                digest.preprocessing_state_sha256,
                digest.feature_vector_sha256,
                digest.prediction_vector_sha256,
                digest.metric_sha256,
                digest.receipt_sha256,
            )
        ):
            return False
    return True


def _replay_digest_material(digests: tuple[ReplayFoldDigests, ...]) -> list[dict[str, str]]:
    return [
        {
            "fold_id": digest.fold_id,
            "verdict": digest.verdict.value,
            "configuration_sha256": digest.configuration_sha256,
            "preprocessing_state_sha256": digest.preprocessing_state_sha256,
            "feature_vector_sha256": digest.feature_vector_sha256,
            "prediction_vector_sha256": digest.prediction_vector_sha256,
            "metric_sha256": digest.metric_sha256,
            "receipt_sha256": digest.receipt_sha256,
        }
        for digest in digests
    ]


@dataclass(slots=True)
class _ReplaySessionState:
    qualification_results: tuple[QualificationResult, ...]
    expected_digests: tuple[ReplayFoldDigests, ...]
    qualification_inventory_sha256: str
    session_sha256: str
    lock: Lock
    consumed: bool


_REPLAY_SESSION_STATES: WeakKeyDictionary[object, _ReplaySessionState] = WeakKeyDictionary()
_REPLAY_SESSION_REGISTRY_LOCK = Lock()


def _replay_session_state(session: object) -> _ReplaySessionState:
    with _REPLAY_SESSION_REGISTRY_LOCK:
        try:
            return _REPLAY_SESSION_STATES[session]
        except KeyError as error:
            raise ValueError("replay selection session state is invalid") from error


class ReplaySelectionSession:
    """Transient one-shot authorization with a closed, immutable public surface."""

    __slots__ = ("__weakref__",)

    def __init__(
        self,
        qualification_results: tuple[QualificationResult, ...],
        expected_digests: tuple[ReplayFoldDigests, ...],
    ) -> None:
        provisional = rank_qualified(qualification_results)
        if not _valid_replay_digests(expected_digests) or any(
            digest.verdict is not GateVerdict.PASS for digest in expected_digests
        ):
            raise ValueError("expected replay digest inventory is invalid")
        qualification_inventory_sha256 = (
            provisional.qualification_inventory_sha256
            if provisional is not None
            else _qualification_inventory_digest(qualification_results)
        )
        session_sha256 = sha256_hex(
            canonicalize_json(
                {
                    "qualification_inventory_sha256": qualification_inventory_sha256,
                    "expected_replay_digests": _replay_digest_material(expected_digests),
                }
            )
        )
        state = _ReplaySessionState(
            qualification_results=qualification_results,
            expected_digests=expected_digests,
            qualification_inventory_sha256=qualification_inventory_sha256,
            session_sha256=session_sha256,
            lock=Lock(),
            consumed=False,
        )
        with _REPLAY_SESSION_REGISTRY_LOCK:
            if self in _REPLAY_SESSION_STATES:
                raise RuntimeError("replay selection session is already initialized")
            _REPLAY_SESSION_STATES[self] = state

    @property
    def qualification_inventory_sha256(self) -> str:
        """Return only the safe digest identity, never the raw qualification inventory."""
        return _replay_session_state(self).qualification_inventory_sha256

    @property
    def session_sha256(self) -> str:
        """Return the safe one-shot session identity."""
        return _replay_session_state(self).session_sha256

    @property
    def consumed(self) -> bool:
        """Read replay-consumption state under the same lock used by the transition."""
        state = _replay_session_state(self)
        with state.lock:
            return state.consumed

    def __repr__(self) -> str:
        return (
            "ReplaySelectionSession("
            f"session_sha256='{self.session_sha256}', consumed={self.consumed})"
        )

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError("replay selection sessions are transient and non-serializable")

    def consume_once(self) -> bool:
        """Atomically consume this authorization exactly once, with no reset surface."""
        state = _replay_session_state(self)
        with state.lock:
            if state.consumed:
                return False
            state.consumed = True
            return True

    def ranked_provisional(self) -> ProvisionalWinner | None:
        """Recompute rank one from the private immutable qualification inventory."""
        return rank_qualified(_replay_session_state(self).qualification_results)

    def matches_expected_digests(self, digests: object) -> bool:
        """Compare actual replay evidence byte-for-byte with the trusted baseline."""
        return (
            _valid_replay_digests(digests)
            and digests == _replay_session_state(self).expected_digests
        )


def _no_eligible_decision() -> SelectionDecision:
    return SelectionDecision(
        status="NO_ELIGIBLE_CANDIDATE",
        provisional_winner=None,
        final_winner=None,
        retry_allowed=False,
        reason_codes=("NO_QUALIFIED_TRIAL",),
    )


def _replay_terminal(provisional: ProvisionalWinner | None, reason_code: str) -> SelectionDecision:
    return SelectionDecision(
        status="UNKNOWN/NO_ELIGIBLE_CANDIDATE",
        provisional_winner=provisional,
        final_winner=None,
        retry_allowed=False,
        reason_codes=(reason_code,),
    )


def finalize_selection(
    session: ReplaySelectionSession,
    provisional: ProvisionalWinner | None,
    replay: ReplayResult | None,
) -> SelectionDecision:
    """Atomically consume one replay and promote only exact expected replay bytes."""
    if type(session) is not ReplaySelectionSession:
        raise ValueError("replay selection session is invalid")
    if not session.consume_once():
        return _replay_terminal(session.ranked_provisional(), "REPLAY_ALREADY_CONSUMED")

    canonical_provisional = session.ranked_provisional()
    if canonical_provisional is None:
        if provisional is None and replay is None:
            return _no_eligible_decision()
        return _replay_terminal(None, "PROVISIONAL_WINNER_UNEXPECTED")
    if not _valid_provisional(provisional) or provisional != canonical_provisional:
        return _replay_terminal(canonical_provisional, "PROVISIONAL_WINNER_MISMATCH")
    if type(replay) is not ReplayResult:
        return _replay_terminal(canonical_provisional, "REPLAY_RESULT_INVALID")
    if type(replay.verdict) is not GateVerdict:
        return _replay_terminal(canonical_provisional, "REPLAY_VERDICT_INVALID")
    if not _valid_sha256(replay.qualification_inventory_sha256) or not _valid_sha256(
        replay.session_sha256
    ):
        return _replay_terminal(canonical_provisional, "REPLAY_IDENTITY_INVALID")
    if not _valid_ranking_key(
        replay.ranking_key,
        trial_id=replay.trial_id,
        family_id=replay.family_id,
    ) or (
        replay.trial_id != canonical_provisional.trial_id
        or replay.family_id != canonical_provisional.family_id
        or replay.ranking_key != canonical_provisional.ranking_key
        or replay.qualification_inventory_sha256
        != canonical_provisional.qualification_inventory_sha256
        or replay.qualification_inventory_sha256 != session.qualification_inventory_sha256
        or replay.session_sha256 != session.session_sha256
    ):
        return _replay_terminal(canonical_provisional, "REPLAY_IDENTITY_INVALID")

    if replay.verdict is not GateVerdict.PASS:
        return _replay_terminal(canonical_provisional, f"REPLAY_{replay.verdict.value}")
    if not session.matches_expected_digests(replay.digests):
        return _replay_terminal(canonical_provisional, "REPLAY_DIGEST_MISMATCH")
    return SelectionDecision(
        status="PASS",
        provisional_winner=canonical_provisional,
        final_winner=canonical_provisional,
        retry_allowed=False,
        reason_codes=(),
    )
