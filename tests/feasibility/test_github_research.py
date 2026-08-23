from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from mdcp.feasibility.gate import GateStatus, evaluate_research

REPOSITORY_ROOT = Path(__file__).parents[2]
RESEARCH_PATH = REPOSITORY_ROOT / "docs" / "research" / "github-supply-chain-capability.md"


def test_research_records_permissions_subject_and_read_only_boundary() -> None:
    research = RESEARCH_PATH.read_text(encoding="utf-8")

    assert "Retrieved: 2026-08-24" in research
    assert "packages: write" in research
    assert "attestations: write" in research
    assert "id-token: write" in research
    assert "fully-qualified image name" in research
    assert "must not include a tag" in research
    assert "No remote mutation performed" in research
    assert "does not verify" in research


def test_research_uses_only_official_github_documentation_urls() -> None:
    research = RESEARCH_PATH.read_text(encoding="utf-8")
    urls = re.findall(r"https://[^)\s]+", research)

    assert len(urls) >= 4
    assert {urlparse(url).hostname for url in urls} == {"docs.github.com"}


def test_research_gate_fails_if_a_nonofficial_source_is_added(tmp_path: Path) -> None:
    tampered = tmp_path / "research.md"
    tampered.write_text(
        RESEARCH_PATH.read_text(encoding="utf-8")
        + "\n[untrusted](https://example.com/supply-chain)\n",
        encoding="utf-8",
    )

    assert evaluate_research(RESEARCH_PATH).verdict is GateStatus.PASS
    assert evaluate_research(tampered).verdict is GateStatus.FAIL
