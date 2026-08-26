from __future__ import annotations

import argparse
import ast
import base64
import copy
import inspect
import io
import json
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import mdcp.temporal.cli as cli
import mdcp.temporal.run_evidence as run_evidence
import mdcp.temporal.runner as runner
import mdcp.temporal.search_identity as search_identity
from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex
from mdcp.temporal.run_evidence import (
    FormalDevelopmentOutcome,
    FormalDevelopmentRequest,
    FormalDevelopmentSeal,
    FormalRunConsumptionMarker,
    PrivateBundleIdentity,
    PrivateFoldEvidence,
    PrivateRunBundle,
    PublicDevelopmentResult,
)

ZERO = "0" * 64
A = "a" * 64
B = "2" * 64
M = "b" * 64
R = "c" * 64
S = "d" * 64
INVENTORY = "e" * 64
P = "f" * 64
FREEZE = "1" * 40
ARCHIVE = "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"


@pytest.mark.parametrize(
    ("head", "remotes", "tags", "reason"),
    (
        ("2" * 40, "", "", "SEARCH_FREEZE_HEAD_MISMATCH"),
        (FREEZE, "origin", "", "SEARCH_FREEZE_REMOTE_INVALID"),
        (FREEZE, "", "v0.2.0", "SEARCH_FREEZE_HEAD_TAGGED"),
    ),
)
def test_freeze_preflight_rejects_repository_identity_before_evidence_reads(
    monkeypatch: pytest.MonkeyPatch,
    head: str,
    remotes: str,
    tags: str,
    reason: str,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(_root: Path, *arguments: str) -> str | None:
        calls.append(arguments)
        values = {
            ("rev-parse", "HEAD"): head,
            ("remote",): remotes,
            ("tag", "--points-at", "HEAD"): tags,
        }
        return values.get(arguments)

    monkeypatch.setattr(search_identity, "_is_clean_checkout", lambda _root: True)
    monkeypatch.setattr(search_identity, "_has_exact_search_source_head_modes", lambda *_args: True)
    monkeypatch.setattr(search_identity, "_git", fake_git)
    monkeypatch.setattr(
        search_identity,
        "_has_regular_public_evidence",
        lambda *_args: pytest.fail("evidence read reached after repository identity failure"),
    )

    result = search_identity.verify_search_freeze(
        Path("C:/repository"),
        Path("C:/repository/search-receipt.json"),
        Path("C:/repository/evidence-index.json"),
        expected_head=FREEZE,
    )

    assert (result.verdict, result.reason_codes) == ("FAIL", (reason,))
    assert calls[0] == ("rev-parse", "HEAD")


def public_result(
    *, evidence_class: str = "natural_development", status: str = "PASS"
) -> PublicDevelopmentResult:
    folds = tuple(
        {
            "fold_id": fold_id,
            "status": "PASS",
            "metrics": {
                "row_count": 100.0,
                "stable_mae": 1.0,
                "candidate_mae": 0.9,
                "point_ratio": 0.9,
                "ucb95": 0.95,
            },
            "reason_codes": (),
        }
        for fold_id in ("F1", "F2", "F3", "F4")
    )
    return PublicDevelopmentResult.model_validate(
        {
            "schema_version": "mdcp.development-result-index.v1",
            "canonicalization_version": "RFC8785",
            "evidence_class": evidence_class,
            "status": status,
            "h1_role": "OBSERVED_DEVELOPMENT_ONLY",
            "h2_state": "SEALED_NOT_LOADED",
            "h2_loaded_rows": 0,
            "selection_fit_count": 80,
            "result_sha256": A,
            "trials": tuple(
                {
                    "trial_id": f"TRIAL-{number:02d}",
                    "selection_fit_count": 4,
                    "folds": folds,
                }
                for number in range(1, 21)
            ),
        }
    )


def private_identity() -> PrivateBundleIdentity:
    return PrivateBundleIdentity(
        file_count=5,
        total_bytes=10,
        inventory_sha256=INVENTORY,
        manifest_sha256=P,
    )


def seal_document(
    *,
    selection_status: str = "PASS",
    development_status: str = "PASS",
    fit_count: int = 84,
) -> dict[str, object]:
    return {
        "schema_version": "mdcp.formal-development-seal.v1",
        "canonicalization_version": "RFC8785",
        "terminal_state": "SEALED",
        "authorization_sha256": A,
        "consumption_marker_sha256": M,
        "search_freeze_commit": FREEZE,
        "search_receipt_sha256": S,
        "source_inventory_sha256": INVENTORY,
        "protocol_sha256": P,
        "repository_inventory_sha256": R,
        "dataset_archive_sha256": ARCHIVE,
        "private_identity": private_identity().model_dump(mode="json"),
        "exit_observation_sha256": "2" * 64,
        "fit_count": fit_count,
        "selection_status": selection_status,
        "h1_role": "OBSERVED_DEVELOPMENT_ONLY",
        "h2_status": "SEALED_NOT_LOADED",
        "h2_loaded_rows": 0,
        "development_result": public_result(status=development_status).model_dump(mode="json"),
    }


def pass_outcome() -> FormalDevelopmentOutcome:
    return FormalDevelopmentOutcome(
        verdict="PASS",
        reason_codes=(),
        private_identity=private_identity(),
        seal_record_sha256=S,
        repository_inventory_sha256=R,
        authorization_sha256=A,
        consumption_marker_sha256=M,
        fit_count=84,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )


def test_authorization_model_matches_checked_in_closed_schema() -> None:
    checked = json.loads(
        Path("schemas/v2/formal-run-authorization.schema.json").read_text(encoding="utf-8")
    )
    assert search_identity.FormalRunAuthorization.model_json_schema() == checked
    value = search_identity.FormalRunAuthorization(
        schema_version="mdcp.formal-run-authorization.v1",
        canonicalization_version="RFC8785",
        search_freeze_commit=FREEZE,
        search_receipt_sha256=A,
        protocol_sha256=P,
        dataset_archive_sha256=ARCHIVE,
        authorization_id="12345678-1234-4234-8234-123456789abc",
        authorized_action="ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN",
        authorized_at_utc="2026-08-26T00:00:00Z",
        consumed=False,
    )
    assert value.consumed is False


@pytest.mark.parametrize(
    "field", ("search_freeze_commit", "search_receipt_sha256", "protocol_sha256")
)
def test_authorization_rejects_zero_identity(field: str) -> None:
    document = {
        "schema_version": "mdcp.formal-run-authorization.v1",
        "canonicalization_version": "RFC8785",
        "search_freeze_commit": FREEZE,
        "search_receipt_sha256": A,
        "protocol_sha256": P,
        "dataset_archive_sha256": ARCHIVE,
        "authorization_id": "12345678-1234-4234-8234-123456789abc",
        "authorized_action": "ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN",
        "authorized_at_utc": "2026-08-26T00:00:00Z",
        "consumed": False,
    }
    document[field] = "0" * (40 if field == "search_freeze_commit" else 64)
    with pytest.raises(ValueError, match="FORMAL_RUN_AUTHORIZATION_INVALID"):
        search_identity.FormalRunAuthorization.model_validate(document)


def test_outcome_matrix_is_closed() -> None:
    assert pass_outcome().fit_count == 84
    for fit_count in (0, 1, 79, 81, 83, 85, True):
        with pytest.raises(ValueError, match="FORMAL_DEVELOPMENT_OUTCOME_INVALID"):
            replace(pass_outcome(), fit_count=fit_count)
    for reason in (
        "FORMAL_RUN_REQUEST_INVALID",
        "SEARCH_FREEZE_INVALID",
        "FORMAL_RUN_AUTHORIZATION_INVALID",
        "FORMAL_RUN_REPOSITORY_INVALID",
        "PUBLICATION_UNSUPPORTED",
    ):
        result = FormalDevelopmentOutcome(
            verdict="FAIL",
            reason_codes=(reason,),
            private_identity=None,
            seal_record_sha256=None,
            repository_inventory_sha256=None,
            authorization_sha256=ZERO,
            consumption_marker_sha256=None,
            fit_count=0,
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
        )
        assert result.reason_codes == (reason,)
    with pytest.raises(ValueError, match="FORMAL_DEVELOPMENT_OUTCOME_INVALID"):
        replace(pass_outcome(), reason_codes=("FORMAL_RUN_SEAL_UNKNOWN",))


def test_terminal_schema_is_the_exact_checked_in_top_level() -> None:
    checked = json.loads(
        Path("schemas/v2/development-result-index.schema.json").read_text(encoding="utf-8")
    )
    assert FormalDevelopmentSeal.model_json_schema() == checked
    seal = FormalDevelopmentSeal(
        schema_version="mdcp.formal-development-seal.v1",
        canonicalization_version="RFC8785",
        terminal_state="SEALED",
        authorization_sha256=A,
        consumption_marker_sha256=M,
        search_freeze_commit=FREEZE,
        search_receipt_sha256=S,
        source_inventory_sha256=INVENTORY,
        protocol_sha256=P,
        repository_inventory_sha256=R,
        dataset_archive_sha256=ARCHIVE,
        private_identity=private_identity(),
        exit_observation_sha256="2" * 64,
        fit_count=84,
        selection_status="PASS",
        h1_role="OBSERVED_DEVELOPMENT_ONLY",
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
        development_result=public_result(),
    )
    assert seal.fit_count == 84
    with pytest.raises(ValueError, match="FORMAL_DEVELOPMENT_SEAL_INVALID"):
        seal.model_copy(
            update={"selection_status": "NO_ELIGIBLE_CANDIDATE"}, deep=True
        ).__class__.model_validate(
            {**seal.model_dump(mode="json"), "selection_status": "NO_ELIGIBLE_CANDIDATE"}
        )


@pytest.mark.parametrize(
    ("selection_status", "development_status", "fit_count"),
    (
        ("PASS", "PASS", 84),
        ("NO_ELIGIBLE_CANDIDATE", "FAIL", 80),
        ("UNKNOWN/NO_ELIGIBLE_CANDIDATE", "UNKNOWN", 80),
        ("UNKNOWN/NO_ELIGIBLE_CANDIDATE", "UNKNOWN", 84),
    ),
)
def test_terminal_seal_accepts_only_the_four_closed_operation_rows(
    selection_status: str, development_status: str, fit_count: int
) -> None:
    seal = FormalDevelopmentSeal.model_validate(
        seal_document(
            selection_status=selection_status,
            development_status=development_status,
            fit_count=fit_count,
        )
    )
    assert (seal.selection_status, seal.development_result.status, seal.fit_count) == (
        selection_status,
        development_status,
        fit_count,
    )


@pytest.mark.parametrize(
    ("selection_status", "development_status", "fit_count"),
    (
        ("PASS", "PASS", 80),
        ("PASS", "FAIL", 84),
        ("NO_ELIGIBLE_CANDIDATE", "FAIL", 84),
        ("NO_ELIGIBLE_CANDIDATE", "PASS", 80),
        ("UNKNOWN/NO_ELIGIBLE_CANDIDATE", "PASS", 80),
    ),
)
def test_terminal_seal_rejects_every_status_or_fit_mismatch(
    selection_status: str, development_status: str, fit_count: int
) -> None:
    with pytest.raises(ValueError, match="FORMAL_DEVELOPMENT_SEAL_INVALID"):
        FormalDevelopmentSeal.model_validate(
            seal_document(
                selection_status=selection_status,
                development_status=development_status,
                fit_count=fit_count,
            )
        )


@pytest.mark.parametrize(
    "field",
    (
        "authorization_sha256",
        "consumption_marker_sha256",
        "search_receipt_sha256",
        "source_inventory_sha256",
        "protocol_sha256",
        "repository_inventory_sha256",
        "exit_observation_sha256",
    ),
)
def test_terminal_seal_rejects_every_zero_top_level_identity(field: str) -> None:
    document = seal_document()
    document[field] = ZERO
    with pytest.raises(ValueError, match="FORMAL_DEVELOPMENT_SEAL_INVALID"):
        FormalDevelopmentSeal.model_validate(document)


@pytest.mark.parametrize("field", ("inventory_sha256", "manifest_sha256"))
def test_terminal_seal_rejects_zero_private_identity(field: str) -> None:
    document = seal_document()
    document["private_identity"][field] = ZERO
    with pytest.raises(ValueError, match="FORMAL_DEVELOPMENT_SEAL_INVALID"):
        FormalDevelopmentSeal.model_validate(document)


@pytest.mark.parametrize(
    "field", ("authorization_sha256", "search_receipt_sha256", "protocol_sha256")
)
def test_consumption_marker_rejects_zero_chain_identity(field: str) -> None:
    document = {
        "schema_version": "mdcp.formal-run-consumption.v1",
        "canonicalization_version": "RFC8785",
        "consumed": True,
        "authorization_sha256": A,
        "search_freeze_commit": FREEZE,
        "search_receipt_sha256": S,
        "protocol_sha256": P,
        "dataset_archive_sha256": ARCHIVE,
    }
    document[field] = ZERO
    with pytest.raises(ValueError, match="FORMAL_RUN_CONSUMPTION_INVALID"):
        FormalRunConsumptionMarker.model_validate(document)


def test_no_named_intermediate_formal_authority_or_raw_publisher_exists() -> None:
    forbidden = (
        "FormalRunPermit",
        "consume_formal_run_authorization",
        "claim_formal_run",
        "activate_formal_run",
        "write_formal_bundle_no_clobber",
        "canonical_natural_container",
        "publish_windows_container",
        "_publish_windows_container",
        "_authorize_natural_container_seal",
    )
    for module in (cli, run_evidence, runner, search_identity):
        for name in forbidden:
            assert not hasattr(module, name)
    assert not hasattr(runner, "run_formal_development")
    assert not hasattr(runner, "FormalDevelopmentInputs")
    assert not hasattr(run_evidence, "_make_evidence_mutation_surface")
    assert not hasattr(run_evidence, "_MUTATION_BINDINGS")


def test_formal_surface_is_one_operation_and_one_read_only_verifier() -> None:
    expected = {
        "FormalDevelopmentRequest",
        "FormalDevelopmentOutcome",
        "FormalDevelopmentSeal",
        "FormalRunConsumptionMarker",
        "FormalSealCheck",
        "execute_authorized_formal_development",
        "verify_formal_development_seal",
    }
    actual = {name for name in expected if hasattr(run_evidence, name)}
    assert actual == expected
    for function in (
        run_evidence.write_synthetic_bundle_no_clobber,
        run_evidence.execute_authorized_formal_development,
    ):
        closure = inspect.getclosurevars(function)
        assert not closure.unbound
        assert all(
            fragment not in name
            for name in closure.globals
            for fragment in ("publish_windows", "windows_write", "natural_container")
        )


def test_module_builder_rejects_natural_even_with_forged_override() -> None:
    natural = PrivateRunBundle(
        evidence_class="natural_development",
        files=(PrivateFoldEvidence(logical_path="one.json", canonical_bytes=b"{}"),),
    )
    with pytest.raises(ValueError, match="^FORMAL_RUN_SEAL_AUTHORITY_REQUIRED$"):
        run_evidence._canonical_private_container(natural)
    with pytest.raises(ValueError, match="^FORMAL_RUN_SEAL_AUTHORITY_REQUIRED$"):
        run_evidence._canonical_private_container(natural, object())


def test_non_nt_formal_operation_fails_before_path_access() -> None:
    source = Path(run_evidence.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_make_evidence_mutation_surface"
    )
    bindings = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "_MUTATION_BINDINGS"
    )
    module = ast.Module(body=[bindings, factory], type_ignores=[])
    namespace = dict(vars(run_evidence))
    namespace["os"] = SimpleNamespace(name="posix")
    exec(compile(ast.fix_missing_locations(module), "<isolated-factory>", "exec"), namespace)
    _, operation = namespace["_make_evidence_mutation_surface"]()
    request = FormalDevelopmentRequest(
        repository_root=Path("C:/sentinel"),
        expected_freeze_head=FREEZE,
        search_receipt_path=Path("C:/sentinel/receipt"),
        evidence_index_path=Path("C:/sentinel/index"),
        authorization_path=Path("C:/sentinel/auth"),
        consumption_root=Path("C:/sentinel/consume"),
        archive_path=Path("C:/sentinel/archive"),
        private_container_path=Path("C:/sentinel/private"),
    )
    result = operation(request)
    assert (result.verdict, result.reason_codes) == (
        "FAIL",
        ("PUBLICATION_UNSUPPORTED",),
    )


def test_final_cli_has_exact_command_and_callable_surface() -> None:
    parser = cli.build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    assert tuple(subparsers.choices) == (
        "run-development",
        "verify-search-freeze",
        "prepare-search-freeze",
        "verify-search-source",
        "verify-development-result",
    )
    callables = tuple(
        sorted(
            name
            for name, value in vars(cli).items()
            if inspect.isfunction(value) and value.__module__ == cli.__name__
        )
    )
    assert callables == ("_emit_check", "build_parser", "main")


def test_formal_operation_closes_terminal_guard_sequence_on_every_exception() -> None:
    source_path = Path(run_evidence.__file__)
    tree = ast.parse(source_path.read_bytes(), filename=str(source_path))
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_make_evidence_mutation_surface"
    )
    operation = next(
        node
        for node in factory.body
        if isinstance(node, ast.FunctionDef) and node.name == "formal_operation"
    )
    helper_names = {node.name for node in operation.body if isinstance(node, ast.FunctionDef)}
    assert {
        "_attempt_pre_seal",
        "_attempt_exit",
        "_finish_terminal_guards",
    } <= helper_names
    exception_handlers = [
        node for node in ast.walk(operation) if isinstance(node, ast.ExceptHandler)
    ]
    finish_calls = [
        node
        for handler in exception_handlers
        for node in ast.walk(handler)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_finish_terminal_guards"
    ]
    assert len(finish_calls) == 1


def _isolated_formal_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    failure_phase: str,
    private_container_path: Path,
) -> tuple[FormalDevelopmentOutcome, dict[str, object]]:
    source_path = Path(run_evidence.__file__)
    tree = ast.parse(source_path.read_bytes(), filename=str(source_path))
    factory = copy.deepcopy(
        next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_make_evidence_mutation_surface"
        )
    )
    bindings = copy.deepcopy(
        next(
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "_MUTATION_BINDINGS"
        )
    )
    overrides = {
        "_read_bounded_regular": "return test_raw_by_name.get(path.name)",
        "_retained_destination": "return test_retained_destination(destination)",
        "_windows_nt_relative_file": ("return test_nt_relative_file(parent_handle, name)"),
        "_windows_file_information": "return test_file_information(handle)",
        "_windows_normalized_handle_name": "return 'trusted'",
        "_windows_names_equal": "return True",
        "_windows_write_all": "return None",
        "_windows_flush": "return None",
        "_revalidate_retained_ancestors": "return None",
        "_revalidate_final_handle": "return None",
        "_marker_leaf_state": "return test_marker_leaf_state()",
        "_windows_close": "return test_close(handle)",
        "_build_formal_execution_plan": "return test_plan",
        "_run_development_core": (
            "test_calls['loader'] += 1\ntest_calls['fit'] += 1\nreturn test_run_result"
        ),
        "formalize": "return test_files, test_public_result, 'PASS'",
        "encode_natural": "return b'private', test_private_identity",
        "_checkpoint": "return None",
    }
    for function_name, body_source in overrides.items():
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
    returns[0].value.elts.append(ast.Name("formal_operation", ast.Load()))
    returns[0].value.elts.append(ast.Name("attempt_states", ast.Load()))
    returns[0].value.elts.append(ast.Name("consume_marker", ast.Load()))

    repository = tmp_path / "repository"
    repository.mkdir(exist_ok=True)
    consumption_root = tmp_path / "consumption"
    consumption_root.mkdir(exist_ok=True)
    private_container_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_raw = (
        source_path.parents[3] / "evidence/public/v02/search/search-receipt.json"
    ).read_bytes()
    receipt = search_identity.SearchReceipt.model_validate(parse_json_bytes(receipt_raw))
    authorization_raw = canonicalize_json(
        search_identity.FormalRunAuthorization(
            schema_version="mdcp.formal-run-authorization.v1",
            canonicalization_version="RFC8785",
            search_freeze_commit=FREEZE,
            search_receipt_sha256=sha256_hex(receipt_raw),
            protocol_sha256=receipt.dataset_contract_sha256,
            dataset_archive_sha256=receipt.dataset_archive_sha256,
            authorization_id="12345678-1234-4234-8234-123456789abc",
            authorized_action="ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN",
            authorized_at_utc="2026-08-27T00:00:00Z",
            consumed=False,
        ).model_dump(mode="json")
    )
    calls: dict[str, object] = {
        "preflight": 0,
        "marker": 0,
        "loader": 0,
        "fit": 0,
        "nt": 0,
        "closes": [],
        "reentrant": [],
    }
    operation_holder: dict[str, object] = {}
    reentered = False
    private_destination = SimpleNamespace(
        absolute_path=private_container_path,
        leaf_name=private_container_path.name,
        ancestors=(SimpleNamespace(handle=301, volume_serial_number=1, file_index=1),),
        parent_handle=301,
        created=False,
        closed=False,
    )
    terminal_path = private_container_path.with_name(f"{private_container_path.name}.public.json")
    terminal_destination = SimpleNamespace(
        absolute_path=terminal_path,
        leaf_name=terminal_path.name,
        ancestors=(SimpleNamespace(handle=302, volume_serial_number=1, file_index=2),),
        parent_handle=302,
        created=False,
        closed=False,
    )
    marker_destination = SimpleNamespace(
        absolute_path=consumption_root / "marker.json",
        leaf_name="marker.json",
        ancestors=(SimpleNamespace(handle=303, volume_serial_number=1, file_index=3),),
        parent_handle=303,
        created=False,
        closed=False,
    )

    def test_retained_destination(path: Path) -> object:
        nonlocal reentered
        if path.name.endswith(".consumed.json"):
            calls["marker"] += 1
            marker_destination.absolute_path = path
            marker_destination.leaf_name = path.name
            return marker_destination
        calls["preflight"] += 1
        if failure_phase == "preflight_reentry" and not reentered:
            reentered = True
            calls["reentrant"].append(operation_holder["operation"](operation_holder["request"]))
        if path.name.endswith(".public.json"):
            if failure_phase == "preflight":
                raise RuntimeError("synthetic retained-terminal failure")
            return terminal_destination
        return private_destination

    def test_nt_relative_file(_parent_handle: int, _leaf_name: str) -> tuple[object, ...]:
        calls["nt"] += 1
        number = calls["nt"]
        if failure_phase in ("precall_pair", "precall_clean"):
            return False, None, None, None, None
        handle = {1: 201, 2: 202, 3: 203}[number]
        if failure_phase == "marker_owned" and number == 1:
            return True, 259, 0, 0, handle
        return True, 0, 0, 2, handle

    def test_file_information(_handle: int) -> tuple[int, tuple[int, int, int]]:
        return 0, (1, 2, 3)

    def test_marker_leaf_state() -> str:
        return "ABSENT" if failure_phase in ("precall_pair", "precall_clean") else "PRESENT"

    failing_handle = {
        "preflight": 301,
        "marker_owned": 201,
        "precall_pair": 302,
        "private_publish": 202,
        "terminal_publish": 203,
    }.get(failure_phase)

    def test_close(handle: int) -> bool:
        calls["closes"].append(handle)
        return handle != failing_handle

    test_public_result = public_result()
    identity = private_identity()
    namespace = dict(vars(run_evidence))
    namespace.update(
        {
            "__name__": f"_mdcp_formal_operation_{id(tmp_path)}",
            "test_calls": calls,
            "test_failure_phase": failure_phase,
            "test_raw_by_name": {
                "receipt.json": receipt_raw,
                "index.json": b"{}",
                "authorization.json": authorization_raw,
            },
            "test_retained_destination": test_retained_destination,
            "test_nt_relative_file": test_nt_relative_file,
            "test_file_information": test_file_information,
            "test_marker_leaf_state": test_marker_leaf_state,
            "test_close": test_close,
            "test_plan": object(),
            "test_run_result": SimpleNamespace(fit_ledger=SimpleNamespace(total_count=84)),
            "test_files": (),
            "test_public_result": test_public_result,
            "test_private_identity": identity,
        }
    )
    module = ast.fix_missing_locations(ast.Module(body=[bindings, factory], type_ignores=[]))
    isolated = ModuleType(namespace["__name__"])
    isolated.__dict__.update(namespace)
    monkeypatch.setitem(sys.modules, namespace["__name__"], isolated)
    exec(compile(module, str(source_path), "exec"), isolated.__dict__)
    values = isolated.__dict__["_make_evidence_mutation_surface"]()
    operation = values[2]
    attempt_states = values[3]
    consume_marker = values[4]

    monkeypatch.chdir(repository)
    monkeypatch.setattr(
        search_identity,
        "verify_search_freeze",
        lambda *_args, **_kwargs: SimpleNamespace(verdict="PASS"),
    )

    class PassingGuard:
        @staticmethod
        def checkpoint(_stage: object) -> SimpleNamespace:
            return SimpleNamespace(
                verdict="PASS",
                reason_codes=(),
                repository_inventory_sha256=R,
                elapsed_ns=1,
                peak_process_bytes=1,
            )

    monkeypatch.setattr(
        "mdcp.temporal.runtime_guards.build_production_runtime_guard",
        lambda *_args, **_kwargs: PassingGuard(),
    )
    request = FormalDevelopmentRequest(
        repository_root=repository,
        expected_freeze_head=FREEZE,
        search_receipt_path=repository / "receipt.json",
        evidence_index_path=repository / "index.json",
        authorization_path=repository / "authorization.json",
        consumption_root=consumption_root,
        archive_path=repository / "archive.zip",
        private_container_path=private_container_path,
    )
    operation_holder.update({"operation": operation, "request": request})
    outcome = operation(request)
    authorization_sha256 = sha256_hex(authorization_raw)
    calls["attempt_state"] = attempt_states.get(authorization_sha256)
    if failure_phase in {
        "preflight",
        "marker_owned",
        "precall_pair",
        "precall_clean",
        "private_publish",
        "terminal_publish",
    }:
        calls["retry_result"] = consume_marker(
            consumption_root,
            authorization_sha256,
            b"canonical-marker",
        ).result
    return outcome, calls


def test_ignored_repository_destination_fails_before_marker_and_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    private = repository / "runtime" / "formal.json"
    outcome, calls = _isolated_formal_operation(
        tmp_path,
        monkeypatch,
        failure_phase="none",
        private_container_path=private,
    )

    assert (outcome.verdict, outcome.reason_codes) == (
        "FAIL",
        ("FORMAL_RUN_DESTINATION_INVALID",),
    )
    assert calls["preflight"] == calls["marker"] == calls["loader"] == calls["fit"] == 0


def test_same_digest_reentry_is_blocked_during_output_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private = tmp_path / "external" / "formal.json"
    outcome, calls = _isolated_formal_operation(
        tmp_path,
        monkeypatch,
        failure_phase="preflight_reentry",
        private_container_path=private,
    )

    assert outcome.verdict == "PASS"
    assert len(calls["reentrant"]) == 1
    reentrant = calls["reentrant"][0]
    assert (reentrant.verdict, reentrant.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_RUN_CONSUMPTION_UNKNOWN",),
    )
    assert (calls["preflight"], calls["marker"], calls["loader"], calls["fit"]) == (
        2,
        1,
        1,
        1,
    )


@pytest.mark.parametrize(
    ("phase", "expected"),
    (
        ("preflight", ("FAIL", "FORMAL_RUN_DESTINATION_INVALID")),
        ("marker_owned", ("UNKNOWN", "FORMAL_RUN_CONSUMPTION_UNKNOWN")),
        ("precall_pair", ("UNKNOWN", "FORMAL_RUN_CONSUMPTION_UNKNOWN")),
        ("precall_clean", ("FAIL", "FORMAL_RUN_CONSUMPTION_FAILED")),
        ("private_publish", ("UNKNOWN", "FORMAL_RUN_EXECUTION_UNKNOWN")),
        ("terminal_publish", ("UNKNOWN", "FORMAL_RUN_SEAL_UNKNOWN")),
    ),
)
def test_each_checked_close_failure_is_consumed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    expected: tuple[str, str],
) -> None:
    private = tmp_path / "external" / "formal.json"
    outcome, calls = _isolated_formal_operation(
        tmp_path,
        monkeypatch,
        failure_phase=phase,
        private_container_path=private,
    )

    assert (outcome.verdict, outcome.reason_codes[0]) == expected
    expected_closes = {
        "preflight": [301],
        "marker_owned": [201, 303, 302, 301],
        "precall_pair": [303, 302, 301],
        "precall_clean": [303, 302, 301],
        "private_publish": [201, 303, 202, 302, 301],
        "terminal_publish": [201, 303, 202, 203, 302, 301],
    }
    assert calls["closes"] == expected_closes[phase]
    expected_states = {
        "preflight": "UNKNOWN",
        "marker_owned": "UNKNOWN",
        "precall_pair": "UNKNOWN",
        "precall_clean": None,
        "private_publish": "CONSUMED",
        "terminal_publish": "CONSUMED",
    }
    assert calls["attempt_state"] == expected_states[phase]
    expected_retries = {
        "preflight": "INDETERMINATE",
        "marker_owned": "INDETERMINATE",
        "precall_pair": "INDETERMINATE",
        "precall_clean": "PRECALL_FAILED",
        "private_publish": "COLLISION",
        "terminal_publish": "COLLISION",
    }
    assert calls["retry_result"] == expected_retries[phase]
    expected_attempt_counts = {
        "preflight": (0, 0),
        "marker_owned": (1, 1),
        "precall_pair": (1, 1),
        "precall_clean": (2, 2),
        "private_publish": (1, 2),
        "terminal_publish": (1, 3),
    }
    assert (calls["marker"], calls["nt"]) == expected_attempt_counts[phase]


def _cli_arguments() -> tuple[str, ...]:
    return (
        "run-development",
        "--expected-freeze-head",
        FREEZE,
        "--search-receipt",
        "receipt.json",
        "--evidence-index",
        "index.json",
        "--authorization-env",
        "MDCP_FORMAL_RUN_AUTHORIZATION",
        "--consumption-root-env",
        "MDCP_FORMAL_RUN_CONSUMPTION_ROOT",
        "--archive-env",
        "MDCP_UCI_ARCHIVE",
        "--private-container-env",
        "MDCP_V02_PRIVATE_CONTAINER",
    )


def _prepare_cli(monkeypatch: pytest.MonkeyPatch) -> io.BytesIO:
    for name in (
        "MDCP_FORMAL_RUN_AUTHORIZATION",
        "MDCP_FORMAL_RUN_CONSUMPTION_ROOT",
        "MDCP_UCI_ARCHIVE",
        "MDCP_V02_PRIVATE_CONTAINER",
    ):
        monkeypatch.setenv(name, f"C:/{name}")
    output = io.BytesIO()
    monkeypatch.setattr(cli.sys, "stdout", SimpleNamespace(buffer=output))
    return output


def test_cli_pass_emits_one_exact_custody_line(monkeypatch: pytest.MonkeyPatch) -> None:
    output = _prepare_cli(monkeypatch)
    monkeypatch.setattr(
        run_evidence,
        "execute_authorized_formal_development",
        lambda request: pass_outcome(),
    )
    assert cli.main(_cli_arguments()) == 0
    assert (
        output.getvalue()
        == canonicalize_json(
            {
                "repository_inventory_sha256": R,
                "schema_version": "mdcp.formal-seal-custody.v1",
                "seal_record_sha256": S,
            }
        )
        + b"\n"
    )


@pytest.mark.parametrize(
    ("outcome", "exit_code", "reason"),
    (
        (
            FormalDevelopmentOutcome(
                verdict="FAIL",
                reason_codes=("FORMAL_RUN_REQUEST_INVALID",),
                private_identity=None,
                seal_record_sha256=None,
                repository_inventory_sha256=None,
                authorization_sha256=ZERO,
                consumption_marker_sha256=None,
                fit_count=0,
                h2_status="SEALED_NOT_LOADED",
                h2_loaded_rows=0,
            ),
            2,
            "FORMAL_RUN_REQUEST_INVALID",
        ),
        (
            FormalDevelopmentOutcome(
                verdict="UNKNOWN",
                reason_codes=("FORMAL_RUN_EXECUTION_UNKNOWN",),
                private_identity=None,
                seal_record_sha256=None,
                repository_inventory_sha256=None,
                authorization_sha256=A,
                consumption_marker_sha256=M,
                fit_count=0,
                h2_status="SEALED_NOT_LOADED",
                h2_loaded_rows=0,
            ),
            3,
            "FORMAL_RUN_EXECUTION_UNKNOWN",
        ),
    ),
)
def test_cli_fail_and_unknown_are_one_closed_line(
    monkeypatch: pytest.MonkeyPatch,
    outcome: FormalDevelopmentOutcome,
    exit_code: int,
    reason: str,
) -> None:
    output = _prepare_cli(monkeypatch)
    monkeypatch.setattr(
        run_evidence,
        "execute_authorized_formal_development",
        lambda request: outcome,
    )
    assert cli.main(_cli_arguments()) == exit_code
    assert (
        output.getvalue()
        == canonicalize_json(
            {
                "reason_code": reason,
                "schema_version": "mdcp.formal-run-cli-result.v1",
                "verdict": outcome.verdict,
            }
        )
        + b"\n"
    )


def test_cli_parser_rejection_has_no_argparse_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    output = _prepare_cli(monkeypatch)
    assert cli.main(()) == 2
    assert b"usage:" not in output.getvalue().lower()
    assert output.getvalue().count(b"\n") == 1


def test_cli_output_write_failure_uses_exit_four(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailedBuffer:
        def write(self, value: bytes) -> int:
            del value
            raise OSError("closed")

        def flush(self) -> None:
            raise AssertionError("flush must not follow a failed write")

    _prepare_cli(monkeypatch)
    monkeypatch.setattr(cli.sys, "stdout", SimpleNamespace(buffer=FailedBuffer()))
    monkeypatch.setattr(
        run_evidence,
        "execute_authorized_formal_development",
        lambda request: pass_outcome(),
    )
    assert cli.main(_cli_arguments()) == 4


def test_mutating_cli_commands_have_no_digest_injection_flags() -> None:
    parser = cli.build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    options_by_command = {
        name: {
            option
            for action in command._actions
            for option in action.option_strings
            if "sha256" in option or "digest" in option
        }
        for name, command in subparsers.choices.items()
    }
    assert options_by_command == {
        "run-development": set(),
        "verify-search-freeze": set(),
        "prepare-search-freeze": set(),
        "verify-search-source": {"--expected-index-sha256"},
        "verify-development-result": {
            "--expected-authorization-sha256",
            "--expected-repository-inventory-sha256",
            "--expected-seal-record-sha256",
            "--expected-search-receipt-sha256",
            "--expected-source-inventory-sha256",
        },
    }


def _recover(marker: Path, private: Path, terminal: Path) -> run_evidence.FormalSealCheck:
    return run_evidence.verify_formal_development_seal(
        marker,
        private,
        terminal,
        expected_authorization_sha256=A,
        expected_search_receipt_sha256=S,
        expected_source_inventory_sha256=INVENTORY,
        expected_repository_inventory_sha256=R,
        expected_seal_record_sha256=ZERO,
    )


def test_recovery_precedence_for_absent_partial_and_malformed_chain(tmp_path: Path) -> None:
    marker = (tmp_path / "marker").absolute()
    private = (tmp_path / "private").absolute()
    terminal = (tmp_path / "terminal").absolute()

    absent = _recover(marker, private, terminal)
    assert (absent.verdict, absent.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_ABSENT",),
    )

    private.write_bytes(b"private-artifact")
    marker_missing = _recover(marker, private, terminal)
    assert (marker_missing.verdict, marker_missing.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )
    private.unlink()

    marker.write_bytes(b"not-json")
    malformed = _recover(marker, private, terminal)
    assert (malformed.verdict, malformed.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_SEAL_CONSUMPTION_UNKNOWN",),
    )

    valid_marker = FormalRunConsumptionMarker(
        schema_version="mdcp.formal-run-consumption.v1",
        canonicalization_version="RFC8785",
        consumed=True,
        authorization_sha256=A,
        search_freeze_commit=FREEZE,
        search_receipt_sha256=S,
        protocol_sha256=P,
        dataset_archive_sha256=ARCHIVE,
    )
    marker.write_bytes(canonicalize_json(valid_marker.model_dump(mode="json")))
    incomplete = _recover(marker, private, terminal)
    assert (incomplete.verdict, incomplete.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_SEAL_INCOMPLETE",),
    )
    for result in (absent, marker_missing, malformed, incomplete):
        assert (
            result.private_identity,
            result.seal_record_sha256,
            result.repository_inventory_sha256,
            result.fit_count,
        ) == (None, None, None, 0)


def _natural_chain_public_result() -> PublicDevelopmentResult:
    document = public_result().model_dump(mode="json")
    for trial in document["trials"][2:]:
        for fold in trial["folds"]:
            fold["status"] = "FAIL"
            fold["reason_codes"] = ["QUALITY_THRESHOLD_EXCEEDED"]
    return PublicDevelopmentResult.model_validate(document)


def _fixture_fold_digest(
    document: dict[str, object],
    stable_document: dict[str, object],
    *,
    replay: bool,
) -> dict[str, object]:
    from mdcp.temporal.runner import EXACT_TRIAL_IDS
    from mdcp.temporal.trials import canonical_trial_identity

    trial_label = document["trial_id"]
    canonical_trial_id = EXACT_TRIAL_IDS[int(trial_label[-2:]) - 1]
    receipt_material = {
        "trial_id": canonical_trial_id,
        "fold_id": document["fold_id"],
        "contract_verdict": document["contract_verdict"],
        "inventory": document["inventory"],
        "adapters": document["adapters"],
        "stable_predictions": stable_document["predictions"],
        "candidate_predictions": document["predictions"],
        "labels": document["labels"],
        "declared_digests": {
            field: document[field]
            for field in (
                "preprocessing_state_sha256",
                "feature_vector_sha256",
                "prediction_vector_sha256",
                "metric_sha256",
                "receipt_sha256",
            )
        },
    }
    digest = {
        "fold_id": document["fold_id"],
        "configuration_sha256": canonical_trial_identity(canonical_trial_id).configuration_sha256,
        "preprocessing_state_sha256": document["preprocessing_state_sha256"],
        "feature_vector_sha256": document["feature_vector_sha256"],
        "prediction_vector_sha256": document["prediction_vector_sha256"],
        "metric_sha256": document["metric_sha256"],
        "receipt_sha256": sha256_hex(canonicalize_json(receipt_material)),
    }
    if replay:
        digest["verdict"] = document["contract_verdict"]
    return digest


def _set_false_declared_digests(document: dict[str, object]) -> None:
    from mdcp.temporal.runner import EXACT_TRIAL_IDS

    trial_label = document["trial_id"]
    document["prediction_vector_sha256"] = B
    document["metric_sha256"] = M
    declared = {
        "trial_id": EXACT_TRIAL_IDS[int(trial_label[-2:]) - 1],
        "fold_id": document["fold_id"],
        "preprocessing_state_sha256": document["preprocessing_state_sha256"],
        "feature_vector_sha256": document["feature_vector_sha256"],
        "prediction_vector_sha256": document["prediction_vector_sha256"],
        "metric_sha256": document["metric_sha256"],
    }
    document["receipt_sha256"] = sha256_hex(canonicalize_json(declared))


def _refresh_declared_digests(document: dict[str, object]) -> None:
    from mdcp.temporal.runner import EXACT_TRIAL_IDS

    trial_label = document["trial_id"]
    prediction_values = tuple(float(item["value"]) for item in document["predictions"])
    label_values = tuple(float(item["value"]) for item in document["labels"])
    document["prediction_vector_sha256"] = sha256_hex(canonicalize_json(prediction_values))
    document["metric_sha256"] = sha256_hex(
        canonicalize_json({"labels": label_values, "predictions": prediction_values})
    )
    declared = {
        "trial_id": EXACT_TRIAL_IDS[int(trial_label[-2:]) - 1],
        "fold_id": document["fold_id"],
        "preprocessing_state_sha256": document["preprocessing_state_sha256"],
        "feature_vector_sha256": document["feature_vector_sha256"],
        "prediction_vector_sha256": document["prediction_vector_sha256"],
        "metric_sha256": document["metric_sha256"],
    }
    document["receipt_sha256"] = sha256_hex(canonicalize_json(declared))


def _set_false_source_identity_digest(document: dict[str, object]) -> None:
    document["inventory"][0]["identity_sha256"] = B
    for collection in ("adapters", "predictions", "labels"):
        document[collection][0]["identity"]["identity_sha256"] = B


def _refresh_selected_chain(documents: dict[str, dict[str, object]]) -> None:
    summary = documents["trial-summary.json"]
    selection_by_identity = {
        (document["trial_id"], document["fold_id"]): document
        for document in summary["selection_folds"]
    }
    stable_by_fold = {
        fold_id: selection_by_identity[("TRIAL-01", fold_id)]
        for fold_id in ("F1", "F2", "F3", "F4")
    }
    qualification = documents["qualification-report.json"]
    selected = qualification["qualifications"][0]
    selected["fold_digests"] = [
        _fixture_fold_digest(
            selection_by_identity[("TRIAL-02", fold_id)],
            stable_by_fold[fold_id],
            replay=False,
        )
        for fold_id in ("F1", "F2", "F3", "F4")
    ]
    qualification_sha256 = sha256_hex(canonicalize_json(qualification["qualifications"]))
    qualification["qualification_inventory_sha256"] = qualification_sha256
    winners = documents["provisional-winner.json"]
    for winner_name in ("provisional_winner", "final_winner"):
        winner = winners[winner_name]
        if winner is not None:
            winner["fold_digests"] = selected["fold_digests"]
            winner["qualification_inventory_sha256"] = qualification_sha256
    documents["ranking-report.json"]["qualification_inventory_sha256"] = qualification_sha256
    replay = documents["replay-report.json"]
    replay["replay_digests"] = [
        _fixture_fold_digest(document, stable_by_fold[document["fold_id"]], replay=True)
        for document in replay["replay_folds"]
    ]


def _set_no_winner_chain(
    documents: dict[str, dict[str, object]],
    *,
    qualification_unknown: bool,
) -> None:
    qualification = documents["qualification-report.json"]
    selected = qualification["qualifications"][0]
    selected["verdict"] = "UNKNOWN" if qualification_unknown else "FAIL"
    selected["qualified"] = False
    selected["reason_codes"] = [
        "EVIDENCE_UNKNOWN" if qualification_unknown else "QUALITY_THRESHOLD_EXCEEDED"
    ]
    qualification_sha256 = sha256_hex(canonicalize_json(qualification["qualifications"]))
    qualification["qualification_inventory_sha256"] = qualification_sha256
    public_folds = documents["trial-summary.json"]["public_trials"][1]["folds"]
    for fold in public_folds:
        fold["status"] = selected["verdict"]
        if qualification_unknown:
            fold["metrics"] = dict.fromkeys(
                ("row_count", "stable_mae", "candidate_mae", "point_ratio", "ucb95")
            )
            fold["reason_codes"] = ["METRICS_UNAVAILABLE"]
        else:
            fold["reason_codes"] = ["QUALITY_THRESHOLD_EXCEEDED"]
    documents["provisional-winner.json"]["provisional_winner"] = None
    documents["provisional-winner.json"]["final_winner"] = None
    status = "UNKNOWN/NO_ELIGIBLE_CANDIDATE" if qualification_unknown else "NO_ELIGIBLE_CANDIDATE"
    reason = "QUALIFICATION_UNKNOWN" if qualification_unknown else "NO_QUALIFIED_TRIAL"
    ranking = documents["ranking-report.json"]
    ranking["selection_status"] = status
    ranking["reason_codes"] = [reason]
    ranking["qualification_inventory_sha256"] = qualification_sha256
    ranking["provisional_ranking_key"] = None
    replay = documents["replay-report.json"]
    replay["selection_status"] = status
    replay["reason_codes"] = [reason]
    replay["replay_trial_id"] = None
    replay["replay_folds"] = []
    replay["replay_digests"] = []


def _write_natural_container(path: Path) -> PrivateBundleIdentity:
    from mdcp.temporal.runner import EXACT_TRIAL_IDS
    from mdcp.temporal.trials import canonical_trial_identity

    label_to_trial = {
        f"TRIAL-{index:02d}": trial_id for index, trial_id in enumerate(EXACT_TRIAL_IDS, start=1)
    }

    def fold_document(trial_id: str, fold_id: str, phase: str) -> dict[str, object]:
        identity_material = {
            "fold_id": fold_id,
            "request_id": f"{trial_id}-{fold_id}",
            "local_timestamp": "2011-01-01T00:00:00-05:00",
            "source_position": 1,
        }
        identity = {
            **identity_material,
            "identity_sha256": sha256_hex(canonicalize_json(identity_material)),
        }
        value = {
            "identity": identity,
            "succeeded": True,
            "value": 1.0,
            "reason_code": None,
        }
        preprocessing_sha256 = sha256_hex(f"{trial_id}:{fold_id}:preprocessing".encode())
        feature_sha256 = sha256_hex(f"{trial_id}:{fold_id}:features".encode())
        prediction_sha256 = sha256_hex(canonicalize_json((1.0,)))
        metric_sha256 = sha256_hex(canonicalize_json({"labels": (1.0,), "predictions": (1.0,)}))
        declared = {
            "trial_id": label_to_trial[trial_id],
            "fold_id": fold_id,
            "preprocessing_state_sha256": preprocessing_sha256,
            "feature_vector_sha256": feature_sha256,
            "prediction_vector_sha256": prediction_sha256,
            "metric_sha256": metric_sha256,
        }
        return {
            "phase": phase,
            "trial_id": trial_id,
            "fold_id": fold_id,
            "contract_verdict": "PASS",
            "inventory": [identity],
            "adapters": [
                {
                    "identity": identity,
                    "succeeded": True,
                    "calendar_day": "2011-01-01",
                    "groups": ["ALL"],
                    "reason_code": None,
                }
            ],
            "predictions": [value],
            "labels": [value],
            "preprocessing_state_sha256": preprocessing_sha256,
            "feature_vector_sha256": feature_sha256,
            "prediction_vector_sha256": prediction_sha256,
            "metric_sha256": metric_sha256,
            "receipt_sha256": sha256_hex(canonicalize_json(declared)),
        }

    def fold_digest(
        document: dict[str, object],
        stable_document: dict[str, object],
        *,
        replay: bool,
    ) -> dict[str, object]:
        return _fixture_fold_digest(document, stable_document, replay=replay)

    common = {
        "canonicalization_version": "RFC8785",
        "evidence_class": "natural_development",
    }
    selection_folds = [
        fold_document(f"TRIAL-{trial:02d}", fold_id, "SELECTION")
        for trial in range(1, 21)
        for fold_id in ("F1", "F2", "F3", "F4")
    ]
    selection_by_identity = {
        (document["trial_id"], document["fold_id"]): document for document in selection_folds
    }
    stable_by_fold = {
        fold_id: selection_by_identity[("TRIAL-01", fold_id)]
        for fold_id in ("F1", "F2", "F3", "F4")
    }
    qualifications = [
        {
            "trial_id": (trial_label := f"TRIAL-{trial:02d}"),
            "family_id": canonical_trial_identity(label_to_trial[trial_label]).family_id,
            "configuration_sha256": canonical_trial_identity(
                label_to_trial[trial_label]
            ).configuration_sha256,
            "report_sha256": sha256_hex(f"{trial_label}:report".encode()),
            "verdict": "PASS" if trial == 2 else "FAIL",
            "qualified": trial == 2,
            "reason_codes": [] if trial == 2 else ["QUALITY_THRESHOLD_EXCEEDED"],
            "pooled_ucb95": 0.9,
            "worst_fold_point": 0.9,
            "worst_subgroup_ucb95": 0.9,
            "fold_digests": [
                fold_digest(
                    selection_by_identity[(trial_label, fold_id)],
                    stable_by_fold[fold_id],
                    replay=False,
                )
                for fold_id in ("F1", "F2", "F3", "F4")
            ],
        }
        for trial in range(2, 21)
    ]
    qualification_sha256 = sha256_hex(canonicalize_json(qualifications))
    selected = qualifications[0]
    winner = {
        "trial_id": "TRIAL-02",
        "family_id": selected["family_id"],
        "configuration_sha256": selected["configuration_sha256"],
        "report_sha256": selected["report_sha256"],
        "pooled_ucb95": 0.9,
        "worst_fold_point": 0.9,
        "worst_subgroup_ucb95": 0.9,
        "ranking_key": [0.9, 0.9, 0.9, 1, "TRIAL-02"],
        "fold_digests": selected["fold_digests"],
        "qualification_inventory_sha256": qualification_sha256,
    }
    replay_folds = [
        fold_document("TRIAL-02", fold_id, "REPLAY") for fold_id in ("F1", "F2", "F3", "F4")
    ]
    documents = {
        "provisional-winner.json": {
            "schema_version": "mdcp.natural-provisional-winner.v1",
            **common,
            "provisional_winner": winner,
            "final_winner": winner,
        },
        "qualification-report.json": {
            "schema_version": "mdcp.natural-qualification-report.v1",
            **common,
            "qualification_inventory_sha256": qualification_sha256,
            "qualifications": qualifications,
        },
        "ranking-report.json": {
            "schema_version": "mdcp.natural-ranking-report.v1",
            **common,
            "selection_status": "PASS",
            "reason_codes": [],
            "retry_allowed": False,
            "qualification_inventory_sha256": qualification_sha256,
            "provisional_ranking_key": winner["ranking_key"],
        },
        "replay-report.json": {
            "schema_version": "mdcp.natural-replay-report.v1",
            **common,
            "selection_status": "PASS",
            "reason_codes": [],
            "replay_trial_id": "TRIAL-02",
            "replay_folds": replay_folds,
            "replay_digests": [
                fold_digest(document, stable_by_fold[document["fold_id"]], replay=True)
                for document in replay_folds
            ],
        },
        "trial-summary.json": {
            "schema_version": "mdcp.natural-trial-summary.v1",
            **common,
            "selection_fit_count": 80,
            "selection_folds": selection_folds,
            "public_trials": _natural_chain_public_result().model_dump(mode="json")["trials"],
        },
    }
    entries = []
    for logical_path in sorted(documents):
        payload = canonicalize_json(documents[logical_path])
        entries.append(
            {
                "logical_path": logical_path,
                "byte_size": len(payload),
                "sha256": sha256_hex(payload),
                "payload_base64": base64.b64encode(payload).decode("ascii"),
            }
        )
    inventory = [
        {key: item[key] for key in ("logical_path", "byte_size", "sha256")} for item in entries
    ]
    inventory_sha256 = sha256_hex(canonicalize_json(inventory))
    manifest = {
        "schema_version": "mdcp.private-evidence-container.v1",
        "canonicalization_version": "RFC8785",
        "evidence_class": "natural_development",
        "file_count": 5,
        "total_bytes": sum(item["byte_size"] for item in entries),
        "inventory_sha256": inventory_sha256,
    }
    manifest_sha256 = sha256_hex(canonicalize_json(manifest))
    path.write_bytes(
        canonicalize_json({**manifest, "entries": entries, "manifest_sha256": manifest_sha256})
    )
    return PrivateBundleIdentity(
        file_count=5,
        total_bytes=manifest["total_bytes"],
        inventory_sha256=inventory_sha256,
        manifest_sha256=manifest_sha256,
    )


def _write_valid_recovery_chain(
    tmp_path: Path,
) -> tuple[Path, Path, Path, FormalDevelopmentSeal, bytes]:
    marker_path = (tmp_path / "marker.json").absolute()
    private_path = (tmp_path / "private.json").absolute()
    terminal_path = (tmp_path / "private.json.public.json").absolute()
    marker = FormalRunConsumptionMarker(
        schema_version="mdcp.formal-run-consumption.v1",
        canonicalization_version="RFC8785",
        consumed=True,
        authorization_sha256=A,
        search_freeze_commit=FREEZE,
        search_receipt_sha256=S,
        protocol_sha256=P,
        dataset_archive_sha256=ARCHIVE,
    )
    marker_raw = canonicalize_json(marker.model_dump(mode="json"))
    marker_path.write_bytes(marker_raw)
    identity = _write_natural_container(private_path)
    exit_sha256 = sha256_hex(
        canonicalize_json(
            {
                "elapsed_within_budget": True,
                "max_elapsed_ns": 21_600_000_000_000,
                "max_peak_process_bytes": 4_294_967_296,
                "memory_within_budget": True,
                "reason_codes": [],
                "repository_inventory_sha256": R,
                "schema_version": "mdcp.formal-exit-observation.v1",
                "search_freeze_commit": FREEZE,
                "stage": "EXIT",
                "verdict": "PASS",
            }
        )
    )
    seal = FormalDevelopmentSeal(
        schema_version="mdcp.formal-development-seal.v1",
        canonicalization_version="RFC8785",
        terminal_state="SEALED",
        authorization_sha256=A,
        consumption_marker_sha256=sha256_hex(marker_raw),
        search_freeze_commit=FREEZE,
        search_receipt_sha256=S,
        source_inventory_sha256=INVENTORY,
        protocol_sha256=P,
        repository_inventory_sha256=R,
        dataset_archive_sha256=ARCHIVE,
        private_identity=identity,
        exit_observation_sha256=exit_sha256,
        fit_count=84,
        selection_status="PASS",
        h1_role="OBSERVED_DEVELOPMENT_ONLY",
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
        development_result=_natural_chain_public_result(),
    )
    terminal_raw = canonicalize_json(seal.model_dump(mode="json"))
    terminal_path.write_bytes(terminal_raw)
    return marker_path, private_path, terminal_path, seal, terminal_raw


def _rewrite_natural_container(
    path: Path,
    mutation: Callable[[dict[str, dict[str, object]]], None],
) -> tuple[PrivateBundleIdentity, dict[str, dict[str, object]]]:
    container = parse_json_bytes(path.read_bytes())
    documents = {
        entry["logical_path"]: parse_json_bytes(base64.b64decode(entry["payload_base64"]))
        for entry in container["entries"]
    }
    mutation(documents)
    entries = []
    for logical_path in sorted(documents):
        payload = canonicalize_json(documents[logical_path])
        entries.append(
            {
                "logical_path": logical_path,
                "byte_size": len(payload),
                "sha256": sha256_hex(payload),
                "payload_base64": base64.b64encode(payload).decode("ascii"),
            }
        )
    inventory = [
        {key: entry[key] for key in ("logical_path", "byte_size", "sha256")} for entry in entries
    ]
    container["entries"] = entries
    container["total_bytes"] = sum(entry["byte_size"] for entry in entries)
    container["inventory_sha256"] = sha256_hex(canonicalize_json(inventory))
    manifest = {
        key: container[key]
        for key in (
            "schema_version",
            "canonicalization_version",
            "evidence_class",
            "file_count",
            "total_bytes",
            "inventory_sha256",
        )
    }
    container["manifest_sha256"] = sha256_hex(canonicalize_json(manifest))
    path.write_bytes(canonicalize_json(container))
    return (
        PrivateBundleIdentity(
            file_count=container["file_count"],
            total_bytes=container["total_bytes"],
            inventory_sha256=container["inventory_sha256"],
            manifest_sha256=container["manifest_sha256"],
        ),
        documents,
    )


def _reseal_rewritten_chain(
    terminal_path: Path,
    seal: FormalDevelopmentSeal,
    identity: PrivateBundleIdentity,
    documents: dict[str, dict[str, object]],
    *,
    selection_status: str | None = None,
    fit_count: int | None = None,
    development_status: str | None = None,
) -> bytes:
    seal_document = seal.model_dump(mode="json")
    seal_document["private_identity"] = identity.model_dump(mode="json")
    development_result = seal_document["development_result"]
    development_result["trials"] = documents["trial-summary.json"]["public_trials"]
    if selection_status is not None:
        seal_document["selection_status"] = selection_status
    if fit_count is not None:
        seal_document["fit_count"] = fit_count
    if development_status is not None:
        development_result["status"] = development_status
    rewritten = FormalDevelopmentSeal.model_validate(seal_document)
    raw = canonicalize_json(rewritten.model_dump(mode="json"))
    terminal_path.write_bytes(raw)
    return raw


def _anchored_recovery(
    marker_path: Path,
    private_path: Path,
    terminal_path: Path,
    terminal_sha256: str,
):
    return run_evidence.verify_formal_development_seal(
        marker_path,
        private_path,
        terminal_path,
        expected_authorization_sha256=A,
        expected_search_receipt_sha256=S,
        expected_source_inventory_sha256=INVENTORY,
        expected_repository_inventory_sha256=R,
        expected_seal_record_sha256=terminal_sha256,
    )


def test_recovery_requires_external_terminal_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker_path, private_path, terminal_path, _seal, terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )
    original_reader = run_evidence._read_private_container_once
    reads: list[Path] = []

    def counting_reader(path: Path) -> bytes:
        reads.append(path)
        return original_reader(path)

    monkeypatch.setattr(run_evidence, "_read_private_container_once", counting_reader)
    check = run_evidence.verify_formal_development_seal(
        marker_path,
        private_path,
        terminal_path,
        expected_authorization_sha256=A,
        expected_search_receipt_sha256=S,
        expected_source_inventory_sha256=INVENTORY,
        expected_repository_inventory_sha256=R,
        expected_seal_record_sha256=ZERO,
    )
    assert (check.verdict, check.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_SEAL_UNANCHORED",),
    )
    assert reads == [marker_path, private_path, terminal_path]
    anchored = _anchored_recovery(
        marker_path,
        private_path,
        terminal_path,
        sha256_hex(terminal_raw),
    )
    assert anchored.verdict == "PASS"
    trust_mismatch = run_evidence.verify_formal_development_seal(
        marker_path,
        private_path,
        terminal_path,
        expected_authorization_sha256=A,
        expected_search_receipt_sha256=S,
        expected_source_inventory_sha256=INVENTORY,
        expected_repository_inventory_sha256="3" * 64,
        expected_seal_record_sha256=sha256_hex(terminal_raw),
    )
    assert (trust_mismatch.verdict, trust_mismatch.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_TRUST_MISMATCH",),
    )


def test_coordinated_terminal_mutation_fails_against_unchanged_external_anchor(
    tmp_path: Path,
) -> None:
    marker_path, private_path, terminal_path, seal, terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )
    changed = seal.model_dump(mode="json")
    changed["development_result"]["result_sha256"] = B
    assert seal.development_result.result_sha256 != B
    terminal_path.write_bytes(
        canonicalize_json(FormalDevelopmentSeal.model_validate(changed).model_dump(mode="json"))
    )

    check = _anchored_recovery(
        marker_path,
        private_path,
        terminal_path,
        sha256_hex(terminal_raw),
    )

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_TRUST_MISMATCH",),
    )


def test_recovery_rejects_winner_not_equal_to_selected_qualification(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        winners = documents["provisional-winner.json"]
        winners["provisional_winner"]["configuration_sha256"] = B
        winners["final_winner"]["configuration_sha256"] = B

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)

    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))
    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_rejects_replay_document_digest_divergence(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        documents["replay-report.json"]["replay_folds"][0]["prediction_vector_sha256"] = B

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)

    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))
    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_coordinated_five_file_rehash_still_requires_one_semantic_chain(
    tmp_path: Path,
) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        selection = next(
            document
            for document in documents["trial-summary.json"]["selection_folds"]
            if (document["trial_id"], document["fold_id"]) == ("TRIAL-02", "F1")
        )
        replay = documents["replay-report.json"]["replay_folds"][0]
        _set_false_declared_digests(selection)
        _set_false_declared_digests(replay)
        _refresh_selected_chain(documents)

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)

    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))
    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_rejects_qualified_trial_with_failed_selection_contract(
    tmp_path: Path,
) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        selection = next(
            document
            for document in documents["trial-summary.json"]["selection_folds"]
            if (document["trial_id"], document["fold_id"]) == ("TRIAL-02", "F1")
        )
        selection["contract_verdict"] = "UNKNOWN"
        documents["replay-report.json"]["replay_folds"][0]["contract_verdict"] = "UNKNOWN"
        _refresh_selected_chain(documents)
        documents["provisional-winner.json"]["final_winner"] = None
        for name in ("ranking-report.json", "replay-report.json"):
            documents[name]["selection_status"] = "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
            documents[name]["reason_codes"] = ["REPLAY_UNKNOWN"]

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(
        terminal_path,
        seal,
        identity,
        documents,
        selection_status="UNKNOWN/NO_ELIGIBLE_CANDIDATE",
        fit_count=84,
        development_status="UNKNOWN",
    )
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_rejects_canonical_raw_trial_tie_break_mismatch(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        qualification = documents["qualification-report.json"]
        trial_three = qualification["qualifications"][1]
        trial_three["verdict"] = "PASS"
        trial_three["qualified"] = True
        trial_three["reason_codes"] = []
        for fold in documents["trial-summary.json"]["public_trials"][2]["folds"]:
            fold["status"] = "PASS"
            fold["reason_codes"] = []
        _refresh_selected_chain(documents)

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_classifies_deterministic_private_container_mismatch_as_invalid(
    tmp_path: Path,
) -> None:
    marker_path, private_path, terminal_path, _seal, terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )
    container = parse_json_bytes(private_path.read_bytes())
    container["entries"][0]["sha256"] = B
    private_path.write_bytes(canonicalize_json(container))

    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))
    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_keeps_malformed_private_bytes_incomplete(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, _seal, terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )
    private_path.write_bytes(b"{")

    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))
    assert (check.verdict, check.reason_codes) == (
        "UNKNOWN",
        ("FORMAL_SEAL_INCOMPLETE",),
    )


def test_recovery_rejects_coordinated_false_source_identity_digest(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        selection = next(
            document
            for document in documents["trial-summary.json"]["selection_folds"]
            if (document["trial_id"], document["fold_id"]) == ("TRIAL-02", "F1")
        )
        replay = documents["replay-report.json"]["replay_folds"][0]
        _set_false_source_identity_digest(selection)
        _set_false_source_identity_digest(replay)
        _refresh_selected_chain(documents)

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_rejects_false_stable_control_inner_digests(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        stable = documents["trial-summary.json"]["selection_folds"][0]
        _set_false_declared_digests(stable)

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_rejects_nonqualified_fail_with_unknown_selection_contract(
    tmp_path: Path,
) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        selection = next(
            document
            for document in documents["trial-summary.json"]["selection_folds"]
            if (document["trial_id"], document["fold_id"]) == ("TRIAL-02", "F1")
        )
        selection["contract_verdict"] = "UNKNOWN"
        _refresh_selected_chain(documents)
        _set_no_winner_chain(documents, qualification_unknown=False)

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(
        terminal_path,
        seal,
        identity,
        documents,
        selection_status="NO_ELIGIBLE_CANDIDATE",
        fit_count=80,
        development_status="FAIL",
    )
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_rejects_qualification_metric_that_contradicts_trial_summary(
    tmp_path: Path,
) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        for fold in documents["trial-summary.json"]["public_trials"][1]["folds"]:
            fold["metrics"]["point_ratio"] = 999.0

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_rejects_selection_document_qualification_digest_divergence(
    tmp_path: Path,
) -> None:
    from mdcp.temporal.runner import EXACT_TRIAL_IDS

    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        selection = next(
            document
            for document in documents["trial-summary.json"]["selection_folds"]
            if (document["trial_id"], document["fold_id"]) == ("TRIAL-02", "F1")
        )
        selection["predictions"][0]["value"] = 2.0
        selection["prediction_vector_sha256"] = sha256_hex(canonicalize_json((2.0,)))
        selection["metric_sha256"] = sha256_hex(
            canonicalize_json({"labels": (1.0,), "predictions": (2.0,)})
        )
        declared = {
            "trial_id": EXACT_TRIAL_IDS[1],
            "fold_id": "F1",
            "preprocessing_state_sha256": selection["preprocessing_state_sha256"],
            "feature_vector_sha256": selection["feature_vector_sha256"],
            "prediction_vector_sha256": selection["prediction_vector_sha256"],
            "metric_sha256": selection["metric_sha256"],
        }
        selection["receipt_sha256"] = sha256_hex(canonicalize_json(declared))

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "selection_order",
        "selection_cardinality",
        "qualification_order",
        "qualification_cardinality",
        "qualification_family",
        "qualification_configuration",
        "qualification_fold_order",
        "qualification_fold_missing",
        "qualification_fold_extra",
        "qualification_fold_duplicate",
        "ranking_key",
        "ranking_reason",
        "replay_reason",
        "replay_fold_cardinality",
        "replay_fold_extra",
        "replay_fold_duplicate",
        "replay_digest_cardinality",
        "replay_digest_extra",
        "replay_digest_duplicate",
        "replay_order",
        "replay_trial_id",
        "final_winner",
    ),
)
def test_recovery_rejects_semantic_inventory_and_terminal_mutations(
    tmp_path: Path,
    mutation: str,
) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate_chain(documents: dict[str, dict[str, object]]) -> None:
        if mutation == "selection_order":
            folds = documents["trial-summary.json"]["selection_folds"]
            folds[0], folds[1] = folds[1], folds[0]
        elif mutation == "selection_cardinality":
            documents["trial-summary.json"]["selection_folds"].pop()
        elif mutation == "qualification_order":
            qualifications = documents["qualification-report.json"]["qualifications"]
            qualifications[0], qualifications[1] = qualifications[1], qualifications[0]
            qualification_sha256 = sha256_hex(canonicalize_json(qualifications))
            documents["qualification-report.json"]["qualification_inventory_sha256"] = (
                qualification_sha256
            )
            documents["ranking-report.json"]["qualification_inventory_sha256"] = (
                qualification_sha256
            )
            for name in ("provisional_winner", "final_winner"):
                documents["provisional-winner.json"][name]["qualification_inventory_sha256"] = (
                    qualification_sha256
                )
        elif mutation == "qualification_cardinality":
            qualification = documents["qualification-report.json"]
            qualification["qualifications"].pop()
            qualification_sha256 = sha256_hex(canonicalize_json(qualification["qualifications"]))
            qualification["qualification_inventory_sha256"] = qualification_sha256
            documents["ranking-report.json"]["qualification_inventory_sha256"] = (
                qualification_sha256
            )
            for name in ("provisional_winner", "final_winner"):
                documents["provisional-winner.json"][name]["qualification_inventory_sha256"] = (
                    qualification_sha256
                )
        elif mutation in {"qualification_family", "qualification_configuration"}:
            qualification = documents["qualification-report.json"]
            selected = qualification["qualifications"][0]
            winners = documents["provisional-winner.json"]
            if mutation == "qualification_family":
                selected["family_id"] = "STAT"
                for name in ("provisional_winner", "final_winner"):
                    winners[name]["family_id"] = "STAT"
                    winners[name]["ranking_key"][3] = 0
                documents["ranking-report.json"]["provisional_ranking_key"][3] = 0
            else:
                selected["configuration_sha256"] = B
                for name in ("provisional_winner", "final_winner"):
                    winners[name]["configuration_sha256"] = B
            qualification_sha256 = sha256_hex(canonicalize_json(qualification["qualifications"]))
            qualification["qualification_inventory_sha256"] = qualification_sha256
            documents["ranking-report.json"]["qualification_inventory_sha256"] = (
                qualification_sha256
            )
            for name in ("provisional_winner", "final_winner"):
                winners[name]["qualification_inventory_sha256"] = qualification_sha256
        elif mutation.startswith("qualification_fold_"):
            qualification = documents["qualification-report.json"]
            fold_digests = qualification["qualifications"][0]["fold_digests"]
            if mutation == "qualification_fold_order":
                fold_digests[0], fold_digests[1] = fold_digests[1], fold_digests[0]
            elif mutation == "qualification_fold_missing":
                fold_digests.pop()
            elif mutation == "qualification_fold_extra":
                fold_digests.append(copy.deepcopy(fold_digests[-1]))
            elif mutation == "qualification_fold_duplicate":
                fold_digests[1] = copy.deepcopy(fold_digests[0])
            else:
                raise AssertionError("unknown qualification fold mutation")
            qualification_sha256 = sha256_hex(canonicalize_json(qualification["qualifications"]))
            qualification["qualification_inventory_sha256"] = qualification_sha256
            documents["ranking-report.json"]["qualification_inventory_sha256"] = (
                qualification_sha256
            )
            for name in ("provisional_winner", "final_winner"):
                winner = documents["provisional-winner.json"][name]
                winner["fold_digests"] = fold_digests
                winner["qualification_inventory_sha256"] = qualification_sha256
        elif mutation == "ranking_key":
            documents["ranking-report.json"]["provisional_ranking_key"][-1] = "TRIAL-03"
        elif mutation == "ranking_reason":
            documents["ranking-report.json"]["reason_codes"] = ["NO_QUALIFIED_TRIAL"]
        elif mutation == "replay_reason":
            documents["replay-report.json"]["reason_codes"] = ["REPLAY_UNKNOWN"]
        elif mutation == "replay_fold_cardinality":
            documents["replay-report.json"]["replay_folds"].pop()
            documents["replay-report.json"]["replay_digests"].pop()
        elif mutation == "replay_fold_extra":
            replay = documents["replay-report.json"]
            replay["replay_folds"].append(copy.deepcopy(replay["replay_folds"][-1]))
        elif mutation == "replay_fold_duplicate":
            replay = documents["replay-report.json"]
            replay["replay_folds"][1] = copy.deepcopy(replay["replay_folds"][0])
        elif mutation == "replay_digest_cardinality":
            documents["replay-report.json"]["replay_digests"].pop()
        elif mutation == "replay_digest_extra":
            replay = documents["replay-report.json"]
            replay["replay_digests"].append(copy.deepcopy(replay["replay_digests"][-1]))
        elif mutation == "replay_digest_duplicate":
            replay = documents["replay-report.json"]
            replay["replay_digests"][1] = copy.deepcopy(replay["replay_digests"][0])
        elif mutation == "replay_order":
            replay = documents["replay-report.json"]
            replay["replay_folds"][0], replay["replay_folds"][1] = (
                replay["replay_folds"][1],
                replay["replay_folds"][0],
            )
            replay["replay_digests"][0], replay["replay_digests"][1] = (
                replay["replay_digests"][1],
                replay["replay_digests"][0],
            )
        elif mutation == "replay_trial_id":
            documents["replay-report.json"]["replay_trial_id"] = "TRIAL-03"
        elif mutation == "final_winner":
            documents["provisional-winner.json"]["final_winner"] = None
        else:
            raise AssertionError("unknown test mutation")

    identity, documents = _rewrite_natural_container(private_path, mutate_chain)
    terminal_raw = _reseal_rewritten_chain(terminal_path, seal, identity, documents)
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_accepts_closed_no_eligible_chain_with_eighty_fits(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        qualification = documents["qualification-report.json"]
        selected = qualification["qualifications"][0]
        selected["verdict"] = "FAIL"
        selected["qualified"] = False
        selected["reason_codes"] = ["QUALITY_THRESHOLD_EXCEEDED"]
        qualification_sha256 = sha256_hex(canonicalize_json(qualification["qualifications"]))
        qualification["qualification_inventory_sha256"] = qualification_sha256
        for fold in documents["trial-summary.json"]["public_trials"][1]["folds"]:
            fold["status"] = "FAIL"
            fold["reason_codes"] = ["QUALITY_THRESHOLD_EXCEEDED"]
        documents["provisional-winner.json"]["provisional_winner"] = None
        documents["provisional-winner.json"]["final_winner"] = None
        ranking = documents["ranking-report.json"]
        ranking["selection_status"] = "NO_ELIGIBLE_CANDIDATE"
        ranking["reason_codes"] = ["NO_QUALIFIED_TRIAL"]
        ranking["qualification_inventory_sha256"] = qualification_sha256
        ranking["provisional_ranking_key"] = None
        replay = documents["replay-report.json"]
        replay["selection_status"] = "NO_ELIGIBLE_CANDIDATE"
        replay["reason_codes"] = ["NO_QUALIFIED_TRIAL"]
        replay["replay_trial_id"] = None
        replay["replay_folds"] = []
        replay["replay_digests"] = []

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(
        terminal_path,
        seal,
        identity,
        documents,
        selection_status="NO_ELIGIBLE_CANDIDATE",
        fit_count=80,
        development_status="FAIL",
    )
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes, check.fit_count) == ("PASS", (), 80)


@pytest.mark.parametrize("mutation", ("missing", "extra", "duplicate"))
def test_recovery_rejects_non_exact_natural_five_file_inventory(
    tmp_path: Path,
    mutation: str,
) -> None:
    marker_path, private_path, terminal_path, seal, original_terminal_raw = (
        _write_valid_recovery_chain(tmp_path)
    )
    if mutation in {"missing", "extra"}:

        def mutate_documents(documents: dict[str, dict[str, object]]) -> None:
            if mutation == "missing":
                documents.pop("replay-report.json")
            else:
                documents["unexpected.json"] = copy.deepcopy(documents["ranking-report.json"])

        identity, documents = _rewrite_natural_container(private_path, mutate_documents)
    else:
        identity, documents = _rewrite_natural_container(private_path, lambda _: None)
        container = parse_json_bytes(private_path.read_bytes())
        container["entries"].append(copy.deepcopy(container["entries"][0]))
        container["entries"].sort(key=lambda item: item["logical_path"].encode("ascii"))
        container["file_count"] = len(container["entries"])
        container["total_bytes"] = sum(item["byte_size"] for item in container["entries"])
        inventory = [
            {key: item[key] for key in ("logical_path", "byte_size", "sha256")}
            for item in container["entries"]
        ]
        container["inventory_sha256"] = sha256_hex(canonicalize_json(inventory))
        manifest = {
            key: container[key]
            for key in (
                "schema_version",
                "canonicalization_version",
                "evidence_class",
                "file_count",
                "total_bytes",
                "inventory_sha256",
            )
        }
        container["manifest_sha256"] = sha256_hex(canonicalize_json(manifest))
        private_path.write_bytes(canonicalize_json(container))
        identity = PrivateBundleIdentity(
            file_count=container["file_count"],
            total_bytes=container["total_bytes"],
            inventory_sha256=container["inventory_sha256"],
            manifest_sha256=container["manifest_sha256"],
        )
    terminal_raw = (
        original_terminal_raw
        if mutation == "duplicate"
        else _reseal_rewritten_chain(terminal_path, seal, identity, documents)
    )
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes) == (
        "FAIL",
        ("FORMAL_SEAL_CHAIN_INVALID",),
    )


def test_recovery_accepts_closed_qualification_unknown_chain(tmp_path: Path) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        _set_no_winner_chain(documents, qualification_unknown=True)

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(
        terminal_path,
        seal,
        identity,
        documents,
        selection_status="UNKNOWN/NO_ELIGIBLE_CANDIDATE",
        fit_count=80,
        development_status="UNKNOWN",
    )
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes, check.fit_count) == ("PASS", (), 80)


@pytest.mark.parametrize("reason_code", ("REPLAY_UNKNOWN", "REPLAY_DIGEST_MISMATCH"))
def test_recovery_accepts_closed_replay_unknown_chains(
    tmp_path: Path,
    reason_code: str,
) -> None:
    marker_path, private_path, terminal_path, seal, _terminal_raw = _write_valid_recovery_chain(
        tmp_path
    )

    def mutate(documents: dict[str, dict[str, object]]) -> None:
        replay = documents["replay-report.json"]
        if reason_code == "REPLAY_UNKNOWN":
            replay["replay_folds"][0]["contract_verdict"] = "UNKNOWN"
        else:
            replay["replay_folds"][0]["predictions"][0]["value"] = 2.0
            _refresh_declared_digests(replay["replay_folds"][0])
        _refresh_selected_chain(documents)
        documents["provisional-winner.json"]["final_winner"] = None
        for name in ("ranking-report.json", "replay-report.json"):
            documents[name]["selection_status"] = "UNKNOWN/NO_ELIGIBLE_CANDIDATE"
            documents[name]["reason_codes"] = [reason_code]

    identity, documents = _rewrite_natural_container(private_path, mutate)
    terminal_raw = _reseal_rewritten_chain(
        terminal_path,
        seal,
        identity,
        documents,
        selection_status="UNKNOWN/NO_ELIGIBLE_CANDIDATE",
        fit_count=84,
        development_status="UNKNOWN",
    )
    check = _anchored_recovery(marker_path, private_path, terminal_path, sha256_hex(terminal_raw))

    assert (check.verdict, check.reason_codes, check.fit_count) == ("PASS", (), 84)
