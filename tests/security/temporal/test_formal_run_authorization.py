from __future__ import annotations

import argparse
import ast
import inspect
import io
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

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


def _write_natural_container(path: Path) -> PrivateBundleIdentity:
    import base64

    def fold_document(trial_id: str, fold_id: str, phase: str) -> dict[str, object]:
        identity = {
            "fold_id": fold_id,
            "request_id": f"{trial_id}-{fold_id}-{phase}",
            "local_timestamp": "2011-01-01T00:00:00-05:00",
            "source_position": 1,
            "identity_sha256": sha256_hex(
                canonicalize_json({"trial_id": trial_id, "fold_id": fold_id, "phase": phase})
            ),
        }
        value = {
            "identity": identity,
            "succeeded": True,
            "value": 1.0,
            "reason_code": None,
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
            "preprocessing_state_sha256": A,
            "feature_vector_sha256": M,
            "prediction_vector_sha256": R,
            "metric_sha256": S,
            "receipt_sha256": INVENTORY,
        }

    def fold_digest(fold_id: str, *, replay: bool) -> dict[str, object]:
        digest = {
            "fold_id": fold_id,
            "configuration_sha256": A,
            "preprocessing_state_sha256": M,
            "feature_vector_sha256": R,
            "prediction_vector_sha256": S,
            "metric_sha256": INVENTORY,
            "receipt_sha256": P,
        }
        if replay:
            digest["verdict"] = "PASS"
        return digest

    common = {
        "canonicalization_version": "RFC8785",
        "evidence_class": "natural_development",
    }
    selection_folds = [
        fold_document(f"TRIAL-{trial:02d}", fold_id, "SELECTION")
        for trial in range(1, 21)
        for fold_id in ("F1", "F2", "F3", "F4")
    ]
    qualifications = [
        {
            "trial_id": f"TRIAL-{trial:02d}",
            "family_id": f"family-{trial:02d}",
            "configuration_sha256": A,
            "report_sha256": M,
            "verdict": "PASS" if trial == 2 else "FAIL",
            "qualified": trial == 2,
            "reason_codes": [] if trial == 2 else ["QUALITY_THRESHOLD_EXCEEDED"],
            "pooled_ucb95": 0.9,
            "worst_fold_point": 0.9,
            "worst_subgroup_ucb95": 0.9,
            "fold_digests": [
                fold_digest(fold_id, replay=False) for fold_id in ("F1", "F2", "F3", "F4")
            ],
        }
        for trial in range(2, 21)
    ]
    qualification_sha256 = sha256_hex(canonicalize_json(qualifications))
    winner = {
        "trial_id": "TRIAL-02",
        "family_id": "family-02",
        "configuration_sha256": A,
        "report_sha256": M,
        "pooled_ucb95": 0.9,
        "worst_fold_point": 0.9,
        "worst_subgroup_ucb95": 0.9,
        "ranking_key": [0.9, 0.9, 0.9, 0, "TRIAL-02"],
        "fold_digests": [
            fold_digest(fold_id, replay=False) for fold_id in ("F1", "F2", "F3", "F4")
        ],
        "qualification_inventory_sha256": qualification_sha256,
    }
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
            "replay_folds": [
                fold_document("TRIAL-02", fold_id, "REPLAY") for fold_id in ("F1", "F2", "F3", "F4")
            ],
            "replay_digests": [
                fold_digest(fold_id, replay=True) for fold_id in ("F1", "F2", "F3", "F4")
            ],
        },
        "trial-summary.json": {
            "schema_version": "mdcp.natural-trial-summary.v1",
            **common,
            "selection_fit_count": 80,
            "selection_folds": selection_folds,
            "public_trials": public_result().model_dump(mode="json")["trials"],
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


def test_recovery_requires_external_terminal_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
        development_result=public_result(),
    )
    terminal_raw = canonicalize_json(seal.model_dump(mode="json"))
    terminal_path.write_bytes(terminal_raw)
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
    anchored = run_evidence.verify_formal_development_seal(
        marker_path,
        private_path,
        terminal_path,
        expected_authorization_sha256=A,
        expected_search_receipt_sha256=S,
        expected_source_inventory_sha256=INVENTORY,
        expected_repository_inventory_sha256=R,
        expected_seal_record_sha256=sha256_hex(terminal_raw),
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

    import base64

    container = parse_json_bytes(private_path.read_bytes())
    summary_entry = next(
        item for item in container["entries"] if item["logical_path"] == "trial-summary.json"
    )
    summary = parse_json_bytes(base64.b64decode(summary_entry["payload_base64"]))
    summary["selection_folds"][0]["trial_id"] = "TRIAL-20"
    payload = canonicalize_json(summary)
    summary_entry["payload_base64"] = base64.b64encode(payload).decode("ascii")
    summary_entry["byte_size"] = len(payload)
    summary_entry["sha256"] = sha256_hex(payload)
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
    coordinated_identity = PrivateBundleIdentity(
        file_count=container["file_count"],
        total_bytes=container["total_bytes"],
        inventory_sha256=container["inventory_sha256"],
        manifest_sha256=container["manifest_sha256"],
    )
    coordinated_seal = FormalDevelopmentSeal.model_validate(
        {**seal.model_dump(mode="json"), "private_identity": coordinated_identity.model_dump()}
    )
    coordinated_terminal = canonicalize_json(coordinated_seal.model_dump(mode="json"))
    terminal_path.write_bytes(coordinated_terminal)
    coordinated = run_evidence.verify_formal_development_seal(
        marker_path,
        private_path,
        terminal_path,
        expected_authorization_sha256=A,
        expected_search_receipt_sha256=S,
        expected_source_inventory_sha256=INVENTORY,
        expected_repository_inventory_sha256=R,
        expected_seal_record_sha256=sha256_hex(coordinated_terminal),
    )
    assert (coordinated.verdict, coordinated.private_identity, coordinated.fit_count) == (
        "UNKNOWN",
        None,
        0,
    )
