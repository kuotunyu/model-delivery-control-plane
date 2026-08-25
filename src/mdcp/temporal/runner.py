# ruff: noqa: E402
"""Bounded, CPU-only formal temporal-development execution primitives.

This module deliberately accepts fold execution as an injected boundary.  It never opens an
archive itself, so the formal ledger can be exercised with synthetic material without granting
this layer any H2 or network capability.
"""

from __future__ import annotations

import os

# These assignments must precede every import that can transitively load an estimator.
for _thread_environment_name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "LOKY_MAX_CPU_COUNT",
):
    os.environ[_thread_environment_name] = "1"
os.environ["JOBLIB_MULTIPROCESSING"] = "0"

import ctypes
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import GateVerdict
from mdcp.temporal.selection import ReplayFoldDigests, ReplayResult
from mdcp.temporal.trials import canonical_trial_identity

EXACT_FOLD_IDS = ("F1", "F2", "F3", "F4")
EXACT_TRIAL_IDS = (
    "CTRL-01",
    "REC-180-L4",
    "REC-180-L12",
    "REC-270-L4",
    "REC-270-L12",
    "REC-365-L4",
    "REC-365-L12",
    "STAT-A0.1",
    "STAT-A1",
    "STAT-A10",
    "STAT-A100",
    "STAT-A1000",
    "NL-E64-R0.03-D2",
    "NL-E64-R0.03-D3",
    "NL-E64-R0.07-D2",
    "NL-E64-R0.07-D3",
    "NL-E128-R0.03-D2",
    "NL-E128-R0.03-D3",
    "NL-E128-R0.07-D2",
    "NL-E128-R0.07-D3",
)
_SELECTION_LIMIT = 80
_REPLAY_LIMIT = 4
_FINAL_LIMIT = 1
_MAXIMUM_LIMIT = 85
_WALL_CLOCK_NS = 21_600 * 1_000_000_000
_PEAK_MEMORY_BYTES = 4_294_967_296


class FitPhase(StrEnum):
    SELECTION = "SELECTION"
    REPLAY = "REPLAY"
    FINAL = "FINAL"


class FitBudgetError(RuntimeError):
    """Raised before an attempt can exceed the immutable formal fit plan."""


class ExecutionConfigurationError(ValueError):
    """Raised before execution for a non-CPU, networked, or unsafe context."""


@dataclass(frozen=True, slots=True)
class FitRecord:
    phase: FitPhase
    trial_id: str
    fold_id: str


@dataclass(slots=True)
class FitLedger:
    """Append-only exact-order accounting for selection, replay, and final fitting."""

    _records: list[FitRecord] = field(default_factory=list, init=False, repr=False)
    _replay_trial_id: str | None = field(default=None, init=False, repr=False)

    @property
    def records(self) -> tuple[FitRecord, ...]:
        return tuple(self._records)

    @property
    def selection_count(self) -> int:
        return sum(record.phase is FitPhase.SELECTION for record in self._records)

    @property
    def replay_count(self) -> int:
        return sum(record.phase is FitPhase.REPLAY for record in self._records)

    @property
    def final_count(self) -> int:
        return sum(record.phase is FitPhase.FINAL for record in self._records)

    @property
    def total_count(self) -> int:
        return len(self._records)

    def record(self, phase: FitPhase, trial_id: str, fold_id: str) -> None:
        """Reserve exactly one declared fit, failing before any excess execution starts."""
        if not isinstance(phase, FitPhase):
            raise FitBudgetError("fit phase is invalid")
        if self.total_count >= _MAXIMUM_LIMIT:
            raise FitBudgetError("maximum fits frozen at 85")
        if phase is FitPhase.SELECTION:
            self._record_selection(trial_id, fold_id)
        elif phase is FitPhase.REPLAY:
            self._record_replay(trial_id, fold_id)
        else:
            self._record_final(trial_id, fold_id)
        self._records.append(FitRecord(phase, trial_id, fold_id))

    def _record_selection(self, trial_id: str, fold_id: str) -> None:
        if self.selection_count >= _SELECTION_LIMIT:
            raise FitBudgetError("selection fits frozen at 80")
        expected = divmod(self.selection_count, len(EXACT_FOLD_IDS))
        expected_trial = EXACT_TRIAL_IDS[expected[0]]
        expected_fold = EXACT_FOLD_IDS[expected[1]]
        if (trial_id, fold_id) != (expected_trial, expected_fold):
            raise FitBudgetError("selection fit violates frozen order")

    def _record_replay(self, trial_id: str, fold_id: str) -> None:
        if self.selection_count != _SELECTION_LIMIT:
            raise FitBudgetError("replay requires the complete frozen selection inventory")
        if self.replay_count >= _REPLAY_LIMIT:
            raise FitBudgetError("replay fits frozen at 4")
        expected_fold = EXACT_FOLD_IDS[self.replay_count]
        if fold_id != expected_fold or trial_id not in EXACT_TRIAL_IDS[1:]:
            raise FitBudgetError("replay fit violates frozen order")
        if self._replay_trial_id is None:
            self._replay_trial_id = trial_id
        if trial_id != self._replay_trial_id:
            raise FitBudgetError("replay trial is frozen")

    def _record_final(self, trial_id: str, fold_id: str) -> None:
        if self.selection_count != _SELECTION_LIMIT or self.replay_count != _REPLAY_LIMIT:
            raise FitBudgetError("final fit requires complete selection and replay")
        if self.final_count >= _FINAL_LIMIT:
            raise FitBudgetError("final fits frozen at 1")
        if trial_id != self._replay_trial_id or fold_id != "FINAL":
            raise FitBudgetError("final fit violates frozen order")


@dataclass(frozen=True, slots=True)
class FoldFitResult:
    """Private fold evidence supplied by an approved bounded-development loader."""

    fold_id: str
    train_identity_digests: tuple[str, ...]
    validation_identity_digests: tuple[str, ...]
    preprocessing_state_sha256: str
    feature_vector_sha256: str
    stable_prediction_digest: str
    candidate_prediction_digest: str
    completeness_verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    quality_verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    metric_values: Mapping[str, float]
    receipt_sha256: str
    contract_valid: bool = True


@dataclass(frozen=True, slots=True)
class PublicFoldReceipt:
    """Public-safe aggregate evidence for one attempted fold; no rows or predictions."""

    fold_id: str
    train_row_count: int
    validation_row_count: int
    preprocessing_state_sha256: str
    feature_vector_sha256: str
    completeness_verdict: str
    quality_verdict: str
    metric_values: tuple[tuple[str, float], ...]
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class TrialRunReceipt:
    """Public-safe four-fold trial summary; private evidence stays in the injected boundary."""

    trial_id: str
    contract_valid: bool
    reason_codes: tuple[str, ...]
    fold_receipts: tuple[PublicFoldReceipt, ...]
    quality_verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class DevelopmentRunReceipt:
    """Sanitized terminal formal-development selection result."""

    status: Literal["NO_ELIGIBLE_CANDIDATE", "UNKNOWN/COMPUTE_BUDGET_EXCEEDED"]
    retry_allowed: Literal[False]
    reason_codes: tuple[str, ...]
    trials: tuple[TrialRunReceipt, ...]
    fit_ledger: FitLedger
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]

    def public_document(self) -> dict[str, object]:
        """Return counts, metrics, and digests only; never row identities or predictions."""
        return {
            "status": self.status,
            "retry_allowed": self.retry_allowed,
            "reason_codes": list(self.reason_codes),
            "selection_fit_count": self.fit_ledger.selection_count,
            "replay_fit_count": self.fit_ledger.replay_count,
            "final_fit_count": self.fit_ledger.final_count,
            "h2_status": self.h2_status,
            "h2_loaded_rows": self.h2_loaded_rows,
            "trials": [
                {
                    "trial_id": trial.trial_id,
                    "contract_valid": trial.contract_valid,
                    "reason_codes": list(trial.reason_codes),
                    "quality_verdict": trial.quality_verdict,
                    "receipt_sha256": trial.receipt_sha256,
                    "folds": [
                        {
                            "fold_id": fold.fold_id,
                            "train_row_count": fold.train_row_count,
                            "validation_row_count": fold.validation_row_count,
                            "preprocessing_state_sha256": fold.preprocessing_state_sha256,
                            "feature_vector_sha256": fold.feature_vector_sha256,
                            "completeness_verdict": fold.completeness_verdict,
                            "quality_verdict": fold.quality_verdict,
                            "metric_values": dict(fold.metric_values),
                            "receipt_sha256": fold.receipt_sha256,
                        }
                        for fold in trial.fold_receipts
                    ],
                }
                for trial in self.trials
            ],
        }


@dataclass(frozen=True, slots=True)
class FormalRunContext:
    """Explicit, dependency-injected boundary for one selection or replay attempt."""

    repository_root: Path
    output_root: Path
    fit_fold: Callable[[str, str], FoldFitResult]
    process_memory_probe: Callable[[], int | None] | None = None
    repository_is_clean: Callable[[Path], bool] | None = None
    monotonic_ns: Callable[[], int] = time.monotonic_ns
    h2_status: Literal["SEALED_NOT_LOADED"] = "SEALED_NOT_LOADED"
    h2_loaded_rows: Literal[0] = 0
    execution_providers: tuple[str, ...] = ("CPUExecutionProvider",)
    network_mode: str = "none"
    socket_configuration: Mapping[str, object] | None = None


def run_selection(context: FormalRunContext) -> DevelopmentRunReceipt:
    """Run the fixed 20-by-4 selection schedule once, with no automatic replay or final fit."""
    _validate_context(context)
    ledger = FitLedger()
    start_ns = context.monotonic_ns()
    trials: list[TrialRunReceipt] = []
    for trial_id in EXACT_TRIAL_IDS:
        fold_receipts: list[PublicFoldReceipt] = []
        contract_valid = True
        reason_codes: list[str] = []
        for fold_id in EXACT_FOLD_IDS:
            ledger.record(FitPhase.SELECTION, trial_id, fold_id)
            result = _fit_without_replacement(context, trial_id, fold_id)
            receipt = _public_fold_receipt(result)
            fold_receipts.append(receipt)
            if not result.contract_valid:
                contract_valid = False
                if "CONTRACT_INVALID" not in reason_codes:
                    reason_codes.append("CONTRACT_INVALID")
            terminal = _budget_terminal(context, start_ns)
            if terminal:
                return _terminal_budget_receipt(
                    ledger,
                    trials,
                    trial_id,
                    contract_valid,
                    reason_codes,
                    fold_receipts,
                )
        quality_verdict = _trial_quality_verdict(fold_receipts)
        if quality_verdict != "PASS" and "QUALITY_NOT_QUALIFIED" not in reason_codes:
            reason_codes.append("QUALITY_NOT_QUALIFIED")
        trials.append(
            _trial_receipt(
                trial_id,
                contract_valid,
                tuple(reason_codes),
                tuple(fold_receipts),
                quality_verdict,
            )
        )
    return DevelopmentRunReceipt(
        status="NO_ELIGIBLE_CANDIDATE",
        retry_allowed=False,
        reason_codes=("NO_QUALIFIED_TRIAL",),
        trials=tuple(trials),
        fit_ledger=ledger,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )


def replay_provisional(context: FormalRunContext, provisional_id: str) -> ReplayResult:
    """Replay exactly four folds of one declared candidate without any fallback surface."""
    _validate_context(context)
    if provisional_id not in EXACT_TRIAL_IDS[1:]:
        raise ExecutionConfigurationError("provisional trial is invalid")
    ledger = FitLedger()
    for trial_id in EXACT_TRIAL_IDS:
        for fold_id in EXACT_FOLD_IDS:
            ledger.record(FitPhase.SELECTION, trial_id, fold_id)
    digests: list[ReplayFoldDigests] = []
    start_ns = context.monotonic_ns()
    for fold_id in EXACT_FOLD_IDS:
        ledger.record(FitPhase.REPLAY, provisional_id, fold_id)
        result = _fit_without_replacement(context, provisional_id, fold_id)
        if _budget_terminal(context, start_ns):
            return _replay_unknown(provisional_id, digests)
        identity = canonical_trial_identity(provisional_id)
        digests.append(
            ReplayFoldDigests(
                fold_id=fold_id,
                verdict=GateVerdict.PASS if result.contract_valid else GateVerdict.UNKNOWN,
                configuration_sha256=identity.configuration_sha256,
                preprocessing_state_sha256=result.preprocessing_state_sha256,
                feature_vector_sha256=result.feature_vector_sha256,
                prediction_vector_sha256=sha256_hex(
                    canonicalize_json(
                        {
                            "stable": result.stable_prediction_digest,
                            "candidate": result.candidate_prediction_digest,
                        }
                    )
                ),
                metric_sha256=sha256_hex(canonicalize_json(dict(result.metric_values))),
                receipt_sha256=result.receipt_sha256,
            )
        )
    identity = canonical_trial_identity(provisional_id)
    ranking_key = (0.0, 0.0, 0.0, 0, provisional_id)
    inventory_sha256 = sha256_hex(canonicalize_json([record.trial_id for record in ledger.records]))
    return ReplayResult(
        trial_id=provisional_id,
        family_id=identity.family_id,
        ranking_key=ranking_key,
        qualification_inventory_sha256=inventory_sha256,
        session_sha256=sha256_hex(canonicalize_json([digest.receipt_sha256 for digest in digests])),
        verdict=GateVerdict.PASS,
        digests=tuple(digests),
    )


def _validate_context(context: FormalRunContext) -> None:
    if not isinstance(context, FormalRunContext):
        raise ExecutionConfigurationError("formal run context is invalid")
    if context.h2_status != "SEALED_NOT_LOADED" or context.h2_loaded_rows != 0:
        raise ExecutionConfigurationError("H2 must remain sealed and unloaded")
    if context.execution_providers != ("CPUExecutionProvider",):
        raise ExecutionConfigurationError("GPU providers are forbidden")
    if context.network_mode != "none" or context.socket_configuration:
        raise ExecutionConfigurationError("network/socket configuration is forbidden")
    try:
        repository_root = context.repository_root.resolve(strict=False)
        output_root = context.output_root.resolve(strict=False)
        output_root.relative_to(repository_root)
    except ValueError:
        pass
    except OSError as error:
        raise ExecutionConfigurationError("output root is invalid") from error
    else:
        raise ExecutionConfigurationError("output root must be outside repository")
    clean_check = context.repository_is_clean or _repository_is_clean
    if not clean_check(repository_root):
        raise ExecutionConfigurationError("repository must be clean and read-only")


def _repository_is_clean(repository_root: Path) -> bool:
    try:
        completed = subprocess.run(
            ("git", "status", "--porcelain=v1", "--untracked-files=all"),
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return completed.returncode == 0 and completed.stdout == ""


def _fit_without_replacement(
    context: FormalRunContext, trial_id: str, fold_id: str
) -> FoldFitResult:
    try:
        result = context.fit_fold(trial_id, fold_id)
    except Exception:
        return _invalid_fold_result(fold_id)
    if not isinstance(result, FoldFitResult) or result.fold_id != fold_id:
        return _invalid_fold_result(fold_id)
    return result


def _invalid_fold_result(fold_id: str) -> FoldFitResult:
    digest = sha256_hex(f"invalid:{fold_id}".encode())
    return FoldFitResult(
        fold_id=fold_id,
        train_identity_digests=(),
        validation_identity_digests=(),
        preprocessing_state_sha256=digest,
        feature_vector_sha256=digest,
        stable_prediction_digest=digest,
        candidate_prediction_digest=digest,
        completeness_verdict="UNKNOWN",
        quality_verdict="UNKNOWN",
        metric_values={},
        receipt_sha256=digest,
        contract_valid=False,
    )


def _public_fold_receipt(result: FoldFitResult) -> PublicFoldReceipt:
    return PublicFoldReceipt(
        fold_id=result.fold_id,
        train_row_count=len(result.train_identity_digests),
        validation_row_count=len(result.validation_identity_digests),
        preprocessing_state_sha256=result.preprocessing_state_sha256,
        feature_vector_sha256=result.feature_vector_sha256,
        completeness_verdict=result.completeness_verdict,
        quality_verdict=result.quality_verdict,
        metric_values=tuple(sorted(result.metric_values.items())),
        receipt_sha256=result.receipt_sha256,
    )


def _trial_quality_verdict(receipts: list[PublicFoldReceipt]) -> Literal["PASS", "FAIL", "UNKNOWN"]:
    verdicts = {receipt.quality_verdict for receipt in receipts}
    if "UNKNOWN" in verdicts:
        return "UNKNOWN"
    if "FAIL" in verdicts:
        return "FAIL"
    return "PASS"


def _trial_receipt(
    trial_id: str,
    contract_valid: bool,
    reason_codes: tuple[str, ...],
    fold_receipts: tuple[PublicFoldReceipt, ...],
    quality_verdict: Literal["PASS", "FAIL", "UNKNOWN"],
) -> TrialRunReceipt:
    document = {
        "trial_id": trial_id,
        "contract_valid": contract_valid,
        "reason_codes": list(reason_codes),
        "fold_receipt_digests": [receipt.receipt_sha256 for receipt in fold_receipts],
        "quality_verdict": quality_verdict,
    }
    return TrialRunReceipt(
        trial_id=trial_id,
        contract_valid=contract_valid,
        reason_codes=reason_codes,
        fold_receipts=fold_receipts,
        quality_verdict=quality_verdict,
        receipt_sha256=sha256_hex(canonicalize_json(document)),
    )


def _budget_terminal(context: FormalRunContext, start_ns: int) -> bool:
    elapsed = context.monotonic_ns() - start_ns
    if elapsed > _WALL_CLOCK_NS:
        return True
    probe = context.process_memory_probe or _authoritative_process_high_water_mark
    try:
        peak_bytes = probe()
    except Exception:
        return True
    return type(peak_bytes) is not int or peak_bytes < 0 or peak_bytes > _PEAK_MEMORY_BYTES


def _terminal_budget_receipt(
    ledger: FitLedger,
    completed_trials: list[TrialRunReceipt],
    trial_id: str,
    contract_valid: bool,
    reason_codes: list[str],
    fold_receipts: list[PublicFoldReceipt],
) -> DevelopmentRunReceipt:
    if fold_receipts:
        completed_trials.append(
            _trial_receipt(
                trial_id,
                contract_valid,
                tuple((*reason_codes, "COMPUTE_BUDGET_EXCEEDED")),
                tuple(fold_receipts),
                _trial_quality_verdict(fold_receipts),
            )
        )
    return DevelopmentRunReceipt(
        status="UNKNOWN/COMPUTE_BUDGET_EXCEEDED",
        retry_allowed=False,
        reason_codes=("COMPUTE_BUDGET_EXCEEDED",),
        trials=tuple(completed_trials),
        fit_ledger=ledger,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )


def _authoritative_process_high_water_mark() -> int | None:
    if sys.platform == "win32":
        return _windows_peak_working_set_size()
    if sys.platform.startswith("linux"):
        return _linux_peak_resident_bytes()
    return None


def _linux_peak_resident_bytes() -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmHWM:"):
                parts = line.split()
                if len(parts) == 3 and parts[2] == "kB":
                    return int(parts[1]) * 1024
    except (OSError, ValueError):
        return None
    return None


def _windows_peak_working_set_size() -> int | None:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = ctypes.windll.kernel32.GetCurrentProcess()
        success = ctypes.windll.psapi.GetProcessMemoryInfo(
            process, ctypes.byref(counters), counters.cb
        )
    except (AttributeError, OSError):
        return None
    return int(counters.PeakWorkingSetSize) if success else None


def _replay_unknown(provisional_id: str, digests: list[ReplayFoldDigests]) -> ReplayResult:
    identity = canonical_trial_identity(provisional_id)
    return ReplayResult(
        trial_id=provisional_id,
        family_id=identity.family_id,
        ranking_key=(0.0, 0.0, 0.0, 0, provisional_id),
        qualification_inventory_sha256=sha256_hex(b"COMPUTE_BUDGET_EXCEEDED"),
        session_sha256=sha256_hex(b"COMPUTE_BUDGET_EXCEEDED"),
        verdict=GateVerdict.UNKNOWN,
        digests=tuple(digests),
    )
