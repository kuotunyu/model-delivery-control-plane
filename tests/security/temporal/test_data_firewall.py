from __future__ import annotations

import runpy
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
        "import pandas as pd\nrecovered = pd.read_csv('synthetic-h2.csv')",
        "import pandas as pd\nreader = pd.read_csv\nrecovered = reader('synthetic-h2.csv')",
    ),
)
def test_static_firewall_rejects_unbounded_pandas_reader_capability(
    tmp_path: Path,
    source: str,
) -> None:
    logical_path = "src/mdcp/temporal/firewall.py"
    _write_logical_module(tmp_path, logical_path, source)

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


def test_static_firewall_rejects_retargeted_approved_file_receiver(tmp_path: Path) -> None:
    logical_path = "src/mdcp/predictor/app_v2.py"
    _write_logical_module(
        tmp_path,
        logical_path,
        "import os\n"
        "from pathlib import Path\n"
        "def runtime_from_environment():\n"
        "    descriptor_path = (\n"
        "        Path(os.environ['MDCP_DESCRIPTOR_PATH']).parent / 'synthetic-h2.csv'\n"
        "    )\n"
        "    return descriptor_path.read_text(encoding='utf-8')",
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "shadow",
    (
        "def Path(value, _real=Path):\n    return _real('synthetic-h2.json')\n",
        "class Path:\n    pass\n",
    ),
)
def test_static_firewall_rejects_definition_shadowing_of_imported_capability(
    tmp_path: Path,
    shadow: str,
) -> None:
    logical_path = "src/mdcp/predictor/app_v2.py"
    _write_logical_module(
        tmp_path,
        logical_path,
        "import os\n"
        "from pathlib import Path\n"
        f"{shadow}"
        "def runtime_from_environment():\n"
        "    descriptor_path = Path(os.environ['MDCP_DESCRIPTOR_PATH'])\n"
        "    return descriptor_path.read_text(encoding='utf-8')",
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_rejects_argument_shadowing_of_imported_capability(
    tmp_path: Path,
) -> None:
    logical_path = "src/mdcp/predictor/app_v2.py"
    _write_logical_module(
        tmp_path,
        logical_path,
        "import os\n"
        "from pathlib import Path\n"
        "def runtime_from_environment(Path=Path):\n"
        "    descriptor_path = Path(os.environ['MDCP_DESCRIPTOR_PATH'])\n"
        "    return descriptor_path.read_text(encoding='utf-8')",
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("logical_path", "function_name"),
    (
        ("src/mdcp/temporal/contract_gate.py", "_path_digest"),
        ("src/mdcp/temporal/contract_gate.py", "_checked_json"),
        ("src/mdcp/temporal/golden_vectors.py", "verify_golden_vector_manifest"),
    ),
)
def test_static_firewall_rejects_retargeted_file_path_parameters(
    tmp_path: Path,
    logical_path: str,
    function_name: str,
) -> None:
    _write_logical_module(
        tmp_path,
        logical_path,
        "from pathlib import Path\n"
        f"def {function_name}(path: Path):\n"
        "    path = Path('synthetic-h2.csv')\n"
        "    return path.read_bytes()",
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("needle", "replacement"),
    (
        (
            "        source_path = repository_root / logical_path\n",
            "        source_path = repository_root / logical_path\n"
            "        source_path = Path('synthetic-h2.py')\n",
        ),
        (
            "from __future__ import annotations\n\n",
            "from __future__ import annotations\n\n__file__ = 'synthetic-h2.py'\n\n",
        ),
        (
            "    code = function.__code__\n",
            "    code = function.__code__\n"
            "    code = type('Code', (), {'co_filename': 'synthetic-h2.py'})()\n",
        ),
    ),
)
def test_static_firewall_rejects_retargeted_trusted_file_sources(
    tmp_path: Path,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/firewall.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) == 1
    _write_logical_module(tmp_path, logical_path, source.replace(needle, replacement, 1))

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_rejects_writes_to_approved_environment_keys(tmp_path: Path) -> None:
    logical_path = "src/mdcp/predictor/app_v2.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    needle = "import os\n"
    assert source.count(needle) == 1
    mutated = source.replace(
        needle,
        needle + "os.environ['MDCP_DESCRIPTOR_PATH'] = 'synthetic-h2.json'\n",
        1,
    )
    _write_logical_module(tmp_path, logical_path, mutated)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "call",
    (
        "_path_digest(Path('synthetic-h2.bin'))",
        "_checked_json(Path('synthetic-h2.json'))",
        "verify_golden_vector_manifest(Path('synthetic-h2.json'))",
    ),
)
def test_static_firewall_rejects_unscoped_file_helper_calls(
    tmp_path: Path,
    call: str,
) -> None:
    logical_path = "src/mdcp/temporal/contract_gate.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, f"{source}\n{call}")

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize("source", ("breakpoint()", "help('modules')"))
def test_static_firewall_rejects_runtime_import_and_evaluation_hooks(
    tmp_path: Path,
    source: str,
) -> None:
    logical_path = "src/mdcp/temporal/adapter.py"
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


def test_static_firewall_rejects_executable_source_encoding_polyglot(
    tmp_path: Path,
) -> None:
    logical_path = "src/mdcp/temporal/contract_gate.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    sentinel_path = tmp_path / "synthetic-sentinel.json"
    sentinel_path.write_text('{"sentinel":"UTF7_ROW_RECOVERED"}', encoding="utf-8")
    target = tmp_path / logical_path
    target.parent.mkdir(parents=True)
    polyglot = (
        b"# coding: utf-7\n"
        + source.encode("ascii")
        + b"\n#+AAo-RECOVERED = _checked_json(Path("
        + repr(sentinel_path.as_posix()).encode("ascii")
        + b"))\n"
    )
    target.write_bytes(polyglot)

    executed = runpy.run_path(str(target))
    assert executed["RECOVERED"] == {"sentinel": "UTF7_ROW_RECOVERED"}

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "prefix",
    (
        b"# coding: latin-1\n",
        b"# coding: utf_8\n",
        b"\xef\xbb\xbf# coding: utf-8\n",
    ),
)
def test_static_firewall_rejects_noncanonical_source_encoding_markers(
    tmp_path: Path,
    prefix: bytes,
) -> None:
    logical_path = "formal.py"
    (tmp_path / logical_path).write_bytes(prefix + b"answer = 1\n")

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_accepts_canonical_utf8_source_cookie(tmp_path: Path) -> None:
    logical_path = "formal.py"
    (tmp_path / logical_path).write_bytes(b"# coding: utf-8\nanswer = 1\n")

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"


@pytest.mark.parametrize(
    ("logical_path", "source"),
    (
        ("src/mdcp/temporal/folds.py", "from pathlib import Path\ntarget = Path"),
        ("src/mdcp/temporal/trials.py", "from pathlib import Path\ntarget = Path"),
        ("src/mdcp/temporal/folds.py", "import pandas as pd\ntarget = pd.read_csv"),
        ("src/mdcp/temporal/trials.py", "import math\ntarget = math.sqrt"),
    ),
    ids=(
        "folds-unknown-import",
        "trials-unknown-import",
        "folds-unapproved-module-attribute",
        "trials-unapproved-module-attribute",
    ),
)
def test_static_firewall_keeps_new_temporal_paths_closed_to_unapproved_capabilities(
    tmp_path: Path,
    logical_path: str,
    source: str,
) -> None:
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("case_id", "source"),
    (
        ("unknown-direct", "from pathlib import Path\ntarget = Path"),
        ("unknown-alias", "from pathlib import Path as HiddenPath\ntarget = HiddenPath"),
        ("unknown-qualified", "import math\ntarget = math.sqrt"),
        ("dynamic-import", "target = __import__('math')"),
    ),
)
def test_static_firewall_keeps_completeness_path_closed_to_unapproved_capabilities(
    tmp_path: Path,
    case_id: str,
    source: str,
) -> None:
    logical_path = "src/mdcp/temporal/completeness.py"
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$") as caught:
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert case_id not in str(caught.value)
    assert source not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_static_firewall_allows_committed_completeness_module(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/completeness.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"
    assert result.checked_paths == (logical_path,)
    assert len(result.implementation_sha256) == 64


@pytest.mark.parametrize(
    ("case_id", "source"),
    (
        ("unknown-direct", "from pathlib import Path\ntarget = Path"),
        ("unknown-alias", "from pathlib import Path as HiddenPath\ntarget = HiddenPath"),
        ("unknown-qualified", "import math\ntarget = math.sqrt"),
        ("dynamic-import", "target = __import__('math')"),
    ),
)
def test_static_firewall_keeps_evaluation_path_closed_to_unapproved_capabilities(
    tmp_path: Path,
    case_id: str,
    source: str,
) -> None:
    logical_path = "src/mdcp/temporal/evaluation.py"
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$") as caught:
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert case_id not in str(caught.value)
    assert source not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_static_firewall_allows_committed_evaluation_module(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/evaluation.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"
    assert result.checked_paths == (logical_path,)
    assert len(result.implementation_sha256) == 64


@pytest.mark.parametrize(
    ("case_id", "source"),
    (
        ("unknown-direct", "from pathlib import Path\ntarget = Path"),
        ("unknown-alias", "from pathlib import Path as HiddenPath\ntarget = HiddenPath"),
        ("unknown-qualified", "import math\ntarget = math.sqrt"),
        ("dynamic-import", "target = __import__('math')"),
    ),
)
def test_static_firewall_keeps_selection_path_closed_to_unapproved_capabilities(
    tmp_path: Path,
    case_id: str,
    source: str,
) -> None:
    logical_path = "src/mdcp/temporal/selection.py"
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$") as caught:
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert case_id not in str(caught.value)
    assert source not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_static_firewall_allows_committed_selection_module(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/selection.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"
    assert result.checked_paths == (logical_path,)
    assert len(result.implementation_sha256) == 64


def test_static_firewall_allows_exact_fold_timestamp_normalization(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/folds.py"
    _write_logical_module(
        tmp_path,
        logical_path,
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class FoldSpec:\n"
        "    train_start: object\n"
        "    train_end: object\n"
        "    validation_start: object\n"
        "    validation_end: object\n"
        "    def __post_init__(self) -> None:\n"
        "        train_start = self.train_start\n"
        "        train_end = self.train_end\n"
        "        validation_start = self.validation_start\n"
        "        validation_end = self.validation_end\n"
        "        object.__setattr__(self, 'train_start', train_start)\n"
        "        object.__setattr__(self, 'train_end', train_end)\n"
        "        object.__setattr__(self, 'validation_start', validation_start)\n"
        "        object.__setattr__(self, 'validation_end', validation_end)",
    )

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"


def test_real_formal_source_set_passes_with_deterministic_discovery() -> None:
    result = audit_static_h2_firewall(REPOSITORY_ROOT)
    expected_temporal_paths = tuple(
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in sorted(
            (REPOSITORY_ROOT / FORMAL_TEMPORAL_PACKAGE_ROOT).glob("*.py"),
            key=lambda path: path.as_posix(),
        )
        if path.name != "search_identity.py"
    )

    assert result.verdict == "PASS"
    assert result.checked_paths == tuple(sorted((*FORMAL_V2_FIXED_PATHS, *expected_temporal_paths)))
    assert len(result.implementation_sha256) == 64


def test_runtime_guard_and_command_surfaces_are_discovered() -> None:
    result = audit_static_h2_firewall(REPOSITORY_ROOT)

    assert {
        "src/mdcp/temporal/runtime_guards.py",
        "src/mdcp/temporal/runner.py",
        "src/mdcp/temporal/cli.py",
    }.issubset(result.checked_paths)


@pytest.mark.parametrize(
    ("mutation", "needle", "replacement"),
    (
        ("unlisted-import", "import subprocess\n", "import inspect\nimport subprocess\n"),
        ("module-attribute", "import time\n", "import time\nunused = time.sleep\n"),
        (
            "environment-key",
            "import os\n",
            "import os\nunused = os.environ['MDCP_REVIEW_H2']\n",
        ),
        (
            "subprocess-argument",
            '("git", "rev-parse", "HEAD")',
            '("git", "rev-parse", "--show-toplevel")',
        ),
        (
            "file-path",
            'Path("/proc/self/status")',
            'Path("/etc/passwd")',
        ),
    ),
)
def test_runtime_guard_capabilities_remain_exact(
    tmp_path: Path,
    mutation: str,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) == 1, mutation
    _write_logical_module(tmp_path, logical_path, source.replace(needle, replacement, 1))

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_development_partition_type_has_no_h2_capability() -> None:
    assert tuple(DevelopmentPartitions.__dataclass_fields__) == ("train", "h1")
    assert "h2" not in vars(DevelopmentPartitions)
    assert "open_h2" not in vars(DevelopmentPartitions)
