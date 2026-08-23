from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "crypto"
PAYLOAD_SHA256 = "03a17e22b7b64db833cca8a9397cc120f61b0077c27a2e7a5ebc89b5da88b997"


def test_fresh_python_process_recomputes_and_verifies_vector() -> None:
    script = """
import json
import sys
from pathlib import Path
from mdcp.common.canonical import canonicalize_json, parse_json_bytes
from mdcp.common.digests import sha256_hex, verify_ed25519

root = Path(sys.argv[1])
canonical = canonicalize_json(parse_json_bytes((root / 'route-plan-v1.json').read_bytes()))
public_key = bytes.fromhex((root / 'route-plan-v1.public.hex').read_text(encoding='ascii').strip())
signature = bytes.fromhex(
    (root / 'route-plan-v1.signature.hex').read_text(encoding='ascii').strip()
)
verify_ed25519(public_key, canonical, signature)
print(json.dumps(
    {'canonical_hex': canonical.hex(), 'sha256': sha256_hex(canonical)}, sort_keys=True
))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(FIXTURE_ROOT)],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)

    assert result == {
        "canonical_hex": (FIXTURE_ROOT / "route-plan-v1.canonical.hex").read_text(
            encoding="ascii"
        ).strip(),
        "sha256": PAYLOAD_SHA256,
    }
