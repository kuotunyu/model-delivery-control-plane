from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

import mdcp.temporal.formal_worker_protocol as protocol
import mdcp.temporal.run_evidence as run_evidence
from mdcp.common.digests import sha256_hex

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _task_five_wrong_digest_request(tmp_path: Path) -> tuple[protocol.FormalWorkerRequest, Path]:
    receipt_document = json.loads(
        (REPOSITORY_ROOT / "evidence/public/v02/search/search-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    receipt_document["search_source_commit"] = "2" * 40
    receipt_document["created_at_utc"] = (
        datetime(2026, 8, 28, tzinfo=UTC).isoformat().replace("+00:00", "Z")
    )
    receipt = protocol.SearchReceipt.model_validate(receipt_document)
    receipt_raw = protocol.canonicalize_json(receipt.model_dump(mode="json"))
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(receipt_raw)

    source_entries = tuple(
        protocol.SearchSourceEntry(
            logical_path=logical_path,
            git_mode="100644",
            byte_size=len(raw := (REPOSITORY_ROOT / logical_path).read_bytes()),
            sha256=sha256_hex(raw),
        )
        for logical_path in protocol.SEARCH_SOURCE_PATHS
    )
    index = protocol.SearchEvidenceIndex(
        schema_version="mdcp.search-evidence-index.v1",
        canonicalization_version="RFC8785",
        source_entries=source_entries,
        source_inventory_sha256=protocol.search_source_inventory_sha256(source_entries),
        private_logical_outputs=protocol.PRIVATE_LOGICAL_OUTPUTS,
        search_receipt_sha256=sha256_hex(receipt_raw),
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )
    index_raw = protocol.canonicalize_json(index.model_dump(mode="json"))
    index_path = tmp_path / "index.json"
    index_path.write_bytes(index_raw)

    authorization = protocol.FormalRunAuthorization(
        schema_version="mdcp.formal-run-authorization.v1",
        canonicalization_version="RFC8785",
        search_freeze_commit="1" * 40,
        search_receipt_sha256=sha256_hex(receipt_raw),
        protocol_sha256=receipt.dataset_contract_sha256,
        dataset_archive_sha256=receipt.dataset_archive_sha256,
        authorization_id="12345678-1234-4123-8123-123456789abc",
        authorized_action="ONE_FORMAL_20_TRIAL_DEVELOPMENT_RUN",
        authorized_at_utc="2026-08-28T00:00:00Z",
        consumed=False,
    )
    authorization_raw = protocol.canonicalize_json(authorization.model_dump(mode="json"))
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_bytes(authorization_raw)

    archive_path = tmp_path / "wrong-digest-archive.zip"
    archive_path.write_bytes(b"x" * 279_992)
    consumption_root = tmp_path / "consumption"
    publication_root = tmp_path / "publication"
    consumption_root.mkdir()
    publication_root.mkdir()

    worker_entries = tuple(
        protocol.FormalWorkerSourceEntry(
            logical_path=logical_path,
            sha256=sha256_hex((REPOSITORY_ROOT / logical_path).read_bytes()),
        )
        for logical_path in protocol.FORMAL_WORKER_SOURCE_PATHS
    )
    request = protocol.FormalWorkerRequest(
        schema_version="mdcp.formal-worker-request.v1",
        canonicalization_version="RFC8785",
        expected_freeze_head="1" * 40,
        repository_root=REPOSITORY_ROOT.as_posix(),
        search_receipt_path=receipt_path.as_posix(),
        evidence_index_path=index_path.as_posix(),
        authorization_path=authorization_path.as_posix(),
        consumption_root=consumption_root.as_posix(),
        archive_path=archive_path.as_posix(),
        private_container_path=(publication_root / "private.json").as_posix(),
        search_receipt_sha256=sha256_hex(receipt_raw),
        evidence_index_sha256=sha256_hex(index_raw),
        authorization_sha256=sha256_hex(authorization_raw),
        source_inventory_sha256=index.source_inventory_sha256,
        repository_inventory_sha256="6" * 64,
        formal_worker_inventory_sha256=protocol.formal_worker_inventory_sha256(worker_entries),
        launch_profile_sha256=protocol.launch_profile_sha256(),
    )
    return request, consumption_root / f"{sha256_hex(authorization_raw)}.consumed.json"


def test_dedicated_worker_direct_main_fails_before_marker_or_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_path = REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker.py"
    assert worker_path.is_file()
    import mdcp.temporal.formal_worker as worker

    def forbidden(*_args: object, **_kwargs: object) -> object:
        pytest.fail("direct worker call crossed the pre-authorization boundary")

    monkeypatch.setattr(worker, "_create_durable_marker", forbidden)
    monkeypatch.setattr(worker, "_hash_archive", forbidden)
    monkeypatch.setattr(worker, "_execute_natural_run", forbidden)
    assert str(inspect.signature(worker.main)) == "() -> 'int'"
    assert worker.main() == 2


def test_worker_request_sha256_is_bound_into_terminal_seal_by_exact_worker_inputs() -> None:
    import mdcp.temporal.formal_worker as worker

    tree = ast.parse(inspect.getsource(worker))
    complete = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_complete_finalized_run"
    )
    imports = {
        alias.name
        for node in ast.walk(complete)
        if isinstance(node, ast.ImportFrom)
        and node.module == "mdcp.temporal.formal_worker_protocol"
        for alias in node.names
    }
    seal_call = next(
        node
        for node in ast.walk(complete)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FormalDevelopmentSeal"
    )
    keywords = {keyword.arg: keyword.value for keyword in seal_call.keywords}

    assert imports == {"worker_request_sha256"}
    expected = {
        "worker_request_sha256": "worker_request_sha256(context.request)",
        "formal_worker_inventory_sha256": ("context.request.formal_worker_inventory_sha256"),
        "launch_profile_sha256": "context.request.launch_profile_sha256",
        "evidence_index_sha256": "context.request.evidence_index_sha256",
    }
    assert {name: ast.unparse(keywords[name]) for name in expected} == expected


def test_dedicated_worker_exact_launch_reaches_preconsumption_verification() -> None:
    worker_path = REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker.py"
    entries = tuple(
        protocol.FormalWorkerSourceEntry(
            logical_path=logical_path,
            sha256=sha256_hex((REPOSITORY_ROOT / logical_path).read_bytes()),
        )
        for logical_path in protocol.FORMAL_WORKER_SOURCE_PATHS
    )
    request = protocol.FormalWorkerRequest(
        schema_version="mdcp.formal-worker-request.v1",
        canonicalization_version="RFC8785",
        expected_freeze_head="1" * 40,
        repository_root=REPOSITORY_ROOT.as_posix(),
        search_receipt_path=(REPOSITORY_ROOT / "receipt.json").as_posix(),
        evidence_index_path=(REPOSITORY_ROOT / "index.json").as_posix(),
        authorization_path=(REPOSITORY_ROOT / "authorization.json").as_posix(),
        consumption_root=(REPOSITORY_ROOT / "consumption").as_posix(),
        archive_path=(REPOSITORY_ROOT / "archive.zip").as_posix(),
        private_container_path=(REPOSITORY_ROOT / "private.json").as_posix(),
        search_receipt_sha256="2" * 64,
        evidence_index_sha256="3" * 64,
        authorization_sha256="4" * 64,
        source_inventory_sha256="5" * 64,
        repository_inventory_sha256="6" * 64,
        formal_worker_inventory_sha256=protocol.formal_worker_inventory_sha256(entries),
        launch_profile_sha256=protocol.launch_profile_sha256(),
    )

    raw = run_evidence._run_fixed_worker_transport(
        REPOSITORY_ROOT,
        Path(run_evidence._current_python_executable()),
        worker_path,
        protocol.encode_formal_worker_request(request),
    )
    response = protocol.parse_formal_worker_response(raw)

    assert response.verdict == "FAIL"
    assert response.reason_codes == ("FORMAL_RUN_AUTHORIZATION_INVALID",)
    assert response.fit_count == 0
    assert response.worker_request_sha256 == protocol.worker_request_sha256(request)
    assert response.launch_profile_sha256 == protocol.launch_profile_sha256()


def test_worker_lifecycle_wrong_digest_consumes_marker_before_archive_denial(
    tmp_path: Path,
) -> None:
    request, marker_path = _task_five_wrong_digest_request(tmp_path)
    completed = subprocess.run(
        (
            sys.executable,
            "-I",
            "-B",
            "-S",
            str(REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker.py"),
        ),
        cwd=REPOSITORY_ROOT,
        input=protocol.encode_formal_worker_request(request),
        capture_output=True,
        check=False,
        env={
            "SYSTEMROOT": str(Path(sys.executable).anchor),
            "WINDIR": str(Path(sys.executable).anchor),
        },
    )

    assert completed.returncode == 0
    assert completed.stderr == b""
    response = protocol.parse_formal_worker_response(completed.stdout)
    assert response.verdict == "UNKNOWN"
    assert response.reason_codes == ("FORMAL_RUN_EXECUTION_UNKNOWN",)
    assert response.authorization_sha256 == request.authorization_sha256
    assert response.consumption_marker_sha256 == sha256_hex(marker_path.read_bytes())
    assert response.fit_count == 0
    assert not Path(f"{request.private_container_path}.public.json").exists()


def test_marker_before_access_worker_has_no_natural_authority_in_supervisor() -> None:
    import ast

    tree = ast.parse(inspect.getsource(run_evidence))
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    for retired_name in (
        "_build_formal_execution_plan",
        "_load_formal_execution_state",
        "_fit_formal_fold",
        "formal_operation",
        "encode_natural",
    ):
        assert retired_name not in definitions
    assert all(
        not isinstance(node, ast.Constant)
        or not isinstance(node.value, str)
        or len(node.value) < 1_024
        for node in ast.walk(tree)
    ), "supervisor must not hide retired natural capability in a dormant code string"


def _fix_round_one_worker_process(
    tmp_path: Path,
    case_id: str,
) -> tuple[subprocess.CompletedProcess[bytes], protocol.FormalWorkerRequest, Path]:
    request, marker_path = _task_five_wrong_digest_request(tmp_path)
    worker_path = REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker.py"
    arguments = [sys.executable, "-I", "-B", "-S", str(worker_path)]
    environment = {
        "SYSTEMROOT": os.environ["SYSTEMROOT"],
        "WINDIR": os.environ["WINDIR"],
    }
    cwd = REPOSITORY_ROOT
    if case_id == "wrong-cwd":
        cwd = tmp_path / "wrong-cwd"
        cwd.mkdir()
    elif case_id == "missing-systemroot":
        environment.pop("SYSTEMROOT")
    elif case_id == "missing-windir":
        environment.pop("WINDIR")
    elif case_id == "extra-environment":
        environment["MDCP_FORBIDDEN_EXTRA"] = "1"
    elif case_id == "non-isolated":
        arguments.remove("-I")
    elif case_id == "site-enabled":
        arguments.remove("-S")
    elif case_id == "bytecode-enabled":
        arguments.remove("-B")
    elif case_id == "wrong-script-target":
        clone = tmp_path / "formal_worker_clone.py"
        clone.write_bytes(worker_path.read_bytes())
        arguments[-1] = str(clone)
    else:  # pragma: no cover - the parameter table is closed
        raise AssertionError(case_id)
    return (
        subprocess.run(
            arguments,
            cwd=cwd,
            input=protocol.encode_formal_worker_request(request),
            capture_output=True,
            check=False,
            env=environment,
        ),
        request,
        marker_path,
    )


@pytest.mark.parametrize(
    "case_id",
    (
        "wrong-cwd",
        "missing-systemroot",
        "missing-windir",
        "extra-environment",
        "non-isolated",
        "site-enabled",
        "bytecode-enabled",
        "wrong-script-target",
    ),
)
def test_dedicated_worker_nonexact_launch_profile_never_reaches_protocol(
    tmp_path: Path,
    case_id: str,
) -> None:
    completed, request, marker_path = _fix_round_one_worker_process(tmp_path, case_id)

    assert completed.returncode != 0
    assert completed.stdout == b""
    assert completed.stderr == b""
    assert not marker_path.exists()
    assert not Path(request.private_container_path).exists()
    assert not Path(f"{request.private_container_path}.public.json").exists()
