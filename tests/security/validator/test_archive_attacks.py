from __future__ import annotations

import io
import stat
import zipfile
from pathlib import Path

import pytest

from mdcp.common.enums import ValidationVerdict
from mdcp.validator.identity_checks import validate_archive
from mdcp.validator.policy import ValidationPolicy
from mdcp.validator.service import ReasonCode

REPOSITORY_ROOT = Path(__file__).parents[3]
INDEX = REPOSITORY_ROOT / "tests" / "fixtures" / "artifacts" / "adversarial" / "fixture-index.json"


@pytest.fixture
def policy() -> ValidationPolicy:
    return ValidationPolicy.model_validate_json(
        (REPOSITORY_ROOT / "configs" / "policy" / "validation-v1.json").read_text(encoding="utf-8")
    )


def _write_zip(tmp_path: Path, entries: list[tuple[zipfile.ZipInfo | str, bytes]]) -> Path:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    path = tmp_path / "attack.zip"
    path.write_bytes(stream.getvalue())
    return path


@pytest.mark.parametrize("name", ["../outside", "/absolute", "safe/../../escape"])
def test_archive_traversal_is_quarantined(
    tmp_path: Path,
    policy: ValidationPolicy,
    name: str,
) -> None:
    path = _write_zip(tmp_path, [(name, b"attack")])

    checks = validate_archive(path, policy)

    assert checks[0].code is ReasonCode.VAL_PATH_ESCAPE
    assert checks[0].verdict is ValidationVerdict.QUARANTINE


def test_archive_duplicate_member_is_quarantined(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    with pytest.warns(UserWarning, match="Duplicate name"):
        path = _write_zip(tmp_path, [("model.onnx", b"a"), ("model.onnx", b"b")])

    checks = validate_archive(path, policy)

    assert checks[0].code is ReasonCode.VAL_PATH_ESCAPE
    assert checks[0].verdict is ValidationVerdict.QUARANTINE


def test_archive_link_is_quarantined(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    link = zipfile.ZipInfo("model.onnx")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    path = _write_zip(tmp_path, [(link, b"../secret")])

    checks = validate_archive(path, policy)

    assert checks[0].code is ReasonCode.VAL_PATH_ESCAPE
    assert checks[0].verdict is ValidationVerdict.QUARANTINE


def test_archive_expansion_limit_fails_closed(
    tmp_path: Path,
    policy: ValidationPolicy,
) -> None:
    bounded = policy.model_copy(update={"max_total_bytes": 16})
    path = _write_zip(tmp_path, [("large.bin", b"x" * 17)])

    checks = validate_archive(path, bounded)

    assert checks[0].code is ReasonCode.VAL_RESOURCE_LIMIT
    assert checks[0].verdict is ValidationVerdict.FAIL


def test_adversarial_fixture_index_names_every_attack() -> None:
    import json

    document = json.loads(INDEX.read_text(encoding="utf-8"))

    assert {(item["fixture"], item["code"]) for item in document["fixtures"]} == {
        ("pickle.bin", "VAL_FORBIDDEN_FORMAT"),
        ("traversal.zip", "VAL_PATH_ESCAPE"),
        ("duplicate.zip", "VAL_PATH_ESCAPE"),
        ("symlink.zip", "VAL_PATH_ESCAPE"),
        ("oversized.zip", "VAL_RESOURCE_LIMIT"),
        ("external-parent.onnx", "VAL_PATH_ESCAPE"),
        ("unsupported-op.onnx", "VAL_ONNX_OPERATOR"),
        ("nan-output.onnx", "VAL_ONNX_INVALID"),
        ("negative-output.onnx", "VAL_ONNX_INVALID"),
    }
