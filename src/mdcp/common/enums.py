from enum import StrEnum


class GateVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ValidationVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    QUARANTINE = "QUARANTINE"


class ReleaseState(StrEnum):
    SUBMITTED = "SUBMITTED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    SHADOW = "SHADOW"
    CANARY_10 = "CANARY_10"
    CANARY_25 = "CANARY_25"
    CANARY_50 = "CANARY_50"
    PRODUCTION = "PRODUCTION"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    ROLLED_BACK = "ROLLED_BACK"
    QUARANTINED = "QUARANTINED"


class ExecutionRole(StrEnum):
    STABLE = "stable"
    CANDIDATE = "candidate"
    SHADOW = "shadow"


class EvidenceClass(StrEnum):
    BOOTSTRAP_BASELINE = "bootstrap_baseline"
    MEASURED_WORKLOAD = "measured_workload"
    INJECTED_TEST = "injected_test"
    RELEASE_CI_VERIFIED = "release_ci_verified"
    REVIEWER_LOCALLY_RECOMPUTED = "reviewer_locally_recomputed"
    SYNTHETIC_TEST = "synthetic_test"


class FaultProfile(StrEnum):
    NONE = "none"
    LATENCY_PLUS_30MS = "latency_plus_30ms"
    ERROR_RATE = "error_rate"
    MEMORY_PAD = "memory_pad"
    SUBGROUP_CORRUPTION = "subgroup_corruption"
    TELEMETRY_DROP = "telemetry_drop"
    DUPLICATE_CONFLICT = "duplicate_conflict"
    OUT_OF_ORDER = "out_of_order"
    STALE_ROUTE_REVISION = "stale_route_revision"
