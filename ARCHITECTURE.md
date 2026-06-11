# Architecture
# 架構

This document describes the current system architecture for the multi-agent genetic-circuit design prototype. The system is best understood as a computational design-assistance workflow: LLM agents propose and revise candidates, while deterministic tools and benchmark evaluators provide partial checks.

本文件描述了多智能體基因電路設計原型目前的系統架構。該系統最好被理解為一個計算輔助設計工作流：LLM 智能體提出並修正候選方案，而確定性工具與基準評估器則提供部分檢查。

The architecture does not make the project a complete plasmid-design platform or an experimentally validated biological design system. For explicit claim boundaries, see [LIMITATION.md](LIMITATION.md).

此架構並未使本專案成為一個完整的質體設計平台，或是一個經過實驗驗證的生物設計系統。有關明確的宣稱邊界，請參見 [LIMITATION.md](LIMITATION.md)。

## 1. Purpose and Scope
## 1. 目的與範圍

The architecture is designed to support:

本架構旨在支援：

- natural-language intent capture;
  自然語言意圖捕獲；
- Boolean logic proposal;
  布林邏輯提案；
- Cello-compatible combinational Verilog generation;
  與 Cello 相容的組合邏輯 Verilog 生成；
- optional external Cello mapping;
  可選的外部 Cello 映射；
- reduced resource-aware ODE simulation;
  簡化的資源感知 ODE 模擬；
- heuristic benchmark scoring;
  啟發式基準評分；
- Critic-guided repair and search;
  Critic（評論者）引導的修復與搜尋；
- transparent recording of failed attempts and decision signals.
  對失敗嘗試與決策訊號的透明記錄。

The central design goal is not full automation of synthetic-biology design. The goal is to make candidate generation, evaluation, and repair more structured and inspectable.

核心設計目標並非合成生物學設計的完全自動化。其目標是使候選方案的生成、評估和修復更加結構化且易於檢查。

## 2. High-Level Flow
## 2. 高階流程

```text
User intent
  -> DesignState
  -> BuilderAgent
  -> TranslatorAgent
  -> CelloWrapper
  -> DataMinerAgent
  -> BatchODESimulator
  -> benchmark_suite.evaluate_candidate()
  -> CriticAgent
  -> repair / exploitation / consolidation
```

The workflow is coordinated by [workflows/reflexion_controller.py](workflows/reflexion_controller.py). The Streamlit interface in [app.py](app.py) exposes the workflow to users.

該工作流由 [workflows/reflexion_controller.py](workflows/reflexion_controller.py) 進行協調。位於 [app.py](app.py) 的 Streamlit 介面則將該工作流呈現給使用者。

## 3. Repository Components
## 3. 儲存庫組件

| Path / 路徑 | Role / 角色 |
| --- | --- |
| [app.py](app.py) | Streamlit UI, demo workflow controls, BYOK settings, result panels, and visualization. <br> Streamlit UI、展示工作流控制項、BYOK 設定、結果面板與視覺化。 |
| [schemas/state.py](schemas/state.py) | Shared state models: `DesignState` and `SearchNode`. <br> 共享狀態模型：`DesignState` 與 `SearchNode`。 |
| [workflows/reflexion_controller.py](workflows/reflexion_controller.py) | Main Reflexion loop, search routing, benchmark integration, and pause logic. <br> 主 Reflexion 迴圈、搜尋路由、基準整合與暫停邏輯。 |
| [agents/](agents) | Builder, Translator, DataMiner, Critic, Consolidator, and SkillExtractor agents. <br> Builder、Translator、DataMiner、Critic、Consolidator 和 SkillExtractor 智能體。 |
| [tools/cello_wrapper.py](tools/cello_wrapper.py) | Optional external Cello integration and explicit mock topology fallback. <br> 可選的外部 Cello 整合與明確的模擬拓撲回退。 |
| [tools/ode_simulator.py](tools/ode_simulator.py) | Reduced resource-aware ODE simulation and Monte Carlo perturbation. <br> 簡化的資源感知 ODE 模擬與蒙特卡羅微擾。 |
| [benchmark_suite/](benchmark_suite) | Deterministic and heuristic scoring components. <br> 確定性與啟發式評分組件。 |
| [tools/skill_retriever.py](tools/skill_retriever.py) | Skill retrieval for contextual guidance. <br> 用於上下文引導的技能檢索。 |
| [tools/vector_retriever.py](tools/vector_retriever.py) | Vector retrieval wrapper for local records. <br> 用於本地記錄的向量檢索包裝器。 |
| [mcp_server/](mcp_server) | Local service for run artifacts and serialized outputs. <br> 用於運行產物與序列化輸出的本地服務。 |
| [tests/](tests) | Tests for workflow behavior, topology graphs, simulation, UI support logic, and MCP server behavior. <br> 針對工作流行為、拓撲圖、模擬、UI 支援邏輯與 MCP 伺服器行為的測試。 |

## 4. Data Model
## 4. 資料模型

The shared state is defined in [schemas/state.py](schemas/state.py).

共享狀態定義於 [schemas/state.py](schemas/state.py)。

### `DesignState`
### `DesignState`

`DesignState` carries the global workflow state:

`DesignState` 承載了全局工作流狀態：

- `user_intent`: natural-language design request.
  `user_intent`：自然語言設計請求。
- `host_organism`: current host context, defaulting to `Escherichia coli`.
  `host_organism`：當前宿主環境，預設為大腸桿菌（`Escherichia coli`）。
- `tree_nodes`: search tree keyed by `node_id`.
  `tree_nodes`：以 `node_id` 為鍵的搜尋樹。
- `active_frontier`: queue of nodes to evaluate.
  `active_frontier`：待評估節點的佇列。
- `current_node_id`: node currently being processed.
  `current_node_id`：當前正在處理的節點。
- `compute_budget` / `used_budget`: search budget control.
  `compute_budget` / `used_budget`：搜尋預算控制。
- `rag_context` / `skill_library_context`: retrieved context for LLM agents.
  `rag_context` / `skill_library_context`：為 LLM 智能體檢索的上下文。
- `biokinetic_context`: parameter context from data mining.
  `biokinetic_context`：來自數據挖掘的生物動力學參數上下文。
- `logic_proposals`: generated logic-level candidates.
  `logic_proposals`：生成的邏輯層級候選方案。
- `verilog_codes`: generated Cello-compatible Verilog candidates.
  `verilog_codes`：生成的與 Cello 相容的 Verilog 候選方案。
- `candidate_topologies`: mapped or mock topologies.
  `candidate_topologies`：已映射或模擬的拓撲結構。
- `best_topology`: best candidate selected during evaluation.
  `best_topology`：評估期間選出的最佳候選方案。
- `critic_feedbacks`: feedback from the Critic.
  `critic_feedbacks`：來自 Critic 的反饋。
- `failed_attempts`: repair history and failure records.
  `failed_attempts`：修復歷史與失敗記錄。
- `requires_human_input`, `pause_reason`, `human_feedback_prompt`: human-in-the-loop pause state.
  `requires_human_input`、`pause_reason`、`human_feedback_prompt`：人機協同（human-in-the-loop）暫停狀態。

### `SearchNode`
### `SearchNode`

`SearchNode` records one branch in the Reflexion search tree:

`SearchNode` 記錄了 Reflexion 搜尋樹中的一個分支：

- `node_id`, `parent_id`, `children_ids`: lineage.
  `node_id`、`parent_id`、`children_ids`：世系關係（父子關係）。
- `search_mode`: `Exploration`, `Repair`, or `Exploitation`.
  `search_mode`：搜尋模式，包含 `Exploration`（探索）、`Repair`（修復）或 `Exploitation`（利用）。
- `status`: `Pending`, `Evaluated`, `Pass`, `Dead_End`, or `Needs_Human_Input`.
  `status`：狀態，包含 `Pending`（待定）、`Evaluated`（已評估）、`Pass`（通過）、`Dead_End`（死胡同）或 `Needs_Human_Input`（需要人工輸入）。
- `logic_proposals`, `verilog_codes`, `candidate_topologies`: node-local artifacts.
  `logic_proposals`、`verilog_codes`、`candidate_topologies`：節點本地產物。
- `best_topology` and `score`: selected candidate and score.
  `best_topology` 與 `score`：選出的候選方案與其分數。
- metric fields such as `metabolic_burden_score`, `robustness_score`, `orthogonality_score`, and `cello_assignment_score`.
  指標欄位，例如 `metabolic_burden_score`（代謝負載分數）、`robustness_score`（魯棒性分數）、`orthogonality_score`（正交性分數）與 `cello_assignment_score`（Cello 分配分數）。
- `critic_feedbacks`, `error_type`, and `failed_attempts`.
  `critic_feedbacks`、`error_type` 與 `failed_attempts`。

`SearchNode.sync_evaluation_metrics()` copies benchmark fields from the selected topology into the node so the search tree can be inspected without re-parsing the full topology object.

`SearchNode.sync_evaluation_metrics()` 將選定拓撲結構的基準欄位複製到節點中，以便在不重新解析完整拓撲對象的情況下檢查搜尋樹。

## 5. Agent Layer
## 5. 智能體層

### BuilderAgent
### BuilderAgent

The Builder proposes logic-level designs from the user intent, retrieved context, human constraints, and previous Critic feedback. It is LLM-dependent.

Builder 根據使用者意圖、檢索的上下文、人工約束以及先前的 Critic 反饋提出邏輯層級的設計。它依賴於 LLM。

Expected outputs include strategy fields such as:

預期的輸出包括以下策略欄位：

- `gate_count_optimization`
  `gate_count_optimization`（邏輯閘數量優化）
- `depth_optimization`
  `depth_optimization`（邏輯深度優化）
- `robustness_strategy`
  `robustness_strategy`（魯棒性策略）

The Builder is responsible for design strategy, not experimental validation.

Builder 負責設計策略，而非實驗驗證。

### TranslatorAgent
### TranslatorAgent

The Translator converts Builder proposals into Cello-compatible combinational Verilog. It is LLM-dependent, but includes programmatic validation of generated Verilog structure.

Translator 將 Builder 提案轉換為與 Cello 相容的組合邏輯 Verilog。它依賴於 LLM，但包含了對生成的 Verilog 結構的程式化驗證。

The validator expects constructs such as:

驗證器預期包含以下結構：

- `module` / `endmodule`
- `input` / `output`
- `assign`
- primitive gates such as `and`, `or`, `not`, `nand`, `nor`, `xor`, and `xnor`
  基本邏輯閘，例如 `and`、`or`、`not`、`nand`、`nor`、`xor` 和 `xnor`

It rejects unsupported constructs such as:

它會拒絕不支持的結構，例如：

- `always`
- `reg`
- delay syntax `#`
  延遲語法 `#`
- sequential logic, clocks, memories, or latches
  時序邏輯、時脈、記憶體或鎖存器

### DataMinerAgent
### DataMinerAgent

The DataMiner attaches biokinetic parameters to candidate topologies. If a vector retriever is available, local records may override defaults. Otherwise, it uses conservative defaults defined in [agents/data_miner_agent.py](agents/data_miner_agent.py).

DataMiner 將生物動力學參數附加到候選拓撲中。如果向量檢索器可用，本地記錄可能會覆蓋預設值。否則，它將使用定義於 [agents/data_miner_agent.py](agents/data_miner_agent.py) 的保守預設值。

The current unit system is:

目前的單位系統為：

```text
nM and seconds
nM 和秒
```

These parameters support simulation continuity. They should not be assumed to be calibrated unless their provenance says so.

這些參數支援模擬的連續性。除非其來源明確說明，否則不應假定它們已校準。

### CriticAgent
### CriticAgent

The Critic evaluates proposals, benchmark reports, failed-attempt history, and the best topology. It is LLM-dependent but also includes deterministic guardrails around thresholds and routing.

Critic 評估提案、基準測試報告、失敗嘗試歷史以及最佳拓撲。它依賴於 LLM，但也包含圍繞閾值和路由的確定性防護欄。

The Critic uses error types:

Critic 使用以下錯誤類型：

- `LOGIC_ERROR`（邏輯錯誤）
- `PART_ERROR`（元件錯誤）
- `BOTH`（兩者皆有）
- `NONE`（無）

Current thresholds include:

目前的閾值包括：

| Threshold / 評估指標 | Value / 閾值 |
| --- | ---: |
| `PASS_SCORE_THRESHOLD` | 0.80 |
| `FAIL_SCORE_THRESHOLD` | 0.60 |
| `METABOLIC_BURDEN_THRESHOLD` | 0.70 |
| `ROBUSTNESS_THRESHOLD` | 0.75 |
| `ORTHOGONALITY_THRESHOLD` | 0.20 |
| `SEMANTIC_FAITHFULNESS_THRESHOLD` | 0.90 |

Low metabolic burden, low robustness, failed Cello buildability, or severe semantic mismatch can force rejection even if the LLM response is permissive.

即使 LLM 的回應是允許的，低代謝負載、低魯棒性、Cello 構建失敗或嚴重的語義不匹配也會強制拒絕。

### ConsolidatorAgent
### ConsolidatorAgent

The Consolidator prepares the final selected result for display or downstream use. It should be interpreted as a result-packaging step, not as additional biological validation.

Consolidator 準備最終選定的結果以供展示或下游使用。它應被視為一個結果包裝步驟，而非額外的生物學驗證。

### SkillExtractorAgent
### SkillExtractorAgent

The SkillExtractor can summarize lessons from failed attempts, best topology data, and Critic feedback into reusable design memory. This supports later workflow iterations but does not independently verify biological correctness.

SkillExtractor 可以將失敗嘗試中的教訓、最佳拓撲數據以及 Critic 反饋總結為可重複使用的設計記憶。這能支援後續的工作流迭代，但並不會獨立驗證生物學的正確性。

## 6. Tool and Evaluator Layer
## 6. 工具與評估器層

### CelloWrapper
### CelloWrapper

[tools/cello_wrapper.py](tools/cello_wrapper.py) has two modes:

[tools/cello_wrapper.py](tools/cello_wrapper.py) 有兩種模式：

- External mode: runs a configured Cello command with a Verilog netlist and optional UCF path.
  外部模式：使用配置的 Cello 指令運行 Verilog 網表（netlist）和可選的 UCF 路徑。
- Mock mode: when `cello_command is None`, returns mock unmapped topology objects.
  模擬模式：當 `cello_command is None` 時，返回模擬的未映射拓撲對象。

Mock mode is useful for UI and workflow testing. It is not successful Cello mapping.

模擬模式對於 UI 和工作流測試非常有用。它並非成功的 Cello 映射。

External Cello failures are categorized when possible:

在可能的情況下，外部 Cello 失敗會被歸類為：

- `UCF_INCOMPATIBLE`（UCF 不相容）
- `VERILOG_SYNTAX_ERROR`（Verilog 語法錯誤）
- `UNSUPPORTED_GATE`（不支持的邏輯閘）
- `PART_UNAVAILABLE`（元件不可用）
- `TIMEOUT`（超時）
- `MAPPING_FAILED`（映射失敗）

### BatchODESimulator
### BatchODESimulator

[tools/ode_simulator.py](tools/ode_simulator.py) runs a reduced resource-aware ODE model. It tracks mRNA, protein, RNAP/ribosome resource availability, and coarse burden signals. It may run Monte Carlo perturbations for robustness screening.

[tools/ode_simulator.py](tools/ode_simulator.py) 運行一個簡化的資源感知 ODE 模型。它追蹤 mRNA、蛋白質、RNAP/核糖體的資源可用性，以及粗略的負載訊號。它可能會運行蒙特卡羅微擾以進行魯棒性篩選。

For detailed biological assumptions, see [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md).

如需詳細的生物學假設，請參見 [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)。

### Benchmark Suite
### Benchmark Suite

[benchmark_suite/benchmark_controller.py](benchmark_suite/benchmark_controller.py) combines component scores:

[benchmark_suite/benchmark_controller.py](benchmark_suite/benchmark_controller.py) 組合了各子項分數：

- `functional`
- `kinetic`
- `static_plausibility`
- `metabolic_burden`
- `robustness`
- `temporal`
- `orthogonality`
- `cello_assignment`

For formulas and fallback behavior, see [EVALUATION_METRICS.md](EVALUATION_METRICS.md).

如需了解公式與回退（fallback）行為，請參見 [EVALUATION_METRICS.md](EVALUATION_METRICS.md)。

## 7. Deterministic vs LLM-Dependent Components
## 7. 確定性組件與依賴 LLM 的組件

LLM-dependent components:

依賴 LLM 的組件：

- Builder proposal generation.
  Builder 的提案生成。
- Translator generation before validation.
  驗證前 Translator 的生成。
- Critic reasoning and textual feedback.
  Critic 的推理與文本反饋。
- Semantic faithfulness evaluation when explicitly used.
  明確使用時的語義忠實性評估。

Programmatic or deterministic components:

程式化或確定性的組件：

- `DesignState` and `SearchNode` state transitions.
  `DesignState` 與 `SearchNode` 的狀態轉移。
- Verilog structural validation in the Translator.
  Translator 中 Verilog 的結構驗證。
- External Cello command execution and log classification.
  外部 Cello 指令執行與日誌分類。
- Mock Cello fallback behavior.
  模擬 Cello 的回退行為。
- ODE simulation and Monte Carlo perturbation.
  ODE 模擬與蒙特卡羅微擾。
- Gate counting for metabolic-burden proxy.
  用於代謝負載代理指標的邏輯閘計數。
- Static plausibility scoring.
  靜態合理性評分。
- Temporal scoring.
  時序評分。
- Weighted benchmark aggregation.
  加權基準聚合。
- Critic threshold guardrails after LLM output.
  LLM 輸出後 Critic 的閾值防護欄。

This distinction matters because LLM-generated outputs can be incomplete or wrong. The deterministic checks reduce some risks, but they do not provide full biological validation.

這種區別非常重要，因為 LLM 生成的輸出可能不完整或出錯。確定性檢查降低了某些風險，但它們並不提供完整的生物學驗證。

## 8. Search Modes
## 8. 搜尋模式

The Reflexion controller uses three search modes:

Reflexion 控制器使用三種搜尋模式：

| Mode / 模式 | Purpose / 用途 |
| --- | --- |
| `Exploration` | Generate broader candidate strategies. <br> 生成更廣泛的候選策略。 |
| `Repair` | Revise logic after a detected design or scoring failure. <br> 在檢測到設計或評分失敗後修正邏輯。 |
| `Exploitation` | Keep existing logic and try translation or mapping-oriented repair. <br> 保留現有邏輯，並嘗試進行與翻譯或映射相關的修復。 |

`Exploration` typically uses a higher LLM temperature. `Repair` and `Exploitation` use lower-temperature behavior. `Exploitation` can skip the Builder and reuse inherited logic proposals.

`Exploration` 通常使用較高的 LLM 溫度（Temperature）。`Repair` 與 `Exploitation` 使用較低溫度的行為。`Exploitation` 可以跳過 Builder，直接重用繼承的邏輯提案。

## 9. Mock, Fallback, and Default Behavior
## 9. 模擬、回退與預設行為

The system intentionally has fallback paths so the workflow can run during prototyping:

本系統刻意設計了回退路徑，以便工作流在原型開發期間可以運行：

- If Cello is not configured, `CelloWrapper` returns mock unmapped topology data.
  若未配置 Cello，`CelloWrapper` 將返回模擬的未映射拓撲數據。
- If no vector-retrieved biokinetic records are available, `DataMinerAgent` uses conservative defaults.
  若沒有向量檢索的生物動力學記錄，`DataMinerAgent` 將使用保守的預設值。
- If some evaluator inputs are missing, scorers may skip, fallback, or use candidate-provided scores.
  若缺少某些評估器輸入，評分器可能會跳過、回退或使用候選方案提供的分數。
- If SciPy is unavailable or fails, the ODE simulator can use an internal integration fallback.
  若 SciPy 不可用或失敗，ODE 模擬器可以使用內部積分回退方案。
- Semantic faithfulness is recorded when available, but it is not currently part of the weighted benchmark total.
  語義忠實性會在可用時予以記錄，但目前並不屬於加權基準總分的一部分。

These fallback paths should be disclosed when presenting results.

在展示結果時，應公開說明這些回退路徑。

## 10. Human-in-the-Loop Boundaries
## 10. 人機協同邊界

The workflow can pause for human input when:

工作流可在以下情況暫停並等待人工輸入：

- compute budget is exceeded;
  計算預算用盡；
- the Critic marks a problem unrecoverable;
  Critic 標記問題為無法復原；
- repeated error types suggest the loop is stuck;
  重複出現的錯誤類型表明迴圈卡住；
- additional design constraints or trade-offs are needed.
  需要額外的設計約束或權衡。

Human input is expected for biological interpretation, constraint selection, and deciding whether a candidate is worth deeper modeling or experimental follow-up.

人工輸入預期用於生物學解讀、約束選擇，以及決定某個候選方案是否值得進行更深入的建模或實驗後續跟進。

## 11. Related Documents
## 11. 相關文件

- [README.md](README.md): high-level overview and project entry point.
  [README.md](README.md)：高階概述與專案進入點。
- [WORKFLOW.md](WORKFLOW.md): how a run proceeds and how to interpret outputs.
  [WORKFLOW.md](WORKFLOW.md)：運行如何進行以及如何解讀輸出。
- [EVALUATION_METRICS.md](EVALUATION_METRICS.md): scoring formulas and evaluator behavior.
  [EVALUATION_METRICS.md](EVALUATION_METRICS.md)：評分公式與評估器行為。
- [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md): ODE model scope and biological assumptions.
  [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)：ODE 模型範圍與生物學假設。
- [LIMITATION.md](LIMITATION.md): capabilities, non-goals, and safe claim boundaries.
  [LIMITATION.md](LIMITATION.md)：能力、非目標與安全宣稱邊界。
# Current Design-Data Architecture (2026-06-06)
# 目前設計資料架構（2026-06-06）

The implementation now separates workflow state from biological design representation.

目前實作將工作流程狀態與生物設計表示分離。

```text
DesignState / SearchNode
  -> candidate topology dictionary
  -> topology_to_design_ir()
  -> DesignIR
       - BiologicalPart
       - RegulatoryInteraction
       - GeneticConstruct
       - ProvenanceRecord
       - PartAssignment
       - DesignRevision
  -> replacement validation / immutable revision
  -> DesignDiff
  -> BOM / GenBank / SBOL3 exporters
```

## DesignIR Boundary
## DesignIR 邊界

`DesignState` and `SearchNode` remain responsible for search, agent routing, scores, and candidate selection. `DesignIR` is the canonical reader/export representation for one candidate design.

`DesignState` 與 `SearchNode` 仍負責搜尋、代理路由、評分與候選選擇；`DesignIR` 則是一個候選設計的標準檢視與匯出表示。

UI and exporters should consume `DesignIR` rather than reparsing independent topology fields. This keeps the regulatory view, construct view, part inspector, revisions, comparison, and exports aligned to the same candidate.

UI 與 exporter 應使用 `DesignIR`，而不是各自重新解析 topology 欄位，確保調控圖、construct、元件檢視、版本、比較與匯出代表同一個候選。

## Cello Artifact Path
## Cello Artifact 路徑

`CelloWrapper` executes an external command in a temporary directory, then copies the complete execution directory into a persistent artifact root. Each manifest records:

`CelloWrapper` 在暫存目錄執行外部命令，完成後將整個執行目錄複製到持久化 artifact root。每份 manifest 記錄：

- run ID, candidate index, time, status, command, return code, and UCF path;
- run ID、候選索引、時間、狀態、command、return code 與 UCF path；
- input Verilog, output files, stdout, and stderr;
- 輸入 Verilog、輸出檔案、stdout 與 stderr；
- relative/absolute path, byte size, media type, and SHA-256 for every file.
- 每個檔案的相對／絕對路徑、大小、media type 與 SHA-256。

`CelloV2JsonParser` parses supported JSON assignment structures after a successful external run. Parser absence or unsupported files produce warnings and never fabricate assignments.

外部執行成功後，`CelloV2JsonParser` 會解析支援的 JSON assignment 結構。找不到支援格式時只會產生警告，不會虛構 assignment。

## Part and Revision Layer
## 元件與版本層

`PartLibrary` loads fixed JSON libraries and supports type/host/gate compatibility queries. The included `demo-cello-library@1.0.0` is demonstration-only.

`PartLibrary` 載入固定 JSON 元件庫，並支援類型、宿主與 gate 相容性查詢。內建的 `demo-cello-library@1.0.0` 僅供展示。

`replace_part_immutable()` validates a replacement, deep-copies the source `DesignIR`, updates assignment/provenance, and creates a child `DesignRevision`. It does not mutate the input design.

`replace_part_immutable()` 先驗證替換，再 deep-copy 來源 `DesignIR`、更新 assignment/provenance，並建立子 `DesignRevision`；它不會修改輸入設計。

## Export Layer
## 匯出層

- `bom_exporter.py`: ordered construct/part inventory with assignment and evidence fields.
- `bom_exporter.py`：含元件順序、assignment 與證據欄位的清單。
- `genbank_exporter.py`: one GenBank record per construct with feature coordinates and annotations; blocked for missing or invalid sequences.
- `genbank_exporter.py`：每個 construct 一筆 GenBank record，含 feature 座標與 annotation；缺失或非法序列時阻擋。
- `sbol3_exporter.py`: SBOL3 Turtle Components, Sequences, SubComponents, Ranges, Constraints, Interactions, Participations, and provenance activities.
- `sbol3_exporter.py`：輸出 SBOL3 Turtle 的 Component、Sequence、SubComponent、Range、Constraint、Interaction、Participation 與 provenance activity。
