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
    "dynamic_relative_destructured": (
        "import importlib\n"
        "(loader,) = (importlib.import_module,)\n"
        "target = loader('.dataset', package='mdcp.workload')"
    ),
    "dunder_relative_expanded_level": (
        "options = {'level': 2}\n"
        "target = __import__('workload.dataset', globals(), locals(), (), **options)"
    ),
    "dynamic_relative_reflective": (
        "import importlib\n"
        "loader = getattr(importlib, 'import_module')\n"
        "target = loader('.dataset', package='mdcp.workload')"
    ),
    "dunder_relative_reflective": (
        "import builtins\n"
        "loader = getattr(builtins, '__import__')\n"
        "target = loader('dataset', globals(), locals(), (), 1)"
    ),
    "dunder_relative_builtin_namespace": (
        "loader = getattr(__builtins__, '__import__')\n"
        "target = loader('dataset', globals(), locals(), (), 1)"
    ),
    "dunder_relative_globals_subscript": (
        "namespace = globals()['__builtins__']\n"
        "loader = namespace['__import__'] if isinstance(namespace, dict) "
        "else getattr(namespace, '__import__')\n"
        "target = loader('workload.splits', globals(), locals(), (), 2)"
    ),
    "dunder_relative_globals_get": (
        "namespace = globals().get('__builtins__')\n"
        "loader = namespace.get('__import__') if isinstance(namespace, dict) "
        "else getattr(namespace, '__import__')\n"
        "target = loader('workload.dataset', globals(), locals(), (), level=2)"
    ),
    "narrow_function_globals": (
        "from mdcp.workload.dataset import load_uci_development_archive\n"
        "target = load_uci_development_archive.__globals__['load_uci_archive']"
    ),
    "rebound_narrow_function_globals": (
        "from mdcp.workload.dataset import load_uci_development_archive\n"
        "bounded = load_uci_development_archive\n"
        "target = bounded.__globals__['load_uci_archive']"
    ),
    "reflective_narrow_function_globals": (
        "from mdcp.workload.splits import split_development_rows\n"
        "namespace = getattr(split_development_rows, '__globals__')\n"
        "target = namespace['split_rows']"
    ),
    "computed_reflective_narrow_function_globals": (
        "from mdcp.workload.splits import split_development_rows\n"
        "attribute = '__' + 'globals__'\n"
        "namespace = getattr(split_development_rows, attribute)\n"
        "target = namespace['DatasetPartitions']"
    ),
    "dunder_getattribute_narrow_function_globals": (
        "from mdcp.workload.dataset import load_uci_development_archive\n"
        "namespace = object.__getattribute__(load_uci_development_archive, '__globals__')\n"
        "target = namespace['load_uci_archive']"
    ),
    "narrow_function_builtin_import": (
        "from mdcp.workload.dataset import load_uci_development_archive\n"
        "namespace = load_uci_development_archive.__globals__['__builtins__']\n"
        "target = namespace['__import__']"
    ),
    "getattr_sys_modules": (
        "import sys\n"
        "modules = getattr(sys, 'modules')\n"
        "target = modules['mdcp.workload.dataset'].load_uci_archive"
    ),
    "sys_dict_modules": (
        "import sys\n"
        "modules = sys.__dict__['modules']\n"
        "target = modules['mdcp.workload.splits'].split_rows"
    ),
    "eval_narrow_function_globals": (
        "from mdcp.workload.dataset import load_uci_development_archive\n"
        "target = eval(\"load_uci_development_archive.__globals__['load_uci_archive']\")"
    ),
    "exec_narrow_function_globals": (
        "from mdcp.workload.dataset import load_uci_development_archive\n"
        "exec(\"target = load_uci_development_archive.__globals__['load_uci_archive']\")"
    ),
    "compiled_narrow_function_globals": (
        "from mdcp.workload.dataset import load_uci_development_archive\n"
        "target = compile(\"load_uci_development_archive.__globals__\", '<formal>', 'eval')"
    ),
    "transitive_pandas_import_helper": (
        "import pandas as pd\n"
        "target = pd.compat._optional.import_optional_dependency("
        "'mdcp.workload.dataset').load_uci_archive"
    ),
    "direct_pandas_import_helper": (
        "from pandas.compat._optional import import_optional_dependency\n"
        "target = import_optional_dependency('mdcp.workload.splits').split_rows"
    ),
    "zipfile_archive_loader": "import zipfile\ntarget = zipfile.ZipFile",
    "direct_zipfile_archive_loader": "from zipfile import ZipFile\ntarget = ZipFile",
    "unreviewed_process_surface": "import os\ntarget = os.popen('python')",
    "builtin_function_self_import": (
        "target = print.__self__.__import__("
        "'mdcp.workload.dataset', fromlist=['load_uci_archive']).load_uci_archive"
    ),
    "traceback_frame_builtin_import": (
        "try:\n"
        "    1 / 0\n"
        "except Exception as error:\n"
        "    target = error.__traceback__.tb_frame.f_builtins['__import__']("
        "'mdcp.workload.splits', fromlist=['split_rows']).split_rows"
    ),
    "generator_frame_builtin_import": (
        "generator = (value for value in ())\n"
        "target = generator.gi_frame.f_builtins['__import__']("
        "'mdcp.workload.dataset', fromlist=['load_uci_archive']).load_uci_archive"
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


def _write_logical_module(root: Path, logical_path: str, source: str) -> str:
    target = root / logical_path
    target.parent.mkdir(parents=True)
    target.write_text(source + "\n", encoding="utf-8")
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
    ("logical_path", "source"),
    (
        (
            "src/mdcp/temporal/contract_gate.py",
            "import pandas as pd\n"
            "dependency_surface = pd\n"
            "target = dependency_surface.compat._optional.import_optional_dependency("
            "'mdcp.workload.dataset').load_uci_archive",
        ),
        (
            "src/mdcp/temporal/contract_gate.py",
            "import pandas as pd\n"
            "(dependency_surface,) = (pd,)\n"
            "target = dependency_surface.compat._optional.import_optional_dependency("
            "'mdcp.workload.splits').split_rows",
        ),
        (
            "src/mdcp/predictor/app_v2.py",
            "import os\nprocess_surface = os\ntarget = process_surface.popen('python')",
        ),
    ),
)
def test_static_firewall_rejects_rebinding_an_approved_module_surface(
    tmp_path: Path,
    logical_path: str,
    source: str,
) -> None:
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("logical_path", "source"),
    (
        (
            "src/mdcp/predictor/app_v2.py",
            "from pathlib import Path\ntarget = Path._flavour.os.popen",
        ),
        (
            "src/mdcp/temporal/contract_gate.py",
            "from pathlib import Path\ntarget = Path._flavour.os.open",
        ),
    ),
)
def test_static_firewall_rejects_private_attribute_capability_recovery(
    tmp_path: Path,
    logical_path: str,
    source: str,
) -> None:
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize("method", ("eval", "query"))
def test_static_firewall_rejects_object_level_string_evaluation(
    tmp_path: Path,
    method: str,
) -> None:
    logical_path = "src/mdcp/temporal/firewall.py"
    source = (
        "import pandas as pd\n"
        "frame = pd.DataFrame({'x': [1]})\n"
        f"target = frame.{method}("
        "\"@__builtins__.__import__('mdcp.workload.dataset', "
        'fromlist=[\'load_uci_archive\'])", engine="python")'
    )
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "source",
    (
        "import os\n"
        "with open(os.environ['MDCP_REVIEW_H2'], 'rb') as stream:\n"
        "    recovered = stream.read()",
        "import os\n"
        "from pathlib import Path\n"
        "recovered = Path(os.environ['MDCP_REVIEW_H2']).read_bytes()",
        "with open('descriptor.json', 'rb') as stream:\n    recovered = stream.read()",
        "from pathlib import Path\nrecovered = Path('descriptor.json').read_bytes()",
    ),
)
def test_static_firewall_rejects_unscoped_public_file_access(
    tmp_path: Path,
    source: str,
) -> None:
    logical_path = "src/mdcp/predictor/app_v2.py"
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_rejects_file_reader_capability_alias(tmp_path: Path) -> None:
    logical_path = "src/mdcp/predictor/app_v2.py"
    _write_logical_module(
        tmp_path,
        logical_path,
        "from pathlib import Path\n"
        "reader = Path('descriptor.json').read_bytes\n"
        "recovered = reader()",
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "source",
    (
        "import os\nrecovered = os.environ['MDCP_REVIEW_H2']",
        "import os\nrecovered = os.getenv('MDCP_REVIEW_H2')",
    ),
)
def test_static_firewall_rejects_unapproved_environment_keys(
    tmp_path: Path,
    source: str,
) -> None:
    logical_path = "src/mdcp/predictor/app_v2.py"
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


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
