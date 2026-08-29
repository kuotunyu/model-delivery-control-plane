# MDCP Deterministic Recruiter Demo Design

- Status: approved design direction; written specification awaiting owner review
- Date: 2026-08-30
- Audience: Taiwan-based ML Engineer, AI Engineer, Computer Vision Engineer, LLM Engineer, and technical reviewers
- Primary language: 正體中文 (`zh-TW`), with established technical terms kept in English
- Publication boundary: local Git branch only; no remote creation, push, tag, release, workflow execution, or network campaign

## 1. Purpose

目前 repository 已有完整的 zh-TW README、actual-vs-designed architecture、offline fast path 與
canonical readiness evidence。下一個最高效益的 local enhancement 不是英文履歷或新的大型
workload，而是一個約兩分鐘、可由技術 reviewer 親手執行的 deterministic demo。

demo 必須直接證明 MDCP 的核心主張：正常且完整的 evidence 可以通過，但把未執行的 action 改成
已執行，或竄改被 identity 綁定的 public bytes，都會被 fail-closed boundary 以固定 reason code
拒絕。它不是 model-quality demo，也不把 local rejection evidence 誤寫成 production evidence。

## 2. Selected approach

新增 cross-platform `scripts/reviewer-demo.py`，重用現有 read-only public-release verifier、closed
readiness model 與 canonicalization implementation。script 只讀目前 repository，並把所有故意
mutation 限制在 memory 或 OS-managed temporary directory。

這個方案優於兩個替代方案：

- **Documentation-only tour**：成本最低，但 reviewer 只能閱讀 assertion，無法直接看到真實
  fail-closed behavior。
- **New CV or LLM workload**：domain signal 較強，但需要新的 workload contract、fixture、identity、
  validation 與 evidence cycle；此時加入會稀釋已完成的 delivery-control story。

英文履歷與英文 README 不屬於本階段。root `README.md` 繼續以 zh-TW 作為唯一主要入口。

## 3. Reviewer interface

從 repository root 執行：

```text
uv run --no-sync python scripts/reviewer-demo.py --repository-root .
```

成功時依序輸出四行穩定 terminal：

```text
MDCP_DEMO_PASS case=baseline
MDCP_DEMO_REJECT case=remote_release_claim reason=PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID
MDCP_DEMO_REJECT case=public_surface_tamper reason=PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH
MDCP_REVIEWER_DEMO_PASS cases=3 repository_mutations=0
```

任何 case 未得到精確結果、Git porcelain state 在執行前後不一致、temporary cleanup 失敗，或發生
未分類 exception 時，script 必須回傳 nonzero。失敗輸出只能包含固定 public-safe reason code，不得
輸出 absolute path、temporary path、file contents、raw exception、environment 或 private custody
資訊。

在目前 project baseline environment 的 warm run 必須於 `120` 秒內完成；這是 acceptance budget，
不是對所有 reviewer hardware 的效能保證。實際 measured duration 只寫入 task report，不寫入
canonical readiness evidence。

四行 success terminals 必須先保存在 memory；只有三個 cases、temporary cleanup 與 final no-clobber
check 全部通過後才依序寫入 stdout。任何 failure 的 stdout 必須為空，避免同一次執行同時留下
PASS 與 FAIL 的矛盾結果。

## 4. Demo cases

### 4.1 Baseline

以使用者提供的 `--repository-root` 呼叫現有 `verify_public_release`。這會驗證 canonical readiness、
public evidence scanner、public-surface inventory、Markdown links、historical Git parent/diff topology、
closure blobs 與 ancestry。只有完整 verifier 通過後才能輸出 baseline PASS。

### 4.2 False remote-release claim

讀取已通過 baseline 的 readiness document，在 memory 中把
`claim_execution.remote_release_executed` 從 `false` 改成 `true`，重新 RFC 8785 canonicalize，然後
交給真正的 `parse_readiness_bytes`。closed `Literal[False]` contract 必須產生
`PUBLIC_RELEASE_SLICE_EVIDENCE_INVALID`；其他 reason、exception 或意外 PASS 都使 demo nonzero。

這個 case 只證明未授權 claim 會被拒絕，不建立 remote-release evidence。

### 4.3 Public-surface byte tamper

在 `TemporaryDirectory` 中複製 `PUBLIC_SURFACE_PATHS` 與 readiness file，保留 logical relative
paths，然後只修改 temporary `README.md` bytes。對 temporary root 執行真正的
`verify_public_release`；inventory gate 必須在 link 或 Git checks 前產生
`PUBLIC_RELEASE_SLICE_INVENTORY_MISMATCH`。

temporary fixture 不得包含 `.git`、dataset、model、private evidence 或 external custody。cleanup
由 context-managed temporary directory 負責，demo 不提供保留 fixture 的 option。

## 5. No-clobber and capability boundary

script 在第一個 case 前與所有 cleanup 後，透過固定 Git arguments 取得
`status --porcelain=v1 --untracked-files=all`，並要求 before/after bytes 完全相等。最後的
`repository_mutations=0` 精確表示 Git porcelain state delta 為零；它不表示 remote 或 production
state 已被檢查。

允許的 capabilities 僅限：

- read repository-relative public files;
- read fixed historical Git objects through existing verifier behavior;
- allocate、write、read and delete an OS-managed temporary directory;
- emit fixed stdout/stderr terminals.

禁止 network、dependency installation、dataset/model access、formal producer、H2 authorization or
execution、Docker、workflow execution、remote mutation、callback/plugin loading、arbitrary command
execution，以及 repository 內的 write。

## 6. Public-surface identity evolution

`scripts/reviewer-demo.py` 是 recruiter-facing executable surface，不能成為未被 evidence 綁定的
旁路。因此 `PUBLIC_SURFACE_PATHS` 從八個演進為九個，保持 ASCII byte ordering：

```text
LICENSE
README.md
docs/architecture.md
docs/reviewer/quickstart.md
docs/reviewer/release-evidence.md
schemas/portfolio/local-release-readiness.schema.json
scripts/reviewer-demo.py
scripts/reviewer-fast-path.ps1
scripts/verify-public-release.py
```

readiness evidence 自身仍排除於 inventory，維持 acyclic。`.gitattributes` 新增精確
`scripts/reviewer-demo.py text eol=lf`；不得使用 wildcard 或 basename-recursive pattern。

`scripts/verify-public-release.py`、README、quickstart、fast-path wrapper 與新 demo 的合法 publication
變更會使 public-surface entries 與 inventory SHA-256 演進。若 Pydantic-generated JSON Schema bytes
未因 tuple constant 改變而演進，checked-in schema 必須保持 byte-identical；不得為製造 schema diff
而修改 model contract。

所有 production、temporal、serving、source、worker、firewall、receipt、index、dependency-lock 與
historical closure identities 必須保持不變。

## 7. Documentation integration

README 的 reviewer section 加入「2 分鐘 fail-closed demo」命令、四行 expected terminal 的精簡說明，
並明確說明 mutation 不會發生在 repository 中。

`docs/reviewer/quickstart.md` 在現有 Level 1 fast path 前加入 demo entrypoint。既有三層 reviewer path
不重新編號為另一套產品流程；demo 是進入 Level 1 前的短 proof，fast path 仍是正式 curated gate。

`scripts/reviewer-fast-path.ps1` 在 standalone verifier 通過後執行 demo，再執行現有 curated tests。
任何 demo nonzero 都必須 fail fast，finally block 仍須檢查 repository state 並還原 location 與
`PYTHONDONTWRITEBYTECODE`。

## 8. Error behavior

expected rejections 是 demo 的成功案例；只有精確 case/reason pair 才能輸出
`MDCP_DEMO_REJECT`。以下情況全部是 demo failure：

- baseline verifier failure;
- mutation 意外通過；
- mutation 產生非預期 reason code；
- source／destination 是 link、reparse point 或非 regular file；
- Git before/after state 不一致；
- temporary cleanup failure；
- uncaught or malformed input。

public CLI failure terminal 只能使用以下固定 taxonomy，不輸出 traceback、input token 或原始
exception text：

```text
MDCP_REVIEWER_DEMO_FAIL reason=MDCP_REVIEWER_DEMO_BASELINE_INVALID
MDCP_REVIEWER_DEMO_FAIL reason=MDCP_REVIEWER_DEMO_CASE_INVALID
MDCP_REVIEWER_DEMO_FAIL reason=MDCP_REVIEWER_DEMO_STATE_CHANGED
MDCP_REVIEWER_DEMO_FAIL reason=MDCP_REVIEWER_DEMO_INTERNAL
```

custom argument-parser error path 必須把 unknown／malformed arguments 映射到
`MDCP_REVIEWER_DEMO_INTERNAL`，不得回顯 user-supplied token。baseline 的底層 fixed verifier reason
只用於 internal classification，不直接拼入 failure terminal。

## 9. Testing strategy

implementation 必須使用 TDD。先加入會因 demo script 不存在而失敗的 subprocess behavior test，再
實作最小 script。測試至少覆蓋：

- exact four-line successful output and exit code 0;
- real baseline verifier invocation;
- exact false-claim rejection code;
- exact temporary byte-tamper rejection code;
- before/after repository state equality；
- temporary fixture cleanup；
- unexpected reason、unexpected PASS 與 internal exception 的 sanitized nonzero behavior；
- failure 不得留下 partial PASS stdout；
- nine-path inventory order、membership、acyclic digest and EOL portability；
- fast-path ordering、fail-fast and failure-path no-clobber；
- README/quickstart command and claim wording。

完成前必須重跑 publication tests、standalone demo、public verifier、fast path、full suite、Ruff、format、
`uv lock --check`、`git diff --check`、all frozen identities 與 independent whole-range review。

## 10. Planned file scope

design spec核准後的 implementation plan 可修改或新增的候選路徑限於：

```text
.gitattributes
README.md
docs/reviewer/quickstart.md
scripts/reviewer-demo.py
scripts/reviewer-fast-path.ps1
scripts/verify-public-release.py
evidence/public/portfolio/local-release-readiness.json
schemas/portfolio/local-release-readiness.schema.json
tests/publication/test_public_release_surface.py
docs/superpowers/plans/2026-08-30-mdcp-deterministic-recruiter-demo.md
```

schema 只在 deterministic generated output 實際改變時修改。design spec 本身獨立提交，不屬於後續
implementation allowlist。

不得修改 `src/mdcp`、existing temporal evidence、dependency files、models、workloads、workflow、
Docker、Compose、private custody 或其他 repository。

## 11. Acceptance result

成功的 demo 讓 reviewer 在 dependency setup 完成後，無需 dataset、model、GPU、Docker 或 network，
於 warm `120` 秒 budget 內觀察一個真實 PASS 與兩個真實 fail-closed rejection。它改善可理解性與可驗證性，但
terminal claim 仍是 local reviewer evidence：

```text
MDCP_REVIEWER_DEMO_PASS != REMOTE_RELEASED != PRODUCTION_READY
```

remote creation、push、merge、tag、GitHub Release、workflow execution、H2/data/model execution 與
CV/LLM workload implementation仍需獨立授權與新的 evidence cycle。
