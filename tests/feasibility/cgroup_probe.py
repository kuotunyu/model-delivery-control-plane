from __future__ import annotations

import json
import os
import platform
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request

_ALLOCATIONS: list[bytearray] = []


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True), flush=True)


class CandidateHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self) -> None:
        if self.path != "/allocate":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        _ALLOCATIONS.append(bytearray(16 * 1024 * 1024))
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def run_candidate() -> None:
    _emit({"phase": "container_start"})
    _ALLOCATIONS.append(bytearray(16 * 1024 * 1024))
    _emit({"phase": "model_load"})
    for _ in range(200):
        warmup = bytearray(64 * 1024)
        warmup[0] = 1
    _emit({"phase": "warmup", "requests": 200})
    _ALLOCATIONS.append(bytearray(32 * 1024 * 1024))
    _emit({"phase": "scenario_end"})
    ThreadingHTTPServer(("0.0.0.0", 8080), CandidateHandler).serve_forever()


def run_observer(root: Path) -> None:
    payload = _read_exact(root)
    payload.update(
        {
            "kernel": platform.release(),
            "cgroup_version": 2
            if Path("/sys/fs/cgroup/cgroup.controllers").is_file()
            else 1,
            "docker_socket_present": Path("/var/run/docker.sock").exists(),
            "memory_peak_mode": oct((root / "memory.peak").stat().st_mode & 0o777),
        }
    )
    _emit(payload)


def run_reset_probe(root: Path, allocation_url: str) -> None:
    peak = root / "memory.peak"
    try:
        descriptor = os.open(peak, os.O_RDWR)
    except OSError as error:
        _emit(
            {
                "reset_capability_verdict": "UNSUPPORTED_READ_ONLY",
                "errno": error.errno,
            }
        )
        return
    try:
        before = _read_same_fd(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, b"0")
        reset_value = _read_same_fd(descriptor)
        allocation_request = request.Request(allocation_url, method="POST")
        with request.urlopen(allocation_request, timeout=5) as response:
            if response.status != HTTPStatus.NO_CONTENT:
                raise RuntimeError(f"allocation HTTP status {response.status}")
        deadline = time.monotonic() + 5
        increased = _read_same_fd(descriptor)
        while increased <= reset_value and time.monotonic() < deadline:
            time.sleep(0.05)
            increased = _read_same_fd(descriptor)
        verdict = (
            "SUPPORTED_SAME_FD"
            if reset_value <= before and increased > reset_value
            else "PROOF_FAILED"
        )
        _emit(
            {
                "reset_capability_verdict": verdict,
                "before": before,
                "reset_value": reset_value,
                "increased": increased,
            }
        )
    except (OSError, RuntimeError, error.URLError) as reset_error:
        _emit(
            {
                "reset_capability_verdict": "PROOF_FAILED",
                "error_type": type(reset_error).__name__,
            }
        )
    finally:
        os.close(descriptor)


def _read_same_fd(descriptor: int) -> int:
    os.lseek(descriptor, 0, os.SEEK_SET)
    return int(os.read(descriptor, 64).decode("ascii").strip())


def _read_exact(root: Path) -> dict[str, int | str]:
    return {
        "memory_current_bytes": int((root / "memory.current").read_text(encoding="ascii")),
        "memory_peak_bytes": int((root / "memory.peak").read_text(encoding="ascii")),
        "memory_max_bytes": int((root / "memory.max").read_text(encoding="ascii")),
        "cpu_max": (root / "cpu.max").read_text(encoding="ascii").strip(),
    }


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("mode required")
    mode = sys.argv[1]
    if mode == "candidate":
        run_candidate()
        return 0
    if mode == "observe" and len(sys.argv) == 3:
        run_observer(Path(sys.argv[2]))
        return 0
    if mode == "reset" and len(sys.argv) == 4:
        run_reset_probe(Path(sys.argv[2]), sys.argv[3])
        return 0
    raise SystemExit("invalid probe arguments")


if __name__ == "__main__":
    raise SystemExit(main())
