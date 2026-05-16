# Workflow & Configuration Guide

本文件說明目前的設計迭代流程、Graph RAG 記憶增長機制，以及 Tree Search controller 如何在不同搜尋模式間切換。系統的主要入口為 [workflows/reflexion_controller.py](workflows/reflexion_controller.py)，全域狀態由 `DesignState` 管理，單次設計嘗試由 `SearchNode` 表示。

## 1. Standard Pipeline

### 1.1 Intent & Memory Retrieval

1. 使用者輸入自然語言需求，例如目標邏輯、宿主、輸入訊號與期望行為。
2. `DesignState.user_intent` 保存原始需求，並初始化 `tree_nodes` 與 `active_frontier`。
3. 若啟用記憶系統，`SkillRetriever` 會依目前 `search_mode` 從 `邏輯設計skill.json` 載入技能，並用 tags / backlinks 做輕量 Graph RAG 檢索：
   - `Exploration`：偏向多樣化 motif、成功案例與可嘗試的設計策略。
   - `Repair`：偏向邏輯修復、錯誤案例與 Critic feedback pattern。
   - `Exploitation`：偏向 part selection、Cello mapping、ODE score 改善與物理層約束。

### 1.2 Node Initialization

若 `DesignState.active_frontier` 與 `DesignState.tree_nodes` 皆為空，Controller 會建立 `root`：

```text
SearchNode(node_id="root", search_mode="Exploration")
```

`root` 會被放入 `active_frontier`。之後每次循環都從 frontier 取出一個節點，設定 `current_node_id`，並依節點模式執行 Agent。

### 1.3 Generation & Translation

1. **BuilderAgent**：[agents/builder_agent.py](agents/builder_agent.py) 根據 `user_intent`、`rag_context` 與 Critic feedback 產生 Cello-compatible logic proposals。
2. **TranslatorAgent**：[agents/translator_agent.py](agents/translator_agent.py) 將 proposals 轉成 Verilog，並檢查 Cello 不支援的語法。
3. 在 `Exploitation` 模式下，Builder 會被略過，Translator 直接沿用父節點的 `logic_proposals`，只做物理層微調。

### 1.4 Mapping & Simulation

1. **Cello Wrapper**：[tools/cello_wrapper.py](tools/cello_wrapper.py) 將 Verilog 映射為 genetic circuit topology。
2. **ODE Simulator**：[tools/ode_simulator.py](tools/ode_simulator.py) 對候選拓撲做動態模擬與評分。
3. Controller 會將節點中的最高分拓撲寫入 `node.best_topology` 與 `node.score`，並同步更新 `DesignState.best_topology`。

### 1.5 Critic & Branching

**CriticAgent**：[agents/critic_agent.py](agents/critic_agent.py) 會輸出 `is_approved`、`error_type` 與具體 feedback。

當 `is_approved=True` 時：

- 節點狀態設為 `Pass`。
- `DesignState.is_completed=True`。
- 搜尋停止，進入 Consolidator。

當節點未通過時，Controller 依 `error_type` 展開分支：

- `LOGIC_ERROR`：建立 `Repair` 子節點，回到 Builder 重新設計邏輯。
- `BOTH`：建立 `Repair` 子節點；若 budget 允許，也建立新的 `Exploration` 子節點。
- `PART_ERROR`：建立 `Exploitation` 子節點，沿用父節點邏輯，直接修物理層。

## 2. Design Iteration Modes

### Exploration Mode

`Exploration` 是預設搜尋模式。它使用較高 temperature，鼓勵 Builder 產生多樣化候選策略。適用於 root node、重新開分支、或現有設計方向不明確時。

### Repair Mode

當 Critic 判定 `LOGIC_ERROR` 或 `BOTH`，系統會切換到 `Repair`。此模式將 Critic feedback 視為主要約束，要求 Builder 重新思考邏輯關係，例如輸入極性、布林表示、gate composition 或不符合需求的 truth table。

### Exploitation Mode

當 Critic 判定 `PART_ERROR`，系統會切換到 `Exploitation`。這表示邏輯層大致正確，但 Cello mapping、part constraints、ODE dynamics 或分數不足。

在此模式下，系統會精準繞過邏輯層：

- 不重新呼叫 Builder。
- 從父節點複製 `logic_proposals`。
- Translator 收到 `MODE: EXPLOITATION` 指令。
- 修正範圍限制在 Verilog 結構、part hints、mapping constraints 與物理實作細節。

這個路徑能保留已經有效的設計意圖，避免把局部物理失敗誤判成需要全面重寫邏輯。

## 3. Frontier, BFS & Beam Search Extension Point

`active_frontier` 是待處理節點佇列。Controller 目前使用 BFS 順序取節點：

```text
current_node_id = active_frontier.pop(0)
```

每個節點被評估後，會依 Critic 結果產生子節點並 append 回 frontier。當前實作是 BFS；若後續加入 beam width，排序依據應以 `node.score`、`confidence_score`、error recoverability 與 mode diversity 綜合決定。

`parent_id` 是分支設計的關鍵。它讓子節點能：

- 繼承父節點的 logic proposals。
- 保留 Critic feedback 歷史。
- 在 `PART_ERROR` 時只修 physical layer。
- 在 Consolidator 或 Archivist 階段追蹤完整設計 lineage。

## 4. Compute Budget

`DesignState.compute_budget` 限制搜尋成本，`used_budget` 追蹤已消耗的分支嘗試。每當節點未通過並需要展開新分支，`used_budget` 會增加。

當 budget 用盡時：

1. Controller 停止處理更多 frontier 節點。
2. 從 `tree_nodes` 中尋找具有 `best_topology` 的最高分節點。
3. 將該拓撲設為 `DesignState.best_topology`。
4. 進入 Consolidator，輸出最佳可用結果與失敗原因。

## 5. Memory Growth Mechanism

單次設計結束後，系統可把搜尋經驗轉化為技能記憶。這個流程由 `SkillExtractorAgent` 擔任 Archivist；在 Streamlit BYOK workflow 中，技能卡會寫入 `outputs/obsidian_skills/`，並加入本次執行的 in-memory vector store。

### 5.1 Skill Extraction

Archivist 會讀取：

- `DesignState.user_intent`
- 成功或最高分 `SearchNode`
- `critic_feedbacks`
- `error_type` 與 dead-end nodes
- 最終 `best_topology`
- Cello / ODE 評分與失敗訊息

然後萃取成技能卡：

- **What worked**：成功 motif、logic blueprint、Verilog pattern。
- **What failed**：導致 `LOGIC_ERROR`、`PART_ERROR` 或 `Dead_End` 的設計。
- **When to use**：適用 host、gate family、intent tags、input/output pattern。
- **How confident**：`confidence_score`，目前主要根據來源節點分數估計，並保留 tags、backlinks、source nodes 與失敗嘗試摘要。

### 5.2 Obsidian Wiki Cards

每張技能卡會被寫成 Obsidian Markdown，包含 tags、backlinks 與結構化 metadata。這讓使用者可以直接瀏覽知識圖譜，也讓 `SkillRetriever` 能用 tags / backlinks 做鄰近技能加分。

範例 metadata：

```yaml
tags:
  - motif/feed-forward
  - host/ecoli
  - failure/part-error
confidence_score: 0.82
source_node: root_exploit_a31f
```

### 5.3 Retrieval Awakening

下一次搜尋開始時，`SkillRetriever` 會：

1. 用 `user_intent` 做關鍵詞 overlap 檢索。
2. 找到初始技能卡。
3. 沿 tags / backlinks 做輕量鄰近擴展。
4. 依 `confidence_score`、`recency_score`、搜尋模式與任務相似度排序。
5. 將最有價值的技能濃縮成 `rag_context`。

因此，每次設計都會增加下一次搜尋可用的經驗，而不是只留下一次性的輸出。

## 6. Graph RAG Pruning

Graph RAG Pruning 用來避免低品質記憶污染 prompt context。當前剪枝策略包含：

- **Confidence threshold**：低於門檻的 `confidence_score` 不注入 prompt。
- **Mode-aware ranking**：`Repair` 偏好 failure recovery，`Exploitation` 偏好 physical tuning，`Exploration` 偏好多樣成功 motif。
- **Negative memory handling**：包含 `Dead_End` 或 avoid pattern 的技能，在非 `Repair` 模式下降權。
- **Recency and validation weighting**：若技能資料提供 `recency_score`，近期成功技能會獲得額外加分。

這讓記憶系統維持可塑性，同時避免舊錯誤被系統反覆放大。

## 7. Configuration Toggles

### Enable RAG

- **ON**：使用 `SkillRetriever` 取得 Graph RAG context，Builder / Translator 可引用歷史技能。
- **OFF**：以 zero-shot 或本地預設 gate library 執行，不使用長期記憶。

### Enable ODE Simulation

- **ON**：使用 ODE Simulator 評估拓撲動態分數，Critic 可根據物理層結果判斷 `PART_ERROR`。
- **OFF**：僅使用 Cello mapping 或靜態 plausibility；Critic 的物理判斷會較弱。

### Enable Multi-Agent Search

- **ON**：啟用 Tree Search、Critic routing、frontier expansion 與 budget fallback。
- **OFF**：執行單次 Builder / Translator / Cello 流程，適合快速 smoke test。

### Enable Caching

- **LLM Caching**：降低相同 prompt 的 API 成本。
- **ODE Caching**：`BatchODESimulator` 在同一執行程序內快取相同拓撲、參數與模擬設定的結果；跨程序持久化快取仍是後續擴充方向。

## 8. Error Handling

### Translator Validation Failure

Translator 會檢查 Cello-compatible Verilog 條件：

- 必須包含 `module` / `endmodule`。
- 必須有 input / output declaration。
- 必須使用 combinational logic。
- 不允許 `always`、`reg`、clock、memory、delay syntax 或 `#`。

若多次修復仍失敗，節點會記錄 `last_error` 並標為 `Dead_End`。

### Cello Mapping Failure

若 Verilog 合法但 Cello 無法映射，Critic 應偏向輸出 `PART_ERROR`。Controller 隨後建立 `Exploitation` 子節點，讓 Translator 針對 mapping constraint 或 part hints 微調。

### Budget Exhaustion

若沒有任何節點 `Pass`，系統會保留所有已評估節點中分數最高且有 `best_topology` 的候選。若 workflow 設定了 `SkillExtractorAgent`，這個結果會被轉成包含失敗脈絡的技能卡。

## 9. Output & Traceability

最終輸出應包含：

- 最佳拓撲與分數。
- 對應 `SearchNode.node_id`。
- 搜尋路徑與 `parent_id` lineage。
- Critic feedback 摘要。
- 若未通過，說明 fallback 原因。
- 可匯出 artifact，例如 Verilog、拓撲 JSON、ODE 結果、Obsidian 技能卡。

這些資料讓使用者能展示最終設計，也能回頭理解系統為何走到該分支。
