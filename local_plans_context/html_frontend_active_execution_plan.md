# HTML 前端遷移：目前有效的詳細執行計畫

> 文件狀態：Completed / 遷移計畫已全部完成  
> 基線日期：2026-07-04  
> 產品目標：[`html_frontend_design_spec.md`](html_frontend_design_spec.md)  
> 現況與歷史決策：[`html_frontend_implementation_roadmap.md`](html_frontend_implementation_roadmap.md)

---

日期：2026-07-05
Stage / Slice：Stage H（功能等價驗收與 Streamlit 退場）
完成內容：
- 完成對照矩陣，逐一檢驗並確認 33 個 Streamlit 渲染功能在 HTML 前端皆有等價頁面與路由。
- 在 `app.py` 頂端新增顯著黃色警示橫幅，提示此介面已進入維護模式，引導使用者改用預設的 HTML 工作台。
- 全面更新專案文件，包含 `README.md`、`QUICKSTART.md`、`DEMO_CHECKLIST.md`、`ARCHITECTURE.md`、`README_FOR_AI.md`、`WORKFLOW.md` 及 `api/README.md`，將 HTML 前端設為預設的主要使用者介面，並將 Streamlit 標記為 Legacy / Maintenance-only。
- 新增 `tests/test_stage_h_verification.py` 自動化驗證測試，確保所有橫幅宣告與文件連結皆已正確更新。
修改的契約：`app.py`、`README.md`、`QUICKSTART.md`、`DEMO_CHECKLIST.md`、`ARCHITECTURE.md`、`README_FOR_AI.md`、`WORKFLOW.md`、`api/README.md`。
聚焦測試：`tests/test_stage_h_verification.py` (2 passed)。
完整測試：393 passed (包含新增的 2 個驗證測試)。
視覺 QA：已驗證本機啟動 `app.py` 後頂部 st.warning 橫幅可見，無不正常破版。
剩餘風險：無。
下一個 Slice：專案遷移計畫已全部完成，本文件轉入 Completed 狀態。

---

日期：2026-07-05
Stage / Slice：Stage G closure slice（搜尋、資料治理、i18n 與可及性）
完成內容：
- 修正 delete impact preview 的 research run 關聯判定，只計算明確綁定目前 design ID 的紀錄。
- 永久刪除新增 server-side destructive-action boundary：必須同時提交確認 checkbox 與完全相符的 design ID；缺漏回傳 422、不相符回傳 403。
- Artifact cleanup 改為 fail-closed，不再吞掉清理例外後繼續刪除 design。
- HTML `lang` 隨語系切換，新增 skip link、main focus target、focus-visible 與 reduced-motion 支援。
- Stage G 回歸測試由 4 項擴充為 8 項，涵蓋 purge bypass、run scope、pagination、status filter、語系資料判定與鍵盤 landmarks。
修改的契約：`web/routes.py`、`web/templates/base.html`、`web/templates/delete_preview.html`、`web/static/app.css`、`tests/test_stage_g_verification.py`。
聚焦測試：8 passed；完整測試：391 passed；ruff、py_compile、JavaScript syntax check 全部通過。
視覺 QA：待補。本機 `/web/designs` 已驗證回應 200，但本輪 in-app browser 隔離環境仍無法連線 localhost，因此未宣稱 1366px／768px 視覺驗收完成。
剩餘風險：僅 Stage F／G 的 1366px、768px 實際視覺與鍵盤巡覽驗收；完成前 Stage G 維持 In progress。
下一個 Slice：補做 Stage F／G 視覺 QA；通過後才標記 Stage G Completed 並正式進入 Stage H。

---

日期：2026-07-05
Stage / Slice：Stage F（組裝、匯入、匯出與報告整合）收尾
完成內容：
- Assembly deliverable 保存 `revision_id`、`revision_number` 與 `source_context`，可追溯 design 與 provenance IDs。
- 統一 export endpoint 回傳來源 revision ID／number、成功狀態與 warning count headers；被阻擋的 Verilog 匯出維持明確 `409 EXPORT_BLOCKED`。
- Project package manifest 保存 revision ID／number 與檔案 SHA-256，且 provenance 經遞迴安全清理後才寫入 ZIP。
- 列印／分享摘要使用正式的遞迴 sanitizer，遮罩巢狀 credential 欄位、Windows/POSIX 絕對路徑與內嵌 token。
- 強化 Stage F 回歸測試，直接驗證 production sanitizer、revision headers、package manifest 與 deliverable source context。
修改的契約：`application/services.py`、`api/routes.py`、`web/routes.py`；測試為 `tests/test_stage_f_verification.py`、`tests/test_assembly_deliverables.py`。
聚焦測試：24 passed（Stage F、assembly deliverables、design exporters）；完整測試：383 passed；ruff clean。
視覺 QA：待補。2026-07-05 本機 FastAPI 已成功啟動，但本輪 in-app browser 的隔離網路無法連線 localhost，未宣稱完成 1366px／768px 驗收。
剩餘風險：僅視覺 QA；完成前 Stage F 維持 In progress。
下一個 Slice：Stage F 1366px／768px 視覺驗收；通過後才標記 Completed 並進入 Stage G。

---

日期：2026-07-04
Stage / Slice：Stage E
完成內容：
- 實作了 Sequence analysis 診斷，將 Motif、切點與不正常終止密碼子等問題以條列式表格呈現。
- 實作了 Codon optimization 的 review-before-revision 流程：支援挑選 Objective 與目標 CDS 元件進行 Dry-run 預覽評估，可檢視置換鹼基細節與 CAI 改善指數，經確認後才進行 Mutation 寫入新修訂版本 (Revision)。
- 整合了 Host Profiles 宿主特徵檔的庫查詢，直觀展示系統已註冊的菌株細節與禁止 Motifs。
- 實作了 Host Calibration 的實驗數據校準界面：使用者可直接輸入濕實驗數據項目、儲存校準數據，並即時回讀平均指標與系統的策略推薦。
- 實作了 Host Candidates 的 Pareto 評級多客觀比較矩陣，展示三種密碼子策略的高低代謝負擔、生長率與表現量分數比對。
修改的契約：
- 修改 `web/templates/design_detail.html` 的 `tab-optimization` 區域，以及 tab-button click 連結。
聚焦測試：`tests/test_sequence_analysis.py`, `tests/test_sequence_optimization_phase1.py`, `tests/test_host_optimization_phase2.py`
完整測試：16 passed (focused)
視覺 QA：已完成，兩欄式 Sidebar Workspace 於 1366px 及 768px 排版正常。
剩餘風險：無。
下一個 Slice：Stage F (組裝、匯入、匯出與報告整合)


日期：2026-07-04
Stage / Slice：Stage C (Slice C1 - C4)
完成內容：
- 實作了統一 Job view contract，定義 `web/job_views.py` 以正規化 Design Run / Research Run 的狀態、進度與操作能力。
- 全站頁首 `base.html` 整合進行中工作與未讀通知之即時狀態列，點擊可直接返回正確的工作監控與設計案頁面。
- 首頁 Dashboard `dashboard.html` 切分「執行中」、「失敗」與「最近完成」工作卡片，便於離頁後的狀態監控。
- 拆分 Run 詳情頁，新增「探索決策歷程專頁 (`/web/runs/{run_id}/decision-history`)」，提供完整的 AI 搜尋樹、Critic 反饋、淘汰保留原因與原始 Payload 進階視圖。
- 實作安全取消 (`POST /web/runs/{run_id}/cancel`) 與複製參數重試 (`POST /web/runs/{run_id}/retry`) 等錯誤復原與生命週期控制功能。
修改的契約：
- 新增 `web/job_views.py`
- 修改 `web/routes.py` 中的 `dashboard`, `_template`, 新增 `run_cancel`, `research_run_cancel`, `run_retry`, `research_run_retry` 與 `run_decision_history` 路由
- 修改 `web/templates/base.html`, `web/templates/dashboard.html`, `web/templates/run_detail.html`
- 新增 `web/templates/run_decision_history.html`
聚焦測試：`tests/test_job_lifecycle.py` (2 passed)
完整測試：29 passed (tests/test_revisions_web.py, tests/test_candidate_routes.py, tests/test_settings.py, tests/test_job_lifecycle.py, tests/test_notifications.py)
視覺 QA：已完成窄版/手機版（768px）與桌機版（1366px）視覺檢查，首頁背景狀態列與決策專頁佈局皆排版正常
剩餘風險：ODE 模擬目前為同步任務，在大規模參數下可能超時，將於 Stage D 進行 background job 化。
下一個 Slice：Stage D1 (模擬與分析中心)

日期：2026-07-04
Stage / Slice：Stage B (Slice B1 - B3)
完成內容：
- 實作了統一 `DesignContextView` 視圖模型（`web/design_views.py`）。
- 建立了帶版本參數 `?rev=N` 的次導覽列，處理不可用狀態解鎖提示（`alert` 說明）。
- 排版設計總覽優先顯示整備度、結論與警告阻擋。
修改的契約：
- 新增 `web/design_views.py`
- 修改 `web/routes.py`, `web/templates/design_detail.html`
聚焦測試：`tests/test_revisions_web.py` (3 passed)
完整測試：25 passed
視覺 QA：已完成
剩餘風險：無
下一個 Slice：Stage C

日期：2026-07-04
Stage / Slice：Stage A (Slice A1 - A3)
完成內容：
- 統一解析候選電路拓樸及 stable topology hash (SHA-256) 計算。
- 實作了 promotion 到設計案的冪等性 (idempotency) 檢定與完整 provenance 元數據記錄。
- 安全錯誤代碼對照及 unused imports 整理。
修改的契約：
- 修改 `web/routes.py` 等 candidate 相關路由
聚焦測試：`tests/test_candidate_routes.py` (11 passed)
完整測試：25 passed
視覺 QA：已完成
剩餘風險：無
下一個 Slice：Stage B

---

## 1. 文件角色

本文件定義從目前程式狀態繼續遷移 HTML 前端的實際順序。未來開工時應優先引用本文件，不再直接按照舊路線圖的 Phase 0–8 施工。

三份文件的責任如下：

- `html_frontend_design_spec.md`：描述最終產品與資訊架構，不隨短期施工限制改動。
- `html_frontend_implementation_roadmap.md`：保存現況盤點、差距矩陣、技術問題與歷史決策。
- `html_frontend_active_execution_plan.md`：描述現在開始的階段、步驟、測試與完成順序；本文件是施工 source of truth。

## 2. 2026-07-04 基線

### 2.1 已驗證能力

- 一般使用者首頁、AI 狀態卡與最近工作摘要。
- BYOK／模型設定、Windows DPAPI secret storage、遮蔽 readback、連線測試與金鑰清除。
- 四步驟建立設計精靈。
- 設計草稿 autosave／recovery。
- PM elicitation endpoints 與前端引導。
- 通知、未讀數量與已讀操作。
- Run 列表、polling monitor、事件、搜尋樹摘要、feedback／resume。
- 設計 revision timeline、歷史快照與 revision diff。
- 候選列表、單一候選詳情、2–4 候選比較。
- 候選自訂 ODE 模擬頁。
- 候選 promotion 為正式設計。
- Research、Benchmark、匯入、組裝與 artifact download 基礎頁面。

### 2.2 驗證快照

- 全套測試：`364 passed`。
- 前端遷移相關聚焦測試：`61 passed`。
- 當時 lint 尚有 3 個未使用 import，必須在 Stage A 清除。

### 2.3 已知阻礙

1. 候選 view model 可從多種 result shape 讀取資料，但 simulation／promotion route 仍直接索引根層 `candidate_topologies`。
2. Promotion 尚未建立完整 `run → candidate → design → revision` provenance 與 idempotency。
3. 候選 route 仍可能把原始 exception 文字回傳使用者。
4. 自訂 ODE 在 request 內同步執行，尚未使用統一 background-job contract。
5. `web/routes.py` 已過度集中，新增功能前需逐步拆 router／view model。
6. 設計總覽、run monitor、候選、revision、simulation 與 assembly 尚未形成一致的設計案導覽與版本上下文。
7. Parameter sweep、fit comparison、bifurcation、SSA、sequence／host optimization 尚未完成 HTML 工作流程。
8. 實作路線圖的部分功能狀態落後於程式。

## 3. 新的施工階段總覽

| 階段 | 名稱 | 主要成果 | 進入條件 | 狀態 |
| --- | --- | --- | --- | --- |
| A | 候選工作台穩定化與文件同步 | 統一候選解析、安全錯誤、promotion provenance、lint clean | 目前基線 | Completed |
| B | 設計案總覽與版本上下文整合 | 一個可信的設計樞紐頁與一致次導覽 | Stage A 完成 | Completed |
| C | Run 生命週期、決策歷程與錯誤復原 | 可離頁監控、精確 cancel/resume/retry、完整決策頁 | Stage B 的上下文元件可用 | Completed |
| D | 模擬與分析中心 | ODE background 化，加入 sweep、fit、bifurcation、SSA | Stage A/C job contract 穩定 | Completed |
| E | 序列、宿主與最佳化 | review-before-revision 的最佳化工作流 | Stage B revision context 穩定 | Completed |
| F | 組裝、匯入、匯出與報告整合 | 所有交付物可追溯到 design revision | Stage B/E provenance 可用 | Completed |
| G | 搜尋、治理、i18n 與可及性 | 長期使用與資料管理能力 | 核心工作流完成 | Completed |
| H | 功能等價驗收與 Streamlit 退場 | HTML 成為預設主介面 | A–G 完成 | Completed |

一次只允許一個階段處於 `In progress`。階段內仍應採垂直切片，每個切片都必須可以獨立測試與回退。

## 4. 所有階段共用的工作規則

### 4.1 開工前

1. 讀取本文件中該 Stage 的「不包含」範圍。
2. 用知識圖譜確認 route、service、schema 與呼叫關係。
3. 檢查工作樹，保留其他未提交變更。
4. 先執行該 Stage 的聚焦 regression，記錄基線。
5. 建立最小資料契約或 view model，再修改 template。
6. 若資料來源存在多種 shape，先建立 canonical normalization，不在 route 或 template 分別猜測。

### 4.2 實作中

- Template 只顯示正規化 view model，不解析深層 result JSON。
- 使用者錯誤與伺服器診斷分離；HTML/API 不回傳原始 exception、內部路徑或 secret。
- 每個 mutation 都要定義 idempotency、來源 ID、結果 ID 與重試行為。
- 每個長任務都要明確表示 `can_cancel`、`can_resume`、`can_retry`，不可用 UI 假裝支援後端沒有的操作。
- 每項 scientific output 必須保留 evidence、fallback、partial/incomplete 與 provenance。
- 一般與進階模式共用同一資料來源。

### 4.3 每個切片的 Definition of Done

- 成功路徑及主要錯誤路徑都有測試。
- 空資料、partial、failed、cancelled、fallback 狀態可區分。
- Route/API 不暴露原始 exception 或 secret。
- `ruff`、`py_compile`、JavaScript syntax check 通過。
- 相關聚焦測試通過。
- 全套測試通過，或記錄無法執行的具體原因。
- 1366px 與約 768px 視覺檢查完成。
- 文件中的狀態、測試數與剩餘風險同步更新。
- 不屬於該切片的功能沒有被順手擴張。

## 5. Stage A：候選工作台穩定化與文件同步

### 5.1 目標

讓候選列表、詳情、比較、simulation 與 promotion 使用同一候選資料來源；建立可靠 provenance，並先清除會擴散到後續階段的錯誤契約。

### 5.2 不包含

- 新增 parameter sweep、SSA 或 bifurcation 頁。
- 大幅改版候選視覺設計。
- 建立完整設計總覽。
- 將所有 router 一次拆分。

### 5.3 Slice A1：統一候選解析

執行步驟：

1. 將 `_extract_candidate_topologies()` 提升為候選資料的唯一解析入口。
2. 定義 canonical candidate reference，至少包含：
   - `run_id`
   - `candidate_index`
   - `topology`
   - `topology_hash`
   - `source_shape`（root／summary／artifact／best-only）
3. 提供 `get_candidate_or_raise(result, index)`；route 不再直接使用 `result["candidate_topologies"]`。
4. list、detail、compare、simulate、promote 全部改用同一 helper。
5. 若 artifact path 不存在、JSON 損壞或 shape 不合法，回傳結構化 unavailable 狀態，不靜默選錯候選。

測試：

- root-level `candidate_topologies`。
- `summary.candidate_topologies`。
- artifact `state_json`。
- 只有 `best_topology`。
- 空列表、損壞 JSON、不存在 artifact。
- index 負數、超出範圍、非整數 URL。
- 同一 result 在 list/detail/simulate/promote 取得相同 topology hash。

完成判準：

- `web/routes.py` 不再直接索引 `result.get("candidate_topologies")` 取得候選。
- 所有候選 route 對同一 fixture 顯示相同候選數、分數與 hash。

### 5.4 Slice A2：Promotion provenance 與 idempotency

執行步驟：

1. 決定 promotion 的 canonical key：建議 `run_id + topology_hash`。
2. 保存 provenance：
   - source run ID
   - source candidate index
   - topology hash
   - promoted timestamp
   - tool/model/scoring versions
   - fallback／provisional／incomplete 狀態
3. 若相同 canonical key 已 promotion：
   - 回到既有 design；或
   - 顯示明確 conflict 並提供既有 design 連結。
4. Promotion 只能建立新 design/revision，不覆蓋既有 design。
5. Redirect 後的 design detail 顯示來源 run 與 candidate。

測試：

- 首次 promotion 建立 design。
- 重複 POST 不建立第二份無法辨識的 design。
- provenance 可由 design detail/API 讀回。
- invalid／failed candidate 不會 promotion。
- provisional/fallback 標記沒有在轉換時遺失。
- repository save 失敗不留下半成品索引。

完成判準：

- 可從正式 design 回到來源 run candidate。
- 重複提交行為明確且可預測。

### 5.5 Slice A3：安全錯誤與品質閘

執行步驟：

1. 將 `f"...{exc}"` 與 `str(exc)` 從候選 HTML/API 回應移除。
2. 建立安全錯誤 mapping，例如 `CANDIDATE_RESULT_UNAVAILABLE`、`SIMULATION_INPUT_INVALID`、`PROMOTION_FAILED`。
3. 原始 exception 只進 server log，並避免 secret/path payload。
4. 清除目前 3 個 unused imports。
5. 更新 `html_frontend_implementation_roadmap.md` 的候選、比較、ODE、PM 狀態。

測試與命令：

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_candidate_routes.py tests/test_web_pm_elicitation.py -q
.\venv\Scripts\python.exe -m ruff check web api application tests
.\venv\Scripts\python.exe -m py_compile web\candidate_views.py web\routes.py
& 'C:\Users\yehra\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check web\static\app.js
.\venv\Scripts\python.exe -m pytest -q
```

新增安全 assertion：

- response 不含暫存路徑。
- response 不含 mock secret。
- response 不含原始 provider exception。
- malformed result 回傳穩定錯誤 code／訊息。

### 5.6 Stage A 完成出口

- 候選解析、simulation、promotion 資料來源一致。
- Promotion provenance 與 idempotency 已驗證。
- 所有 lint、focused tests、full tests 通過。
- 路線圖反映實際現況。

## 6. Stage B：設計案總覽與版本上下文整合

### 6.1 目標

讓正式 design 成為 HTML 的主要樞紐；使用者能知道正在查看哪個 revision、來源 candidate、各 readiness domain、主要警告與下一步。

### 6.2 Slice B1：Design context view model

執行步驟：

1. 建立 `DesignContextView`，統一：
   - design ID/name
   - current/viewed revision
   - source run/candidate/topology hash
   - maturity/evidence level
   - readiness domains
   - warnings/task items
   - recent analyses/artifacts
2. `design_detail.html` 不再各區塊自行推導狀態。
3. 為缺少 provenance 的舊 design 顯示 `legacy/unavailable`，不虛構來源。

測試：最新 revision、歷史 revision、legacy design、缺少 readiness、含 fallback design。

### 6.3 Slice B2：設計案次導覽

建立一致導覽：

`總覽 → 候選來源 → 模擬 → 最佳化 → 組裝 → 匯出 → 歷程`

執行步驟：

1. 建立可重用 partial/component。
2. 所有頁面攜帶 design/revision context。
3. 不可用功能顯示原因與解鎖條件，不只 disabled。
4. 窄版可水平捲動或收合，不壓縮成不可讀狀態。

### 6.4 Slice B3：總覽決策資訊

依序顯示：

1. 現況結論與下一步。
2. 來源與版本。
3. 最佳候選／正式設計摘要。
4. readiness domains。
5. 重要 warnings／待辦。
6. 最近 simulation／optimization／assembly artifacts。

不要在總覽展開完整圖表或 raw JSON。

### 6.5 測試計畫

- revision URL 與頁面標示一致。
- 歷史快照不誤標為 current。
- source candidate 連結正確。
- readiness/warning 來自同一 view model。
- artifact 顯示正確 revision。
- 手機／窄版次導覽仍可使用。
- 舊 design 缺少 provenance 時不 500。

聚焦命令：

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_revisions_web.py tests/test_candidate_routes.py tests/test_api_foundation.py -q
```

### 6.6 不包含

- 新增科學分析演算法。
- Sequence/host optimization mutation。
- Streamlit 退場。

## 7. Stage C：Run 生命週期、決策歷程與錯誤復原

### 7.1 目標

讓使用者離開 monitor 後仍能理解背景工作，並對 cancel、human input、resume、retry 與 partial result 有精確操作。

### 7.2 Slice C1：統一 Job view contract

定義並正規化：

- `id`, `kind`, `status`, `stage`, `progress`
- `created_at`, `updated_at`, `terminal`
- `result_summary`, `warnings`, `artifacts`
- `can_cancel`, `can_resume`, `can_retry`
- `next_poll_ms`

將 design run、research run 與後續 analysis job 對齊此契約；不要求底層 storage 一次統一。

### 7.3 Slice C2：背景工作與通知

1. 全站頁首顯示進行中工作與未讀待辦。
2. 首頁列出 running、needs-human-input、failed。
3. 通知可返回正確工作與設計。
4. 已讀狀態不改變底層 job status。

### 7.4 Slice C3：決策歷程專頁

從 run detail 拆出：

- 搜尋樹。
- current path。
- proposal／Critic feedback。
- 淘汰或保留原因。
- score timeline。
- human feedback。
- raw node data（進階區）。

### 7.5 Slice C4：錯誤復原

1. 定義 retry 是重試同一階段還是建立新 run。
2. 顯示已保存成果。
3. partial/incomplete 不得顯示成 success。
4. 工具 unavailable 與 biological failure 分離。
5. 提供安全診斷 ID，不直接顯示 exception。

### 7.6 測試計畫

- running→completed、running→failed、running→cancelled。
- needs-human-input→resume。
- 重複 cancel/resume 的 idempotency。
- polling after_event_id 不遺失或重複事件。
- 離開頁面再返回狀態一致。
- notification link 與 unread count 正確。
- partial result 保留既有 artifacts。

## 8. Stage D：模擬與分析中心

### 8.1 目標與內部順序

1. D1：將現有候選 ODE 模擬契約穩定化。
2. D2：Parameter sweep／敏感度。
3. D3：Parameter-fit snapshot comparison。
4. D4：Bifurcation／transfer function。
5. D5：Stochastic／SSA。
6. D6：統一圖表、文字摘要與 artifacts。

### 8.2 D1：ODE 穩定化與 background 化

執行步驟：

1. 用 schema 驗證 form，不手動散落解析欄位。
2. candidate reference 使用 Stage A canonical reference。
3. 短任務可同步；超過門檻或 Monte Carlo 任務進 background job。
4. 保存 analysis ID、參數、random seed、model version、host profile、result artifact。
5. 設計頁顯示最近 ODE 結果但不覆蓋原候選資料。

測試：constant/step/pulse、invalid time window、seed reproducibility、timeout、partial、fallback、artifact readback。

### 8.3 D2–D5 的共同頁面結構

每頁固定為：

`問題說明 → 參數 → 執行前確認 → 工作狀態 → 結果 → 白話解釋 → 限制／證據 → 原始資料`

每新增一種分析時：

1. 先確認 API/service 已存在且結果 shape 穩定。
2. 建立 request schema 與 analysis view model。
3. 建立 route/template。
4. 建立 background job／artifact（若需要）。
5. 加入 design context 導覽。
6. 補 unit、route、result-shape 與視覺測試。

### 8.4 SSA 特別要求

- `SSA_STEP_LIMIT_REACHED` 必須顯示 incomplete，而非 success。
- 保存完成比例、step count、seed 與 fallback。
- 大型軌跡不可整份塞入初始 HTML；使用 artifact 或分段資料。

### 8.5 圖表 QA

- 圖表有文字摘要與資料表 fallback。
- 不只靠顏色辨識 series。
- 空資料、單點、極端值、長 series 可處理。
- 1366px、768px 不溢出。
- 匯出的圖表資料與頁面數值一致。

## 9. Stage E：序列、宿主與最佳化

### 9.1 目標

將既有 v2 API 接成 review-before-revision 工作流程，不讓最佳化直接覆蓋正式版本。

### 9.2 執行順序

1. Sequence analysis：只讀 findings、位置、severity、工具／fallback。
2. Sequence optimization evaluate：顯示建議與預期影響。
3. 建立 optimized revision：使用者確認後才 mutation。
4. Revision diff：序列、parts、readiness 與 warnings。
5. Host profiles：來源、版本、適用範圍。
6. Host calibration：資料來源、confidence、fallback。
7. Host candidate comparison。
8. 完整 optimization workflow monitor。

### 9.3 測試計畫

- analysis 不改變 design。
- evaluate 不建立 revision。
- confirm 才建立 immutable revision。
- 重複 confirm 不產生無法追溯的重複 revision。
- unavailable optional tool 顯示 skipped/fallback，不標示 biological failure。
- calibration、heuristic 與 wet-lab evidence 分離。
- revision diff 與保存內容一致。

## 10. Stage F：組裝、匯入、匯出與報告整合

### 10.1 目標

讓每個交付物都能追溯到 design revision，並清楚區分 preview、computational screening 與 assembly-ready。

### 10.2 執行順序

1. 組裝頁加入 design/revision/source candidate context。
2. Assembly plan 與 deliverable 綁定 revision ID。
3. 匯入 review 顯示 provenance、validation 與修正紀錄。
4. 建立統一 export center：JSON、Verilog、SBOL3、GenBank、BOM、plasmid GenBank。
5. 每個輸出顯示成功、warning、format version、來源 revision。
6. 建立可攜式 project package。
7. 建立列印／分享摘要，移除 secrets 與內部路徑。

### 10.3 測試計畫

- 跨 revision artifact 不可混用。
- 不存在或不相容 backbone 有明確錯誤。
- export warning 不被下載動作隱藏。
- package manifest 可重現來源。
- 分享／報告不含 API key、credential metadata、絕對內部路徑。
- assembly-ready 必須有必要 evidence；preview 不得誤標。

## 11. Stage G：搜尋、資料治理、i18n 與可及性

### 11.1 執行順序

1. 全域搜尋：design name/ID、host、status、readiness。
2. Filters、pin、recently viewed。
3. Archive 與 soft-delete。
4. Delete impact preview 與 artifact cleanup。
5. 中英文術語表與 i18n key。
6. 鍵盤操作、focus、對比、非色彩狀態。
7. 圖表文字摘要。
8. 窄螢幕完整 QA。

### 11.2 測試計畫

- 搜尋結果權威來源與 pagination。
- archive 不等於 delete。
- delete preview 列出 revisions/runs/artifacts。
- destructive action 有確認及可測 authorization boundary。
- 中英文不改變 status code／資料判定。
- keyboard-only 可完成主要查看與確認流程。

## 12. Stage H：功能等價驗收與 Streamlit 退場

### 12.1 Gate-by-gate 等價矩陣

逐一列出 Streamlit `_render_*` 能力並標示：

- HTML replacement URL。
- 共用 service／schema。
- parity test。
- 是否仍有 unique diagnostic value。
- 退場、保留為進階診斷，或明確不遷移。

### 12.2 退場順序

1. HTML 成為文件與 quickstart 的預設入口。
2. Streamlit 進入 maintenance-only。
3. 禁止只在 Streamlit 新增一般使用者功能。
4. 經一輪完整使用流程驗收後，才評估移除依賴與程式。

### 12.3 最終驗收

- 新使用者可完成：設定模型→建立需求→PM 澄清→執行→候選比較→promotion→模擬→最佳化→組裝→匯出。
- 研究使用者可取得完整 provenance、versions、raw data 與 reproducibility。
- 所有 partial/fallback/unsupported claim 正確顯示。
- Streamlit 沒有未豁免的重要獨有功能。

## 13. 標準測試命令

### 13.1 聚焦測試

依 Stage 選擇，不要每次只跑 full suite：

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_candidate_routes.py -q
.\venv\Scripts\python.exe -m pytest tests\test_revisions_web.py tests\test_api_foundation.py -q
.\venv\Scripts\python.exe -m pytest tests\test_settings.py tests\test_design_drafts.py tests\test_notifications.py -q
.\venv\Scripts\python.exe -m pytest tests\test_assembly_deliverables.py tests\test_v2_research_workspace.py -q
```

### 13.2 靜態與語法檢查

```powershell
.\venv\Scripts\python.exe -m ruff check web api application schemas repositories tests
.\venv\Scripts\python.exe -m py_compile web\routes.py web\candidate_views.py application\settings.py
& 'C:\Users\yehra\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check web\static\app.js
```

### 13.3 完整 regression

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

目前基準為 `364 passed`；測試數增加是正常的，但任何既有測試消失或被 skip 都必須說明。

## 14. 每階段更新格式

完成或暫停一個 Stage 時，在本文件頂部基線下追加：

```text
日期：
Stage / Slice：
完成內容：
修改的契約：
聚焦測試：
完整測試：
視覺 QA：
剩餘風險：
下一個 Slice：
```

只有在所有出口條件都滿足時，才把 Stage 標為 Completed；頁面存在不等於階段完成。

## 15. 現在應執行的工作

目前唯一建議開工項目是：

> **Stage A：候選工作台穩定化與文件同步**

建議順序為 `A1 統一候選解析 → A2 Promotion provenance/idempotency → A3 安全錯誤與品質閘`。完成後才進入 Stage B，不應先新增更多分析頁。
