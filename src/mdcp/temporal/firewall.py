from __future__ import annotations

import ast
import re
import sys
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
    "__loader__",
    "__spec__",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "locals",
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
        "sys",
        "tb_frame",
        "tb_next",
    }
)
_TRUSTED_FIREWALL_PATH = "src/mdcp/temporal/firewall.py"
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
            ("pandas", None),
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
            ("types", "FrameType"),
            ("types", "FunctionType"),
            ("typing", "Annotated"),
            ("typing", "Literal"),
            ("typing_extensions", "TypedDict"),
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
}
_FORMAL_MODULE_ATTRIBUTE_ALLOWLIST = {
    "src/mdcp/predictor/app_v2.py": frozenset(
        {"json.loads", "math.isfinite", "os.environ", "os.getenv"}
    ),
    "src/mdcp/temporal/adapter.py": frozenset(
        {"math.cos", "math.isfinite", "math.pi", "math.sin", "re.compile"}
    ),
    "src/mdcp/temporal/contract_gate.py": frozenset({"pandas.DataFrame"}),
    "src/mdcp/temporal/evidence.py": frozenset({"re.IGNORECASE", "re.MULTILINE", "re.compile"}),
    _TRUSTED_FIREWALL_PATH: frozenset(
        {
            "ast.AST",
            "ast.Attribute",
            "ast.Call",
            "ast.Import",
            "ast.ImportFrom",
            "ast.Name",
            "ast.expr",
            "ast.iter_child_nodes",
            "ast.parse",
            "ast.walk",
            "pandas.DataFrame",
            "pandas.read_csv",
            "re.compile",
            "sys.getprofile",
            "sys.setprofile",
        }
    ),
    "src/mdcp/temporal/golden_vectors.py": frozenset(
        {"hashlib.sha256", "math.isfinite", "struct.error", "struct.pack"}
    ),
}
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


def _allowed_dunder_attribute(node: ast.Attribute, logical_path: str) -> bool:
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
    return False


def _import_allowed(logical_path: str, module: str, imported_name: str | None) -> bool:
    if imported_name is not None and module in _ALLOWED_DIRECT_IMPORTS:
        return imported_name in _ALLOWED_DIRECT_IMPORTS[module]
    return (module, imported_name) in _FORMAL_IMPORT_ALLOWLIST.get(logical_path, frozenset())


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
                bindings[local_name] = qualified_name
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
                bindings[local_name] = f"{module}.{alias.name}" if module else alias.name

    return bindings, frozenset(module_roots)


def _audit_tree(tree: ast.AST, logical_path: str) -> None:
    bindings, module_roots = _build_bindings(tree, logical_path)
    allowed_module_attributes = _FORMAL_MODULE_ATTRIBUTE_ALLOWLIST.get(logical_path, frozenset())
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name | ast.Attribute):
            qualified_name = _attribute_name(node, bindings)
            if qualified_name in _FORBIDDEN_DYNAMIC_REFERENCES or (
                isinstance(node, ast.Attribute)
                and (
                    (
                        node.attr.startswith("_")
                        and not _allowed_dunder_attribute(node, logical_path)
                    )
                    or node.attr in _FORBIDDEN_REFLECTION_ATTRIBUTES
                    or (qualified_name is not None and _is_forbidden_module(qualified_name))
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
            source = source_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=logical_path)
        except (OSError, UnicodeError, SyntaxError):
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
