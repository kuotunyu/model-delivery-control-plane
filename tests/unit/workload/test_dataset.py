from __future__ import annotations

import hashlib
import io
import stat
import zipfile
from pathlib import Path

import pytest

from mdcp.workload.dataset import (
    EXPECTED_UCI_COLUMNS,
    DatasetIntegrityError,
    load_uci_archive,
)


def _hour_csv(columns: tuple[str, ...] = EXPECTED_UCI_COLUMNS) -> bytes:
    values = {
        "instant": "1",
        "dteday": "2011-01-01",
        "season": "1",
        "yr": "0",
        "mnth": "1",
        "hr": "0",
        "holiday": "0",
        "weekday": "6",
        "workingday": "0",
        "weathersit": "1",
        "temp": "0.24",
        "atemp": "0.2879",
        "hum": "0.81",
        "windspeed": "0.0",
        "casual": "3",
        "registered": "13",
        "cnt": "16",
    }
    return (",".join(columns) + "\n" + ",".join(values[name] for name in columns) + "\n").encode()


def _archive_bytes(
    *,
    hour_csv: bytes | None = None,
    extra: tuple[tuple[str, bytes], ...] = (),
    symlink_hour: bool = False,
) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("Readme.txt", b"fixture")
        archive.writestr("day.csv", b"fixture")
        if symlink_hour:
            info = zipfile.ZipInfo("hour.csv")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, b"target")
        else:
            archive.writestr("hour.csv", hour_csv or _hour_csv())
        for name, body in extra:
            archive.writestr(name, body)
    return stream.getvalue()


def _write_archive(tmp_path: Path, content: bytes) -> tuple[Path, str]:
    path = tmp_path / "dataset.zip"
    path.write_bytes(content)
    return path, hashlib.sha256(content).hexdigest()


def test_load_uci_archive_checks_digest_and_schema(tmp_path: Path) -> None:
    path, digest = _write_archive(tmp_path, _archive_bytes())

    frame = load_uci_archive(path, digest)

    assert tuple(frame.columns) == EXPECTED_UCI_COLUMNS
    assert frame.loc[0, "cnt"] == 16


def test_load_uci_archive_rejects_digest_mismatch(tmp_path: Path) -> None:
    path, _ = _write_archive(tmp_path, _archive_bytes())

    with pytest.raises(DatasetIntegrityError, match="archive digest mismatch"):
        load_uci_archive(path, "0" * 64)


@pytest.mark.parametrize(
    "extra_name",
    ["../outside.csv", "/absolute.csv", "unexpected.csv"],
)
def test_load_uci_archive_rejects_traversal_and_unexpected_members(
    tmp_path: Path, extra_name: str
) -> None:
    path, digest = _write_archive(
        tmp_path,
        _archive_bytes(extra=((extra_name, b"bad"),)),
    )

    with pytest.raises(DatasetIntegrityError, match="unsafe archive members"):
        load_uci_archive(path, digest)


def test_load_uci_archive_rejects_duplicate_members(tmp_path: Path) -> None:
    with pytest.warns(UserWarning, match="Duplicate name"):
        content = _archive_bytes(extra=(("hour.csv", _hour_csv()),))
    path, digest = _write_archive(tmp_path, content)

    with pytest.raises(DatasetIntegrityError, match="duplicate archive member"):
        load_uci_archive(path, digest)


def test_load_uci_archive_rejects_links(tmp_path: Path) -> None:
    path, digest = _write_archive(tmp_path, _archive_bytes(symlink_hour=True))

    with pytest.raises(DatasetIntegrityError, match="regular files"):
        load_uci_archive(path, digest)


def test_load_uci_archive_rejects_unexpected_columns(tmp_path: Path) -> None:
    content = _archive_bytes(hour_csv=_hour_csv(EXPECTED_UCI_COLUMNS[:-1]))
    path, digest = _write_archive(tmp_path, content)

    with pytest.raises(DatasetIntegrityError, match="unexpected columns"):
        load_uci_archive(path, digest)
