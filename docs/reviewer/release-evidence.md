# Release Evidence Guide

MDCP 不宣稱「某個檢查通過」就代表系統已經 release／production-ready。這份 taxonomy 說明每類
evidence 能支持什麼，也說明哪些 action 沒有發生。

## 五類 evidence

### 1. Historical formal closure evidence

Technical formal closure commit
`b1bb0d80cd40e6f39372c0a45892500cc9530712` content-authenticates 已 review 的
dedicated-worker corrective tree、public search receipt/index 與 H2 sealed state。`1546 passed,
7 skipped` 是 reported historical closure-review measurement；該 terminal output is
not authenticated by the closure commit，因此只能作為有範圍標示的 historical report。

### 2. Local portfolio readiness evidence

[local-release-readiness.json](../../evidence/public/portfolio/local-release-readiness.json) 是
RFC 8785 canonical JSON。它綁定 public surface inventory、historical identities、claim ceiling、
reviewer entrypoint 與所有未執行 action 的 explicit `false` booleans。對應 closed schema 是
[local-release-readiness.schema.json](../../schemas/portfolio/local-release-readiness.schema.json)。

### 3. Synthetic fixture evidence

Deterministic fixtures、golden vectors 與 contract tests 可重現 validator、identity、temporal protocol
與 security behavior。Synthetic/local PASS 是 engineering evidence，不是 production traffic evidence。

### 4. Designed remote release-CI evidence

[release-ci.yml](../../.github/workflows/release-ci.yml) 展示 manual dispatch、least privilege、
digest-pinned actions、formal candidate preflight 與 supply-chain stages。它在這個 slice 中是
Not executed remotely，因此不能被引用為 completed GitHub/GHCR release evidence。

### 5. 不存在的 evidence

未授權或未執行的 action 不建立假證據：沒有 remote release、push、tag、GitHub Release、GHCR
publication、production deployment、real incident、H2 execution、CV workload 或 LLM workload
result。H2 維持 `SEALED_NOT_LOADED`，loaded rows `0`。

## Machine-verifiable bindings

- [Historical search receipt](../../evidence/public/v02/search/search-receipt.json)
- [Historical evidence index](../../evidence/public/v02/search/evidence-index.json)
- [Local readiness evidence](../../evidence/public/portfolio/local-release-readiness.json)
- [Reviewer fast path](../../scripts/reviewer-fast-path.ps1)
- [Read-only verifier](../../scripts/verify-public-release.py)

verifier 會要求 formal closure 是目前 publication branch 的 ancestor，但不要求 current HEAD 等於
closure。這保留 historical freeze 語意，也允許後續純 publication commits。

## Claim ceiling

```text
LOCAL_PORTFOLIO_RELEASE_READY != REMOTE_RELEASED != PRODUCTION_READY
```

因此 local PASS 只表示 repository 的 public slice 在當下 checkout 可重現且證據一致；它不宣稱
production deployed、不宣稱 H2 已執行，也不宣稱 Kubernetes-ready。回到
[README](../../README.md) 查看精簡版範圍說明。
