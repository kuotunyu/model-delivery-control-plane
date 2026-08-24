from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from mdcp.common.digests import sha256_hex

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
                continue
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
        if function_name not in {"importlib.import_module", "__import__"}:
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            _fail()
        module_name = node.args[0].value
        if not isinstance(module_name, str) or _is_forbidden_module(module_name):
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
