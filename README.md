# Multi-Agent Framework for Translating Natural Language to Genetic Circuit Design Candidates
# 用於將自然語言翻譯為基因電路設計候選方案的多智能體框架

This project is a research prototype for exploring how LLM-based agents can turn a natural-language circuit design request into computational genetic-circuit design candidates. It focuses on the design-assistance layer: intent interpretation, Boolean-logic drafting, Cello-compatible Verilog generation, optional Cello mapping, resource-aware ODE simulation, and benchmark-driven revision.

本專案是一個研究原型，旨在探索基於大型語言模型（LLM）的智能體如何將自然語言電路設計請求轉化為計算基因電路設計候選方案。它專注於設計輔助層：意圖解釋、布林邏輯草稿擬定、與 Cello 相容的 Verilog 生成、可選的 Cello 映射、資源感知的常微分方程（ODE）模擬，以及基準驅動的修改。

The current system should be read as a computational workflow for proposing and evaluating candidate regulatory-circuit topologies, not as a complete plasmid-design or wet-lab validation platform.

目前的系統應被理解為提出和評估候選調節電路拓撲結構的計算工作流，而非一個完整的質體設計或濕實驗室驗證平台。

## Project Status
## 專案狀態

This repository is an actively developed research prototype. It is suitable for local demonstrations, workflow experiments, and evaluation research, but its APIs, data models, and scoring behavior may still change. A practical release label for the current codebase is `0.x research preview`, not a stable production release.

本儲存庫是持續開發中的研究原型，適合本機展示、工作流實驗與評估研究；API、資料模型和評分行為仍可能變更。目前較合適的發布標示是 `0.x research preview`，而非穩定的正式版本。

## Scope and Boundaries
## 範圍與邊界

What this project attempts to do:

本專案嘗試做的事情：

- Parse a user request such as "activate GFP only when input A is present and input B is absent."
  解析使用者請求，例如「僅在輸入 A 存在且輸入 B 不存在時激活 GFP」。
- Generate candidate Boolean logic and Cello-compatible combinational Verilog.
  生成候選的布林邏輯以及與 Cello 相容的組合邏輯 Verilog。
- Route candidates through a multi-agent Reflexion loop: Builder, Translator, Cello wrapper, DataMiner, ODE simulator, Benchmark, Critic, Consolidator, and SkillExtractor.
  將候選方案路由至多智能體 Reflexion 迴圈：Builder（構建者）、Translator（翻譯者）、Cello wrapper（Cello 包裝器）、DataMiner（數據挖掘者）、ODE simulator（ODE 模擬器）、Benchmark（基準測試）、Critic（評論者）、Consolidator（鞏固者）以及 SkillExtractor（技能提取者）。
- Score candidates with functional, kinetic, burden, robustness, temporal, orthogonality, and Cello-assignment metrics.
  利用功能性、動力學、負載、魯棒性、時序、正交性以及 Cello 分配指標對候選方案進行評分。
- Surface failure modes so later iterations can repair logic, mapping, or part-assignment problems.
  顯現失敗模式，以便後續迭代能修復邏輯、映射或元件分配問題。

What this project does not claim to do:

本專案不宣稱能做的事情：

- It does not design every element of a full plasmid. The workflow reasons about regulatory logic, selected biological parts or part-like assignments, and simulated expression behavior, but it does not fully specify cloning strategy, backbone, origin of replication, selectable marker, complete sequence-level constraints, assembly scars, or host-specific genomic context.
  它不設計完整質體的每個元素。該工作流僅推導調節邏輯、選定的生物元件或類似元件的分配，以及模擬的表達行為，但它並不完整指定克隆策略、骨架、複製起點、篩選標記、完整的序列級約束、組裝疤痕或宿主特定的基因組環境。
- It does not prove that a candidate is a real experimentally validated biological logic gate. A candidate may be a plausible computational design or a Cello-mappable assignment, but experimental truth requires construction, measurement, and characterization.
  它不證明候選方案是真實經過實驗驗證的生物邏輯閘。候選方案可能是一個合理的計算設計或可進行 Cello 映射的分配，但實驗真實性需要構建、測量和表徵。
- It does not replace expert synthetic-biology design review. The benchmark scores are heuristics intended to guide iteration, not biological guarantees.
  它不取代合成生物學專家的設計審查。基準分數是旨在引導迭代的啟發式指標，而非生物學上的保證。
- In the default configuration, the Cello stage can run in mock mode when no external Cello command is configured. Mock output is useful for UI and workflow testing but should not be interpreted as successful biological part mapping.
  在預設配置中，若未配置外部 Cello 指令，Cello 階段可以在模擬模式下運行。模擬輸出對於 UI 和工作流測試非常有用，但不應被解讀為成功的生物元件映射。

For a concise list of current capabilities, non-goals, and safe claim boundaries, see [LIMITATION.md](LIMITATION.md).

如需了解目前能力、非目標和安全宣稱邊界的簡要列表，請參見 [LIMITATION.md](LIMITATION.md)。

## Why This Framing Matters
## 為什麼這種框架定位很重要

Natural-language interfaces are useful for making genetic circuit design more accessible, but they can easily overstate what has actually been designed. This repository therefore treats the output as a candidate design package with explicit uncertainty:

自然語言介面有助於讓基因電路設計更易於使用，但它們很容易誇大實際設計的內容。因此，本儲存庫將輸出視為具有明確不確定性的候選設計套件：

- Boolean intent and truth-table consistency can be checked computationally.
  布林意圖和真值表的一致性可以通過計算進行檢查。
- Verilog syntax and primitive-gate compatibility can be checked before Cello mapping.
  在進行 Cello 映射之前，可以檢查 Verilog 語法和基本邏輯閘的相容性。
- Cello compatibility depends on the selected UCF/library and the availability of orthogonal parts.
  Cello 相容性取決於所選的 UCF/庫以及正交元件的可用性。
- ODE simulation can test a simplified resource-aware dynamical model, but model quality depends on parameter provenance and biological assumptions.
  ODE 模擬可以測試簡化的資源感知動力學模型，但模型品質取決於參數來源和生物學假設。
- ODE explanations summarize trajectory readouts such as peak output, time to peak, burden proxies, steady-state status, and missing coverage warnings; these are interpretive screening aids, not calibrated experimental measurements.
  ODE 解釋會彙整軌跡讀數，例如最大輸出、達峰時間、負載代理指標、穩態狀態與覆蓋缺口警示；這些是解讀性的篩選輔助，而非經校準的實驗量測。
- Benchmark scores help compare candidates, but they do not establish buildability or experimental function by themselves.
  基準分數有助於比較候選方案，但它們本身並不能證明其可構建性或實驗功能。

## Workflow
## 工作流

The main Reflexion workflow is implemented in [workflows/reflexion_controller.py](workflows/reflexion_controller.py).

主要的 Reflexion 工作流實作於 [workflows/reflexion_controller.py](workflows/reflexion_controller.py)。

1. The user provides a natural-language design request and optional host/model settings.
   使用者提供自然語言設計請求以及選擇性的宿主/模型設定。
2. `BuilderAgent` proposes logic strategies, truth-table structure, and design constraints.
   `BuilderAgent` 提出邏輯策略、真值表結構與設計約束。
3. `TranslatorAgent` converts the proposal into Cello-compatible combinational Verilog.
   `TranslatorAgent` 將提案轉換為與 Cello 相容的組合邏輯 Verilog。
4. `CelloWrapper` either runs an external Cello command or returns mock unmapped topology data when Cello is not configured. Topologies carry explicit `cello_mode`, `cello_claim_level`, and `cello_warning` metadata so mock output is not confused with real part mapping.
   `CelloWrapper` 可以運行外部 Cello 指令，或者在未配置 Cello 時返回模擬的未映射拓撲數據。拓撲會帶有明確的 `cello_mode`、`cello_claim_level` 與 `cello_warning` 後設資料，以避免將 mock 輸出誤解為真實元件映射。
5. `DataMinerAgent` attaches biokinetic parameters from local retrieval or defaults.
   `DataMinerAgent` 從本地檢索或預設值附加生物動力學參數。
6. `BatchODESimulator` runs resource-aware mRNA/protein ODE simulation and optional Monte Carlo perturbation. The UI and MCP explanation layer can extract ODE readouts and limitations from the stored trace.
   `BatchODESimulator` 運行資源感知的 mRNA/蛋白質 ODE 模擬以及可選的蒙特卡羅微擾。UI 與 MCP 解釋層可以從保存的軌跡中萃取 ODE 讀數與限制。
7. `benchmark_suite.evaluate_candidate()` calculates weighted component scores.
   `benchmark_suite.evaluate_candidate()` 計算加權的子項分數。
8. `CriticAgent` approves, rejects, or routes the design back to Builder or Translator for repair.
   `CriticAgent` 批准、拒絕，或將設計路由回 Builder 或 Translator 進行修復。
9. `ConsolidatorAgent` prepares the best candidate for display, and `SkillExtractorAgent` can save reusable design lessons.
   `ConsolidatorAgent` 準備最佳候選方案以供展示，而 `SkillExtractorAgent` 可以儲存可重複使用的設計經驗。

## Evaluation Model
## 評估模型

The benchmark controller combines normalized component scores into `weighted_total_score`. This score is used to rank candidates and guide the Reflexion loop toward repair or consolidation; it is not an experimental validation score.

基準控制器將歸一化的子項分數組合成 `weighted_total_score`（加權總分）。此分數用於對候選方案進行排序，並引導 Reflexion 迴圈進行修復或鞏固；它並非實驗驗證分數。

| Component / 評估子項 | Weight / 權重 |
| --- | ---: |
| `functional` | 0.22 |
| `kinetic` | 0.15 |
| `static_plausibility` | 0.08 |
| `metabolic_burden` | 0.15 |
| `robustness` | 0.15 |
| `temporal` | 0.05 |
| `orthogonality` | 0.10 |
| `cello_assignment` | 0.10 |

The weighted score is computed as:

加權分數的計算方式如下：

```text
weighted_total_score =
  0.22 * functional
+ 0.15 * kinetic
+ 0.08 * static_plausibility
+ 0.15 * metabolic_burden
+ 0.15 * robustness
+ 0.05 * temporal
+ 0.10 * orthogonality
+ 0.10 * cello_assignment
```

The component scores summarize different kinds of evidence:

各項子分數彙整了不同類型的證據：

- `functional`: consistency between the requested logic, truth-table behavior, Verilog, and ON/OFF separation when available.
  `functional`（功能性）：所請求的邏輯、真值表行為、Verilog 以及（在可用時）ON/OFF 分離度之間的一致性。
- `kinetic`: simulated expression dynamics under the implemented ODE model.
  `kinetic`（動力學）：在所實現的 ODE 模型下模擬的表達動力學。
- `static_plausibility`: structural plausibility, including repeated parts and excessive logic depth.
  `static_plausibility`（靜態合理性）：結構合理性，包括重複元件和過深的邏輯深度。
- `metabolic_burden`: a penalty for unnecessary gate complexity.
  `metabolic_burden`（代謝負載）：對不必要的邏輯閘複雜度所施加的懲罰。
- `robustness`: Monte Carlo stability under parameter perturbation when simulation data are available.
  `robustness`（魯棒性）：在模擬數據可用時，參數微擾下的蒙特卡羅穩定性。
- `temporal`: response-time or rise-time behavior.
  `temporal`（時序）：響應時間或上升時間行為。
- `orthogonality`: whether the candidate appears compatible with non-cross-reactive biological parts or Cello constraints.
  `orthogonality`（正交性）：候選方案是否與非交叉反應的生物元件或 Cello 約束相容。
- `cello_assignment`: quality or availability of Cello part assignment when external mapping is configured.
  `cello_assignment`（Cello 分配）：配置外部映射時 Cello 元件分配的品質或可用性。

Grades are assigned as:

評級分配如下：

- `Excellent`: `weighted_total_score >= 0.80`
  `Excellent`（優秀）：`weighted_total_score >= 0.80`
- `Pass`: `0.60 <= weighted_total_score < 0.80`
  `Pass`（通過）：`0.60 <= weighted_total_score < 0.80`
- `Fail`: `weighted_total_score < 0.60`
  `Fail`（不通過）：`weighted_total_score < 0.60`

The scoring system is intentionally conservative in interpretation. A high score means "promising under the implemented computational checks," not "ready for biological deployment."

評分系統在解讀上刻意保持保守。高分代表「在已實現的計算檢查下具有前景」，並不代表「已準備好進行生物學部署」。

## ODE Model Assumptions
## ODE 模型假設

The simulator intentionally uses a reduced resource-aware ODE model because the goal is early computational triage, not quantitative prediction of in vivo expression. It tracks mRNA and protein species for the candidate topology, plus coarse RNAP/ribosome resource availability and aggregate burden signals.

模擬器刻意使用簡化的資源感知 ODE 模型，因為其目標是早期的計算篩選，而非活體內（in vivo）表達的定量預測。它追蹤候選拓撲結構的 mRNA 和蛋白質物種，以及粗略的 RNAP/核糖體資源可用性和聚合負載訊號。

This level of modeling is useful for comparing candidate designs for obvious problems such as weak dynamic margin, high resource occupancy, unstable output, or sensitivity to parameter perturbation. It also keeps the simulation tractable enough to run inside an iterative multi-agent search loop.

這種層級的建模有助於比較候選設計是否存在明顯問題，例如動態邊際微弱、資源佔用過高、輸出不穩定或對參數微擾敏感。它也使模擬保持足夠的計算可行性，以便在迭代的多智能體搜尋迴圈中運行。

The current model does not fully represent:

目前的模型未能完全呈現：

- full plasmid architecture, copy-number dynamics, or sequence-level design constraints;
  完整的質體架構、複製數動力學或序列級設計約束；
- host growth, cell-cycle effects, dilution by growth, or global metabolic regulation;
  宿主生長、細胞週期效應、生長導致的稀釋或全局代謝調節；
- DNA supercoiling, chromatin-like context, RNA folding, codon usage, protein maturation, or degradation-tag behavior;
  DNA 超螺旋、類染色質環境、RNA 折疊、密碼子使用偏好、蛋白質成熟或降解標籤行為；
- detailed transcription-factor binding kinetics or promoter-specific mechanistic models;
  詳細的轉錄因子結合動力學或啟動子特異性機制模型；
- toxicity feedback, burden-growth coupling, or experimentally calibrated noise distributions.
  毒性反饋、負載與生長的耦合，或經實驗校準的雜訊分布。

Therefore, ODE results should be read as a simplified screening signal. Stronger biological claims would require calibrated parameters, real Cello/UCF assignments, sequence-level design checks, and experimental characterization of ON/OFF ratios, growth effects, burden, noise, and stability.

因此，ODE 結果應被視為簡化的篩選訊號。若要做出更強的生物學宣稱，將需要校準的參數、真實的 Cello/UCF 分配、序列級設計檢查，以及對 ON/OFF 比率、生長效應、負載、雜訊和穩定性的實驗表徵。

The current interface and MCP adapter include an ODE explanation layer that reports selected trajectory readouts (`peak_output_protein`, `time_to_peak`, `final_output_protein`), coarse burden readouts (`max_total_mrna`, `max_total_protein`, RNAP/ribosome occupancy), uncertainty metadata, coverage warnings, model limitations, and suggested next checks. These explanations are intended to make the simulation easier to audit; they do not expand the model's biological scope.

目前的介面與 MCP adapter 包含 ODE 解釋層，會回報選定的軌跡讀數（`peak_output_protein`、`time_to_peak`、`final_output_protein`）、粗略負載讀數（`max_total_mrna`、`max_total_protein`、RNAP/核糖體佔用率）、不確定性後設資料、覆蓋缺口警示、模型限制與建議的下一步檢查。這些解釋旨在讓模擬更容易審查；它們並不擴張模型的生物學適用範圍。

For a more detailed discussion of model scope, assumptions, and missing biological mechanisms, see [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md).

如需對模型範圍、假設和缺失的生物學機制進行更詳細的討論，請參見 [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)。

## Repository Map
## 儲存庫地圖

| Path / 路徑 | Purpose / 用途 |
| --- | --- |
| [app.py](app.py) | Streamlit interface, demo workflow, BYOK controls, status panels, and result visualization. <br> Streamlit 介面、展示工作流、BYOK 控制項、狀態面板與結果視覺化。 |
| [schemas/state.py](schemas/state.py) | `DesignState` and `SearchNode` data models used across the Reflexion search tree. <br> 用於整個 Reflexion 搜尋樹的 `DesignState` 和 `SearchNode` 資料模型。 |
| [workflows/reflexion_controller.py](workflows/reflexion_controller.py) | Main multi-agent loop, routing logic, budget handling, and benchmark integration. <br> 主多智能體迴圈、路由邏輯、預算處理與基準整合。 |
| [agents/](agents) | Builder, Translator, Critic, DataMiner, Consolidator, and SkillExtractor agents. <br> Builder、Translator、Critic、DataMiner、Consolidator 和 SkillExtractor 智能體。 |
| [tools/cello_wrapper.py](tools/cello_wrapper.py) | External Cello command integration plus explicit mock-mode fallback. <br> 外部 Cello 指令整合以及明確的模擬模式回退。 |
| [tools/ode_simulator.py](tools/ode_simulator.py) | Resource-aware ODE simulator with optional Monte Carlo perturbation and kinetic scoring. <br> 資源感知 ODE 模擬器，包含可選的蒙特卡羅微擾和動力學評分。 |
| [benchmark_suite/](benchmark_suite) | Functional, kinetic, static plausibility, metabolic burden, temporal, and Cello-constraint evaluators. <br> 功能性、動力學、靜態合理性、代謝負載、時序與 Cello 約束評估器。 |
| [mcp_server/](mcp_server) | Local MCP service for storing and serving run artifacts, including selectable score, decision-trace, Cello-provenance, and ODE explanation outputs. <br> 用於儲存和提供運行產物的本地 MCP 服務，包含可選擇的分數、決策紀錄、Cello 來源與 ODE 解釋輸出。 |
| [tests/](tests) | Unit tests for workflow behavior, topology graphs, ODE charts, MCP server behavior, and external-tool paths. <br> 工作流行為、拓撲圖、ODE 圖表、MCP 伺服器行為與外部工具路徑的單元測試。 |

## Quick Start
## 快速開始

Requires Python 3.11.

需要 Python 3.11。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the Streamlit app, then enter a LiteLLM-compatible model name and API key in the sidebar. The key is kept in the Streamlit session and should not be committed to the repository.

運行 Streamlit 應用程式，然後在側邊欄輸入與 LiteLLM 相容的模型名稱和 API key。金鑰保留在 Streamlit session 中，不應提交到儲存庫。

```powershell
streamlit run app.py
```

The default Cello path is a mock workflow. Real Cello mapping requires an external Cello command and compatible UCF configuration; see [Optional Cello Integration](#optional-cello-integration).

預設的 Cello 路徑是模擬工作流。真實 Cello mapping 需要外部 Cello 指令和相容的 UCF 設定；請參閱[可選的 Cello 整合](#可選的-cello-整合)。

### Development and Tests
### 開發與測試

Install development dependencies and run the full test suite:

安裝開發依賴並運行完整測試：

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

The local MCP adapter has one additional optional runtime dependency:

本機 MCP adapter 另有一個可選的執行依賴：

```powershell
pip install mcp
python -m mcp_server.server
```

See [mcp_server/README.md](mcp_server/README.md) for MCP tools, environment-variable configuration, and focused test commands.

## External Design Import v1

The Streamlit sidebar includes an **External Design Import v1** workspace for
bringing literature or repository designs into the same canonical `DesignIR`
representation used by generated candidates.

Supported entry paths:

- guided entry for source, host, inputs, outputs, logic, validation status, and
  optional biological parts;
- project JSON draft upload and download;
- basic GenBank flat-file parsing for explicitly annotated promoter, RBS, CDS,
  terminator, and regulatory features.

Every imported draft is reviewed before conversion to `DesignIR`. The review
reports data completeness, evidence quality, applicable evaluation sections,
missing fields, and validation warnings. Unknown and not-reported values remain
explicit; they are not silently replaced with assumed biological facts.

Confirmed external designs can be compared with each other or with current
workflow-generated candidates using `DesignDiff`.

GenBank import does not infer circuit inputs, outputs, Boolean logic,
experimental validation, backbone completeness, or assembly readiness. These
fields require user confirmation or additional evidence.

## FastAPI Foundation v1.25

The Streamlit interface and FastAPI adapter now share the same application
services and local JSON repositories. The Streamlit layout remains unchanged,
but confirmed external designs persist across processes under
`outputs/api_data`.

Start the API:

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/docs`.

The versioned `/api/v1` contract currently covers:

- external draft validation and JSON/GenBank import;
- draft confirmation into `DesignIR`;
- design listing and retrieval;
- design comparison and benchmark evaluation;
- BOM, GenBank, and SBOL3 export.

See [api/README.md](api/README.md) for the endpoint list, response envelope,
persistence configuration, and current scope boundaries.

## Web Application Foundation v1.5

The FastAPI process also serves a lower-density, multi-page HTML interface:

```text
http://127.0.0.1:8000/web
```

Pages include Dashboard, New Design, Runs, External Imports, Design Library,
Design Detail, and Compare. Streamlit remains available for the denser
research-oriented inspection interface.

Design workflows run in the background:

```text
POST /api/v1/runs -> 202 Accepted + run_id
GET  /api/v1/runs/{run_id}
GET  /api/v1/runs/{run_id}/events
```

Human feedback and resume operations are available for runs that pause for
input. Run metadata, events, results, and external design records persist under
`outputs/api_data`.

The web and API layers do not accept API keys. Configure LiteLLM/OpenAI
credentials in the server environment so browser clients cannot accidentally
persist or expose them.

## Data Foundation v1.6

Confirmed designs are persisted as DesignIR v2 records in
`outputs/api_data/research.db`. Existing API, HTML, comparison, and export
consumers continue to receive the compatible v1 representation.

DesignIR v2 separates logical specification, biological context, biological
parts, regulatory interactions, ordered constructs, plasmid properties,
field-level provenance, assumptions, validation, extensions, and revision
metadata.

The SQLite repository creates immutable revisions when design content changes.
Saving the same content again is idempotent. Existing
`outputs/api_data/designs/*.json` records are imported once when application
services start.

```text
GET /api/v1/designs/{design_id}/ir-v2
GET /api/v1/designs/{design_id}/revisions
```

Preview a legacy JSON migration with:

```powershell
python -m scripts.migrate_designs_v1_to_v2 `
  outputs/api_data/designs outputs/api_data/research.db --dry-run
```

Background runs now write `run_manifest.json` beside their metadata. It records
the redacted request, model and workflow versions, request/result hashes, and
generated artifact hashes.

## Research Evaluation v1.8

The evaluation layer now exposes explicit, versioned scoring profiles:

- `legacy-weighted@1.0.0` preserves the existing agent workflow score.
- `research-v1.8@1.8.0` adds seven explainable dimensions: logic function,
  dynamic behavior, robustness, resource burden, buildability, evidence
  quality, and data completeness.

Every evaluation includes the profile ID, semantic version, configuration
hash, dimension scores, weights, and applicability metadata. Scores from
different versions should not be treated as directly calibrated equivalents.

The bundled `research_smoke_v1@1.0.0` dataset contains synthetic positive and
negative fixtures. It validates evaluation infrastructure and score direction;
it is explicitly not a wet-lab validation dataset.

```text
GET  /api/v1/evaluation/profiles
GET  /api/v1/benchmarks/datasets
POST /api/v1/benchmarks/runs
GET  /api/v1/benchmarks/runs/{benchmark_run_id}
POST /api/v1/benchmarks/comparisons
```

The HTML workspace is available at `/web/benchmarks`. Benchmark runs persist
under `outputs/api_data/benchmark_runs`, with JSON, CSV, and Markdown reports
under `outputs/api_data/benchmark_reports`.

MCP 工具、環境變數設定與專用測試指令請參閱 [mcp_server/README.md](mcp_server/README.md)。

## Optional Cello Integration
## 可選的 Cello 整合

By default, the workflow can operate without an installed Cello toolchain by using mock topology output. To perform real Cello mapping, configure `CelloWrapper` with an external Cello command and a compatible UCF path. Only externally mapped results should be discussed as Cello mapping results.

預設情況下，該工作流可以藉由使用模擬拓撲輸出，在未安裝 Cello 工具鏈的情形下運行。若要執行真實的 Cello 映射，請使用外部 Cello 指令與相容的 UCF 路徑來配置 `CelloWrapper`。只有外部映射的結果才應作為 Cello 映射結果來討論。

When presenting this project to synthetic biologists, it is better to say:

向合成生物學家展示此專案時，最好說：

> This system generates and evaluates computational candidate designs for regulatory logic circuits.
> 本系統生成並評估調節邏輯電路的計算候選設計。

rather than:

而非：

> This system automatically designs complete plasmids or validated genetic logic gates.
> 本系統自動設計完整的質體或經過驗證的基因邏輯閘。

## Current Research Questions
## 當前的研究問題

- Can a multi-agent Reflexion loop reduce logic, mapping, and scoring failures compared with one-shot generation?
  與單次（one-shot）生成相比，多智能體 Reflexion 迴圈是否能減少邏輯、映射與評分失敗？
- Which benchmark components are most useful for early rejection of weak circuit candidates?
  哪些基準子項最有用於早期拒絕較弱的電路候選方案？
- How should natural-language design constraints be translated into explicit truth tables, Verilog, and biological-part constraints?
  如何將自然語言設計約束轉換為明確的真值表、Verilog 以及生物元件約束？
- What evidence should be required before a computational candidate is described as buildable, plausible, or experimentally meaningful?
  在將計算候選方案描述為可構建、合理或具有實驗意義之前，需要哪些證據？

## For AI-Assisted Review
## 用於 AI 輔助審查

If you are using an AI assistant to quickly understand this repository, you can give it the repository link together with the following prompt:

如果您正在使用 AI 助理來快速了解此儲存庫，您可以將儲存庫連結連同以下提示詞（Prompt）一同提供給它：

```text
Please review this repository as a synthetic-biology research prototype, not as a finished plasmid-design or wet-lab validation platform.

Start with README.md for the high-level overview. Then read LIMITATION.md to understand current capabilities, non-goals, and safe claim boundaries. Read EVALUATION_METRICS.md to understand how candidate designs are scored and why the scores are heuristic. Read MODEL_ASSUMPTIONS.md to understand the reduced resource-aware ODE model and its biological limitations. Read ARCHITECTURE.md and WORKFLOW.md to understand the multi-agent architecture, deterministic checks, fallback behavior, and execution flow.

When summarizing the project, distinguish between:
- computational candidate generation,
- Cello-compatible Verilog generation,
- optional real vs mock Cello mapping,
- simplified ODE-based screening,
- heuristic benchmark scoring,
- and experimental validation, which has not been performed.

Please identify what the project can currently support, what it cannot yet claim, and what evidence would be needed to make stronger biological claims.
```

## Related Documentation
## 相關文件

- [ARCHITECTURE.md](ARCHITECTURE.md): architecture and agent responsibilities.
  [ARCHITECTURE.md](ARCHITECTURE.md)：架構與智能體職責。
- [WORKFLOW.md](WORKFLOW.md): Reflexion workflow details.
  [WORKFLOW.md](WORKFLOW.md)：Reflexion 工作流詳情。
- [EVALUATION_METRICS.md](EVALUATION_METRICS.md): scoring formulas and evaluator behavior.
  [EVALUATION_METRICS.md](EVALUATION_METRICS.md)：評分公式與評估器行為。
- [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md): ODE model scope, assumptions, and biological limitations.
  [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)：ODE 模型範圍、假設與生物學限制。
- [LIMITATION.md](LIMITATION.md): explicit project capabilities, non-goals, and safe claim boundaries.
  [LIMITATION.md](LIMITATION.md)：明確的專案能力、非目標與安全宣稱邊界。
# Current Implementation Update (2026-06-06)
# 目前實作更新（2026-06-06）

The project now includes a typed biological-design layer in addition to the agent workflow and benchmark pipeline:

除了代理工作流程與 benchmark pipeline，專案目前也包含具型別的生物設計層：

- `DesignIR` represents parts, regulatory interactions, ordered constructs, provenance, assignments, validation status, and immutable revisions.
- `DesignIR` 表示元件、調控關係、有序 construct、來源、元件映射、驗證狀態與不可變版本。
- External Cello runs preserve complete artifact directories and manifests for success, failure, and timeout cases.
- 外部 Cello 執行會保存完整 artifact 目錄與 manifest，涵蓋成功、失敗與逾時情況。
- Supported Cello v2 JSON artifacts can be parsed into `part_assignments`.
- 支援的 Cello v2 JSON artifact 可解析為 `part_assignments`。
- A fixed demonstration library, `demo-cello-library@1.0.0`, supports UI, parser, replacement, and test workflows.
- 固定版本示範元件庫 `demo-cello-library@1.0.0` 支援 UI、parser、替換與測試流程。
- Replacement validation creates immutable revisions rather than modifying the source design.
- 元件替換驗證會建立不可變版本，不修改來源設計。
- `DesignDiff` compares candidate parts, constructs, maturity status, and metrics.
- `DesignDiff` 比較候選元件、construct、成熟度狀態與指標。
- The UI exports BOM CSV, GenBank, and SBOL3 Turtle.
- UI 可匯出 BOM CSV、GenBank 與 SBOL3 Turtle。

Export behavior is conservative. GenBank requires complete valid IUPAC DNA sequences for all parts in exported constructs. SBOL3 can represent sequence-less conceptual components but reports warnings. No exporter invents missing sequence data.

匯出行為採保守原則。GenBank 要求匯出 construct 中所有元件都有完整且有效的 IUPAC DNA 序列；SBOL3 可以表示沒有序列的概念性元件，但會回報警告。所有 exporter 都不會自行補入缺失序列。

### External plasmid assembly preview

The v2 API includes a first sequence-complete plasmid assembly path backed by
Biopython and pydna:

```text
POST /api/v2/designs/{design_id}/plasmid-assemblies
```

Backbones must first be registered through `POST /api/v2/backbones` with a
version, trusted source URI, sequence checksum, host metadata, origin,
selection marker, copy-number class, legal insertion regions, and protected
essential regions. Assembly requests reference the registered backbone
version and a zero-based half-open insertion window. The assembler:

- rejects unregistered or checksum-drifted backbone versions;
- blocks insertion outside the selected legal region or across an essential
  region;
- blocks conceptual, illustrative, unknown, or otherwise insufficient part
  evidence;
- preserves and remaps non-overlapping backbone features;
- removes backbone features replaced by the insertion window and reports them;
- applies forward or reverse-complement part orientation;
- writes part and construct provenance into GenBank features;
- validates the final circular molecule with pydna;
- reports CDS framing, host annotation, common restriction sites, tool
  versions, and a sequence checksum.
- records readiness progression from `conceptual` through
  `assembly_check_passed`.

This is a sequence-complete computational assembly preview. Gibson overlap
arms, primers, restriction-fragment planning, codon optimization, and expert
experimental review remain outside this first version.

Relevant implementation paths:

- [schemas/design_ir.py](schemas/design_ir.py)
- [schemas/design_operations.py](schemas/design_operations.py)
- [schemas/design_diff.py](schemas/design_diff.py)
- [tools/cello_artifact_parser.py](tools/cello_artifact_parser.py)
- [tools/part_library.py](tools/part_library.py)
- [part_libraries/](part_libraries)
- [exporters/](exporters)
- [CHANGELOG.md](CHANGELOG.md)

## Simulation Foundation v1.9

The resource-aware ODE core now exposes content-addressed `SimulationSpec`
and `SimulationResult` contracts. They record the model version, chassis,
copy number, truth-table scenarios, solver and Monte Carlo settings,
configuration hash, parameter-set hash, scenario-set hash, and result hash.

DesignIR v2 can be projected into a simulation specification, run manifests
retain simulation identifiers, and the API exposes:

- `GET /api/v1/simulation/models`
- `POST /api/v1/simulations`
- `GET /api/v1/designs/{design_id}/simulation-spec`

`research-v2-preview@1.9.0` links multidimensional scoring to the v1.9
simulation contract without changing the existing v1.8 API default.
Simulation outputs remain computational screening estimates and require
chassis-specific calibration and wet-lab validation.

## Research Workspace v2.0

v2.0 turns the existing data, evaluation, and simulation foundations into an
end-to-end research workspace:

- `/api/v2/research/runs` queues reproducible simulation and evaluation jobs.
- `/web/research` provides a lower-density, step-oriented HTML workspace.
- Research results export JSON, dimension CSV, Markdown, and a run manifest.
- Run comparison checks simulation and scoring versions before ranking.
- Design pages separate overview, constructs, plasmids, evidence, assumptions,
  and simulation readiness.
- `GENETIC_CIRCUIT_DATABASE_URL` enables PostgreSQL while SQLite remains the
  default local repository.

The v1 API remains available for existing clients. v2 research runs use the
v1.9 ODE model contract and `research-v2-preview@1.9.0` scoring profile until
future model or scoring versions are explicitly released.
