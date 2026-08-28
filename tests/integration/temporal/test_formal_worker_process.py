from __future__ import annotations

import inspect
from pathlib import Path

import mdcp.temporal.formal_worker_protocol as protocol
import mdcp.temporal.run_evidence as run_evidence
from mdcp.common.digests import sha256_hex

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_worker_process_bootstrap_is_a_no_argument_import_safe_target() -> None:
    worker_path = REPOSITORY_ROOT / "src/mdcp/temporal/formal_worker.py"
    assert worker_path.is_file()
    import mdcp.temporal.formal_worker as worker

    assert str(inspect.signature(worker.main)) == "() -> 'int'"
    assert worker.main() == 2


def test_worker_process_task_four_response_is_canonical_and_fail_closed() -> None:
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
    assert response.reason_codes == ("FORMAL_RUN_REQUEST_INVALID",)
    assert response.fit_count == 0
    assert response.worker_request_sha256 == protocol.worker_request_sha256(request)
    assert response.launch_profile_sha256 == protocol.launch_profile_sha256()
