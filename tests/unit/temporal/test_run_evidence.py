from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import mdcp.temporal.run_evidence as run_evidence
from mdcp.common.canonical import canonicalize_json
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
    """A hand-authored closed inventory; changing any inventory guard must fail this test."""
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
    trials = [
        {
            "trial_id": f"TRIAL-{number:02d}",
            "selection_fit_count": 4,
            "folds": folds,
        }
        for number in range(1, 21)
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
        "trials": trials,
    }


def mutate(document: dict[str, object], mutation: str) -> dict[str, object]:
    """Return one deliberately untrusted mutation without using publisher code."""
    result = json.loads(json.dumps(document))
    if mutation == "extra_key":
        result["unexpected"] = True
    elif mutation == "unknown_metric":
        result["trials"][0]["folds"][0]["metrics"]["unknown"] = 1.0
    elif mutation == "nan":
        result["trials"][0]["folds"][0]["metrics"]["ucb95"] = float("nan")
    elif mutation == "uppercase_digest":
        result["result_sha256"] = "A" * 64
    elif mutation == "short_digest":
        result["result_sha256"] = "a" * 63
    elif mutation == "private_path":
        result["private_path"] = "C:/private/model.bin"
    elif mutation == "raw_timestamp":
        result["created_at_utc"] = "2026-08-25T12:00:00Z"
    elif mutation == "traceback":
        result["traceback"] = "Traceback (most recent call last):"
    elif mutation == "credential":
        result["credential"] = "Bearer " + "a" * 32
    elif mutation == "raw_prediction":
        result["raw_prediction"] = [0.1]
    else:
        raise AssertionError(f"unhandled mutation: {mutation}")
    return result


def write_raw_result(tmp_path: Path, document: dict[str, object]) -> Path:
    """Write adversarial bytes directly, never through the trusted publisher."""
    path = tmp_path / "untrusted-result.json"
    path.write_text(json.dumps(document, allow_nan=True), encoding="utf-8")
    return path


def synthetic_private_bundle() -> PrivateRunBundle:
    """Two canonical private logical files with no time, environment, or entropy source."""
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


@pytest.mark.parametrize(
    "mutation",
    [
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
    ],
)
def test_public_result_fails_closed(tmp_path: Path, mutation: str) -> None:
    document = mutate(valid_public_result(), mutation)
    path = write_raw_result(tmp_path, document)

    assert verify_development_result(path).verdict == "FAIL"


def test_valid_closed_public_result_verifies_only_when_schema_and_bytes_are_canonical(
    tmp_path: Path,
) -> None:
    result = PublicDevelopmentResult.model_validate(valid_public_result())
    path = tmp_path / "result.json"
    path.write_bytes(canonicalize_json(result.model_dump(mode="json")))

    assert verify_development_result(path).verdict == "PASS"


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_private_bundle_public_identity_contains_no_private_material(tmp_path: Path) -> None:
    identity = write_synthetic_bundle_no_clobber(tmp_path / "new-run", synthetic_private_bundle())

    assert set(identity.model_dump()) == {
        "file_count",
        "total_bytes",
        "inventory_sha256",
        "manifest_sha256",
    }
    assert public_evidence_violations(identity.model_dump(mode="json")) == ()


@pytest.mark.parametrize(
    "setup",
    ["existing_destination", "partial_destination", "symlink_destination"],
)
@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_private_writer_rejects_existing_or_linked_destination(tmp_path: Path, setup: str) -> None:
    destination = tmp_path / "new-run"
    if setup == "existing_destination":
        destination.mkdir()
    elif setup == "partial_destination":
        destination.mkdir()
        (destination / "partial.json").write_text("{}", encoding="utf-8")
    else:
        target = tmp_path / "linked-target"
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
                pytest.skip("the platform cannot create a link in pytest tmp_path")

    with pytest.raises(ValueError) as error:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert str(error.value) == "DESTINATION_EXISTS"


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_private_writer_requires_a_precreated_nonlinked_parent(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as error:
        write_synthetic_bundle_no_clobber(
            tmp_path / "missing" / "new-run", synthetic_private_bundle()
        )

    assert str(error.value) == "TRUSTED_PARENT_REQUIRED"


def test_private_writer_rejects_duplicate_logical_paths_without_echoing_them(
    tmp_path: Path,
) -> None:
    source = synthetic_private_bundle()
    duplicate = PrivateRunBundle(
        evidence_class="synthetic_test",
        files=(source.files[0], source.files[0]),
    )

    with pytest.raises(ValueError) as error:
        write_synthetic_bundle_no_clobber(tmp_path / "new-run", duplicate)

    assert str(error.value) == "DUPLICATE_LOGICAL_PATH"
    assert source.files[0].logical_path not in str(error.value)


def test_private_writer_rejects_noncanonical_bytes(tmp_path: Path) -> None:
    bundle = PrivateRunBundle(
        evidence_class="synthetic_test",
        files=(
            PrivateFoldEvidence(
                logical_path="private/folds/F1.json", canonical_bytes=b'{"b":1,"a":2}'
            ),
        ),
    )

    with pytest.raises(ValueError) as error:
        write_synthetic_bundle_no_clobber(tmp_path / "new-run", bundle)

    assert str(error.value) == "NONCANONICAL_PRIVATE_BYTES"


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_private_writer_rejects_second_publication(tmp_path: Path) -> None:
    destination = tmp_path / "new-run"
    write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    with pytest.raises(ValueError) as error:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert str(error.value) == "DESTINATION_EXISTS"


def test_private_writer_rejects_natural_development_without_permit(tmp_path: Path) -> None:
    source = synthetic_private_bundle()
    natural = PrivateRunBundle(evidence_class="natural_development", files=source.files)

    with pytest.raises(ValueError) as error:
        write_synthetic_bundle_no_clobber(tmp_path / "new-run", natural)

    assert str(error.value) == "FORMAL_RUN_PERMIT_REQUIRED"


@pytest.mark.parametrize(
    "logical_path",
    [
        "private/CON.json",
        "private/CON .json",
        "private/com1.payload",
        "private/LPT9",
        "private/a:.json",
        "private/x.",
        "private/x ",
    ],
)
def test_private_logical_paths_reject_windows_aliases(logical_path: str) -> None:
    with pytest.raises(ValueError, match="LOGICAL_PATH_INVALID"):
        PrivateFoldEvidence(logical_path=logical_path, canonical_bytes=b"{}")


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("trials.0.folds.0.metrics.row_count", True),
        ("selection_fit_count", True),
        ("h2_loaded_rows", False),
    ],
)
def test_public_result_rejects_boolean_numeric_coercion(path: str, value: bool) -> None:
    document = valid_public_result()
    if path in {"selection_fit_count", "h2_loaded_rows"}:
        document[path] = value
    else:
        document["trials"][0]["folds"][0]["metrics"]["row_count"] = value

    with pytest.raises(ValueError):
        PublicDevelopmentResult.model_validate(document)


def test_verifier_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_bytes(b'{"schema_version":"one","schema_version":"two"}')

    assert verify_development_result(path).verdict == "FAIL"


def test_canonical_public_result_bytes_returns_rfc8785_bytes() -> None:
    result = PublicDevelopmentResult.model_validate(valid_public_result())

    assert canonical_public_result_bytes(result) == canonicalize_json(
        result.model_dump(mode="json")
    )


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_private_writer_cleans_staging_after_raced_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "new-run"
    original_publish = run_evidence._windows_rename_noreplace

    def race(staging_handle: int, target: Path) -> None:
        target.mkdir()
        original_publish(staging_handle, target)

    monkeypatch.setattr(run_evidence, "_windows_rename_noreplace", race)

    with pytest.raises(ValueError, match="^DESTINATION_EXISTS$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert destination.is_dir()
    assert not (tmp_path / ".new-run.staging").exists()


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_writer_does_not_fall_back_to_path_based_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_path_rename(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("path-based rename is not an approved publication primitive")

    monkeypatch.setattr(run_evidence.os, "rename", forbidden_path_rename)

    identity = write_synthetic_bundle_no_clobber(tmp_path / "new-run", synthetic_private_bundle())

    assert identity.file_count == 2
    assert (tmp_path / "new-run" / "manifest.json").is_file()


def test_posix_publication_is_unsupported_without_filesystem_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "new-run"
    staging = tmp_path / ".new-run.staging"
    monkeypatch.setattr(
        run_evidence,
        "_publication_platform",
        lambda: "posix",
        raising=False,
    )

    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert str(caught.value) == "PUBLICATION_UNSUPPORTED"
    assert caught.value.__cause__ is None
    assert not destination.exists()
    assert not staging.exists()
    assert tuple(tmp_path.iterdir()) == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows protected-handle semantics")
def test_windows_holds_parent_and_staging_against_replacement_until_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trusted_parent = tmp_path / "trusted"
    trusted_parent.mkdir()
    destination = trusted_parent / "new-run"
    staging = trusted_parent / ".new-run.staging"
    original = run_evidence._windows_rename_noreplace

    def probe(staging_handle: int, target: Path) -> None:
        with pytest.raises(OSError):
            os.rename(trusted_parent, tmp_path / "redirected-parent")
        with pytest.raises(OSError):
            os.rename(staging, trusted_parent / "redirected-staging")
        original(staging_handle, target)

    monkeypatch.setattr(run_evidence, "_windows_rename_noreplace", probe)

    write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert destination.is_dir()
    assert not staging.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows protected-handle semantics")
def test_windows_cleans_owned_staging_after_file_flush_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "new-run"
    staging = tmp_path / ".new-run.staging"
    original_flush = run_evidence._windows_flush
    calls = 0

    def fail_first_file_flush(handle: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            raise OSError("sensitive path")
        original_flush(handle)

    monkeypatch.setattr(run_evidence, "_windows_flush", fail_first_file_flush)

    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert str(caught.value) == "PUBLICATION_FAILED"
    assert not staging.exists()


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_private_writer_rejects_linked_ancestor_without_touching_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "linked-target"
    target.mkdir()
    linked_parent = tmp_path / "linked-parent"
    completed = subprocess.run(
        ("cmd", "/c", "mklink", "/J", str(linked_parent), str(target)),
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0

    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(linked_parent / "new-run", synthetic_private_bundle())

    assert str(caught.value) == "TRUSTED_PARENT_REQUIRED"
    assert tuple(target.iterdir()) == ()


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_preexisting_staging_link_is_not_cleaned_as_owned(tmp_path: Path) -> None:
    target = tmp_path / "attacker-owned"
    target.mkdir()
    sentinel = target / "sentinel.json"
    sentinel.write_text("{}", encoding="utf-8")
    staging = tmp_path / ".new-run.staging"
    completed = subprocess.run(
        ("cmd", "/c", "mklink", "/J", str(staging), str(target)),
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0

    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(tmp_path / "new-run", synthetic_private_bundle())

    assert str(caught.value) == "STAGING_EXISTS"
    assert sentinel.read_text(encoding="utf-8") == "{}"


@pytest.mark.parametrize("name", ["CON", "run.", "run ", "run:stream"])
def test_private_writer_rejects_windows_alias_destination_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(tmp_path / name, synthetic_private_bundle())

    assert str(caught.value) == "TRUSTED_PARENT_REQUIRED"
    assert tuple(tmp_path.iterdir()) == ()


def test_private_model_validation_does_not_echo_sensitive_input() -> None:
    sensitive_path = "private/CON .secret.json"

    with pytest.raises(ValueError) as caught:
        PrivateFoldEvidence(logical_path=sensitive_path, canonical_bytes=b"{}")

    assert sensitive_path not in str(caught.value)


def test_private_identity_rejects_boolean_counts_without_echoing_input() -> None:
    with pytest.raises(ValueError) as caught:
        PrivateBundleIdentity(
            file_count=True,
            total_bytes=2,
            inventory_sha256="a" * 64,
            manifest_sha256="b" * 64,
        )

    assert "True" not in str(caught.value)


@pytest.mark.skipif(os.name != "nt", reason="Windows atomic directory-create semantics")
def test_windows_normal_directory_swap_cannot_redirect_bundle_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_create = run_evidence._windows_nt_create_relative
    owned_paths: dict[int, Path] = {}
    swaps = 0
    denied_moves = 0

    def swap_after_create(
        parent_handle: int,
        name: str,
        is_directory: bool,
        share_mode: int,
    ) -> tuple[int | None, tuple[int, int, int] | None, int]:
        nonlocal denied_moves, swaps
        result = original_create(parent_handle, name, is_directory, share_mode)
        handle, _, _ = result
        if handle is None or not is_directory:
            return result
        path = owned_paths.get(parent_handle, tmp_path) / name
        assert path.is_dir()
        displaced = path.parent / f".invocation-owned-{swaps}"
        try:
            os.rename(path, displaced)
        except OSError:
            denied_moves += 1
            owned_paths[handle] = path
            return result
        swaps += 1
        owned_paths[handle] = displaced
        path.mkdir()
        (path / "attacker-sentinel.json").write_text("{}", encoding="utf-8")
        return result

    monkeypatch.setattr(
        run_evidence,
        "_windows_nt_create_relative",
        swap_after_create,
    )

    destination = tmp_path / "new-run"
    staging = tmp_path / ".new-run.staging"
    write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert swaps == 0
    assert denied_moves == 3
    assert not staging.exists()
    assert (destination / "private" / "folds" / "F1.json").read_bytes() == (
        b'{"fold_id":"F1","rows":[1,2]}'
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows delete-sharing semantics")
def test_windows_live_file_handle_denies_private_byte_displacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_create = run_evidence._windows_nt_create_relative
    original_flush = run_evidence._windows_flush
    owned_paths: dict[int, Path] = {}
    escaped = tmp_path / "escaped-private.json"
    move_denied = False
    move_attempted = False

    def attempt_file_move(
        parent_handle: int,
        name: str,
        is_directory: bool,
        share_mode: int,
    ) -> tuple[int | None, tuple[int, int, int] | None, int]:
        result = original_create(parent_handle, name, is_directory, share_mode)
        handle, _, _ = result
        if handle is None:
            return result
        path = owned_paths.get(parent_handle, tmp_path) / name
        owned_paths[handle] = path
        return result

    def attempt_move_before_layout_seal(handle: int) -> None:
        nonlocal move_attempted, move_denied
        path = owned_paths.get(handle)
        if path is not None and path.name == "F2.json" and not move_attempted:
            move_attempted = True
            first_file = path.with_name("F1.json")
            assert first_file.is_file()
            try:
                os.rename(first_file, escaped)
            except OSError:
                move_denied = True
        original_flush(handle)

    monkeypatch.setattr(
        run_evidence,
        "_windows_nt_create_relative",
        attempt_file_move,
    )
    monkeypatch.setattr(run_evidence, "_windows_flush", attempt_move_before_layout_seal)

    destination = tmp_path / "new-run"
    publication_error: ValueError | None = None
    try:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    except ValueError as error:
        publication_error = error

    assert not escaped.exists()
    assert publication_error is None
    assert move_attempted and move_denied
    assert (destination / "private" / "folds" / "F1.json").read_bytes() == (
        b'{"fold_id":"F1","rows":[1,2]}'
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows identity-bound cleanup semantics")
def test_windows_cleanup_does_not_delete_attacker_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "new-run"
    staging = tmp_path / ".new-run.staging"
    replacement = b'{"attacker":true}'
    stolen = tmp_path / "stolen-F1.json"
    original_publish = run_evidence._windows_rename_noreplace

    def replace_before_cleanup(staging_handle: int, target: Path) -> None:
        source = staging / "private" / "folds" / "F1.json"
        os.rename(source, stolen)
        source.write_bytes(replacement)
        target.mkdir()
        original_publish(staging_handle, target)

    monkeypatch.setattr(
        run_evidence,
        "_windows_rename_noreplace",
        replace_before_cleanup,
    )

    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert str(caught.value) == "PUBLICATION_FAILED"
    assert (staging / "private" / "folds" / "F1.json").read_bytes() == replacement
    assert stolen.is_file()


@pytest.mark.skipif(os.name != "nt", reason="Windows identity-bound cleanup semantics")
def test_windows_cleanup_delete_failure_is_terminal_and_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "new-run"
    staging = tmp_path / ".new-run.staging"
    original_publish = run_evidence._windows_rename_noreplace

    def collide(staging_handle: int, target: Path) -> None:
        target.mkdir()
        original_publish(staging_handle, target)

    monkeypatch.setattr(run_evidence, "_windows_rename_noreplace", collide)
    monkeypatch.setattr(
        run_evidence,
        "_windows_set_delete_disposition",
        lambda _handle: False,
        raising=False,
    )

    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert str(caught.value) == "PUBLICATION_FAILED"
    assert staging.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows identity-bound cleanup semantics")
def test_windows_cleanup_flush_failure_is_terminal_and_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "new-run"
    original_publish = run_evidence._windows_rename_noreplace
    original_flush = run_evidence._windows_flush
    cleanup_started = False

    def collide(staging_handle: int, target: Path) -> None:
        nonlocal cleanup_started
        target.mkdir()
        try:
            original_publish(staging_handle, target)
        finally:
            cleanup_started = True

    def fail_cleanup_flush(handle: int) -> None:
        if cleanup_started:
            raise run_evidence._PublicationError("PUBLICATION_FAILED")
        original_flush(handle)

    monkeypatch.setattr(run_evidence, "_windows_rename_noreplace", collide)
    monkeypatch.setattr(run_evidence, "_windows_flush", fail_cleanup_flush)

    with pytest.raises(ValueError) as caught:
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert str(caught.value) == "PUBLICATION_FAILED"
