# Reviewer Quickstart

這條 reviewer path 讓你先在低摩擦、CPU-only 的條件下驗證 repository 的核心 claims，再決定是否
進一步閱讀完整 architecture 與 test suite。

repository remains Private; portfolio_ci_passed: false
Ubuntu failed run: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33311024512
Windows mixed-EOL failed run: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33316653641
The replacement mixed-EOL corrective has not passed remote CI yet.
WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY
Release CI: manual design surface only; not dispatched and not evidence of a release.
所有 release、tag、package、P2、H2、workload、Kubernetes 與 production claims 仍為 false；因此兩者都不表示
remote release、GHCR/package publication、tag、GitHub Release、production deployment、Kubernetes readiness、
H2 execution、CV workload 或 LLM workload 已發生。

## 前置條件

- Python `3.12`
- `uv`
- 完整 Git history（不是 source ZIP，也不是缺少 historical commits 的 shallow clone）
- Fast path 不需要 dataset、GPU、Docker 或 model execution
- PowerShell 7 (`pwsh`) 是 convenience wrapper；所有底層命令也可個別執行

第一次建立 dependency environment：

```powershell
uv sync --frozen --group ml
```

若 packages 尚未在本機 cache，這個 setup step 可能使用 network；它不計入 warm verification
時間。依賴建立完成後，下面的 fast path 使用 `--no-sync`，verification 本身不需要 network。

## 2 分鐘 fail-closed demo

從 repository root 執行這個 shell-neutral proof：

```text
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
```

預期輸出固定為：

```text
MDCP_DEMO_PASS case=baseline
MDCP_DEMO_REJECT case=remote_release_claim reason=PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID
MDCP_DEMO_REJECT case=public_surface_tamper reason=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH
MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0
```

`repository_mutations=0` 表示 demo 前後的 Git porcelain bytes 完全相同。所有故意 mutation 都只存在
於 memory 或 OS-managed temporary directory，不會修改 repository 內的檔案；這是 local reviewer
evidence，不是 remote release 或 production evidence。

```text
WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY
```

## Level 1：Fast path（建議先跑）

```powershell
pwsh ./scripts/reviewer-fast-path.ps1
```

Warm target 是 **3–5 minutes**。wrapper 先驗證 canonical local readiness 與 historical Git
topology，再執行 curated publication/contract/process/security tests；任何一步失敗就回傳 nonzero。

沒有 PowerShell 時，可從 repository root 執行相同的 shell-neutral commands：

```text
uv run --no-sync python scripts/verify-public-release.py --repository-root .
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
uv run --no-sync pytest -p no:cacheprovider -q tests/publication/test_public_release_surface.py tests/publication/test_release_workflow.py tests/contract/workload/test_serving_identity_isolation.py tests/contract/workload/test_serving_identity_v2.py tests/unit/temporal/test_formal_worker_protocol.py tests/integration/temporal/test_formal_worker_process.py tests/security/temporal/test_public_evidence_boundary.py
```

Fast path 預期看到：

```text
PUBLIC_RELEASE_SLICE_PASS
PUBLIC_RELEASE_FAST_PATH_PASS evidence_class=local_portfolio mutations=0
```

## Level 2：Full test path

```text
uv run pytest -q
```

Technical closure 的 historical measurement 是 `1546 passed, 7 skipped in 681.43s`。它只提供
規模與時間參考；publication commits 之後的實際 test count 與 duration 必須以當次輸出為準。

## Level 3：Architecture / deep inspection

建議閱讀：

- [Actual-vs-designed architecture](../architecture.md)
- [Release evidence taxonomy](release-evidence.md)
- [Threat model](../threat-model.md)
- [Private-failed-staging Portfolio CI corrective](../../.github/workflows/portfolio-ci.yml)
- [Manual Release CI design surface](../../.github/workflows/release-ci.yml)

Docker、validator internals 與 workflow source 可以作為 optional deep inspection；這不是要求 reviewer
執行 remote workflow，也不表示 repository 已完成 remote release、production deployment，並且
不宣稱 Kubernetes production readiness。

## 為什麼需要完整 Git history？

Local verifier 會從 immutable Git objects 重新驗證 historical formal closure、direct parents、兩輪
D/D 與 A/A evidence topology，以及 closure blobs 的 receipt/index SHA-256。source ZIP 沒有這些
objects；shallow clone 也可能缺少 ancestors，因此無法完成同等 authentication。

回到 [README](../../README.md)。
