from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import unicodedata
from pathlib import Path

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
    with pytest.raises(ValueError, match="^FORMAL_RUN_PERMIT_REQUIRED$"):
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


def test_posix_publication_is_unsupported_before_path_work_or_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run_evidence, "_publication_platform", lambda: "posix")
    monkeypatch.setattr(
        run_evidence,
        "_absolute_destination",
        lambda _path: pytest.fail("POSIX dispatch reached destination oracle"),
    )
    with pytest.raises(ValueError, match="^PUBLICATION_UNSUPPORTED$") as caught:
        write_synthetic_bundle_no_clobber(
            tmp_path / "new.container.json", synthetic_private_bundle()
        )
    assert caught.value.__cause__ is None
    assert tuple(tmp_path.iterdir()) == ()


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


def _raw_invalid_destinations(tmp_path: Path) -> tuple[Path, ...]:
    decomposed = unicodedata.normalize("NFD", "café")
    return (
        tmp_path / "SHORT~1" / "bundle.json",
        tmp_path / "bundle.",
        tmp_path / "bundle ",
        *(tmp_path / name for name in ("CON", "PRN", "AUX", "NUL")),
        *(tmp_path / f"COM{number}" for number in range(1, 10)),
        *(tmp_path / f"LPT{number}" for number in range(1, 10)),
        tmp_path / "bundle:stream",
        Path(r"\\server\share\bundle.json"),
        Path(r"\\?\C:\bundle.json"),
        Path(r"\\.\C:\bundle.json"),
        Path("relative.container.json"),
        tmp_path / ".." / "bundle.json",
        tmp_path / decomposed / "bundle.json",
    )


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_windows_raw_destination_oracle_rejects_aliases_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        run_evidence,
        "_publish_windows_container",
        lambda *_args: (_ for _ in ()).throw(AssertionError("destination oracle bypassed")),
    )
    for destination in _raw_invalid_destinations(tmp_path):
        before = tuple(tmp_path.iterdir())
        with pytest.raises(ValueError, match="^TRUSTED_PARENT_REQUIRED$") as caught:
            write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
        assert str(destination) not in str(caught.value)
        assert tuple(tmp_path.iterdir()) == before


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
@pytest.mark.parametrize(
    "raw_case",
    ("dot", "forward_slash", "unicode_drive", "missing_state", "malformed_state"),
)
def test_windows_raw_spelling_is_rejected_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw_case: str
) -> None:
    if raw_case == "dot":
        destination = Path(str(tmp_path) + r"\.\bundle.container.json")
    elif raw_case == "forward_slash":
        destination = Path(tmp_path.as_posix() + "/bundle.container.json")
    elif raw_case == "unicode_drive":
        destination = Path(r"Ｃ:\root\bundle.container.json")
    else:
        destination = tmp_path / "bundle.container.json"
        destination._raw_paths = None if raw_case == "missing_state" else [str(tmp_path), 7]

    monkeypatch.setattr(
        run_evidence,
        "_publish_windows_container",
        lambda *_args: (_ for _ in ()).throw(AssertionError("destination oracle bypassed")),
    )
    before = tuple(tmp_path.iterdir())
    with pytest.raises(ValueError, match="^TRUSTED_PARENT_REQUIRED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert tuple(tmp_path.iterdir()) == before


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
@pytest.mark.parametrize("raw_case", ("repeated_separator", "rooted_fragment", "drive_fragment"))
def test_windows_raw_fragments_cannot_reset_or_hide_empty_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw_case: str
) -> None:
    if raw_case == "repeated_separator":
        destination = Path(str(tmp_path) + r"\\repeated\bundle.container.json")
    elif raw_case == "rooted_fragment":
        destination = tmp_path / Path(r"\reset\bundle.container.json")
    else:
        destination = tmp_path / Path(f"{tmp_path.drive}\\reset\\bundle.container.json")

    monkeypatch.setattr(
        run_evidence,
        "_publish_windows_container",
        lambda *_args: (_ for _ in ()).throw(AssertionError("destination oracle bypassed")),
    )
    before = tuple(tmp_path.iterdir())
    with pytest.raises(ValueError, match="^TRUSTED_PARENT_REQUIRED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert tuple(tmp_path.iterdir()) == before


@pytest.mark.skipif(os.name != "nt", reason="publication is supported only on Windows")
def test_windows_uses_exact_relative_create_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[bool, int, int, int]] = []
    original = run_evidence._windows_nt_relative_file

    def inspect(
        parent_handle: int,
        name: str,
        is_directory: bool,
        desired_access: int,
        share_mode: int,
        create_disposition: int,
        create_options: int,
    ) -> tuple[int | None, tuple[int, int, int] | None, int]:
        calls.append((is_directory, share_mode, create_disposition, create_options))
        return original(
            parent_handle,
            name,
            is_directory,
            desired_access,
            share_mode,
            create_disposition,
            create_options,
        )

    monkeypatch.setattr(run_evidence, "_windows_nt_relative_file", inspect)
    destination = tmp_path / "bundle.container.json"
    write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    directory_options = (
        run_evidence._WINDOWS_FILE_DIRECTORY_FILE
        | run_evidence._WINDOWS_FILE_OPEN_REPARSE_POINT
        | run_evidence._WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT
    )
    final_options = (
        run_evidence._WINDOWS_FILE_NON_DIRECTORY_FILE
        | run_evidence._WINDOWS_FILE_WRITE_THROUGH
        | run_evidence._WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT
    )
    assert calls[-1] == (
        False,
        0,
        run_evidence._WINDOWS_FILE_CREATE,
        final_options,
    )
    assert all(
        call[1:]
        == (
            run_evidence._WINDOWS_FILE_SHARE_READ_WRITE,
            run_evidence._WINDOWS_FILE_OPEN,
            directory_options,
        )
        for call in calls[:-1]
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows protected-handle semantics")
def test_windows_retains_no_delete_ancestor_handles_until_parent_flush(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    original_flush = run_evidence._windows_flush
    denied = False

    def probe(handle: int) -> None:
        nonlocal denied
        try:
            os.rename(trusted, tmp_path / "redirected")
        except OSError:
            denied = True
        original_flush(handle)

    monkeypatch.setattr(run_evidence, "_windows_flush", probe)
    write_synthetic_bundle_no_clobber(trusted / "bundle.container.json", synthetic_private_bundle())
    assert denied


@pytest.mark.skipif(os.name != "nt", reason="Windows link fixture semantics")
def test_windows_rejects_linked_ancestor_without_touching_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    completed = subprocess.run(
        ("cmd", "/c", "mklink", "/J", str(linked), str(target)),
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("the platform cannot create a junction in pytest tmp_path")
    with pytest.raises(ValueError, match="^TRUSTED_PARENT_REQUIRED$"):
        write_synthetic_bundle_no_clobber(
            linked / "bundle.container.json", synthetic_private_bundle()
        )
    assert tuple(target.iterdir()) == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows cross-volume fixture semantics")
def test_windows_rejects_cross_volume_junction_ancestor(tmp_path: Path) -> None:
    target: Path | None = None
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        drive = Path(f"{letter}:\\")
        if drive.exists():
            try:
                target = Path(tempfile.mkdtemp(prefix="mdcp-cross-volume-", dir=drive))
            except OSError:
                continue
            break
    if target is None:
        pytest.skip("no second writable Windows volume is available")
    linked = tmp_path / "cross-volume"
    completed = subprocess.run(
        ("cmd", "/c", "mklink", "/J", str(linked), str(target)),
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("the platform cannot create a cross-volume junction")
    try:
        with pytest.raises(ValueError, match="^TRUSTED_PARENT_REQUIRED$"):
            write_synthetic_bundle_no_clobber(
                linked / "bundle.container.json", synthetic_private_bundle()
            )
        assert tuple(target.iterdir()) == ()
    finally:
        target.rmdir()


@pytest.mark.skipif(os.name != "nt", reason="Windows normalized handle names")
def test_windows_rejects_normalized_handle_name_mismatch_before_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = run_evidence._windows_normalized_handle_name
    calls = 0

    def mismatch(handle: int) -> str:
        nonlocal calls
        calls += 1
        value = original(handle)
        return value if calls == 1 else value + "-mismatch"

    monkeypatch.setattr(run_evidence, "_windows_normalized_handle_name", mismatch)
    with pytest.raises(ValueError, match="^TRUSTED_PARENT_REQUIRED$"):
        write_synthetic_bundle_no_clobber(
            tmp_path / "bundle.container.json", synthetic_private_bundle()
        )
    assert not (tmp_path / "bundle.container.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows create-new semantics")
def test_windows_destination_create_collision_preserves_attacker_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle.container.json"
    original = run_evidence._windows_nt_relative_file

    def collide(
        parent_handle: int,
        name: str,
        is_directory: bool,
        desired_access: int,
        share_mode: int,
        create_disposition: int,
        create_options: int,
    ) -> tuple[int | None, tuple[int, int, int] | None, int]:
        if not is_directory and not destination.exists():
            destination.write_bytes(b"attacker")
        return original(
            parent_handle,
            name,
            is_directory,
            desired_access,
            share_mode,
            create_disposition,
            create_options,
        )

    monkeypatch.setattr(run_evidence, "_windows_nt_relative_file", collide)
    with pytest.raises(ValueError, match="^DESTINATION_EXISTS$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert destination.read_bytes() == b"attacker"


@pytest.mark.skipif(os.name != "nt", reason="Windows handle cleanup semantics")
@pytest.mark.parametrize("failure", ("short_write", "file_flush", "parent_flush", "identity"))
def test_windows_failures_use_handle_bound_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    destination = tmp_path / "bundle.container.json"
    deleted_handles: list[int] = []
    original_delete = run_evidence._windows_set_delete_disposition
    original_flush = run_evidence._windows_flush
    original_information = run_evidence._windows_file_information
    flush_calls = 0
    information_calls = 0

    def record_delete(handle: int) -> bool:
        deleted_handles.append(handle)
        return original_delete(handle)

    def fail_flush(handle: int) -> None:
        nonlocal flush_calls
        flush_calls += 1
        if (failure == "file_flush" and flush_calls == 1) or (
            failure == "parent_flush" and flush_calls == 2
        ):
            raise run_evidence._PublicationError("PUBLICATION_FAILED")
        original_flush(handle)

    def changed_information(handle: int) -> tuple[int, tuple[int, int, int]]:
        nonlocal information_calls
        result = original_information(handle)
        information_calls += 1
        if failure == "identity" and information_calls > 3:
            return result[0], (result[1][0], result[1][1], result[1][2] + 1)
        return result

    monkeypatch.setattr(run_evidence, "_windows_set_delete_disposition", record_delete)
    monkeypatch.setattr(run_evidence, "_windows_flush", fail_flush)
    monkeypatch.setattr(run_evidence, "_windows_file_information", changed_information)
    if failure == "short_write":
        monkeypatch.setattr(
            run_evidence, "_windows_write_chunk", lambda _handle, data: len(data) - 1
        )
    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert len(deleted_handles) == 1
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows handle cleanup semantics")
def test_windows_cleanup_failure_is_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle.container.json"
    monkeypatch.setattr(run_evidence, "_windows_write_chunk", lambda _handle, _data: 0)
    monkeypatch.setattr(run_evidence, "_windows_set_delete_disposition", lambda _handle: False)
    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows handle cleanup semantics")
def test_windows_immediate_final_metadata_failure_keeps_handle_for_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle.container.json"
    original_relative = run_evidence._windows_nt_relative_file
    original_information = run_evidence._windows_file_information
    original_delete = run_evidence._windows_set_delete_disposition
    final_handle: int | None = None
    deleted_handles: list[int] = []

    def mark_final(
        parent_handle: int,
        name: str,
        is_directory: bool,
        desired_access: int,
        share_mode: int,
        create_disposition: int,
        create_options: int,
    ) -> tuple[int | None, tuple[int, int, int] | None, int]:
        nonlocal final_handle
        result = original_relative(
            parent_handle,
            name,
            is_directory,
            desired_access,
            share_mode,
            create_disposition,
            create_options,
        )
        if not is_directory:
            final_handle = result[0]
        return result

    def unexpected_reparse(handle: int) -> tuple[int, tuple[int, int, int]]:
        attributes, identity = original_information(handle)
        if handle == final_handle:
            attributes |= run_evidence._WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
        return attributes, identity

    def record_delete(handle: int) -> bool:
        deleted_handles.append(handle)
        return original_delete(handle)

    monkeypatch.setattr(run_evidence, "_windows_nt_relative_file", mark_final)
    monkeypatch.setattr(run_evidence, "_windows_file_information", unexpected_reparse)
    monkeypatch.setattr(run_evidence, "_windows_set_delete_disposition", record_delete)

    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert len(deleted_handles) == 1
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows ancestor handle semantics")
def test_windows_native_ancestor_name_failure_closes_opened_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle.container.json"
    original_create = run_evidence._windows_create_file
    original_close = run_evidence._windows_close
    opened: list[int] = []
    closed: list[int] = []

    def record_open(
        path: Path, desired_access: int, creation: int, flags: int
    ) -> tuple[int | None, int]:
        handle, error = original_create(path, desired_access, creation, flags)
        if handle is not None:
            opened.append(handle)
        return handle, error

    def record_close(handle: int) -> bool:
        closed.append(handle)
        return original_close(handle)

    monkeypatch.setattr(run_evidence, "_windows_create_file", record_open)
    monkeypatch.setattr(run_evidence, "_windows_close", record_close)
    monkeypatch.setattr(
        run_evidence,
        "_windows_normalized_handle_name",
        lambda _handle: (_ for _ in ()).throw(OSError("sensitive path")),
    )

    with pytest.raises(ValueError, match="^TRUSTED_PARENT_REQUIRED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert opened and closed == opened
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows ancestor close aggregation")
@pytest.mark.parametrize(("metadata_call", "expected_close_count"), ((1, 1), (2, 2)))
@pytest.mark.parametrize("close_failure", ("false", "exception"))
def test_windows_early_ancestor_metadata_close_failure_is_aggregated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata_call: int,
    expected_close_count: int,
    close_failure: str,
) -> None:
    destination = tmp_path / "bundle.container.json"
    original_information = run_evidence._windows_file_information
    original_close = run_evidence._windows_close
    information_calls = 0
    close_calls: list[int] = []

    def fail_selected_metadata(handle: int) -> tuple[int, tuple[int, int, int]]:
        nonlocal information_calls
        information_calls += 1
        if information_calls == metadata_call:
            raise run_evidence._PublicationError("PUBLICATION_FAILED")
        return original_information(handle)

    def raise_first_close(handle: int) -> bool:
        close_calls.append(handle)
        result = original_close(handle)
        if len(close_calls) == 1:
            if close_failure == "exception":
                raise OSError("sensitive close failure")
            return False
        return result

    monkeypatch.setattr(run_evidence, "_windows_file_information", fail_selected_metadata)
    monkeypatch.setattr(run_evidence, "_windows_close", raise_first_close)

    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert len(close_calls) == expected_close_count
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows cleanup handle semantics")
def test_windows_delete_disposition_exception_still_closes_every_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle.container.json"
    original_close = run_evidence._windows_close
    closed: list[int] = []

    def record_close(handle: int) -> bool:
        closed.append(handle)
        return original_close(handle)

    monkeypatch.setattr(run_evidence, "_windows_write_chunk", lambda _handle, _data: 0)
    monkeypatch.setattr(
        run_evidence,
        "_windows_set_delete_disposition",
        lambda _handle: (_ for _ in ()).throw(OSError("sensitive path")),
    )
    monkeypatch.setattr(run_evidence, "_windows_close", record_close)

    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())

    assert len(closed) >= 2


@pytest.mark.skipif(os.name != "nt", reason="Windows close failure semantics")
@pytest.mark.parametrize("failed_close_index", (1, 2))
def test_windows_close_failure_after_success_is_terminal_and_all_handles_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_close_index: int
) -> None:
    destination = tmp_path / "bundle.container.json"
    original_close = run_evidence._windows_close
    close_calls: list[int] = []

    def fail_selected_close(handle: int) -> bool:
        close_calls.append(handle)
        original_close(handle)
        return len(close_calls) != failed_close_index

    monkeypatch.setattr(run_evidence, "_windows_close", fail_selected_close)
    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert len(close_calls) >= 2
    assert destination.is_file()


@pytest.mark.skipif(os.name != "nt", reason="Windows close failure semantics")
def test_windows_close_failure_after_delete_disposition_overrides_prior_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle.container.json"
    original_close = run_evidence._windows_close
    original_delete = run_evidence._windows_set_delete_disposition
    close_calls: list[int] = []
    delete_calls: list[int] = []

    def fail_write(_handle: int, _content: bytes) -> int:
        raise run_evidence._PublicationError("PRIOR_FAILURE")

    def record_delete(handle: int) -> bool:
        delete_calls.append(handle)
        return original_delete(handle)

    def fail_first_close(handle: int) -> bool:
        close_calls.append(handle)
        original_close(handle)
        return len(close_calls) != 1

    monkeypatch.setattr(run_evidence, "_windows_write_chunk", fail_write)
    monkeypatch.setattr(run_evidence, "_windows_set_delete_disposition", record_delete)
    monkeypatch.setattr(run_evidence, "_windows_close", fail_first_close)
    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert len(delete_calls) == 1
    assert len(close_calls) >= 2
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows final identity semantics")
def test_windows_final_normalized_name_mismatch_is_cleaned_by_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle.container.json"
    original = run_evidence._windows_normalized_handle_name

    def mismatch_final(handle: int) -> str:
        value = original(handle)
        return value + "-mismatch" if value.endswith(destination.name) else value

    monkeypatch.setattr(run_evidence, "_windows_normalized_handle_name", mismatch_final)
    with pytest.raises(ValueError, match="^PUBLICATION_FAILED$"):
        write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows publication surface")
def test_windows_publisher_has_no_staging_rename_or_destination_path_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root_opens: list[Path] = []
    original = run_evidence._windows_create_file

    def root_only(
        path: Path, desired_access: int, creation: int, flags: int
    ) -> tuple[int | None, int]:
        root_opens.append(path)
        return original(path, desired_access, creation, flags)

    monkeypatch.setattr(run_evidence, "_windows_create_file", root_only)
    destination = tmp_path / "bundle.container.json"
    identity = write_synthetic_bundle_no_clobber(destination, synthetic_private_bundle())
    assert root_opens == [Path(destination.anchor)]
    assert destination.is_file()
    assert run_evidence.verify_private_container(destination, identity).verdict == "PASS"
    assert not hasattr(run_evidence, "_windows_rename_noreplace")
    assert not any("staging" in path.name.lower() for path in tmp_path.iterdir())


def test_private_bundle_public_identity_contains_no_private_material() -> None:
    _, identity = private_container_bytes()
    assert set(identity.model_dump()) == {
        "file_count",
        "total_bytes",
        "inventory_sha256",
        "manifest_sha256",
    }
    assert public_evidence_violations(identity.model_dump(mode="json")) == ()
