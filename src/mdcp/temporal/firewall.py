from __future__ import annotations

import ast
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import FrameType, FunctionType
from typing import Annotated, Literal

import pandas as pd
from pydantic import BeforeValidator, ConfigDict, StringConstraints, with_config
from pydantic.dataclasses import dataclass as pydantic_dataclass
from typing_extensions import TypedDict

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.workload.dataset import load_uci_development_archive
from mdcp.workload.splits import split_development_rows

FORMAL_V2_FIXED_PATHS = (
    "src/mdcp/contracts/workload_v2.py",
    "src/mdcp/predictor/app_v2.py",
)
FORMAL_TEMPORAL_PACKAGE_ROOT = "src/mdcp/temporal"

_FORBIDDEN_MODULES = frozenset(
    {
        "mdcp.workload.dataset",
        "mdcp.workload.splits",
    }
)
_DYNAMIC_IMPORT_FUNCTIONS = frozenset(
    {
        "importlib.import_module",
        "__import__",
        "builtins.__import__",
    }
)
_DYNAMIC_IMPORT_MODULES = frozenset({"importlib", "builtins"})
_REFLECTION_MODULES = frozenset({"gc", "inspect", "marshal", "operator", "pickle"})
_FORBIDDEN_DYNAMIC_REFERENCES = _DYNAMIC_IMPORT_FUNCTIONS | {
    "__builtins__",
    "__file__",
    "__loader__",
    "__spec__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "locals",
    "open",
    "setattr",
    "vars",
    "sys.modules",
}
_FORBIDDEN_REFLECTION_ATTRIBUTES = frozenset(
    {
        "__base__",
        "__bases__",
        "__builtins__",
        "__class__",
        "__closure__",
        "__dict__",
        "__getattribute__",
        "__globals__",
        "__mro__",
        "__subclasses__",
        "ag_frame",
        "cr_frame",
        "f_back",
        "f_builtins",
        "f_globals",
        "f_locals",
        "gi_frame",
        "modules",
        "query",
        "sys",
        "tb_frame",
        "tb_next",
        "eval",
    }
)
_TRUSTED_FIREWALL_PATH = "src/mdcp/temporal/firewall.py"
_ENCODING_COOKIE_PATTERN = re.compile(rb"^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)")
_UTF8_BOM = b"\xef\xbb\xbf"
_ALLOWED_DIRECT_IMPORTS = {
    "mdcp.workload.dataset": frozenset({"load_uci_development_archive"}),
    "mdcp.workload.splits": frozenset({"DevelopmentPartitions", "split_development_rows"}),
}
_FORMAL_IMPORT_ALLOWLIST = {
    "src/mdcp/contracts/workload_v2.py": frozenset(
        {
            ("__future__", "annotations"),
            ("mdcp.contracts.workload", "BikeRequest"),
            ("mdcp.contracts.workload", "NormalizedFloat"),
            ("mdcp.contracts.workload", "RequestId"),
            ("pydantic", "BaseModel"),
            ("pydantic", "ConfigDict"),
            ("pydantic", "Field"),
            ("pydantic", "StringConstraints"),
            ("typing", "Annotated"),
            ("typing", "Literal"),
        }
    ),
    "src/mdcp/predictor/app_v2.py": frozenset(
        {
            ("__future__", "annotations"),
            ("fastapi", "FastAPI"),
            ("fastapi", "Request"),
            ("fastapi.exceptions", "RequestValidationError"),
            ("fastapi.responses", "JSONResponse"),
            ("json", None),
            ("math", None),
            ("mdcp.common.enums", "ExecutionRole"),
            ("mdcp.contracts.workload", "PredictionResponse"),
            ("mdcp.contracts.workload", "SafeErrorResponse"),
            ("mdcp.predictor.runtime", "OnnxPredictor"),
            ("mdcp.predictor.runtime", "PredictionContractError"),
            ("mdcp.temporal.routing", "AdmissionKind"),
            ("mdcp.temporal.routing", "classify_envelope"),
            ("os", None),
            ("pathlib", "Path"),
            ("pydantic", "ValidationError"),
            ("typing", "Protocol"),
        }
    ),
    "src/mdcp/temporal/adapter.py": frozenset(
        {
            ("__future__", "annotations"),
            ("dataclasses", "dataclass"),
            ("datetime", "date"),
            ("datetime", "datetime"),
            ("enum", "StrEnum"),
            ("math", None),
            ("mdcp.contracts.workload_v2", "BikeRequestV2"),
            ("mdcp.temporal.constants", "DOMAIN_END_LOCAL"),
            ("mdcp.temporal.constants", "DOMAIN_START_LOCAL"),
            ("mdcp.temporal.constants", "TEMPORAL_FEATURE_COLUMNS"),
            ("mdcp.temporal.constants", "TIMEZONE_NAME"),
            ("re", None),
            ("zoneinfo", "ZoneInfo"),
        }
    ),
    "src/mdcp/temporal/completeness.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections", "Counter"),
            ("collections", "defaultdict"),
            ("collections.abc", "Callable"),
            ("collections.abc", "Iterable"),
            ("dataclasses", "dataclass"),
            ("datetime", "date"),
            ("datetime", "datetime"),
            ("math", None),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.common.enums", "GateVerdict"),
            ("mdcp.policy.cluster_bootstrap", "PairedQualityRow"),
            ("mdcp.temporal.folds", "SourceRowIdentity"),
            ("typing", "TypeVar"),
        }
    ),
    "src/mdcp/temporal/evaluation.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections.abc", "Mapping"),
            ("collections.abc", "Sequence"),
            ("dataclasses", "asdict"),
            ("dataclasses", "dataclass"),
            ("datetime", "date"),
            ("datetime", "datetime"),
            ("math", None),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.common.enums", "GateVerdict"),
            ("mdcp.policy.cluster_bootstrap", "BootstrapResult"),
            ("mdcp.policy.cluster_bootstrap", "PairedQualityRow"),
            ("mdcp.policy.cluster_bootstrap", "RatioMetric"),
            ("mdcp.policy.cluster_bootstrap", "cluster_bootstrap_ratios"),
            ("mdcp.temporal.completeness", "ADAPTER_REASON_CODES"),
            ("mdcp.temporal.completeness", "LABEL_REASON_CODES"),
            ("mdcp.temporal.completeness", "PREDICTION_REASON_CODES"),
            ("mdcp.temporal.completeness", "CompletenessReceipt"),
            ("mdcp.temporal.completeness", "LayerAccounting"),
            ("mdcp.temporal.folds", "SourceRowIdentity"),
            ("mdcp.temporal.folds", "is_frozen_validation_timestamp"),
            ("mdcp.temporal.trials", "TrialIdentity"),
            ("mdcp.temporal.trials", "is_canonical_trial_identity"),
        }
    ),
    "src/mdcp/temporal/selection.py": frozenset(
        {
            ("__future__", "annotations"),
            ("dataclasses", "dataclass"),
            ("math", None),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.common.enums", "GateVerdict"),
            ("mdcp.temporal.evaluation", "QualificationFoldDigests"),
            ("mdcp.temporal.evaluation", "QualificationResult"),
            ("mdcp.temporal.trials", "canonical_trial_identity"),
            ("threading", "Lock"),
            ("typing", "Literal"),
            ("weakref", "WeakKeyDictionary"),
        }
    ),
    "src/mdcp/temporal/constants.py": frozenset({("datetime", "datetime")}),
    "src/mdcp/temporal/contract_gate.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections.abc", "Mapping"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.canonical", "parse_json_bytes"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.contracts.release", "serving_inventory_digest"),
            ("mdcp.contracts.release", "serving_inventory_from_root"),
            ("mdcp.contracts.serving_identity_v2", "V2_SERVING_PATHS"),
            ("mdcp.contracts.serving_identity_v2", "V2ServingInventoryBody"),
            ("mdcp.contracts.serving_identity_v2", "V2ServingInventoryResult"),
            ("mdcp.contracts.serving_identity_v2", "build_v2_serving_inventory"),
            ("mdcp.contracts.serving_identity_v2", "verify_v2_serving_inventory"),
            ("mdcp.contracts.workload_v2", "BikeRequestV2"),
            ("mdcp.predictor.app", "create_app"),
            ("mdcp.predictor.app_v2", "create_app"),
            ("mdcp.temporal.constants", "TEMPORAL_FEATURE_COLUMNS"),
            ("mdcp.temporal.constants", "TEMPORAL_SCHEMA_ID"),
            ("mdcp.temporal.evidence", "public_evidence_violations"),
            ("mdcp.temporal.firewall", "BehavioralFirewallBody"),
            ("mdcp.temporal.firewall", "BehavioralFirewallResult"),
            ("mdcp.temporal.firewall", "DevelopmentBoundaryResult"),
            ("mdcp.temporal.firewall", "audit_static_h2_firewall"),
            ("mdcp.temporal.firewall", "run_behavioral_h2_firewall"),
            ("mdcp.temporal.firewall", "run_development_boundary"),
            ("mdcp.temporal.golden_vectors", "GoldenInventoryResult"),
            ("mdcp.temporal.golden_vectors", "verify_golden_vector_manifest"),
            ("mdcp.temporal.routing", "AdmissionKind"),
            ("mdcp.temporal.routing", "classify_envelope"),
            ("mdcp.workload.features", "audit_temporal_feature_lineage"),
            ("pathlib", "Path"),
            ("pydantic", "BaseModel"),
            ("pydantic", "ConfigDict"),
            ("pydantic", "Field"),
            ("pydantic", "StringConstraints"),
            ("typing", "Annotated"),
            ("typing", "Literal"),
        }
    ),
    "src/mdcp/temporal/evidence.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections.abc", "Mapping"),
            ("collections.abc", "Sequence"),
            ("dataclasses", "asdict"),
            ("dataclasses", "dataclass"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("re", None),
        }
    ),
    _TRUSTED_FIREWALL_PATH: frozenset(
        {
            ("__future__", "annotations"),
            ("ast", None),
            ("dataclasses", "dataclass"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.workload.dataset", "load_uci_development_archive"),
            ("mdcp.workload.splits", "split_development_rows"),
            ("pandas", None),
            ("pathlib", "Path"),
            ("pathlib", "PurePosixPath"),
            ("pydantic", "BeforeValidator"),
            ("pydantic", "ConfigDict"),
            ("pydantic", "StringConstraints"),
            ("pydantic", "with_config"),
            ("pydantic.dataclasses", "dataclass"),
            ("re", None),
            ("sys", None),
            ("tokenize", None),
            ("types", "FrameType"),
            ("types", "FunctionType"),
            ("typing", "Annotated"),
            ("typing", "Literal"),
            ("typing_extensions", "TypedDict"),
        }
    ),
    "src/mdcp/temporal/folds.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections.abc", "Iterable"),
            ("collections.abc", "Mapping"),
            ("collections.abc", "Sequence"),
            ("dataclasses", "dataclass"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.workload.splits", "DevelopmentPartitions"),
            ("pandas", None),
            ("typing", "Any"),
        }
    ),
    "src/mdcp/temporal/golden_vectors.py": frozenset(
        {
            ("__future__", "annotations"),
            ("dataclasses", "dataclass"),
            ("hashlib", None),
            ("math", None),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.canonical", "parse_json_bytes"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.contracts.workload_v2", "BikeRequestV2"),
            ("mdcp.temporal.adapter", "TemporalContractError"),
            ("mdcp.temporal.adapter", "adapt_v2"),
            ("mdcp.temporal.constants", "TEMPORAL_FEATURE_COLUMNS"),
            ("mdcp.temporal.constants", "TEMPORAL_SCHEMA_ID"),
            ("pathlib", "Path"),
            ("pydantic", "ValidationError"),
            ("struct", None),
            ("typing", "Literal"),
        }
    ),
    "src/mdcp/temporal/routing.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections.abc", "Mapping"),
            ("dataclasses", "dataclass"),
            ("enum", "StrEnum"),
            ("mdcp.contracts.workload", "BikeRequest"),
            ("mdcp.contracts.workload_v2", "BikeRequestV2"),
            ("mdcp.temporal.adapter", "TemporalContractError"),
            ("mdcp.temporal.adapter", "TemporalFeatureVector"),
            ("mdcp.temporal.adapter", "adapt_v2"),
            ("pydantic", "ValidationError"),
        }
    ),
    "src/mdcp/temporal/trials.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections.abc", "Mapping"),
            ("dataclasses", "dataclass"),
            ("datetime", "UTC"),
            ("enum", "StrEnum"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.contracts.workload_v2", "BikeRequestV2"),
            ("mdcp.temporal.adapter", "adapt_v2"),
            ("mdcp.temporal.constants", "TEMPORAL_FEATURE_COLUMNS"),
            ("mdcp.temporal.constants", "TIMEZONE_NAME"),
            ("mdcp.temporal.folds", "FoldRows"),
            ("numpy", None),
            ("pandas", None),
            ("sklearn.base", "BaseEstimator"),
            ("sklearn.base", "TransformerMixin"),
            ("sklearn.compose", "ColumnTransformer"),
            ("sklearn.ensemble", "GradientBoostingRegressor"),
            ("sklearn.ensemble", "RandomForestRegressor"),
            ("sklearn.linear_model", "Ridge"),
            ("sklearn.pipeline", "Pipeline"),
            ("sklearn.preprocessing", "OneHotEncoder"),
            ("sklearn.utils.validation", "check_array"),
            ("sklearn.utils.validation", "check_is_fitted"),
            ("types", "MappingProxyType"),
            ("typing", "Any"),
            ("typing", "Literal"),
            ("zoneinfo", "ZoneInfo"),
        }
    ),
    "src/mdcp/temporal/runtime_guards.py": frozenset(
        {
            ("__future__", "annotations"),
            ("collections.abc", "Callable"),
            ("ctypes", None),
            ("dataclasses", "dataclass"),
            ("enum", "StrEnum"),
            ("hashlib", None),
            ("os", None),
            ("pathlib", "Path"),
            ("pathlib", "PurePosixPath"),
            ("stat", None),
            ("subprocess", None),
            ("sys", None),
            ("time", None),
            ("typing", "Literal"),
            ("mdcp.temporal.formal_worker_protocol", "FORMAL_WORKER_SOURCE_PATHS"),
            ("mdcp.temporal.formal_worker_protocol", "FormalWorkerSourceEntry"),
            (
                "mdcp.temporal.formal_worker_protocol",
                "formal_worker_inventory_sha256",
            ),
            ("mdcp.temporal.formal_worker_protocol", "SEARCH_SOURCE_PATHS"),
            ("mdcp.temporal.formal_worker_protocol", "SearchSourceEntry"),
            (
                "mdcp.temporal.formal_worker_protocol",
                "search_source_inventory_sha256",
            ),
        }
    ),
    "src/mdcp/temporal/runner.py": frozenset(
        {
            ("__future__", "annotations"),
            ("dataclasses", "asdict"),
            ("dataclasses", "dataclass"),
            ("dataclasses", "field"),
            ("enum", "StrEnum"),
            ("math", None),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.common.enums", "GateVerdict"),
            ("mdcp.temporal.completeness", "AdapterOutcome"),
            ("mdcp.temporal.completeness", "CompletenessReceipt"),
            ("mdcp.temporal.completeness", "LabelOutcome"),
            ("mdcp.temporal.completeness", "PredictionOutcome"),
            ("mdcp.temporal.completeness", "assemble_development_pairs"),
            ("mdcp.temporal.evaluation", "DevelopmentQualityReport"),
            ("mdcp.temporal.evaluation", "FoldQualificationContext"),
            ("mdcp.temporal.evaluation", "QualificationContext"),
            ("mdcp.temporal.evaluation", "QualificationEvidence"),
            ("mdcp.temporal.evaluation", "QualificationFoldDigests"),
            ("mdcp.temporal.evaluation", "QualificationResult"),
            ("mdcp.temporal.evaluation", "evaluate_pooled"),
            ("mdcp.temporal.evaluation", "qualify_trial"),
            ("mdcp.temporal.folds", "SourceRowIdentity"),
            ("mdcp.temporal.run_evidence", "ClosedMetrics"),
            ("mdcp.temporal.run_evidence", "PrivateFoldEvidence"),
            ("mdcp.temporal.run_evidence", "PrivateRunBundle"),
            ("mdcp.temporal.run_evidence", "PublicDevelopmentResult"),
            ("mdcp.temporal.run_evidence", "PublicFoldReceipt"),
            ("mdcp.temporal.run_evidence", "PublicTrialReceipt"),
            ("mdcp.temporal.selection", "ProvisionalWinner"),
            ("mdcp.temporal.selection", "ReplayFoldDigests"),
            ("mdcp.temporal.selection", "ReplayResult"),
            ("mdcp.temporal.selection", "ReplaySelectionSession"),
            ("mdcp.temporal.selection", "SelectionDecision"),
            ("mdcp.temporal.selection", "finalize_selection"),
            ("mdcp.temporal.trials", "canonical_trial_identity"),
        }
    ),
    "src/mdcp/temporal/cli.py": frozenset(
        {
            ("__future__", "annotations"),
            ("argparse", None),
            ("collections.abc", "Sequence"),
            ("datetime", "datetime"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.temporal", "run_evidence"),
            ("mdcp.temporal.search_identity", "verify_search_freeze"),
            ("mdcp.temporal.search_identity", "prepare_search_freeze"),
            ("mdcp.temporal.search_identity", "verify_search_source_inventory"),
            ("os", None),
            ("pathlib", "Path"),
            ("sys", None),
        }
    ),
    "src/mdcp/temporal/search_identity.py": frozenset(
        {
            ("__future__", "annotations"),
            ("dataclasses", "dataclass"),
            ("datetime", "UTC"),
            ("datetime", "datetime"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.canonical", "parse_json_bytes"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.temporal.evidence", "public_evidence_violations"),
            ("mdcp.temporal.formal_worker_protocol", "FormalRunAuthorization"),
            ("mdcp.temporal.formal_worker_protocol", "GitCommit"),
            ("mdcp.temporal.formal_worker_protocol", "PRIVATE_LOGICAL_OUTPUTS"),
            ("mdcp.temporal.formal_worker_protocol", "SEARCH_SOURCE_PATHS"),
            ("mdcp.temporal.formal_worker_protocol", "SearchEvidenceIndex"),
            ("mdcp.temporal.formal_worker_protocol", "SearchReceipt"),
            ("mdcp.temporal.formal_worker_protocol", "SearchSourceEntry"),
            ("mdcp.temporal.formal_worker_protocol", "Sha256"),
            ("mdcp.temporal.formal_worker_protocol", "search_source_inventory_sha256"),
            ("os", None),
            ("pathlib", "Path"),
            ("pydantic", "BaseModel"),
            ("pydantic", "ConfigDict"),
            ("pydantic", "StringConstraints"),
            ("pydantic", "field_validator"),
            ("pydantic", "model_validator"),
            ("subprocess", None),
            ("stat", None),
            ("typing", "Annotated"),
            ("typing", "Literal"),
        }
    ),
    "src/mdcp/temporal/formal_worker_protocol.py": frozenset(
        {
            ("__future__", "annotations"),
            ("datetime", "UTC"),
            ("datetime", "datetime"),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.canonical", "parse_json_bytes"),
            ("mdcp.common.digests", "sha256_hex"),
            ("pydantic", "BaseModel"),
            ("pydantic", "ConfigDict"),
            ("pydantic", "StringConstraints"),
            ("pydantic", "field_validator"),
            ("pydantic", "model_validator"),
            ("typing", "Annotated"),
            ("typing", "Literal"),
        }
    ),
    "src/mdcp/temporal/formal_worker.py": frozenset(
        {
            ("__future__", "annotations"),
            ("base64", "b64encode"),
            ("ctypes", None),
            ("ctypes", "wintypes"),
            ("dataclasses", "asdict"),
            ("dataclasses", "dataclass"),
            ("dataclasses", "is_dataclass"),
            ("datetime", "datetime"),
            ("hashlib", None),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.canonical", "parse_json_bytes"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.common.enums", "GateVerdict"),
            ("mdcp.temporal", "run_evidence"),
            ("mdcp.temporal.completeness", "AdapterOutcome"),
            ("mdcp.temporal.completeness", "LabelOutcome"),
            ("mdcp.temporal.completeness", "PredictionOutcome"),
            ("mdcp.temporal.folds", "load_fold_specs"),
            ("mdcp.temporal.folds", "materialize_folds"),
            ("mdcp.temporal.formal_worker_protocol", "FORMAL_WORKER_SOURCE_PATHS"),
            ("mdcp.temporal.formal_worker_protocol", "FormalRunAuthorization"),
            ("mdcp.temporal.formal_worker_protocol", "FormalWorkerPrivateIdentity"),
            ("mdcp.temporal.formal_worker_protocol", "FormalWorkerResponse"),
            ("mdcp.temporal.formal_worker_protocol", "FormalWorkerSourceEntry"),
            ("mdcp.temporal.formal_worker_protocol", "MAX_WORKER_MESSAGE_BYTES"),
            ("mdcp.temporal.formal_worker_protocol", "PRIVATE_LOGICAL_OUTPUTS"),
            ("mdcp.temporal.formal_worker_protocol", "SEARCH_SOURCE_PATHS"),
            ("mdcp.temporal.formal_worker_protocol", "SearchEvidenceIndex"),
            ("mdcp.temporal.formal_worker_protocol", "SearchReceipt"),
            ("mdcp.temporal.formal_worker_protocol", "SearchSourceEntry"),
            ("mdcp.temporal.formal_worker_protocol", "encode_formal_worker_response"),
            ("mdcp.temporal.formal_worker_protocol", "formal_worker_inventory_sha256"),
            ("mdcp.temporal.formal_worker_protocol", "launch_profile_sha256"),
            ("mdcp.temporal.formal_worker_protocol", "parse_formal_worker_request"),
            ("mdcp.temporal.formal_worker_protocol", "search_source_inventory_sha256"),
            ("mdcp.temporal.formal_worker_protocol", "worker_request_sha256"),
            ("mdcp.temporal.run_evidence", "FormalDevelopmentSeal"),
            ("mdcp.temporal.run_evidence", "PrivateFoldEvidence"),
            ("mdcp.temporal.run_evidence", "PublicDevelopmentResult"),
            ("mdcp.temporal.runner", "DevelopmentFoldResult"),
            ("mdcp.temporal.runner", "DevelopmentRunBundle"),
            ("mdcp.temporal.runner", "DevelopmentStateMachine"),
            ("mdcp.temporal.runner", "EXACT_FOLD_IDS"),
            ("mdcp.temporal.runner", "EXACT_TRIAL_IDS"),
            ("mdcp.temporal.runner", "FitPhase"),
            ("mdcp.temporal.runner", "_formal_groups"),
            ("mdcp.temporal.runtime_guards", "RuntimeStage"),
            ("mdcp.temporal.runtime_guards", "build_worker_runtime_guard"),
            ("mdcp.temporal.trials", "_feature_names"),
            ("mdcp.temporal.trials", "_materialize_features"),
            ("mdcp.temporal.trials", "build_estimator"),
            ("mdcp.temporal.trials", "canonical_trial_identity"),
            ("mdcp.temporal.trials", "load_trial_specs"),
            ("mdcp.temporal.trials", "training_rows_for_trial"),
            ("mdcp.workload.dataset", "load_uci_development_archive"),
            ("mdcp.workload.splits", "split_development_rows"),
            ("os", None),
            ("pathlib", "Path"),
            ("shutil", None),
            ("stat", None),
            ("sys", None),
            ("unicodedata", None),
        }
    ),
    "src/mdcp/temporal/run_evidence.py": frozenset(
        {
            ("__future__", "annotations"),
            ("base64", None),
            ("ctypes", None),
            ("ctypes", "wintypes"),
            ("dataclasses", "asdict"),
            ("dataclasses", "dataclass"),
            ("dataclasses", "field"),
            ("contextlib", "suppress"),
            ("json", None),
            ("math", None),
            ("mdcp.common.canonical", "canonicalize_json"),
            ("mdcp.common.canonical", "parse_json_bytes"),
            ("mdcp.common.digests", "sha256_hex"),
            ("mdcp.temporal.evidence", "public_evidence_violations"),
            ("mdcp.temporal.formal_worker_protocol", "FORMAL_WORKER_SOURCE_PATHS"),
            ("mdcp.temporal.formal_worker_protocol", "FormalWorkerSourceEntry"),
            ("mdcp.temporal.formal_worker_protocol", "formal_worker_inventory_sha256"),
            ("mdcp.temporal.formal_worker_protocol", "FormalRunAuthorization"),
            ("mdcp.temporal.formal_worker_protocol", "FormalWorkerRequest"),
            ("mdcp.temporal.formal_worker_protocol", "SearchEvidenceIndex"),
            ("mdcp.temporal.formal_worker_protocol", "SearchReceipt"),
            ("mdcp.temporal.formal_worker_protocol", "SEARCH_SOURCE_PATHS"),
            ("mdcp.temporal.formal_worker_protocol", "SearchSourceEntry"),
            ("mdcp.temporal.formal_worker_protocol", "encode_formal_worker_request"),
            ("mdcp.temporal.formal_worker_protocol", "launch_profile_sha256"),
            (
                "mdcp.temporal.formal_worker_protocol",
                "search_source_inventory_sha256",
            ),
            ("mdcp.temporal.formal_worker_protocol", "worker_request_sha256"),
            (
                "mdcp.temporal.formal_worker_protocol",
                "FORMAL_WORKER_TERMINATION_WAIT_SECONDS",
            ),
            ("mdcp.temporal.formal_worker_protocol", "FORMAL_WORKER_TIMEOUT_SECONDS"),
            ("mdcp.temporal.formal_worker_protocol", "MAX_WORKER_MESSAGE_BYTES"),
            ("mdcp.temporal.formal_worker_protocol", "WORKER_STDOUT_PROBE_BYTES"),
            ("mdcp.temporal.formal_worker_protocol", "parse_formal_worker_response"),
            ("mdcp.temporal.runner", "EXACT_TRIAL_IDS"),
            ("mdcp.temporal.trials", "canonical_trial_identity"),
            ("os", None),
            ("pathlib", "Path"),
            ("pathlib", "PurePosixPath"),
            ("pydantic", "BaseModel"),
            ("pydantic", "ConfigDict"),
            ("pydantic", "StringConstraints"),
            ("pydantic", "StrictFloat"),
            ("pydantic", "StrictInt"),
            ("pydantic", "field_validator"),
            ("pydantic", "model_validator"),
            ("stat", None),
            ("subprocess", None),
            ("sys", None),
            ("threading", "Event"),
            ("threading", "Thread"),
            ("time", None),
            ("typing", "Annotated"),
            ("typing", "Literal"),
            ("unicodedata", None),
        }
    ),
}
_SCOPED_IMPORT_ALLOWLIST = {
    "src/mdcp/temporal/runtime_guards.py": {
        (
            "mdcp.temporal.formal_worker_protocol",
            "FORMAL_WORKER_SOURCE_PATHS",
        ): frozenset({"_formal_worker_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FormalWorkerSourceEntry",
        ): frozenset({"_formal_worker_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "formal_worker_inventory_sha256",
        ): frozenset({"_formal_worker_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SEARCH_SOURCE_PATHS",
        ): frozenset({"_worker_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SearchSourceEntry",
        ): frozenset({"_worker_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "search_source_inventory_sha256",
        ): frozenset({"_worker_source_inventory"}),
    },
    "src/mdcp/temporal/run_evidence.py": {
        ("sys", None): frozenset({"_current_python_executable", "_supervisor_preflight"}),
        ("subprocess", None): frozenset({"_git_bytes", "_run_fixed_worker_transport"}),
        ("time", None): frozenset({"_run_fixed_worker_transport"}),
        ("threading", "Thread"): frozenset({"_run_fixed_worker_transport"}),
        ("threading", "Event"): frozenset({"_run_fixed_worker_transport"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FORMAL_WORKER_SOURCE_PATHS",
        ): frozenset({"_formal_worker_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FormalWorkerSourceEntry",
        ): frozenset({"_formal_worker_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "formal_worker_inventory_sha256",
        ): frozenset({"_formal_worker_inventory"}),
        ("mdcp.temporal.formal_worker_protocol", "FormalRunAuthorization"): frozenset(
            {"_supervisor_preflight"}
        ),
        ("mdcp.temporal.formal_worker_protocol", "FormalWorkerRequest"): frozenset(
            {"_supervisor_preflight"}
        ),
        ("mdcp.temporal.formal_worker_protocol", "SearchReceipt"): frozenset(
            {"_supervisor_preflight"}
        ),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SEARCH_SOURCE_PATHS",
        ): frozenset({"_verified_search_freeze_topology", "_verified_search_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SearchEvidenceIndex",
        ): frozenset({"_supervisor_preflight", "_verified_search_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SearchSourceEntry",
        ): frozenset({"_verified_search_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "search_source_inventory_sha256",
        ): frozenset({"_verified_search_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "encode_formal_worker_request",
        ): frozenset({"_supervisor_preflight"}),
        ("mdcp.temporal.formal_worker_protocol", "launch_profile_sha256"): frozenset(
            {"_supervisor_preflight"}
        ),
        ("mdcp.temporal.formal_worker_protocol", "worker_request_sha256"): frozenset(
            {"_supervisor_preflight"}
        ),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FORMAL_WORKER_TERMINATION_WAIT_SECONDS",
        ): frozenset({"_run_fixed_worker_transport"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FORMAL_WORKER_TIMEOUT_SECONDS",
        ): frozenset({"_run_fixed_worker_transport"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "MAX_WORKER_MESSAGE_BYTES",
        ): frozenset({"_run_fixed_worker_transport"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "WORKER_STDOUT_PROBE_BYTES",
        ): frozenset({"_run_fixed_worker_transport"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "parse_formal_worker_response",
        ): frozenset({"_accept_worker_response"}),
    },
    "src/mdcp/temporal/formal_worker.py": {
        ("__future__", "annotations"): frozenset({None}),
        ("base64", "b64encode"): frozenset({"_encode_natural"}),
        ("ctypes", None): frozenset({None}),
        ("ctypes", "wintypes"): frozenset({None}),
        ("dataclasses", "asdict"): frozenset({"_json_value"}),
        ("dataclasses", "dataclass"): frozenset({None}),
        ("dataclasses", "is_dataclass"): frozenset({"_json_value"}),
        ("datetime", "datetime"): frozenset({"_fit_natural_request"}),
        ("hashlib", None): frozenset({None}),
        ("mdcp.common.canonical", "canonicalize_json"): frozenset(
            {
                "_validate_preconsumption",
                "_create_durable_marker",
                "_fit_natural_request",
                "_formalize_natural",
                "_encode_natural",
                "_complete_finalized_run",
            }
        ),
        ("mdcp.common.canonical", "parse_json_bytes"): frozenset(
            {"_validate_preconsumption", "_formalize_natural", "_execute_natural_run"}
        ),
        ("mdcp.common.digests", "sha256_hex"): frozenset(
            {
                "_fit_natural_request",
                "_formalize_natural",
                "_encode_natural",
                "_execute_natural_run",
                "_complete_finalized_run",
                "_response",
            }
        ),
        ("mdcp.common.enums", "GateVerdict"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal", "run_evidence"): frozenset({"_encode_natural"}),
        ("mdcp.temporal.completeness", "AdapterOutcome"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.completeness", "LabelOutcome"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.completeness", "PredictionOutcome"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.folds", "load_fold_specs"): frozenset({"_execute_natural_run"}),
        ("mdcp.temporal.folds", "materialize_folds"): frozenset({"_execute_natural_run"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FORMAL_WORKER_SOURCE_PATHS",
        ): frozenset({"_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FormalRunAuthorization",
        ): frozenset({"_validate_preconsumption"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FormalWorkerPrivateIdentity",
        ): frozenset({"_response"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FormalWorkerResponse",
        ): frozenset({"_response"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "FormalWorkerSourceEntry",
        ): frozenset({"_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "MAX_WORKER_MESSAGE_BYTES",
        ): frozenset({"main"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "PRIVATE_LOGICAL_OUTPUTS",
        ): frozenset({"_validate_preconsumption"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SEARCH_SOURCE_PATHS",
        ): frozenset({"_validate_preconsumption"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SearchEvidenceIndex",
        ): frozenset({"_validate_preconsumption"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SearchReceipt",
        ): frozenset({"_validate_preconsumption"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "SearchSourceEntry",
        ): frozenset({"_validate_preconsumption"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "encode_formal_worker_response",
        ): frozenset({"_emit_response"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "formal_worker_inventory_sha256",
        ): frozenset({"_source_inventory"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "launch_profile_sha256",
        ): frozenset({"_response", "main"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "parse_formal_worker_request",
        ): frozenset({"main"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "search_source_inventory_sha256",
        ): frozenset({"_validate_preconsumption"}),
        (
            "mdcp.temporal.formal_worker_protocol",
            "worker_request_sha256",
        ): frozenset({"_complete_finalized_run", "_response"}),
        ("mdcp.temporal.run_evidence", "FormalDevelopmentSeal"): frozenset(
            {"_complete_finalized_run"}
        ),
        ("mdcp.temporal.run_evidence", "PrivateFoldEvidence"): frozenset({"_formalize_natural"}),
        ("mdcp.temporal.run_evidence", "PublicDevelopmentResult"): frozenset(
            {"_formalize_natural"}
        ),
        ("mdcp.temporal.runner", "DevelopmentFoldResult"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.runner", "DevelopmentRunBundle"): frozenset({"_formalize_natural"}),
        ("mdcp.temporal.runner", "DevelopmentStateMachine"): frozenset({"_execute_natural_run"}),
        ("mdcp.temporal.runner", "EXACT_FOLD_IDS"): frozenset(
            {"_formalize_natural", "_execute_natural_run"}
        ),
        ("mdcp.temporal.runner", "EXACT_TRIAL_IDS"): frozenset(
            {"_formalize_natural", "_execute_natural_run"}
        ),
        ("mdcp.temporal.runner", "FitPhase"): frozenset({"_formalize_natural"}),
        ("mdcp.temporal.runner", "_formal_groups"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.runtime_guards", "RuntimeStage"): frozenset(
            {"_complete_finalized_run", "_execute_natural_run"}
        ),
        (
            "mdcp.temporal.runtime_guards",
            "build_worker_runtime_guard",
        ): frozenset({"_execute_natural_run"}),
        ("mdcp.temporal.trials", "_feature_names"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.trials", "_materialize_features"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.trials", "build_estimator"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.trials", "canonical_trial_identity"): frozenset({"_fit_natural_request"}),
        ("mdcp.temporal.trials", "load_trial_specs"): frozenset({"_execute_natural_run"}),
        ("mdcp.temporal.trials", "training_rows_for_trial"): frozenset({"_fit_natural_request"}),
        ("mdcp.workload.dataset", "load_uci_development_archive"): frozenset(
            {"_execute_natural_run"}
        ),
        ("mdcp.workload.splits", "split_development_rows"): frozenset({"_execute_natural_run"}),
        ("os", None): frozenset({None}),
        ("pathlib", "Path"): frozenset({None}),
        ("shutil", None): frozenset({None}),
        ("stat", None): frozenset({None}),
        ("sys", None): frozenset({None}),
        ("unicodedata", None): frozenset({None}),
    },
}
_FORMAL_MODULE_ATTRIBUTE_ALLOWLIST = {
    "src/mdcp/predictor/app_v2.py": frozenset(
        {"json.loads", "math.isfinite", "os.environ", "os.getenv"}
    ),
    "src/mdcp/temporal/adapter.py": frozenset(
        {"math.cos", "math.isfinite", "math.pi", "math.sin", "re.compile"}
    ),
    "src/mdcp/temporal/completeness.py": frozenset({"math.isfinite"}),
    "src/mdcp/temporal/evaluation.py": frozenset({"math.isclose", "math.isfinite"}),
    "src/mdcp/temporal/selection.py": frozenset({"math.isfinite"}),
    "src/mdcp/temporal/evidence.py": frozenset({"re.IGNORECASE", "re.MULTILINE", "re.compile"}),
    _TRUSTED_FIREWALL_PATH: frozenset(
        {
            "ast.AST",
            "ast.Assign",
            "ast.Attribute",
            "ast.AsyncFunctionDef",
            "ast.BinOp",
            "ast.Call",
            "ast.ClassDef",
            "ast.Constant",
            "ast.Del",
            "ast.Div",
            "ast.ExceptHandler",
            "ast.Expr",
            "ast.For",
            "ast.FunctionDef",
            "ast.Global",
            "ast.IfExp",
            "ast.Import",
            "ast.ImportFrom",
            "ast.Is",
            "ast.List",
            "ast.Lambda",
            "ast.Load",
            "ast.Add",
            "ast.Compare",
            "ast.MatchAs",
            "ast.MatchMapping",
            "ast.MatchStar",
            "ast.Name",
            "ast.Nonlocal",
            "ast.Starred",
            "ast.Store",
            "ast.Sub",
            "ast.Subscript",
            "ast.Tuple",
            "ast.arg",
            "ast.dump",
            "ast.expr",
            "ast.iter_child_nodes",
            "ast.parse",
            "ast.walk",
            "pandas.DataFrame",
            "pandas.read_csv",
            "re.compile",
            "sys.getprofile",
            "sys.setprofile",
            "tokenize.detect_encoding",
        }
    ),
    "src/mdcp/temporal/folds.py": frozenset(
        {"pandas.DataFrame", "pandas.DatetimeIndex", "pandas.Timestamp", "pandas.concat"}
    ),
    "src/mdcp/temporal/golden_vectors.py": frozenset(
        {"hashlib.sha256", "math.isfinite", "struct.error", "struct.pack"}
    ),
    "src/mdcp/temporal/trials.py": frozenset(
        {
            "numpy.any",
            "numpy.asarray",
            "numpy.isfinite",
            "numpy.maximum",
            "numpy.mean",
            "numpy.ndarray",
            "numpy.std",
            "pandas.DataFrame",
            "pandas.DatetimeIndex",
            "pandas.Timedelta",
            "pandas.Timestamp",
        }
    ),
    "src/mdcp/temporal/runtime_guards.py": frozenset(
        {
            "ctypes.POINTER",
            "ctypes.Structure",
            "ctypes.byref",
            "ctypes.c_int",
            "ctypes.c_size_t",
            "ctypes.c_ulong",
            "ctypes.c_void_p",
            "ctypes.sizeof",
            "ctypes.windll",
            "ctypes.windll.kernel32",
            "ctypes.windll.kernel32.GetCurrentProcess",
            "ctypes.windll.psapi",
            "ctypes.windll.psapi.GetProcessMemoryInfo",
            "hashlib.sha256",
            "os.environ",
            "os.fsdecode",
            "os.fsencode",
            "os.readlink",
            "stat.S_ISREG",
            "subprocess.run",
            "sys.platform",
            "sys.platform.startswith",
            "time.monotonic_ns",
        }
    ),
    "src/mdcp/temporal/cli.py": frozenset(
        {
            "argparse.ArgumentParser",
            "argparse.Namespace",
            "datetime.fromisoformat",
            "os.environ",
            "os.getenv",
            "mdcp.temporal.run_evidence.FormalDevelopmentOutcome",
            "mdcp.temporal.run_evidence.FormalDevelopmentRequest",
            "mdcp.temporal.run_evidence.execute_authorized_formal_development",
            "pathlib.Path.cwd",
            "sys.stdout",
            "sys.stdout.buffer",
            "sys.stdout.buffer.flush",
            "sys.stdout.buffer.write",
            "sys.stdout.flush",
            "sys.stdout.write",
        }
    ),
    "src/mdcp/temporal/runner.py": frozenset(
        {
            "datetime.fromisoformat",
            "math.isfinite",
            "os.name",
            "pathlib.Path.cwd",
            "stat.S_ISDIR",
        }
    ),
    "src/mdcp/temporal/search_identity.py": frozenset(
        {
            "json.loads",
            "os.name",
            "os.close",
            "os.O_CREAT",
            "os.O_EXCL",
            "os.O_WRONLY",
            "os.lstat",
            "os.open",
            "os.write",
            "pathlib.Path.cwd",
            "pathlib.Path.exists",
            "pathlib.Path.mkdir",
            "pathlib.Path.read_bytes",
            "pathlib.Path.resolve",
            "stat.S_ISDIR",
            "stat.S_ISREG",
            "stat.FILE_ATTRIBUTE_REPARSE_POINT",
            "subprocess.run",
        }
    ),
    "src/mdcp/temporal/run_evidence.py": frozenset(
        {
            "base64.b64decode",
            "base64.b64encode",
            "ctypes.POINTER",
            "ctypes.Structure",
            "ctypes.Union",
            "ctypes.byref",
            "ctypes.c_int",
            "ctypes.c_size_t",
            "ctypes.c_void_p",
            "ctypes.create_string_buffer",
            "ctypes.create_unicode_buffer",
            "ctypes.cast",
            "ctypes.pointer",
            "ctypes.sizeof",
            "ctypes.windll",
            "ctypes.windll.kernel32",
            "ctypes.windll.kernel32.CloseHandle",
            "ctypes.windll.kernel32.CreateFileW",
            "ctypes.windll.kernel32.GetFileInformationByHandle",
            "ctypes.windll.kernel32.ReadFile",
            "windll.kernel32",
            "windll.kernel32.CloseHandle",
            "windll.kernel32.CompareStringOrdinal",
            "windll.kernel32.CreateFileW",
            "windll.kernel32.FlushFileBuffers",
            "windll.kernel32.GetFileInformationByHandle",
            "windll.kernel32.GetFinalPathNameByHandleW",
            "windll.kernel32.GetLastError",
            "windll.kernel32.SetFileInformationByHandle",
            "windll.kernel32.WriteFile",
            "windll.ntdll",
            "windll.ntdll.NtCreateFile",
            "ctypes.wintypes.BOOL",
            "ctypes.wintypes.DWORD",
            "ctypes.wintypes.FILETIME",
            "ctypes.wintypes.HANDLE",
            "ctypes.wintypes.LONG",
            "ctypes.wintypes.LPCWSTR",
            "ctypes.wintypes.LPWSTR",
            "ctypes.wintypes.ULONG",
            "ctypes.wintypes.USHORT",
            "json.JSONDecodeError",
            "json.loads",
            "math.isfinite",
            "os.environ",
            "os.fsdecode",
            "os.name",
            "os.O_NOFOLLOW",
            "os.O_NONBLOCK",
            "os.O_RDONLY",
            "os.close",
            "os.fstat",
            "os.open",
            "os.read",
            "stat.S_ISDIR",
            "stat.S_ISREG",
            "subprocess.DEVNULL",
            "subprocess.PIPE",
            "subprocess.Popen",
            "subprocess.run",
            "sys.executable",
            "sys.version_info",
            "time.monotonic",
            "unicodedata.normalize",
        }
    ),
    "src/mdcp/temporal/formal_worker.py": frozenset(
        {
            "ctypes.POINTER",
            "ctypes.Structure",
            "ctypes.Union",
            "ctypes.byref",
            "ctypes.c_int",
            "ctypes.c_size_t",
            "ctypes.c_void_p",
            "ctypes.cast",
            "ctypes.create_string_buffer",
            "ctypes.create_unicode_buffer",
            "ctypes.pointer",
            "ctypes.sizeof",
            "ctypes.windll",
            "ctypes.windll.kernel32",
            "ctypes.windll.kernel32.CloseHandle",
            "ctypes.windll.kernel32.CompareStringOrdinal",
            "ctypes.windll.kernel32.CreateFileW",
            "ctypes.windll.kernel32.FlushFileBuffers",
            "ctypes.windll.kernel32.GetFileInformationByHandle",
            "ctypes.windll.kernel32.GetFinalPathNameByHandleW",
            "ctypes.windll.kernel32.GetLastError",
            "ctypes.windll.kernel32.WriteFile",
            "ctypes.windll.ntdll",
            "ctypes.windll.ntdll.NtCreateFile",
            "ctypes.wintypes.BOOL",
            "ctypes.wintypes.DWORD",
            "ctypes.wintypes.FILETIME",
            "ctypes.wintypes.HANDLE",
            "ctypes.wintypes.LONG",
            "ctypes.wintypes.LPCWSTR",
            "ctypes.wintypes.LPWSTR",
            "ctypes.wintypes.ULONG",
            "ctypes.wintypes.USHORT",
            "hashlib.sha256",
            "os.O_CREAT",
            "os.O_EXCL",
            "os.O_WRONLY",
            "os.close",
            "os.environ",
            "os.fstat",
            "os.fsync",
            "os.open",
            "os.write",
            "pathlib.Path.cwd",
            "shutil.which",
            "stat.S_ISDIR",
            "stat.S_ISREG",
            "sys.argv",
            "sys.dont_write_bytecode",
            "sys.executable",
            "sys.flags",
            "sys.flags.isolated",
            "sys.flags.no_site",
            "sys.path",
            "sys.path.insert",
            "sys.stdin",
            "sys.stdin.buffer",
            "sys.stdin.buffer.read",
            "sys.stdout",
            "sys.stdout.buffer",
            "sys.stdout.buffer.flush",
            "sys.stdout.buffer.write",
            "sys.version_info",
            "unicodedata.normalize",
        }
    ),
}
_FILE_ACCESS_METHODS = frozenset(
    {
        "open",
        "read",
        "read1",
        "read_bytes",
        "read_csv",
        "read_text",
        "readinto",
        "readinto1",
        "readline",
        "readlines",
        "lstat",
        "write",
        "write_bytes",
        "write_text",
        "writelines",
    }
)
_ALLOWED_FILE_ACCESS_CALLS = {
    "src/mdcp/predictor/app_v2.py": frozenset(
        {("runtime_from_environment", "read_text", "name:descriptor_path")}
    ),
    "src/mdcp/temporal/contract_gate.py": frozenset(
        {
            ("_checked_json", "read_bytes", "name:path"),
            ("_path_digest", "read_bytes", "name:path"),
        }
    ),
    _TRUSTED_FIREWALL_PATH: frozenset(
        {
            ("_implementation_sha256", "read_bytes", "Path:code.co_filename"),
            ("audit_static_h2_firewall", "read_bytes", "Path:__file__"),
            ("audit_static_h2_firewall", "read_bytes", "name:source_path"),
            ("run_behavioral_h2_firewall", "read_bytes", "Path:__file__"),
        }
    ),
    "src/mdcp/temporal/golden_vectors.py": frozenset(
        {("verify_golden_vector_manifest", "read_bytes", "name:path")}
    ),
    "src/mdcp/temporal/runtime_guards.py": frozenset(
        {
            ("_linux_peak_process_bytes", "read_text", "Path:/proc/self/status"),
            ("_repository_inventory", "read_bytes", "name:working_path"),
            ("_formal_worker_source_inventory", "lstat", "name:path"),
            ("_formal_worker_source_inventory", "read_bytes", "name:path"),
            ("_worker_source_inventory", "lstat", "name:path"),
            ("_worker_source_inventory", "read_bytes", "name:path"),
        }
    ),
    "src/mdcp/temporal/search_identity.py": frozenset(
        {
            ("_parse_formal_authorization", "read_text", "name:_FORMAL_AUTHORIZATION_SCHEMA_PATH"),
            ("_bound_digests_recompute", "read_bytes", "Path:root/relative_path"),
            ("_read_expected_public_file", "read_bytes", "name:expected_path"),
            ("_read_regular_nonlink_file", "lstat", "name:os"),
            ("_read_regular_nonlink_file", "read_bytes", "name:path"),
            ("prepare_search_freeze", "read_bytes", "Path:root/path"),
            ("_publish_no_clobber", "open", "name:os"),
            ("_publish_no_clobber", "write", "name:os"),
        }
    ),
    "src/mdcp/temporal/cli.py": frozenset({("main", "write", None)}),
    "src/mdcp/temporal/run_evidence.py": frozenset(
        {
            ("_canonical_existing_path", "lstat", "name:path"),
            ("_read_private_container_posix", "open", "name:os"),
            (
                "_checked_in_schema",
                "read_text",
                "Path:schemas/v2/development-result-index.schema.json",
            ),
            ("verify_development_result", "read_bytes", "name:path"),
            ("_read_private_container_posix", "read", "name:os"),
            ("_recovery_leaf", "lstat", "name:path"),
            ("read_response", "read", "attr:process.stdout"),
            ("write_request", "write", "attr:process.stdin"),
        }
    ),
    "src/mdcp/temporal/formal_worker.py": frozenset(
        {
            ("_canonical_path", "lstat", "name:path"),
            ("_hash_archive", "open", "name:path"),
            ("_hash_archive", "read", "name:source"),
            ("_read_regular", "read_bytes", "name:checked"),
            ("_read_regular", "lstat", "name:checked"),
            ("_source_inventory", "read_bytes", "name:path"),
            ("_validate_preconsumption", "read_bytes", "name:path"),
            ("_validate_preconsumption", "lstat", "name:archive_path"),
            ("_emit_response", "write", "attr:sys.stdout.buffer"),
            ("main", "read", "attr:sys.stdin.buffer"),
        }
    ),
}
_ALLOWED_ENVIRONMENT_KEYS = {
    "src/mdcp/predictor/app_v2.py": frozenset(
        {
            "MDCP_DESCRIPTOR_PATH",
            "MDCP_ONNX_PATH",
            "MDCP_RELEASE_ID",
            "MDCP_ROUTE_REVISION",
        }
    ),
    "src/mdcp/temporal/cli.py": frozenset(
        {
            "BLIS_NUM_THREADS",
            "LOKY_MAX_CPU_COUNT",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
            "MDCP_FORMAL_RUN_AUTHORIZATION",
            "MDCP_FORMAL_RUN_CONSUMPTION_ROOT",
            "MDCP_UCI_ARCHIVE",
            "MDCP_V02_PRIVATE_CONTAINER",
        }
    ),
    "src/mdcp/temporal/run_evidence.py": frozenset({"SYSTEMROOT", "WINDIR"}),
    "src/mdcp/temporal/formal_worker.py": frozenset({"SYSTEMROOT", "WINDIR"}),
}
_CLI_THREAD_ENVIRONMENT_KEYS = frozenset(
    {
        "BLIS_NUM_THREADS",
        "LOKY_MAX_CPU_COUNT",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    }
)
_PROTECTED_PATH_PARAMETER_FUNCTIONS = {
    "src/mdcp/temporal/contract_gate.py": frozenset({"_checked_json", "_path_digest"}),
    "src/mdcp/temporal/golden_vectors.py": frozenset({"verify_golden_vector_manifest"}),
}
_PINNED_FILE_CAPABILITY_FUNCTIONS = {
    "src/mdcp/predictor/app_v2.py": {
        "runtime_from_environment": (
            "1e0beb1151f8323d21c1d79f3a3a3a04d682786198c355d157d32921584628f8"
        )
    },
    "src/mdcp/temporal/cli.py": {
        "build_parser": "efb9630bc0c7c5fb868d1887a6cac04bfbb720c1d4910bc4b875c866f8528e4f",
        "main": "88e8ab0f5b5cbd355a01cb22fed0dd0e271c09becc0a1e12a75635ac40cf6122",
    },
    "src/mdcp/temporal/contract_gate.py": {
        "_checked_json": "e4508a7b837471a78db8ffc3873c055315f5392b033c59f100e6935e57d59214",
        "_check_golden_vector_inventory": (
            "55c7cdf79b7afd77932a12f26627bda42585dc3fe562699aeaec5a6fe5890b09"
        ),
        "_check_v2_schemas": ("5252e5cfe101bd51573cc6a52bec695762f05182972eba6f6913b3aa58a39642"),
        "_path_digest": "306b3c291c806ed597a75f69d52400f9a0850e6c3ef3196e33e287169d8d1195",
    },
    "src/mdcp/temporal/firewall.py": {
        "_canonical_utf8_source": (
            "7b12f7345a7f783e6dc9eaca37272ce950378f2a5a3ff4a8ad8b627adcd54614"
        ),
        "_implementation_sha256": (
            "def57863c42ba3e307708387ad0444828a184aca2b4cb2cd22024dc3ae53908d"
        ),
        "audit_static_h2_firewall": (
            "68dcffab9f0d9f8a61231bd8a8cb3c838401e9e438e53fcde62deee7db88f880"
        ),
        "run_behavioral_h2_firewall": (
            "3b9fda1edda8772d9c0cb9abe55bf83fa0f9f80dc20dae5e9e43c9e9d4adbe92"
        ),
    },
    "src/mdcp/temporal/evidence.py": {
        "_key_violation": ("0b46472b463cab894ac9582c2db4bff1171c6099d48c7d3e678754506a008866"),
        "public_evidence_violations": (
            "433cc57f76d0eddab71cda6acc0221de15b5d8b88b9179a8ab481b33af9ab59f"
        ),
    },
    "src/mdcp/temporal/golden_vectors.py": {
        "verify_golden_vector_manifest": (
            "a3afbe4051812bfcd039d7171f839e2395865288daf457b75c590f7fee4e3994"
        )
    },
}
_PINNED_FILE_CAPABILITY_MODULES = {
    "src/mdcp/predictor/app_v2.py": (
        "2b5af76e338af04c5a1e44ddb63ac0882a9242e752b9fdfd7aa5088d74ef49c7"
    ),
    "src/mdcp/temporal/contract_gate.py": (
        "971feef355fc7c9767d6ab496e7b69ca525e8487de2daf7a3195012398073a4e"
    ),
    "src/mdcp/temporal/golden_vectors.py": (
        "a5b6458b522bc43e1a64925118d8c9617377cada5955dd214271d0c59dedf490"
    ),
    "src/mdcp/temporal/formal_worker.py": (
        "3e9312f5f55fb5be20cc1921c8b3ea60c5b03bfc0be8dd6ae6f483360a15ee70"
    ),
    "src/mdcp/temporal/runner.py": (
        "81334542d1aceb0bb00edfcc1b4d31dac68824223866fa4d38954bb33c8483e9"
    ),
    "src/mdcp/temporal/runtime_guards.py": (
        "f27d267ac1418c4feacdd8522c4f68a9517583a442adc78a8e3124b8bad7d7cd"
    ),
}
_ALLOWED_PRIVATE_ATTRIBUTES = {
    "src/mdcp/temporal/runtime_guards.py": frozenset(
        {
            "_expected_head",
            "_fields_",
            "_monotonic_ns",
            "_peak_process_bytes",
            "_repository_inventory_sha256",
            "_repository_root",
            "_start_ns",
            "_tracked_paths",
            "_unknown",
            "_core",
        }
    ),
    "src/mdcp/temporal/formal_worker.py": frozenset(
        {
            "_PrivateContainer",
            "_PrivateContainerEntry",
            "_inventory_core",
            "_manifest_core",
            "_raw_paths",
            "_validated_private_files",
        }
    ),
    "src/mdcp/temporal/runner.py": frozenset(
        {
            "_baseline",
            "_finalized",
            "_ledger",
            "_outstanding",
            "_private_folds",
            "_processed_selection",
            "_provisional",
            "_qualifications",
            "_record_replay_result",
            "_record_selection_result",
            "_records",
            "_replay",
            "_replay_digests",
            "_reports",
            "_require_active",
            "_selection",
            "_selection_bound",
            "_session",
        }
    ),
    "src/mdcp/temporal/run_evidence.py": frozenset({"_raw_paths"}),
}
_ALLOWED_SUBPROCESS_CALLS = {
    "src/mdcp/temporal/runtime_guards.py": {
        "_repository_head": ("git", "rev-parse", "HEAD"),
        "_repository_is_dirty": ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        "_tracked_paths": ("git", "ls-tree", "-r", "-z", "--name-only", "name:expected_head"),
    },
    "src/mdcp/temporal/run_evidence.py": {
        "_git_bytes": ("git", "name:arguments"),
    },
}
_ALLOWED_RUN_EVIDENCE_GIT_CALLS = {
    "_repository_snapshot": frozenset(
        {
            ("rev-parse", "--show-toplevel"),
            ("rev-parse", "HEAD"),
            ("status", "--porcelain=v1", "--untracked-files=all"),
            ("remote",),
            ("tag", "--points-at", "HEAD"),
            ("ls-tree", "-r", "-z", "--name-only", "name:expected_head"),
        }
    ),
    "_verified_search_freeze_topology": frozenset(
        {
            ("show", "-s", "--format=%P", "name:expected_head"),
            (
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                "name:expected_head",
            ),
            ("ls-tree", "name:expected_head", "--", "name:SEARCH_SOURCE_PATHS"),
        }
    ),
}
_ALLOWED_SEARCH_IDENTITY_GIT_CALLS = {
    "verify_search_freeze": frozenset(
        {
            ("rev-parse", "HEAD"),
            ("remote",),
            ("show", "-s", "--format=%P", "HEAD"),
            ("tag", "--points-at", "HEAD"),
        }
    ),
    "prepare_search_freeze": frozenset({("rev-parse", "HEAD")}),
    "_has_exact_search_source_modes": frozenset(
        {("ls-files", "-s", "--", "name:SEARCH_SOURCE_PATHS")}
    ),
    "_has_exact_search_source_head_modes": frozenset(
        {("ls-tree", "name:head", "--", "name:SEARCH_SOURCE_PATHS")}
    ),
    "_is_clean_checkout": frozenset({("status", "--porcelain=v1", "--untracked-files=all")}),
    "_has_exact_allowlisted_additions": frozenset(
        {("diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD")}
    ),
    "_has_regular_public_evidence": frozenset(
        {("ls-tree", "name:head", "--", "name:relative_path")}
    ),
}
_SENSITIVE_FILE_CALLABLE_SCOPES = {
    "src/mdcp/temporal/contract_gate.py": {
        "_checked_json": "_check_v2_schemas",
        "_path_digest": "_check_v2_schemas",
        "mdcp.temporal.golden_vectors.verify_golden_vector_manifest": (
            "_check_golden_vector_inventory"
        ),
    }
}
_RESERVED_BINDING_NAMES = frozenset({"__file__"})
_FAILURE_REASON = "H2_IMPORT_CAPABILITY_FORBIDDEN"
_BEHAVIORAL_FAILURE_REASON = "BEHAVIORAL_H2_FIREWALL_FAILED"
_FORBIDDEN_CALL_REASON = "FORBIDDEN_CAPABILITY_CALLED"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DEVELOPMENT_ROWS = 13_003
_TRAIN_ROWS = 8_645
_H1_ROWS = 4_358

_BOUNDED_LOADER = load_uci_development_archive
_DEVELOPMENT_SPLITTER = split_development_rows
_FORBIDDEN_CALL_IDENTITIES = {
    (_BOUNDED_LOADER.__code__.co_filename, "load_uci_archive"): "load_uci_archive",
    (_DEVELOPMENT_SPLITTER.__code__.co_filename, "split_rows"): "split_rows",
    (_DEVELOPMENT_SPLITTER.__code__.co_filename, "open_h2"): "DatasetPartitions.open_h2",
}

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def _strict_zero(value: object) -> object:
    if type(value) is not int or value != 0:
        raise ValueError("forbidden call count must be integer zero")
    return value


StrictZero = Annotated[Literal[0], BeforeValidator(_strict_zero)]
ForbiddenCallCounts = with_config(ConfigDict(extra="forbid"))(
    TypedDict(
        "ForbiddenCallCounts",
        {
            "load_uci_archive": StrictZero,
            "split_rows": StrictZero,
            "DatasetPartitions.open_h2": StrictZero,
        },
    )
)


@dataclass(frozen=True)
class ImportBinding:
    local_name: str
    qualified_name: str


@dataclass(frozen=True)
class StaticFirewallResult:
    schema_version: Literal["mdcp.static-h2-firewall.v1"]
    verdict: Literal["PASS"]
    checked_paths: tuple[str, ...]
    implementation_sha256: str


class StaticFirewallError(ValueError):
    def __init__(self, reason_code: str = _FAILURE_REASON) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class BehavioralFirewallError(RuntimeError):
    def __init__(self, reason_code: str = _BEHAVIORAL_FAILURE_REASON) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@pydantic_dataclass(config=ConfigDict(extra="forbid", frozen=True))
class DevelopmentBoundaryResult:
    schema_version: Literal["mdcp.development-boundary.v1"]
    verdict: Literal["PASS"]
    archive_sha256: Sha256
    development_row_count: Literal[13_003]
    development_rows_sha256: Sha256
    train_row_count: Literal[8_645]
    train_rows_sha256: Sha256
    h1_row_count: Literal[4_358]
    h1_rows_sha256: Sha256
    read_csv_nrows: tuple[Literal[13_003]]
    forbidden_call_counts: ForbiddenCallCounts
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]


@pydantic_dataclass(config=ConfigDict(extra="forbid", frozen=True))
class BehavioralFirewallBody:
    schema_version: Literal["mdcp.behavioral-h2-firewall.v1"]
    verdict: Literal["PASS"]
    fixture_recipe_sha256: Sha256
    development_boundary: DevelopmentBoundaryResult
    static_firewall_implementation_sha256: Sha256
    behavioral_firewall_implementation_sha256: Sha256
    bounded_loader_implementation_sha256: Sha256
    development_split_implementation_sha256: Sha256


@pydantic_dataclass(config=ConfigDict(extra="forbid", frozen=True))
class BehavioralFirewallResult:
    body: BehavioralFirewallBody
    behavioral_result_sha256: Sha256


def _fail() -> None:
    raise StaticFirewallError()


def _canonical_utf8_source(raw_source: bytes) -> str:
    raw_lines = raw_source.splitlines(keepends=True)
    line_index = 0

    def read_line() -> bytes:
        nonlocal line_index
        if line_index >= len(raw_lines):
            return b""
        line = raw_lines[line_index]
        line_index += 1
        return line

    try:
        encoding, _ = tokenize.detect_encoding(read_line)
    except (SyntaxError, UnicodeError):
        _fail()
    if encoding != "utf-8" or raw_source.startswith(_UTF8_BOM):
        _fail()
    for line in raw_lines[:2]:
        cookie = _ENCODING_COOKIE_PATTERN.match(line)
        if cookie is not None and cookie.group(1) != b"utf-8":
            _fail()
    try:
        return raw_source.decode("utf-8")
    except UnicodeDecodeError:
        _fail()


def _is_forbidden_module(qualified_name: str) -> bool:
    return any(
        qualified_name == module or qualified_name.startswith(f"{module}.")
        for module in _FORBIDDEN_MODULES
    )


def _attribute_name(node: ast.expr, bindings: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        qualified_name = node.id
        seen: set[str] = set()
        while qualified_name in bindings:
            if qualified_name in seen:
                return None
            seen.add(qualified_name)
            next_name = bindings[qualified_name]
            if next_name == qualified_name:
                return qualified_name
            qualified_name = next_name
        return qualified_name
    if isinstance(node, ast.Attribute):
        parent = _attribute_name(node.value, bindings)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _allowed_dunder_attribute(
    node: ast.Attribute,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if node.attr == "__init__":
        return (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "super"
            and not node.value.args
            and not node.value.keywords
        )
    if node.attr == "__setattr__" and logical_path == "src/mdcp/temporal/runtime_guards.py":
        parent = parents.get(node)
        return (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "super"
            and not node.value.args
            and not node.value.keywords
            and isinstance(parent, ast.Call)
            and parent.func is node
            and len(parent.args) == 2
            and not parent.keywords
            and isinstance(parent.args[0], ast.Constant)
            and parent.args[0].value == "_core"
            and isinstance(parent.args[1], ast.Name)
            and parent.args[1].id == "core"
            and _enclosing_function(node, parents) == "__init__"
        )
    if node.attr == "__module__" and logical_path == "src/mdcp/temporal/contract_gate.py":
        return isinstance(node.value, ast.Name) and node.value.id in {
            "create_v1_app",
            "create_v2_app",
        }
    if node.attr == "__code__" and logical_path == _TRUSTED_FIREWALL_PATH:
        return isinstance(node.value, ast.Name) and node.value.id in {
            "_BOUNDED_LOADER",
            "_DEVELOPMENT_SPLITTER",
            "function",
        }
    if (
        node.attr == "__setattr__"
        and logical_path == "src/mdcp/temporal/folds.py"
        and isinstance(node.value, ast.Name)
        and node.value.id == "object"
    ):
        call = parents.get(node)
        if not (
            isinstance(call, ast.Call)
            and call.func is node
            and len(call.args) == 3
            and not call.keywords
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == "self"
            and isinstance(call.args[1], ast.Constant)
            and isinstance(call.args[1].value, str)
            and call.args[1].value
            in {"train_start", "train_end", "validation_start", "validation_end"}
            and isinstance(call.args[2], ast.Name)
            and call.args[2].id == call.args[1].value
        ):
            return False
        function = parents.get(call)
        while function is not None and not isinstance(function, ast.FunctionDef):
            function = parents.get(function)
        return (
            isinstance(function, ast.FunctionDef)
            and function.name == "__post_init__"
            and isinstance(parents.get(function), ast.ClassDef)
            and parents[function].name == "FoldSpec"
        )
    return False


def _enclosing_function(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> str | None:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef):
            return current.name
        current = parents.get(current)
    return None


def _protected_path_scope(
    node: ast.AST,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> str | None:
    protected_functions = _PROTECTED_PATH_PARAMETER_FUNCTIONS.get(logical_path, frozenset())
    current = parents.get(node)
    while current is not None:
        if (
            isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef)
            and current.name in protected_functions
        ):
            return current.name
        current = parents.get(current)
    return None


def _has_exact_path_parameter(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    arguments = node.args
    positional = (*arguments.posonlyargs, *arguments.args)
    return (
        len(positional) == 1
        and positional[0].arg == "path"
        and not arguments.defaults
        and not arguments.kwonlyargs
        and not arguments.kw_defaults
        and arguments.vararg is None
        and arguments.kwarg is None
    )


def _validate_pinned_file_capability_functions(tree: ast.AST, logical_path: str) -> None:
    expected_module_sha256 = _PINNED_FILE_CAPABILITY_MODULES.get(logical_path)
    if expected_module_sha256 is not None:
        normalized_module = ast.dump(tree, include_attributes=False).encode("utf-8")
        if sha256_hex(normalized_module) != expected_module_sha256:
            _fail()
    expected_functions = _PINNED_FILE_CAPABILITY_FUNCTIONS.get(logical_path, {})
    for function_name, expected_sha256 in expected_functions.items():
        matches = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == function_name
        ]
        if len(matches) != 1:
            _fail()
        normalized = ast.dump(matches[0], include_attributes=False).encode("utf-8")
        if sha256_hex(normalized) != expected_sha256:
            _fail()


def _file_receiver_identity(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return f"name:{node.id}"
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.left, ast.Name)
        and isinstance(node.right, ast.Name)
    ):
        return f"Path:{node.left.id}/{node.right.id}"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and len(node.args) == 1
        and not node.keywords
    ):
        argument = node.args[0]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            return f"Path:{argument.value}"
        if isinstance(argument, ast.Name) and argument.id == "__file__":
            return "Path:__file__"
        if (
            isinstance(argument, ast.Attribute)
            and argument.attr == "co_filename"
            and isinstance(argument.value, ast.Name)
            and argument.value.id == "code"
        ):
            return "Path:code.co_filename"
    return None


def _allowed_file_access_call(
    node: ast.Call,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if not isinstance(node.func, ast.Attribute):
        return False
    receiver_identity = _file_receiver_identity(node.func.value)
    if receiver_identity is None and logical_path in {
        "src/mdcp/temporal/formal_worker.py",
        "src/mdcp/temporal/run_evidence.py",
    }:
        attribute_identity = _simple_attribute_identity(node.func.value)
        receiver_identity = None if attribute_identity is None else f"attr:{attribute_identity}"
    identity = (
        _enclosing_function(node, parents),
        node.func.attr,
        receiver_identity,
    )
    return identity in _ALLOWED_FILE_ACCESS_CALLS.get(logical_path, frozenset())


def _allowed_file_source_name(
    node: ast.Name,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    if (
        logical_path == "src/mdcp/temporal/formal_worker.py"
        and node.id == "__file__"
        and isinstance(parent, ast.Call)
        and len(parent.args) == 1
        and parent.args[0] is node
        and not parent.keywords
        and isinstance(parent.func, ast.Name)
        and parent.func.id == "Path"
        and _enclosing_function(node, parents) == "_bootstrap_paths"
    ):
        return True
    if (
        logical_path != _TRUSTED_FIREWALL_PATH
        or node.id != "__file__"
        or not isinstance(parent, ast.Call)
        or len(parent.args) != 1
        or parent.args[0] is not node
        or parent.keywords
        or not isinstance(parent.func, ast.Name)
        or parent.func.id != "Path"
    ):
        return False
    attribute = parents.get(parent)
    call = parents.get(attribute) if isinstance(attribute, ast.Attribute) else None
    return (
        isinstance(attribute, ast.Attribute)
        and attribute.value is parent
        and attribute.attr == "read_bytes"
        and isinstance(call, ast.Call)
        and call.func is attribute
        and _allowed_file_access_call(call, logical_path, parents)
    )


def _allowed_sensitive_file_callable_reference(
    node: ast.expr,
    qualified_name: str,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    allowed_scope = _SENSITIVE_FILE_CALLABLE_SCOPES.get(logical_path, {}).get(qualified_name)
    parent = parents.get(node)
    return (
        allowed_scope is not None
        and isinstance(parent, ast.Call)
        and parent.func is node
        and _enclosing_function(node, parents) == allowed_scope
    )


def _allowed_pandas_reader_reference(
    node: ast.Attribute,
    bindings: dict[str, str],
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if _attribute_name(node, bindings) != "pandas.read_csv":
        return False
    parent = parents.get(node)
    if (
        not isinstance(parent, ast.Assign)
        or _enclosing_function(node, parents) != "run_development_boundary"
        or len(parent.targets) != 1
    ):
        return False
    target = parent.targets[0]
    if parent.value is node:
        return isinstance(target, ast.Name) and target.id == "previous_read_csv"
    if target is node:
        return isinstance(parent.value, ast.Name) and parent.value.id in {
            "bounded_read_csv",
            "previous_read_csv",
        }
    return False


def _allowed_previous_reader_reference(
    node: ast.Name,
    bindings: dict[str, str],
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1:
        target = parent.targets[0]
        if target is node:
            return (
                _enclosing_function(node, parents) == "run_development_boundary"
                and isinstance(parent.value, ast.Attribute)
                and _attribute_name(parent.value, bindings) == "pandas.read_csv"
            )
        if parent.value is node:
            return (
                _enclosing_function(node, parents) == "run_development_boundary"
                and isinstance(target, ast.Attribute)
                and _attribute_name(target, bindings) == "pandas.read_csv"
            )
    return (
        isinstance(parent, ast.Call)
        and parent.func is node
        and _enclosing_function(node, parents) == "bounded_read_csv"
        and len(parent.args) == 1
        and isinstance(parent.args[0], ast.Starred)
        and isinstance(parent.args[0].value, ast.Name)
        and parent.args[0].value.id == "args"
        and len(parent.keywords) == 1
        and parent.keywords[0].arg is None
        and isinstance(parent.keywords[0].value, ast.Name)
        and parent.keywords[0].value.id == "kwargs"
    )


def _constant_string(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _approved_descriptor_path_expression(
    node: ast.expr,
    bindings: dict[str, str],
) -> bool:
    if (
        not isinstance(node, ast.Call)
        or _attribute_name(node.func, bindings) != "pathlib.Path"
        or len(node.args) != 1
        or node.keywords
    ):
        return False
    source = node.args[0]
    return (
        isinstance(source, ast.Subscript)
        and _attribute_name(source.value, bindings) == "os.environ"
        and _constant_string(source.slice) == "MDCP_DESCRIPTOR_PATH"
    )


def _allowed_descriptor_path_reference(
    node: ast.Name,
    bindings: dict[str, str],
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if _enclosing_function(node, parents) != "runtime_from_environment":
        return False
    parent = parents.get(node)
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1 and parent.targets[0] is node:
        return _approved_descriptor_path_expression(parent.value, bindings)
    return (
        isinstance(parent, ast.Attribute)
        and parent.value is node
        and parent.attr == "read_text"
        and isinstance(parents.get(parent), ast.Call)
        and parents[parent].func is parent
        and _allowed_file_access_call(parents[parent], "src/mdcp/predictor/app_v2.py", parents)
    )


def _environment_access_allowed(
    node: ast.Attribute,
    qualified_name: str,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if logical_path == "src/mdcp/temporal/formal_worker.py" and qualified_name == "os.environ":
        parent = parents.get(node)
        return (
            isinstance(parent, ast.Call)
            and parent.args == [node]
            and not parent.keywords
            and isinstance(parent.func, ast.Name)
            and parent.func.id == "set"
            and _enclosing_function(node, parents)
            in {"_bootstrap_paths", "_validate_preconsumption"}
        )
    if (
        logical_path == "src/mdcp/temporal/run_evidence.py"
        and _enclosing_function(node, parents) != "_run_fixed_worker_transport"
    ):
        return False
    allowed_keys = _ALLOWED_ENVIRONMENT_KEYS.get(logical_path, frozenset())
    parent = parents.get(node)
    if qualified_name == "os.environ":
        if not isinstance(parent, ast.Subscript) or parent.value is not node:
            return False
        key = _constant_string(parent.slice)
        if key not in allowed_keys:
            return False
        if isinstance(parent.ctx, ast.Load):
            return True
        assignment = parents.get(parent)
        return (
            logical_path == "src/mdcp/temporal/cli.py"
            and key in _CLI_THREAD_ENVIRONMENT_KEYS
            and isinstance(parent.ctx, ast.Store)
            and isinstance(assignment, ast.Assign)
            and len(assignment.targets) == 1
            and assignment.targets[0] is parent
            and isinstance(assignment.value, ast.Constant)
            and assignment.value.value == "1"
            and _enclosing_function(parent, parents) is None
        )
    if qualified_name == "os.getenv":
        return (
            isinstance(parent, ast.Call)
            and parent.func is node
            and len(parent.args) == 1
            and not parent.keywords
            and _constant_string(parent.args[0]) in allowed_keys
        )
    return True


def _subprocess_argument_identity(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return f"name:{node.id}"
    return None


def _simple_attribute_identity(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _simple_attribute_identity(node.value)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _str_call_of(node: ast.expr, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "str"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == name
    )


def _fixed_worker_factory_assignment(node: ast.Assign) -> bool:
    if (
        len(node.targets) != 1
        or not isinstance(node.targets[0], ast.Name)
        or node.targets[0].id != "factory"
        or not isinstance(node.value, ast.IfExp)
    ):
        return False
    conditional = node.value
    return (
        isinstance(conditional.test, ast.Compare)
        and isinstance(conditional.test.left, ast.Name)
        and conditional.test.left.id == "_process_factory"
        and len(conditional.test.ops) == 1
        and isinstance(conditional.test.ops[0], ast.Is)
        and len(conditional.test.comparators) == 1
        and isinstance(conditional.test.comparators[0], ast.Constant)
        and conditional.test.comparators[0].value is None
        and isinstance(conditional.body, ast.Attribute)
        and isinstance(conditional.body.value, ast.Name)
        and conditional.body.value.id == "subprocess"
        and conditional.body.attr == "Popen"
        and isinstance(conditional.orelse, ast.Name)
        and conditional.orelse.id == "_process_factory"
    )


def _fixed_worker_process_call(node: ast.Call) -> bool:
    if (
        not isinstance(node.func, ast.Name)
        or node.func.id != "factory"
        or len(node.args) != 1
        or not isinstance(node.args[0], ast.List)
    ):
        return False
    command = node.args[0].elts
    if not (
        len(command) == 5
        and _str_call_of(command[0], "executable")
        and all(
            isinstance(command[index], ast.Constant) and command[index].value == value
            for index, value in ((1, "-I"), (2, "-B"), (3, "-S"))
        )
        and _str_call_of(command[4], "worker_script")
    ):
        return False
    keywords = {keyword.arg: keyword.value for keyword in node.keywords}
    if set(keywords) != {
        "shell",
        "cwd",
        "close_fds",
        "stdin",
        "stdout",
        "stderr",
        "env",
    }:
        return False

    return (
        isinstance(keywords["shell"], ast.Constant)
        and keywords["shell"].value is False
        and _str_call_of(keywords["cwd"], "repository_root")
        and isinstance(keywords["close_fds"], ast.Constant)
        and keywords["close_fds"].value is True
        and isinstance(keywords["stdin"], ast.Attribute)
        and isinstance(keywords["stdin"].value, ast.Name)
        and keywords["stdin"].value.id == "subprocess"
        and keywords["stdin"].attr == "PIPE"
        and isinstance(keywords["stdout"], ast.Attribute)
        and isinstance(keywords["stdout"].value, ast.Name)
        and keywords["stdout"].value.id == "subprocess"
        and keywords["stdout"].attr == "PIPE"
        and isinstance(keywords["stderr"], ast.Attribute)
        and isinstance(keywords["stderr"].value, ast.Name)
        and keywords["stderr"].value.id == "subprocess"
        and keywords["stderr"].attr == "DEVNULL"
        and isinstance(keywords["env"], ast.Name)
        and keywords["env"].id == "environment"
    )


def _validate_fixed_worker_transport(tree: ast.AST, logical_path: str) -> None:
    if logical_path != "src/mdcp/temporal/run_evidence.py":
        return
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_run_fixed_worker_transport"
    ]
    if not matches:
        return
    if len(matches) != 1:
        _fail()
    function = matches[0]
    parents = {
        child: parent for parent in ast.walk(function) for child in ast.iter_child_nodes(parent)
    }
    assignments = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Assign) and _fixed_worker_factory_assignment(node)
    ]
    launches = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and _fixed_worker_process_call(node)
    ]
    factory_calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "factory"
    ]
    if len(assignments) != 1 or len(launches) != 1 or factory_calls != launches:
        _fail()
    for reference in ast.walk(function):
        if not isinstance(reference, ast.Name) or reference.id != "factory":
            continue
        parent = parents.get(reference)
        if (
            isinstance(parent, ast.Assign)
            and reference in parent.targets
            and _fixed_worker_factory_assignment(parent)
        ) or (
            isinstance(parent, ast.Call)
            and parent.func is reference
            and _fixed_worker_process_call(parent)
        ):
            continue
        _fail()
    allowed_receiver_attributes = frozenset(
        {
            "process.stdin",
            "process.stdin.close",
            "process.stdin.flush",
            "process.stdin.write",
            "process.stdout",
            "process.stdout.read",
            "process.terminate",
            "process.wait",
            "process_errors.append",
            "process_waiter.is_alive",
            "process_waiter.join",
            "process_waiter.start",
            "reader.is_alive",
            "reader.join",
            "reader.start",
            "reader_errors.append",
            "response.extend",
            "return_codes.append",
            "controller_signal.set",
            "controller_signal.wait",
            "thread.is_alive",
            "thread.join",
            "writer.is_alive",
            "writer.join",
            "writer.start",
            "writer_errors.append",
            "overflow.append",
        }
    )
    for node in ast.walk(function):
        if not isinstance(node, ast.Attribute):
            continue
        identity = _simple_attribute_identity(node)
        if (
            identity is not None
            and identity.split(".", 1)[0]
            in {
                "process",
                "process_errors",
                "process_waiter",
                "reader",
                "reader_errors",
                "response",
                "return_codes",
                "controller_signal",
                "thread",
                "writer",
                "writer_errors",
                "overflow",
            }
            and identity not in allowed_receiver_attributes
        ):
            _fail()
        if identity == "process.stdout.read":
            call = next(
                (
                    candidate
                    for candidate in ast.walk(function)
                    if isinstance(candidate, ast.Call) and candidate.func is node
                ),
                None,
            )
            if (
                not isinstance(call, ast.Call)
                or len(call.args) != 1
                or call.keywords
                or not isinstance(call.args[0], ast.BinOp)
                or not isinstance(call.args[0].op, ast.Sub)
                or not isinstance(call.args[0].left, ast.Name)
                or call.args[0].left.id != "WORKER_STDOUT_PROBE_BYTES"
                or not isinstance(call.args[0].right, ast.Call)
                or not isinstance(call.args[0].right.func, ast.Name)
                or call.args[0].right.func.id != "len"
                or len(call.args[0].right.args) != 1
                or not isinstance(call.args[0].right.args[0], ast.Name)
                or call.args[0].right.args[0].id != "response"
            ):
                _fail()


def _validate_formal_worker_bootstrap(tree: ast.AST, logical_path: str) -> None:
    if logical_path != "src/mdcp/temporal/formal_worker.py":
        return
    bootstrap = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_bootstrap_paths"
    ]
    main = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    if len(bootstrap) != 1 or len(main) != 1:
        _fail()
    bootstrap_function = bootstrap[0]
    expected_environment_guard = ast.parse(
        'if set(os.environ) != {"SYSTEMROOT", "WINDIR"}:\n    raise ValueError'
    ).body[0]
    expected_cwd_guard = ast.parse(
        "if _canonical_path(Path.cwd(), directory=True) != repository_root:\n    raise ValueError"
    ).body[0]
    environment_guards = [
        node
        for node in bootstrap_function.body
        if ast.dump(node, include_attributes=False)
        == ast.dump(expected_environment_guard, include_attributes=False)
    ]
    cwd_guards = [
        node
        for node in bootstrap_function.body
        if ast.dump(node, include_attributes=False)
        == ast.dump(expected_cwd_guard, include_attributes=False)
    ]
    if len(environment_guards) != 1 or len(cwd_guards) != 1:
        _fail()
    derivation_names = {
        "script",
        "repository_root",
        "source_root",
        "executable",
        "site_packages",
    }
    observed_derivations: list[ast.AST] = []
    for node in ast.walk(bootstrap[0]):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in derivation_names
        ) or (
            isinstance(node, ast.Call)
            and _simple_attribute_identity(node.func) == "sys.path.insert"
        ):
            observed_derivations.append(node)
    observed_derivations.sort(key=lambda node: node.lineno)
    expected_sources = (
        "script = _canonical_path(Path(__file__), directory=False)",
        "repository_root = _canonical_path(script.parents[3], directory=True)",
        'source_root = _canonical_path(repository_root / "src", directory=True)',
        "executable = _canonical_path(Path(sys.executable), directory=False)",
        "site_packages = _canonical_path(executable.parents[1] / "
        '"Lib/site-packages", directory=True)',
        "sys.path.insert(0, str(site_packages))",
        "sys.path.insert(0, str(source_root))",
    )
    expected_derivations: list[ast.AST] = []
    for source in expected_sources:
        statement = ast.parse(source).body[0]
        expected_derivations.append(
            statement.value if isinstance(statement, ast.Expr) else statement
        )
    if tuple(ast.dump(node, include_attributes=False) for node in observed_derivations) != tuple(
        ast.dump(node, include_attributes=False) for node in expected_derivations
    ):
        _fail()
    derivation_lines = {
        node.targets[0].id: node.lineno
        for node in observed_derivations
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    if not (
        environment_guards[0].lineno < derivation_lines["script"]
        and derivation_lines["repository_root"]
        < cwd_guards[0].lineno
        < derivation_lines["source_root"]
    ):
        _fail()
    reads = [
        node
        for node in ast.walk(main[0])
        if isinstance(node, ast.Call)
        and _simple_attribute_identity(node.func) == "sys.stdin.buffer.read"
    ]
    if len(reads) != 1:
        _fail()
    read = reads[0]
    if (
        len(read.args) != 1
        or read.keywords
        or not isinstance(read.args[0], ast.BinOp)
        or not isinstance(read.args[0].op, ast.Add)
        or not isinstance(read.args[0].left, ast.Name)
        or read.args[0].left.id != "MAX_WORKER_MESSAGE_BYTES"
        or not isinstance(read.args[0].right, ast.Constant)
        or read.args[0].right.value != 1
    ):
        _fail()


def _validate_formal_worker_lifecycle(tree: ast.AST, logical_path: str) -> None:
    if logical_path != "src/mdcp/temporal/formal_worker.py":
        return
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    required = {
        "_execute_worker_request",
        "_execute_natural_run",
        "_complete_finalized_run",
        "_create_durable_marker",
        "_hash_archive",
        "_publish_retained",
        "_publish_private",
        "_publish_terminal",
        "_emit_response",
        "main",
    }
    if not required.issubset(functions):
        _fail()

    execute = functions["_execute_worker_request"]
    lifecycle_names = {
        "_validate_preconsumption",
        "_create_durable_marker",
        "_hash_archive",
        "_execute_natural_run",
        "_publish_private",
        "_publish_terminal",
    }
    execute_calls = tuple(
        node.func.id
        for node in sorted(
            (
                item
                for item in ast.walk(execute)
                if isinstance(item, ast.Call)
                and isinstance(item.func, ast.Name)
                and item.func.id in lifecycle_names
            ),
            key=lambda item: (item.lineno, item.col_offset),
        )
    )
    if execute_calls != (
        "_validate_preconsumption",
        "_create_durable_marker",
        "_hash_archive",
        "_execute_natural_run",
    ):
        _fail()

    natural = functions["_execute_natural_run"]
    execution_events: list[str] = []
    for call in sorted(
        (item for item in ast.walk(natural) if isinstance(item, ast.Call)),
        key=lambda item: (item.lineno, item.col_offset),
    ):
        if isinstance(call.func, ast.Name) and call.func.id == "_checkpoint":
            if (
                len(call.args) != 2
                or call.keywords
                or not isinstance(call.args[1], ast.Attribute)
                or not isinstance(call.args[1].value, ast.Name)
                or call.args[1].value.id != "RuntimeStage"
                or call.args[1].attr not in {"PRE_LOAD", "PRE_FIT", "POST_FIT", "PRE_SEAL", "EXIT"}
            ):
                _fail()
            execution_events.append(f"checkpoint:{call.args[1].attr}")
        elif isinstance(call.func, ast.Name) and call.func.id == "_complete_finalized_run":
            if (
                len(call.args) != 5
                or call.keywords
                or not isinstance(call.args[0], ast.Name)
                or call.args[0].id != "context"
                or not isinstance(call.args[1], ast.Name)
                or call.args[1].id != "marker_sha256"
                or not isinstance(call.args[2], ast.Name)
                or call.args[2].id != "guard"
                or not isinstance(call.args[3], ast.Name)
                or call.args[3].id != "result"
                or not isinstance(call.args[4], ast.Name)
                or call.args[4].id != "fit_count"
            ):
                _fail()
            execution_events.append("complete-finalized")
    if tuple(execution_events) != (
        "checkpoint:PRE_LOAD",
        "checkpoint:PRE_FIT",
        "checkpoint:POST_FIT",
        "complete-finalized",
    ):
        _fail()

    finalized = functions["_complete_finalized_run"]
    finalized_events: list[str] = []
    for node in sorted(
        (item for item in ast.walk(finalized) if isinstance(item, ast.Call | ast.Assign)),
        key=lambda item: (item.lineno, item.col_offset),
    ):
        if isinstance(node, ast.Assign):
            if (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "seal_bytes"
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "canonicalize_json"
            ):
                finalized_events.append("encode:terminal")
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "_checkpoint":
            if (
                len(node.args) != 2
                or node.keywords
                or not isinstance(node.args[1], ast.Attribute)
                or not isinstance(node.args[1].value, ast.Name)
                or node.args[1].value.id != "RuntimeStage"
                or node.args[1].attr not in {"PRE_SEAL", "EXIT"}
            ):
                _fail()
            finalized_events.append(f"checkpoint:{node.args[1].attr}")
        elif isinstance(node.func, ast.Name) and node.func.id in {
            "_formalize_natural",
            "_encode_natural",
            "_publish_private",
            "FormalDevelopmentSeal",
            "_publish_terminal",
        }:
            finalized_events.append(node.func.id)
    if tuple(finalized_events) != (
        "_formalize_natural",
        "checkpoint:PRE_SEAL",
        "_encode_natural",
        "_publish_private",
        "checkpoint:EXIT",
        "FormalDevelopmentSeal",
        "encode:terminal",
        "_publish_terminal",
    ):
        _fail()

    main_calls = tuple(
        node.func.id
        for node in sorted(
            (
                item
                for item in ast.walk(functions["main"])
                if isinstance(item, ast.Call)
                and isinstance(item.func, ast.Name)
                and item.func.id in {"_execute_worker_request", "_emit_response"}
            ),
            key=lambda item: (item.lineno, item.col_offset),
        )
    )
    if main_calls != ("_execute_worker_request", "_emit_response"):
        _fail()
    emitter_calls = tuple(
        _simple_attribute_identity(node.func)
        for node in sorted(
            (item for item in ast.walk(functions["_emit_response"]) if isinstance(item, ast.Call)),
            key=lambda item: (item.lineno, item.col_offset),
        )
        if _simple_attribute_identity(node.func)
        in {"encode_formal_worker_response", "sys.stdout.buffer.write", "sys.stdout.buffer.flush"}
    )
    if emitter_calls != (
        "encode_formal_worker_response",
        "sys.stdout.buffer.write",
        "sys.stdout.buffer.flush",
    ):
        _fail()


def _validate_runtime_guard_inventories(tree: ast.AST, logical_path: str) -> None:
    if logical_path != "src/mdcp/temporal/runtime_guards.py":
        return
    direct_nodes = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }
    expected = {
        "_worker_source_inventory": (
            ast.FunctionDef,
            "SEARCH_SOURCE_PATHS",
            "5163a07f008182936e773e2c599d814fde3251d708f006744307b15ab5c48871",
        ),
        "_formal_worker_source_inventory": (
            ast.FunctionDef,
            "FORMAL_WORKER_SOURCE_PATHS",
            "67797519cf49c14939a06c25be3712e481b54f578cf9dba2677c881be97c30f0",
        ),
        "_WorkerRuntimeGuard": (
            ast.ClassDef,
            None,
            "1afcc05d9cc79ec1c9e425fdda88a6c0dd6a83e5e0f673c97ef1dd230946f7f9",
        ),
        "build_worker_runtime_guard": (
            ast.FunctionDef,
            None,
            "051ba83878ca7a30b3a89973767f43489b8eed04a4060bbd34d15795d2de0855",
        ),
    }
    if not expected.keys() <= direct_nodes.keys():
        _fail()
    for protected_name, (node_type, path_name, expected_sha256) in expected.items():
        protected_node = direct_nodes[protected_name]
        if type(protected_node) is not node_type:
            _fail()
        normalized = ast.dump(protected_node, include_attributes=False).encode("utf-8")
        if sha256_hex(normalized) != expected_sha256:
            _fail()
        if path_name is not None:
            loops = [node for node in ast.walk(protected_node) if isinstance(node, ast.For)]
            if len(loops) != 1:
                _fail()
            loop = loops[0]
            if (
                not isinstance(loop.target, ast.Name)
                or loop.target.id != "logical_path"
                or not isinstance(loop.iter, ast.Name)
                or loop.iter.id != path_name
            ):
                _fail()

    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    def has_local_scope(node: ast.AST) -> bool:
        current = node
        parent = parents.get(current)
        while parent is not None:
            if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                if current in parent.body:
                    return True
                current = parent
                parent = parents.get(current)
                continue
            if isinstance(parent, ast.Lambda):
                if current is parent.body:
                    return True
                current = parent
                parent = parents.get(current)
                continue
            current = parent
            parent = parents.get(current)
        return False

    module_bindings: dict[str, list[ast.AST]] = {name: [] for name in expected}
    for node in ast.walk(tree):
        binding_names: tuple[str, ...] = ()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            binding_names = (node.name,)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
            binding_names = (node.id,)
        elif isinstance(node, ast.Import):
            binding_names = tuple(
                alias.asname or alias.name.split(".", 1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            binding_names = tuple(alias.asname or alias.name for alias in node.names)
        elif (
            isinstance(node, ast.ExceptHandler | ast.MatchAs | ast.MatchStar)
            and node.name is not None
        ):
            binding_names = (node.name,)
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            binding_names = (node.rest,)
        elif isinstance(node, ast.Global | ast.Nonlocal):
            binding_names = tuple(node.names)
        if not binding_names:
            continue
        is_scope_declaration = isinstance(node, ast.Global | ast.Nonlocal)
        if has_local_scope(node) and not is_scope_declaration:
            continue
        for binding_name in binding_names:
            if binding_name in module_bindings:
                module_bindings[binding_name].append(node)

    for protected_name, protected_node in direct_nodes.items():
        if protected_name in module_bindings and module_bindings[protected_name] != [
            protected_node
        ]:
            _fail()


def _allowed_run_evidence_git_call(
    node: ast.Call,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "_git_bytes":
        return True
    if (
        _enclosing_function(node, parents) not in _ALLOWED_RUN_EVIDENCE_GIT_CALLS
        or not node.args
        or node.keywords
        or not isinstance(node.args[0], ast.Name)
        or node.args[0].id != "root"
    ):
        return False
    command = tuple(
        (
            f"name:{argument.value.id}"
            if isinstance(argument, ast.Starred) and isinstance(argument.value, ast.Name)
            else _subprocess_argument_identity(argument)
        )
        for argument in node.args[1:]
    )
    return command in _ALLOWED_RUN_EVIDENCE_GIT_CALLS[_enclosing_function(node, parents)]


def _allowed_subprocess_call(
    node: ast.Call,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "run":
        return False
    if (
        not isinstance(node.func.value, ast.Name)
        or node.func.value.id != "subprocess"
        or len(node.args) != 1
    ):
        return False
    if not isinstance(node.args[0], ast.Tuple):
        return False
    command = tuple(
        (
            f"name:{argument.value.id}"
            if isinstance(argument, ast.Starred) and isinstance(argument.value, ast.Name)
            else _subprocess_argument_identity(argument)
        )
        for argument in node.args[0].elts
    )
    enclosing_function = _enclosing_function(node, parents)
    expected = _ALLOWED_SUBPROCESS_CALLS.get(logical_path, {}).get(enclosing_function)
    if logical_path == "src/mdcp/temporal/search_identity.py":
        if enclosing_function != "_git" or command != ("git", "name:arguments"):
            return False
    elif command != expected:
        return False
    keywords = {keyword.arg: keyword.value for keyword in node.keywords}
    expected_text = not (
        (
            logical_path == "src/mdcp/temporal/runtime_guards.py"
            and _enclosing_function(node, parents) == "_tracked_paths"
        )
        or logical_path == "src/mdcp/temporal/run_evidence.py"
    )
    return (
        set(keywords) == {"cwd", "check", "capture_output", "text"}
        and isinstance(keywords["cwd"], ast.Name)
        and keywords["cwd"].id
        == ("root" if logical_path == "src/mdcp/temporal/search_identity.py" else "repository_root")
        and isinstance(keywords["check"], ast.Constant)
        and keywords["check"].value is False
        and isinstance(keywords["capture_output"], ast.Constant)
        and keywords["capture_output"].value is True
        and isinstance(keywords["text"], ast.Constant)
        and keywords["text"].value is expected_text
    )


def _allowed_search_identity_git_call(
    node: ast.Call,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "_git":
        return True
    if not node.args or node.keywords or not isinstance(node.args[0], ast.Name):
        return False
    command = tuple(
        (
            f"name:{argument.value.id}"
            if isinstance(argument, ast.Starred) and isinstance(argument.value, ast.Name)
            else _subprocess_argument_identity(argument)
        )
        for argument in node.args[1:]
    )
    return command in _ALLOWED_SEARCH_IDENTITY_GIT_CALLS.get(
        _enclosing_function(node, parents), frozenset()
    )


def _allowed_getattr_reference(
    node: ast.Name,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    if logical_path == "src/mdcp/temporal/formal_worker.py" and (
        node.id == "getattr"
        and isinstance(parent, ast.Call)
        and parent.func is node
        and _enclosing_function(node, parents) == "_write_exclusive"
        and len(parent.args) == 3
        and not parent.keywords
        and isinstance(parent.args[0], ast.Name)
        and parent.args[0].id == "os"
        and isinstance(parent.args[1], ast.Constant)
        and parent.args[1].value == "O_BINARY"
        and isinstance(parent.args[2], ast.Constant)
        and parent.args[2].value == 0
    ):
        return True
    if logical_path in {
        "src/mdcp/temporal/formal_worker.py",
        "src/mdcp/temporal/run_evidence.py",
        "src/mdcp/temporal/runtime_guards.py",
    }:
        if logical_path == "src/mdcp/temporal/runtime_guards.py":
            expected_scopes = {
                "_worker_source_inventory",
                "_formal_worker_source_inventory",
            }
        else:
            expected_scopes = {
                {
                    "src/mdcp/temporal/formal_worker.py": "_canonical_path",
                    "src/mdcp/temporal/run_evidence.py": "_canonical_existing_path",
                }[logical_path]
            }
        return (
            node.id == "getattr"
            and isinstance(parent, ast.Call)
            and parent.func is node
            and _enclosing_function(node, parents) in expected_scopes
            and len(parent.args) == 3
            and not parent.keywords
            and isinstance(parent.args[0], ast.Name)
            and parent.args[0].id == "information"
            and isinstance(parent.args[1], ast.Constant)
            and parent.args[1].value == "st_file_attributes"
            and isinstance(parent.args[2], ast.Constant)
            and parent.args[2].value == 0
        )
    return (
        logical_path == "src/mdcp/temporal/search_identity.py"
        and node.id == "getattr"
        and isinstance(parent, ast.Call)
        and parent.func is node
        and _enclosing_function(node, parents) == "_bound_digests_recompute"
        and len(parent.args) == 2
        and not parent.keywords
        and all(isinstance(argument, ast.Name) for argument in parent.args)
        and parent.args[0].id == "receipt"
        and parent.args[1].id == "field_name"
    )


def _allowed_formal_worker_module_reference(
    node: ast.Name,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    return (
        logical_path == "src/mdcp/temporal/formal_worker.py"
        and node.id == "os"
        and isinstance(parent, ast.Call)
        and len(parent.args) == 3
        and parent.args[0] is node
        and isinstance(parent.func, ast.Name)
        and parent.func.id == "getattr"
        and _allowed_getattr_reference(parent.func, logical_path, parents)
    )


def _import_allowed(logical_path: str, module: str, imported_name: str | None) -> bool:
    if (
        imported_name is not None
        and module in _ALLOWED_DIRECT_IMPORTS
        and imported_name not in _ALLOWED_DIRECT_IMPORTS[module]
    ):
        return False
    return (module, imported_name) in _FORMAL_IMPORT_ALLOWLIST.get(logical_path, frozenset())


def _scoped_import_allowed(
    node: ast.Import | ast.ImportFrom,
    logical_path: str,
    module: str,
    imported_name: str | None,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    allowed_scopes = _SCOPED_IMPORT_ALLOWLIST.get(logical_path, {}).get((module, imported_name))
    if logical_path == "src/mdcp/temporal/formal_worker.py":
        matching_aliases = tuple(
            alias
            for alias in node.names
            if (alias.name if isinstance(node, ast.ImportFrom) else None) == imported_name
            or (isinstance(node, ast.Import) and alias.name == module)
        )
        if (
            allowed_scopes is None
            or len(matching_aliases) != 1
            or matching_aliases[0].asname is not None
        ):
            return False
    return allowed_scopes is None or _enclosing_function(node, parents) in allowed_scopes


def _allowed_fixed_launch_profile_reference(
    node: ast.Attribute,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    current: ast.AST | None = node
    while current is not None and not isinstance(current, ast.Call):
        current = parents.get(current)
    return (
        isinstance(current, ast.Call)
        and _fixed_worker_process_call(current)
        and _enclosing_function(node, parents) == "_run_fixed_worker_transport"
    )


def _allowed_fixed_process_factory_reference(
    node: ast.Attribute,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    return (
        isinstance(parent, ast.IfExp)
        and parent.body is node
        and isinstance(parents.get(parent), ast.Assign)
        and _fixed_worker_factory_assignment(parents[parent])
        and _enclosing_function(node, parents) == "_run_fixed_worker_transport"
    )


def _bind_import(bindings: dict[str, str], local_name: str, qualified_name: str) -> None:
    if local_name in bindings:
        if bindings[local_name] == qualified_name:
            return
        _fail()
    if local_name in _RESERVED_BINDING_NAMES:
        _fail()
    bindings[local_name] = qualified_name


def _build_bindings(tree: ast.AST, logical_path: str) -> tuple[dict[str, str], frozenset[str]]:
    bindings: dict[str, str] = {}
    module_roots: set[str] = set()
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".", 1)[0]
                if (
                    root_module in _DYNAMIC_IMPORT_MODULES | _REFLECTION_MODULES
                    or (
                        root_module == "sys"
                        and logical_path
                        not in {
                            _TRUSTED_FIREWALL_PATH,
                            "src/mdcp/temporal/cli.py",
                            "src/mdcp/temporal/formal_worker.py",
                            "src/mdcp/temporal/run_evidence.py",
                            "src/mdcp/temporal/runtime_guards.py",
                        }
                    )
                    or _is_forbidden_module(alias.name)
                ):
                    _fail()
                if not _import_allowed(logical_path, alias.name, None):
                    _fail()
                if not _scoped_import_allowed(node, logical_path, alias.name, None, parents):
                    _fail()
                local_name = alias.asname or alias.name.split(".", 1)[0]
                qualified_name = alias.name if alias.asname else local_name
                _bind_import(bindings, local_name, qualified_name)
                module_roots.add(qualified_name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                _fail()
            root_module = module.split(".", 1)[0]
            if root_module in _DYNAMIC_IMPORT_MODULES | _REFLECTION_MODULES or (
                root_module == "sys"
                and logical_path
                not in {
                    _TRUSTED_FIREWALL_PATH,
                    "src/mdcp/temporal/formal_worker.py",
                    "src/mdcp/temporal/run_evidence.py",
                    "src/mdcp/temporal/runtime_guards.py",
                }
            ):
                _fail()
            if any(alias.name == "*" for alias in node.names):
                _fail()
            if module in _FORBIDDEN_MODULES:
                allowed = _ALLOWED_DIRECT_IMPORTS[module]
                if any(alias.name not in allowed for alias in node.names):
                    _fail()
            elif (
                module == "mdcp.workload"
                and any(alias.name in {"dataset", "splits", "*"} for alias in node.names)
            ) or _is_forbidden_module(module):
                _fail()
            for alias in node.names:
                if not _import_allowed(logical_path, module, alias.name):
                    _fail()
                if not _scoped_import_allowed(
                    node,
                    logical_path,
                    module,
                    alias.name,
                    parents,
                ):
                    _fail()
                local_name = alias.asname or alias.name
                _bind_import(
                    bindings,
                    local_name,
                    f"{module}.{alias.name}" if module else alias.name,
                )

    return bindings, frozenset(module_roots)


def _shadows_imported_binding(node: ast.AST, bindings: dict[str, str]) -> bool:
    protected_names = bindings.keys() | _RESERVED_BINDING_NAMES
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return node.name in protected_names
    if isinstance(node, ast.arg):
        return node.arg in protected_names
    if isinstance(node, ast.ExceptHandler):
        return node.name in protected_names if node.name is not None else False
    if isinstance(node, ast.Global | ast.Nonlocal):
        return any(name in protected_names for name in node.names)
    if isinstance(node, ast.MatchAs | ast.MatchStar):
        return node.name in protected_names if node.name is not None else False
    if isinstance(node, ast.MatchMapping):
        return node.rest in protected_names if node.rest is not None else False
    return False


def _audit_tree(tree: ast.AST, logical_path: str) -> None:
    _validate_pinned_file_capability_functions(tree, logical_path)
    _validate_fixed_worker_transport(tree, logical_path)
    _validate_formal_worker_bootstrap(tree, logical_path)
    _validate_formal_worker_lifecycle(tree, logical_path)
    _validate_runtime_guard_inventories(tree, logical_path)
    bindings, module_roots = _build_bindings(tree, logical_path)
    allowed_module_attributes = _FORMAL_MODULE_ATTRIBUTE_ALLOWLIST.get(logical_path, frozenset())
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    pandas_reader_references = 0
    previous_reader_references = 0
    descriptor_path_references = 0
    protected_function_counts = {
        name: 0 for name in _PROTECTED_PATH_PARAMETER_FUNCTIONS.get(logical_path, frozenset())
    }
    for node in ast.walk(tree):
        if _shadows_imported_binding(node, bindings):
            _fail()
        if (
            logical_path == "src/mdcp/temporal/search_identity.py"
            and isinstance(node, ast.Name)
            and node.id == "_git"
        ):
            parent = parents.get(node)
            if not (
                isinstance(parent, ast.Call)
                and parent.func is node
                and _allowed_search_identity_git_call(parent, parents)
            ):
                _fail()
        if (
            logical_path == "src/mdcp/temporal/run_evidence.py"
            and isinstance(node, ast.Call)
            and not _allowed_run_evidence_git_call(node, parents)
        ):
            _fail()
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name in protected_function_counts
        ):
            protected_function_counts[node.name] += 1
            if not _has_exact_path_parameter(node):
                _fail()
        protected_path_scope = _protected_path_scope(node, logical_path, parents)
        if (
            isinstance(node, ast.Name)
            and node.id == "path"
            and protected_path_scope is not None
            and not (
                _enclosing_function(node, parents) == protected_path_scope
                and isinstance(parents.get(node), ast.Attribute)
                and parents[node].value is node
                and isinstance(parents.get(parents[node]), ast.Call)
                and parents[parents[node]].func is parents[node]
                and _allowed_file_access_call(
                    parents[parents[node]],
                    logical_path,
                    parents,
                )
            )
        ):
            _fail()
        if (
            isinstance(node, ast.Global | ast.Nonlocal)
            and "path" in node.names
            and protected_path_scope is not None
        ):
            _fail()
        if isinstance(node, ast.Attribute) and _attribute_name(node, bindings) == "pandas.read_csv":
            pandas_reader_references += 1
        if isinstance(node, ast.Name) and node.id == "previous_read_csv":
            previous_reader_references += 1
            if logical_path != _TRUSTED_FIREWALL_PATH or not _allowed_previous_reader_reference(
                node,
                bindings,
                parents,
            ):
                _fail()
        if isinstance(node, ast.Name) and node.id == "descriptor_path":
            descriptor_path_references += 1
            if logical_path != "src/mdcp/predictor/app_v2.py" or not (
                _allowed_descriptor_path_reference(node, bindings, parents)
            ):
                _fail()
        if (
            isinstance(node, ast.Attribute)
            and node.attr in _FILE_ACCESS_METHODS
            and not (
                (
                    node.attr == "read_csv"
                    and logical_path == _TRUSTED_FIREWALL_PATH
                    and _allowed_pandas_reader_reference(node, bindings, parents)
                )
                or (
                    isinstance(parents.get(node), ast.Call)
                    and parents[node].func is node
                    and _allowed_file_access_call(parents[node], logical_path, parents)
                )
            )
        ):
            _fail()
        if (
            isinstance(node, ast.Attribute)
            and _attribute_name(node, bindings) == "subprocess.run"
            and isinstance(parents.get(node), ast.Call)
            and parents[node].func is node
            and not _allowed_subprocess_call(parents[node], logical_path, parents)
        ):
            _fail()
        if (
            logical_path == "src/mdcp/temporal/search_identity.py"
            and isinstance(node, ast.Call)
            and not _allowed_search_identity_git_call(node, parents)
        ):
            _fail()
        if isinstance(node, ast.Name | ast.Attribute):
            qualified_name = _attribute_name(node, bindings)
            if (
                logical_path == "src/mdcp/temporal/run_evidence.py"
                and isinstance(node, ast.Attribute)
                and qualified_name == "subprocess.Popen"
                and not _allowed_fixed_process_factory_reference(node, parents)
            ):
                _fail()
            if (
                logical_path == "src/mdcp/temporal/run_evidence.py"
                and isinstance(node, ast.Attribute)
                and qualified_name in {"subprocess.PIPE", "subprocess.DEVNULL"}
                and not _allowed_fixed_launch_profile_reference(node, parents)
            ):
                _fail()
            if qualified_name in _SENSITIVE_FILE_CALLABLE_SCOPES.get(
                logical_path, {}
            ) and not _allowed_sensitive_file_callable_reference(
                node,
                qualified_name,
                logical_path,
                parents,
            ):
                _fail()
            if (
                isinstance(node, ast.Name)
                and node.id in bindings
                and not isinstance(node.ctx, ast.Load)
            ):
                _fail()
            if (
                qualified_name in _FORBIDDEN_DYNAMIC_REFERENCES
                and not (
                    isinstance(node, ast.Name)
                    and qualified_name == "__file__"
                    and _allowed_file_source_name(node, logical_path, parents)
                )
                and not (
                    isinstance(node, ast.Name)
                    and qualified_name == "getattr"
                    and _allowed_getattr_reference(node, logical_path, parents)
                )
            ) or (
                isinstance(node, ast.Attribute)
                and (
                    (
                        node.attr.startswith("_")
                        and not _allowed_dunder_attribute(node, logical_path, parents)
                        and node.attr
                        not in _ALLOWED_PRIVATE_ATTRIBUTES.get(logical_path, frozenset())
                    )
                    or node.attr in _FORBIDDEN_REFLECTION_ATTRIBUTES
                    or (qualified_name is not None and _is_forbidden_module(qualified_name))
                )
            ):
                _fail()
            if (
                isinstance(node, ast.Attribute)
                and qualified_name in {"os.environ", "os.getenv"}
                and not _environment_access_allowed(
                    node,
                    qualified_name,
                    logical_path,
                    parents,
                )
            ):
                _fail()
            if (
                isinstance(node, ast.Name)
                and qualified_name in module_roots
                and not (
                    isinstance(parents.get(node), ast.Attribute) and parents[node].value is node
                )
                and not _allowed_formal_worker_module_reference(node, logical_path, parents)
            ):
                _fail()
            if (
                isinstance(node, ast.Attribute)
                and qualified_name is not None
                and any(
                    qualified_name.startswith(f"{module_root}.") for module_root in module_roots
                )
                and qualified_name not in allowed_module_attributes
            ):
                _fail()
            if (
                logical_path == "src/mdcp/temporal/run_evidence.py"
                and isinstance(node, ast.Attribute)
                and qualified_name is not None
                and qualified_name.startswith("windll.")
                and qualified_name not in allowed_module_attributes
            ):
                _fail()
    if logical_path == _TRUSTED_FIREWALL_PATH and (
        pandas_reader_references != 3 or previous_reader_references != 3
    ):
        _fail()
    if logical_path == "src/mdcp/predictor/app_v2.py" and descriptor_path_references != 2:
        _fail()
    if any(count != 1 for count in protected_function_counts.values()):
        _fail()


def _safe_logical_path(value: str) -> str:
    candidate = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or candidate.is_absolute()
        or ".." in candidate.parts
        or candidate.as_posix() != value
        or candidate.suffix != ".py"
    ):
        _fail()
    return value


def _default_paths(repository_root: Path) -> tuple[str, ...]:
    temporal_root = repository_root / FORMAL_TEMPORAL_PACKAGE_ROOT
    if not temporal_root.is_dir():
        _fail()
    temporal_paths = tuple(
        path.relative_to(repository_root).as_posix()
        for path in sorted(temporal_root.glob("*.py"), key=lambda item: item.as_posix())
    )
    return tuple(sorted((*FORMAL_V2_FIXED_PATHS, *temporal_paths)))


def audit_static_h2_firewall(
    repository_root: Path,
    *,
    formal_paths: tuple[str, ...] | None = None,
) -> StaticFirewallResult:
    logical_paths = _default_paths(repository_root) if formal_paths is None else formal_paths
    if not logical_paths or len(set(logical_paths)) != len(logical_paths):
        _fail()

    checked_paths = tuple(sorted(_safe_logical_path(path) for path in logical_paths))
    for logical_path in checked_paths:
        source_path = repository_root / logical_path
        try:
            raw_source = source_path.read_bytes()
            source = _canonical_utf8_source(raw_source)
            tree = ast.parse(source, filename=logical_path)
            executable_tree = ast.parse(raw_source, filename=logical_path)
        except (OSError, UnicodeError, SyntaxError):
            _fail()
        if ast.dump(tree, include_attributes=False) != ast.dump(
            executable_tree, include_attributes=False
        ):
            _fail()
        _audit_tree(tree, logical_path)

    return StaticFirewallResult(
        schema_version="mdcp.static-h2-firewall.v1",
        verdict="PASS",
        checked_paths=checked_paths,
        implementation_sha256=sha256_hex(Path(__file__).read_bytes()),
    )


def _implementation_sha256(function: object) -> str:
    if not isinstance(function, FunctionType):
        raise BehavioralFirewallError()
    code = function.__code__
    try:
        return sha256_hex(Path(code.co_filename).read_bytes())
    except OSError as error:
        raise BehavioralFirewallError() from error


def _boundary_document(boundary: DevelopmentBoundaryResult) -> dict[str, object]:
    return {
        "schema_version": boundary.schema_version,
        "verdict": boundary.verdict,
        "archive_sha256": boundary.archive_sha256,
        "development_row_count": boundary.development_row_count,
        "development_rows_sha256": boundary.development_rows_sha256,
        "train_row_count": boundary.train_row_count,
        "train_rows_sha256": boundary.train_rows_sha256,
        "h1_row_count": boundary.h1_row_count,
        "h1_rows_sha256": boundary.h1_rows_sha256,
        "read_csv_nrows": list(boundary.read_csv_nrows),
        "forbidden_call_counts": dict(boundary.forbidden_call_counts),
        "h2_status": boundary.h2_status,
        "h2_loaded_rows": boundary.h2_loaded_rows,
    }


def _behavioral_body_document(body: BehavioralFirewallBody) -> dict[str, object]:
    return {
        "schema_version": body.schema_version,
        "verdict": body.verdict,
        "fixture_recipe_sha256": body.fixture_recipe_sha256,
        "development_boundary": _boundary_document(body.development_boundary),
        "static_firewall_implementation_sha256": (body.static_firewall_implementation_sha256),
        "behavioral_firewall_implementation_sha256": (
            body.behavioral_firewall_implementation_sha256
        ),
        "bounded_loader_implementation_sha256": (body.bounded_loader_implementation_sha256),
        "development_split_implementation_sha256": (body.development_split_implementation_sha256),
    }


def run_development_boundary(
    archive_path: Path,
    expected_sha256: str,
) -> DevelopmentBoundaryResult:
    read_csv_nrows: list[int] = []
    forbidden_call_counts = {name: 0 for name in _FORBIDDEN_CALL_IDENTITIES.values()}
    previous_read_csv = pd.read_csv
    previous_profile = sys.getprofile()

    def bounded_read_csv(*args: object, **kwargs: object) -> pd.DataFrame:
        nrows = kwargs.get("nrows")
        if nrows != _DEVELOPMENT_ROWS:
            raise BehavioralFirewallError()
        read_csv_nrows.append(nrows)
        return previous_read_csv(*args, **kwargs)

    def deny_forbidden_call(frame: FrameType, event: str, arg: object) -> None:
        del arg
        if event != "call":
            return
        identity = (frame.f_code.co_filename, frame.f_code.co_name)
        capability = _FORBIDDEN_CALL_IDENTITIES.get(identity)
        if capability is not None:
            forbidden_call_counts[capability] += 1
            raise BehavioralFirewallError(_FORBIDDEN_CALL_REASON)

    try:
        pd.read_csv = bounded_read_csv
        sys.setprofile(deny_forbidden_call)
        frame = load_uci_development_archive(archive_path, expected_sha256)
        partitions = split_development_rows(frame)
    except BehavioralFirewallError:
        raise
    except Exception as error:
        raise BehavioralFirewallError() from error
    finally:
        sys.setprofile(previous_profile)
        pd.read_csv = previous_read_csv

    if (
        tuple(read_csv_nrows) != (_DEVELOPMENT_ROWS,)
        or any(forbidden_call_counts.values())
        or len(frame) != _DEVELOPMENT_ROWS
        or len(partitions.train) != _TRAIN_ROWS
        or len(partitions.h1) != _H1_ROWS
        or hasattr(partitions, "h2")
        or hasattr(partitions, "open_h2")
    ):
        raise BehavioralFirewallError()

    return DevelopmentBoundaryResult(
        schema_version="mdcp.development-boundary.v1",
        verdict="PASS",
        archive_sha256=str(frame.attrs["archive_sha256"]),
        development_row_count=_DEVELOPMENT_ROWS,
        development_rows_sha256=str(frame.attrs["development_rows_sha256"]),
        train_row_count=_TRAIN_ROWS,
        train_rows_sha256=str(partitions.train.attrs["rows_sha256"]),
        h1_row_count=_H1_ROWS,
        h1_rows_sha256=str(partitions.h1.attrs["rows_sha256"]),
        read_csv_nrows=(_DEVELOPMENT_ROWS,),
        forbidden_call_counts=dict(forbidden_call_counts),
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )


def run_behavioral_h2_firewall(
    archive_path: Path,
    expected_sha256: str,
    *,
    fixture_recipe_sha256: str,
) -> BehavioralFirewallResult:
    if not _SHA256_PATTERN.fullmatch(fixture_recipe_sha256):
        raise BehavioralFirewallError()
    boundary = run_development_boundary(archive_path, expected_sha256)
    firewall_implementation_sha256 = sha256_hex(Path(__file__).read_bytes())
    body = BehavioralFirewallBody(
        schema_version="mdcp.behavioral-h2-firewall.v1",
        verdict="PASS",
        fixture_recipe_sha256=fixture_recipe_sha256,
        development_boundary=boundary,
        static_firewall_implementation_sha256=firewall_implementation_sha256,
        behavioral_firewall_implementation_sha256=firewall_implementation_sha256,
        bounded_loader_implementation_sha256=_implementation_sha256(_BOUNDED_LOADER),
        development_split_implementation_sha256=_implementation_sha256(_DEVELOPMENT_SPLITTER),
    )
    result_digest = sha256_hex(canonicalize_json(_behavioral_body_document(body)))
    return BehavioralFirewallResult(
        body=body,
        behavioral_result_sha256=result_digest,
    )
