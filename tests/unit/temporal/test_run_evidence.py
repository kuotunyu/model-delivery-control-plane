from __future__ import annotations

import ast
import base64
import copy
import ctypes
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import mdcp.temporal.formal_worker_protocol as worker_protocol
import mdcp.temporal.run_evidence as run_evidence
from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.evidence import public_evidence_violations
from mdcp.temporal.run_evidence import (
    PrivateBundleIdentity,
    PrivateFoldEvidence,
    PrivateRunBundle,
    PublicDevelopmentResult,
    canonical_public_result_bytes,
    verify_development_result,
    write_synthetic_bundle_no_clobber,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def valid_public_result() -> dict[str, object]:
    folds = [
        {
            "fold_id": fold_id,
            "status": "PASS",
            "metrics": {
                "row_count": 20.0,
                "stable_mae": 1.0,
                "candidate_mae": 0.9,
                "point_ratio": 0.9,
                "ucb95": 0.95,
            },
            "reason_codes": [],
        }
        for fold_id in ("F1", "F2", "F3", "F4")
    ]
    return {
        "schema_version": "mdcp.development-result-index.v1",
        "canonicalization_version": "RFC8785",
        "evidence_class": "synthetic_test",
        "status": "PASS",
        "h1_role": "OBSERVED_DEVELOPMENT_ONLY",
        "h2_state": "SEALED_NOT_LOADED",
        "h2_loaded_rows": 0,
        "selection_fit_count": 80,
        "result_sha256": "a" * 64,
        "trials": [
            {
                "trial_id": f"TRIAL-{number:02d}",
                "selection_fit_count": 4,
                "folds": folds,
            }
            for number in range(1, 21)
        ],
    }


def mutate(document: dict[str, object], mutation: str) -> dict[str, object]:
    result = json.loads(json.dumps(document))
    targets = {
        "extra_key": lambda: result.__setitem__("unexpected", True),
        "unknown_metric": lambda: result["trials"][0]["folds"][0]["metrics"].__setitem__(
            "unknown", 1.0
        ),
        "nan": lambda: result["trials"][0]["folds"][0]["metrics"].__setitem__(
            "ucb95", float("nan")
        ),
        "uppercase_digest": lambda: result.__setitem__("result_sha256", "A" * 64),
        "short_digest": lambda: result.__setitem__("result_sha256", "a" * 63),
        "private_path": lambda: result.__setitem__("private_path", "C:/private/model.bin"),
        "raw_timestamp": lambda: result.__setitem__("created_at_utc", "2026-08-25T12:00:00Z"),
        "traceback": lambda: result.__setitem__("traceback", "Traceback (most recent call last):"),
        "credential": lambda: result.__setitem__("credential", "Bearer " + "a" * 32),
        "raw_prediction": lambda: result.__setitem__("raw_prediction", [0.1]),
    }
    targets[mutation]()
    return result


def synthetic_private_bundle() -> PrivateRunBundle:
    return PrivateRunBundle(
        evidence_class="synthetic_test",
        files=(
            PrivateFoldEvidence(
                logical_path="private/folds/F1.json",
                canonical_bytes=canonicalize_json({"fold_id": "F1", "rows": [1, 2]}),
            ),
            PrivateFoldEvidence(
                logical_path="private/folds/F2.json",
                canonical_bytes=canonicalize_json({"fold_id": "F2", "rows": [3, 4]}),
            ),
        ),
    )


def private_container_bytes() -> tuple[bytes, PrivateBundleIdentity]:
    bundle = synthetic_private_bundle()
    entries = [
        {
            "logical_path": item.logical_path,
            "byte_size": len(item.canonical_bytes),
            "sha256": sha256_hex(item.canonical_bytes),
            "payload_base64": base64.b64encode(item.canonical_bytes).decode("ascii"),
        }
        for item in bundle.files
    ]
    inventory = [
        {key: entry[key] for key in ("logical_path", "byte_size", "sha256")} for entry in entries
    ]
    inventory_sha256 = sha256_hex(canonicalize_json(inventory))
    manifest = {
        "schema_version": "mdcp.private-evidence-container.v1",
        "canonicalization_version": "RFC8785",
        "evidence_class": "synthetic_test",
        "file_count": 2,
        "total_bytes": sum(entry["byte_size"] for entry in entries),
        "inventory_sha256": inventory_sha256,
    }
    manifest_sha256 = sha256_hex(canonicalize_json(manifest))
    identity = PrivateBundleIdentity(
        file_count=2,
        total_bytes=manifest["total_bytes"],
        inventory_sha256=inventory_sha256,
        manifest_sha256=manifest_sha256,
    )
    return canonicalize_json(
        {**manifest, "entries": entries, "manifest_sha256": manifest_sha256}
    ), identity


def coordinate_payload_and_all_internal_digests(document: dict[str, object]) -> None:
    payload = canonicalize_json({"fold_id": "F1", "rows": [99]})
    entry = document["entries"][0]
    entry["payload_base64"] = base64.b64encode(payload).decode("ascii")
    entry["byte_size"] = len(payload)
    entry["sha256"] = sha256_hex(payload)
    document["total_bytes"] = sum(item["byte_size"] for item in document["entries"])
    inventory = [
        {key: item[key] for key in ("logical_path", "byte_size", "sha256")}
        for item in document["entries"]
    ]
    document["inventory_sha256"] = sha256_hex(canonicalize_json(inventory))
    manifest = {
        key: document[key]
        for key in (
            "schema_version",
            "canonicalization_version",
            "evidence_class",
            "file_count",
            "total_bytes",
            "inventory_sha256",
        )
    }
    document["manifest_sha256"] = sha256_hex(canonicalize_json(manifest))


def write_untrusted_container(tmp_path: Path, raw: bytes) -> Path:
    path = tmp_path / "untrusted.container.json"
    path.write_bytes(raw)
    return path


def _isolated_mutation_factory_adapter(
    fake_ctypes: object,
    *,
    retained_error: str | None = None,
    binding_overrides: dict[str, object] | None = None,
    function_overrides: dict[str, str] | None = None,
    exports: tuple[str, ...] = (),
) -> dict[str, object]:
    """Extract the deleted factory and append an in-memory-only test adapter."""

    source_path = Path(run_evidence.__file__)
    tree = ast.parse(source_path.read_bytes(), filename=str(source_path))
    factories = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_make_evidence_mutation_surface"
    ]
    assert len(factories) == 1
    binding_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "_MUTATION_BINDINGS"
    ]
    assert len(binding_assignments) == 1
    factory = copy.deepcopy(factories[0])
    if retained_error is not None:
        retained = [
            node
            for node in ast.walk(factory)
            if isinstance(node, ast.FunctionDef) and node.name == "_retained_destination"
        ]
        assert len(retained) == 1
        retained[0].body = [
            ast.Raise(
                exc=ast.Call(
                    func=ast.Name("_PublicationError", ast.Load()),
                    args=[ast.Constant(retained_error)],
                    keywords=[],
                )
            )
        ]
    for function_name, body_source in (function_overrides or {}).items():
        matches = [
            node
            for node in ast.walk(factory)
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        ]
        assert len(matches) == 1
        matches[0].body = ast.parse(body_source).body
    returns = [
        node
        for node in ast.walk(factory)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Tuple)
        and [item.id for item in node.value.elts if isinstance(item, ast.Name)]
        == ["write_synthetic", "execute"]
    ]
    assert len(returns) == 1
    returns[0].value.elts.append(
        ast.Dict(
            keys=[
                ast.Constant("nt_relative_file"),
                ast.Constant("classify_marker_observation"),
                ast.Constant("consume_marker"),
                ast.Constant("attempt_states"),
                *(ast.Constant(name) for name in exports),
            ],
            values=[
                ast.Name("_windows_nt_relative_file", ast.Load()),
                ast.Name("_classify_marker_observation", ast.Load()),
                ast.Name("consume_marker", ast.Load()),
                ast.Name("attempt_states", ast.Load()),
                *(ast.Name(name, ast.Load()) for name in exports),
            ],
        )
    )
    isolated_module = ast.fix_missing_locations(
        ast.Module(body=[copy.deepcopy(binding_assignments[0]), factory], type_ignores=[])
    )
    module_name = f"_mdcp_isolated_run_evidence_{id(fake_ctypes)}"
    isolated = ModuleType(module_name)
    namespace = isolated.__dict__
    namespace.update(vars(run_evidence))
    namespace.update(
        {
            "__name__": module_name,
            "ctypes": fake_ctypes,
        }
    )
    namespace.update(binding_overrides or {})
    sys.modules[module_name] = isolated
    try:
        exec(compile(isolated_module, str(source_path), "exec"), namespace)
        result = namespace["_make_evidence_mutation_surface"]()
    finally:
        sys.modules.pop(module_name, None)
    assert len(result) == 3
    return result[2]


class _FakeNtCreateFile:
    def __init__(
        self,
        *,
        ntstatus: int,
        iosb_status: int,
        information: int,
        handle: int | None,
    ) -> None:
        self.ntstatus = ntstatus
        self.iosb_status = iosb_status
        self.information = information
        self.handle = handle
        self.calls = 0
        self.argtypes: object = None
        self.restype: object = None

    def __call__(self, output: object, *_arguments: object) -> int:
        self.calls += 1
        io_status = _arguments[2]
        if self.handle is not None:
            output._obj.value = self.handle
        io_status._obj.StatusOrPointer.Status = self.iosb_status
        io_status._obj.Information = self.information
        return self.ntstatus


class _CtypesProxy:
    def __init__(self, nt_create_file: object) -> None:
        self.windll = SimpleNamespace(
            kernel32=SimpleNamespace(),
            ntdll=SimpleNamespace(NtCreateFile=nt_create_file),
        )

    def __getattr__(self, name: str) -> object:
        return getattr(ctypes, name)


@pytest.mark.parametrize(
    ("ntstatus", "iosb_status", "information", "handle"),
    (
        (0, 0, 2, 101),
        (-1073741771, 0, 0, None),
        (-1073741771, 0, 0, 202),
        (0, 0, 2, None),
        (0, 0, 1, 303),
        (0, -1, 2, 404),
        (259, 0, 2, 505),
    ),
)
def test_isolated_factory_preserves_exact_nt_create_observation(
    ntstatus: int,
    iosb_status: int,
    information: int,
    handle: int | None,
) -> None:
    fake = _FakeNtCreateFile(
        ntstatus=ntstatus,
        iosb_status=iosb_status,
        information=information,
        handle=handle,
    )
    adapter = _isolated_mutation_factory_adapter(_CtypesProxy(fake))

    observed = adapter["nt_relative_file"](1, "marker", False, 2, 0, 2, 0x62)

    assert observed == (True, ntstatus, iosb_status, information, handle)
    assert fake.calls == 1


def test_isolated_factory_records_pre_call_resolution_failure_without_a_create() -> None:
    class MissingNtDll:
        @property
        def NtCreateFile(self) -> object:
            raise OSError("unavailable")

    proxy = _CtypesProxy(None)
    proxy.windll.ntdll = MissingNtDll()
    adapter = _isolated_mutation_factory_adapter(proxy)

    observed = adapter["nt_relative_file"](1, "marker", False, 2, 0, 2, 0x62)

    assert observed == (False, None, None, None, None)


def test_nt_wrapper_closes_preparation_exception() -> None:
    class PreparationFailureProxy(_CtypesProxy):
        def create_unicode_buffer(self, *_arguments: object) -> object:
            raise OSError("synthetic preparation failure")

    adapter = _isolated_mutation_factory_adapter(PreparationFailureProxy(None))

    observed = adapter["nt_relative_file"](1, "marker", False, 2, 0, 2, 0x62)

    assert observed == (False, None, None, None, None)


def test_nt_wrapper_closes_post_call_iosb_observation_exception() -> None:
    class ExplodingIoStatus:
        Information = 2

        @property
        def StatusOrPointer(self) -> object:
            raise OSError("synthetic IOSB observation failure")

    class SuccessfulNtCreate:
        argtypes: object = None
        restype: object = None

        def __call__(self, output: object, *_arguments: object) -> int:
            output._obj.value = 606
            return 0

    class ByrefProxy(_CtypesProxy):
        @staticmethod
        def POINTER(_value: object) -> object:
            return object

        @staticmethod
        def byref(value: object) -> object:
            return SimpleNamespace(_obj=value)

    adapter = _isolated_mutation_factory_adapter(
        ByrefProxy(SuccessfulNtCreate()),
        binding_overrides={"_WindowsIoStatusBlock": ExplodingIoStatus},
    )

    observed = adapter["nt_relative_file"](1, "marker", False, 2, 0, 2, 0x62)

    assert observed == (True, 0, None, None, 606)


@pytest.mark.parametrize(
    ("entered", "status", "iosb", "information", "owned", "leaf", "expected"),
    (
        (False, None, None, None, None, "ABSENT", "PRECALL_FAILED"),
        (False, None, None, None, None, "PRESENT", "COLLISION"),
        (False, None, None, None, None, "INDETERMINATE", "INDETERMINATE"),
        (True, -1073741771, 0, 0, None, "ABSENT", "COLLISION"),
        (True, -1073741771, 0, 0, 202, "PRESENT", "INDETERMINATE"),
        (True, 0, 0, 2, 101, "INDETERMINATE", "CREATED"),
        (True, 0, 0, 2, None, "PRESENT", "INDETERMINATE"),
        (True, 0, 0, 1, 303, "PRESENT", "INDETERMINATE"),
        (True, 259, 0, 2, None, "ABSENT", "INDETERMINATE"),
    ),
)
def test_marker_observation_matrix_is_closed(
    entered: bool,
    status: int | None,
    iosb: int | None,
    information: int | None,
    owned: int | None,
    leaf: str,
    expected: str,
) -> None:
    adapter = _isolated_mutation_factory_adapter(ctypes)

    result = adapter["classify_marker_observation"](entered, status, iosb, information, owned, leaf)

    assert result == expected


def test_marker_preflight_uncertainty_is_never_reported_as_retryable(tmp_path: Path) -> None:
    adapter = _isolated_mutation_factory_adapter(ctypes, retained_error="TRUSTED_PARENT_REQUIRED")
    authorization_sha256 = "9" * 64

    result = adapter["consume_marker"](tmp_path, authorization_sha256, b"canonical-marker")

    assert (result.create_entered, result.leaf_state, result.result) == (
        False,
        "INDETERMINATE",
        "INDETERMINATE",
    )
    assert adapter["attempt_states"][authorization_sha256] == "UNKNOWN"


def test_retained_publication_revalidates_ancestors_and_leaf_before_close() -> None:
    source_path = Path(run_evidence.__file__)
    tree = ast.parse(source_path.read_bytes(), filename=str(source_path))
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_make_evidence_mutation_surface"
    )
    retained_ancestor = next(
        node
        for node in factory.body
        if isinstance(node, ast.ClassDef) and node.name == "RetainedAncestor"
    )
    assert [
        node.target.id
        for node in retained_ancestor.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == ["handle", "volume_serial_number", "file_index"]

    for function_name in ("_publish_retained", "consume_marker"):
        function = next(
            node
            for node in ast.walk(factory)
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        )
        ordered_calls = [
            node.func.id
            for node in sorted(
                (item for item in ast.walk(function) if isinstance(item, ast.Call)),
                key=lambda item: (item.lineno, item.col_offset),
            )
            if isinstance(node.func, ast.Name)
        ]
        assert "_windows_flush" in ordered_calls
        assert "_revalidate_retained_ancestors" in ordered_calls
        assert "_revalidate_final_handle" in ordered_calls
        assert ordered_calls.index("_windows_flush") < ordered_calls.index(
            "_revalidate_retained_ancestors"
        )
        assert ordered_calls.index("_revalidate_retained_ancestors") < ordered_calls.index(
            "_revalidate_final_handle"
        )


@pytest.mark.parametrize(
    ("nt_result", "failing_handle", "expected_error", "expected_closes"),
    (
        ((True, 0, 0, 1, 202), None, "DESTINATION_EXISTS", (202, 101)),
        ((True, 259, 0, 0, 202), None, "TRUSTED_PARENT_REQUIRED", (202, 101)),
        ((True, 0, 0, 1, 202), 202, "PUBLICATION_FAILED", (202, 101)),
        ((True, 259, 0, 0, 202), 101, "PUBLICATION_FAILED", (202, 101)),
    ),
)
def test_retained_destination_closes_every_observed_handle(
    nt_result: tuple[bool, int, int, int, int],
    failing_handle: int | None,
    expected_error: str,
    expected_closes: tuple[int, ...],
) -> None:
    closes: list[int] = []

    def test_close(handle: int) -> bool:
        closes.append(handle)
        return handle != failing_handle

    adapter = _isolated_mutation_factory_adapter(
        ctypes,
        binding_overrides={
            "test_ancestors": [(101, (1, 2, 3), "C:\\")],
            "test_close": test_close,
            "test_nt_result": nt_result,
        },
        function_overrides={
            "_absolute_destination": "return destination",
            "_windows_open_trusted_ancestors": "return test_ancestors",
            "_windows_nt_relative_file": "return test_nt_result",
            "_windows_close": "return test_close(handle)",
        },
        exports=("_retained_destination",),
    )

    with pytest.raises(ValueError, match=f"^{expected_error}$"):
        adapter["_retained_destination"](Path("C:/outside/result.json"))

    assert tuple(closes) == expected_closes


@pytest.mark.parametrize(
    ("close_behavior", "expected_error"),
    (
        ("pass", "TRUSTED_PARENT_REQUIRED"),
        ("false", "PUBLICATION_FAILED"),
        ("raise", "PUBLICATION_FAILED"),
    ),
)
def test_trusted_ancestor_cleanup_owns_anomalous_nonnull_handle_before_validation(
    close_behavior: str,
    expected_error: str,
) -> None:
    closes: list[int] = []

    def test_close(handle: int) -> bool:
        closes.append(handle)
        if close_behavior == "raise":
            raise OSError("synthetic close failure")
        return close_behavior != "false"

    adapter = _isolated_mutation_factory_adapter(
        ctypes,
        binding_overrides={"test_close": test_close},
        function_overrides={
            "_windows_create_file": "return (101, 0)",
            "_windows_file_information": (
                "return (_WINDOWS_FILE_ATTRIBUTE_DIRECTORY, (1, 0, handle))"
            ),
            "_windows_normalized_handle_name": "return 'trusted'",
            "_windows_names_equal": "return True",
            "_windows_nt_relative_file": "return (True, 259, 0, 0, 202)",
            "_windows_close": "return test_close(handle)",
        },
        exports=("_windows_open_trusted_ancestors",),
    )

    with pytest.raises(ValueError, match=f"^{expected_error}$"):
        adapter["_windows_open_trusted_ancestors"](Path("C:/root/parent/result.json"))

    assert closes == [202, 101]


@pytest.mark.parametrize("close_behavior", ("pass", "false", "raise"))
def test_marker_probe_anomalous_handle_is_closed_and_never_proves_absence(
    close_behavior: str,
) -> None:
    closes: list[int] = []

    def test_close(handle: int) -> bool:
        closes.append(handle)
        if close_behavior == "raise":
            raise OSError("synthetic close failure")
        return close_behavior != "false"

    adapter = _isolated_mutation_factory_adapter(
        ctypes,
        binding_overrides={"test_close": test_close},
        function_overrides={
            "_windows_nt_relative_file": "return (False, -1073741772, 0, 0, 202)",
            "_windows_close": "return test_close(handle)",
        },
        exports=("_marker_leaf_state",),
    )
    destination = SimpleNamespace(parent_handle=101, leaf_name="marker.json")

    assert adapter["_marker_leaf_state"](destination) == "INDETERMINATE"
    assert closes == [202]


def test_clean_precall_keeps_in_progress_until_outer_pair_close_resolves(
    tmp_path: Path,
) -> None:
    destination = SimpleNamespace(
        parent_handle=101,
        leaf_name="marker.json",
        absolute_path=tmp_path / "marker.json",
        ancestors=(SimpleNamespace(handle=101, volume_serial_number=1),),
        closed=False,
    )
    adapter = _isolated_mutation_factory_adapter(
        ctypes,
        binding_overrides={"test_destination": destination},
        function_overrides={
            "_retained_destination": "return test_destination",
            "_windows_nt_relative_file": "return (False, None, None, None, None)",
            "_marker_leaf_state": "return 'ABSENT'",
            "close_destination": "return True",
        },
    )
    authorization_sha256 = "8" * 64

    first = adapter["consume_marker"](
        tmp_path,
        authorization_sha256,
        b"canonical-marker",
    )
    second = adapter["consume_marker"](
        tmp_path,
        authorization_sha256,
        b"canonical-marker",
    )

    assert first.result == "PRECALL_FAILED"
    assert adapter["attempt_states"][authorization_sha256] == "IN_PROGRESS"
    assert second.result == "INDETERMINATE"


@pytest.mark.parametrize("close_behavior", ("pass", "false", "raise"))
def test_created_marker_exception_closes_owned_leaf_and_retained_ancestors(
    tmp_path: Path,
    close_behavior: str,
) -> None:
    closes: list[int] = []

    def test_close(handle: int) -> bool:
        closes.append(handle)
        if close_behavior == "raise":
            raise OSError("synthetic close failure")
        return close_behavior != "false"

    destination = SimpleNamespace(
        parent_handle=101,
        leaf_name="marker.json",
        absolute_path=tmp_path / "marker.json",
        ancestors=(SimpleNamespace(handle=101, volume_serial_number=1),),
        closed=False,
    )
    adapter = _isolated_mutation_factory_adapter(
        ctypes,
        binding_overrides={
            "test_close": test_close,
            "test_destination": destination,
        },
        function_overrides={
            "_retained_destination": "return test_destination",
            "_windows_nt_relative_file": "return (True, 0, 0, 2, 202)",
            "_windows_file_information": ("raise _PublicationError('PUBLICATION_FAILED')"),
            "_windows_close": "return test_close(handle)",
        },
    )
    authorization_sha256 = "9" * 64

    result = adapter["consume_marker"](
        tmp_path,
        authorization_sha256,
        b"canonical-marker",
    )

    assert (result.result, result.leaf_state) == ("INDETERMINATE", "PRESENT")
    assert adapter["attempt_states"][authorization_sha256] == "UNKNOWN"
    assert closes == [202, 101]


def test_production_factory_is_deleted_and_exposes_exactly_two_wrappers() -> None:
    source = Path(run_evidence.__file__).read_text(encoding="utf-8")
    assert source.count("windll.ntdll.NtCreateFile") == 1
    assert "FlushFileBuffers(parent_handle)" not in source
    assert not hasattr(run_evidence, "_make_evidence_mutation_surface")
    assert not hasattr(run_evidence, "_MUTATION_BINDINGS")
    assert not hasattr(run_evidence, "RetainedDestination")
    assert not hasattr(run_evidence, "MarkerAttempt")


@pytest.mark.skipif(os.name != "nt", reason="formal marker publication is Windows-only")
def test_isolated_factory_consumes_one_marker_under_eight_callers(tmp_path: Path) -> None:
    adapter = _isolated_mutation_factory_adapter(ctypes)
    consumption_root = (tmp_path / "consumption").absolute()
    consumption_root.mkdir()
    authorization_sha256 = "9" * 64
    marker_bytes = canonicalize_json({"authorization_sha256": authorization_sha256})

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = tuple(
            pool.map(
                lambda _: adapter["consume_marker"](
                    consumption_root, authorization_sha256, marker_bytes
                ),
                range(8),
            )
        )

    assert sum(item.result == "CREATED" for item in outcomes) == 1
    assert all(item.result in {"CREATED", "COLLISION", "INDETERMINATE"} for item in outcomes)
    assert adapter["attempt_states"][authorization_sha256] == "CONSUMED"
    marker_path = consumption_root / f"{authorization_sha256}.consumed.json"
    assert marker_path.read_bytes() == marker_bytes
    repeated = adapter["consume_marker"](consumption_root, authorization_sha256, marker_bytes)
    assert repeated.result == "COLLISION"


@pytest.mark.parametrize(
    "mutation",
    (
        "extra_key",
        "unknown_metric",
        "nan",
        "uppercase_digest",
        "short_digest",
        "private_path",
        "raw_timestamp",
        "traceback",
        "credential",
        "raw_prediction",
    ),
)
def test_public_result_fails_closed(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "untrusted-result.json"
    path.write_text(json.dumps(mutate(valid_public_result(), mutation), allow_nan=True))
    assert verify_development_result(path).verdict == "FAIL"


def test_valid_closed_public_result_verifies_only_when_schema_and_bytes_are_canonical(
    tmp_path: Path,
) -> None:
    result = PublicDevelopmentResult.model_validate(valid_public_result())
    path = tmp_path / "result.json"
    path.write_bytes(canonicalize_json(result.model_dump(mode="json")))
    assert verify_development_result(path).verdict == "PASS"


def test_public_result_rejects_boolean_numeric_coercion() -> None:
    document = valid_public_result()
    document["h2_loaded_rows"] = False
    with pytest.raises(ValueError):
        PublicDevelopmentResult.model_validate(document)


def test_public_verifier_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_bytes(b'{"schema_version":"one","schema_version":"two"}')
    assert verify_development_result(path).verdict == "FAIL"


def test_canonical_public_result_bytes_returns_rfc8785_bytes() -> None:
    result = PublicDevelopmentResult.model_validate(valid_public_result())
    assert canonical_public_result_bytes(result) == canonicalize_json(
        result.model_dump(mode="json")
    )


def test_private_bundle_is_one_deterministic_canonical_file(tmp_path: Path) -> None:
    first = tmp_path / "first.container.json"
    second = tmp_path / "second.container.json"
    first_identity = write_synthetic_bundle_no_clobber(first, synthetic_private_bundle())
    second_identity = write_synthetic_bundle_no_clobber(second, synthetic_private_bundle())
    assert first.is_file() and second.is_file()
    assert first.read_bytes() == second.read_bytes()
    assert first_identity == second_identity
    assert run_evidence.verify_private_container(first, first_identity).verdict == "PASS"


def test_coordinated_internal_rehash_cannot_change_bound_container(tmp_path: Path) -> None:
    destination = tmp_path / "bundle.container.json"
    identity = write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    document = parse_json_bytes(destination.read_bytes())
    coordinate_payload_and_all_internal_digests(document)
    destination.write_bytes(canonicalize_json(document))
    assert run_evidence.verify_private_container(destination, identity).reason_codes == (
        "PRIVATE_CONTAINER_IDENTITY_MISMATCH",
    )


def test_private_container_builder_matches_independent_digest_construction() -> None:
    expected_bytes, expected_identity = private_container_bytes()
    actual_bytes, actual_identity = run_evidence._canonical_private_container(
        synthetic_private_bundle()
    )
    assert actual_bytes == expected_bytes
    assert actual_identity == expected_identity


@pytest.mark.parametrize(
    "mutation",
    (
        "top_extra",
        "entry_extra",
        "top_missing",
        "entry_missing",
        "missing_path",
        "extra_path",
        "duplicate_path",
        "reordered_paths",
        "count_boolean",
        "entry_size_boolean",
        "total_boolean",
        "uppercase_entry_digest",
        "short_inventory_digest",
        "bad_manifest_digest",
    ),
)
def test_private_container_closed_negative_matrix(tmp_path: Path, mutation: str) -> None:
    raw, identity = private_container_bytes()
    document = parse_json_bytes(raw)
    if mutation == "top_extra":
        document["extra"] = 1
    elif mutation == "entry_extra":
        document["entries"][0]["extra"] = 1
    elif mutation == "top_missing":
        del document["canonicalization_version"]
    elif mutation == "entry_missing":
        del document["entries"][0]["sha256"]
    elif mutation == "missing_path":
        document["entries"].pop()
    elif mutation == "extra_path":
        extra = dict(document["entries"][-1])
        extra["logical_path"] = "private/folds/F3.json"
        document["entries"].append(extra)
    elif mutation == "duplicate_path":
        document["entries"][1]["logical_path"] = document["entries"][0]["logical_path"]
    elif mutation == "reordered_paths":
        document["entries"].reverse()
    elif mutation == "count_boolean":
        document["file_count"] = True
    elif mutation == "entry_size_boolean":
        document["entries"][0]["byte_size"] = False
    elif mutation == "total_boolean":
        document["total_bytes"] = True
    elif mutation == "uppercase_entry_digest":
        document["entries"][0]["sha256"] = "A" * 64
    elif mutation == "short_inventory_digest":
        document["inventory_sha256"] = "a" * 63
    else:
        document["manifest_sha256"] = "g" * 64
    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, canonicalize_json(document)), identity
    )
    assert check.verdict == "FAIL"
    assert check.identity is None
    assert set(check.reason_codes) <= {
        "PRIVATE_CONTAINER_INVALID",
        "PRIVATE_CONTAINER_NONCANONICAL",
        "PRIVATE_CONTAINER_IDENTITY_MISMATCH",
        "PRIVATE_CONTAINER_SIZE_EXCEEDED",
    }


@pytest.mark.parametrize("scope", ("top", "entry"))
def test_private_container_duplicate_keys_fail_closed(tmp_path: Path, scope: str) -> None:
    raw, identity = private_container_bytes()
    if scope == "top":
        raw = raw.replace(
            b'{"canonicalization_version"',
            b'{"file_count":2,"canonicalization_version"',
            1,
        )
    else:
        raw = raw.replace(b'{"byte_size"', b'{"byte_size":1,"byte_size"', 1)
    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, raw), identity
    )
    assert check.reason_codes == ("PRIVATE_CONTAINER_INVALID",)


def test_private_container_noncanonical_outer_json_is_distinct(tmp_path: Path) -> None:
    raw, identity = private_container_bytes()
    noncanonical = json.dumps(parse_json_bytes(raw), indent=2).encode()
    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, noncanonical), identity
    )
    assert check.reason_codes == ("PRIVATE_CONTAINER_NONCANONICAL",)


@pytest.mark.parametrize("bad_base64", ("@@==", "e30", "e30===", "e3-9", "e30=\n", "Zh=="))
def test_private_container_requires_strict_canonical_base64(
    tmp_path: Path, bad_base64: str
) -> None:
    raw, identity = private_container_bytes()
    document = parse_json_bytes(raw)
    document["entries"][0]["payload_base64"] = bad_base64
    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, canonicalize_json(document)), identity
    )
    assert check.reason_codes == ("PRIVATE_CONTAINER_INVALID",)


def test_private_container_rejects_noncanonical_decoded_payload(tmp_path: Path) -> None:
    raw, identity = private_container_bytes()
    document = parse_json_bytes(raw)
    payload = b'{"z":1, "a":2}'
    entry = document["entries"][0]
    entry["payload_base64"] = base64.b64encode(payload).decode("ascii")
    entry["byte_size"] = len(payload)
    entry["sha256"] = sha256_hex(payload)
    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, canonicalize_json(document)), identity
    )
    assert check.reason_codes == ("PRIVATE_CONTAINER_NONCANONICAL",)


def test_private_container_rejects_non_file_and_link(tmp_path: Path) -> None:
    _, identity = private_container_bytes()
    directory = tmp_path / "directory"
    directory.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        completed = subprocess.run(
            ("cmd", "/c", "mklink", "/J", str(link), str(target)),
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            pytest.skip("the platform cannot create a junction in pytest tmp_path")
    assert run_evidence.verify_private_container(directory, identity).reason_codes == (
        "PRIVATE_CONTAINER_INVALID",
    )
    assert run_evidence.verify_private_container(link, identity).reason_codes == (
        "PRIVATE_CONTAINER_INVALID",
    )


def test_private_verifier_opens_once_without_path_preflight(
    tmp_path: Path,
) -> None:
    raw, identity = private_container_bytes()
    path = write_untrusted_container(tmp_path, raw)

    class GuardedPath(type(path)):
        def is_symlink(self) -> bool:
            raise AssertionError("verifier performed a path preflight")

        def is_file(self) -> bool:
            raise AssertionError("verifier performed a path preflight")

        def stat(self, *, follow_symlinks: bool = True) -> object:
            raise AssertionError("verifier performed a path preflight")

        def read_bytes(self) -> bytes:
            raise AssertionError("verifier reopened the path")

    assert run_evidence.verify_private_container(GuardedPath(path), identity).verdict == "PASS"


def test_posix_private_verifier_opens_fifo_nonblocking_before_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    read_descriptor, write_descriptor = os.pipe()
    nonblocking_flag = 0x800

    def open_fifo(_path: str, flags: int) -> int:
        if not flags & nonblocking_flag:
            raise AssertionError("POSIX FIFO open could block")
        return os.dup(read_descriptor)

    monkeypatch.setattr(run_evidence.os, "O_NOFOLLOW", 0x20000, raising=False)
    monkeypatch.setattr(run_evidence.os, "O_NONBLOCK", nonblocking_flag, raising=False)
    monkeypatch.setattr(run_evidence.os, "open", open_fifo)
    try:
        with pytest.raises(ValueError, match="^PRIVATE_CONTAINER_INVALID$"):
            run_evidence._read_private_container_posix(tmp_path / "untrusted.fifo")
    finally:
        os.close(read_descriptor)
        os.close(write_descriptor)


def test_private_container_entry_limit_is_128() -> None:
    bundle = PrivateRunBundle(
        evidence_class="synthetic_test",
        files=tuple(
            PrivateFoldEvidence(logical_path=f"private/{number:03d}.json", canonical_bytes=b"{}")
            for number in range(129)
        ),
    )
    with pytest.raises(ValueError, match="^PRIVATE_CONTAINER_SIZE_EXCEEDED$"):
        run_evidence._canonical_private_container(bundle)


def test_private_verifier_preflights_base64_size_before_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw, identity = private_container_bytes()
    path = write_untrusted_container(tmp_path, raw)

    def forbidden_decode(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("oversized payload reached base64 decoding")

    monkeypatch.setattr(run_evidence, "_MAX_PRIVATE_PAYLOAD_BYTES", 1)
    monkeypatch.setattr(run_evidence.base64, "b64decode", forbidden_decode)

    assert run_evidence.verify_private_container(path, identity).reason_codes == (
        "PRIVATE_CONTAINER_SIZE_EXCEEDED",
    )


def test_private_models_reject_precoercion_runtime_types() -> None:
    fold = PrivateFoldEvidence(logical_path="private/fold.json", canonical_bytes=b"{}")
    digest = "a" * 64

    with pytest.raises(ValueError):
        PrivateFoldEvidence(logical_path=b"private/fold.json", canonical_bytes=b"{}")
    with pytest.raises(ValueError):
        PrivateFoldEvidence(logical_path="private/fold.json", canonical_bytes="{}")
    with pytest.raises(ValueError):
        PrivateFoldEvidence(logical_path="private/fold.json", canonical_bytes=bytearray(b"{}"))
    with pytest.raises(ValueError):
        PrivateRunBundle(evidence_class=b"synthetic_test", files=(fold,))
    with pytest.raises(ValueError):
        PrivateRunBundle(evidence_class="synthetic_test", files=[fold])
    with pytest.raises(ValueError):
        PrivateBundleIdentity(
            file_count=1,
            total_bytes=2,
            inventory_sha256=digest.encode("ascii"),
            manifest_sha256=digest,
        )
    with pytest.raises(ValueError):
        PrivateBundleIdentity(
            file_count=1,
            total_bytes=2,
            inventory_sha256=digest,
            manifest_sha256=digest.upper(),
        )


def test_private_container_verifier_rejects_129_entries(tmp_path: Path) -> None:
    raw, identity = private_container_bytes()
    document = parse_json_bytes(raw)
    template = document["entries"][0]
    document["entries"] = [
        {**template, "logical_path": f"private/{number:03d}.json"} for number in range(129)
    ]
    document["file_count"] = 129

    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, canonicalize_json(document)), identity
    )

    assert check.reason_codes == ("PRIVATE_CONTAINER_SIZE_EXCEEDED",)


def test_private_container_empty_inventory_is_invalid_not_a_size_failure(
    tmp_path: Path,
) -> None:
    raw, identity = private_container_bytes()
    document = parse_json_bytes(raw)
    document["entries"] = []
    document["file_count"] = 0
    document["total_bytes"] = 0
    document["inventory_sha256"] = sha256_hex(canonicalize_json([]))
    manifest = {
        key: document[key]
        for key in (
            "schema_version",
            "canonicalization_version",
            "evidence_class",
            "file_count",
            "total_bytes",
            "inventory_sha256",
        )
    }
    document["manifest_sha256"] = sha256_hex(canonicalize_json(manifest))

    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, canonicalize_json(document)), identity
    )

    assert check.reason_codes == ("PRIVATE_CONTAINER_INVALID",)


@pytest.mark.parametrize("limit_name", ("payload", "aggregate", "container"))
def test_private_container_enforces_all_byte_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit_name: str
) -> None:
    if limit_name == "payload":
        monkeypatch.setattr(run_evidence, "_MAX_PRIVATE_PAYLOAD_BYTES", 1)
    elif limit_name == "aggregate":
        monkeypatch.setattr(run_evidence, "_MAX_PRIVATE_TOTAL_BYTES", 1)
    else:
        monkeypatch.setattr(run_evidence, "_MAX_PRIVATE_CONTAINER_BYTES", 1)
    with pytest.raises(ValueError, match="^PRIVATE_CONTAINER_SIZE_EXCEEDED$"):
        run_evidence._canonical_private_container(synthetic_private_bundle())
    raw, identity = private_container_bytes()
    check = run_evidence.verify_private_container(
        write_untrusted_container(tmp_path, raw), identity
    )
    assert check.reason_codes == ("PRIVATE_CONTAINER_SIZE_EXCEEDED",)


@pytest.mark.parametrize(
    "logical_path",
    (
        "/absolute.json",
        "private/雪.json",
        "private/./x.json",
        "private/../x.json",
        "private\\x.json",
        "private/CON",
        "private/PRN.json",
        "private/AUX",
        "private/NUL.txt",
        "private/COM1.bin",
        "private/LPT9",
        "private/a:.json",
        "private/x.",
        "private/x ",
        "private/a~1.json",
        f"private/{'a' * 65}.json",
        f"private/{'a' * 241}",
    ),
)
def test_private_logical_path_matrix_is_closed(logical_path: str) -> None:
    with pytest.raises(ValueError, match="LOGICAL_PATH_INVALID") as caught:
        PrivateFoldEvidence(logical_path=logical_path, canonical_bytes=b"{}")
    assert logical_path not in str(caught.value)


def test_private_writer_rejects_natural_development_without_permit(tmp_path: Path) -> None:
    source = synthetic_private_bundle()
    natural = PrivateRunBundle(evidence_class="natural_development", files=source.files)
    with pytest.raises(ValueError, match="^FORMAL_RUN_SEAL_AUTHORITY_REQUIRED$"):
        write_synthetic_bundle_no_clobber(tmp_path / "new.container.json", natural)
    assert tuple(tmp_path.iterdir()) == ()


def test_private_identity_rejects_boolean_counts_without_echoing_input() -> None:
    with pytest.raises(ValueError) as caught:
        PrivateBundleIdentity(
            file_count=True,
            total_bytes=2,
            inventory_sha256="a" * 64,
            manifest_sha256="b" * 64,
        )
    assert "True" not in str(caught.value)


def test_private_container_failures_expose_only_fixed_codes(tmp_path: Path) -> None:
    secret = "PRIVATE_PAYLOAD_SENTINEL"
    path = tmp_path / secret
    path.write_text(secret)
    _, identity = private_container_bytes()
    result = run_evidence.verify_private_container(path, identity)
    assert result.reason_codes == ("PRIVATE_CONTAINER_INVALID",)
    assert secret not in repr(result)


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
@pytest.mark.parametrize("kind", ("file", "directory", "link"))
def test_windows_private_writer_rejects_existing_destination(tmp_path: Path, kind: str) -> None:
    destination = tmp_path / "bundle.container.json"
    if kind == "file":
        destination.write_bytes(b"sentinel")
    elif kind == "directory":
        destination.mkdir()
    else:
        target = tmp_path / "target"
        target.mkdir()
        try:
            destination.symlink_to(target, target_is_directory=True)
        except OSError:
            completed = subprocess.run(
                ("cmd", "/c", "mklink", "/J", str(destination), str(target)),
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                pytest.skip("the platform cannot create a junction in pytest tmp_path")
    with pytest.raises(ValueError, match="^DESTINATION_EXISTS$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    if kind == "file":
        assert destination.read_bytes() == b"sentinel"


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_windows_second_publication_is_no_clobber(tmp_path: Path) -> None:
    destination = tmp_path / "bundle.container.json"
    identity = write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    original = destination.read_bytes()
    with pytest.raises(ValueError, match="^DESTINATION_EXISTS$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert destination.read_bytes() == original
    assert run_evidence.verify_private_container(destination, identity).verdict == "PASS"


def test_private_bundle_public_identity_contains_no_private_material() -> None:
    _, identity = private_container_bytes()
    assert set(identity.model_dump()) == {
        "file_count",
        "total_bytes",
        "inventory_sha256",
        "manifest_sha256",
    }
    assert public_evidence_violations(identity.model_dump(mode="json")) == ()


def test_bounded_transport_uses_one_fixed_process_and_exact_launch_profile(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    executable = tmp_path / "python.exe"
    worker = repository / "src/mdcp/temporal/formal_worker.py"
    worker.parent.mkdir(parents=True)
    executable.write_bytes(b"python")
    worker.write_bytes(b"worker")
    launches: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class Input:
        def __init__(self) -> None:
            self.raw = bytearray()
            self.closed = False

        def write(self, raw: bytes) -> int:
            self.raw.extend(raw)
            return len(raw)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    class Output:
        def __init__(self, raw: bytes) -> None:
            self.raw = raw
            self.offset = 0

        def read(self, size: int) -> bytes:
            chunk = self.raw[self.offset : self.offset + size]
            self.offset += len(chunk)
            return chunk

    class Process:
        def __init__(self) -> None:
            self.stdin = Input()
            self.stdout = Output(b"response")
            self.returncode = 0
            self.terminations = 0

        def wait(self, timeout: float) -> int:
            assert 0 < timeout <= 21_600
            return self.returncode

        def terminate(self) -> None:
            self.terminations += 1

    process = Process()

    def factory(*arguments: object, **keywords: object) -> Process:
        launches.append((arguments, keywords))
        return process

    result = run_evidence._run_fixed_worker_transport(
        repository,
        executable,
        worker,
        b"request",
        _process_factory=factory,
        _monotonic=lambda: 100.0,
        _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
    )

    assert result == b"response"
    assert process.stdin.raw == b"request"
    assert process.stdin.closed is True
    assert process.terminations == 0
    assert len(launches) == 1
    arguments, keywords = launches[0]
    assert arguments == ([str(executable), "-I", "-B", "-S", str(worker)],)
    assert keywords["shell"] is False
    assert keywords["cwd"] == str(repository)
    assert keywords["close_fds"] is True
    assert keywords["stdin"] is subprocess.PIPE
    assert keywords["stdout"] is subprocess.PIPE
    assert keywords["stderr"] is subprocess.DEVNULL
    assert keywords["env"] == {"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"}


def test_bounded_transport_detects_the_65537th_stdout_byte_without_retry(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    executable = tmp_path / "python.exe"
    worker = tmp_path / "formal_worker.py"
    executable.write_bytes(b"python")
    worker.write_bytes(b"worker")
    launches = 0

    class Input:
        def write(self, raw: bytes) -> int:
            return len(raw)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            return None

    class Output:
        def __init__(self) -> None:
            self.remaining = 65_537

        def read(self, size: int) -> bytes:
            count = min(size, self.remaining)
            self.remaining -= count
            return b"x" * count

    class Process:
        stdin = Input()
        stdout = Output()
        returncode = 0

        def __init__(self) -> None:
            self.terminations = 0

        def wait(self, timeout: float) -> int:
            return 0

        def terminate(self) -> None:
            self.terminations += 1

    process = Process()

    def factory(*_arguments: object, **_keywords: object) -> Process:
        nonlocal launches
        launches += 1
        return process

    with pytest.raises(run_evidence._WorkerProcessUnknown):
        run_evidence._run_fixed_worker_transport(
            repository,
            executable,
            worker,
            b"request",
            _process_factory=factory,
            _monotonic=lambda: 0.0,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )
    assert launches == 1
    assert process.terminations == 1


def _task_four_preflight_fixture(
    tmp_path: Path,
) -> tuple[
    run_evidence.FormalDevelopmentRequest,
    dict[str, object],
]:
    source_commit = "1" * 40
    head = "2" * 40
    repository = tmp_path / "repository"
    external = tmp_path / "external"
    repository.mkdir()
    external.mkdir()
    physical: dict[str, bytes] = {}
    for number, logical_path in enumerate(worker_protocol.SEARCH_SOURCE_PATHS):
        raw = f"reviewed-source-{number:02d}".encode()
        path = repository / logical_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        physical[logical_path] = raw
    for logical_path in worker_protocol.FORMAL_WORKER_SOURCE_PATHS:
        if logical_path not in physical:
            path = repository / logical_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"worker-source:{logical_path}".encode())

    current_receipt = worker_protocol.SearchReceipt.model_validate(
        parse_json_bytes(
            (REPOSITORY_ROOT / "evidence/public/v02/search/search-receipt.json").read_bytes()
        )
    )
    receipt = current_receipt.model_copy(update={"search_source_commit": source_commit})
    entries = tuple(
        worker_protocol.SearchSourceEntry(
            logical_path=logical_path,
            git_mode="100644",
            byte_size=len(physical[logical_path]),
            sha256=sha256_hex(physical[logical_path]),
        )
        for logical_path in worker_protocol.SEARCH_SOURCE_PATHS
    )
    authorization_path = external / "authorization.json"
    archive_path = external / "archive.zip"
    consumption_root = external / "consumption"
    private_parent = external / "private"
    archive_path.write_bytes(b"synthetic-archive-placeholder")
    consumption_root.mkdir()
    private_parent.mkdir()
    request = run_evidence.FormalDevelopmentRequest(
        repository_root=repository,
        expected_freeze_head=head,
        search_receipt_path=repository / "evidence/public/v02/search/search-receipt.json",
        evidence_index_path=repository / "evidence/public/v02/search/evidence-index.json",
        authorization_path=authorization_path,
        consumption_root=consumption_root,
        archive_path=archive_path,
        private_container_path=private_parent / "formal.container.json",
    )
    state: dict[str, object] = {
        "repository": repository,
        "physical": physical,
        "receipt": receipt,
        "entries": entries,
        "request": request,
        "authorization_path": authorization_path,
        "freeze_parents": (source_commit,),
        "freeze_diff": (
            ("A", "evidence/public/v02/search/evidence-index.json"),
            ("A", "evidence/public/v02/search/search-receipt.json"),
        ),
        "freeze_source_entries": tuple(
            ("100644", "blob", logical_path) for logical_path in worker_protocol.SEARCH_SOURCE_PATHS
        ),
    }
    return request, state


def _write_task_four_preflight_documents(state: dict[str, object]) -> None:
    repository = state["repository"]
    receipt = state["receipt"]
    entries = state["entries"]
    request = state["request"]
    authorization_path = state["authorization_path"]
    assert isinstance(repository, Path)
    assert isinstance(receipt, worker_protocol.SearchReceipt)
    assert isinstance(entries, tuple)
    assert isinstance(request, run_evidence.FormalDevelopmentRequest)
    assert isinstance(authorization_path, Path)
    receipt_raw = canonicalize_json(receipt.model_dump(mode="json"))
    receipt_sha256 = sha256_hex(receipt_raw)
    index = worker_protocol.SearchEvidenceIndex(
        schema_version="mdcp.search-evidence-index.v1",
        canonicalization_version="RFC8785",
        source_entries=entries,
        source_inventory_sha256=worker_protocol.search_source_inventory_sha256(entries),
        private_logical_outputs=worker_protocol.PRIVATE_LOGICAL_OUTPUTS,
        search_receipt_sha256=receipt_sha256,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )
    authorization = worker_protocol.FormalRunAuthorization(
        schema_version="mdcp.formal-run-authorization.v1",
        canonicalization_version="RFC8785",
        search_freeze_commit=request.expected_freeze_head,
        search_receipt_sha256=receipt_sha256,
        protocol_sha256=receipt.dataset_contract_sha256,
        dataset_archive_sha256=receipt.dataset_archive_sha256,
        authorization_id="12345678-1234-4123-8123-123456789abc",
        authorized_action="ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN",
        authorized_at_utc="2026-08-28T00:00:00Z",
        consumed=False,
    )
    request.search_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    request.search_receipt_path.write_bytes(receipt_raw)
    request.evidence_index_path.write_bytes(canonicalize_json(index.model_dump(mode="json")))
    authorization_path.write_bytes(canonicalize_json(authorization.model_dump(mode="json")))


def _install_task_four_topology_git(
    monkeypatch: pytest.MonkeyPatch,
    state: dict[str, object],
) -> None:
    repository = state["repository"]
    request = state["request"]
    parents = state["freeze_parents"]
    diff = state["freeze_diff"]
    source_entries = state["freeze_source_entries"]
    assert isinstance(repository, Path)
    assert isinstance(request, run_evidence.FormalDevelopmentRequest)
    assert isinstance(parents, tuple)
    assert isinstance(diff, tuple)
    assert isinstance(source_entries, tuple)

    def fixed_git(root: Path, *arguments: str) -> bytes:
        assert root == repository
        if arguments == ("show", "-s", "--format=%P", request.expected_freeze_head):
            return (" ".join(parents) + "\n").encode("ascii")
        if arguments == (
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            request.expected_freeze_head,
        ):
            return "".join(f"{status}\t{logical_path}\n" for status, logical_path in diff).encode(
                "utf-8"
            )
        if arguments == (
            "ls-tree",
            request.expected_freeze_head,
            "--",
            *worker_protocol.SEARCH_SOURCE_PATHS,
        ):
            return "".join(
                f"{mode} {object_type} {'a' * 40}\t{logical_path}\n"
                for mode, object_type, logical_path in source_entries
            ).encode("utf-8")
        raise AssertionError(f"unexpected git arguments: {arguments!r}")

    monkeypatch.setattr(run_evidence, "_git_bytes", fixed_git)


def _install_task_four_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    request: run_evidence.FormalDevelopmentRequest,
) -> None:
    monkeypatch.setattr(
        run_evidence,
        "_repository_snapshot",
        lambda *_args, **_kwargs: run_evidence._RepositorySnapshot(
            head=request.expected_freeze_head,
            inventory_sha256="a" * 64,
        ),
    )


def test_task_four_round_two_preflight_accepts_direct_child_freeze_topology(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, state = _task_four_preflight_fixture(tmp_path)
    _write_task_four_preflight_documents(state)
    _install_task_four_topology_git(monkeypatch, state)
    _install_task_four_snapshot(monkeypatch, request)
    launches = 0

    def launch_once(*_args: object, **_kwargs: object) -> bytes:
        nonlocal launches
        launches += 1
        raise run_evidence._WorkerLaunchFailed

    monkeypatch.setattr(run_evidence, "_run_fixed_worker_transport", launch_once)

    outcome = run_evidence.execute_authorized_formal_development(request)

    assert launches == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "FAIL",
        ("FORMAL_WORKER_LAUNCH_FAILED",),
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "self_reference",
        "wrong_parent",
        "zero_parents",
        "multiple_parents",
        "wrong_diff_status",
        "missing_diff_path",
        "extra_diff_path",
        "wrong_diff_path",
        "wrong_source_mode",
        "wrong_source_type",
        "wrong_source_path_order",
    ),
)
def test_task_four_round_two_preflight_rejects_invalid_freeze_topology(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    request, state = _task_four_preflight_fixture(tmp_path)
    receipt = state["receipt"]
    assert isinstance(receipt, worker_protocol.SearchReceipt)
    if mutation == "self_reference":
        state["receipt"] = receipt.model_copy(
            update={"search_source_commit": request.expected_freeze_head}
        )
        state["freeze_parents"] = (request.expected_freeze_head,)
    elif mutation == "wrong_parent":
        state["freeze_parents"] = ("3" * 40,)
    elif mutation == "zero_parents":
        state["freeze_parents"] = ()
    elif mutation == "multiple_parents":
        state["freeze_parents"] = (receipt.search_source_commit, "3" * 40)
    elif mutation == "wrong_diff_status":
        state["freeze_diff"] = (
            ("M", "evidence/public/v02/search/evidence-index.json"),
            ("A", "evidence/public/v02/search/search-receipt.json"),
        )
    elif mutation == "missing_diff_path":
        state["freeze_diff"] = (("A", "evidence/public/v02/search/evidence-index.json"),)
    elif mutation == "extra_diff_path":
        state["freeze_diff"] = (*state["freeze_diff"], ("A", "unexpected.json"))
    elif mutation == "wrong_diff_path":
        state["freeze_diff"] = (
            ("A", "evidence/public/v02/search/evidence-index.json"),
            ("A", "evidence/public/v02/search/wrong-receipt.json"),
        )
    else:
        source_entries = list(state["freeze_source_entries"])
        mode, object_type, logical_path = source_entries[0]
        if mutation == "wrong_source_mode":
            source_entries[0] = ("100755", object_type, logical_path)
        elif mutation == "wrong_source_type":
            source_entries[0] = (mode, "tree", logical_path)
        else:
            source_entries[0], source_entries[1] = source_entries[1], source_entries[0]
        state["freeze_source_entries"] = tuple(source_entries)
    _write_task_four_preflight_documents(state)
    _install_task_four_topology_git(monkeypatch, state)
    _install_task_four_snapshot(monkeypatch, request)
    launches = 0

    def forbidden_transport(*_args: object, **_kwargs: object) -> bytes:
        nonlocal launches
        launches += 1
        raise run_evidence._WorkerLaunchFailed

    monkeypatch.setattr(run_evidence, "_run_fixed_worker_transport", forbidden_transport)

    outcome = run_evidence.execute_authorized_formal_development(request)

    assert launches == 0
    assert (outcome.verdict, outcome.reason_codes) == (
        "FAIL",
        ("FORMAL_RUN_REQUEST_INVALID",),
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "stale_source_entry",
        "wrong_source_size",
        "wrong_source_hash",
        "physical_source_mismatch",
    ),
)
def test_task_four_corrective_preflight_binds_freeze_to_physical_source_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    request, state = _task_four_preflight_fixture(tmp_path)
    entries = list(state["entries"])
    first = entries[0]
    assert isinstance(first, worker_protocol.SearchSourceEntry)
    if mutation == "stale_source_entry":
        stale = b"stale-reviewed-source"
        entries[0] = first.model_copy(update={"byte_size": len(stale), "sha256": sha256_hex(stale)})
        state["entries"] = tuple(entries)
    elif mutation == "wrong_source_size":
        entries[0] = first.model_copy(update={"byte_size": first.byte_size + 1})
        state["entries"] = tuple(entries)
    elif mutation == "wrong_source_hash":
        entries[0] = first.model_copy(update={"sha256": "f" * 64})
        state["entries"] = tuple(entries)
    else:
        repository = state["repository"]
        assert isinstance(repository, Path)
        (repository / first.logical_path).write_bytes(b"physical-drift-after-index")
    _write_task_four_preflight_documents(state)
    _install_task_four_topology_git(monkeypatch, state)

    launches = 0

    def forbidden_transport(*_args: object, **_kwargs: object) -> bytes:
        nonlocal launches
        launches += 1
        raise run_evidence._WorkerLaunchFailed

    _install_task_four_snapshot(monkeypatch, request)
    monkeypatch.setattr(run_evidence, "_run_fixed_worker_transport", forbidden_transport)

    outcome = run_evidence.execute_authorized_formal_development(request)

    assert launches == 0
    assert (outcome.verdict, outcome.reason_codes) == (
        "FAIL",
        ("FORMAL_RUN_REQUEST_INVALID",),
    )
    assert outcome.fit_count == 0
    assert outcome.private_identity is None
    assert outcome.seal_record_sha256 is None
    assert outcome.repository_inventory_sha256 is None


def test_task_four_corrective_overflow_terminates_before_blocked_process_wait(
    tmp_path: Path,
) -> None:
    overflow_read = threading.Event()
    terminated = threading.Event()
    events: list[tuple[str, float | None]] = []

    class Input:
        def write(self, raw: bytes) -> int:
            return len(raw)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            return None

    class Output:
        def read(self, size: int) -> bytes:
            overflow_read.set()
            return b"x" * size

    class Process:
        stdin = Input()
        stdout = Output()

        def wait(self, timeout: float) -> int:
            events.append(("wait", timeout))
            if timeout == worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS:
                assert terminated.is_set()
                return 1
            assert overflow_read.wait(1.0)
            if not terminated.wait(0.25):
                events.append(("formal_wait_expired_before_termination", timeout))
                raise TimeoutError
            return 1

        def terminate(self) -> None:
            events.append(("terminate", None))
            terminated.set()

    with pytest.raises(run_evidence._WorkerProcessUnknown):
        run_evidence._run_fixed_worker_transport(
            tmp_path,
            tmp_path / "python.exe",
            tmp_path / "formal_worker.py",
            b"request",
            _process_factory=lambda *_args, **_kwargs: Process(),
            _monotonic=lambda: 0.0,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )

    assert not any(event[0] == "formal_wait_expired_before_termination" for event in events)
    assert sum(event[0] == "terminate" for event in events) == 1
    assert (
        sum(
            event == ("wait", worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS)
            for event in events
        )
        == 1
    )


class _TaskFourMatrixInput:
    def __init__(self, *, close_error: bool = False, write_zero: bool = False) -> None:
        self.close_error = close_error
        self.write_zero = write_zero

    def write(self, raw: bytes) -> int:
        return 0 if self.write_zero else len(raw)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        if self.close_error:
            raise OSError


class _TaskFourMatrixOutput:
    def __init__(
        self,
        raw: bytes = b"response",
        *,
        read_error: bool = False,
        missing_eof: bool = False,
        wrong_type: bool = False,
    ) -> None:
        self.raw = raw
        self.read_error = read_error
        self.missing_eof = missing_eof
        self.wrong_type = wrong_type
        self.reads = 0

    def read(self, size: int) -> bytes:
        self.reads += 1
        if self.read_error:
            raise OSError
        if self.wrong_type:
            return "not-bytes"  # type: ignore[return-value]
        if self.missing_eof and self.reads > 1:
            raise OSError
        raw, self.raw = self.raw[:size], self.raw[size:]
        return raw


class _TaskFourMatrixProcess:
    def __init__(
        self,
        *,
        returncode: int = 0,
        close_error: bool = False,
        write_zero: bool = False,
        read_error: bool = False,
        missing_eof: bool = False,
        wrong_type: bool = False,
        wait_error: bool = False,
    ) -> None:
        self.stdin = _TaskFourMatrixInput(close_error=close_error, write_zero=write_zero)
        self.stdout = _TaskFourMatrixOutput(
            read_error=read_error,
            missing_eof=missing_eof,
            wrong_type=wrong_type,
        )
        self.returncode = returncode
        self.wait_error = wait_error
        self.terminations = 0
        self.waits: list[float] = []

    def wait(self, timeout: float) -> int:
        self.waits.append(timeout)
        if self.wait_error and timeout != worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS:
            raise OSError
        return self.returncode

    def terminate(self) -> None:
        self.terminations += 1


def test_task_four_corrective_request_cap_and_creation_failure_are_precreation() -> None:
    launches = 0

    def factory(*_args: object, **_kwargs: object) -> object:
        nonlocal launches
        launches += 1
        raise OSError

    with pytest.raises(run_evidence._WorkerLaunchFailed):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"x" * (worker_protocol.MAX_WORKER_MESSAGE_BYTES + 1),
            _process_factory=factory,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )
    assert launches == 0

    with pytest.raises(run_evidence._WorkerLaunchFailed):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"request",
            _process_factory=factory,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )
    assert launches == 1


@pytest.mark.parametrize(
    ("failure", "process_kwargs"),
    (
        ("request_eof", {"close_error": True}),
        ("request_write", {"write_zero": True}),
        ("stdout_read", {"read_error": True}),
        ("stdout_missing_eof", {"missing_eof": True}),
        ("stdout_wrong_type", {"wrong_type": True}),
        ("nonzero_exit", {"returncode": 2}),
        ("unobservable_exit", {"wait_error": True}),
    ),
)
def test_task_four_corrective_postcreation_failure_matrix_is_one_shot(
    failure: str,
    process_kwargs: dict[str, object],
) -> None:
    del failure
    launches = 0
    process = _TaskFourMatrixProcess(**process_kwargs)

    def factory(*_args: object, **_kwargs: object) -> _TaskFourMatrixProcess:
        nonlocal launches
        launches += 1
        return process

    with pytest.raises(run_evidence._WorkerProcessUnknown):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"request",
            _process_factory=factory,
            _monotonic=lambda: 0.0,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )

    assert launches == 1
    assert process.terminations == 1
    assert process.waits.count(worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS) == 1


@pytest.mark.parametrize("failure", ("construction", "start"))
def test_task_four_corrective_thread_setup_failure_is_sanitized_after_creation(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    process = _TaskFourMatrixProcess()
    launches = 0

    def factory(*_args: object, **_kwargs: object) -> _TaskFourMatrixProcess:
        nonlocal launches
        launches += 1
        return process

    class BrokenStartThread:
        def start(self) -> None:
            raise RuntimeError("thread start sentinel")

    def broken_thread(*_args: object, **_kwargs: object) -> object:
        if failure == "construction":
            raise RuntimeError("thread construction sentinel")
        return BrokenStartThread()

    monkeypatch.setattr(threading, "Thread", broken_thread)
    with pytest.raises(run_evidence._WorkerProcessUnknown):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"request",
            _process_factory=factory,
            _monotonic=lambda: 0.0,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )
    assert launches == 1
    assert process.terminations == 1
    assert process.waits.count(worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS) == 1


def test_task_four_round_two_event_construction_failure_is_normalized_after_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _TaskFourMatrixProcess()
    launches = 0

    def factory(*_args: object, **_kwargs: object) -> _TaskFourMatrixProcess:
        nonlocal launches
        launches += 1
        return process

    def broken_event() -> object:
        raise RuntimeError("event construction sentinel")

    monkeypatch.setattr(threading, "Event", broken_event)
    with pytest.raises(run_evidence._WorkerProcessUnknown):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"request",
            _process_factory=factory,
            _monotonic=lambda: 0.0,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )

    assert launches == 1
    assert process.terminations == 1
    assert process.waits.count(worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS) == 1


def test_task_four_round_two_event_failure_is_publicly_sanitized_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = _task_four_acceptance_fixture(tmp_path)
    process = _TaskFourMatrixProcess()
    launches = 0

    def factory(*_args: object, **_kwargs: object) -> _TaskFourMatrixProcess:
        nonlocal launches
        launches += 1
        return process

    def broken_event() -> object:
        raise RuntimeError("event construction sentinel")

    monkeypatch.setattr(run_evidence, "_supervisor_preflight", lambda _request: launch)
    monkeypatch.setattr(subprocess, "Popen", factory)
    monkeypatch.setattr(threading, "Event", broken_event)
    monkeypatch.setenv("SYSTEMROOT", "C:/Windows")
    monkeypatch.setenv("WINDIR", "C:/Windows")
    request = run_evidence.FormalDevelopmentRequest(
        repository_root=launch.repository_root,
        expected_freeze_head=launch.snapshot.head,
        search_receipt_path=Path("C:/repository/receipt.json"),
        evidence_index_path=Path("C:/repository/index.json"),
        authorization_path=Path("C:/external/authorization.json"),
        consumption_root=Path("C:/external/consumption"),
        archive_path=Path("C:/external/archive.zip"),
        private_container_path=Path("C:/external/private.json"),
    )

    outcome = run_evidence.execute_authorized_formal_development(request)

    assert launches == 1
    assert process.terminations == 1
    assert process.waits.count(worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS) == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_WORKER_PROCESS_UNKNOWN",),
    )
    assert outcome.fit_count is None
    assert outcome.private_identity is None
    assert outcome.seal_record_sha256 is None
    assert outcome.repository_inventory_sha256 is None


def test_task_four_round_two_deadline_failure_is_launch_failed_before_creation() -> None:
    launches = 0

    def factory(*_args: object, **_kwargs: object) -> _TaskFourMatrixProcess:
        nonlocal launches
        launches += 1
        return _TaskFourMatrixProcess()

    def broken_monotonic() -> float:
        raise RuntimeError("deadline sentinel")

    with pytest.raises(run_evidence._WorkerLaunchFailed):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"request",
            _process_factory=factory,
            _monotonic=broken_monotonic,
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )

    assert launches == 0


def test_task_four_corrective_timeout_is_one_shot_and_sanitized() -> None:
    process = _TaskFourMatrixProcess()
    launches = 0
    monotonic_values = iter((0.0, 21_601.0, 21_601.0, 21_601.0))

    def factory(*_args: object, **_kwargs: object) -> _TaskFourMatrixProcess:
        nonlocal launches
        launches += 1
        return process

    with pytest.raises(run_evidence._WorkerProcessUnknown):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"request",
            _process_factory=factory,
            _monotonic=lambda: next(monotonic_values),
            _environment={"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows"},
        )

    assert launches == 1
    assert process.terminations == 1
    assert process.waits.count(worker_protocol.FORMAL_WORKER_TERMINATION_WAIT_SECONDS) == 1


def _task_four_acceptance_fixture(tmp_path: Path) -> run_evidence._SupervisorLaunch:
    request = worker_protocol.FormalWorkerRequest(
        schema_version="mdcp.formal-worker-request.v1",
        canonicalization_version="RFC8785",
        expected_freeze_head="1" * 40,
        repository_root="C:/repository",
        search_receipt_path="C:/repository/receipt.json",
        evidence_index_path="C:/repository/index.json",
        authorization_path="C:/external/authorization.json",
        consumption_root="C:/external/consumption",
        archive_path="C:/external/archive.zip",
        private_container_path="C:/external/private.json",
        search_receipt_sha256="1" * 64,
        evidence_index_sha256="2" * 64,
        authorization_sha256="3" * 64,
        source_inventory_sha256="4" * 64,
        repository_inventory_sha256="5" * 64,
        formal_worker_inventory_sha256="6" * 64,
        launch_profile_sha256="7" * 64,
    )
    return run_evidence._SupervisorLaunch(
        repository_root=tmp_path,
        executable=tmp_path / "python.exe",
        worker_script=tmp_path / "formal_worker.py",
        request=request,
        request_bytes=worker_protocol.encode_formal_worker_request(request),
        request_sha256=worker_protocol.worker_request_sha256(request),
        snapshot=run_evidence._RepositorySnapshot(
            head=request.expected_freeze_head,
            inventory_sha256=request.repository_inventory_sha256,
        ),
        terminal_seal_path=tmp_path / "formal.public.json",
    )


def _task_four_fail_response(
    launch: run_evidence._SupervisorLaunch,
) -> worker_protocol.FormalWorkerResponse:
    return worker_protocol.FormalWorkerResponse(
        schema_version="mdcp.formal-worker-response.v1",
        canonicalization_version="RFC8785",
        verdict="FAIL",
        reason_codes=("FORMAL_RUN_REQUEST_INVALID",),
        private_identity=None,
        seal_record_sha256=None,
        repository_inventory_sha256=None,
        authorization_sha256="0" * 64,
        consumption_marker_sha256=None,
        fit_count=0,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
        worker_request_sha256=launch.request_sha256,
        formal_worker_inventory_sha256=launch.request.formal_worker_inventory_sha256,
        launch_profile_sha256=launch.request.launch_profile_sha256,
    )


def test_task_four_corrective_public_surface_rejects_caller_launch_arguments() -> None:
    request = run_evidence.FormalDevelopmentRequest(
        repository_root=Path("C:/repository"),
        expected_freeze_head="1" * 40,
        search_receipt_path=Path("C:/repository/receipt.json"),
        evidence_index_path=Path("C:/repository/index.json"),
        authorization_path=Path("C:/external/authorization.json"),
        consumption_root=Path("C:/external/consumption"),
        archive_path=Path("C:/external/archive.zip"),
        private_container_path=Path("C:/external/private.json"),
    )
    with pytest.raises(TypeError):
        run_evidence.execute_authorized_formal_development(  # type: ignore[call-arg]
            request,
            executable=Path("C:/alternate-python.exe"),
        )


def test_task_four_corrective_transport_rejects_path_environment_before_creation() -> None:
    launches = 0

    def factory(*_args: object, **_kwargs: object) -> _TaskFourMatrixProcess:
        nonlocal launches
        launches += 1
        return _TaskFourMatrixProcess()

    with pytest.raises(run_evidence._WorkerLaunchFailed):
        run_evidence._run_fixed_worker_transport(
            Path("C:/repository"),
            Path("C:/python.exe"),
            Path("C:/formal_worker.py"),
            b"request",
            _process_factory=factory,
            _environment={
                "SYSTEMROOT": "C:/Windows",
                "WINDIR": "C:/Windows",
                "PATH": "C:/forbidden",
            },
        )
    assert launches == 0


def test_task_four_corrective_preflight_rejects_relative_interpreter_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, state = _task_four_preflight_fixture(tmp_path)
    _write_task_four_preflight_documents(state)
    _install_task_four_topology_git(monkeypatch, state)
    launches = 0

    def forbidden_transport(*_args: object, **_kwargs: object) -> bytes:
        nonlocal launches
        launches += 1
        raise run_evidence._WorkerLaunchFailed

    monkeypatch.setattr(
        run_evidence,
        "_repository_snapshot",
        lambda *_args, **_kwargs: run_evidence._RepositorySnapshot(
            head=request.expected_freeze_head,
            inventory_sha256="a" * 64,
        ),
    )
    monkeypatch.setattr(run_evidence, "_run_fixed_worker_transport", forbidden_transport)
    monkeypatch.setattr(sys, "executable", "python.exe")

    outcome = run_evidence.execute_authorized_formal_development(request)

    assert launches == 0
    assert (outcome.verdict, outcome.reason_codes) == (
        "FAIL",
        ("FORMAL_RUN_REQUEST_INVALID",),
    )


def test_task_four_corrective_changed_worker_script_is_rejected_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, state = _task_four_preflight_fixture(tmp_path)
    _write_task_four_preflight_documents(state)
    _install_task_four_topology_git(monkeypatch, state)
    launches = 0

    def forbidden_transport(*_args: object, **_kwargs: object) -> bytes:
        nonlocal launches
        launches += 1
        raise run_evidence._WorkerLaunchFailed

    monkeypatch.setattr(
        run_evidence,
        "_repository_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("changed worker script")),
    )
    monkeypatch.setattr(run_evidence, "_run_fixed_worker_transport", forbidden_transport)

    outcome = run_evidence.execute_authorized_formal_development(request)

    assert launches == 0
    assert (outcome.verdict, outcome.reason_codes) == (
        "FAIL",
        ("FORMAL_RUN_REQUEST_INVALID",),
    )


def test_task_four_corrective_process_creation_failure_is_sanitized_publicly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = _task_four_acceptance_fixture(tmp_path)
    launches = 0

    def creation_failure(*_args: object, **_kwargs: object) -> bytes:
        nonlocal launches
        launches += 1
        raise run_evidence._WorkerLaunchFailed

    monkeypatch.setattr(run_evidence, "_supervisor_preflight", lambda _request: launch)
    monkeypatch.setattr(run_evidence, "_run_fixed_worker_transport", creation_failure)
    request = run_evidence.FormalDevelopmentRequest(
        repository_root=tmp_path,
        expected_freeze_head=launch.snapshot.head,
        search_receipt_path=Path("C:/repository/receipt.json"),
        evidence_index_path=Path("C:/repository/index.json"),
        authorization_path=Path("C:/external/authorization.json"),
        consumption_root=Path("C:/external/consumption"),
        archive_path=Path("C:/external/archive.zip"),
        private_container_path=Path("C:/external/private.json"),
    )

    outcome = run_evidence.execute_authorized_formal_development(request)

    assert launches == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "FAIL",
        ("FORMAL_WORKER_LAUNCH_FAILED",),
    )
    assert outcome.fit_count is None
    assert outcome.private_identity is None
    assert outcome.seal_record_sha256 is None
    assert outcome.repository_inventory_sha256 is None


def _execute_task_four_fake_response(
    monkeypatch: pytest.MonkeyPatch,
    launch: run_evidence._SupervisorLaunch,
    raw: bytes,
    *,
    after: object | None = None,
) -> tuple[run_evidence.FormalDevelopmentOutcome, int]:
    launches = 0

    def transport(*_args: object, **_kwargs: object) -> bytes:
        nonlocal launches
        launches += 1
        return raw

    monkeypatch.setattr(run_evidence, "_supervisor_preflight", lambda _request: launch)
    monkeypatch.setattr(run_evidence, "_run_fixed_worker_transport", transport)
    if isinstance(after, BaseException):
        monkeypatch.setattr(
            run_evidence,
            "_repository_snapshot",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(after),
        )
    else:
        monkeypatch.setattr(
            run_evidence,
            "_repository_snapshot",
            lambda *_args, **_kwargs: launch.snapshot if after is None else after,
        )
    request = run_evidence.FormalDevelopmentRequest(
        repository_root=launch.repository_root,
        expected_freeze_head=launch.snapshot.head,
        search_receipt_path=Path("C:/repository/receipt.json"),
        evidence_index_path=Path("C:/repository/index.json"),
        authorization_path=Path("C:/external/authorization.json"),
        consumption_root=Path("C:/external/consumption"),
        archive_path=Path("C:/external/archive.zip"),
        private_container_path=Path("C:/external/private.json"),
    )
    return run_evidence.execute_authorized_formal_development(request), launches


@pytest.mark.parametrize("mutation", ("partial", "extra", "malformed", "noncanonical"))
def test_task_four_corrective_text_response_matrix_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    launch = _task_four_acceptance_fixture(tmp_path)
    canonical = worker_protocol.encode_formal_worker_response(_task_four_fail_response(launch))
    raw = {
        "partial": canonical[:-1],
        "extra": canonical + b"x",
        "malformed": b"{",
        "noncanonical": b" " + canonical,
    }[mutation]

    outcome, launches = _execute_task_four_fake_response(monkeypatch, launch, raw)

    assert launches == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_WORKER_PROCESS_UNKNOWN",),
    )
    assert outcome.fit_count is None
    assert outcome.private_identity is None
    assert outcome.seal_record_sha256 is None
    assert outcome.repository_inventory_sha256 is None


@pytest.mark.parametrize(
    "field",
    ("worker_request_sha256", "formal_worker_inventory_sha256", "launch_profile_sha256"),
)
def test_task_four_corrective_response_identity_mismatch_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    launch = _task_four_acceptance_fixture(tmp_path)
    response = _task_four_fail_response(launch).model_copy(update={field: "f" * 64})
    raw = worker_protocol.encode_formal_worker_response(response)

    outcome, launches = _execute_task_four_fake_response(monkeypatch, launch, raw)

    assert launches == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_WORKER_PROCESS_UNKNOWN",),
    )
    assert outcome.fit_count is None


def test_task_four_corrective_authorization_response_mismatch_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = _task_four_acceptance_fixture(tmp_path)
    response = _task_four_fail_response(launch).model_copy(
        update={
            "reason_codes": ("FORMAL_RUN_AUTHORIZATION_MISMATCH",),
            "authorization_sha256": "f" * 64,
        }
    )
    raw = worker_protocol.encode_formal_worker_response(response)

    outcome, launches = _execute_task_four_fake_response(monkeypatch, launch, raw)

    assert launches == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_WORKER_PROCESS_UNKNOWN",),
    )
    assert outcome.fit_count is None


def test_task_four_corrective_public_terminal_leaf_mismatch_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = _task_four_acceptance_fixture(tmp_path)
    response = worker_protocol.FormalWorkerResponse(
        schema_version="mdcp.formal-worker-response.v1",
        canonicalization_version="RFC8785",
        verdict="PASS",
        reason_codes=(),
        private_identity=worker_protocol.FormalWorkerPrivateIdentity(
            file_count=5,
            total_bytes=100,
            inventory_sha256="8" * 64,
            manifest_sha256="9" * 64,
        ),
        seal_record_sha256="a" * 64,
        repository_inventory_sha256=launch.snapshot.inventory_sha256,
        authorization_sha256=launch.request.authorization_sha256,
        consumption_marker_sha256="b" * 64,
        fit_count=80,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
        worker_request_sha256=launch.request_sha256,
        formal_worker_inventory_sha256=launch.request.formal_worker_inventory_sha256,
        launch_profile_sha256=launch.request.launch_profile_sha256,
    )
    raw = worker_protocol.encode_formal_worker_response(response)

    outcome, launches = _execute_task_four_fake_response(monkeypatch, launch, raw)

    assert launches == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_WORKER_PROCESS_UNKNOWN",),
    )
    assert outcome.fit_count is None
    assert outcome.private_identity is None
    assert outcome.seal_record_sha256 is None
    assert outcome.repository_inventory_sha256 is None


@pytest.mark.parametrize("drift", ("head", "clean_state", "inventory"))
def test_task_four_corrective_post_exit_git_drift_is_one_shot_and_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    launch = _task_four_acceptance_fixture(tmp_path)
    raw = worker_protocol.encode_formal_worker_response(_task_four_fail_response(launch))
    after: object
    if drift == "head":
        after = run_evidence._RepositorySnapshot(
            head="2" * 40,
            inventory_sha256=launch.snapshot.inventory_sha256,
        )
    elif drift == "inventory":
        after = run_evidence._RepositorySnapshot(
            head=launch.snapshot.head,
            inventory_sha256="f" * 64,
        )
    else:
        after = ValueError("dirty repository")

    outcome, launches = _execute_task_four_fake_response(
        monkeypatch,
        launch,
        raw,
        after=after,
    )

    assert launches == 1
    assert (outcome.verdict, outcome.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_WORKER_PROCESS_UNKNOWN",),
    )
    assert outcome.fit_count is None
    assert outcome.private_identity is None
    assert outcome.seal_record_sha256 is None
    assert outcome.repository_inventory_sha256 is None
