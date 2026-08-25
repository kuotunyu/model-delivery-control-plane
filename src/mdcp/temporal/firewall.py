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
            "ast.Call",
            "ast.ClassDef",
            "ast.Constant",
            "ast.ExceptHandler",
            "ast.FunctionDef",
            "ast.Global",
            "ast.Import",
            "ast.ImportFrom",
            "ast.Load",
            "ast.MatchAs",
            "ast.MatchMapping",
            "ast.MatchStar",
            "ast.Name",
            "ast.Nonlocal",
            "ast.Starred",
            "ast.Subscript",
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
}
_ALLOWED_ENVIRONMENT_KEYS = {
    "src/mdcp/predictor/app_v2.py": frozenset(
        {
            "MDCP_DESCRIPTOR_PATH",
            "MDCP_ONNX_PATH",
            "MDCP_RELEASE_ID",
            "MDCP_ROUTE_REVISION",
        }
    )
}
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
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and len(node.args) == 1
        and not node.keywords
    ):
        argument = node.args[0]
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
    identity = (
        _enclosing_function(node, parents),
        node.func.attr,
        _file_receiver_identity(node.func.value),
    )
    return identity in _ALLOWED_FILE_ACCESS_CALLS.get(logical_path, frozenset())


def _allowed_file_source_name(
    node: ast.Name,
    logical_path: str,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
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
    allowed_keys = _ALLOWED_ENVIRONMENT_KEYS.get(logical_path, frozenset())
    parent = parents.get(node)
    if qualified_name == "os.environ":
        return (
            isinstance(parent, ast.Subscript)
            and parent.value is node
            and isinstance(parent.ctx, ast.Load)
            and _constant_string(parent.slice) in allowed_keys
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


def _import_allowed(logical_path: str, module: str, imported_name: str | None) -> bool:
    if imported_name is not None and module in _ALLOWED_DIRECT_IMPORTS:
        return imported_name in _ALLOWED_DIRECT_IMPORTS[module]
    return (module, imported_name) in _FORMAL_IMPORT_ALLOWLIST.get(logical_path, frozenset())


def _bind_import(bindings: dict[str, str], local_name: str, qualified_name: str) -> None:
    if local_name in bindings or local_name in _RESERVED_BINDING_NAMES:
        _fail()
    bindings[local_name] = qualified_name


def _build_bindings(tree: ast.AST, logical_path: str) -> tuple[dict[str, str], frozenset[str]]:
    bindings: dict[str, str] = {}
    module_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".", 1)[0]
                if (
                    root_module in _DYNAMIC_IMPORT_MODULES | _REFLECTION_MODULES
                    or (root_module == "sys" and logical_path != _TRUSTED_FIREWALL_PATH)
                    or _is_forbidden_module(alias.name)
                ):
                    _fail()
                if not _import_allowed(logical_path, alias.name, None):
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
                root_module == "sys" and logical_path != _TRUSTED_FIREWALL_PATH
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
        if isinstance(node, ast.Name | ast.Attribute):
            qualified_name = _attribute_name(node, bindings)
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
            ) or (
                isinstance(node, ast.Attribute)
                and (
                    (
                        node.attr.startswith("_")
                        and not _allowed_dunder_attribute(node, logical_path, parents)
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
