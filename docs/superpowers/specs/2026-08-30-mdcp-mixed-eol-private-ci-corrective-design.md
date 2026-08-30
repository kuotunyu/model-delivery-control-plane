# MDCP Mixed-EOL Private CI Corrective Design

## Status

- Date: 2026-08-30
- Repository: `kuotunyu/model-delivery-control-plane`
- Branch: `codex/wave0-foundation-feasibility`
- Corrective base commit: `13b922849f89691ab2d98d89d8750bee40309f32`
- Failed Windows Portfolio CI run:
  `https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33316653641`
- Current repository visibility: Private
- Selected approach: repository-native mixed-EOL checkout contract with fresh-checkout regression

本 corrective 只修正 Windows fresh checkout 對 frozen byte identities 的 materialization。
`docs/superpowers/specs/2026-08-30-mdcp-windows-native-portfolio-ci-corrective-design.md`
仍是 workflow、runner 與 external-action boundary 的上位設計；本文件僅取代其中假設
`core.autocrlf=true` 足以重建既有 bytes 的部分。未在本文件明確變更的 release、P2、H2、
model/data、production、repository ownership 與 external-action 禁止事項全部維持有效。

## 1. Problem statement

Windows-native corrective commit `13b922849f89691ab2d98d89d8750bee40309f32` 已通過本機完整
verification 與 independent review：

```text
1625 passed, 7 skipped
Critical: 0
Important: 0
```

相同 commit 的 Private Windows Portfolio CI run `33316653641` 則以：

```text
34 failed, 1592 passed, 6 skipped in 1099.01s
```

結束。失敗發生於完整 pytest step；tracked-file mutation step 因前一步失敗而未執行。
本 run 的 terminal state 與完整 pytest summary 是透過 authenticated GitHub UI readback 取得；
當時 GitHub REST API rate limit 已耗盡，因此未把無法驗證的 API response 當成 evidence。

Systematic debugging 證實問題不是 workflow authority、production behavior 或 frozen identity
algorithm，而是 repository 尚未宣告完整的 mixed-EOL checkout contract：

1. Git index 中的 tracked blobs 是 LF-normalized；
2. 既有本機 worktree 的 frozen identity profile 卻包含精確 16 個 CRLF paths；
3. Windows runner 在 `core.autocrlf=true` 下把近乎所有 text paths materialize 成 CRLF；
4. 因此原本應維持 LF 的 identity inputs 也改變 bytes，連帶破壞 v1/v2 serving identity、
   search inventory、Wave 1 inventory、golden vectors 與 contract-gate assertions；
5. 對 unchanged commit rerun不會測試新假設，也不能修正 repository checkout semantics。

本 corrective 的目標是讓 Git 在任何支援的 `core.autocrlf` user setting 下，從相同 commit
materialize 相同的專案定義 bytes，而不是改寫 identity implementation 或接受新的 identities。

## 2. Authoritative byte profile

### 2.1 LF baseline

所有未被精確覆寫的 tracked text paths 以 LF materialize。這包含 public reviewer surface、
schema、workflow、Python source，以及所有其他 identity-bound text paths。

Repository baseline 使用：

```gitattributes
* text=auto eol=lf
```

`text=auto` 讓 Git 只對判定為 text 的內容進行 EOL normalization；它不把所有檔案強制視為
text。Known binary subtree 仍受獨立 `-text` rule 保護，並由 regression 以 byte equality 驗證。

### 2.2 Exact CRLF exceptions

只有下列 16 個既有 frozen inputs 必須在 checkout materialize 為 CRLF：

```text
docs/superpowers/plans/2026-08-23-mdcp-wave-0-foundation-feasibility.md
docs/superpowers/plans/2026-08-23-mdcp-wave-1-workload-identity.md
docs/superpowers/plans/2026-08-23-mdcp-wave-2-validator-supply-chain.md
docs/superpowers/plans/2026-08-23-mdcp-wave-3-control-routing-shadow.md
docs/superpowers/plans/2026-08-23-mdcp-wave-4-windows-policy.md
docs/superpowers/plans/2026-08-23-mdcp-wave-5-canary-recovery.md
docs/superpowers/plans/2026-08-23-mdcp-wave-6-observability-reviewer.md
docs/superpowers/plans/2026-08-23-mdcp-wave-7-release-closure.md
docs/superpowers/plans/2026-08-23-model-delivery-control-plane-plan-index.md
docs/superpowers/specs/2026-08-23-model-delivery-control-plane-design.md
evidence/public/feasibility/wave0-report.json
src/mdcp/temporal/firewall.py
src/mdcp/temporal/runner.py
src/mdcp/temporal/search_identity.py
tests/fixtures/artifacts/candidate/artifact-descriptor.json
tests/fixtures/artifacts/stable/artifact-descriptor.json
```

每個 exception 都以 exact repository-relative path 與 `text eol=crlf` 宣告；禁止 glob、directory
wildcard 或 extension-wide CRLF rule。`src/mdcp/temporal/run_evidence.py` 現行 authoritative
worktree bytes 是 LF，因此不得加入 exception list。

### 2.3 Binary and public LF protection

既有 rules 需保留：

- `tests/fixtures/supply-chain/** -text` 必須在 global text baseline 後保持 authoritative；
- 十個 `PUBLIC_SURFACE_PATHS` 的既有 explicit LF rules 必須保留；
- `.gitattributes` 本身納入 fresh-checkout regression；
- known supply-chain binary fixtures 在所有 checkout modes 必須與 source blobs byte-identical。

如果 TDD RED test 顯示 rule ordering 無法讓 `-text` 保持 authoritative，implementation 只能以
更精確的 binary attribute 修正同一 subtree；不得放寬成 generic binary policy。Acceptance
criterion 是 bytes 不變，而不是僅檢查 `git check-attr` 的文字輸出。

## 3. Approaches considered

### 3.1 Selected: repository-native mixed-EOL contract

在 `.gitattributes` 宣告 LF baseline 與 16 個 exact CRLF exceptions，讓 checkout semantics 成為
tracked、reviewable、可在 clone 時生效的 repository contract。

這個方案直接控制 identity functions 實際讀取的 bytes，且不依賴 runner-local rewrite、shell
order 或 developer global Git config。它保留所有既有 frozen digests。

### 3.2 Rejected: workflow-local post-checkout rewrite

在 workflow 內用 PowerShell 改寫 paths 會造成 tracked worktree mutation、使 mutation guard
失去訊號，並把 byte contract 藏在單一 CI implementation 中。其他 clone 仍會得到不同 bytes。

### 3.3 Rejected: accept new CRLF-derived identities

修改 identity implementation、fixtures 或 expected digests 以接受 runner bytes，會把 checkout
accident 誤當成新 protocol，破壞 frozen evidence 與先前 review 結論。本 corrective 禁止此作法。

### 3.4 Rejected: rerun unchanged commit

Run `33316653641` 已 terminal failure；unchanged rerun不能驗證 `.gitattributes` hypothesis。
下一個 remote run 必須由 reviewed corrective commit 的一次 non-force push 產生。

## 4. Fresh-checkout regression design

Implementation 採 TDD。第一個 RED test 必須在目前 `.gitattributes` 上重現不同 checkout
settings 產生不同 bytes，之後才修改 attribute contract。

Regression 建立不需 network 的 local source repository，提交 production `.gitattributes` 與
受測 tracked files，再分別以以下 settings clone 到短 temporary paths：

```text
core.autocrlf=true
core.autocrlf=false
core.autocrlf=input
```

短 path 是必要的 test harness property：先前 diagnostic 在深層 ignored workspace 中碰到
Windows path-length `FileNotFoundError`；將 extraction 移至短 path 後相同 tests 正常 collection。
Test 不得因 harness path length 而誤報 EOL failure。

每個 checkout 必須驗證：

1. 16 個 CRLF exceptions 不含 bare LF，且 content line endings 是 CRLF；
2. 所有其他選定 identity-bound text paths 不含 CRLF，並與 expected LF bytes 相同；
3. 十個 `PUBLIC_SURFACE_PATHS` 與 source fixture bytes 相同；
4. known supply-chain binary fixtures 與 source blobs byte-identical；
5. `git check-attr` 回報 exact exceptions、public LF rules 與 binary subtree 的預期 attributes；
6. 三個 checkout modes 的分類結果與 frozen digest results 完全一致。

Regression 不能只逐字比對目前 worktree，因為此 worktree 的 CRLF bytes 是被測 contract 的一部分。
Expected profile 必須由 exact path lists 與 canonical byte expectations建立，避免測試把 accidental
worktree state 當 oracle。

## 5. Frozen identity acceptance

本 corrective 不允許 identity migration。Focused verification 必須證明下列 frozen values 保持
不變：

```text
v1 serving identity:
d81af556dbc06b3f9d703f38f47867044f99d3d908a7bfc816c8bf6a60719209

v2 serving identity:
198610d3cfcb48bf713b414a1d11073c2ac2e438f4a4dd99fc8dd907789152ea

uv.lock SHA-256:
781845de1b742769bbc446906425dcd9f74358ec457bdb1d28b63699ec1277ae
```

Focused suite 至少覆蓋：

```text
tests/contract/workload/test_serving_identity_isolation.py
tests/contract/workload/test_serving_identity_v2.py
tests/contract/workload/test_wave1_inventory.py
tests/integration/temporal/test_contract_gate.py
tests/integration/temporal/test_search_freeze_preflight.py
tests/unit/temporal/test_golden_vectors.py
```

Diagnostic mixed-EOL profile 已在短-path extraction 上取得：

```text
126 passed, 2 skipped in 116.14s
```

這只支持 root-cause hypothesis，不是 implementation completion evidence。正式 corrective 仍須通過
新增 regression、所有 focused gates、完整 local suite 與 independent review。

## 6. Truthful readiness v1.2

現有 readiness v1.1 真實記錄 failed Ubuntu staging run，但尚未記錄 Windows EOL failure。
Corrective commit 在任何新 push 前，必須演進為 closed intermediate state：

```text
schema_version: mdcp.local-release-readiness.v1.2
evidence_class: github_private_staging_eol_corrective_readiness
claim_ceiling: mdcp.private-staging-eol-corrective-claim-ceiling.v1
portfolio_ci_commit: 13b922849f89691ab2d98d89d8750bee40309f32
portfolio_ci_run_url: https://github.com/kuotunyu/model-delivery-control-plane/actions/runs/33316653641
portfolio_ci_conclusion: failure
```

Execution state 必須維持：

```text
push_executed: true
portfolio_ci_executed: true
portfolio_ci_passed: false
remote_release_executed: false
tag_created: false
production_deployed: false
kubernetes_production_ready: false
h2_executed: false
cv_workload_implemented: false
llm_workload_implemented: false
```

Technical closure verification 同步反映 corrective base 的本機 gate：

```text
full_suite_passed: 1625
full_suite_skipped: 7
review_critical: 0
review_important: 0
review_minor: 0
```

Schema 與 verifier 必須 fail closed：alternate repository/run URL、非 40-hex commit、unknown field、
`portfolio_ci_passed: true` 與 `failure` conclusion 的 impossible combination、或任何 affirmative
release/production/model/data claim 都必須被拒絕。

README 與 reviewer docs 必須同時保留兩筆 remote history：

- Ubuntu run `33311024512`：platform-contract failure；
- Windows run `33316653641`：mixed-EOL materialization failure。

文件須明確說 repository 仍是 Private、corrective 尚未 remote-pass，且不得顯示 success badge 或
暗示 release、production、cross-platform、Kubernetes production、model/data execution 已完成。

## 7. Public surface inventory

`PUBLIC_SURFACE_PATHS` 維持既有十個 exact paths，不加入 `.gitattributes` 或 readiness record。
`.gitattributes` 仍由獨立 fresh-checkout regression 保護；readiness record 仍不能 hash 自己。

因 README、reviewer docs、schema 與 verifier bytes 會演進，implementation 在所有內容固定後必須
重新產生 canonical `public_surface_entries` 與 `public_surface_inventory_sha256`。Unchanged entries
也要從 final physical files 重新讀取，不得手動沿用舊 size/hash。

## 8. Corrective execution sequence

1. 寫 implementation plan，逐步列出 TDD RED、minimal GREEN、focused/full verification、review、
   commit、push 與 remote readback gates；
2. 先新增 fresh-checkout/mixed-EOL regression，確認目前 attributes 產生預期 RED；
3. 只修改 `.gitattributes` 建立 LF baseline、binary protection 與 16 個 CRLF exceptions；
4. 跑 fresh-checkout test 與 frozen identity focused suite；
5. 更新 readiness v1.2、schema、verifier、README、reviewer docs 與 canonical inventory；
6. 跑 publication focused tests、public verifier、reviewer demo、fast path、Ruff、lock check、frozen
   identity/security gates 與完整 local suite；
7. 完成 independent spec/quality review，必須是 Critical `0`、Important `0`；
8. 使用既有 commit identity 提交 corrective，並再次確認 GitHub repository 仍是 Private；
9. 只做一次 non-force push 到 remote `main`，等待該 exact commit 的新 Windows Portfolio CI run；
10. 以 authenticated API readback 驗證 repository、head SHA、workflow、job/step conclusions 與
    negative checks；必要時才以 authenticated UI 補充 terminal log evidence；
11. 如果 run 失敗，保持 Private、保留 run、進入 systematic debugging，不進 Task 3；
12. 只有 replacement Windows run 成功後，才回到既有 Task 3 final readiness v2 sequence。

禁止 rerun unchanged commit。禁止在 GitHub REST rate limit 尚未恢復、或無法完成 authenticated
negative readback 時進行下一次 push。

## 9. Exact implementation path allowlist

本 corrective implementation 只能修改：

```text
.gitattributes
README.md
docs/reviewer/quickstart.md
docs/reviewer/release-evidence.md
evidence/public/portfolio/local-release-readiness.json
schemas/portfolio/local-release-readiness.schema.json
scripts/verify-public-release.py
tests/publication/test_public_release_surface.py
docs/superpowers/plans/2026-08-30-mdcp-mixed-eol-private-ci-corrective.md
```

本 design spec 獨立提交，不算 implementation path。Implementation plan 也必須獨立提交，再開始
TDD work。

不得修改：

- `.github/workflows/portfolio-ci.yml` 或 `.github/workflows/release-ci.yml`；
- 任何 `src/mdcp` production path；
- `V1_SERVING_PATHS`、`V2_SERVING_PATHS`、identity implementation 或 expected frozen digest；
- `uv.lock`、dependency、Docker/Compose configuration、model/data fixture 或 historical evidence；
- local `main`、其他 branch、其他 repository 或 remote settings。

若 RED test 證明 exact allowlist 不足，必須停止並提出新 design delta；不得以既有一般授權擴張路徑。

## 10. Verification and review gates

Corrective commit 前的 mandatory local gates：

- new mixed-EOL fresh-checkout regression for all three `core.autocrlf` modes；
- publication-focused test file；
- frozen v1/v2/search/Wave 1/golden/contract focused suite；
- `uv lock --check`；
- Ruff check 與 changed-Python formatting policy；
- public verifier、deterministic reviewer demo 與 reviewer fast path；
- complete pytest suite with cache provider disabled；
- tracked-file mutation check；
- independent review with Critical `0` and Important `0`；
- exact staged-path allowlist 與 `git diff --check`。

Remote Windows Portfolio CI 是額外 evidence，不能取代任何 local gate。若 local full-suite count 因
新增 tests 合理增加，必須在 execution log 與 review evidence 記錄 fresh run 的實際結果。
Readiness v1.2 的 `1625/7` 則刻意驗證其所錨定的 failed base commit `13b9228…`，不得用後續
corrective commit 的 test count 改寫歷史；後續 final readiness v2 依其 implementation plan 記錄
最終 corrective closure。

## 11. External-action and stop boundaries

本 corrective 唯一預先核准的 external mutation 是：local implementation/review 全部通過後，對
既有 Private repository 的 remote `main` 做一次 non-force push。除此之外：

- 不建立或刪除 repository；
- 不改 visibility；
- 不 merge、force-push、tag、release、package、GHCR、deploy 或 dispatch `release-ci`；
- 不啟動 container、network、model/data execution、P2 或 H2 rows；
- 不修改 auth scopes，不接觸其他 repository；
- 不刪除既有 failed runs、evidence history 或 custody；
- 不以 success badge 或文件文字提前宣告通過。

進入 Public visibility 前仍須滿足原 safe-publication design 的 package readback authorization 與所有
final external gates。本 corrective 的成功只表示 Private Windows Portfolio CI 能從 deterministic
fresh checkout 重建既有 contract，不代表 release 或 production readiness。

## 12. Acceptance criteria

只有同時滿足下列條件，本 corrective 才算 technical closure：

1. `.gitattributes` 精確表達 LF baseline、16 個 CRLF exceptions、binary protection 與 public LF
   rules；
2. `core.autocrlf=true/false/input` 三種 fresh checkouts 產生相同 expected byte profile；
3. known binary fixtures byte-identical；
4. v1/v2 identities、search/Wave 1 inventories、golden vectors 與 `uv.lock` digest 未變；
5. readiness v1.2 與 docs 如實記錄 run `33316653641` failure，所有 forbidden claims 為 false；
6. canonical public inventory 從 final files 重新產生並通過 verifier；
7. 所有 local gates 通過，independent review 為 Critical `0`、Important `0`；
8. corrective commit 的 changed paths 完全落在 allowlist；
9. 一次 non-force push 產生新 Windows Portfolio CI run，且該 run 對 exact corrective commit 成功；
10. authenticated readback 證實 repository 仍是 Private，沒有 release/tag/package/deployment、
    permission escalation、release-ci dispatch 或其他 forbidden side effect。

若第 9 或第 10 點不成立，corrective 保持 open、repository 保持 Private，並停在 Task 2 的
systematic-debugging boundary；不得進 Task 3 或 Public transition。
