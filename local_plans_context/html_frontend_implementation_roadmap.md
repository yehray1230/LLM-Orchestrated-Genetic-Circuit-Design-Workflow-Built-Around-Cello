# HTML 前端實作差距與路線圖

> 文件狀態：Completed / 所有遷移與退場工作已完成  
> 建立日期：2026-07-03  
> 配套產品規格：[`html_frontend_design_spec.md`](html_frontend_design_spec.md)  
> 目前施工順序：[`html_frontend_active_execution_plan.md`](html_frontend_active_execution_plan.md)  
> 主要實作範圍：`web/`、必要的 `api/`／`application/`／repository 擴充，以及對應測試

## 1. 文件目的與使用方式

產品規格回答「完整 HTML 前端應該提供什麼」；本文件回答：

- 現有 Streamlit、HTML、API 與 service 已經具備什麼。
- 距離產品規格還缺少哪些 UI、資料契約與持久化能力。
- 哪些問題是前置依賴，不能等到畫面完成後才處理。
- 應按什麼順序施工，才能用最小風險逐步讓 HTML 成為主介面。
- 每個階段如何驗證，而不是只憑頁面看起來完成。

本文件保存現況、差距與歷史決策。每完成一個 Stage，應更新差距矩陣與剩餘風險；實際施工順序以 Active Plan 為準，不要修改產品規格來迎合暫時的技術限制。

### 狀態標記

- **完整**：已有 HTML 使用流程、後端能力與基本測試。
- **部分**：已有頁面或後端，但尚未形成完整使用流程。
- **僅 API／Service**：核心能力存在，HTML 尚未承接。
- **僅 Streamlit**：舊介面已有，但 HTML／持久化契約尚未承接。
- **缺少契約**：需要新增資料模型、service 或安全邊界。
- **待驗證**：名稱或入口存在，但仍需在該 Phase 開工前確認完整資料形狀。

### 目前進度（2026-07-05）

已完成的基礎切片與決策收尾：

- **已完成 Stage H（功能等價驗收與 Streamlit 退場）**：完成對照矩陣，逐一檢驗確認 33 個 Streamlit 渲染功能在 HTML 前端皆有等價頁面與路由，增加 `app.py` 維護警告橫幅，並將所有文件預設介面修改為 HTML 工作空間。
- **已完成 Phase 1 戰略決策收尾 (D-008 至 D-014)**：確定採用單機單使用者部署、全域單一 API 金鑰範圍、草稿本地永久保存不設過期、動態已讀 JSON 列表通知持久化、全域檢視模式搭配 URL 覆寫、背景併發任務上限為 2 限制以及英文為主中文為輔語系。
- 一般使用者首頁與唯讀 AI 服務狀態卡。
- BYOK／模型設定頁與連線測試。
- 四步驟建立設計精靈、設計草稿自動儲存與恢復。
- 通知列表、未讀數量與已讀操作。
- 設計 revision 時間軸、歷史快照與 revision diff。
- BYOK secret-storage 邊界：一般 `settings.json` 不再保存 API key；Windows 使用目前使用者範圍的 DPAPI 加密持久化，未配置安全持久化後端的平台只保留程序內秘密。
- 舊版明文 `settings.json` API key 的讀取時自動遷移與明文移除。
- API key 明確清除操作、遮蔽 readback 及對外連線錯誤訊息收斂。
- PM elicitation endpoints 與建立設計精靈整合。
- 候選列表、候選詳情、2–4 候選比較、自訂 ODE 模擬與 promotion 頁面。
- 全套 regression 基線為 `364 passed`；前端遷移聚焦測試為 `61 passed`。
- 目前候選工作台仍需統一 result shape、補 promotion provenance／idempotency、收斂 route exception，才能視為完成。

## 2. 本輪盤點範圍與證據

本輪以程式知識圖譜及實際 HTML template／JavaScript 字串盤點為基礎，涵蓋：

- `app.py`：Streamlit 主介面及 30 多個 `_render_*` 功能。
- `web/routes.py`：31 個 server-rendered Web route／handler。
- `web/templates/`：dashboard、design、run、research、benchmark、import、assembly 與 comparison 頁面。
- `web/static/app.js`：表單互動與 run monitor polling。
- `api/routes.py`：設計、版本、模擬、評估、benchmark、run、artifact 與 export API。
- `api/v2_routes.py`：序列、宿主最佳化、組裝、research 與 artifacts API。
- `application/services.py`、`application/research.py`：主要 application service。
- repositories 與 schemas：設計版本、匯入草稿與持久化能力。
- 相關 Web 測試：`tests/test_api_foundation.py`、`tests/test_assembly_deliverables.py`、`tests/test_v2_research_workspace.py`。

### 2.1 現有 HTML 頁面

目前已有：

- `/web` dashboard。
- `/web/designs` 及 design detail。
- `/web/new-design`、`/web/runs`、run detail、status polling、feedback、resume。
- `/web/imports`、guided/upload、review、confirm。
- `/web/benchmarks` 及 benchmark detail。
- `/web/research`、research run detail、research comparison。
- `/web/compare` 設計比較。
- `/web/assembly`、backbone registry、建立 deliverable、report、downloads、artifact download。

### 2.2 現有 Streamlit 獨有或較完整功能

`app.py` 仍承擔：

- BYOK、provider/model preset 與 Cello 控制。
- PM 需求澄清與人機迴圈。
- pipeline、狀態摘要、搜尋樹及決策時間軸。
- 候選解釋、評分拆解、Verilog、拓撲、設計 workspace。
- logic、regulatory、construct、parts、export。
- 候選比較。
- ODE、參數配適、敏感度、分岔／transfer function。
- topology charts 與 stochastic simulation。
- 原始資料與 layout/debug 檢查。

### 2.3 已存在但 HTML 尚未充分使用的後端能力

後端已有明確入口：

- 設計版本列表與 revision repository。
- simulation models、ODE simulation、snapshot comparison、parameter sweep、bifurcation。
- evaluation profiles 及 evaluations。
- benchmark datasets、runs、comparisons、parameter-fit snapshots。
- background runs、events、result、artifacts、cancel、feedback、resume。
- exports。
- tool capabilities。
- sequence analysis、sequence optimization revision。
- host profiles、host optimization、calibration 與 optimization workflow。
- assembly plans、deliverables 及 artifacts。
- research runs、result、comparison、cancel 與 artifact download。

這代表近期主策略應為「建立 HTML view model 與工作流程」，而非重寫這些核心服務。

## 3. 功能差距矩陣

| 能力 | Streamlit | 現有 HTML | 後端 | 判定 | 主要缺口 | 優先級 |
| --- | --- | --- | --- | --- | --- | --- |
| 首頁／快速開始 | 有整體工作台 | 已有一般入口、AI 狀態、通知與最近工作 | 可列 designs/runs | 接近完整 | 全站背景工作摘要與設計下一步仍需整合 | P0 |
| 建立設計 | sidebar＋PM elicitation | 已有四步驟精靈、PM elicitation、autosave/recovery | run/draft/settings service 已有 | 接近完整 | 執行前成本／工具能力確認與完整 browser QA | P0 |
| BYOK／模型設定 | session state 中完整 | 已有設定頁、狀態與清除操作 | SettingsService＋secret-store 邊界 | 完整 | 已確立單使用者部署及全域 Credential 範圍 | P0 |
| Cello 設定與狀態 | 有控制與 claim notice | 無統一設定頁 | wrapper/capability 可用，需再確認契約 | 部分 | 設定 view、availability、fallback、claim boundary | P1 |
| 設計案總覽 | 分散於 inspector/workspace | design detail 有 logic、context、construct、provenance、readiness | design service 完整度高 | 部分 | 最佳候選、跨域 readiness、warning、下一步 | P0 |
| 設計版本 | 局部 revision/export | 已有 timeline、快照與 diff | revision API/repository 已有 | 部分 | 正式選定版本、版本來源與 artifact 關聯仍需補齊 | P1 |
| 候選詳情 | 相對完整 | 已有列表、單一詳情、評分、logic/regulatory/construct/parts | run result/design conversion 可用 | 接近完整 | 統一 result shape、來源 hash、錯誤安全與 parity | P1 |
| 候選比較 | 有完整互動比較 | 已有 2–4 候選多維比較與推薦 | candidate comparison view 已有 | 接近完整 | 相容性 contract、來源一致性與視覺 QA | P1 |
| 執行列表 | 有目前 session | 有 runs 頁 | run list/status 完整 | 部分 | 篩選、背景工作全站摘要、成本與待辦 | P1 |
| 執行監控 | pipeline/tree/HITL | 已有 polling、events、topology、ODE、search tree、feedback/resume | RunService/RunStore 已有 | 接近完整 | cancel UI、重試語意、保存成果、成本資訊 | P1 |
| 搜尋與決策歷程 | 完整 tree/path/timeline | 只在 run detail 顯示摘要 | run result/tree data 可用 | 部分 | 獨立頁、節點詳情、Critic/淘汰理由、人工紀錄 | P2 |
| ODE 模擬 | 完整互動 | 已有候選自訂 ODE 參數與結果專頁 | simulation API/service 已有 | 部分 | canonical candidate reference、background job、artifact 與安全錯誤 | P2 |
| SSA／隨機模擬 | 有 | 無專頁 | adapter／simulation 能力存在，契約待確認 | 僅 Streamlit／待驗證 | 正式 request/response、長任務處理、partial-run metadata | P2 |
| 參數配適 | 有 snapshot comparison | benchmark 有部分相關頁面 | fit snapshot API 已有 | 僅 API／Service | workflow、比較圖、來源與適用範圍 | P2 |
| 敏感度 sweep | 有 | 無 | `/simulations/sweep` 已有 | 僅 API／Service | 表單、圖表、限制說明 | P2 |
| 分岔／transfer function | 有 | 無 | `/simulations/bifurcation` 已有 | 僅 API／Service | 表單、圖表、解釋與 provenance | P2 |
| 評估／Benchmark | 有部分視圖 | 有列表、執行及 detail | API/service 完整度高 | 部分 | 版本可比性、報告、證據標籤、導覽重組 | P2 |
| Research workspace | Streamlit 非主要入口 | 已有 run/detail/compare | research service 已有 | 接近完整 | 一般／研究模式邊界、狀態一致性、通知 | P2 |
| 序列分析 | 有工具結果 | 無 Web workspace | v2 API/service 已有 | 僅 API／Service | 分析頁、finding 定位、建議與 claim boundary | P3 |
| 序列最佳化 | 有局部修訂能力 | 無 | revision API/service 已有 | 僅 API／Service | evaluate→review→create revision 流程 | P3 |
| 宿主與 calibration | sidebar 有 host | 無 workspace | v2 API/service 已有 | 僅 API／Service | profile、calibration、候選、來源與 readiness | P3 |
| 組裝 | 有 design export | HTML 已有 workspace/backbone/deliverable/report/download | v2 service 完整度高 | 接近完整 | 與設計案版本整合、錯誤復原、readiness 一致 | P3 |
| 匯入 | Streamlit sidebar 有 | guided/upload/review/confirm 已有 | ImportService/draft 已有 | 接近完整 | provenance 顯示、格式說明、修正與草稿管理 | P3 |
| 匯出 | Streamlit 有多格式下載 | assembly artifact 有；design export 無統一中心 | export API 已有 | 部分 | 設計匯出中心、警告、版本與 readiness | P3 |
| 通知／待辦 | session 內提示 | 首頁與全站未讀摘要已存在 | NotificationService 已存在 | 完整 | 確定採用動態狀態對照與輕量已讀 ID JSON 持久化 | P0/P1 |
| 自動儲存草稿 | session state | 新設計精靈已有 autosave/recovery | DesignDraftService 已存在 | 完整 | 確定為單使用者本地儲存，無併發與過期刪除限制 | P0 |
| 全域搜尋／收藏 | 無完整能力 | 無 | 未發現專用契約 | 缺少契約 | query、filter、pin/recent-view models | P4 |
| 資料封存／刪除 | 無完整 UI | 無 | 待驗證 repository semantics | 缺少契約／待驗證 | soft delete、impact preview、artifact cleanup | P4 |
| 多語系／可及性 | 混合中英文 | templates 混合中英文 | 不需核心後端 | 未建立 | i18n 字典、術語、keyboard/contrast/chart summary | P4 |

## 4. 關鍵實作問題

### 4.1 Streamlit session state 不能直接搬到 HTML

BYOK、PM 問答、選定節點、表單進度與 UI options 現在高度依賴 session state。HTML 需要把狀態分類：

- URL 可表達：design ID、revision ID、candidate ID、run ID、mode。
- session cookie 可表達：短期 UI 偏好與未登入使用者 session。
- repository 必須保存：草稿、版本、人工決策、通知、執行與 evidence。
- secret store 必須保存：API key；不得放入一般 design repository。

如果不先分類，後續頁面會各自發明狀態來源，導致重新整理遺失或頁面互相矛盾。

### 4.2 BYOK 是安全功能，不只是表單

需先決定：

- 是否有登入與 user identity。
- key 的作用範圍是 process、session、user 還是 project。
- 儲存加密、更新、測試與刪除方式。
- 後端如何只回傳 `configured/provider/model/last_tested` 等 metadata。
- logs、exception、debug payload、reports 如何避免洩漏秘密。
- 外部 provider 呼叫前如何提示會傳送的資料。

在這些問題未定案前，不應先做「記住 API key」的 UI。

### 4.3 新設計草稿與匯入草稿是不同概念

現有 `ImportDraft` 可保存外部匯入審查內容，但不能直接假設適合建立設計精靈。新 design draft 至少需要：

- owner/session scope。
- current step。
- natural-language intent 與 structured specification。
- host、constraints、budget、model selection metadata。
- optimistic concurrency/version token。
- last saved/expiry/status。

### 4.4 一般／進階模式必須共享同一 view model

不要建立兩套結果計算。推薦：route/service 產生完整且正規化的 view model；template 根據 mode 控制摘要與進階區塊。所有 evidence、warning、readiness 都必須源自同一份資料。

### 4.5 `web/routes.py` 不宜持續無限制膨脹

目前所有主要 HTML handler 與大量 monitor normalization 已集中在 `web/routes.py`。新增 simulation、optimization、settings、notifications 後，應按功能拆出 router/view-model modules，例如：

- `web/routes/designs.py`
- `web/routes/runs.py`
- `web/routes/simulations.py`
- `web/routes/optimization.py`
- `web/routes/settings.py`
- `web/view_models/`

拆分時保持 URL 與既有測試相容，不需要一次性重寫。

### 4.6 長任務與 polling 契約需要統一

目前 design run monitor 已有可重用模式；research 與其他分析不應各做一套互不相容的狀態格式。建議統一最小欄位：

- `id`, `kind`, `status`, `stage`, `progress`
- `created_at`, `updated_at`, `terminal`
- `events`, `result_summary`, `warnings`, `artifacts`
- `can_cancel`, `can_resume`, `can_retry`
- `next_poll_ms`

pause、cancel、resume、retry 必須使用精確語意。現況可見 cancel/resume 及 workflow human-input pause，但不能假設所有工作都支援真正 pause。

### 4.7 圖表策略需先標準化

短期建議沿用 server-rendered HTML＋小型 JavaScript／SVG：

- 小型 topology、sparkline、readiness：inline SVG。
- 大型互動搜尋樹、參數 sweep、分岔圖：選定一個輕量 library 或以 JSON＋專用 component 實作。
- 提供表格或文字摘要作為可及性 fallback。
- 避免每種分析引入不同圖表框架。

### 4.8 證據、警告與 readiness 需要正規化

不同服務已產生 warnings、provenance、readiness 或 claim notice，但 HTML 不應逐頁自行拼字串。需要共用 view model：

- severity/category/code/message。
- affected entity/location。
- source/tool/version。
- evidence level/confidence。
- fallback/partial/incomplete。
- recommended action。

### 4.9 版本、run、candidate 與 artifact 必須有明確關係

任何 export、simulation 或 assembly artifact 都應能追溯到：

`design → revision → candidate/topology → run/analysis → artifact`

否則使用者可能下載到舊版本或錯誤候選的成果。UI 必須顯示來源版本，後端也必須以 ID 驗證關聯。

### 4.10 相容性與退場不能靠一次切換

HTML 遷移期間應保留 Streamlit 作為對照與診斷入口。只有當某能力完成契約、HTML、測試與結果對照後，才能把該能力標記為已遷移。

## 5. 初始技術決策

| 編號 | 決策 | 原因 | 可逆性 |
| --- | --- | --- | --- |
| D-001 | 維持 FastAPI＋Jinja server-rendered 架構，局部使用 JavaScript | 現有基礎完整，無需為遷移先引入 SPA 複雜度 | 可逆；未來可逐頁 API 化 |
| D-002 | 先重用 application services/API，不在 template 重做科學邏輯 | 避免 Streamlit、HTML、API 結果漂移 | 高度應維持 |
| D-003 | 一般／進階模式使用同一 view model | 保持狀態、證據與計算一致 | 高度應維持 |
| D-004 | BYOK 完整設定放設定頁；首頁只放狀態與入口 | 保持可發現性但不增加主要流程負擔 | 可調整呈現位置 |
| D-005 | 新設計精靈使用專用 design draft，不重用 ImportDraft | 兩者生命週期與欄位不同 | 在 schema 定案前可逆 |
| D-006 | 沿用 run monitor normalization boundary | 已有實證且避免 Jinja 承擔資料抽取 | 可擴充 |
| D-007 | 先建立共用 status/warning/evidence 元件，再大量增加分析頁 | 避免每頁產生不同語言與判定 | 高度應維持 |

尚未決定的事項列於第 9 節，不應被視為已批准的技術選擇。

## 6. 歷史實作路線圖（已由 Active Plan 取代）

> 自 2026-07-04 起，本節保留作為歷史規劃與決策脈絡，不再代表目前施工順序。  
> 目前唯一有效的詳細執行計畫請使用 [`html_frontend_active_execution_plan.md`](html_frontend_active_execution_plan.md)。

### Phase 0：可執行基線與完整契約盤點

**目標**：把本輪高階矩陣提升成逐功能、逐資料欄位的施工清單。

工作：

- 建立 Streamlit render function → HTML page/component → API/service → test 的對照表。
- 讀取關鍵 request/response schemas，確認候選、simulation、optimization 與 evidence 的實際 shape。
- 為各功能建立狀態：ready-to-wire、needs-view-model、needs-contract、blocked-by-decision。
- 確認目前 HTML 啟動命令、測試命令及視覺 QA 方法。
- 凍結現有主要 Web route 行為作為 regression baseline。

完成判準：

- 所有產品規格頁面都有明確資料來源或缺口票據。
- 不再以「應該有 API」描述關鍵能力。
- 既有 Web 測試全綠，主要頁面可啟動檢視。

### Phase 1：P0 基礎契約

**目標**：先解決會影響所有後續頁面的狀態與安全問題。（已完成）

工作：

- [x] 決定部署身份模型與 BYOK scope。（決策 D-008、D-009）
- [x] 設計 credential metadata/service；秘密不進一般 payload。
- [x] 設計 design draft schema、repository 與 autosave API。（決策 D-010）
- [x] 設計共用 notification/task item schema 的最小版本。（決策 D-011）
- [x] 建立共用 status、warning、evidence、readiness view model。
- [x] 定義 general/advanced mode 的儲存與 URL 行為。（決策 D-012）

完成判準：

- [x] API key 可設定、測試、替換與刪除，readback 不含原值。
- [x] design draft 可建立、更新、恢復並處理過期／版本衝突。
- [x] 警告與 evidence 可由至少兩個不同 service 正規化呈現。

### Phase 2：一般使用者入口與建立設計

**目標**：讓新使用者從首頁走到成功啟動一個設計 run。

工作：

- 重構 dashboard 為一般使用者首頁。
- 加入 AI 服務狀態卡與設定入口。
- 建立「設定 → AI 與模型」頁。
- 將 new-design 單頁表單改為可恢復精靈。
- 整合 PM elicitation／structured specification review。
- 執行前顯示 host、budget、model、tools、成本提示與確認。
- 提供快速預覽／完整分析選項，但不宣稱不可靠的精確時間或價格。

完成判準：

- 全新 session 能從首頁完成模型確認、建立草稿並啟動 run。
- 重新整理或離開後能恢復草稿。
- 無模型、key 無效、Cello 不可用等狀態有清楚 fallback／阻擋原因。

### Phase 3：設計總覽、版本與候選工作台

**目標**：讓完成的 run 變成可理解、可比較、可追溯的設計資產。

工作：

- 擴充 design detail 成設計案總覽。
- 加入 revision timeline、來源版本與 diff 入口。
- 建立候選列表及候選 detail 專頁。
- 搬移 explanation、score breakdown、Verilog、topology、regulatory、construct、parts。
- 擴充 comparison page 支援多候選與相容性提示。
- 建立設計案次導覽。

完成判準：

- 使用者能指出目前選定 revision 與 candidate。
- 每個結論、simulation、export 均顯示來源版本。
- Streamlit 與 HTML 對同一保存結果的主要分數、拓撲與 warning 一致。

### Phase 4：執行監控、背景工作與錯誤復原

**目標**：讓使用者不必守在單一頁面，也能理解並恢復長任務。

工作：

- 保留並整理既有 run monitor。
- 補 cancel UI、精確 retry/resume 行為與已保存成果摘要。
- 建立全站背景工作 indicator。
- 建立通知／待辦最小中心。
- 把搜尋樹與決策歷程拆成專頁。
- 統一 design/research/analysis job 狀態呈現。

完成判準：

- 離開 monitor 後仍可從全站入口返回工作。
- success、failed、cancelled、human-input、partial/incomplete 都可區分。
- 錯誤畫面提供可行的下一步，不只顯示 exception。

### Phase 5：模擬與分析中心

**目標**：以 HTML 承接 Streamlit 的主要分析能力。

建議內部順序：

1. ODE simulation。
2. Parameter sweep／敏感度。
3. Snapshot／parameter-fit comparison。
4. Bifurcation／transfer function。
5. Stochastic／SSA。
6. 圖表摘要與下載。

工作：

- 每種分析建立獨立 route、template、view model 與 request validation。
- 統一參數來源、模型版本、host profile 與 fallback 顯示。
- 大型分析接入 background job，而非阻塞 request。
- 對 incomplete stochastic runs 保留明確 metadata。
- 提供表格／文字摘要及 artifact download。

完成判準：

- 每頁遵守「問題→參數→執行→結果→解釋→限制」。
- 同一 request 經 API 與 HTML 產生一致結果。
- 大型資料不直接塞入不可控的 HTML payload。

### Phase 6：序列、宿主與最佳化 (已完成)

**目標**：接通現有 v2 能力，形成 review-before-revision 流程。

工作：

- sequence analysis workspace。
- optimization suggestion review。
- sequence optimization revision 建立與 diff。
- host profile、calibration 與候選比較。
- optimization workflow 狀態與 readiness。

完成判準：

- 最佳化不會直接覆蓋既有 revision。
- 使用者能採用／拒絕建議並理解依據。
- calibration、heuristic、fallback 與 wet-lab evidence 明確分離。

### Phase 7：組裝、匯入、匯出與報告整合

**目標**：把已有但分散的交付能力接回設計版本主線。

工作：

- 組裝頁顯示 design/revision/candidate 來源。
- 匯入頁補 provenance、修正流程與 draft 管理。
- 建立統一 design export center。
- 加入可攜式專案包與可列印摘要。
- 對每個 artifact 顯示版本、警告及 readiness。
- 分享輸出移除秘密與內部路徑。

完成判準：

- 使用者不會誤下載其他版本的 artifact。
- 所有匯出失敗與 warning 可見。
- assembly-ready 與 computational preview 不會混淆。

### Phase 8：搜尋、資料治理、國際化與 Streamlit 退場

**目標**：完成長期使用能力，再評估主介面切換。

工作：

- 全域搜尋、篩選、收藏、最近瀏覽。
- archive、soft-delete、impact preview、artifact cleanup。
- 中英文術語與 i18n 結構。
- 鍵盤、對比、圖表文字摘要與窄螢幕 QA。
- 建立 Streamlit→HTML 功能等價清單。
- 將已完成能力的預設入口切到 HTML。
- Streamlit 先進入維護／診斷模式，最後才評估移除。

完成判準：

- 產品規格的完成 checklist 全部可驗證。
- 主要使用流程有瀏覽器級或端到端測試。
- 沒有只存在 Streamlit、又未被明確豁免的重要使用者功能。

## 7. 測試與驗證策略

### 7.1 每個 Phase 的最低測試

- service/schema unit tests。
- route 成功、validation、not-found、conflict、failed-state tests。
- template 中必要狀態與安全字串 assertions。
- JavaScript syntax check。
- 主要工作流程的 browser QA。
- 與 API／Streamlit 保存結果的 parity assertions。

### 7.2 高風險測試

- API key 不出現在 response、HTML、logs、debug 或 report。
- draft autosave concurrency 及過期恢復。
- run/candidate/revision/artifact 關聯不可交叉。
- cancel/resume/retry idempotency。
- partial/incomplete simulation 不被顯示成 success。
- evidence level 與 claim boundary 不被 template 簡化掉。
- destructive actions 的 CSRF、確認與 authorization（若引入身份系統）。

### 7.3 視覺 QA

每個新頁至少檢查：

- 1366px 寬的一般桌面。
- 約 768px 的窄版。
- 長 ID、長錯誤、無資料與大量 warning。
- loading、partial、failed、completed。
- 一般模式與進階模式。
- 中文與英文內容不破版。

## 8. 風險登錄

| 風險 | 可能影響 | 降低方式 |
| --- | --- | --- |
| 過早做完整 BYOK UI | key 洩漏或 scope 不清 | Phase 1 先定 credential boundary |
| 直接複製 Streamlit state | refresh 遺失、跨頁不一致 | 先分類 URL/session/repository/secret state |
| `web/routes.py` 持續膨脹 | 難測試、難維護 | 漸進拆 router 與 view model，不一次重寫 |
| 每頁自行解讀 result JSON | 顯示互相矛盾 | 正規化共用 view models |
| 假設所有 job 都能 pause | UI 承諾與後端不符 | capability flags＋精確操作語意 |
| 圖表 library 多頭發展 | bundle、風格及可及性失控 | Phase 5 前先做圖表技術決策 |
| 匯出未綁定 revision | 下載錯誤成果 | 強制 provenance chain 與 UI 顯示 |
| 把 fallback 當成功 | 科學 claim 過度 | 統一 partial/fallback/evidence metadata |
| 一次替換全部前端 | regression 範圍過大 | 分能力切換、保留 Streamlit 對照 |
| 只測 HTML 字串 | 互動流程仍可能失效 | 補 browser-level workflow tests |

## 9. 開工前待決策事項

以下決策會改變 Phase 1–2 架構，開始實作前需確認：

1. 部署是單機單使用者、共享伺服器，還是未來需要帳號系統？
2. 是否提供系統共用模型？若否，首次啟動必須強制 BYOK。
3. API key 可以只存在 process/session，還是需要跨重啟保存？
4. 一般／進階模式是全域偏好、每個 session，還是 URL 可分享狀態？
5. design draft 的保存期限與擁有者如何定義？
6. notification 是只根據 run 動態計算，還是需要 read/unread 持久化？
7. 是否允許同時啟動多個重量級 simulation／research jobs？
8. Streamlit 在遷移期間是正式備援介面，還是只供開發診斷？
9. 第一個正式支援的瀏覽器與部署方式為何？
10. 中英文哪一個是預設語言？既有混合介面何時統一？

建議第一個明確產品假設為：**先支援單機或可信任環境中的單一使用者，但 credential storage 仍保持可替換邊界，不把秘密混入 design data。** 若實際目標是共享部署，必須在 Phase 1 直接加入身份與 authorization，不能之後補救。

## 10. 下一個最小可執行切片

在開始大規模版面重構前，建議下一個切片是：

### 「HTML 首頁＋AI 狀態卡的唯讀垂直切片」

範圍：

- 建立共用 `AIServiceStatus` view model，僅回傳 availability、mode、provider、model、configured、message。
- 從現有環境／設定讀取狀態，不保存新 key。
- 在 dashboard 顯示綠／黃／紅狀態與設定入口 placeholder。
- 無可用模型時，建立設計入口顯示明確阻擋或設定提示。
- 加入 route/template tests，確認 key 或 secret 不會出現在 response。

此切片的價值：

- 可先驗證一般使用者首頁方向。
- 建立 BYOK 安全 view boundary，但不冒然設計 secret persistence。
- 為後續設定頁與建立設計精靈提供可重用狀態元件。
- 變更範圍小，容易視覺 QA 與回退。

完成此切片後，再進入 credential scope 與 design draft 的正式契約設計。

## 11. 維護規則

- 每完成一個功能，更新第 3 節狀態，不只更新 Phase checklist。
- 新增後端契約時記錄是否被 API、HTML、MCP 或 Streamlit 共用。
- 技術決策改變時，在第 5 節新增或 supersede 決策，不直接刪除歷史原因。
- 未驗證的能力保持「待驗證」，不要因 route 名稱存在就標為完整。
- 產品範圍改變時先更新產品規格，再同步本路線圖。
- 每個 Phase 結束時記錄測試命令、視覺 QA 範圍、剩餘風險與下一切片。
