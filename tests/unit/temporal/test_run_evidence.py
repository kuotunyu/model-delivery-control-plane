from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mdcp.common.canonical import canonicalize_json
from mdcp.temporal.evidence import public_evidence_violations
from mdcp.temporal.run_evidence import (
    PrivateFoldEvidence,
    PrivateRunBundle,
    PublicDevelopmentResult,
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
