from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "release-ci.yml"
PORTFOLIO_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "portfolio-ci.yml"
LOCK_PATH = REPOSITORY_ROOT / "constraints" / "github-actions.lock"
LOCAL_SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "release-ci-local.ps1"
EXPECTED_STAGES = ["build_push", "supply_chain", "final_manifest", "validate", "seal"]
REQUIRED_ACTIONS = {
    "actions/checkout",
    "docker/setup-buildx-action",
    "docker/build-push-action",
    "actions/attest-build-provenance",
    "actions/upload-artifact",
}
PORTFOLIO_ACTIONS = {
    "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
    "astral-sh/setup-uv": "20cfd1bf945f4377ade1205e4dbc17946fc9a30d",
}
EXPECTED_PORTFOLIO_WORKFLOW = (
    """\
name: Portfolio CI

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

permissions:
  contents: read

concurrency:
  group: portfolio-ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  verify:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
      - name: Checkout complete evidence history
        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Set up locked Python and uv
        uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d
        with:
          version: "0.11.18"
          python-version: "3.12"
          enable-cache: false
      - name: Install locked dependencies
        run: uv sync --frozen --group ml
      - name: Verify lock and static checks
        run: |
          uv lock --check
          uv run --no-sync ruff check src/mdcp tests scripts
          uv run --no-sync ruff format --check scripts/verify-public-release.py """
    "tests/publication/test_public_release_surface.py "
    "tests/publication/test_release_workflow.py"
    """
      - name: Verify public evidence and deterministic demo
        run: |
          uv run --no-sync python scripts/verify-public-release.py --repository-root .
          uv run --no-sync python scripts/reviewer-demo.py --repository-root .
      - name: Run complete test suite
        run: uv run --no-sync pytest -p no:cacheprovider -q
      - name: Reject tracked-file mutation
        run: git diff --exit-code
"""
)


def _lock() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in LOCK_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or line.startswith("oci."):
            continue
        name, sha_and_comment = line.split("=", 1)
        entries[name] = sha_and_comment.split("#", 1)[0].strip()
    return entries


def _portfolio_workflow() -> str:
    return PORTFOLIO_WORKFLOW_PATH.read_text(encoding="utf-8")


def test_release_workflow_is_manual_least_privilege_and_repository_bound() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "expected_commit:" in workflow
    assert "pull_request:" not in workflow
    assert re.search(r"^\s*push:\s*$", workflow, re.MULTILINE) is None
    for permission, value in {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
        "attestations": "write",
    }.items():
        assert re.search(rf"^\s{{2}}{permission}: {value}$", workflow, re.MULTILINE)
    assert "github.repository == 'kuotunyu/model-delivery-control-plane'" in workflow


def test_release_workflow_action_refs_are_full_sha_and_match_lock() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    references = dict(
        re.findall(r"^\s*uses: ([a-z0-9_.-]+/[a-z0-9_.-]+)@([0-9a-f]+)\s*$", workflow, re.MULTILINE)
    )

    assert references.keys() >= REQUIRED_ACTIONS
    assert all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in references.values())
    assert references == _lock()


def test_release_workflow_is_acyclic_and_uses_buildkit_digest_once() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    stages = re.findall(
        r"^\s+id: (build_push|supply_chain|final_manifest|validate|seal)$",
        workflow,
        re.MULTILINE,
    )

    assert stages == EXPECTED_STAGES
    assert "rebuild_after_manifest" not in workflow
    assert workflow.count("uses: docker/build-push-action@") == 1
    assert "steps.build_push.outputs.digest" in workflow
    assert "subject-digest: ${{ steps.build_push.outputs.digest }}" in workflow
    assert "provenance: mode=max" in workflow
    assert "sbom: true" in workflow


def test_formal_candidate_gate_precedes_every_remote_mutation() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    preflight = workflow.index("id: formal_candidate_preflight")

    assert "ELIGIBLE_H1_PASS" in workflow
    assert preflight < workflow.index("docker login ghcr.io")
    assert preflight < workflow.index("id: build_push")
    build_inputs = workflow[
        workflow.index("with:", workflow.index("id: build_push")) : workflow.index(
            "id: supply_chain"
        )
    ]
    assert "secrets.GITHUB_TOKEN" not in build_inputs
    assert "build-args:" not in workflow


def test_supply_chain_tools_are_nonroot_and_digest_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    lock_text = LOCK_PATH.read_text(encoding="utf-8")

    assert re.search(r"oci\.anchore/syft=.*-nonroot@sha256:[0-9a-f]{64}", lock_text)
    assert re.search(r"oci\.anchore/grype=.*-nonroot@sha256:[0-9a-f]{64}", lock_text)
    assert "ghcr.io/anchore/syft:v1.51.0-nonroot@sha256:" in workflow
    assert "ghcr.io/anchore/grype:v0.117.0-nonroot@sha256:" in workflow
    assert "anchore/scan-action" not in workflow


def test_local_validate_only_runner_has_no_remote_mutation_command() -> None:
    script = LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
    prohibited = (
        r"\bgh\s+(repo|workflow|release|api)",
        r"docker\s+login",
        r"docker\s+push",
        r"git\s+push",
        r"attest-build-provenance",
    )

    assert "ValidateOnly" in script
    assert "RELEASE-CI LOCAL PASS evidence_class=dev/test mutations=0" in script
    assert all(re.search(pattern, script, re.IGNORECASE) is None for pattern in prohibited)


def test_task_2_7_recorded_remote_evidence_is_not_fabricated() -> None:
    recorded = REPOSITORY_ROOT / "tests" / "fixtures" / "supply-chain" / "recorded-release-ci"

    assert not recorded.exists()


def test_portfolio_workflow_rejects_any_added_authority_or_command() -> None:
    assert _portfolio_workflow() == EXPECTED_PORTFOLIO_WORKFLOW


def test_portfolio_workflow_has_only_main_push_and_pull_request_triggers() -> None:
    workflow = _portfolio_workflow()

    assert workflow.startswith("name: Portfolio CI\n")
    assert re.search(
        r"^on:\n  push:\n    branches:\n      - main\n"
        r"  pull_request:\n    branches:\n      - main\n$",
        workflow,
        re.MULTILINE,
    )
    assert all(
        trigger not in workflow
        for trigger in ("workflow_dispatch", "schedule:", "tags:", "release:")
    )


def test_portfolio_workflow_is_read_only_and_bounded() -> None:
    workflow = _portfolio_workflow()

    assert "permissions:\n  contents: read\n\nconcurrency:" in workflow
    assert re.search(
        r"^concurrency:\n  group: portfolio-ci-\$\{\{ github\.workflow \}\}-"
        r"\$\{\{ github\.ref \}\}\n  cancel-in-progress: true$",
        workflow,
        re.MULTILINE,
    )
    assert "runs-on: ubuntu-24.04" in workflow
    assert "timeout-minutes: 30" in workflow
    assert re.search(r"^    permissions:", workflow, re.MULTILINE) is None
    assert re.search(r"\b(?:contents|packages|id-token|attestations): write\b", workflow) is None


def test_portfolio_workflow_pins_setup_and_checks_out_complete_history() -> None:
    workflow = _portfolio_workflow()
    reference_pairs = re.findall(
        r"^\s*uses: ([a-z0-9_.-]+/[a-z0-9_.-]+)@([0-9a-f]+)\s*$", workflow, re.MULTILINE
    )
    references = dict(reference_pairs)

    assert references == PORTFOLIO_ACTIONS
    assert len(reference_pairs) == len(references)
    assert all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in references.values())
    assert re.search(
        r"uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
        r"        with:\n          fetch-depth: 0\n          persist-credentials: false",
        workflow,
    )
    assert re.search(
        r"uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d\n"
        r'        with:\n          version: "0\.11\.18"\n'
        r'          python-version: "3\.12"\n          enable-cache: false',
        workflow,
    )


def test_portfolio_workflow_runs_only_the_read_only_local_gate() -> None:
    workflow = _portfolio_workflow()

    for command in (
        "uv sync --frozen --group ml",
        "uv lock --check",
        "uv run --no-sync ruff check src/mdcp tests scripts",
        "uv run --no-sync ruff format --check scripts/verify-public-release.py "
        "tests/publication/test_public_release_surface.py "
        "tests/publication/test_release_workflow.py",
        "uv run --no-sync python scripts/verify-public-release.py --repository-root .",
        "uv run --no-sync python scripts/reviewer-demo.py --repository-root .",
        "uv run --no-sync pytest -p no:cacheprovider -q",
        "git diff --exit-code",
    ):
        assert command in workflow
    assert all(
        prohibited not in workflow.casefold()
        for prohibited in (
            "secrets",
            "docker",
            "ghcr",
            "oidc",
            "attestation",
            "upload",
            "packages",
        )
    )
    assert all(
        prohibited not in workflow
        for prohibited in ("release:", "tags:", "workflow_dispatch:", "schedule:")
    )
