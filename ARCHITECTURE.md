# Architecture Documentation

## 1. System Overview

本專案是一個**具備自主學習能力的圖譜導向樹狀搜尋系統**，用於將自然語言需求轉譯為可被 Cello CAD 映射、並可經由 ODE 模擬評估的基因電路設計。系統不再把設計視為固定次數的線性反思流程，而是把每一次嘗試封裝為 `SearchNode`，在 `DesignState` 中形成可分支、可回溯、可剪枝的搜尋樹。

核心思想是：每次設計都同時產生一個候選電路與一段可被重用的設計經驗。成功、失敗與修復過程可在設計結束後由 `SkillExtractorAgent` 萃取成技能記憶；BYOK workflow 會將技能卡寫入 `outputs/obsidian_skills/`，並同步放入本次執行的 in-memory vector store。下一次搜尋時，`SkillRetriever` 會依任務語意、標籤與 backlinks 喚醒相關經驗，讓系統的設計能力能隨著實作次數累積。

整體架構由四個層次組成：

1. **Tree Search Controller**：由 [workflows/reflexion_controller.py](workflows/reflexion_controller.py) 管理 `active_frontier`、`parent_id`、搜尋模式與 compute budget。
2. **Design Agents**：Builder、Translator、Critic、Consolidator 等 Agent 產生、轉譯、評估與彙整候選設計。
3. **Graph RAG Memory**：由 `SkillExtractorAgent`、`SkillRetriever`、JSON skill library、in-memory vector store 與 Obsidian Markdown 技能卡共同支撐技能記憶。
4. **Physical Evaluation Layer**：Cello Wrapper 與 ODE Simulator 將邏輯設計落到可映射拓撲與動態模擬分數。

## 2. Technology Stack

### Core Runtime

- **Python 3**：主要執行環境。
- **Pydantic-style state schema**：`DesignState` 與 `SearchNode` 作為跨 Agent 的狀態契約，定義於 [schemas/state.py](schemas/state.py)。
- **LiteLLM**：統一呼叫多種 LLM backend，並支援 LLM response caching，封裝於 [utils/llm_utils.py](utils/llm_utils.py)。
- **Local simulation cache**：`BatchODESimulator` 會在同一執行程序內快取相同拓撲與參數組合的 ODE 結果，避免重複模擬。

### Genetic Circuit Tooling

- **Cello CAD**：負責將 Cello-compatible Verilog 映射到 genetic circuit topology，介面位於 [tools/cello_wrapper.py](tools/cello_wrapper.py)。
- **SciPy / Pandas**：支援 ODE 模擬與批次結果整理。
- **ODE Simulator**：在 [tools/ode_simulator.py](tools/ode_simulator.py) 中評估候選拓撲的動態表現。
- **Oracle Evaluator**：用於功能正確性與測試向量驗證，位於 [oracle_evaluator.py](oracle_evaluator.py)。

### Long-Term Memory

- **JSON / Vector DB**：目前以 `邏輯設計skill.json` 作為預設技能庫，並提供 [vector_db.py](vector_db.py) 的 in-memory store 與 [tools/vector_retriever.py](tools/vector_retriever.py) 的簡易文字檢索接口。
- **Obsidian Wiki System**：作為知識圖譜的可視化與結構化載體。技能卡匯出器位於 [exporters/obsidian_writer.py](exporters/obsidian_writer.py) 與 [exporters/obsidian_skill_formatter.py](exporters/obsidian_skill_formatter.py)。
- **SkillRetriever**：以關鍵字 overlap、`confidence_score`、mode-aware ranking、tags/backlinks 鄰近加分與 avoid/dead-end 降權進行 Graph RAG 檢索，入口位於 [tools/skill_retriever.py](tools/skill_retriever.py)。

## 3. State Machine Schema

`DesignState` 是整個系統的全域狀態容器；`SearchNode` 則是搜尋樹中的基本單位。狀態不再以單一扁平容器保存全部迭代結果，而是把候選設計、分支歷史、評估分數與錯誤型別錨定到各個節點。

### DesignState

`DesignState` 保存跨節點共享的資訊：

- `user_intent`：使用者原始自然語言需求。
- `host_organism`：目標宿主與生物背景。
- `tree_nodes`：以 `node_id` 為 key 的 `SearchNode` 字典。
- `active_frontier`：待評估節點佇列，目前支撐 BFS 展開，並保留 Beam Search 擴充空間。
- `current_node_id`：目前被處理的節點。
- `compute_budget` / `used_budget`：限制總搜尋成本，避免無界展開。
- `rag_context`：由 `SkillRetriever` 取回的歷史技能與約束。
- `best_topology`：目前全域最高分候選，用於 budget 耗盡時的 graceful degradation。

### SearchNode

`SearchNode` 代表一次具體設計嘗試：

- `node_id`：節點唯一識別碼，例如 `root` 或 `root_repair_ab12`。
- `parent_id`：父節點 ID，用來追蹤分支來源與繼承上下文。
- `children_ids`：子節點列表。
- `search_mode`：`Exploration`、`Repair` 或 `Exploitation`。
- `logic_proposals`：Builder 產生的候選邏輯方案。
- `verilog_codes`：Translator 產生的 Cello-compatible Verilog。
- `candidate_topologies`：Cello / ODE 層產生的拓撲與分數。
- `best_topology` / `score`：該節點內最佳候選與其評分。
- `critic_feedbacks`：Critic 對本節點與其分支的修正建議。
- `error_type`：`LOGIC_ERROR`、`PART_ERROR`、`BOTH` 或 `NONE`。
- `status`：節點生命週期狀態，例如 `Evaluated`、`Pass` 或 `Dead_End`。

`active_frontier` 決定下一批要展開的節點；`parent_id` 讓子節點能繼承或局部覆寫父節點的邏輯、Verilog 與 Critic feedback。這使系統可以同時保留多條設計路徑，而不是把所有修正壓縮成單一路徑。

## 4. Workflow & Agents

主要控制流程位於 [workflows/reflexion_controller.py](workflows/reflexion_controller.py)。Controller 會在沒有節點時建立 `root`，再從 `active_frontier` 取出節點並依 `search_mode` 調整溫度、記憶檢索與分支策略。

### BuilderAgent

[agents/builder_agent.py](agents/builder_agent.py) 將 `user_intent`、宿主條件、`rag_context` 與 Critic feedback 轉成三個 Cello-compatible 邏輯設計。當節點處於 `Repair` 模式時，Builder 會被要求重新思考邏輯結構；在一般 `Exploration` 模式則鼓勵較高多樣性。

### TranslatorAgent

[agents/translator_agent.py](agents/translator_agent.py) 將邏輯設計轉成 Cello-compatible Verilog。它包含 AST-like validation，會拒絕 `always`、`reg`、delay syntax、clocked logic 等 Cello 不支援的語法。當節點為 `Exploitation` 模式時，Translator 只應微調 part assignment 或約束，不改變邏輯架構。

### CriticAgent

[agents/critic_agent.py](agents/critic_agent.py) 評估邏輯正確性、Cello mapping 與 ODE simulation score，並輸出：

- `LOGIC_ERROR`：需求理解或布林邏輯錯誤，應回到 Builder。
- `PART_ERROR`：邏輯可用但物理層、part 選擇、mapping 或動態分數不佳，應走 Translator / physical refinement。
- `BOTH`：邏輯與物理層都需要修正。
- `NONE`：節點通過。

### ConsolidatorAgent

[agents/consolidator_agent.py](agents/consolidator_agent.py) 在搜尋完成或 budget 耗盡後彙整最終設計、最佳拓撲、評估結果與可匯出的 artifact。

### SkillExtractorAgent

[agents/skill_extractor_agent.py](agents/skill_extractor_agent.py) 扮演 **Archivist**。它在設計流程結束後讀取 `DesignState` 的搜尋樹、成功節點、失敗節點、Critic feedback 與最終拓撲，萃取成可重用的設計技能。若設定 `vault_dir`，會透過 Obsidian writer 輸出 Markdown 技能卡；若設定 `vector_db`，會同步新增技能 record。技能內容會包含：

- 適用意圖與宿主背景。
- 成功的 logic motif 或 Verilog pattern。
- 應避免的 part / mapping / simulation 失敗模式。
- `confidence_score`、tags、backlinks 與相關節點引用。

### SkillRetriever

[tools/skill_retriever.py](tools/skill_retriever.py) 在搜尋前與不同分支模式下提供 Graph RAG context。它會依技能文字、tags 與 backlinks 做輕量圖譜擴展：

1. 以 `user_intent` 的關鍵詞 overlap 取得候選技能。
2. 從命中技能的 tags / backlinks 出發，擴展到相鄰 motif、host、gate family、failure mode。
3. 以 `confidence_score`、`recency_score`、mode relevance 與 dead-end 降權重新排序。
4. 將高品質技能壓縮成 `rag_context` 注入 Builder / Translator。

## 5. Tree Search Control

Controller 的搜尋行為目前是 BFS frontier expansion，並保留 beam ranking 的擴充點：

- `active_frontier.pop(0)` 讓節點以 BFS 順序被處理。
- 每個節點完成 Critic 評估後，依 `error_type` 產生子節點。
- `LOGIC_ERROR` 或 `BOTH` 會產生 `Repair` 子節點；budget 允許時也會產生新的 `Exploration` 子節點。
- `PART_ERROR` 會產生 `Exploitation` 子節點，沿用父節點的 `logic_proposals`，只在物理層調整。
- `score` 與 `best_topology` 讓 controller 在 budget 耗盡時仍可退回最高分節點。

### Compute Budget

`compute_budget` 是全域搜尋預算，`used_budget` 會在節點未通過並需要展開分支時增加。當 `used_budget >= compute_budget`，Controller 會停止擴展 `active_frontier`，從所有已評估節點中選出最高分且具有 `best_topology` 的候選作為 fallback。

## 6. Resilience Mechanisms

### Graceful Degradation

若沒有任何節點通過，系統不會丟棄所有工作，而是回到搜尋樹中最高分的 `best_topology`。這讓展示或實驗流程仍能產生可分析的輸出，同時保留失敗節點給 Archivist 萃取負面經驗。

### PART_ERROR Feedback Loop

`PART_ERROR` 表示設計問題主要出現在 physical implementation 層。Controller 會建立 `Exploitation` 子節點，並讓 Translator 繼承父節點邏輯，只根據 Critic feedback 微調 Verilog 結構、part constraints 或 Cello mapping hints。這可以避免高成本地重跑 Builder 邏輯設計。

### Traceability

每個 `SearchNode` 都記錄 parent-child 關係、候選拓撲、分數與 feedback。搭配輸出 artifact、Obsidian 技能卡與本次執行的 vector record，可以回溯每個決策是從哪個分支、哪段 feedback 與哪份歷史記憶產生。

## 7. Performance & Caching Optimization

### LLM API Caching

[utils/llm_utils.py](utils/llm_utils.py) 封裝 LLM 呼叫與 caching，降低相同 prompt / context 重複呼叫的成本。

### ODE Simulation Caching

[tools/ode_simulator.py](tools/ode_simulator.py) 會依拓撲、參數與模擬設定建立 process-local cache key，重複拓撲在同一執行程序內可直接重用模擬 payload。

### Graph RAG Pruning

Graph RAG 記憶層會使用 `confidence_score` 做動態剪枝，避免低品質或過時記憶干擾新的設計：

- 低於門檻的技能卡不進入 prompt context。
- 與目前 `search_mode` 不相符的記憶會降權，例如 `Repair` 模式優先取 failure recovery pattern。
- 多次導致低分或 `Dead_End` 的技能會被標記為 avoid pattern。
- 高信心且近期成功的 motif 會在 tags / backlinks 鄰近擴展時獲得較高排序。

這個剪枝機制讓記憶系統保留探索性，但不讓錯誤經驗在後續搜尋中被過度放大。

## 8. Future Roadmap

- 補齊 `DesignState` / `SearchNode` schema 的完整型別定義與序列化測試。
- 將 in-memory vector store 升級為持久化向量資料庫，例如 ChromaDB。
- 將 ODE cache 升級為跨程序持久化快取。
- 將 Beam Search 寬度、`compute_budget` 與 mode transition policy 暴露到 Streamlit UI。
- 擴充 CRISPR / multi-cellular circuit 的 part library 與 Cello mapping constraints。
