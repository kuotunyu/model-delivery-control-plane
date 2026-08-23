from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Literal

import psycopg
from pydantic import BaseModel, ConfigDict

from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex, verify_ed25519

type InjectedFailure = Literal["route_plan_insert", "before_commit"]


class _InjectedFault(RuntimeError):
    pass


class AtomicProbeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    injected_failure: InjectedFailure | None
    visible_row_counts: dict[str, int]
    revisions: dict[str, int]
    payload_digest: str
    split_state: int


class AtomicTransitionProbe:
    def __init__(self, *, dsn: str, fixture_root: Path, sql_path: Path) -> None:
        self._dsn = dsn
        self._fixture_root = fixture_root
        self._sql_path = sql_path

    def _prepare_database(self) -> None:
        schema = self._sql_path.read_text(encoding="utf-8")
        with psycopg.connect(self._dsn, autocommit=True) as connection:
            connection.execute(schema, prepare=False)
            connection.execute(
                "TRUNCATE audit_events, route_plans, releases, environments CASCADE"
            )

    def _vector(self) -> tuple[dict[str, object], bytes, str, bytes]:
        payload_value = parse_json_bytes(
            (self._fixture_root / "route-plan-v1.json").read_bytes()
        )
        if not isinstance(payload_value, dict):
            raise ValueError("route plan fixture must be an object")
        canonical = canonicalize_json(payload_value)
        expected_hex = (self._fixture_root / "route-plan-v1.canonical.hex").read_text(
            encoding="ascii"
        ).strip()
        if canonical.hex() != expected_hex:
            raise ValueError("canonical vector mismatch")
        public_key = bytes.fromhex(
            (self._fixture_root / "route-plan-v1.public.hex")
            .read_text(encoding="ascii")
            .strip()
        )
        signature = bytes.fromhex(
            (self._fixture_root / "route-plan-v1.signature.hex")
            .read_text(encoding="ascii")
            .strip()
        )
        verify_ed25519(public_key, canonical, signature)
        return payload_value, signature, sha256_hex(canonical), canonical

    def run(self, inject_failure_at: InjectedFailure | None) -> AtomicProbeResult:
        self._prepare_database()
        payload, signature, payload_digest, canonical = self._vector()
        environment_id = str(payload["environment_id"])
        release_id = str(payload["stable_release_id"])
        policy_digest = str(payload["policy_digest"])
        revision = int(payload["revision"])

        try:
            with (
                psycopg.connect(self._dsn, autocommit=True) as connection,
                connection.transaction(),
            ):
                connection.execute(
                    """
                    INSERT INTO environments (
                        environment_id, active_release_id, current_revision, policy_digest
                    ) VALUES (%s, NULL, 0, %s)
                    """,
                    (environment_id, policy_digest),
                )
                connection.execute(
                    """
                    SELECT environment_id FROM environments
                    WHERE environment_id = %s FOR UPDATE
                    """,
                    (environment_id,),
                ).fetchone()
                connection.execute(
                    """
                    INSERT INTO releases (release_id, environment_id, state, revision)
                    VALUES (%s, %s, 'PRODUCTION', %s)
                    """,
                    (release_id, environment_id, revision),
                )
                connection.execute(
                    """
                    UPDATE environments
                    SET active_release_id = %s, current_revision = %s
                    WHERE environment_id = %s
                    """,
                    (release_id, revision, environment_id),
                )
                if inject_failure_at == "route_plan_insert":
                    raise _InjectedFault("route plan insertion")
                connection.execute(
                    """
                    INSERT INTO route_plans (
                        environment_id, revision, payload, payload_digest, signature
                    ) VALUES (%s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        environment_id,
                        revision,
                        canonical.decode("utf-8"),
                        payload_digest,
                        signature,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, environment_id, revision, payload_digest
                    ) VALUES ('bootstrap-v1', %s, %s, %s)
                    """,
                    (environment_id, revision, payload_digest),
                )
                if inject_failure_at == "before_commit":
                    raise _InjectedFault("before commit")
        except _InjectedFault:
            pass

        return self._observe(inject_failure_at, payload_digest, release_id)

    def _observe(
        self,
        injected_failure: InjectedFailure | None,
        payload_digest: str,
        release_id: str,
    ) -> AtomicProbeResult:
        table_names = {
            "environment": "environments",
            "release": "releases",
            "route_plan": "route_plans",
            "audit": "audit_events",
        }
        with psycopg.connect(self._dsn, autocommit=True) as connection:
            counts = {
                name: int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
                for name, table in table_names.items()
            }
            revisions: dict[str, int] = {}
            if all(count == 1 for count in counts.values()):
                revisions = {
                    "environment": int(
                        connection.execute(
                            "SELECT current_revision FROM environments"
                        ).fetchone()[0]
                    ),
                    "release": int(
                        connection.execute("SELECT revision FROM releases").fetchone()[0]
                    ),
                    "route_plan": int(
                        connection.execute("SELECT revision FROM route_plans").fetchone()[0]
                    ),
                    "audit": int(
                        connection.execute("SELECT revision FROM audit_events").fetchone()[0]
                    ),
                }
                active_release = connection.execute(
                    "SELECT active_release_id FROM environments"
                ).fetchone()[0]
                stored_digests = {
                    connection.execute("SELECT payload_digest FROM route_plans").fetchone()[0],
                    connection.execute("SELECT payload_digest FROM audit_events").fetchone()[0],
                }
                consistent = (
                    set(revisions.values()) == {1}
                    and active_release == release_id
                    and stored_digests == {payload_digest}
                )
            else:
                consistent = all(count == 0 for count in counts.values())
        return AtomicProbeResult(
            injected_failure=injected_failure,
            visible_row_counts=counts,
            revisions=revisions,
            payload_digest=payload_digest,
            split_state=0 if consistent else 1,
        )


def build_atomic_document(probe: AtomicTransitionProbe) -> dict[str, object]:
    rollback_results = {
        fault: probe.run(inject_failure_at=fault)
        for fault in ("route_plan_insert", "before_commit")
    }
    success = probe.run(inject_failure_at=None)
    zero_counts = {"environment": 0, "release": 0, "route_plan": 0, "audit": 0}
    one_counts = {"environment": 1, "release": 1, "route_plan": 1, "audit": 1}
    passed = (
        all(result.visible_row_counts == zero_counts for result in rollback_results.values())
        and all(result.split_state == 0 for result in rollback_results.values())
        and success.visible_row_counts == one_counts
        and set(success.revisions.values()) == {1}
        and success.split_state == 0
    )
    evidence = {
        "rollback_cases": {
            name: result.model_dump(mode="json") for name, result in rollback_results.items()
        },
        "success": success.model_dump(mode="json"),
    }
    return {
        "schema_version": "mdcp.feasibility.atomic.v1",
        "evidence_class": "FEASIBILITY",
        "gate": {
            "name": "postgres_atomic_transition",
            "verdict": "PASS" if passed else "FAIL",
            "evidence_digest": sha256_hex(canonicalize_json(evidence)),
        },
        "result": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--sql", type=Path, required=True)
    args = parser.parse_args()
    dsn = os.environ.get("MDCP_ATOMIC_DSN")
    if not dsn:
        print("FEAS-TX-DSN-MISSING")
        return 1
    try:
        probe = AtomicTransitionProbe(dsn=dsn, fixture_root=args.fixture_root, sql_path=args.sql)
        document = build_atomic_document(probe)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception:
        print("FEAS-TX-FAIL")
        return 1
    verdict = document["gate"]["verdict"]
    print(f"FEAS-TX-{verdict} rollback_cases=2 committed_revision=1 split_state=0")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
