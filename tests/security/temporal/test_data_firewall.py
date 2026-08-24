from __future__ import annotations

from pathlib import Path

import pytest

from mdcp.temporal.firewall import (
    FORMAL_TEMPORAL_PACKAGE_ROOT,
    FORMAL_V2_FIXED_PATHS,
    StaticFirewallError,
    audit_static_h2_firewall,
)
from mdcp.workload.splits import DevelopmentPartitions

REPOSITORY_ROOT = Path(__file__).parents[3]
FIXED_REASON_CODE = "H2_IMPORT_CAPABILITY_FORBIDDEN"

FORBIDDEN_MODULES = {
    "direct": "from mdcp.workload.dataset import load_uci_archive",
    "from_alias": "from mdcp.workload.splits import split_rows as narrow",
    "module": ("import mdcp.workload.dataset\ntarget = mdcp.workload.dataset.load_uci_archive"),
    "module_alias": ("import mdcp.workload.splits as parts\ntarget = parts.split_rows"),
    "package_member": (
        "from mdcp.workload import splits as parts\ntarget = parts.DatasetPartitions"
    ),
    "qualified_dataset_partitions": (
        "import mdcp.workload.splits as partitions\ntarget = partitions.DatasetPartitions"
    ),
    "qualified_open_h2": ("import mdcp.workload.splits as partitions\ntarget = partitions.open_h2"),
    "dynamic_literal": (
        "import importlib\ntarget = importlib.import_module('mdcp.workload.dataset')"
    ),
    "dynamic_alias": (
        "import importlib as loader\ntarget = loader.import_module('mdcp.workload.splits')"
    ),
    "dynamic_from_alias": (
        "from importlib import import_module as loader\ntarget = loader('mdcp.workload.dataset')"
    ),
    "dunder_import": "target = __import__('mdcp.workload.splits')",
    "dynamic_unknown": ("import importlib\ntarget = importlib.import_module(module_name)"),
    "relative_direct": (
        "from ..workload.dataset import load_uci_archive\ntarget = load_uci_archive"
    ),
    "relative_alias": (
        "from ..workload.dataset import load_uci_archive as loader\ntarget = loader"
    ),
    "relative_qualified": (
        "from ..workload import dataset as source\ntarget = source.load_uci_archive"
    ),
    "dynamic_relative": (
        "import importlib\ntarget = importlib.import_module('.dataset', package='mdcp.workload')"
    ),
    "dynamic_relative_alias": (
        "import importlib as loader\n"
        "target = loader.import_module('.splits', package='mdcp.workload')"
    ),
    "dunder_relative": ("target = __import__('.dataset', globals(), locals(), (), 1)"),
    "dunder_relative_qualified": (
        "import builtins\ntarget = builtins.__import__('.splits', globals(), locals(), (), 1)"
    ),
    "dynamic_relative_rebound": (
        "import importlib\n"
        "loader = importlib.import_module\n"
        "target = loader('.dataset', package='mdcp.workload')"
    ),
    "dunder_relative_rebound": (
        "import builtins\n"
        "loader = builtins.__import__\n"
        "target = loader('dataset', globals(), locals(), (), 1)"
    ),
    "dynamic_relative_wildcard": (
        "from importlib import *\ntarget = import_module('.dataset', package='mdcp.workload')"
    ),
}

ALLOWED_NARROW_IMPORTS = (
    "from mdcp.workload.dataset import load_uci_development_archive",
    "from mdcp.workload.splits import DevelopmentPartitions",
    "from mdcp.workload.splits import split_development_rows",
)


def _write_formal_module(root: Path, source: str) -> str:
    logical_path = "formal.py"
    (root / logical_path).write_text(source + "\n", encoding="utf-8")
    return logical_path


@pytest.mark.parametrize(("case_id", "source"), FORBIDDEN_MODULES.items())
def test_static_firewall_rejects_legacy_capability_forms_without_echo(
    tmp_path: Path,
    case_id: str,
    source: str,
) -> None:
    logical_path = _write_formal_module(tmp_path, source)

    with pytest.raises(StaticFirewallError) as caught:
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert caught.value.reason_code == FIXED_REASON_CODE
    assert str(caught.value) == FIXED_REASON_CODE
    assert case_id not in str(caught.value)
    assert source not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


@pytest.mark.parametrize("source", ALLOWED_NARROW_IMPORTS)
def test_static_firewall_allows_only_narrow_development_imports(
    tmp_path: Path,
    source: str,
) -> None:
    logical_path = _write_formal_module(tmp_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"
    assert result.checked_paths == (logical_path,)
    assert len(result.implementation_sha256) == 64


@pytest.mark.parametrize(
    "source",
    (
        "from mdcp.workload.dataset import DatasetIntegrityError",
        "from mdcp.workload.splits import H2SealedError",
        "from mdcp.workload.splits import open_h2",
        "from mdcp.workload.splits import DatasetPartitions",
    ),
)
def test_static_firewall_rejects_non_allowlisted_direct_symbols(
    tmp_path: Path,
    source: str,
) -> None:
    logical_path = _write_formal_module(tmp_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_fails_closed_on_missing_path_and_syntax(tmp_path: Path) -> None:
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=("missing.py",))

    logical_path = _write_formal_module(tmp_path, "from mdcp.workload import (")
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_real_formal_source_set_passes_with_deterministic_discovery() -> None:
    result = audit_static_h2_firewall(REPOSITORY_ROOT)
    expected_temporal_paths = tuple(
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in sorted(
            (REPOSITORY_ROOT / FORMAL_TEMPORAL_PACKAGE_ROOT).glob("*.py"),
            key=lambda path: path.as_posix(),
        )
    )

    assert result.verdict == "PASS"
    assert result.checked_paths == tuple(sorted((*FORMAL_V2_FIXED_PATHS, *expected_temporal_paths)))
    assert len(result.implementation_sha256) == 64


def test_development_partition_type_has_no_h2_capability() -> None:
    assert tuple(DevelopmentPartitions.__dataclass_fields__) == ("train", "h1")
    assert "h2" not in vars(DevelopmentPartitions)
    assert "open_h2" not in vars(DevelopmentPartitions)
