from __future__ import annotations

import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex
from mdcp.common.enums import ValidationVerdict
from mdcp.contracts.release import ArtifactDescriptor
from mdcp.validator.policy import ValidationPolicy
from mdcp.validator.service import ReasonCode, ValidationCheck, make_check


def _check(
    code: ReasonCode,
    verdict: ValidationVerdict,
    facts: dict[str, object],
) -> ValidationCheck:
    return make_check(
        code,
        verdict,
        evidence_digest=sha256_hex(canonicalize_json(facts)),
    )


def validate_identity(
    root: Path,
    descriptor: ArtifactDescriptor,
    policy: ValidationPolicy,
) -> tuple[ValidationCheck, ...]:
    files = tuple(path for path in root.rglob("*") if path.is_file() or path.is_symlink())
    links = tuple(path for path in files if path.is_symlink())
    regular_files = tuple(path for path in files if path.is_file() and not path.is_symlink())
    suffixes = tuple(sorted(path.suffix.lower() for path in regular_files))
    onnx_files = tuple(path for path in regular_files if path.suffix.lower() == ".onnx")

    path_verdict = (
        ValidationVerdict.QUARANTINE if root.is_symlink() or links else ValidationVerdict.PASS
    )
    path_check = _check(
        ReasonCode.VAL_PATH_ESCAPE,
        path_verdict,
        {"root_is_link": root.is_symlink(), "link_count": len(links)},
    )

    forbidden = any(suffix in policy.forbidden_suffixes for suffix in suffixes)
    format_verdict = (
        ValidationVerdict.QUARANTINE
        if forbidden or len(onnx_files) != 1
        else ValidationVerdict.PASS
    )
    format_check = _check(
        ReasonCode.VAL_FORBIDDEN_FORMAT,
        format_verdict,
        {
            "forbidden_suffix_present": forbidden,
            "onnx_file_count": len(onnx_files),
        },
    )

    sizes = tuple(path.stat().st_size for path in regular_files)
    resource_exceeded = (
        len(regular_files) > policy.max_file_count
        or sum(sizes) > policy.max_total_bytes
        or any(size > policy.max_single_file_bytes for size in sizes)
    )
    resource_check = _check(
        ReasonCode.VAL_RESOURCE_LIMIT,
        ValidationVerdict.FAIL if resource_exceeded else ValidationVerdict.PASS,
        {
            "file_count": len(regular_files),
            "total_bytes": sum(sizes),
            "largest_bytes": max(sizes, default=0),
        },
    )

    digest_matches = False
    if len(onnx_files) == 1:
        content = onnx_files[0].read_bytes()
        digest_matches = (
            sha256_hex(content) == descriptor.model_sha256
            and sha256_hex(content) == descriptor.onnx.sha256
            and len(content) == descriptor.onnx.size_bytes
        )
    digest_check = _check(
        ReasonCode.VAL_DIGEST_MISMATCH,
        ValidationVerdict.PASS if digest_matches else ValidationVerdict.FAIL,
        {"model_digest_matches": digest_matches},
    )
    return (digest_check, format_check, path_check, resource_check)


def _unsafe_archive_member(info: zipfile.ZipInfo) -> bool:
    normalized_name = info.filename.replace("\\", "/")
    path = PurePosixPath(normalized_name)
    unix_type = (info.external_attr >> 16) & 0o170000
    return (
        path.is_absolute()
        or ".." in path.parts
        or bool(re.match(r"^[A-Za-z]:", normalized_name))
        or info.is_dir()
        or unix_type == stat.S_IFLNK
    )


def validate_archive(
    archive_path: Path,
    policy: ValidationPolicy,
) -> tuple[ValidationCheck, ...]:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
    except (OSError, zipfile.BadZipFile):
        return (
            _check(
                ReasonCode.VAL_FORBIDDEN_FORMAT,
                ValidationVerdict.QUARANTINE,
                {"valid_zip": False},
            ),
        )

    names = [info.filename.replace("\\", "/") for info in infos]
    if len(names) != len(set(names)) or any(_unsafe_archive_member(info) for info in infos):
        return (
            _check(
                ReasonCode.VAL_PATH_ESCAPE,
                ValidationVerdict.QUARANTINE,
                {"safe_members": False, "member_count": len(infos)},
            ),
        )
    if (
        len(infos) > policy.max_file_count
        or sum(info.file_size for info in infos) > policy.max_total_bytes
        or any(info.file_size > policy.max_single_file_bytes for info in infos)
    ):
        return (
            _check(
                ReasonCode.VAL_RESOURCE_LIMIT,
                ValidationVerdict.FAIL,
                {"within_resource_limits": False, "member_count": len(infos)},
            ),
        )
    if any(PurePosixPath(name).suffix.lower() in policy.forbidden_suffixes for name in names):
        return (
            _check(
                ReasonCode.VAL_FORBIDDEN_FORMAT,
                ValidationVerdict.QUARANTINE,
                {"allowed_member_formats": False},
            ),
        )
    return (
        _check(
            ReasonCode.VAL_OK,
            ValidationVerdict.PASS,
            {"safe_members": True, "member_count": len(infos)},
        ),
    )
