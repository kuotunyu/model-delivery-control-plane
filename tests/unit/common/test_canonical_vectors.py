from __future__ import annotations

import math
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel

from mdcp.common.canonical import CanonicalizationError, canonicalize_json, parse_json_bytes
from mdcp.common.digests import content_digest, sha256_hex, verify_ed25519

FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures" / "crypto"
PAYLOAD_SHA256 = "03a17e22b7b64db833cca8a9397cc120f61b0077c27a2e7a5ebc89b5da88b997"
RFC8032_TEST_VECTOR_1_PUBLIC_HEX = (
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)


def test_route_plan_vector_is_byte_exact_and_signature_valid() -> None:
    payload = parse_json_bytes((FIXTURE_ROOT / "route-plan-v1.json").read_bytes())
    canonical = canonicalize_json(payload)
    canonical_hex = (FIXTURE_ROOT / "route-plan-v1.canonical.hex").read_text(
        encoding="ascii"
    ).strip()
    public_key = bytes.fromhex(
        (FIXTURE_ROOT / "route-plan-v1.public.hex").read_text(encoding="ascii").strip()
    )
    signature = bytes.fromhex(
        (FIXTURE_ROOT / "route-plan-v1.signature.hex").read_text(encoding="ascii").strip()
    )

    assert public_key.hex() == RFC8032_TEST_VECTOR_1_PUBLIC_HEX
    assert canonical.hex() == canonical_hex
    assert sha256_hex(canonical) == PAYLOAD_SHA256
    verify_ed25519(public_key, canonical, signature)
    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, canonical)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    with pytest.raises(CanonicalizationError, match="non-finite number"):
        canonicalize_json({"nested": [value]})


@pytest.mark.parametrize(
    "raw",
    [b'{"revision":1,"revision":2}', b'\xff{"revision":1}', b'{"value":NaN}'],
)
def test_ambiguous_or_non_utf8_json_is_rejected(raw: bytes) -> None:
    with pytest.raises(CanonicalizationError):
        parse_json_bytes(raw)


def test_content_digest_uses_json_mode_and_rfc8785_bytes() -> None:
    class DigestFixture(BaseModel):
        z: int
        a: str

    model = DigestFixture(z=2, a="bike")

    assert content_digest(model) == sha256_hex(b'{"a":"bike","z":2}')
