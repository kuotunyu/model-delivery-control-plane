from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import FrameType
from typing import Literal

import pandas as pd

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
_ALLOWED_DIRECT_IMPORTS = {
    "mdcp.workload.dataset": frozenset({"load_uci_development_archive"}),
    "mdcp.workload.splits": frozenset({"DevelopmentPartitions", "split_development_rows"}),
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
_LEGACY_LOAD_CODE = _BOUNDED_LOADER.__globals__["load_uci_archive"].__code__
_LEGACY_SPLIT_CODE = _DEVELOPMENT_SPLITTER.__globals__["split_rows"].__code__
_DATASET_PARTITIONS = _DEVELOPMENT_SPLITTER.__globals__["DatasetPartitions"]
_OPEN_H2_CODE = _DATASET_PARTITIONS.open_h2.__code__
_FORBIDDEN_CALL_CODES = {
    _LEGACY_LOAD_CODE: "load_uci_archive",
    _LEGACY_SPLIT_CODE: "split_rows",
    _OPEN_H2_CODE: "DatasetPartitions.open_h2",
}


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


@dataclass(frozen=True)
class DevelopmentBoundaryResult:
    schema_version: Literal["mdcp.development-boundary.v1"]
    verdict: Literal["PASS"]
    archive_sha256: str
    development_row_count: Literal[13_003]
    development_rows_sha256: str
    train_row_count: Literal[8_645]
    train_rows_sha256: str
    h1_row_count: Literal[4_358]
    h1_rows_sha256: str
    read_csv_nrows: tuple[Literal[13_003]]
    forbidden_call_counts: dict[str, int]
    h2_status: Literal["SEALED_NOT_LOADED"]
    h2_loaded_rows: Literal[0]


@dataclass(frozen=True)
class BehavioralFirewallBody:
    schema_version: Literal["mdcp.behavioral-h2-firewall.v1"]
    verdict: Literal["PASS"]
    fixture_recipe_sha256: str
    development_boundary: DevelopmentBoundaryResult
    static_firewall_implementation_sha256: str
    behavioral_firewall_implementation_sha256: str
    bounded_loader_implementation_sha256: str
    development_split_implementation_sha256: str


@dataclass(frozen=True)
class BehavioralFirewallResult:
    body: BehavioralFirewallBody
    behavioral_result_sha256: str


def _fail() -> None:
    raise StaticFirewallError()


def _is_forbidden_module(qualified_name: str) -> bool:
    return any(
        qualified_name == module or qualified_name.startswith(f"{module}.")
        for module in _FORBIDDEN_MODULES
    )


def _attribute_name(node: ast.expr, bindings: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return bindings.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _attribute_name(node.value, bindings)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _build_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_module(alias.name):
                    _fail()
                local_name = alias.asname or alias.name.split(".", 1)[0]
                qualified_name = alias.name if alias.asname else local_name
                bindings[local_name] = qualified_name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
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
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                bindings[local_name] = f"{module}.{alias.name}" if module else alias.name
    return bindings


def _audit_tree(tree: ast.AST) -> None:
    bindings = _build_bindings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            qualified_name = _attribute_name(node, bindings)
            if qualified_name is not None and _is_forbidden_module(qualified_name):
                _fail()
        if not isinstance(node, ast.Call):
            continue
        function_name = _attribute_name(node.func, bindings)
        if function_name not in {
            "importlib.import_module",
            "__import__",
            "builtins.__import__",
        }:
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            _fail()
        module_name = node.args[0].value
        if (
            not isinstance(module_name, str)
            or module_name.startswith(".")
            or _is_forbidden_module(module_name)
        ):
            _fail()
        if function_name in {"__import__", "builtins.__import__"}:
            positional_level = node.args[4] if len(node.args) > 4 else None
            keyword_level = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "level"),
                None,
            )
            for level in (positional_level, keyword_level):
                if not isinstance(level, ast.Constant) or not isinstance(level.value, int):
                    if level is not None:
                        _fail()
                    continue
                if level.value != 0:
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
        _audit_tree(tree)

    return StaticFirewallResult(
        schema_version="mdcp.static-h2-firewall.v1",
        verdict="PASS",
        checked_paths=checked_paths,
        implementation_sha256=sha256_hex(Path(__file__).read_bytes()),
    )


def _implementation_sha256(function: object) -> str:
    code = getattr(function, "__code__", None)
    if code is None:
        raise BehavioralFirewallError()
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
    forbidden_call_counts = {name: 0 for name in _FORBIDDEN_CALL_CODES.values()}
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
        capability = _FORBIDDEN_CALL_CODES.get(frame.f_code)
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
