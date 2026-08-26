from __future__ import annotations

import ast
import base64
import copy
import ctypes
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

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
