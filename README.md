<!-- lang: zh-TW -->
# Model Delivery Control Plane

> 把「模型表現較好」與「模型可以取得 production traffic」分開：offline score 不等於 deployment permission。

## 30 秒理解這個專案

Model Delivery Control Plane（MDCP）是一個 evidence-gated model delivery reference
implementation。它示範如何把 workload contract、content-addressed identity、offline
validation、temporal leakage controls、dedicated formal worker 與 fail-closed evidence boundary
串成一條可審查的 delivery path。

目前具體 workload 是 bike-demand **temporal regression**。這個 repository 展示的 delivery
controls 可轉用於 ML、AI、Computer Vision 與 LLM engineering，但不把架構可轉用性誤寫成已經
完成那些 workload。

## 目前完成度

| Surface | Status | 可驗證內容 |
|---|---|---|
| Workload contracts 與 serving identity | Implemented | strict schemas、source/content digests、identity isolation |
| Offline artifact、bundle 與 temporal validation | Verified locally | deterministic fixtures、完整測試與 security gates |
| Dedicated formal worker 與 static firewall | Verified locally | bounded subprocess transport、recovery seal、AST/capability pins |
| Control service、router、canary、rollback、recovery | Designed only | architecture/specification，沒有 end-to-end deployment claim |
| GitHub release workflow | Not executed remotely | checked-in workflow 可供 inspection；本 slice 未執行 remote release |

## 對應 ML／AI／CV／LLM 職務能力

以下對照的是這個 repository 可直接驗證的 engineering evidence；CV／LLM 欄位表示
delivery-control patterns 的可轉用性，不是已完成對應 workload。

| 目標職務／能力 | 可直接檢查的 evidence | 誠實邊界 |
|---|---|---|
| ML Engineer | [workload contract](src/mdcp/contracts/workload.py)、[v2 serving identity](src/mdcp/contracts/serving_identity_v2.py)、[contract tests](tests/contract/workload/test_serving_identity_v2.py) | 已實作的具體 workload 是 temporal regression |
| AI Engineer | [offline validator](src/mdcp/validator/service.py)、[bundle verification](src/mdcp/verify/bundle.py)、[local readiness](evidence/public/portfolio/local-release-readiness.json) | local verification 不等於 remote release 或 production evidence |
| Computer Vision / LLM Engineer | [content-addressed serving identity](src/mdcp/contracts/serving_identity_v2.py)、[release evidence taxonomy](docs/reviewer/release-evidence.md) | engineering pattern 可轉用；不宣稱已實作 CV 或 LLM workload |
| MLOps / reliability / security | [dedicated formal worker](src/mdcp/temporal/formal_worker.py)、[static firewall](src/mdcp/temporal/firewall.py)、[runtime guards](src/mdcp/temporal/runtime_guards.py) | control/router/canary/rollback/recovery 仍是 Designed only |

## 實際 implemented verification path

```mermaid
flowchart LR
    A[Workload contracts + source bytes] --> B[Content-addressed identities]
    B --> C[Offline artifact / bundle validators]
    C --> D[Temporal protocol + dedicated formal worker]
    D --> E[Static firewall + runtime guards]
    E --> F[Canonical public evidence]
```

完整的 actual-vs-designed 說明與 component matrix 請見
[Architecture](docs/architecture.md)。

## Portfolio CI 與 Release CI 的 authority boundary

| Surface | Status | 可主張範圍 |
|---|---|---|
| Portfolio CI | Public；Windows-native remote gate 已通過；evidence recorded during Private staging | mixed-EOL corrective commit 與 exact success run 可直接核對 |
| Release CI | Manual design surface only | 未 dispatch；不是 release evidence |

repository is Public; portfolio_ci_passed: true
Windows-native success commit: 8bc91a548846af0b1f1be1fc9ae6fbb80b7f63f1
Windows-native success run: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33322212462
The mixed-EOL corrective passed Windows-native remote Portfolio CI during Private staging.
WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY
Linux read-only smoke (not portability proof)
Linux read-only smoke first-run commit: c31337bae7a6b6a988984368821337158392c94f
Linux read-only smoke failed run: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33334963036
The first run passed verifier/demo before the Windows-only golden vector failed closed; this corrective verifies that boundary without excluding tests.
Linux read-only smoke success commit: 91d80b6e932f72ed95a2fe422966c177fbb7da8d
Linux read-only smoke success run: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33336107355
The corrective passed the bounded Linux smoke and the authoritative Windows gate.
LINUX_READ_ONLY_SMOKE_PASS != CROSS_PLATFORM_PORTABLE
Windows full suite remains the authoritative gate.
Release CI: manual design surface only; not dispatched and not evidence of a release.
所有 release、tag、package、P2、H2、workload、Kubernetes 與 production claims 仍為 false。

## Reviewer fast path

初次建立 dependency environment（若本機沒有 cached packages，這一步可能使用 network）：

```powershell
uv sync --frozen --group ml
```

### 2 分鐘 fail-closed demo

從 repository root 執行 shell-neutral proof：

```text
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
```

`MDCP_DEMO_PASS case=baseline` 表示 baseline local evidence 通過；
`PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID` 是故意偽造 remote release claim 的預期拒絕，
`PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH` 是故意竄改 public surface 的預期拒絕。
所有故意 mutation 都只發生在 memory 或 OS-managed temporary directory；demo 不會修改 repository 內的檔案。這是 local reviewer evidence，不是 remote release 或 production evidence。

之後執行 CPU-only、無資料集、無模型執行、無 Docker、verification 期間無 network 的 warm path：

```powershell
pwsh ./scripts/reviewer-fast-path.ps1
```

預期 warm target 為 3–5 分鐘。完整前置條件、shell-neutral commands 與 full-suite path 請見
[Reviewer quickstart](docs/reviewer/quickstart.md)。

## Evidence 與安全邊界

- Machine-readable local readiness：[local-release-readiness.json](evidence/public/portfolio/local-release-readiness.json)
- Historical public receipt：[search-receipt.json](evidence/public/v02/search/search-receipt.json)
- Historical public index：[evidence-index.json](evidence/public/v02/search/evidence-index.json)
- Evidence taxonomy 與可主張範圍：[Release evidence guide](docs/reviewer/release-evidence.md)
- Security assumptions 與攻擊面：[Threat model](docs/threat-model.md)
- Portfolio CI（repository is Public；Windows-native corrective run 已通過）：[portfolio-ci.yml](.github/workflows/portfolio-ci.yml)
- Release CI（manual design surface，未 dispatch）：[release-ci.yml](.github/workflows/release-ci.yml)

Technical formal closure 是 immutable historical commit
`b1bb0d80cd40e6f39372c0a45892500cc9530712`；後續 publication-only commits 是它的 descendants，
不會把新的 README HEAD 假裝成 freeze HEAD。H2 維持 `SEALED_NOT_LOADED`，loaded rows 為 `0`。

## Architecture 與程式碼導覽

- `src/mdcp/contracts`：workload contract 與 serving identity boundary
- `src/mdcp/validator`、`src/mdcp/verify`：offline artifact 與 release-bundle validation
- `src/mdcp/temporal`：temporal development protocol、formal worker、firewall 與 evidence gates
- `tests/contract`、`tests/security`、`tests/integration`：可重現 contract/security/process verification
- [Architecture](docs/architecture.md)：Implemented verification path 與 Designed deployment path

## 技術棧與測試

Python 3.12、Pydantic 2、RFC 8785 canonical JSON、pytest、Hypothesis、ONNX Runtime、Git、
PowerShell 7 與 GitHub Actions。historical technical closure 的完整測量是
`1546 passed, 7 skipped in 681.43s`；publication tree 必須以當次實際測試結果為準，不能把這個
歷史時間當成保證。

## Claim ceiling

- repository is Public; portfolio_ci_passed: true。Windows-native mixed-EOL corrective commit `8bc91a548846af0b1f1be1fc9ae6fbb80b7f63f1` 的 exact remote run 已於 Private staging 通過。
- WINDOWS_NATIVE_REMOTE_PORTFOLIO_CI_PASS != CROSS_PLATFORM_PORTABLE != REMOTE_RELEASED != PRODUCTION_READY
- 所有 release、tag、package、P2、H2、workload、Kubernetes 與 production claims 仍為 false。
- Release CI 是 manual design surface，未 dispatch；未執行 remote release，也沒有 tag、GitHub Release 或 GHCR publication evidence。
- 不宣稱 Kubernetes production readiness。
- 不宣稱 production HA、multi-region 或 disaster recovery。
- 沒有 real production incident evidence。
- H2 未執行；`SEALED_NOT_LOADED` 不等於 confirmatory result。
- 不宣稱已實作 CV 或 LLM workload；目前實作是 temporal regression。
- 不宣稱支援任意 model framework 或 task。
- local/synthetic PASS 不等於 production evidence。

## License

本專案程式碼採 [MIT License](LICENSE)。第三方 dependency、dataset 或其他材料仍保留其各自
授權條款，不因本 repository 的專案授權而改變。
