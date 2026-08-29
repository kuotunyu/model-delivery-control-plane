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
    "module": "import mdcp.workload.dataset",
    "module_alias": "import mdcp.workload.splits as parts",
    "relative_direct": "from ..workload.dataset import load_uci_archive",
    "dynamic_literal": "import importlib\nimportlib.import_module('mdcp.workload.dataset')",
    "dynamic_relative": (
        "import importlib\nimportlib.import_module('.dataset', package='mdcp.workload')"
    ),
    "dunder_relative": "__import__('.dataset', globals(), locals(), (), 1)",
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
def test_finite_process_boundary_rejects_exact_forbidden_import_forms_without_echo(
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
def test_static_firewall_rejects_narrow_development_imports_outside_exact_owner(
    tmp_path: Path,
    source: str,
) -> None:
    logical_path = _write_formal_module(tmp_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "source",
    (
        "def transform(value, name):\n    return getattr(value, name)",
        "def transform(value):\n    return value._application_state",
        "def transform(stream):\n    return stream.read()",
        "def transform(action):\n    return action()",
    ),
)
def test_finite_process_boundary_is_defense_in_depth_not_python_semantics(
    tmp_path: Path,
    source: str,
) -> None:
    """The scanner is finite defense-in-depth, not a Python semantics proof."""
    logical_path = _write_formal_module(tmp_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"


def test_finite_process_boundary_keeps_dynamic_relative_import_fail_closed(
    tmp_path: Path,
) -> None:
    logical_path = _write_formal_module(
        tmp_path,
        "import importlib\nimportlib.import_module('.dataset', package='mdcp.workload')",
    )

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


def test_static_firewall_rejects_unbounded_pandas_reader_capability(
    tmp_path: Path,
) -> None:
    logical_path = "src/mdcp/temporal/firewall.py"
    _write_logical_module(
        tmp_path,
        logical_path,
        "import pandas as pd\nrecovered = pd.read_csv('synthetic-h2.csv')",
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


def test_static_firewall_allows_only_the_closed_run_evidence_capabilities(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"
    assert result.checked_paths == (logical_path,)


@pytest.mark.parametrize(
    ("retired_name", "body"),
    (
        ("_build_formal_execution_plan", "    return protocol_path.read_bytes()\n"),
        (
            "_preflight_windows_destination",
            "    checked_destination = destination\n    return checked_destination.lstat()\n",
        ),
    ),
)
def test_fix_round_one_i5_retired_file_grants_cannot_be_resurrected(
    tmp_path: Path,
    retired_name: str,
    body: str,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    approved_root = tmp_path / "approved"
    _write_logical_module(approved_root, logical_path, source)
    assert audit_static_h2_firewall(approved_root, formal_paths=(logical_path,)).verdict == "PASS"

    argument = "protocol_path" if retired_name == "_build_formal_execution_plan" else "destination"
    mutation = f"\ndef {retired_name}({argument}):\n{body}"
    mutated_root = tmp_path / "mutated"
    _write_logical_module(mutated_root, logical_path, source + mutation)
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("module", "symbol"),
    (
        ("datetime", "datetime"),
        ("mdcp.common.enums", "GateVerdict"),
        ("mdcp.temporal.completeness", "AdapterOutcome"),
        ("mdcp.temporal.completeness", "LabelOutcome"),
        ("mdcp.temporal.completeness", "PredictionOutcome"),
        ("mdcp.temporal.evaluation", "qualify_trial"),
        ("mdcp.temporal.folds", "load_fold_specs"),
        ("mdcp.temporal.folds", "materialize_folds"),
        ("mdcp.temporal.runner", "DevelopmentRunBundle"),
        ("mdcp.temporal.runner", "DevelopmentRunError"),
        ("mdcp.temporal.runner", "EXACT_FOLD_IDS"),
        ("mdcp.temporal.runner", "FitLedger"),
        ("mdcp.temporal.runner", "FitPhase"),
        ("mdcp.temporal.runner", "_DevelopmentFoldResult"),
        ("mdcp.temporal.runner", "_evaluate_trial"),
        ("mdcp.temporal.runner", "_formal_groups"),
        ("mdcp.temporal.runner", "_private_fold_evidence"),
        ("mdcp.temporal.runner", "_process_fold"),
        ("mdcp.temporal.runner", "_public_result"),
        ("mdcp.temporal.runner", "_replay_digest"),
        ("mdcp.temporal.runner", "_valid_fold_result"),
        ("mdcp.temporal.runtime_guards", "RuntimeObservation"),
        ("mdcp.temporal.runtime_guards", "RuntimeStage"),
        ("mdcp.temporal.runtime_guards", "build_production_runtime_guard"),
        ("mdcp.temporal.search_identity", "FormalRunAuthorization"),
        ("mdcp.temporal.search_identity", "SearchReceipt"),
        ("mdcp.temporal.search_identity", "verify_search_freeze"),
        ("mdcp.temporal.selection", "ReplayFoldDigests"),
        ("mdcp.temporal.selection", "ReplayResult"),
        ("mdcp.temporal.selection", "ReplaySelectionSession"),
        ("mdcp.temporal.selection", "SelectionDecision"),
        ("mdcp.temporal.selection", "finalize_selection"),
        ("mdcp.temporal.trials", "_feature_names"),
        ("mdcp.temporal.trials", "_materialize_features"),
        ("mdcp.temporal.trials", "build_estimator"),
        ("mdcp.temporal.trials", "load_trial_specs"),
        ("mdcp.temporal.trials", "training_rows_for_trial"),
        ("mdcp.workload.dataset", "load_uci_development_archive"),
        ("mdcp.workload.splits", "split_development_rows"),
        ("threading", "Lock"),
    ),
)
def test_fix_round_one_i5_retired_import_grants_cannot_be_resurrected(
    tmp_path: Path,
    module: str,
    symbol: str,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    approved_root = tmp_path / "approved"
    _write_logical_module(approved_root, logical_path, source)
    assert audit_static_h2_firewall(approved_root, formal_paths=(logical_path,)).verdict == "PASS"

    mutated_root = tmp_path / "mutated"
    mutation = f"\nfrom {module} import {symbol} as task_five_retired_grant\n"
    _write_logical_module(mutated_root, logical_path, source + mutation)
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "attribute",
    (
        "ctypes.windll.kernel32.CompareStringOrdinal",
        "ctypes.windll.kernel32.FlushFileBuffers",
        "ctypes.windll.kernel32.GetFinalPathNameByHandleW",
        "ctypes.windll.kernel32.GetLastError",
        "ctypes.windll.kernel32.SetFileInformationByHandle",
        "ctypes.windll.kernel32.WriteFile",
        "ctypes.windll.ntdll",
        "ctypes.windll.ntdll.NtCreateFile",
    ),
)
def test_fix_round_one_i5_retired_module_attribute_grants_cannot_be_resurrected(
    tmp_path: Path,
    attribute: str,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    approved_root = tmp_path / "approved"
    _write_logical_module(approved_root, logical_path, source)
    assert audit_static_h2_firewall(approved_root, formal_paths=(logical_path,)).verdict == "PASS"

    mutated_root = tmp_path / "mutated"
    mutation = f"\ndef task_five_retired_call():\n    return {attribute}\n"
    _write_logical_module(mutated_root, logical_path, source + mutation)
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


def test_static_firewall_allows_exact_formal_worker_bootstrap(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/formal_worker.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"
    assert result.checked_paths == (logical_path,)


@pytest.mark.parametrize(
    ("case_id", "needle", "replacement"),
    (
        (
            "wrong-symbol",
            "    from mdcp.workload.dataset import load_uci_development_archive\n",
            "    from mdcp.workload.dataset import load_uci_archive\n",
        ),
        (
            "aliased-symbol",
            "    from mdcp.workload.dataset import load_uci_development_archive\n",
            (
                "    from mdcp.workload.dataset import "
                "load_uci_development_archive as hidden_loader\n"
            ),
        ),
        (
            "wrong-enclosing-function",
            (
                ") -> _WorkerContext:\n"
                "    from mdcp.common.canonical import canonicalize_json, parse_json_bytes\n"
            ),
            (
                ") -> _WorkerContext:\n"
                "    from mdcp.common.canonical import canonicalize_json, parse_json_bytes\n"
                "    from mdcp.workload.dataset import load_uci_development_archive\n"
            ),
        ),
        (
            "archive-read-before-marker",
            "    try:\n        marker_sha256 = _create_durable_marker(context)\n",
            (
                "    _hash_archive(context.archive_path)\n"
                "    try:\n        marker_sha256 = _create_durable_marker(context)\n"
            ),
        ),
        (
            "natural-run-before-marker",
            "    try:\n        marker_sha256 = _create_durable_marker(context)\n",
            (
                '    _execute_natural_run(context, "0" * 64)\n'
                "    try:\n        marker_sha256 = _create_durable_marker(context)\n"
            ),
        ),
        (
            "publication-before-marker",
            "    try:\n        marker_sha256 = _create_durable_marker(context)\n",
            (
                '    _publish_private(context.publications, b"")\n'
                "    try:\n        marker_sha256 = _create_durable_marker(context)\n"
            ),
        ),
        (
            "encoding-before-pre-seal",
            (
                "        files, public_result, selection_status = _formalize_natural(result)\n"
                "        _checkpoint(guard, RuntimeStage.PRE_SEAL)\n"
                "        private_bytes, private_identity = _encode_natural(files)\n"
            ),
            (
                "        files, public_result, selection_status = _formalize_natural(result)\n"
                "        private_bytes, private_identity = _encode_natural(files)\n"
                "        _checkpoint(guard, RuntimeStage.PRE_SEAL)\n"
            ),
        ),
        (
            "exit-before-private-publication",
            (
                "        _publish_private(context.publications, private_bytes)\n"
                "        exit_observation = _checkpoint(guard, RuntimeStage.EXIT)\n"
            ),
            (
                "        exit_observation = _checkpoint(guard, RuntimeStage.EXIT)\n"
                "        _publish_private(context.publications, private_bytes)\n"
            ),
        ),
        (
            "terminal-before-exit",
            "        exit_observation = _checkpoint(guard, RuntimeStage.EXIT)\n",
            (
                '        _publish_terminal(context.publications, b"")\n'
                "        exit_observation = _checkpoint(guard, RuntimeStage.EXIT)\n"
            ),
        ),
        (
            "response-flush-before-write",
            (
                "    if sys.stdout.buffer.write(raw) != len(raw):\n"
                "        raise OSError\n"
                "    sys.stdout.buffer.flush()\n"
            ),
            (
                "    sys.stdout.buffer.flush()\n"
                "    if sys.stdout.buffer.write(raw) != len(raw):\n"
                "        raise OSError\n"
            ),
        ),
    ),
)
def test_formal_worker_capability_allowlist_is_symbol_scope_and_order_exact(
    tmp_path: Path,
    case_id: str,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/formal_worker.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) == 1, case_id
    approved_root = tmp_path / "approved"
    _write_logical_module(approved_root, logical_path, source)
    assert audit_static_h2_firewall(approved_root, formal_paths=(logical_path,)).verdict == "PASS"

    mutated_root = tmp_path / "mutated"
    _write_logical_module(mutated_root, logical_path, source.replace(needle, replacement, 1))
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


def test_formal_worker_capability_allowlist_is_path_exact(tmp_path: Path) -> None:
    approved_path = "src/mdcp/temporal/formal_worker.py"
    unapproved_path = "src/mdcp/temporal/formal_worker_clone.py"
    source = (REPOSITORY_ROOT / approved_path).read_text(encoding="utf-8")
    approved_root = tmp_path / "approved"
    _write_logical_module(approved_root, approved_path, source)
    assert audit_static_h2_firewall(approved_root, formal_paths=(approved_path,)).verdict == "PASS"

    unapproved_root = tmp_path / "unapproved"
    _write_logical_module(unapproved_root, unapproved_path, source)
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(unapproved_root, formal_paths=(unapproved_path,))


@pytest.mark.parametrize(
    ("needle", "replacement"),
    (
        ("shell=False", "shell=True"),
        ("close_fds=True", "close_fds=False"),
        ("cwd=str(repository_root)", "cwd=None"),
        ("env=environment", "env={**environment, 'PATH': 'forbidden'}"),
        (
            '[str(executable), "-I", "-B", "-S", str(worker_script)]',
            "[str(executable), str(worker_script)]",
        ),
        ("process.terminate()", "process.kill()"),
        ("process.stdout.read(WORKER_STDOUT_PROBE_BYTES - len(response))", "process.stdout.read()"),
    ),
)
def test_static_firewall_rejects_fixed_supervisor_transport_tampering(
    tmp_path: Path,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) == 1
    _write_logical_module(tmp_path, logical_path, source.replace(needle, replacement, 1))

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "injected_source",
    (
        "factory([str(executable), str(worker_script)])",
        "retry_factory = factory\n        retry_factory([str(executable), str(worker_script)])",
    ),
)
def test_task_four_corrective_static_firewall_rejects_every_second_factory_launch(
    tmp_path: Path,
    injected_source: str,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    needle = "            env=environment,\n        )\n"
    assert source.count(needle) == 1
    mutated = source.replace(
        needle,
        f"{needle}        {injected_source}\n",
        1,
    )
    _write_logical_module(tmp_path, logical_path, mutated)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("needle", "replacement"),
    (
        (
            '_git_bytes(root, "show", "-s", "--format=%P", expected_head)',
            '_git_bytes(root, "show", "-s", "--format=%P", "HEAD")',
        ),
        (
            '            "-r",\n            expected_head,\n',
            '            "-r",\n            source_commit,\n            expected_head,\n',
        ),
        (
            '_git_bytes(root, "ls-tree", expected_head, "--", *SEARCH_SOURCE_PATHS)',
            '_git_bytes(root, "ls-tree", expected_head)',
        ),
        (
            "    from mdcp.temporal.formal_worker_protocol import SEARCH_SOURCE_PATHS\n",
            "    from mdcp.temporal.formal_worker_protocol import SEARCH_SOURCE_PATHS\n"
            '    _git_bytes(root, "status", "--porcelain=v1", "--untracked-files=all")\n',
        ),
    ),
)
def test_task_four_round_two_static_firewall_pins_exact_topology_git_calls(
    tmp_path: Path,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) == 1
    _write_logical_module(tmp_path, logical_path, source.replace(needle, replacement, 1))

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("needle", "replacement"),
    (
        (
            "sys.path.insert(0, str(source_root))",
            "sys.path.insert(0, str(repository_root))",
        ),
        (
            "sys.stdin.buffer.read(MAX_WORKER_MESSAGE_BYTES + 1)",
            "sys.stdin.buffer.read()",
        ),
        (
            "from mdcp.temporal.formal_worker_protocol import (",
            "from mdcp.temporal import cli\n    from mdcp.temporal.formal_worker_protocol import (",
        ),
        (
            "import stat\n",
            "import stat\nimport subprocess\n",
        ),
    ),
)
def test_static_firewall_rejects_formal_worker_bootstrap_tampering(
    tmp_path: Path,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/formal_worker.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) >= 1
    _write_logical_module(tmp_path, logical_path, source.replace(needle, replacement, 1))

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("needle", "replacement"),
    (
        (
            'source_root = _canonical_path(repository_root / "src", directory=True)',
            'source_root = _canonical_path(repository_root / "src", directory=True)\n'
            "    source_root = repository_root",
        ),
        (
            "site_packages = _canonical_path(executable.parents[1] / "
            '"Lib/site-packages", directory=True)',
            "site_packages = _canonical_path(executable.parents[1] / "
            '"Lib/site-packages", directory=True)\n'
            "    site_packages = repository_root",
        ),
        (
            "executable = _canonical_path(Path(sys.executable), directory=False)",
            "executable = _canonical_path(script, directory=False)",
        ),
        (
            'executable.parents[1] / "Lib/site-packages"',
            'executable.parents[0] / "Lib/site-packages"',
        ),
        (
            "sys.path.insert(0, str(site_packages))\n    sys.path.insert(0, str(source_root))",
            "sys.path.insert(0, str(source_root))\n    sys.path.insert(0, str(site_packages))",
        ),
        (
            "sys.path.insert(0, str(site_packages))",
            "sys.path.insert(0, str(site_packages))\n    sys.path.insert(0, str(site_packages))",
        ),
    ),
)
def test_task_four_corrective_static_firewall_pins_bootstrap_derivations(
    tmp_path: Path,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/formal_worker.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) == 1
    _write_logical_module(tmp_path, logical_path, source.replace(needle, replacement, 1))

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_allows_same_qualified_import_in_separate_scopes(
    tmp_path: Path,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (
        "from mdcp.temporal.runner import EXACT_TRIAL_IDS\n"
        "def recover():\n"
        "    from mdcp.temporal.runner import EXACT_TRIAL_IDS\n"
        "    return EXACT_TRIAL_IDS\n"
    )
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"


def test_static_firewall_rejects_conflicting_duplicate_import_binding(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (
        "from mdcp.temporal.runner import EXACT_TRIAL_IDS\n"
        "def recover():\n"
        "    from mdcp.temporal.runner import EXACT_FOLD_IDS as EXACT_TRIAL_IDS\n"
        "    return EXACT_TRIAL_IDS\n"
    )
    _write_logical_module(tmp_path, logical_path, source)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_rejects_unapproved_run_evidence_capability(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    needle = "import math\n"
    assert source.count(needle) == 1
    _write_logical_module(
        tmp_path, logical_path, source.replace(needle, "import math\nimport time\n", 1)
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_rejects_posix_native_recovery_capability(
    tmp_path: Path,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(
        tmp_path,
        logical_path,
        source + "\nctypes.CDLL(None)\n",
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_rejects_dynamic_cli_environment_access(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/cli.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    needle = 'os.getenv("MDCP_FORMAL_RUN_AUTHORIZATION")'
    assert source.count(needle) == 1
    _write_logical_module(
        tmp_path,
        logical_path,
        source.replace(needle, "os.getenv(parsed.authorization_env)", 1),
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_static_firewall_rejects_unapproved_windows_native_symbol(
    tmp_path: Path,
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    needle = "windll.ntdll.NtCreateFile"
    assert source.count(needle) == 1
    _write_logical_module(
        tmp_path,
        logical_path,
        source.replace(needle, "windll.ntdll.NtOpenFile", 1),
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    "recovery",
    (
        "ctypes.memmove(0, 0, 0)",
        "os.path.abspath('private-evidence')",
    ),
)
def test_static_firewall_rejects_removed_directory_publisher_capabilities(
    tmp_path: Path, recovery: str
) -> None:
    logical_path = "src/mdcp/temporal/run_evidence.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, f"{source}\n{recovery}")

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


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

    assert result.verdict == "PASS"
    assert result.checked_paths == FORMAL_V2_FIXED_PATHS + tuple(
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in sorted(
            (REPOSITORY_ROOT / FORMAL_TEMPORAL_PACKAGE_ROOT).glob("*.py"),
            key=lambda path: path.as_posix(),
        )
    )
    assert len(result.implementation_sha256) == 64


def test_static_firewall_allows_only_committed_one_shot_runner(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/runner.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"
    assert result.checked_paths == (logical_path,)


def test_runtime_guard_and_command_surfaces_are_discovered() -> None:
    result = audit_static_h2_firewall(REPOSITORY_ROOT)

    assert {
        "src/mdcp/temporal/runtime_guards.py",
        "src/mdcp/temporal/runner.py",
        "src/mdcp/temporal/cli.py",
        "src/mdcp/temporal/run_evidence.py",
        "src/mdcp/temporal/search_identity.py",
        "src/mdcp/temporal/formal_worker_protocol.py",
    }.issubset(result.checked_paths)


def test_dedicated_worker_source_tuple_has_one_protocol_owner() -> None:
    from mdcp.temporal import formal_worker_protocol, search_identity

    assert search_identity.SEARCH_SOURCE_PATHS is formal_worker_protocol.SEARCH_SOURCE_PATHS
    assert len(formal_worker_protocol.SEARCH_SOURCE_PATHS) == 47
    assert set(formal_worker_protocol.FORMAL_WORKER_SOURCE_PATHS).issubset(
        formal_worker_protocol.SEARCH_SOURCE_PATHS
    )


def test_static_firewall_allows_exact_search_identity_git_calls(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/search_identity.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    _write_logical_module(tmp_path, logical_path, source)

    result = audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))

    assert result.verdict == "PASS"


def test_static_firewall_rejects_unapproved_search_identity_git_call(tmp_path: Path) -> None:
    logical_path = "src/mdcp/temporal/search_identity.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    needle = '    head = _git(root, "rev-parse", "HEAD")\n'
    assert source.count(needle) == 1
    _write_logical_module(
        tmp_path,
        logical_path,
        source.replace(needle, '    head = _git(root, "status", "--short")\n', 1),
    )

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("mutation", "needle", "replacement"),
    (
        ("unlisted-import", "import stat\n", "import inspect\nimport stat\n"),
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


@pytest.mark.parametrize(
    ("case_id", "replacement"),
    (
        ("slice", "        for logical_path in SEARCH_SOURCE_PATHS[:1]:\n"),
        ("filter", "        for logical_path in filter(None, SEARCH_SOURCE_PATHS):\n"),
        ("reorder", "        for logical_path in reversed(SEARCH_SOURCE_PATHS):\n"),
        ("alias", "        for logical_path in source_paths:\n"),
        ("deduplicate", "        for logical_path in dict.fromkeys(SEARCH_SOURCE_PATHS):\n"),
        ("partial", "        for logical_path in SEARCH_SOURCE_PATHS[:-1]:\n"),
    ),
)
def test_fix_round_one_i2_firewall_pins_complete_ordered_inventory_loops(
    tmp_path: Path,
    case_id: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    needle = "        for logical_path in SEARCH_SOURCE_PATHS:\n"
    assert source.count(needle) == 1, case_id
    approved_root = tmp_path / "approved"
    _write_logical_module(approved_root, logical_path, source)
    assert audit_static_h2_firewall(approved_root, formal_paths=(logical_path,)).verdict == "PASS"

    mutated = source.replace(needle, replacement, 1)
    if case_id == "alias":
        import_needle = "    entries = []\n"
        assert mutated.count(import_needle) == 2
        mutated = mutated.replace(
            import_needle,
            "    source_paths = SEARCH_SOURCE_PATHS\n    entries = []\n",
            1,
        )
    mutated_root = tmp_path / "mutated"
    _write_logical_module(mutated_root, logical_path, mutated)
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("path_name", "digest_name"),
    (
        ("SEARCH_SOURCE_PATHS", "search_source_inventory_sha256"),
        ("FORMAL_WORKER_SOURCE_PATHS", "formal_worker_inventory_sha256"),
    ),
)
@pytest.mark.parametrize(
    "case_id",
    (
        "break-before-body",
        "continue-one-path",
        "return-from-loop",
        "partial-digest",
        "aliased-partial-digest",
    ),
)
def test_fix_round_two_i1_firewall_rejects_partial_inventory_loops_and_digests(
    tmp_path: Path,
    path_name: str,
    digest_name: str,
    case_id: str,
) -> None:
    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    loop_needle = f"        for logical_path in {path_name}:\n"
    return_needle = f"    return {digest_name}(tuple(entries))\n"
    assert source.count(loop_needle) == 1, (path_name, case_id)
    assert source.count(return_needle) == 1, (path_name, case_id)

    if case_id == "break-before-body":
        mutated = source.replace(loop_needle, f"{loop_needle}            break\n", 1)
    elif case_id == "continue-one-path":
        mutated = source.replace(
            loop_needle,
            f'{loop_needle}            if logical_path == "src/mdcp/temporal/firewall.py":\n'
            "                continue\n",
            1,
        )
    elif case_id == "return-from-loop":
        mutated = source.replace(loop_needle, f"{loop_needle}            return None\n", 1)
    elif case_id == "partial-digest":
        mutated = source.replace(
            return_needle,
            f"    return {digest_name}(tuple(entries[:1]))\n",
            1,
        )
    else:
        mutated = source.replace(
            return_needle,
            "    selected_entries = entries[:1]\n"
            f"    return {digest_name}(tuple(selected_entries))\n",
            1,
        )

    mutated_root = tmp_path / f"{path_name}-{case_id}"
    _write_logical_module(mutated_root, logical_path, mutated)
    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("protected_name", "other_name"),
    (
        ("_worker_source_inventory", "_formal_worker_source_inventory"),
        ("_formal_worker_source_inventory", "_worker_source_inventory"),
        ("_WorkerRuntimeGuard", "build_worker_runtime_guard"),
        ("build_worker_runtime_guard", "_WorkerRuntimeGuard"),
    ),
)
@pytest.mark.parametrize(
    ("case_id", "binding_template"),
    (
        (
            "conditional-definition",
            "if True:\n    def {name}(repository_root):\n        return None\n",
        ),
        (
            "cached-wrapper",
            "_round3_original = {name}\n"
            "_round3_cached = None\n"
            "if True:\n"
            "    def {name}(repository_root):\n"
            "        global _round3_cached\n"
            "        if _round3_cached is None:\n"
            "            _round3_cached = _round3_original(repository_root)\n"
            "        return _round3_cached\n",
        ),
        ("direct-assignment", "{name} = None\n"),
        ("alias-assignment", "{name} = {other}\n"),
        ("tuple-unpack", "({name}, _round3_other) = (None, None)\n"),
        ("annotated-assignment", "{name}: object = None\n"),
        ("conditional-assignment", "if True:\n    {name} = None\n"),
        ("for-target", "for {name} in ():\n    pass\n"),
        ("named-expression", "_round3_value = ({name} := None)\n"),
        (
            "default-expression-binding",
            "def _round3_default(value=({name} := None)):\n    return value\n",
        ),
        (
            "decorator-expression-binding",
            "def _round3_decorator(function):\n"
            "    return function\n"
            "@({name} := _round3_decorator)\n"
            "def _round3_decorated():\n"
            "    return None\n",
        ),
        ("delete", "del {name}\n"),
        (
            "exception-target",
            "try:\n    pass\nexcept Exception as {name}:\n    pass\n",
        ),
        ("match-capture", "match None:\n    case {name}:\n        pass\n"),
    ),
)
def test_fix_round_three_i1_protected_runtime_inventory_names_have_one_live_binding(
    tmp_path: Path,
    protected_name: str,
    other_name: str,
    case_id: str,
    binding_template: str,
) -> None:
    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    mutation = binding_template.format(name=protected_name, other=other_name)
    mutated_root = tmp_path / f"{protected_name}-{case_id}"
    _write_logical_module(mutated_root, logical_path, f"{source.rstrip()}\n\n{mutation}")

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("case_id", "needle", "replacement"),
    (
        (
            "checkpoint-search-stored-expected",
            "        current_source = _worker_source_inventory(self.repository_root)\n",
            "        current_source = self.source_inventory_sha256\n",
        ),
        (
            "checkpoint-search-alternate-helper",
            "        current_source = _worker_source_inventory(self.repository_root)\n",
            "        current_source = _round3_search_wrapper(self.repository_root)\n",
        ),
        (
            "checkpoint-search-omit-call",
            "        current_source = _worker_source_inventory(self.repository_root)\n",
            "        current_source = None\n",
        ),
        (
            "checkpoint-search-swap-helper",
            "        current_source = _worker_source_inventory(self.repository_root)\n",
            "        current_source = _formal_worker_source_inventory(self.repository_root)\n",
        ),
        (
            "checkpoint-search-wrong-root",
            "        current_source = _worker_source_inventory(self.repository_root)\n",
            "        current_source = _worker_source_inventory(None)\n",
        ),
        (
            "checkpoint-search-wrong-result-target",
            "        current_source = _worker_source_inventory(self.repository_root)\n",
            "        ignored_source = _worker_source_inventory(self.repository_root)\n",
        ),
        (
            "checkpoint-search-wrong-comparison-target",
            "        if current_source != self.source_inventory_sha256:\n",
            "        if current_source != self.expected_formal_worker_inventory_sha256:\n",
        ),
        (
            "checkpoint-search-comparison-order",
            "        if current_source != self.source_inventory_sha256:\n",
            "        if self.source_inventory_sha256 != current_source:\n",
        ),
        (
            "checkpoint-search-wrong-reason",
            "            return self._unknown("
            '"SOURCE_INVENTORY_CHANGED", elapsed_ns, peak_process_bytes)\n',
            "            return self._unknown("
            '"FORMAL_WORKER_INVENTORY_CHANGED", elapsed_ns, peak_process_bytes)\n',
        ),
        (
            "checkpoint-worker-stored-expected",
            "        current_worker = _formal_worker_source_inventory(self.repository_root)\n",
            "        current_worker = self.expected_formal_worker_inventory_sha256\n",
        ),
        (
            "checkpoint-worker-alternate-helper",
            "        current_worker = _formal_worker_source_inventory(self.repository_root)\n",
            "        current_worker = _round3_worker_wrapper(self.repository_root)\n",
        ),
        (
            "checkpoint-worker-omit-call",
            "        current_worker = _formal_worker_source_inventory(self.repository_root)\n",
            "        current_worker = None\n",
        ),
        (
            "checkpoint-worker-swap-helper",
            "        current_worker = _formal_worker_source_inventory(self.repository_root)\n",
            "        current_worker = _worker_source_inventory(self.repository_root)\n",
        ),
        (
            "checkpoint-worker-wrong-root",
            "        current_worker = _formal_worker_source_inventory(self.repository_root)\n",
            "        current_worker = _formal_worker_source_inventory(None)\n",
        ),
        (
            "checkpoint-worker-wrong-result-target",
            "        current_worker = _formal_worker_source_inventory(self.repository_root)\n",
            "        ignored_worker = _formal_worker_source_inventory(self.repository_root)\n",
        ),
        (
            "checkpoint-worker-wrong-comparison-target",
            "        if current_worker != self.expected_formal_worker_inventory_sha256:\n",
            "        if current_worker != self.source_inventory_sha256:\n",
        ),
        (
            "checkpoint-worker-comparison-order",
            "        if current_worker != self.expected_formal_worker_inventory_sha256:\n",
            "        if self.expected_formal_worker_inventory_sha256 != current_worker:\n",
        ),
        (
            "checkpoint-worker-wrong-reason",
            "            return self._unknown("
            '"FORMAL_WORKER_INVENTORY_CHANGED", elapsed_ns, peak_process_bytes)\n',
            "            return self._unknown("
            '"SOURCE_INVENTORY_CHANGED", elapsed_ns, peak_process_bytes)\n',
        ),
        (
            "builder-search-stored-expected",
            "    current_source = _worker_source_inventory(repository_root)\n",
            "    current_source = source_inventory_sha256\n",
        ),
        (
            "builder-search-alternate-helper",
            "    current_source = _worker_source_inventory(repository_root)\n",
            "    current_source = _round3_search_wrapper(repository_root)\n",
        ),
        (
            "builder-search-omit-call",
            "    current_source = _worker_source_inventory(repository_root)\n",
            "    current_source = None\n",
        ),
        (
            "builder-search-swap-helper",
            "    current_source = _worker_source_inventory(repository_root)\n",
            "    current_source = _formal_worker_source_inventory(repository_root)\n",
        ),
        (
            "builder-search-wrong-root",
            "    current_source = _worker_source_inventory(repository_root)\n",
            "    current_source = _worker_source_inventory(None)\n",
        ),
        (
            "builder-search-wrong-result-target",
            "    current_source = _worker_source_inventory(repository_root)\n",
            "    ignored_source = _worker_source_inventory(repository_root)\n",
        ),
        (
            "builder-search-wrong-comparison-target",
            "        current_source != source_inventory_sha256\n",
            "        current_source != expected_formal_worker_inventory_sha256\n",
        ),
        (
            "builder-search-comparison-order",
            "        current_source != source_inventory_sha256\n",
            "        source_inventory_sha256 != current_source\n",
        ),
        (
            "builder-worker-stored-expected",
            "    current_worker = _formal_worker_source_inventory(repository_root)\n",
            "    current_worker = expected_formal_worker_inventory_sha256\n",
        ),
        (
            "builder-worker-alternate-helper",
            "    current_worker = _formal_worker_source_inventory(repository_root)\n",
            "    current_worker = _round3_worker_wrapper(repository_root)\n",
        ),
        (
            "builder-worker-omit-call",
            "    current_worker = _formal_worker_source_inventory(repository_root)\n",
            "    current_worker = None\n",
        ),
        (
            "builder-worker-swap-helper",
            "    current_worker = _formal_worker_source_inventory(repository_root)\n",
            "    current_worker = _worker_source_inventory(repository_root)\n",
        ),
        (
            "builder-worker-wrong-root",
            "    current_worker = _formal_worker_source_inventory(repository_root)\n",
            "    current_worker = _formal_worker_source_inventory(None)\n",
        ),
        (
            "builder-worker-wrong-result-target",
            "    current_worker = _formal_worker_source_inventory(repository_root)\n",
            "    ignored_worker = _formal_worker_source_inventory(repository_root)\n",
        ),
        (
            "builder-worker-wrong-comparison-target",
            "        or current_worker != expected_formal_worker_inventory_sha256\n",
            "        or current_worker != source_inventory_sha256\n",
        ),
        (
            "builder-worker-comparison-order",
            "        or current_worker != expected_formal_worker_inventory_sha256\n",
            "        or expected_formal_worker_inventory_sha256 != current_worker\n",
        ),
    ),
)
def test_fix_round_three_i2_runtime_inventory_consumers_are_exact(
    tmp_path: Path,
    case_id: str,
    needle: str,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    assert source.count(needle) == 1, case_id
    mutated = source.replace(needle, replacement, 1)
    if "alternate-helper" in case_id:
        meaning = "search" if "search" in case_id else "worker"
        helper = (
            "_worker_source_inventory" if meaning == "search" else "_formal_worker_source_inventory"
        )
        mutated = (
            f"{mutated.rstrip()}\n\n"
            f"def _round3_{meaning}_wrapper(repository_root):\n"
            f"    return {helper}(repository_root)\n"
        )
    mutated_root = tmp_path / case_id
    _write_logical_module(mutated_root, logical_path, mutated)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


@pytest.mark.parametrize("meaning", ("search", "worker"))
def test_fix_round_three_i2_construction_cache_cannot_replace_checkpoint_reread(
    tmp_path: Path,
    meaning: str,
) -> None:
    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    if meaning == "search":
        field_needle = "    source_inventory_sha256: str\n"
        field_replacement = (
            "    source_inventory_sha256: str\n    cached_source_inventory_sha256: str\n"
        )
        checkpoint_needle = (
            "        current_source = _worker_source_inventory(self.repository_root)\n"
        )
        checkpoint_replacement = "        current_source = self.cached_source_inventory_sha256\n"
        build_needle = "        source_inventory_sha256=source_inventory_sha256,\n"
        build_replacement = (
            "        source_inventory_sha256=source_inventory_sha256,\n"
            "        cached_source_inventory_sha256=current_source,\n"
        )
    else:
        field_needle = "    expected_formal_worker_inventory_sha256: str\n"
        field_replacement = (
            "    expected_formal_worker_inventory_sha256: str\n"
            "    cached_formal_worker_inventory_sha256: str\n"
        )
        checkpoint_needle = (
            "        current_worker = _formal_worker_source_inventory(self.repository_root)\n"
        )
        checkpoint_replacement = (
            "        current_worker = self.cached_formal_worker_inventory_sha256\n"
        )
        build_needle = (
            "        expected_formal_worker_inventory_sha256="
            "expected_formal_worker_inventory_sha256,\n"
        )
        build_replacement = (
            f"{build_needle}        cached_formal_worker_inventory_sha256=current_worker,\n"
        )
    for needle in (field_needle, checkpoint_needle, build_needle):
        assert source.count(needle) == 1, (meaning, needle)
    mutated = source.replace(field_needle, field_replacement, 1)
    mutated = mutated.replace(checkpoint_needle, checkpoint_replacement, 1)
    mutated = mutated.replace(build_needle, build_replacement, 1)
    mutated_root = tmp_path / f"cached-{meaning}"
    _write_logical_module(mutated_root, logical_path, mutated)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


def test_fix_round_four_runtime_guard_normalized_module_ast_hash_is_exact() -> None:
    import ast
    import hashlib

    logical_path = "src/mdcp/temporal/runtime_guards.py"
    tree = ast.parse((REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8"))
    normalized = ast.dump(tree, include_attributes=False).encode("utf-8")

    assert hashlib.sha256(normalized).hexdigest() == (
        "b27864394e5d3fa2a1e80bc21c79ab7977dfa264fd2d86bbcdab29bf7c9a5f64"
    )


def test_runtime_guard_subprocess_imports_are_scoped_to_supervisor_git_helpers(
    tmp_path: Path,
) -> None:
    import ast

    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    import_scopes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import) or not any(
            alias.name == "subprocess" for alias in node.names
        ):
            continue
        current: ast.AST | None = node
        while current is not None and not isinstance(current, ast.FunctionDef):
            current = parents.get(current)
        import_scopes.append(current.name if isinstance(current, ast.FunctionDef) else None)

    expected_scopes = {"_repository_head", "_repository_is_dirty", "_tracked_paths"}
    assert set(import_scopes) == expected_scopes
    assert len(import_scopes) == len(expected_scopes)

    local_import = "    import subprocess\n"
    assert source.count(local_import) == len(expected_scopes)
    module_scope_mutation = source.replace(local_import, "").replace(
        "import stat\n", "import stat\nimport subprocess\n", 1
    )
    extra_scope_needle = "def _authoritative_peak_process_bytes() -> int | None:\n"
    assert source.count(extra_scope_needle) == 1
    extra_scope_mutation = source.replace(
        extra_scope_needle,
        f"{extra_scope_needle}{local_import}",
        1,
    )

    for case_id, mutated in (
        ("module-scope", module_scope_mutation),
        ("extra-function-scope", extra_scope_mutation),
    ):
        mutated_root = tmp_path / case_id
        _write_logical_module(mutated_root, logical_path, mutated)
        with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
            audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


@pytest.mark.parametrize(
    ("case_id", "needle", "replacement"),
    (
        (
            "checkpoint-wrapper",
            None,
            "def _round4_checkpoint(self, stage):\n"
            "    return RuntimeObservation(\n"
            '        verdict="PASS", reason_codes=(), elapsed_ns=0, peak_process_bytes=0,\n'
            "        repository_inventory_sha256=self.source_inventory_sha256,\n"
            "    )\n"
            "_WorkerRuntimeGuard.checkpoint = _round4_checkpoint\n",
        ),
        (
            "unknown-wrapper",
            None,
            "def _round4_unknown(self, reason_code, elapsed_ns, peak_process_bytes):\n"
            "    return RuntimeObservation(\n"
            '        verdict="PASS", reason_codes=(), elapsed_ns=elapsed_ns,\n'
            "        peak_process_bytes=peak_process_bytes,\n"
            "        repository_inventory_sha256=self.source_inventory_sha256,\n"
            "    )\n"
            "_WorkerRuntimeGuard._unknown = _round4_unknown\n",
        ),
        (
            "checkpoint-alias",
            None,
            "_WorkerRuntimeGuard.checkpoint = _CheckpointGuard.checkpoint\n",
        ),
        (
            "checkpoint-lambda",
            None,
            "_WorkerRuntimeGuard.checkpoint = lambda self, stage: None\n",
        ),
        ("checkpoint-delete", None, "del _WorkerRuntimeGuard.checkpoint\n"),
        ("unknown-delete", None, "del _WorkerRuntimeGuard._unknown\n"),
        (
            "observation-conditional-definition",
            None,
            "if True:\n"
            "    def RuntimeObservation(**values):\n"
            "        values['verdict'] = 'PASS'\n"
            "        values['reason_codes'] = ()\n"
            "        return values\n",
        ),
        ("observation-rebind", None, "RuntimeObservation = _WorkerRuntimeGuard\n"),
        (
            "observation-wrapper",
            None,
            "_round4_observation = RuntimeObservation\n"
            "def RuntimeObservation(**values):\n"
            "    values['verdict'] = 'PASS'\n"
            "    values['reason_codes'] = ()\n"
            "    return _round4_observation(**values)\n",
        ),
        ("elapsed-limit", None, "_MAX_ELAPSED_NS = 10**100\n"),
        ("memory-limit", None, "_MAX_PEAK_PROCESS_BYTES = 10**100\n"),
        (
            "memory-probe",
            None,
            "_authoritative_peak_process_bytes = lambda: 5 * 1024**3\n",
        ),
        ("time-attribute", None, "time.monotonic_ns = lambda: 0\n"),
        ("hashlib-attribute", None, "hashlib.sha256 = lambda value=b'': None\n"),
        ("stat-attribute", None, "stat.S_ISREG = lambda mode: True\n"),
        ("dependency-direct-assignment", None, "time = None\n"),
        (
            "dependency-conditional-assignment",
            None,
            "if True:\n    _authoritative_peak_process_bytes = lambda: 0\n",
        ),
        ("dependency-delete", None, "del time\n"),
        (
            "unprotected-class-base",
            "class _CheckpointGuard:\n",
            "class _CheckpointGuard(object):\n",
        ),
        ("module-lambda", None, "_round4_module_lambda = lambda: None\n"),
        ("harmless-semantic-node", None, "_ROUND4_HARMLESS = 1\n"),
    ),
)
def test_fix_round_four_exact_runtime_guard_module_ast_pin_rejects_live_mutations(
    tmp_path: Path,
    case_id: str,
    needle: str | None,
    replacement: str,
) -> None:
    logical_path = "src/mdcp/temporal/runtime_guards.py"
    source = (REPOSITORY_ROOT / logical_path).read_text(encoding="utf-8")
    if needle is None:
        mutated = f"{source.rstrip()}\n\n{replacement}"
    else:
        assert source.count(needle) == 1, case_id
        mutated = source.replace(needle, replacement, 1)
    mutated_root = tmp_path / case_id
    _write_logical_module(mutated_root, logical_path, mutated)

    with pytest.raises(StaticFirewallError, match=f"^{FIXED_REASON_CODE}$"):
        audit_static_h2_firewall(mutated_root, formal_paths=(logical_path,))


def test_development_partition_type_has_no_h2_capability() -> None:
    assert tuple(DevelopmentPartitions.__dataclass_fields__) == ("train", "h1")
    assert "h2" not in vars(DevelopmentPartitions)
    assert "open_h2" not in vars(DevelopmentPartitions)


def test_dedicated_worker_finite_boundary_keeps_dangerous_modules_out() -> None:
    import ast

    tree = ast.parse(
        (REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker.py").read_text(encoding="utf-8")
    )
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported.isdisjoint(
        {"asyncio", "concurrent", "importlib", "multiprocessing", "socket", "subprocess"}
    )


def test_marker_before_access_keeps_loader_and_model_imports_post_marker() -> None:
    import ast

    tree = ast.parse(
        (REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker.py").read_text(encoding="utf-8")
    )
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    execute = functions["_execute_worker_request"]
    calls = [
        node.func.id
        for node in ast.walk(execute)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert calls.index("_create_durable_marker") < calls.index("_hash_archive")
    assert calls.index("_hash_archive") < calls.index("_execute_natural_run")

    natural = functions["_execute_natural_run"]
    imported_modules = {
        node.module
        for node in ast.walk(natural)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert {
        "mdcp.temporal.folds",
        "mdcp.temporal.runner",
        "mdcp.temporal.trials",
        "mdcp.workload.dataset",
        "mdcp.workload.splits",
    }.issubset(imported_modules)
