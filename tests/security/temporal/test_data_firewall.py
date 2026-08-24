from __future__ import annotations

import ast
from pathlib import Path

from mdcp.workload.splits import DevelopmentPartitions

REPOSITORY_ROOT = Path(__file__).parents[3]
TEMPORAL_SOURCE_ROOT = REPOSITORY_ROOT / "src" / "mdcp" / "temporal"
FORBIDDEN_H2_SYMBOLS = frozenset({"DatasetPartitions", "open_h2", "split_rows"})


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
    return names


def test_formal_temporal_modules_cannot_import_h2_capabilities() -> None:
    violations: dict[str, list[str]] = {}
    for path in sorted(TEMPORAL_SOURCE_ROOT.glob("*.py")):
        imported = _imported_names(ast.parse(path.read_text(encoding="utf-8")))
        forbidden = sorted(imported & FORBIDDEN_H2_SYMBOLS)
        if forbidden:
            violations[path.name] = forbidden

    assert violations == {}


def test_development_partition_type_has_no_h2_capability() -> None:
    assert tuple(DevelopmentPartitions.__dataclass_fields__) == ("train", "h1")
    assert "h2" not in vars(DevelopmentPartitions)
    assert "open_h2" not in vars(DevelopmentPartitions)
