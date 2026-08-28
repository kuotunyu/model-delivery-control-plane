"""Exact isolated process target for one formal development operation."""

from __future__ import annotations

import hashlib
import stat
import sys
from pathlib import Path

_WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400


def _canonical_path(path: Path, *, directory: bool) -> Path:
    if not path.is_absolute():
        raise ValueError
    absolute = path.absolute()
    resolved = path.resolve(strict=True)
    information = path.lstat()
    attributes = getattr(information, "st_file_attributes", 0)
    if (
        absolute != resolved
        or path.is_symlink()
        or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
        or (directory and not stat.S_ISDIR(information.st_mode))
        or (not directory and not stat.S_ISREG(information.st_mode))
    ):
        raise ValueError
    return resolved


def _bootstrap_paths() -> tuple[Path, Path, Path]:
    if (
        __name__ != "__main__"
        or len(sys.argv) != 1
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or not sys.dont_write_bytecode
        or sys.version_info[:2] != (3, 12)
    ):
        raise ValueError
    script = _canonical_path(Path(__file__), directory=False)
    if _canonical_path(Path(sys.argv[0]), directory=False) != script:
        raise ValueError
    repository_root = _canonical_path(script.parents[3], directory=True)
    source_root = _canonical_path(repository_root / "src", directory=True)
    executable = _canonical_path(Path(sys.executable), directory=False)
    site_packages = _canonical_path(executable.parents[1] / "Lib/site-packages", directory=True)
    sys.path.insert(0, str(site_packages))
    sys.path.insert(0, str(source_root))
    return script, repository_root, source_root


def _source_inventory(repository_root: Path) -> str:
    from mdcp.temporal.formal_worker_protocol import (
        FORMAL_WORKER_SOURCE_PATHS,
        FormalWorkerSourceEntry,
        formal_worker_inventory_sha256,
    )

    entries = []
    for logical_path in FORMAL_WORKER_SOURCE_PATHS:
        path = _canonical_path(repository_root / logical_path, directory=False)
        entries.append(
            FormalWorkerSourceEntry(
                logical_path=logical_path,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return formal_worker_inventory_sha256(tuple(entries))


def main() -> int:
    if __name__ != "__main__":
        return 2
    try:
        _script, repository_root, _source_root = _bootstrap_paths()
        from mdcp.temporal.formal_worker_protocol import (
            MAX_WORKER_MESSAGE_BYTES,
            FormalWorkerResponse,
            encode_formal_worker_response,
            launch_profile_sha256,
            parse_formal_worker_request,
            worker_request_sha256,
        )

        raw = sys.stdin.buffer.read(MAX_WORKER_MESSAGE_BYTES + 1)
        request = parse_formal_worker_request(raw)
        inventory_sha256 = _source_inventory(repository_root)
        if (
            request.repository_root != repository_root.as_posix()
            or request.formal_worker_inventory_sha256 != inventory_sha256
            or request.launch_profile_sha256 != launch_profile_sha256()
        ):
            raise ValueError
        response = FormalWorkerResponse(
            schema_version="mdcp.formal-worker-response.v1",
            canonicalization_version="RFC8785",
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
            worker_request_sha256=worker_request_sha256(request),
            formal_worker_inventory_sha256=inventory_sha256,
            launch_profile_sha256=launch_profile_sha256(),
        )
        sys.stdout.buffer.write(encode_formal_worker_response(response))
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
