# Workflow
# 工作流

This document explains how the current multi-agent genetic-circuit design workflow runs, what inputs and outputs it uses, and how to interpret the results.

本文件解釋了目前多智能體基因電路設計工作流如何運行、使用哪些輸入與輸出，以及如何解讀結果。

The workflow should be understood as computational candidate generation and triage. It does not produce complete plasmids or experimentally validated biological logic gates. For explicit boundaries, see [LIMITATION.md](LIMITATION.md).

該工作流應被理解為計算候選方案生成與篩選。它不產生完整的質體或經實驗驗證的生物邏輯閘。有關明確的邊界，請參見 [LIMITATION.md](LIMITATION.md)。

## 1. Running the App
## 1. 運行應用程式

Install dependencies:

安裝依賴項：

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run the Streamlit UI:

運行 Streamlit UI：

```powershell
streamlit run app.py
```

Run tests:

運行測試：

```powershell
pytest
```

## 2. Running Modes
## 2. 運行模式

The app supports multiple practical modes.

本應用程式支援多種實用模式。

### Demo Mode
### 展示模式

Demo mode is intended for UI and workflow demonstration. It may use deterministic or preconfigured behavior rather than full external LLM and Cello execution.

展示模式旨在進行 UI 與工作流的展示。它可能使用確定性或預先配置的行為，而非完整的外部 LLM 與 Cello 執行。

Use this mode to inspect:

使用此模式可檢查：

- UI layout;
  UI 版面配置；
- search-tree display;
  搜尋樹顯示；
- example topology output;
  範例拓撲輸出；
- chart and inspector behavior;
  圖表與檢查器（Inspector）行為；
- benchmark field rendering.
  基準測試欄位渲染。

Do not treat demo output as biological evidence.

請勿將展示輸出視為生物學證據。

### BYOK / External LLM Mode
### BYOK / 外部 LLM 模式

BYOK means "Bring Your Own Key." In this mode, the user supplies:

BYOK 代表「攜帶您自己的 API 金鑰」。在此模式下，使用者提供：

- API key;
  API 金鑰；
- model name;
  模型名稱；
- optional API base URL;
  可選的 API 基礎網址；
- host and workflow settings;
  宿主與工作流設定；
- compute budget;
  計算預算；
- toggles for retrieval, simulation, search, and caching.
  檢索、模擬、搜尋和快取的切換開關。

This mode runs the agent workflow with the configured LLM provider through the local app.

此模式將通過本地應用程式，使用配置的 LLM 提供商運行智能體工作流。

### Mock Cello Mode
### 模擬 Cello 模式

When `CelloWrapper` has no external `cello_command`, it returns mock unmapped topology data.

當 `CelloWrapper` 沒有外部 `cello_command` 時，它會返回模擬的未映射拓撲數據。

Mock mode is useful for:

模擬模式適用於：

- developing the workflow without a Cello installation;
  在未安裝 Cello 的情況下開發工作流；
- test UI and downstream scoring paths;
  測試 UI 與下游評分路徑；
- verifying that invalid or missing mapping does not crash the loop.
  驗證無效或缺失的映射不會使迴圈崩潰。

Mock mode is not real Cello mapping.

模擬模式並非真實的 Cello 映射。

### External Cello Mode
### 外部 Cello 模式

When configured with a real Cello command and compatible UCF/library, `CelloWrapper` writes candidate Verilog to a temporary directory, runs the external command, captures stdout/stderr, and records mapping results.

當配置了真實的 Cello 指令與相容的 UCF/庫時，`CelloWrapper` 會將候選 Verilog 寫入暫存目錄、運行外部指令、捕獲 stdout/stderr，並記錄映射結果。

Only this mode should be discussed as actual Cello execution.

只有此模式才應被作為實際的 Cello 執行來討論。

## 3. Pre-Design Elicitation (PMAgent)
## 3. 設計前置引導 (PMAgent)

Before running the core reflexion sequence, the user interacts with the `PMAgent` to build a structured design specification:
1. **Dialogue autocompletion**: If the intent lacks chassis, inputs, outputs, or logic relation, the PMAgent suggests biological defaults with reasons in a one-click flow.
2. **Visual Preview**: The UI displays a high-level circuit flowchart generated from the specification using Mermaid blocks.
3. **Reactive reset**: Any intent text change in the sidebar automatically resets the PM dialogue and current specification, keeping the elicitation workspace synchronized.

在運行核心 Reflexion 序列之前，使用者與 `PMAgent` 進行對話，共同建立結構化的設計規格：
1. **對話式自動補完**：若意圖缺少宿主、輸入、輸出或邏輯關係，PMAgent 會以一鍵式流程建議生物學預設值與理由。
2. **視覺化預覽**：UI 會以 Mermaid 流程圖即時繪製規格對應的高階信號流向。
3. **自動重設**：若在側邊欄修改了需求意圖文字，系統會自動重設 PM 對話與已確認規格，使引導工作區同步更新。

## 4. End-to-End Run Sequence
## 4. 端到端運行順序

The main function is:

主要函數為：

```python
run_reflexion_workflow(...)
```

defined in [workflows/reflexion_controller.py](workflows/reflexion_controller.py).

定義於 [workflows/reflexion_controller.py](workflows/reflexion_controller.py)。

A typical run proceeds as follows:

典型運行流程如下：

1. Initialize `DesignState`.
   初始化 `DesignState`。
2. Create a root `SearchNode` if the search tree is empty.
   若搜尋樹為空，創建根 `SearchNode`。
3. Pop the next node from `active_frontier`.
   從 `active_frontier` 取出下一個節點。
4. Select search behavior based on `search_mode`.
   根據 `search_mode` 選擇搜尋行為。
5. Retrieve skill/RAG context when configured.
   若有配置，檢索技能/RAG 上下文。
6. Run `BuilderAgent` unless the node is in `Exploitation` mode.
   運行 `BuilderAgent`（除非節點處於 `Exploitation` 模式）。
7. Run `TranslatorAgent` to generate Cello-compatible Verilog.
   運行 `TranslatorAgent` 生成與 Cello 相容的 Verilog。
8. Run `CelloWrapper` in mock or external mode.
   在模擬或外部模式下運行 `CelloWrapper`。
9. Run `DataMinerAgent` if enabled.
   若啟用，運行 `DataMinerAgent`。
10. Run `BatchODESimulator`.
    運行 `BatchODESimulator`。
11. Run `benchmark_suite.evaluate_candidate()` on each topology.
    對每個拓撲運行 `benchmark_suite.evaluate_candidate()`。
12. Select the best topology.
    選擇最佳拓撲。
13. Run `CriticAgent`.
    運行 `CriticAgent`。
14. Mark the node as passed, failed, dead-ended, or needing human input.
    將節點標記為通過（passed）、失敗（failed）、死胡同（dead-ended）或需要人工輸入。
15. Create repair or exploitation child nodes when appropriate.
    在適當時創建修復或利用子節點。
16. Continue until approval, exhaustion, or pause.
    繼續運行，直到批准、預算用盡或暫停。

## 5. Inputs
## 5. 輸入項

Important user-facing inputs include:

重要的使用者輸入包括：

- `user_intent`: natural-language design goal.
  `user_intent`：自然語言設計目標。
- `host_organism`: host context, defaulting to `Escherichia coli`.
  `host_organism`：宿主環境，預設為大腸桿菌（`Escherichia coli`）。
- compute budget.
  計算預算。
- model/API settings.
  模型/API 設定。
- Cello command and UCF path, if external Cello is used.
  Cello 指令與 UCF 路徑（如果使用外部 Cello）。
- optional human constraints or trade-offs.
  可選的人工約束或權衡。

Example intent:

範例意圖：

```text
Activate GFP only when input A is present and input B is absent.
```

This should be interpreted as a request for a candidate regulatory-logic design, not a complete plasmid specification.

這應被解讀為對候選調節邏輯設計的請求，而非完整的質體規範。

## 6. Search Modes
## 6. 搜尋模式

The workflow uses three modes:

該工作流使用三種模式：

| Mode / 模式 | Behavior / 行為 |
| --- | --- |
| `Exploration` | Generate broader candidate logic strategies. <br> 生成更廣泛的候選邏輯策略。 |
| `Repair` | Revise logic after Critic or benchmark failure. <br> 在 Critic 或基準測試失敗後修正邏輯。 |
| `Exploitation` | Reuse existing logic while trying translation, mapping, or part-oriented changes. <br> 重用現有邏輯，同時嘗試翻譯、映射或元件導向的變更。 |

`Exploration` uses a higher-temperature Builder configuration. `Repair` and `Exploitation` use lower-temperature behavior to make targeted changes.

`Exploration` 使用較高溫度的 Builder 配置。`Repair` 和 `Exploitation` 使用較低溫度的行為以進行針對性的修改。

## 7. Outputs
## 7. 輸出項

The workflow records outputs in both `DesignState` and `SearchNode`.

該工作流在 `DesignState` 和 `SearchNode` 中皆會記錄輸出。

Common output fields include:

常見的輸出欄位包括：

- `logic_proposals`
- `verilog_codes`
- `candidate_topologies`
- `best_topology`
- `benchmark_report`
- `weighted_total_score`
- `component_scores`
- `critic_feedbacks`
- `failed_attempts`
- `error_type`
- `requires_human_input`

These outputs are intended for inspection and iteration. They are not equivalent to a finalized biological design package.

這些輸出旨在供檢查和迭代使用。它們不等同於最終確定的生物設計套件。

## 8. How to Read Results
## 8. 如何解讀結果

### `weighted_total_score`
### `weighted_total_score`

The weighted total ranks candidates under the implemented benchmark. It is not an experimental validation score.

加權總分在已實現的基準下對候選方案進行排序。它並非實驗驗證分數。

See [EVALUATION_METRICS.md](EVALUATION_METRICS.md) for formulas.

公式請參見 [EVALUATION_METRICS.md](EVALUATION_METRICS.md)。

### `component_scores`
### `component_scores`

Always inspect component scores rather than relying only on the total. A candidate can have an acceptable total while still having a weak Cello assignment, poor robustness, or fallback-only evidence.

請務必檢查各子項分數，而不要僅僅依賴總分。一個候選方案可能擁有可以接受的總分，但卻同時存在 weak Cello 分配、魯棒性差或僅有回退（fallback）證據的問題。

### `grade`
### `grade`

Current grade thresholds are:

目前的評級閾值為：

| Grade / 評級 | Condition / 條件 |
| --- | --- |
| `Excellent` | `weighted_total_score >= 0.80` |
| `Pass` | `0.60 <= weighted_total_score < 0.80` |
| `Fail` | `weighted_total_score < 0.60` |

`Excellent` means strong under current computational checks. It does not mean experimentally validated.

`Excellent`（優秀）代表在目前的計算檢查下表現優異，不代表經過實驗驗證。

### `ode_status`
### `ode_status`

`ode_status = "simulated"` means numerical simulation completed under the simplified ODE assumptions.

`ode_status = "simulated"` 代表在簡化的 ODE 假設下完成了數值模擬。

It does not mean:

這並不代表：

- the candidate is experimentally buildable;
  該候選方案在實驗上是可構建的；
- the parameter values are calibrated;
  參數值已校準；
- the in vivo expression level is quantitatively predicted.
  定量預測了活體內（in vivo）的表達水平。

See [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md).

請參見 [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)。

### `cello_buildable`
### `cello_buildable`

`cello_buildable = true` means the current Cello-related evaluator interpreted available mapping evidence as buildable.

`cello_buildable = true` 代表目前與 Cello 相關的評估器將可用的映射證據解讀為可構建。

`cello_buildable = false` may mean:

`cello_buildable = false` 可能代表：

- mock mode was used;
  使用了模擬模式；
- external Cello failed;
  外部 Cello 運行失敗；
- UCF/library constraints were not satisfied;
  未滿足 UCF/庫的約束；
- assignment evidence was missing.
  缺少分配證據。

Do not describe mock-mode output as real Cello success.

請勿將模擬模式的輸出描述為真實的 Cello 成功。

### `critic_feedbacks`
### `critic_feedbacks`

Critic feedback is a routing and repair signal. It may include LLM-generated reasoning plus deterministic guardrails from benchmark thresholds.

Critic 反饋是一個路由與修復訊號。它可能包含 LLM 生成的推理以及來自基準測試閾值的確定性防護欄。

It should not be treated as expert biological review.

它不應被視為專家生物學審查。

### `failed_attempts`
### `failed_attempts`

Failed attempts are useful because they show how the Reflexion loop explored and rejected candidates. They may include:

失敗的嘗試非常有用，因為它們顯示了 Reflexion 迴圈如何探索並拒絕候選方案。它們可能包含：

- score summaries;
  分數摘要；
- error type;
  錯誤類型；
- last error;
  最後一次錯誤；
- best topology summary;
  最佳拓撲摘要；
- Critic feedback.
  Critic 反饋。

Use this record to explain what the workflow learned or why it changed direction.

使用此記錄來解釋工作流學到了什麼，或者為什麼改變了方向。

## 9. Repair and Routing Behavior
## 9. 修復與路由行為

The Critic assigns one of four error types:

Critic 會分配四種錯誤類型之一：

| Error Type / 錯誤類型 | Meaning / 意義 | Typical Next Step / 典型下一步 |
| --- | --- | --- |
| `LOGIC_ERROR` | Intent, truth-table behavior, logic complexity, robustness, or semantic coverage problem. <br> 意圖、真值表行為、邏輯複雜度、魯棒性或語義覆蓋率問題。 | Create a `Repair` node for Builder. <br> 為 Builder 創建一個 `Repair` 節點。 |
| `PART_ERROR` | Mapping, part-assignment, plausibility, toxicity, or implementation-oriented problem. <br> 映射、元件分配、合理性、毒性或實現導向的問題。 | Create an `Exploitation` node for Translator/mapping-oriented repair. <br> 為 Translator/映射導向的修復創建一個 `Exploitation` 節點。 |
| `BOTH` | Both design logic and implementation evidence are problematic. <br> 設計邏輯與實現證據皆存在問題。 | Treat like logic repair first. <br> 首先像邏輯修復一樣處理。 |
| `NONE` | Candidate is acceptable under current checks. <br> 候選方案在當前檢查下是可以接受的。 | Consolidate or mark pass. <br> 鞏固或標記為通過。 |

Repeated failures can exhaust the budget or trigger a human-input pause.

重複的失敗可能會用盡預算或觸發人工輸入暫停。

## 10. Human Intervention Points
## 10. 人工介入點

The workflow can pause when:

工作流可在以下情形暫停：

- `used_budget >= compute_budget`;
  `used_budget >= compute_budget`；
- the Critic marks the problem unrecoverable;
  Critic 將問題標記為無法復原；
- repeated error types suggest the search is stuck;
  重複的錯誤類型表明搜尋卡住；
- the workflow needs additional constraints or trade-offs;
  工作流需要額外的約束或權衡；
- no useful frontier remains.
  沒有剩餘有用的邊界（Frontier）。

When this happens, the state may include:

當這種情況發生時，狀態可能包括：

- `requires_human_input = True`
- `pause_reason`
- `human_feedback_prompt`

When the workflow pauses, instead of presenting raw technical logs, the system calls `PMAgent` to translate logs into Traditional Chinese and render three interactive option buttons (Option A/B/C) with automatic constraints and budget updates.

當工作流暫停時，系統不再直接呈現生硬的技術日誌，而是呼叫 `PMAgent` 將日誌翻譯成白話繁體中文，並為使用者提供三個可直接點選的折衷決策選項（選項 A/B/C），點擊即可自動套用限制並重啟設計。

Useful human feedback includes:

有用的人工反饋包括：

- acceptable design trade-offs;
  可接受的設計權衡；
- preferred host or part library;
  偏好的宿主或元件庫；
- whether to prioritize robustness, low burden, or simple logic;
  是否優先考慮魯棒性、低負載或簡單邏輯；
- whether mock Cello output is acceptable for demonstration;
  模擬的 Cello 輸出是否可用於展示；
- whether external Cello/UCF configuration is available.
  外部 Cello/UCF 配置是否可用。

## 11. Common Failure Modes
## 11. 常見失敗模式

| Failure / 失敗 | Typical Cause / 典型原因 | How to Interpret / 如何解讀 |
| --- | --- | --- |
| Invalid Verilog | Translator output failed structural validation. <br> Translator 輸出的結構驗證失敗。 | Needs translation repair. <br> 需要翻譯修復。 |
| No valid Verilog | All translations failed or were rejected. <br> 所有翻譯均失敗或被拒絕。 | Builder/Translator needs stronger constraints. <br> Builder/Translator 需要更強的約束。 |
| Mock Cello output | No external Cello command configured. <br> 未配置外部 Cello 指令。 | Workflow scaffolding only, not mapping success. <br> 僅為工作流支架，並非映射成功。 |
| `cello_buildable = false` | Missing mapping, UCF issue, part constraint, or Cello failure. <br> 缺少映射、UCF 問題、元件約束或 Cello 失敗。 | Cannot claim buildable Cello design. <br> 無法宣稱為可構建的 Cello 設計。 |
| ODE failed | Solver failure or invalid simulation inputs. <br> 求解器失敗或無效的模擬輸入。 | Simulation evidence is unavailable. <br> 模擬證據不可用。 |
| Signal collapse | OFF output overlaps ON output under perturbation. <br> 在微擾下，OFF 輸出與 ON 輸出重疊。 | Candidate is dynamically fragile under current model. <br> 候選方案在目前模型下動態脆弱。 |
| Low metabolic score | Gate count exceeds current ideal complexity. <br> 邏輯閘數量超過目前理想的複雜度。 | Candidate may be too complex under the proxy. <br> 候選方案在代理指標下可能過於複雜。 |
| Low robustness | Perturbations make output unreliable. <br> 微擾使輸出不可靠。 | Candidate needs architecture or margin repair. <br> 候選方案需要架構或邊際修復。 |
| Budget exceeded | Search used all allowed iterations. <br> 搜尋使用了所有允許的迭代次數。 | Needs human constraints or more budget. <br> 需要人工約束或更多預算。 |
| Fallback-only score | Data needed for stronger checks is missing. <br> 缺少更強檢查所需的數據。 | Treat score as weak evidence. <br> 將該分數視為微弱的證據。 |

## 12. Practical Interpretation Example
## 12. 實際解讀範例

If a candidate has:

如果一個候選方案具有：

```text
weighted_total_score = 0.82
cello_buildable = false
ode_status = "simulated"
```

The appropriate interpretation is:

合適的解讀是：

> The candidate scored well under several computational checks, and the ODE simulation completed, but Cello buildability evidence is currently negative or missing. It should not be described as a buildable genetic circuit.
> 該候選方案在幾項計算檢查下得分良好，且 ODE 模擬已完成，但目前 Cello 可構建性證據為陰性或缺失。不應將其描述為可構建的基因電路。

If a candidate has:

如果一個候選方案具有：

```text
weighted_total_score = 0.58
robustness_score = 0.30
collapsed = true
```

The appropriate interpretation is:

合適的解讀是：

> The candidate is weak under the current benchmark, and the simulated ON/OFF separation collapses under perturbation. The workflow should repair or reject it.
> 該候選方案在目前的基準下表現微弱，且模擬的 ON/OFF 分離在微擾下塌陷。工作流應該對其進行修復或拒絕。

## 13. Sequence and Host Optimization Workflow

The v2 optimization workflow is a deterministic post-design workflow for
sequence-backed designs. It complements the agent Reflexion loop; it does not
replace expert experimental design review.

The integrated endpoint is:

```text
POST /api/v2/designs/{design_id}/optimization-workflow
```

It runs the following stages:

1. Sequence analysis through `tools/sequence_analyzer.py`.
2. CDS codon-optimization revision through `tools/sequence_optimization.py`.
3. Host-optimization candidate ranking through `tools/host_optimization.py`.
4. Combined readiness reporting through `benchmark_suite/readiness_evaluator.py`.

The sequence-analysis stage reports IUPAC validity, CDS frame/start/stop
checks, internal stop codons, GC and window GC, homopolymers, repeats, common
restriction sites, Type IIS sites, host annotations, and checksums.

The sequence-optimization stage currently creates conservative *E. coli* CDS
codon-optimization revisions. It preserves the translated protein sequence and
records provenance, before/after analysis, diff information, and readiness
evidence. It does not optimize promoters, RBSs, RNA folding, codon-pair bias,
or real expression balance.

The host-optimization stage ranks computational candidate families:

| Candidate family | Intent | Main trade-off |
| --- | --- | --- |
| `high_expression` | Prioritize stronger output signal | May increase burden and toxicity risk |
| `low_burden` | Prioritize lower host burden | May reduce absolute output |
| `balanced` | Balance expression, burden, sequence quality, and stability | Not a single biological optimum |

The calibration endpoint stores and summarizes user-supplied measurements:

```text
POST /api/v2/host-optimization/calibrations
```

Calibration summaries report coverage, means, and recommendations. They do not
yet fit a validated host-cell model or automatically recalibrate the ODE model.

## 14. Related Documents
## 14. 相關文件

- [README.md](README.md): high-level project overview.
  [README.md](README.md)：高階專案概述。
- [ARCHITECTURE.md](ARCHITECTURE.md): system components and responsibility boundaries.
  [ARCHITECTURE.md](ARCHITECTURE.md)：系統組件與責任邊界。
- [EVALUATION_METRICS.md](EVALUATION_METRICS.md): benchmark formulas and scoring interpretation.
  [EVALUATION_METRICS.md](EVALUATION_METRICS.md)：基準公式與評分合理解讀。
- [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md): ODE assumptions and biological mechanisms not modeled.
  [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)：ODE 假設與未建模的生物機制。
- [LIMITATION.md](LIMITATION.md): safe claims, non-goals, and evidence needed for stronger claims.
  [LIMITATION.md](LIMITATION.md)：安全宣稱、非目標以及做出更強宣稱所需的證據。
# Current Design Review and Export Workflow (2026-06-06)
# 目前設計檢視與匯出流程（2026-06-06）

After candidate generation and evaluation, the current UI performs the following additional steps:

候選生成與評估後，目前 UI 會執行以下額外步驟：

1. Convert the selected topology into `DesignIR`.
   將選定 topology 轉換為 `DesignIR`。
2. Present Logic, Regulatory, DNA Construct, and Parts views.
   顯示 Logic、Regulatory、DNA Construct 與 Parts 視圖。
3. If external Cello artifacts contain a supported JSON assignment structure, apply parsed assignments and available sequences to matching DesignIR nodes.
   若外部 Cello artifact 含支援的 JSON assignment 結構，將解析出的 assignment 與可用序列套用至對應 DesignIR node。
4. Validate proposed replacement parts against type, host, gate role, sequence, and evidence constraints.
   依類型、宿主、gate role、序列與證據限制驗證替換元件。
5. Create a new immutable revision when the user applies a valid replacement.
   使用者套用有效替換時建立新的不可變版本。
6. Compare any two candidates with `DesignDiff`.
   使用 `DesignDiff` 比較任兩個候選。
7. Export the selected candidate or current immutable revision.
   匯出選定候選或目前的不可變版本。

## Export Decision Rules
## 匯出判定規則

| Format | Incomplete design | Sequence requirement | Intended use |
| --- | --- | --- | --- |
| BOM CSV | Allowed | None | Audit, inventory, review, and handoff |
| GenBank | Blocked when construct sequences are incomplete | Every construct part must have valid IUPAC DNA | Sequence-aware downstream tools |
| SBOL3 Turtle | Allowed with warnings | Optional | Structured exchange of conceptual or sequence-backed designs |

| 格式 | 不完整設計 | 序列要求 | 主要用途 |
| --- | --- | --- | --- |
| BOM CSV | 允許 | 無 | 稽核、清單、審查與交接 |
| GenBank | construct 序列不完整時阻擋 | 每個 construct 元件都必須有有效 IUPAC DNA | 需要序列的下游工具 |
| SBOL3 Turtle | 允許，但會警告 | 可選 | 交換概念性或具有序列的設計 |

The Export tab prefers an immutable revised design stored in the current session; otherwise it exports the DesignIR generated from the selected topology.

Export 分頁會優先匯出目前 session 中的不可變修訂設計；若沒有修訂，則匯出由選定 topology 產生的 DesignIR。
