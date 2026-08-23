from __future__ import annotations

import shutil
import socket
from pathlib import Path

from mdcp.common.enums import GateVerdict
from mdcp.verify.bundle import verify_bundle

REPOSITORY_ROOT = Path(__file__).parents[3]


def test_offline_verification_makes_no_network_call(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(
        REPOSITORY_ROOT / "tests" / "fixtures" / "supply-chain" / "valid",
        bundle,
    )
    calls = 0

    def fail_network(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("offline verification attempted network access")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    monkeypatch.setattr(socket, "getaddrinfo", fail_network)

    result = verify_bundle(bundle, online=False)

    assert result.verdict is GateVerdict.PASS
    assert calls == 0
