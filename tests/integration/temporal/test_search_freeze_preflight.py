from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdcp.common.canonical import canonicalize_json
from mdcp.temporal.search_identity import (
    SEARCH_SOURCE_PATHS,
    SearchIdentityInputs,
    build_search_receipt,
    build_search_source_inventory,
    prepare_search_freeze,
    verify_search_freeze,
    verify_search_source_inventory,
)

EXACT_SEARCH_SOURCE_PATHS = (
    "configs/workload/temporal-development-v2.json",
    "configs/workload/uci-bike-sharing-v1.json",
    "docs/superpowers/plans/2026-08-24-mdcp-v02-wave-3-formal-development.md",
    "docs/superpowers/plans/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective.md",
    "docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-dedicated-formal-worker-corrective.md",
    "docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md",
    "docs/superpowers/specs/2026-08-25-mdcp-v02-wave-3-execution-boundary-corrective-design.md",
    "docs/superpowers/specs/2026-08-26-mdcp-v02-private-evidence-container-design.md",
    "docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md",
    "docs/superpowers/specs/2026-08-27-mdcp-v02-rejected-freeze-topology-design.md",
    "pyproject.toml",
    "schemas/v2/bike-request.schema.json",
    "schemas/v2/development-result-index.schema.json",
    "schemas/v2/formal-run-authorization.schema.json",
    "schemas/v2/formal-worker-request.schema.json",
    "schemas/v2/formal-worker-response.schema.json",
    "schemas/v2/search-receipt.schema.json",
    "schemas/v2/temporal-contract-receipt.schema.json",
    "schemas/v2/temporal-development.schema.json",
    "src/mdcp/common/canonical.py",
    "src/mdcp/common/digests.py",
    "src/mdcp/common/enums.py",
    "src/mdcp/contracts/workload.py",
    "src/mdcp/contracts/workload_v2.py",
    "src/mdcp/policy/cluster_bootstrap.py",
    "src/mdcp/temporal/adapter.py",
    "src/mdcp/temporal/cli.py",
    "src/mdcp/temporal/completeness.py",
    "src/mdcp/temporal/constants.py",
    "src/mdcp/temporal/contract_gate.py",
    "src/mdcp/temporal/evaluation.py",
    "src/mdcp/temporal/evidence.py",
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/folds.py",
    "src/mdcp/temporal/formal_worker.py",
    "src/mdcp/temporal/formal_worker_protocol.py",
    "src/mdcp/temporal/golden_vectors.py",
    "src/mdcp/temporal/run_evidence.py",
    "src/mdcp/temporal/runner.py",
    "src/mdcp/temporal/runtime_guards.py",
    "src/mdcp/temporal/search_identity.py",
    "src/mdcp/temporal/selection.py",
    "src/mdcp/temporal/trials.py",
    "src/mdcp/workload/dataset.py",
    "src/mdcp/workload/splits.py",
    "tests/fixtures/temporal/adapter-golden-vectors.json",
    "uv.lock",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RECEIPT_RELATIVE_PATH = Path("evidence/public/v02/search/search-receipt.json")
INDEX_RELATIVE_PATH = Path("evidence/public/v02/search/evidence-index.json")
DEDICATED_WORKER_DESIGN_PATH = (
    "docs/superpowers/specs/2026-08-27-mdcp-v02-dedicated-formal-worker-design.md"
)
DEDICATED_WORKER_PLAN_PATH = (
    "docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-dedicated-formal-worker-corrective.md"
)
OBSOLETE_FINAL_REVIEW_DESIGN_PATH = (
    "docs/superpowers/specs/2026-08-26-mdcp-v02-formal-seal-final-review-corrective-design.md"
)
OBSOLETE_FINAL_REVIEW_PLAN_PATH = (
    "docs/superpowers/plans/2026-08-27-mdcp-v02-wave-3-final-review-corrective.md"
)
FORMAL_WORKER_SOURCE_PATHS = (
    "schemas/v2/formal-worker-request.schema.json",
    "schemas/v2/formal-worker-response.schema.json",
    "src/mdcp/temporal/formal_worker.py",
    "src/mdcp/temporal/formal_worker_protocol.py",
)
CRLF_ARCHIVE_PATHS = (
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/run_evidence.py",
    "src/mdcp/temporal/runner.py",
    "src/mdcp/temporal/search_identity.py",
)
LF_DEDICATED_WORKER_PATHS = FORMAL_WORKER_SOURCE_PATHS
IMPLEMENTATION_TEST_PATHS = (
    "tests/integration/temporal/test_formal_worker_process.py",
    "tests/unit/temporal/test_formal_worker_protocol.py",
)
EXTRA_TEST_PATH = "tests/security/temporal/test_data_firewall.py"
EXTERNAL_ATTRIBUTES_PROFILE = (
    "* text eol=lf\n"
    "src/mdcp/temporal/firewall.py text eol=crlf\n"
    "src/mdcp/temporal/run_evidence.py text eol=crlf\n"
    "src/mdcp/temporal/runner.py text eol=crlf\n"
    "src/mdcp/temporal/search_identity.py text eol=crlf\n"
)
_BOUND_FILES = {
    "approved_spec_sha256": (
        "docs/superpowers/specs/2026-08-24-mdcp-v02-temporal-retraining-design.md"
    ),
    "dependency_lock_sha256": "uv.lock",
    "dataset_contract_sha256": "configs/workload/temporal-development-v2.json",
    "temporal_schema_sha256": "schemas/v2/temporal-development.schema.json",
    "temporal_adapter_sha256": "src/mdcp/temporal/adapter.py",
    "golden_vector_sha256": "tests/fixtures/temporal/adapter-golden-vectors.json",
    "fold_table_sha256": "configs/workload/temporal-development-v2.json",
    "trial_table_sha256": "configs/workload/temporal-development-v2.json",
    "ranking_rule_sha256": "src/mdcp/temporal/selection.py",
    "quality_policy_sha256": "configs/workload/temporal-development-v2.json",
    "statistical_code_sha256": "src/mdcp/temporal/evaluation.py",
}


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit(repository: Path, subject: str) -> str:
    _git(repository, "add", ".")
    return _commit_staged(repository, subject)


def _commit_staged(repository: Path, subject: str) -> str:
    _git(
        repository,
        "-c",
        "user.name=MDCP test",
        "-c",
        "user.email=mdcp-test@example.invalid",
        "commit",
        "-m",
        subject,
    )
    return _git(repository, "rev-parse", "HEAD")


def _stage_symlink_entry(repository: Path, relative_path: Path) -> None:
    blob = subprocess.run(
        ("git", "hash-object", "-w", "--stdin"),
        cwd=repository,
        check=True,
        input="external-search-receipt.json",
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git(repository, "add", str(INDEX_RELATIVE_PATH))
    _git(
        repository,
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{blob},{relative_path.as_posix()}",
    )


def _stage_120000_blob(repository: Path, relative_path: str) -> None:
    blob = subprocess.run(
        ("git", "hash-object", "-w", "--stdin"),
        cwd=repository,
        check=True,
        input="indexed-link-target",
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git(
        repository,
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{blob},{relative_path}",
    )


def _write(repository: Path, relative_path: str | Path, contents: bytes) -> None:
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)


def _receipt_document(repository: Path, source_commit: str) -> bytes:
    fields = {
        field: sha256((repository / path).read_bytes()).hexdigest()
        for field, path in _BOUND_FILES.items()
    }
    receipt = build_search_receipt(
        SearchIdentityInputs(
            search_source_commit=source_commit,
            dataset_archive_sha256=(
                "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"
            ),
            development_rows_sha256=(
                "b6d1bf9218354b112c2b74344283822fc83be678ff08f96f42199cb18076b3cc"
            ),
            created_at_utc=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
            **fields,
        )
    )
    return canonicalize_json(receipt.model_dump(mode="json"))


def _independent_source_entries(repository: Path) -> list[dict[str, object]]:
    return [
        {
            "logical_path": logical_path,
            "git_mode": "100644",
            "byte_size": len((repository / logical_path).read_bytes()),
            "sha256": sha256((repository / logical_path).read_bytes()).hexdigest(),
        }
        for logical_path in EXACT_SEARCH_SOURCE_PATHS
    ]


def _index_document(repository: Path, receipt_bytes: bytes) -> dict[str, object]:
    entries = _independent_source_entries(repository)
    return {
        "schema_version": "mdcp.search-evidence-index.v1",
        "canonicalization_version": "RFC8785",
        "source_entries": entries,
        "source_inventory_sha256": sha256(canonicalize_json(entries)).hexdigest(),
        "private_logical_outputs": [
            "provisional-winner.json",
            "qualification-report.json",
            "ranking-report.json",
            "replay-report.json",
            "trial-summary.json",
        ],
        "search_receipt_sha256": sha256(receipt_bytes).hexdigest(),
        "h2_status": "SEALED_NOT_LOADED",
        "h2_loaded_rows": 0,
    }


def _source_entries(document: dict[str, object]) -> list[dict[str, object]]:
    entries = document["source_entries"]
    assert isinstance(entries, list)
    assert all(isinstance(entry, dict) for entry in entries)
    return entries


def _fresh_archive_index(tmp_path: Path, name: str) -> tuple[Path, Path, dict[str, object]]:
    archive = tmp_path / name
    _archive_source_tree(archive)
    index_path = tmp_path / f"{name}.json"
    return archive, index_path, _index_document(archive, b"receipt")


def _verify_index_document(archive: Path, index_path: Path, document: dict[str, object]):
    entries = _source_entries(document)
    document["source_inventory_sha256"] = sha256(canonicalize_json(entries)).hexdigest()
    index_path.write_bytes(canonicalize_json(document))
    external_anchor = sha256(index_path.read_bytes()).hexdigest()
    return verify_search_source_inventory(archive, index_path, external_anchor)


def _assert_index_invalid(result) -> None:
    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_INDEX_INVALID",)


def _write_receipt_and_index(repository: Path, source_commit: str) -> None:
    receipt_bytes = _receipt_document(repository, source_commit)
    _write(repository, RECEIPT_RELATIVE_PATH, receipt_bytes)
    _write(
        repository,
        INDEX_RELATIVE_PATH,
        canonicalize_json(_index_document(repository, receipt_bytes)),
    )


@pytest.fixture
def git_fixture(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
    _archive_source_tree(repository)
    for position, path in enumerate(_BOUND_FILES.values()):
        _write(repository, path, f"bound input {position}\n".encode())
    _commit(repository, "source")
    return repository


def _receipt_and_index(repository: Path) -> tuple[Path, Path]:
    return repository / RECEIPT_RELATIVE_PATH, repository / INDEX_RELATIVE_PATH


def _freeze(repository: Path, mutation: str | None = None) -> tuple[Path, Path]:
    source = _git(repository, "rev-parse", "HEAD")
    _write_receipt_and_index(repository, source)
    receipt_path, index_path = _receipt_and_index(repository)
    if mutation is not None:
        import json

        document = json.loads(receipt_path.read_text(encoding="utf-8"))
        if mutation == "wrong_parent":
            document["search_source_commit"] = "b" * 40
        elif mutation == "placeholder":
            document["search_source_commit"] = "0" * 40
        elif mutation == "bound_digest":
            document["trial_table_sha256"] = "0" * 64
        elif mutation == "dataset_identity":
            document["dataset_archive_sha256"] = "0" * 64
        elif mutation != "receipt_symlink":
            raise AssertionError(f"unexpected mutation {mutation}")
        if mutation != "receipt_symlink":
            receipt_path.write_bytes(canonicalize_json(document))
            _write(
                repository,
                INDEX_RELATIVE_PATH,
                canonicalize_json(_index_document(repository, receipt_path.read_bytes())),
            )
        else:
            _stage_symlink_entry(repository, RECEIPT_RELATIVE_PATH)
    if mutation == "receipt_symlink":
        _commit_staged(repository, "freeze")
        _git(repository, "update-index", "--skip-worktree", str(RECEIPT_RELATIVE_PATH))
    else:
        _commit(repository, "freeze")
    return receipt_path, index_path


def test_preflight_reports_missing_receipt_at_clean_source_head(
    git_fixture: Path,
) -> None:
    receipt, index = _receipt_and_index(git_fixture)

    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_RECEIPT_MISSING",)


def test_preflight_reports_missing_index_before_parsing_a_partial_freeze(
    git_fixture: Path,
) -> None:
    _write(git_fixture, RECEIPT_RELATIVE_PATH, b"{}")
    _commit(git_fixture, "partial freeze")
    receipt, index = _receipt_and_index(git_fixture)

    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_EVIDENCE_INDEX_MISSING",)


def test_preflight_accepts_a_clean_exact_receipt_only_child(git_fixture: Path) -> None:
    receipt, index = _freeze(git_fixture)

    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "PASS"
    assert result.reason_codes == ("SEARCH_FREEZE_PASS",)


def test_preflight_rejects_code_change_between_source_and_freeze(git_fixture: Path) -> None:
    _write(git_fixture, "src/mdcp/temporal/trials.py", b"changed code\n")
    receipt, index = _freeze(git_fixture)

    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_FREEZE_DIFF_NOT_ALLOWLISTED",)


def test_freeze_verifier_rejects_100755_source_tree_entry(git_fixture: Path) -> None:
    _git(git_fixture, "update-index", "--chmod=+x", EXACT_SEARCH_SOURCE_PATHS[0])
    _commit_staged(git_fixture, "wrong source mode")
    receipt, index = _freeze(git_fixture)

    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_MODE_INVALID",)


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        ("wrong_parent", "SEARCH_FREEZE_PARENT_MISMATCH"),
        ("placeholder", "SEARCH_RECEIPT_INVALID"),
        ("bound_digest", "SEARCH_RECEIPT_BOUND_DIGEST_MISMATCH"),
        ("dataset_identity", "SEARCH_RECEIPT_BOUND_DIGEST_MISMATCH"),
    ),
)
def test_preflight_rejects_invalid_receipt_binding(
    git_fixture: Path, mutation: str, expected_code: str
) -> None:
    receipt_path, index_path = _freeze(git_fixture, mutation)

    result = verify_search_freeze(git_fixture, receipt_path, index_path)

    assert result.verdict == "FAIL"
    assert result.reason_codes == (expected_code,)


def test_preflight_rejects_extra_path_in_freeze_child(git_fixture: Path) -> None:
    _write(git_fixture, "evidence/public/v02/search/unexpected.json", b"{}")
    receipt, index = _freeze(git_fixture)

    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_FREEZE_DIFF_NOT_ALLOWLISTED",)


def test_preflight_rejects_symlinked_allowlisted_receipt(git_fixture: Path) -> None:
    receipt, index = _freeze(git_fixture, "receipt_symlink")

    assert _git(git_fixture, "ls-tree", "HEAD", str(RECEIPT_RELATIVE_PATH)).startswith("120000")
    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_FREEZE_PUBLIC_EVIDENCE_NOT_REGULAR",)


def test_preflight_rejects_head_self_reference_when_status_is_clean(git_fixture: Path) -> None:
    receipt, index = _freeze(git_fixture)
    import json

    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["search_source_commit"] = _git(git_fixture, "rev-parse", "HEAD")
    receipt.write_bytes(canonicalize_json(document))
    _write(
        git_fixture,
        INDEX_RELATIVE_PATH,
        canonicalize_json(_index_document(git_fixture, receipt.read_bytes())),
    )
    _git(
        git_fixture,
        "update-index",
        "--skip-worktree",
        str(receipt.relative_to(git_fixture)),
        str(index.relative_to(git_fixture)),
    )

    result = verify_search_freeze(git_fixture, receipt, index)

    assert _git(git_fixture, "status", "--porcelain=v1", "--untracked-files=all") == ""
    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_FREEZE_SELF_REFERENCE",)


def test_preflight_rejects_a_dirty_checkout(git_fixture: Path) -> None:
    receipt, index = _freeze(git_fixture)
    _write(git_fixture, "scratch.txt", b"dirty\n")

    result = verify_search_freeze(git_fixture, receipt, index)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_FREEZE_DIRTY",)


def _archive_source_tree(destination: Path) -> None:
    for logical_path in EXACT_SEARCH_SOURCE_PATHS:
        target = destination / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / logical_path, target)


def test_source_inventory_is_the_exact_ascii_ordered_47_path_closure(tmp_path: Path) -> None:
    archive = tmp_path / "source-archive"
    _archive_source_tree(archive)
    inventory = build_search_source_inventory(archive)

    assert SEARCH_SOURCE_PATHS == EXACT_SEARCH_SOURCE_PATHS
    assert len(inventory) == 47
    assert len(set(EXACT_SEARCH_SOURCE_PATHS)) == 47
    assert tuple(sorted(EXACT_SEARCH_SOURCE_PATHS, key=str.encode)) == EXACT_SEARCH_SOURCE_PATHS
    assert tuple(entry.logical_path for entry in inventory) == EXACT_SEARCH_SOURCE_PATHS
    assert all(entry.git_mode == "100644" for entry in inventory)
    assert all(EXACT_SEARCH_SOURCE_PATHS.count(path) == 1 for path in FORMAL_WORKER_SOURCE_PATHS)
    assert DEDICATED_WORKER_PLAN_PATH in EXACT_SEARCH_SOURCE_PATHS
    assert DEDICATED_WORKER_DESIGN_PATH in EXACT_SEARCH_SOURCE_PATHS
    assert OBSOLETE_FINAL_REVIEW_PLAN_PATH not in EXACT_SEARCH_SOURCE_PATHS
    assert OBSOLETE_FINAL_REVIEW_DESIGN_PATH not in EXACT_SEARCH_SOURCE_PATHS
    assert all(path not in EXACT_SEARCH_SOURCE_PATHS for path in IMPLEMENTATION_TEST_PATHS)
    assert "evidence/public/v02/search/search-receipt.json" not in SEARCH_SOURCE_PATHS
    assert "evidence/public/v02/search/evidence-index.json" not in SEARCH_SOURCE_PATHS


def test_source_archive_is_identical_under_all_three_autocrlf_modes() -> None:
    tar_digests: tuple[str, ...]
    temporary_root: Path
    with tempfile.TemporaryDirectory(prefix="mdcp-task8-source-archive-") as raw_root:
        temporary_root = Path(raw_root).resolve()
        assert not temporary_root.is_relative_to(REPOSITORY_ROOT)
        repository = temporary_root / "repository"
        repository.mkdir()
        _archive_source_tree(repository)
        _git(repository, "init")
        _git(repository, "-c", "core.autocrlf=false", "add", ".")
        _commit_staged(repository, "source fixture")
        profile = temporary_root / "source-archive.attributes"
        profile.write_text(EXTERNAL_ATTRIBUTES_PROFILE, encoding="ascii", newline="")
        assert profile.read_bytes() == EXTERNAL_ATTRIBUTES_PROFILE.encode("ascii")
        assert not (repository / ".gitattributes").exists()

        extracted_roots: list[Path] = []
        digests: list[str] = []
        for mode in ("true", "false", "input"):
            tar_path = temporary_root / f"source-{mode}.tar"
            subprocess.run(
                (
                    "git",
                    "-c",
                    f"core.autocrlf={mode}",
                    "-c",
                    f"core.attributesFile={profile}",
                    "archive",
                    "--format=tar",
                    f"--output={tar_path}",
                    "HEAD",
                ),
                cwd=repository,
                check=True,
                capture_output=True,
            )
            extracted = temporary_root / f"extracted-{mode}"
            extracted.mkdir()
            with tarfile.open(tar_path, mode="r:") as archive:
                archive.extractall(extracted, filter="data")
            assert not (extracted / ".git").exists()
            extracted_roots.append(extracted)
            digests.append(sha256(tar_path.read_bytes()).hexdigest())

        assert len(set(digests)) == 1
        index_path = temporary_root / "external-index.json"
        index_path.write_bytes(canonicalize_json(_index_document(extracted_roots[0], b"receipt")))
        index_anchor = sha256(index_path.read_bytes()).hexdigest()
        for extracted in extracted_roots:
            result = verify_search_source_inventory(extracted, index_path, index_anchor)
            assert result.verdict == "PASS"
            assert result.reason_codes == ("SEARCH_SOURCE_INVENTORY_PASS",)
            assert len(build_search_source_inventory(extracted)) == 47
            for logical_path in CRLF_ARCHIVE_PATHS:
                raw = (extracted / logical_path).read_bytes()
                assert b"\r\n" in raw
                assert raw.replace(b"\r\n", b"").find(b"\n") == -1
            for logical_path in LF_DEDICATED_WORKER_PATHS:
                raw = (extracted / logical_path).read_bytes()
                assert b"\n" in raw
                assert b"\r\n" not in raw
        tar_digests = tuple(digests)

    assert len(set(tar_digests)) == 1
    assert not temporary_root.exists()


def test_source_archive_without_dot_git_requires_an_external_nonzero_index_anchor(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "source-archive"
    _archive_source_tree(archive)
    entries = _independent_source_entries(archive)
    index_path = tmp_path / "evidence-index.json"
    index_path.write_bytes(
        canonicalize_json(
            {
                "schema_version": "mdcp.search-evidence-index.v1",
                "canonicalization_version": "RFC8785",
                "source_entries": entries,
                "source_inventory_sha256": sha256(canonicalize_json(entries)).hexdigest(),
                "private_logical_outputs": [
                    "provisional-winner.json",
                    "qualification-report.json",
                    "ranking-report.json",
                    "replay-report.json",
                    "trial-summary.json",
                ],
                "search_receipt_sha256": "a" * 64,
                "h2_status": "SEALED_NOT_LOADED",
                "h2_loaded_rows": 0,
            }
        )
    )
    expected = sha256(index_path.read_bytes()).hexdigest()

    verified = verify_search_source_inventory(archive, index_path, expected)
    assert verified.verdict == "PASS"
    assert verified.reason_codes == ("SEARCH_SOURCE_INVENTORY_PASS",)
    assert verify_search_source_inventory(archive, index_path, "0" * 64).verdict == "FAIL"
    (archive / "unrelated-regular-file.txt").write_text("ignored", encoding="utf-8")
    assert verify_search_source_inventory(archive, index_path, expected).verdict == "PASS"


def test_source_archive_rejects_a_missing_indexed_file(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "missing-indexed-file")
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"
    (archive / EXACT_SEARCH_SOURCE_PATHS[0]).unlink()

    result = verify_search_source_inventory(
        archive, index_path, sha256(index_path.read_bytes()).hexdigest()
    )

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_FILE_INVALID",)


def test_source_archive_rejects_wrong_eol_bytes(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "wrong-eol")
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"
    target = archive / "src/mdcp/temporal/formal_worker_protocol.py"
    raw = target.read_bytes()
    wrong_eol = raw.replace(b"\r\n", b"\n") if b"\r\n" in raw else raw.replace(b"\n", b"\r\n")
    assert wrong_eol != raw
    target.write_bytes(wrong_eol)

    result = verify_search_source_inventory(
        archive, index_path, sha256(index_path.read_bytes()).hexdigest()
    )

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_INVENTORY_MISMATCH",)


def test_source_archive_verifier_has_no_dot_git_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mdcp.temporal import search_identity

    archive, index_path, document = _fresh_archive_index(tmp_path, "without-dot-git")
    assert not (archive / ".git").exists()
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"

    monkeypatch.setattr(
        search_identity,
        "_git",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("source archive verification must not invoke Git")
        ),
    )

    result = verify_search_source_inventory(
        archive, index_path, sha256(index_path.read_bytes()).hexdigest()
    )

    assert result.verdict == "PASS"
    assert result.reason_codes == ("SEARCH_SOURCE_INVENTORY_PASS",)


def test_source_archive_rejects_an_absent_external_index(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "absent-index")
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"
    external_anchor = sha256(index_path.read_bytes()).hexdigest()
    index_path.unlink()

    result = verify_search_source_inventory(archive, index_path, external_anchor)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_INDEX_ANCHOR_MISMATCH",)


def test_source_archive_rejects_an_indexed_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "indexed-symlink")
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"
    target = archive / EXACT_SEARCH_SOURCE_PATHS[0]
    linked = tmp_path / "linked-source"
    raw = target.read_bytes()
    linked.write_bytes(raw)
    target.unlink()
    try:
        target.symlink_to(linked)
    except OSError:
        target.write_bytes(raw)
        path_type = type(target)
        real_is_symlink = path_type.is_symlink

        def exact_symlink_leaf(path: Path) -> bool:
            return path.absolute() == target.absolute() or real_is_symlink(path)

        monkeypatch.setattr(path_type, "is_symlink", exact_symlink_leaf)

    result = verify_search_source_inventory(
        archive, index_path, sha256(index_path.read_bytes()).hexdigest()
    )

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_FILE_INVALID",)


def test_source_archive_rejects_an_indexed_directory(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "indexed-directory")
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"
    target = archive / EXACT_SEARCH_SOURCE_PATHS[0]
    target.unlink()
    target.mkdir()

    result = verify_search_source_inventory(
        archive, index_path, sha256(index_path.read_bytes()).hexdigest()
    )

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_FILE_INVALID",)


def test_source_archive_rejects_an_indexed_fifo_when_supported(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable on this platform")
    archive, index_path, document = _fresh_archive_index(tmp_path, "indexed-fifo")
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"
    target = archive / EXACT_SEARCH_SOURCE_PATHS[0]
    target.unlink()
    try:
        os.mkfifo(target)
    except OSError as error:
        pytest.skip(f"FIFO creation is unavailable: {type(error).__name__}")

    result = verify_search_source_inventory(
        archive, index_path, sha256(index_path.read_bytes()).hexdigest()
    )

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_FILE_INVALID",)


def test_windows_reparse_attribute_rejects_an_indexed_regular_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name != "nt" or not hasattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT"):
        pytest.skip("Windows reparse attributes are unavailable on this platform")
    from mdcp.temporal import search_identity

    archive, index_path, document = _fresh_archive_index(tmp_path, "indexed-reparse")
    result = _verify_index_document(archive, index_path, document)
    assert result.verdict == "PASS"
    target = archive / EXACT_SEARCH_SOURCE_PATHS[0]
    real_lstat = search_identity.os.lstat
    reparse_calls = 0

    def reparse_lstat(path: str | bytes | os.PathLike[str] | os.PathLike[bytes]):
        nonlocal reparse_calls
        information = real_lstat(path)
        if Path(path).absolute() == target.absolute():
            reparse_calls += 1
            return SimpleNamespace(
                st_mode=information.st_mode,
                st_size=information.st_size,
                st_file_attributes=(
                    information.st_file_attributes | stat.FILE_ATTRIBUTE_REPARSE_POINT
                ),
            )
        return information

    monkeypatch.setattr(search_identity.os, "lstat", reparse_lstat)

    result = verify_search_source_inventory(
        archive, index_path, sha256(index_path.read_bytes()).hexdigest()
    )

    assert reparse_calls >= 1
    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_FILE_INVALID",)


@pytest.mark.parametrize(
    "anchor",
    ("", "0" * 64, "A" * 64, "a" * 63, "b" * 64),
)
def test_source_archive_verifier_rejects_missing_malformed_or_mismatched_anchor(
    tmp_path: Path, anchor: str
) -> None:
    archive = tmp_path / "source-archive"
    _archive_source_tree(archive)
    entries = _independent_source_entries(archive)
    index_path = tmp_path / "evidence-index.json"
    index_path.write_bytes(
        canonicalize_json(
            {
                "schema_version": "mdcp.search-evidence-index.v1",
                "canonicalization_version": "RFC8785",
                "source_entries": entries,
                "source_inventory_sha256": sha256(canonicalize_json(entries)).hexdigest(),
                "private_logical_outputs": [
                    "provisional-winner.json",
                    "qualification-report.json",
                    "ranking-report.json",
                    "replay-report.json",
                    "trial-summary.json",
                ],
                "search_receipt_sha256": "a" * 64,
                "h2_status": "SEALED_NOT_LOADED",
                "h2_loaded_rows": 0,
            }
        )
    )

    assert verify_search_source_inventory(archive, index_path, anchor).verdict == "FAIL"


def test_source_archive_rejects_coordinated_source_and_index_mutation(tmp_path: Path) -> None:
    archive = tmp_path / "source-archive"
    _archive_source_tree(archive)
    index_path = tmp_path / "evidence-index.json"
    entries = _independent_source_entries(archive)
    document = {
        "schema_version": "mdcp.search-evidence-index.v1",
        "canonicalization_version": "RFC8785",
        "source_entries": entries,
        "source_inventory_sha256": sha256(canonicalize_json(entries)).hexdigest(),
        "private_logical_outputs": [
            "provisional-winner.json",
            "qualification-report.json",
            "ranking-report.json",
            "replay-report.json",
            "trial-summary.json",
        ],
        "search_receipt_sha256": "a" * 64,
        "h2_status": "SEALED_NOT_LOADED",
        "h2_loaded_rows": 0,
    }
    index_path.write_bytes(canonicalize_json(document))
    external_anchor = sha256(index_path.read_bytes()).hexdigest()
    target = archive / EXACT_SEARCH_SOURCE_PATHS[0]
    target.write_bytes(b"coordinated mutation")
    document["source_entries"][0]["byte_size"] = len(target.read_bytes())
    document["source_entries"][0]["sha256"] = sha256(target.read_bytes()).hexdigest()
    document["source_inventory_sha256"] = sha256(
        canonicalize_json(document["source_entries"])
    ).hexdigest()
    index_path.write_bytes(canonicalize_json(document))

    assert verify_search_source_inventory(archive, index_path, external_anchor).verdict == "FAIL"


def test_prepare_search_freeze_rejects_a_clean_non_100644_source_mode(tmp_path: Path) -> None:
    archive = tmp_path / "source-repository"
    archive.mkdir()
    _archive_source_tree(archive)
    _git(archive, "init")
    _commit(archive, "source")
    _git(archive, "update-index", "--chmod=+x", EXACT_SEARCH_SOURCE_PATHS[0])
    _commit_staged(archive, "wrong source mode")

    with pytest.raises(ValueError, match="^SEARCH_SOURCE_MODE_INVALID$"):
        prepare_search_freeze(archive, datetime(2026, 8, 26, 12, 0, tzinfo=UTC))


def test_freeze_verifier_rejects_a_120000_blob_in_the_47_path_source_tree(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "source-repository"
    repository.mkdir()
    _archive_source_tree(repository)
    _git(repository, "init")
    _commit(repository, "regular source")
    linked_source_path = "src/mdcp/temporal/trials.py"
    _stage_120000_blob(repository, linked_source_path)
    source_commit = _commit_staged(repository, "120000 source")
    _git(repository, "update-index", "--skip-worktree", linked_source_path)
    _write_receipt_and_index(repository, source_commit)
    receipt_path, index_path = _receipt_and_index(repository)
    _git(repository, "add", str(receipt_path), str(index_path))
    _commit_staged(repository, "freeze")

    result = verify_search_freeze(repository, receipt_path, index_path)

    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""
    assert _git(repository, "ls-tree", "HEAD", "--", linked_source_path).startswith("120000 blob ")
    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_MODE_INVALID",)


def test_prepare_bytes_are_accepted_by_the_final_freeze_verifier(tmp_path: Path) -> None:
    repository = tmp_path / "source-repository"
    repository.mkdir()
    _archive_source_tree(repository)
    _git(repository, "init")
    _commit(repository, "source")
    prepare_search_freeze(repository, datetime(2026, 8, 26, 12, 0, tzinfo=UTC))
    _commit(repository, "freeze")

    result = verify_search_freeze(
        repository,
        repository / RECEIPT_RELATIVE_PATH,
        repository / INDEX_RELATIVE_PATH,
    )

    assert result.verdict == "PASS"


def test_source_index_rejects_a_wrong_git_mode(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "wrong-mode")
    _source_entries(document)[0]["git_mode"] = "100755"

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    (("byte_size", 0), ("sha256", "0" * 64)),
    ids=("wrong-size", "wrong-digest"),
)
def test_source_index_rejects_wrong_file_identity(
    tmp_path: Path, field: str, wrong_value: object
) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, field)
    _source_entries(document)[0][field] = wrong_value

    result = _verify_index_document(archive, index_path, document)

    assert result.verdict == "FAIL"
    assert result.reason_codes == ("SEARCH_SOURCE_INVENTORY_MISMATCH",)


def test_source_index_rejects_reordered_source_entries(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "reordered")
    entries = _source_entries(document)
    entries[0], entries[1] = entries[1], entries[0]

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


def test_source_index_rejects_the_transitional_43_path_inventory(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "transitional-43")
    entries = _source_entries(document)
    entries[:] = [
        entry for entry in entries if entry["logical_path"] not in FORMAL_WORKER_SOURCE_PATHS
    ]
    substitutions = {
        DEDICATED_WORKER_PLAN_PATH: OBSOLETE_FINAL_REVIEW_PLAN_PATH,
        DEDICATED_WORKER_DESIGN_PATH: OBSOLETE_FINAL_REVIEW_DESIGN_PATH,
    }
    for current_path, obsolete_path in substitutions.items():
        position = next(
            index for index, entry in enumerate(entries) if entry["logical_path"] == current_path
        )
        raw = (REPOSITORY_ROOT / obsolete_path).read_bytes()
        _write(archive, obsolete_path, raw)
        entries[position] = {
            "logical_path": obsolete_path,
            "git_mode": "100644",
            "byte_size": len(raw),
            "sha256": sha256(raw).hexdigest(),
        }
    entries.sort(key=lambda entry: str(entry["logical_path"]).encode())
    assert len(entries) == 43

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


@pytest.mark.parametrize(
    "omitted_path",
    (DEDICATED_WORKER_DESIGN_PATH, DEDICATED_WORKER_PLAN_PATH),
    ids=("dedicated-worker-design", "dedicated-worker-plan"),
)
def test_source_index_rejects_one_exact_required_document_omission(
    tmp_path: Path, omitted_path: str
) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, Path(omitted_path).stem)
    entries = _source_entries(document)
    position = EXACT_SEARCH_SOURCE_PATHS.index(omitted_path)
    del entries[position]
    assert len(entries) == 46
    assert omitted_path not in (entry["logical_path"] for entry in entries)

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


def test_source_index_rejects_test_path_substitution(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "test-substitution")
    raw = (REPOSITORY_ROOT / EXTRA_TEST_PATH).read_bytes()
    _write(archive, EXTRA_TEST_PATH, raw)
    entries = _source_entries(document)
    entries[-1] = {
        "logical_path": EXTRA_TEST_PATH,
        "git_mode": "100644",
        "byte_size": len(raw),
        "sha256": sha256(raw).hexdigest(),
    }
    assert len(entries) == 47

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


@pytest.mark.parametrize(
    "extra_path",
    (
        EXTRA_TEST_PATH,
        RECEIPT_RELATIVE_PATH.as_posix(),
        INDEX_RELATIVE_PATH.as_posix(),
    ),
    ids=("extra-test-path", "extra-search-receipt", "extra-evidence-index"),
)
def test_source_index_rejects_each_extra_forbidden_entry(tmp_path: Path, extra_path: str) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, Path(extra_path).stem)
    raw = f"extra entry for {extra_path}\n".encode()
    _write(archive, extra_path, raw)
    entries = _source_entries(document)
    entries.append(
        {
            "logical_path": extra_path,
            "git_mode": "100644",
            "byte_size": len(raw),
            "sha256": sha256(raw).hexdigest(),
        }
    )
    assert len(entries) == 48

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


def test_source_index_rejects_a_duplicate_entry_addition(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "duplicate")
    entries = _source_entries(document)
    entries.append(dict(entries[0]))
    assert len(entries) == 48

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


def test_source_index_rejects_an_unknown_path_substitution(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "unknown")
    entries = _source_entries(document)
    original = archive / EXACT_SEARCH_SOURCE_PATHS[-1]
    _write(archive, "unlisted.txt", original.read_bytes())
    entries[-1]["logical_path"] = "unlisted.txt"
    assert len(entries) == 47

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


@pytest.mark.parametrize(
    "mutation",
    ("missing", "extra", "duplicate", "order"),
)
def test_source_index_rejects_each_private_output_mutation(tmp_path: Path, mutation: str) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, f"private-{mutation}")
    outputs = document["private_logical_outputs"]
    assert isinstance(outputs, list)
    if mutation == "missing":
        del outputs[-1]
    elif mutation == "extra":
        outputs.append("extra.json")
    elif mutation == "duplicate":
        outputs.append(outputs[0])
    else:
        outputs[0], outputs[1] = outputs[1], outputs[0]

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


def test_source_index_rejects_a_pre_run_private_output_digest(tmp_path: Path) -> None:
    archive, index_path, document = _fresh_archive_index(tmp_path, "pre-run-digest")
    document["private_output_sha256"] = "a" * 64

    _assert_index_invalid(_verify_index_document(archive, index_path, document))


@pytest.mark.parametrize("existing", (RECEIPT_RELATIVE_PATH, INDEX_RELATIVE_PATH))
def test_prepare_search_freeze_refuses_each_preexisting_output(
    tmp_path: Path, existing: Path
) -> None:
    repository = tmp_path / existing.name
    repository.mkdir()
    _archive_source_tree(repository)
    _git(repository, "init")
    _commit(repository, "source")
    preexisting_bytes = f"preexisting {existing.name}\n".encode()
    _write(repository, existing, preexisting_bytes)
    _commit(repository, "existing output")
    other = INDEX_RELATIVE_PATH if existing == RECEIPT_RELATIVE_PATH else RECEIPT_RELATIVE_PATH

    with pytest.raises(ValueError, match="^SEARCH_FREEZE_OUTPUT_EXISTS$"):
        prepare_search_freeze(repository, datetime(2026, 8, 26, 12, 0, tzinfo=UTC))

    assert (repository / existing).read_bytes() == preexisting_bytes
    assert not (repository / other).exists()


def test_prepare_search_freeze_preserves_both_preexisting_outputs(tmp_path: Path) -> None:
    repository = tmp_path / "both-preexisting"
    repository.mkdir()
    _archive_source_tree(repository)
    _git(repository, "init")
    _commit(repository, "source")
    expected = {
        RECEIPT_RELATIVE_PATH: b"preexisting receipt\n",
        INDEX_RELATIVE_PATH: b"preexisting index\n",
    }
    for relative_path, raw in expected.items():
        _write(repository, relative_path, raw)
    _commit(repository, "both existing outputs")

    with pytest.raises(ValueError, match="^SEARCH_FREEZE_OUTPUT_EXISTS$"):
        prepare_search_freeze(repository, datetime(2026, 8, 26, 12, 0, tzinfo=UTC))

    assert {
        relative_path: (repository / relative_path).read_bytes() for relative_path in expected
    } == expected
