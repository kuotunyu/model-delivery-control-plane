from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from jsonschema import validate

from mdcp.contracts.release import (
    FinalReleaseManifest,
    ReleaseCIBundleIndex,
    release_id,
)

REPOSITORY_ROOT = Path(__file__).parents[3]


def test_checked_in_release_schemas_match_pydantic() -> None:
    expected = {
        "final-release-manifest.schema.json": FinalReleaseManifest.model_json_schema(),
        "release-ci-bundle-index.schema.json": ReleaseCIBundleIndex.model_json_schema(),
    }
    for filename, schema in expected.items():
        checked_in = json.loads(
            (REPOSITORY_ROOT / "schemas" / "v1" / filename).read_text(encoding="utf-8")
        )
        assert checked_in == schema
        assert checked_in["additionalProperties"] is False


def test_valid_supply_chain_fixtures_match_schemas_and_member_digests() -> None:
    root = REPOSITORY_ROOT / "tests" / "fixtures" / "supply-chain" / "valid"
    manifest_document = json.loads(
        (root / "final-release-manifest.json").read_text(encoding="utf-8")
    )
    index_document = json.loads((root / "bundle-index.json").read_text(encoding="utf-8"))

    validate(
        manifest_document,
        json.loads(
            (
                REPOSITORY_ROOT / "schemas" / "v1" / "final-release-manifest.schema.json"
            ).read_text(encoding="utf-8")
        ),
    )
    validate(
        index_document,
        json.loads(
            (
                REPOSITORY_ROOT / "schemas" / "v1" / "release-ci-bundle-index.schema.json"
            ).read_text(encoding="utf-8")
        ),
    )
    manifest = FinalReleaseManifest.model_validate(manifest_document)
    index = ReleaseCIBundleIndex.model_validate(index_document)
    assert manifest.release_id == release_id(manifest)
    assert index.release_id == manifest.release_id
    for member in index.members:
        payload = (root / member.path).read_bytes()
        assert len(payload) == member.size_bytes
        assert sha256(payload).hexdigest() == member.sha256
