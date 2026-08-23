from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel

from mdcp.common.canonical import canonicalize_json


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_digest(model: BaseModel) -> str:
    return sha256_hex(canonicalize_json(model.model_dump(mode="json")))


def verify_ed25519(public_key: bytes, message: bytes, signature: bytes) -> None:
    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
