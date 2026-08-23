from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import time
from collections.abc import Awaitable, Callable, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorClass(StrEnum):
    CONNECT_ERROR = "ConnectError"
    CONNECT_TIMEOUT = "ConnectTimeout"
    READ_TIMEOUT = "ReadTimeout"
    PROTOCOL_ERROR = "ProtocolError"
    INVALID_RESPONSE = "InvalidResponse"
    OTHER = "Other"


def empty_error_class_counts() -> dict[ErrorClass, int]:
    return {error_class: 0 for error_class in ErrorClass}


class RequestOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    status_code: int | None = None
    error_class: ErrorClass | None = None


SendRequest = Callable[[], Awaitable[RequestOutcome]]


def classify_http_error(error: Exception) -> ErrorClass:
    if isinstance(error, httpx.ConnectTimeout):
        return ErrorClass.CONNECT_TIMEOUT
    if isinstance(error, httpx.ConnectError):
        return ErrorClass.CONNECT_ERROR
    if isinstance(error, httpx.ReadTimeout):
        return ErrorClass.READ_TIMEOUT
    if isinstance(error, httpx.ProtocolError):
        return ErrorClass.PROTOCOL_ERROR
    return ErrorClass.OTHER


def response_outcome(response: httpx.Response) -> RequestOutcome:
    try:
        payload = response.json() if response.status_code == 200 else {}
    except ValueError:
        payload = {}
    valid = (
        response.status_code == 200
        and isinstance(payload, dict)
        and set(payload) == {"prediction", "schema_version"}
    )
    return RequestOutcome(
        ok=valid,
        status_code=response.status_code,
        error_class=None if valid else ErrorClass.INVALID_RESPONSE,
    )


class LoadProbeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    admitted: int
    completed: int
    errors: int
    achieved_rps: float
    max_in_flight: int
    p95_us: int
    wall_time_ms: int
    error_class_counts: dict[ErrorClass, int] = Field(default_factory=empty_error_class_counts)

    @field_validator("error_class_counts")
    @classmethod
    def validate_error_class_counts(
        cls, counts: dict[ErrorClass, int]
    ) -> dict[ErrorClass, int]:
        if set(counts) != set(ErrorClass) or any(count < 0 for count in counts.values()):
            raise ValueError("fixed non-negative error class counts are required")
        return counts


def nearest_rank_us(samples: Sequence[int], percentile: float = 0.95) -> int:
    if not samples:
        raise ValueError("at least one latency sample is required")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    ordered = sorted(samples)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


async def run_load(
    send: SendRequest,
    *,
    count: int,
    rate_rps: int,
    max_in_flight: int,
) -> LoadProbeResult:
    semaphore = asyncio.Semaphore(max_in_flight)
    interval_ns = 1_000_000_000 // rate_rps
    epoch_ns = time.perf_counter_ns()
    admission_ns: list[int] = []
    latency_us: list[int] = []
    errors = 0
    error_class_counts = empty_error_class_counts()
    active = 0
    observed_max = 0

    async def admit_one(index: int) -> None:
        nonlocal active, errors, observed_max
        target_ns = epoch_ns + index * interval_ns
        remaining_ns = target_ns - time.perf_counter_ns()
        if remaining_ns > 0:
            await asyncio.sleep(remaining_ns / 1_000_000_000)
        admission_ns.append(time.perf_counter_ns())
        started_ns = time.perf_counter_ns()
        async with semaphore:
            active += 1
            observed_max = max(observed_max, active)
            try:
                outcome = await send()
                if not outcome.ok or outcome.status_code != 200:
                    error_class = outcome.error_class or ErrorClass.INVALID_RESPONSE
                    errors += 1
                    error_class_counts[error_class] += 1
            except Exception:
                errors += 1
                error_class_counts[ErrorClass.OTHER] += 1
            finally:
                active -= 1
        elapsed_ns = time.perf_counter_ns() - started_ns
        latency_us.append((elapsed_ns + 999) // 1_000)

    tasks = [asyncio.create_task(admit_one(index)) for index in range(count)]
    await asyncio.gather(*tasks)
    finished_ns = time.perf_counter_ns()
    admission_span_ns = max(interval_ns, admission_ns[-1] - admission_ns[0] + interval_ns)
    achieved_rps = count * 1_000_000_000 / admission_span_ns
    return LoadProbeResult(
        admitted=count,
        completed=count,
        errors=errors,
        achieved_rps=round(achieved_rps, 3),
        max_in_flight=observed_max,
        p95_us=nearest_rank_us(latency_us),
        wall_time_ms=(finished_ns - epoch_ns + 999_999) // 1_000_000,
        error_class_counts=error_class_counts,
    )


def build_load_document(**values: int | float) -> dict[str, Any]:
    result = LoadProbeResult(**values)
    verdict = (
        "PASS"
        if result.admitted == 2_000
        and result.completed == 2_000
        and result.errors == 0
        and all(count == 0 for count in result.error_class_counts.values())
        and result.achieved_rps >= 80.0
        and result.max_in_flight <= 32
        and result.p95_us <= 25_000
        else "FAIL"
    )
    evidence = result.model_dump(mode="json")
    canonical = json.dumps(evidence, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return {
        "schema_version": "mdcp.feasibility.load.v1",
        "evidence_class": "FEASIBILITY",
        "claim_boundary": "load harness feasibility; not predictor performance",
        "gate": {
            "name": "load_harness",
            "verdict": verdict,
            "evidence_digest": hashlib.sha256(canonical.encode("ascii")).hexdigest(),
        },
        "result": evidence,
    }


async def run_http_probe(
    url: str, count: int, rate_rps: int, max_in_flight: int
) -> LoadProbeResult:
    limits = httpx.Limits(max_connections=max_in_flight, max_keepalive_connections=max_in_flight)
    timeout = httpx.Timeout(2.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:

        async def send() -> RequestOutcome:
            try:
                response = await client.post(
                    url,
                    json={"row": {"temp": 0.4, "humidity": 0.7, "hour": 8}},
                )
            except Exception as error:
                return RequestOutcome(ok=False, error_class=classify_http_error(error))
            return response_outcome(response)

        return await run_load(
            send,
            count=count,
            rate_rps=rate_rps,
            max_in_flight=max_in_flight,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--count", type=int, default=2_000)
    parser.add_argument("--rate", type=int, default=80)
    parser.add_argument("--max-in-flight", type=int, default=32)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = asyncio.run(run_http_probe(args.url, args.count, args.rate, args.max_in_flight))
    document = build_load_document(**result.model_dump())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"FEAS-LOAD-{document['gate']['verdict']} admitted={result.admitted} "
        f"completed={result.completed} errors={result.errors} "
        f"achieved_rps={result.achieved_rps} max_in_flight={result.max_in_flight} "
        f"p95_us={result.p95_us} wall_time_ms={result.wall_time_ms}"
    )
    return 0 if document["gate"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
