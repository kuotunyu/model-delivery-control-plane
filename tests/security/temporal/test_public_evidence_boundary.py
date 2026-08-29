from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

import mdcp.temporal.formal_worker_protocol as worker_protocol
import mdcp.temporal.run_evidence as run_evidence
from mdcp.common.canonical import canonicalize_json
from mdcp.temporal.evidence import public_evidence_violations
from mdcp.temporal.run_evidence import (
    FormalDevelopmentOutcome,
    FormalSealCheck,
    PrivateBundleIdentity,
)

_FORMAL_REQUEST_INVALID_STDOUT = (
    '{"reason_code":"FORMAL_RUN_REQUEST_INVALID","schema_version":'
    '"mdcp.formal-run-cli-result.v1","verdict":"FAIL"}\n'
)
_SEARCH_ANCHOR_INVALID_STDOUT = (
    '{"reason_code":"SEARCH_SOURCE_INDEX_ANCHOR_INVALID","schema_version":'
    '"mdcp.search-source-cli-result.v1","verdict":"FAIL"}\n'
)
_SEARCH_ANCHOR_MISMATCH_STDOUT = (
    '{"reason_code":"SEARCH_SOURCE_INDEX_ANCHOR_MISMATCH","schema_version":'
    '"mdcp.search-source-cli-result.v1","verdict":"FAIL"}\n'
)
_CLOSED_COMMAND_ARGUMENTS = (
    (
        "run-development",
        (
            "run-development",
            "--expected-freeze-head",
            "a" * 40,
            "--search-receipt",
            "r",
            "--evidence-index",
            "i",
            "--authorization-env",
            "MDCP_FORMAL_RUN_AUTHORIZATION",
            "--consumption-root-env",
            "MDCP_FORMAL_RUN_CONSUMPTION_ROOT",
            "--archive-env",
            "MDCP_UCI_ARCHIVE",
            "--private-container-env",
            "MDCP_V02_PRIVATE_CONTAINER",
        ),
    ),
    (
        "verify-search-freeze",
        ("verify-search-freeze", "--receipt", "r", "--index", "i"),
    ),
    (
        "prepare-search-freeze",
        (
            "prepare-search-freeze",
            "--repository-root",
            "r",
            "--created-at-utc",
            "2026-08-26T00:00:00+00:00",
        ),
    ),
    (
        "verify-search-source",
        (
            "verify-search-source",
            "--root",
            "r",
            "--index",
            "i",
            "--expected-index-sha256",
            "a" * 64,
        ),
    ),
    (
        "verify-development-result",
        (
            "verify-development-result",
            "--consumption-marker",
            "m",
            "--private-container",
            "p",
            "--terminal-seal",
            "t",
            "--expected-authorization-sha256",
            "a" * 64,
            "--expected-search-receipt-sha256",
            "b" * 64,
            "--expected-worker-request-sha256",
            "f" * 64,
            "--expected-formal-worker-inventory-sha256",
            "1" * 64,
            "--expected-launch-profile-sha256",
            "2" * 64,
            "--expected-source-inventory-sha256",
            "c" * 64,
            "--expected-repository-inventory-sha256",
            "d" * 64,
            "--expected-evidence-index-sha256",
            "3" * 64,
            "--expected-seal-record-sha256",
            "e" * 64,
        ),
    ),
)
_OMITTED_REQUIRED_OPTION_CASES = tuple(
    pytest.param(arguments, option, id=f"{command}-{option[2:]}")
    for command, arguments in _CLOSED_COMMAND_ARGUMENTS
    for option in arguments[1::2]
)


def _verify_search_source_arguments(root: Path, index: Path, anchor: str) -> list[str]:
    return [
        "verify-search-source",
        "--root",
        str(root),
        "--index",
        str(index),
        "--expected-index-sha256",
        anchor,
    ]


def _capture_search_source_verifier(monkeypatch: pytest.MonkeyPatch):
    from mdcp.temporal import search_identity

    real_verifier = search_identity.verify_search_source_inventory
    calls: list[tuple[Path, Path, str]] = []

    def capture(root: Path, index: Path, anchor: str):
        calls.append((root, index, anchor))
        return real_verifier(root, index, anchor)

    monkeypatch.setattr(search_identity, "verify_search_source_inventory", capture)
    return calls


def _development_arguments(tmp_path: Path) -> tuple[list[str], tuple[object, ...]]:
    marker = (tmp_path / "consumption-marker.json").resolve()
    private = (tmp_path / "private-container.json").resolve()
    terminal = (tmp_path / "terminal-seal.json").resolve()
    digests = tuple(character * 64 for character in "abcdef123")
    arguments = [
        "verify-development-result",
        "--consumption-marker",
        str(marker),
        "--private-container",
        str(private),
        "--terminal-seal",
        str(terminal),
        "--expected-authorization-sha256",
        digests[0],
        "--expected-search-receipt-sha256",
        digests[1],
        "--expected-worker-request-sha256",
        digests[2],
        "--expected-formal-worker-inventory-sha256",
        digests[3],
        "--expected-launch-profile-sha256",
        digests[4],
        "--expected-source-inventory-sha256",
        digests[5],
        "--expected-repository-inventory-sha256",
        digests[6],
        "--expected-evidence-index-sha256",
        digests[7],
        "--expected-seal-record-sha256",
        digests[8],
    ]
    return arguments, (marker, private, terminal, *digests)


def _install_offline_denial_sentinels(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    import joblib

    import mdcp.workload.dataset as dataset
    import mdcp.workload.splits as splits

    calls = {
        "uci_loader": 0,
        "h1_loader": 0,
        "h2_loader": 0,
        "model_loader": 0,
        "model_execution": 0,
    }

    def denial(name: str):
        def denied(*args: object, **kwargs: object) -> None:
            del args, kwargs
            calls[name] += 1
            raise AssertionError(f"offline denial sentinel called: {name}")

        return denied

    monkeypatch.setattr(dataset, "load_uci_archive", denial("uci_loader"))
    monkeypatch.setattr(dataset, "load_uci_development_archive", denial("h1_loader"))
    monkeypatch.setattr(splits.DatasetPartitions, "open_h2", denial("h2_loader"))
    monkeypatch.setattr(joblib, "load", denial("model_loader"))
    monkeypatch.setattr(
        run_evidence,
        "execute_authorized_formal_development",
        denial("model_execution"),
    )
    return calls


def test_cli_exposes_only_the_five_closed_commands() -> None:
    from mdcp.temporal.cli import build_parser

    parser = build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert tuple(action.choices) == (
        "run-development",
        "verify-search-freeze",
        "prepare-search-freeze",
        "verify-search-source",
        "verify-development-result",
    )


def test_verify_search_source_requires_explicit_archive_root() -> None:
    from mdcp.temporal.cli import build_parser

    with pytest.raises(ValueError, match="^FORMAL_RUN_REQUEST_INVALID$"):
        build_parser().parse_args(
            [
                "verify-search-source",
                "--index",
                "index.json",
                "--expected-index-sha256",
                "a" * 64,
            ]
        )


def test_prepare_search_freeze_forwards_exact_root_and_timestamp(
    monkeypatch: pytest.MonkeyPatch, capfd, tmp_path: Path
) -> None:
    from datetime import UTC, datetime

    from mdcp.temporal import cli, search_identity

    root = (tmp_path / "repository").resolve()
    created_at = datetime(2026, 8, 26, 0, 0, tzinfo=UTC)
    calls: list[tuple[Path, datetime]] = []

    def capture(repository_root: Path, created_at_utc: datetime) -> None:
        calls.append((repository_root, created_at_utc))

    monkeypatch.setattr(search_identity, "prepare_search_freeze", capture)

    exit_code = cli.main(
        [
            "prepare-search-freeze",
            "--repository-root",
            str(root),
            "--created-at-utc",
            created_at.isoformat(),
        ]
    )

    assert exit_code == 0
    assert calls == [(root, created_at)]
    assert capfd.readouterr().out == (
        '{"reason_code":"SEARCH_FREEZE_PREPARED","schema_version":'
        '"mdcp.search-freeze-cli-result.v1","verdict":"PASS"}\n'
    )


def test_verify_search_source_cli_rejects_an_absent_anchor_flag(
    monkeypatch: pytest.MonkeyPatch, capfd, tmp_path: Path
) -> None:
    from mdcp.temporal import cli, search_identity

    calls = 0

    def denied(*args: object, **kwargs: object):
        nonlocal calls
        del args, kwargs
        calls += 1
        raise AssertionError("source verifier must not run after parser rejection")

    monkeypatch.setattr(search_identity, "verify_search_source_inventory", denied)

    exit_code = cli.main(
        [
            "verify-search-source",
            "--root",
            str(tmp_path / "archive"),
            "--index",
            str(tmp_path / "index.json"),
        ]
    )

    assert exit_code == 2
    assert capfd.readouterr().out == _FORMAL_REQUEST_INVALID_STDOUT
    assert calls == 0


@pytest.mark.parametrize(
    "anchor",
    ("0" * 64, "A" * 64, "a" * 63, "g" + "a" * 63),
    ids=("zero", "uppercase", "malformed-length", "malformed-character"),
)
def test_verify_search_source_cli_rejects_each_invalid_anchor(
    monkeypatch: pytest.MonkeyPatch, capfd, tmp_path: Path, anchor: str
) -> None:
    from mdcp.temporal import cli

    root = (tmp_path / "archive").resolve()
    root.mkdir()
    index = (tmp_path / "index.json").resolve()
    index.write_bytes(b"{}")
    calls = _capture_search_source_verifier(monkeypatch)

    exit_code = cli.main(_verify_search_source_arguments(root, index, anchor))

    assert exit_code == 2
    assert capfd.readouterr().out == _SEARCH_ANCHOR_INVALID_STDOUT
    assert calls == [(root, index, anchor)]


def test_verify_search_source_cli_rejects_a_mismatched_anchor(
    monkeypatch: pytest.MonkeyPatch, capfd, tmp_path: Path
) -> None:
    from mdcp.temporal import cli

    root = (tmp_path / "archive").resolve()
    root.mkdir()
    index = (tmp_path / "index.json").resolve()
    index.write_bytes(b"{}")
    anchor = "a" * 64
    calls = _capture_search_source_verifier(monkeypatch)

    exit_code = cli.main(_verify_search_source_arguments(root, index, anchor))

    assert exit_code == 2
    assert capfd.readouterr().out == _SEARCH_ANCHOR_MISMATCH_STDOUT
    assert calls == [(root, index, anchor)]


def test_verify_search_source_forwards_exact_root_and_emits_fixed_success(
    monkeypatch: pytest.MonkeyPatch, capfd, tmp_path: Path
) -> None:
    from mdcp.temporal import cli
    from mdcp.temporal.search_identity import SearchSourceCheck

    archive = tmp_path / "archive"
    archive.mkdir()
    captured: list[Path] = []
    monkeypatch.setattr(
        "mdcp.temporal.search_identity.verify_search_source_inventory",
        lambda root, index, anchor: (
            captured.append(root) or SearchSourceCheck("PASS", ("SEARCH_SOURCE_INVENTORY_PASS",))
        ),
    )

    assert (
        cli.main(
            [
                "verify-search-source",
                "--root",
                str(archive),
                "--index",
                str(tmp_path / "index.json"),
                "--expected-index-sha256",
                "a" * 64,
            ]
        )
        == 0
    )
    assert captured == [archive]
    assert capfd.readouterr().out == "SEARCH_SOURCE_INVENTORY_PASS\n"


@pytest.mark.parametrize(
    ("verdict", "reason_code", "exit_code"),
    (
        ("PASS", "FORMAL_SEAL_PASS", 0),
        ("FAIL", "FORMAL_SEAL_CHAIN_INVALID", 2),
        ("UNKNOWN", "FORMAL_SEAL_INCOMPLETE", 3),
    ),
)
def test_development_result_cli_emits_exact_status_and_forwards_exact_inputs(
    monkeypatch: pytest.MonkeyPatch,
    capfd,
    tmp_path: Path,
    verdict: str,
    reason_code: str,
    exit_code: int,
) -> None:
    from mdcp.temporal import cli

    arguments, expected_forwarding = _development_arguments(tmp_path)
    calls: list[tuple[object, ...]] = []
    denial_calls = _install_offline_denial_sentinels(monkeypatch)
    if verdict == "PASS":
        check = FormalSealCheck(
            verdict="PASS",
            reason_codes=(),
            private_identity=PrivateBundleIdentity(
                file_count=5,
                total_bytes=1,
                inventory_sha256="f" * 64,
                manifest_sha256="1" * 64,
            ),
            seal_record_sha256="2" * 64,
            repository_inventory_sha256="3" * 64,
            fit_count=84,
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
        )
    else:
        check = FormalSealCheck(
            verdict=verdict,
            reason_codes=(reason_code,),
            private_identity=None,
            seal_record_sha256=None,
            repository_inventory_sha256=None,
            fit_count=0,
            h2_status="SEALED_NOT_LOADED",
            h2_loaded_rows=0,
        )

    def capture(
        marker: Path,
        private: Path,
        terminal: Path,
        *,
        expected_authorization_sha256: str,
        expected_search_receipt_sha256: str,
        expected_worker_request_sha256: str,
        expected_formal_worker_inventory_sha256: str,
        expected_launch_profile_sha256: str,
        expected_source_inventory_sha256: str,
        expected_repository_inventory_sha256: str,
        expected_evidence_index_sha256: str,
        expected_seal_record_sha256: str,
    ) -> FormalSealCheck:
        calls.append(
            (
                marker,
                private,
                terminal,
                expected_authorization_sha256,
                expected_search_receipt_sha256,
                expected_worker_request_sha256,
                expected_formal_worker_inventory_sha256,
                expected_launch_profile_sha256,
                expected_source_inventory_sha256,
                expected_repository_inventory_sha256,
                expected_evidence_index_sha256,
                expected_seal_record_sha256,
            )
        )
        return check

    monkeypatch.setattr(run_evidence, "verify_formal_development_seal", capture)

    assert cli.main(arguments) == exit_code
    assert capfd.readouterr().out == (
        f'{{"reason_code":"{reason_code}","schema_version":'
        f'"mdcp.development-result-cli-result.v1","verdict":"{verdict}"}}\n'
    )
    assert calls == [expected_forwarding]
    assert len(set(expected_forwarding[:3])) == 3
    assert len(set(expected_forwarding[3:])) == 9
    assert denial_calls == {
        "uci_loader": 0,
        "h1_loader": 0,
        "h2_loader": 0,
        "model_loader": 0,
        "model_execution": 0,
    }


@pytest.mark.parametrize(
    ("arguments", "omitted_option"),
    _OMITTED_REQUIRED_OPTION_CASES,
)
def test_each_required_cli_option_value_pair_is_independently_required(
    arguments: tuple[str, ...], omitted_option: str
) -> None:
    from mdcp.temporal.cli import build_parser

    position = arguments.index(omitted_option)
    invalid = (*arguments[:position], *arguments[position + 2 :])

    with pytest.raises(ValueError, match="^FORMAL_RUN_REQUEST_INVALID$"):
        build_parser().parse_args(invalid)


@pytest.mark.parametrize(
    "arguments",
    (pytest.param(arguments, id=command) for command, arguments in _CLOSED_COMMAND_ARGUMENTS),
)
def test_each_closed_cli_command_rejects_an_extra_option(
    arguments: tuple[str, ...],
) -> None:
    from mdcp.temporal.cli import build_parser

    with pytest.raises(ValueError, match="^FORMAL_RUN_REQUEST_INVALID$"):
        build_parser().parse_args((*arguments, "--unexpected", "value"))


@pytest.mark.parametrize(
    "arguments",
    (pytest.param(arguments, id=command) for command, arguments in _CLOSED_COMMAND_ARGUMENTS),
)
def test_each_closed_cli_command_rejects_an_extra_positional(
    arguments: tuple[str, ...],
) -> None:
    from mdcp.temporal.cli import build_parser

    with pytest.raises(ValueError, match="^FORMAL_RUN_REQUEST_INVALID$"):
        build_parser().parse_args((*arguments, "unexpected-positional"))


@pytest.mark.parametrize("command", ("unknown", "verify-unknown", ""))
def test_non_five_commands_are_rejected(command: str) -> None:
    from mdcp.temporal.cli import build_parser

    with pytest.raises(ValueError, match="^FORMAL_RUN_REQUEST_INVALID$"):
        build_parser().parse_args([command])


def test_public_scan_rejects_private_metadata_without_echoing_values() -> None:
    secret = "PRIVATE_PATH_SENTINEL"

    assert public_evidence_violations({"host_path": secret}) == ("PRIVATE_PATH",)
    assert public_evidence_violations({"error": "raw exception text"}) == ("RAW_EXCEPTION",)
    assert secret not in repr(public_evidence_violations({"host_path": secret}))


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ({"artifact": {"source_path": "C:/private/model.onnx"}}, ("PRIVATE_PATH",)),
        ({"username": "private-user"}, ("CREDENTIAL",)),
        ({"api_key": "not-public"}, ("CREDENTIAL",)),
        ({"traceback": "stack frame"}, ("RAW_EXCEPTION",)),
        ({"raw_environment": "NAME=value"}, ("RAW_ENVIRONMENT",)),
        ({"hostname": "private-host"}, ("RAW_ENVIRONMENT",)),
        ({"container_id": "a" * 64}, ("CONTAINER_ID",)),
        ({"payload": {"row": 1}}, ("OPAQUE_PAYLOAD", "RAW_EXECUTION")),
    ],
)
def test_public_scan_returns_fixed_low_cardinality_codes(
    document: object, expected: tuple[str, ...]
) -> None:
    assert public_evidence_violations(document) == expected


def test_public_scan_is_recursive_sorted_unique_and_allows_sanitized_aggregates() -> None:
    assert public_evidence_violations(
        {
            "nested": [
                {"error": "first"},
                {"host_path": "C:/private/one"},
                {"error": "second"},
            ]
        }
    ) == ("PRIVATE_PATH", "RAW_EXCEPTION")
    assert (
        public_evidence_violations(
            {
                "evidence_class": "synthetic_test",
                "inventory_sha256": "a" * 64,
                "reason_codes": ["OVERALL_UCB95"],
                "metrics": {"point_ratio": 0.97, "row_count": 2400},
            }
        )
        == ()
    )


@pytest.mark.parametrize(
    "private_path",
    [
        r"prefix C:\Users\reviewer\private\model.onnx suffix",
        "prefix C:/Users/reviewer/private/model.onnx suffix",
        r"prefix \\private-host\share\model.onnx suffix",
        "prefix /root/private/model.onnx suffix",
        "prefix /home/reviewer/model.onnx suffix",
        "prefix /Users/reviewer/model.onnx suffix",
        "prefix /mnt/private/model.onnx suffix",
        "prefix /tmp/private/model.onnx suffix",
        "prefix /var/tmp/private/model.onnx suffix",
        "prefix /private/model.onnx suffix",
        "prefix /Volumes/private/model.onnx suffix",
    ],
)
def test_public_scan_rejects_embedded_absolute_private_paths(private_path: str) -> None:
    result = public_evidence_violations({"note": private_path})

    assert result == ("PRIVATE_PATH",)
    assert private_path not in repr(result)


@pytest.mark.parametrize(
    "raw_exception",
    [
        "Traceback (most recent call last):\n  synthetic frame\nValueError: redacted",
        "request failed with InvalidResponseError: redacted",
        "unhandled RuntimeException: redacted",
        "ConnectTimeout: redacted",
        "ReadTimeout: redacted",
        "InvalidResponse: redacted",
    ],
)
def test_public_scan_rejects_raw_exceptions_under_arbitrary_keys(raw_exception: str) -> None:
    result = public_evidence_violations({"message": raw_exception})

    assert result == ("RAW_EXCEPTION",)
    assert raw_exception not in repr(result)


@pytest.mark.parametrize(
    "credential",
    [
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN ENCRYPTED PRIVATE KEY-----",
        "Bearer abc",
        "Bearer " + "a" * 32,
        "ghp_" + "A" * 36,
        "github_pat_" + "A" * 22 + "_" + "B" * 59,
        "hf_" + "a" * 34,
        "AKIA" + "A1" * 8,
    ],
)
def test_public_scan_rejects_common_credential_shapes(credential: str) -> None:
    result = public_evidence_violations({"note": credential})

    assert result == ("CREDENTIAL",)
    assert credential not in repr(result)


def test_public_scan_distinguishes_environment_dumps_from_research_assignments() -> None:
    assert public_evidence_violations({"note": "MODEL=rf\nTHREADS=1"}) == ("RAW_ENVIRONMENT",)
    assert public_evidence_violations({"note": "RATIO=0.97"}) == ()


def test_public_scan_allows_sanitized_error_class_labels_without_raw_messages() -> None:
    assert (
        public_evidence_violations(
            {
                "error_classes": [
                    "ConnectError",
                    "ConnectTimeout",
                    "ReadTimeout",
                    "ProtocolError",
                    "InvalidResponse",
                    "Other",
                ]
            }
        )
        == ()
    )


def test_private_bundle_identity_is_public_safe_by_shape_and_value() -> None:
    identity = PrivateBundleIdentity(
        file_count=2,
        total_bytes=42,
        inventory_sha256="a" * 64,
        manifest_sha256="b" * 64,
    )

    assert public_evidence_violations(identity.model_dump(mode="json")) == ()


def test_rejected_formal_outcome_exposes_only_fixed_public_failure_fields() -> None:
    outcome = FormalDevelopmentOutcome(
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
    )
    document = {
        "reason_code": outcome.reason_codes[0],
        "schema_version": "mdcp.formal-run-cli-result.v1",
        "verdict": outcome.verdict,
    }

    assert document == {
        "reason_code": "FORMAL_RUN_REQUEST_INVALID",
        "schema_version": "mdcp.formal-run-cli-result.v1",
        "verdict": "FAIL",
    }
    assert public_evidence_violations(document) == ()


def test_private_container_check_exposes_only_sanitized_shape() -> None:
    check = run_evidence.PrivateContainerCheck(
        verdict="FAIL",
        reason_codes=("PRIVATE_CONTAINER_INVALID",),
    )

    assert set(check.model_dump()) == {"verdict", "reason_codes", "identity"}
    assert check.identity is None
    assert public_evidence_violations(check.model_dump(mode="json")) == ()


def test_private_publication_surface_has_no_direct_natural_writer() -> None:
    assert not hasattr(run_evidence, "write_natural_bundle_no_clobber")
    assert not hasattr(run_evidence, "write_private_bundle_no_clobber")


def test_private_verifier_sanitizes_path_and_identity_type_failures(tmp_path: Path) -> None:
    secret = tmp_path / "PRIVATE_PATH_SENTINEL.container.json"
    secret.write_bytes(b"not-json")

    check = run_evidence.verify_private_container(secret, True)  # type: ignore[arg-type]

    assert check.reason_codes == ("PRIVATE_CONTAINER_INVALID",)
    assert str(secret) not in repr(check)


@pytest.mark.parametrize(
    "document",
    (
        {"command": "python formal_worker.py"},
        {"row": {"cnt": 42}},
        {"label": 42.0},
        {"prediction": 41.0},
        {"created_at_utc": "2026-08-29T00:00:00Z"},
    ),
)
def test_public_worker_response_scanner_rejects_raw_execution_shapes(
    document: dict[str, object],
) -> None:
    violations = public_evidence_violations(document)
    assert violations
    assert all(repr(value) not in repr(violations) for value in document.values())


def test_complete_closed_search_receipt_with_created_at_utc_remains_scanner_clean() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    raw = (repository_root / "evidence/public/v02/search/search-receipt.json").read_bytes()
    receipt = worker_protocol.SearchReceipt.model_validate_json(raw)
    document = receipt.model_dump(mode="json")

    assert set(document) == set(worker_protocol.SearchReceipt.model_fields)
    assert document["schema_version"] == "mdcp.search-receipt.v1"
    assert "created_at_utc" in document
    assert public_evidence_violations(document) == ()


def test_dedicated_worker_source_and_physical_index_digests_keep_distinct_meanings() -> None:
    assert len(worker_protocol.SEARCH_SOURCE_PATHS) == 47
    assert set(worker_protocol.FORMAL_WORKER_SOURCE_PATHS).issubset(
        worker_protocol.SEARCH_SOURCE_PATHS
    )
    source_entries = tuple(
        worker_protocol.SearchSourceEntry(
            logical_path=path,
            git_mode="100644",
            byte_size=len(path.encode("ascii")),
            sha256=sha256(path.encode("ascii")).hexdigest(),
        )
        for path in worker_protocol.SEARCH_SOURCE_PATHS
    )
    worker_entries = tuple(
        worker_protocol.FormalWorkerSourceEntry(
            logical_path=path,
            sha256=sha256(path.encode("ascii")).hexdigest(),
        )
        for path in worker_protocol.FORMAL_WORKER_SOURCE_PATHS
    )
    source_digest = worker_protocol.search_source_inventory_sha256(source_entries)
    worker_digest = worker_protocol.formal_worker_inventory_sha256(worker_entries)
    launch_digest = worker_protocol.launch_profile_sha256()
    index = worker_protocol.SearchEvidenceIndex(
        schema_version="mdcp.search-evidence-index.v1",
        canonicalization_version="RFC8785",
        source_entries=source_entries,
        source_inventory_sha256=source_digest,
        private_logical_outputs=worker_protocol.PRIVATE_LOGICAL_OUTPUTS,
        search_receipt_sha256="a" * 64,
        h2_status="SEALED_NOT_LOADED",
        h2_loaded_rows=0,
    )
    index_digest = sha256(canonicalize_json(index.model_dump(mode="json"))).hexdigest()

    assert len({source_digest, index_digest, worker_digest, launch_digest}) == 4
    assert (
        public_evidence_violations(
            {
                "source_inventory_sha256": source_digest,
                "evidence_index_sha256": index_digest,
                "formal_worker_inventory_sha256": worker_digest,
                "launch_profile_sha256": launch_digest,
            }
        )
        == ()
    )

    copied_index_document = index.model_dump(mode="json")
    copied_index_document["source_inventory_sha256"] = index_digest
    with pytest.raises(ValueError):
        worker_protocol.SearchEvidenceIndex.model_validate(copied_index_document)


def test_search_receipt_timestamp_exemption_requires_the_exact_closed_document() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    raw = (repository_root / "evidence/public/v02/search/search-receipt.json").read_bytes()
    document = worker_protocol.SearchReceipt.model_validate_json(raw).model_dump(mode="json")
    document["unexpected"] = "aggregate"

    assert public_evidence_violations(document) == ("RAW_TIMESTAMP",)


@pytest.mark.parametrize(
    ("needle", "replacement"),
    (
        pytest.param(
            (
                "closed_search_receipt = (\n"
                "                frozenset(current) == _SEARCH_RECEIPT_KEYS\n"
                '                and current.get("schema_version") == '
                '"mdcp.search-receipt.v1"\n'
                "            )"
            ),
            (
                "closed_search_receipt = (\n"
                '                current.get("schema_version") == '
                '"mdcp.search-receipt.v1"\n'
                "            )"
            ),
            id="arbitrary-receipt-exemption",
        ),
        pytest.param(
            "if normalized in _RAW_EXECUTION_KEYS:",
            'if normalized in _RAW_EXECUTION_KEYS or normalized.endswith("_command"):',
            id="generic-scanner-capability",
        ),
    ),
)
def test_task_six_firewall_rejects_scanner_source_capability_mutations(
    tmp_path: Path,
    needle: str,
    replacement: str,
) -> None:
    import mdcp.temporal.firewall as firewall

    logical_path = "src/mdcp/temporal/evidence.py"
    repository_root = Path(__file__).resolve().parents[3]
    source = (repository_root / logical_path).read_text(encoding="utf-8")
    mutated = source.replace(needle, replacement, 1)
    assert mutated != source
    target = tmp_path / logical_path
    target.parent.mkdir(parents=True)
    target.write_text(mutated, encoding="utf-8")

    with pytest.raises(
        firewall.StaticFirewallError,
        match="^H2_IMPORT_CAPABILITY_FORBIDDEN$",
    ):
        firewall.audit_static_h2_firewall(tmp_path, formal_paths=(logical_path,))


def test_public_worker_response_scanner_keeps_exact_not_generic_execution_keys() -> None:
    assert (
        public_evidence_violations(
            {
                "commands": 1,
                "rows": 2,
                "labels": 3,
                "predictions": 4,
            }
        )
        == ()
    )
