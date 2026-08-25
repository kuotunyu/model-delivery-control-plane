from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from mdcp.common.canonical import canonicalize_json
from mdcp.temporal.search_identity import (
    SearchIdentityInputs,
    build_search_receipt,
    verify_search_freeze,
)

RECEIPT_RELATIVE_PATH = Path("evidence/public/v02/search/search-receipt.json")
INDEX_RELATIVE_PATH = Path("evidence/public/v02/search/evidence-index.json")
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


def _write_receipt_and_index(repository: Path, source_commit: str) -> None:
    receipt_bytes = _receipt_document(repository, source_commit)
    _write(repository, RECEIPT_RELATIVE_PATH, receipt_bytes)
    _write(
        repository,
        INDEX_RELATIVE_PATH,
        canonicalize_json(
            {
                "schema_version": "mdcp.search-evidence-index.v1",
                "search_receipt_sha256": sha256(receipt_bytes).hexdigest(),
                "entries": [],
            }
        ),
    )


@pytest.fixture
def git_fixture(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
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
                canonicalize_json(
                    {
                        "schema_version": "mdcp.search-evidence-index.v1",
                        "search_receipt_sha256": sha256(receipt_path.read_bytes()).hexdigest(),
                        "entries": [],
                    }
                ),
            )
        else:
            _stage_symlink_entry(repository, RECEIPT_RELATIVE_PATH)
    if mutation == "receipt_symlink":
        _commit_staged(repository, "freeze")
        _git(repository, "update-index", "--skip-worktree", str(RECEIPT_RELATIVE_PATH))
    else:
        _commit(repository, "freeze")
    return receipt_path, index_path


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
        canonicalize_json(
            {
                "schema_version": "mdcp.search-evidence-index.v1",
                "search_receipt_sha256": sha256(receipt.read_bytes()).hexdigest(),
                "entries": [],
            }
        ),
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
