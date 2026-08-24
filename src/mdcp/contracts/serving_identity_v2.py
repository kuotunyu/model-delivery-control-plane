from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from mdcp.common.canonical import canonicalize_json
from mdcp.common.digests import sha256_hex

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

V2_SERVING_PATHS = (
    "pyproject.toml",
    "schemas/v2/bike-request.schema.json",
    "schemas/v2/temporal-contract-receipt.schema.json",
    "src/mdcp/common/canonical.py",
    "src/mdcp/common/digests.py",
    "src/mdcp/common/enums.py",
    "src/mdcp/contracts/serving_identity_v2.py",
    "src/mdcp/contracts/workload.py",
    "src/mdcp/contracts/workload_v2.py",
    "src/mdcp/predictor/app_v2.py",
    "src/mdcp/predictor/runtime.py",
    "src/mdcp/temporal/adapter.py",
    "src/mdcp/temporal/constants.py",
    "src/mdcp/temporal/contract_gate.py",
    "src/mdcp/temporal/evidence.py",
    "src/mdcp/temporal/firewall.py",
    "src/mdcp/temporal/golden_vectors.py",
    "src/mdcp/temporal/routing.py",
    "src/mdcp/workload/dataset.py",
    "src/mdcp/workload/features.py",
    "src/mdcp/workload/splits.py",
    "tests/fixtures/temporal/adapter-golden-vectors.json",
    "uv.lock",
)

_FAILURE_REASON = "V2_SERVING_INVENTORY_INVALID"


class V2ServingIdentityError(ValueError):
    def __init__(self) -> None:
        self.reason_code = _FAILURE_REASON
        super().__init__(_FAILURE_REASON)


def _safe_path(value: str) -> bool:
    candidate = PurePosixPath(value)
    return bool(
        value
        and "\\" not in value
        and not candidate.is_absolute()
        and ".." not in candidate.parts
        and candidate.as_posix() == value
    )


class V2InventoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: Sha256

    @model_validator(mode="after")
    def path_is_safe(self) -> V2InventoryEntry:
        if not _safe_path(self.path):
            raise ValueError(_FAILURE_REASON)
        return self


class V2ServingInventoryBody(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.v2-serving-inventory.v1"]
    entry_point: Literal["mdcp.predictor.app_v2:app"]
    entries: tuple[V2InventoryEntry, ...]

    @model_validator(mode="after")
    def inventory_is_exact(self) -> V2ServingInventoryBody:
        paths = tuple(entry.path for entry in self.entries)
        if paths != V2_SERVING_PATHS:
            raise ValueError(_FAILURE_REASON)
        return self


class V2ServingInventoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    body: V2ServingInventoryBody
    inventory_sha256: Sha256


def _fail(error: Exception | None = None) -> None:
    if error is None:
        raise V2ServingIdentityError()
    raise V2ServingIdentityError() from error


def _body_sha256(body: V2ServingInventoryBody) -> str:
    return sha256_hex(canonicalize_json(body.model_dump(mode="json")))


def build_v2_serving_inventory(
    repository_root: Path,
    declared_paths: tuple[str, ...],
) -> V2ServingInventoryResult:
    try:
        if declared_paths != V2_SERVING_PATHS:
            _fail()
        if tuple(sorted(declared_paths)) != declared_paths:
            _fail()
        if len(set(declared_paths)) != len(declared_paths):
            _fail()
        if any(not _safe_path(path) for path in declared_paths):
            _fail()
        entries = tuple(
            V2InventoryEntry(
                path=path,
                sha256=sha256_hex((repository_root / path).read_bytes()),
            )
            for path in declared_paths
        )
        body = V2ServingInventoryBody(
            schema_version="mdcp.v2-serving-inventory.v1",
            entry_point="mdcp.predictor.app_v2:app",
            entries=entries,
        )
        return V2ServingInventoryResult(
            body=body,
            inventory_sha256=_body_sha256(body),
        )
    except V2ServingIdentityError:
        raise
    except Exception as error:
        _fail(error)


def verify_v2_serving_inventory(
    repository_root: Path,
    declared_result: V2ServingInventoryResult,
) -> V2ServingInventoryResult:
    try:
        body = declared_result.body
        if (
            body.schema_version != "mdcp.v2-serving-inventory.v1"
            or body.entry_point != "mdcp.predictor.app_v2:app"
            or tuple(entry.path for entry in body.entries) != V2_SERVING_PATHS
            or declared_result.inventory_sha256 != _body_sha256(body)
        ):
            _fail()
        expected = build_v2_serving_inventory(repository_root, V2_SERVING_PATHS)
        if declared_result != expected:
            _fail()
        return expected
    except V2ServingIdentityError:
        raise
    except Exception as error:
        _fail(error)
