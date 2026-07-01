# Changelog

## 2026-06-27

- **Phase 3 Academic Standards and Interoperability**:
  - Optional SBOL 3.0 Semantic Validation: Added validation checks using the `sbol3` library if available, ensuring generated Turtle documents comply with standard semantic specifications.
  - Rich GenBank Feature Mapping: Expanded recognized feature types to map backbone, scar, linker, insulator, and operator domains to standard GenBank feature keys (such as `misc_feature` and `protein_bind`).
  - Codon Adaptation Index (CAI) & Rare Codon Metrics: Integrated host-specific CAI and rare codon calculation into sequence optimization reports as non-blocking informational logs.
  - Exporter Round-trip Validation: Added tests to ensure exported GenBank annotations correctly parse back to original draft specifications.
- **Phase 4b Scoring Reconstruction and Self-Healing**:
  - Reconstructed Biophysical Scorer: Integrated stochastic noise ($CV^2$), retroactivity load index ($R_{max}$), RBS hairpin blocking ($P_{blocked}$), and metabolic burden into a single unified biophysical scoring formula under the `research-v2-preview` profile.
  - Exposed diagnostic tags: `HIGH_RETROACTIVITY`, `RBS_HAIRPIN_DETECTED`, `NOISE_FLIP_RISK`.
  - Self-Healing Action Toolkit: Built programmatic functions to modify topologies (`adjust_copy_number`, `mutate_intergenic_sequence`, `insert_insulator`, `swap_part_by_affinity`, `append_degradation_tag`).
  - Reflexion Controller Integration: Integrated the Critic JSON recommendation output and Reflexion controller repair router to intercept failures and execute targeted self-healing operations automatically.
  - Corrected the `research-v2-preview` score normalization so perfect implemented inputs can reach `1.0` while noise, retroactivity, RBS blocking, and burden reduce the score monotonically.
  - Restricted self-healing to the Critic-evaluated best topology, added recommendation validation, and persisted applied/skipped repair provenance in `SearchNode.self_healing_history`.
- **Simulation and Workflow Reliability**:
  - Added strict stochastic input and operon validation with structured failure results.
  - Added explicit SSA truncation metadata and `SSA_STEP_LIMIT_REACHED` reporting when a run reaches its safety step limit.
  - Fixed Streamlit rendering for dataclass-backed tool warnings.
  - Added Ruff and `feature/**` push coverage to CI.
  - Synchronized README, AI-review guidance, quickstart entry points, model assumptions, limitations, and evaluation documentation with the implemented preview capabilities.
  - Classified `PROJECT_PROFILE.md` as a local-only ignored document.

## 2026-06-16

- Added Product Manager (PM) Agent to orchestrate user interactions and design specifications:
  - Dialogue Elicitation: Prompts users progressively, proposing default biological values based on reference knowledge (Chassis, Inputs, Outputs, Logic relation, copy number) to prevent downstream simulation errors.
  - One-click Consent Flow: Built Streamlit UI cards supporting "Accept Recommendation" and "Custom Modify" for easy, progressive configuration.
  - Human-in-the-Loop (HITL) Translation: Translates complex simulator/critic errors into Traditional Chinese plain language, offering three trade-off option buttons that automatically append constraints and restart the Reflexion workflow.
  - Visual Mermaid Preview: Deterministically generates a high-level circuit flowchart (graph LR) and renders it dynamically inside the PM chat container.
  - Session Reset & Truncation: Auto-resets PM state on sidebar user intent change and truncates dialogue history over 12 messages to manage context size and prevent LLM hallucinations.
- Optimized the metabolic burden scorer by implementing dynamic ideal gate limits:
  - Automatically parses the number of inputs ($N$) from the candidate's truth table or logic matrix.
  - Dynamically calculates the limit as $\max(3, 2N + 1)$ instead of a static value of 3, preventing false rejections of complex logic.
- Integrated semantic faithfulness score into `RESEARCH_PROFILE` (`research-v1.8`) with a weight of `0.10` (adjusting `logic_function` and `evidence_quality` weights to maintain sum of 1.0).
- Bypassed Cello buildability rejections in Critic Agent when Cello is running in mock mode, preventing deadlock loops during dry-runs/local testing.
- Added a sequence quality analyzer (`tools/sequence_analyzer.py`) reporting IUPAC validity, CDS framing, restriction sites, Type IIS sites, homopolymers, repeats, annotations, and checksums.
- Added synonymous E. coli CDS codon optimization (`tools/sequence_optimization.py`) for translated protein sequence preservation.
- Added host-optimization candidate ranking (`tools/host_optimization.py`) supporting E. coli high-expression, low-burden, and balanced strategies.
- Added user-supplied experimental calibrations logging and summary reporting.
- Added v2 optimization workflow API endpoint (`POST /api/v2/designs/{design_id}/optimization-workflow`) integrating sequence analysis, CDS optimization revision, host-candidate ranking, and readiness reporting.
- Added E. coli host profile registry and E. coli readiness evaluation sub-scores for primers, sequence optimization, host optimization, and calibration.
- Added biological rationality optimizations (Phase 1 & Phase 2):
  - Gibson/Seamless assembly overlap $T_m$ calculation using Biopython and planning warnings for Tm out of range.
  - Golden Gate assembly re-cutting check validating circular product sequence does not contain active Type IIS sites.
  - Sliding-window internal Shine-Dalgarno (SD) motif warning.
  - Active C-terminal degradation tag detection (LVA/LAV/ASV) and signal-specific degradation rate scaling in ODE simulation.
  - Cello UCF (User Constraint File) parser extracting characterized gate parameters ($y_{\text{min}}, y_{\text{max}}, K_d, n$) and dynamic mapping to signal-specific ODE Hill parameters.
  - Log-normal plasmid copy-number perturbation preserving arithmetic mean during Monte Carlo robustness analysis.

## 2026-06-15

- Added a Biopython-backed DesignIR v2 plasmid assembler for real GenBank
  backbone records and explicit insertion windows.
- Added pydna circular-molecule validation and sequence checksums.
- Added reverse-complement part orientation, backbone feature remapping,
  restriction-site reporting, and machine-readable assembly reports.
- Added `POST /api/v2/designs/{design_id}/plasmid-assemblies`.
- Added an immutable, versioned backbone registry with trusted-source,
  checksum, host, origin, marker, copy-number, insertion-region, and
  essential-region metadata.
- Assembly now requires a registered backbone version and blocks illegal
  insertion windows, essential-region disruption, and insufficient part
  evidence.
- Added assembly readiness progression from conceptual design to
  `assembly_check_passed`.
- The new path does not yet design Gibson overlaps, primers, restriction
  fragments, or codon-optimized coding sequences.
- Added a shared sequence-level assembly-plan model for fragments, junctions,
  scars, restriction digests, blockers, and tool provenance.
- Added complete Biopython restriction-site and digest-fragment analysis for
  linear inserts and circular backbone/product molecules.
- Added Gibson fragment planning, overlap uniqueness checks, and pydna
  circular-product validation.
- Added Golden Gate planning for BsaI/BsmBI with internal Type IIS site
  blocking, overhang directionality checks, fusion-scar reporting, and pydna
  digestion/ligation validation.
- Added restriction-cloning enzyme-pair selection and
  `POST /api/v2/designs/{design_id}/assembly-plans`.
- Added `readiness-evaluator@1.0.0` with separate logic, dynamics, part
  evidence, sequence quality, assembly-plan, and experimental-readiness
  domains.
- Added stage-aware readiness states and hard blocker handling. Blockers can
  no longer be hidden by a high computational score.
- Preserved `weighted_total_score` and all existing scoring profile versions;
  `computational_design_score` is an explicit compatibility alias.
- Future-stage scores remain null until primer, sequence-optimization, or
  host-optimization evidence is available.

## 2026-06-14 - v2.0 Biological Realism Upgrades

- Upgraded the resource-aware ODE simulator to model protein maturation and folding delay via a three-state system ($mRNA_i$, $P_{\text{immature}, i}$, and $P_{\text{mature}, i}$).
- Coupled dilution from host cellular growth dynamically to available ribosomes ($\mu(t) = \mu_{\text{max}} \cdot R_{\text{free}}/R_{\text{total}}$), introducing negative feedback on circuit protein accumulation.
- Integrated plasmid copy number scaling to modulate promoter transcription rates and transcriptional resources demand statically.
- Configured chassis-specific biokinetic defaults for *Escherichia coli* and *Saccharomyces cerevisiae* (yeast) to automatically adapt simulation to the selected host.
- Enhanced `BuilderProposal` schemas, prompts, and `CelloWrapper` mapping paths to support and propagate optional `copy_number` and `chassis` specifications.
- Added extensive test coverage for delay-induced oscillation, maturation decay, copy-number scaling, and host-specific behavior under regression controls.

## 2026-06-14 - v1.8 Research Evaluation

- Added versioned scoring profiles with stable configuration hashes.
- Added an evidence-aware multidimensional research profile covering logic,
  dynamics, robustness, burden, buildability, evidence, and completeness.
- Preserved the legacy weighted score for existing workflow compatibility.
- Added versioned benchmark dataset manifests with content hashes,
  provenance, expected outcomes, and positive/negative cases.
- Added reproducible benchmark execution, expectation checks, persisted run
  history, and cross-run ranking.
- Added JSON, CSV, and Markdown benchmark reports with explicit research claim
  boundaries.
- Added evaluation profile, dataset, benchmark run, and comparison API
  endpoints plus a server-rendered Benchmark workspace.

## 2026-06-14 - v1.6 Data Foundation

- Added DesignIR v2 with separated specification, biological context,
  constructs, plasmids, field provenance, and explicit assumptions.
- Added validated v1-to-v2 payload migration and a v2-to-v1 compatibility
  projection for existing API, UI, comparison, and export consumers.
- Replaced confirmed-design JSON persistence with a transactional SQLite
  repository while retaining JSON import/export and draft storage.
- Added database schema initialization, content hashes, immutable design
  revisions, migration audit records, and legacy JSON ingestion.
- Added a dry-run capable batch migration command.
- Added reproducible run manifests with redacted requests, model/workflow
  metadata, result hashes, and artifact SHA-256 digests.
- Added read-only DesignIR v2 and revision-history endpoints.

## 2026-06-14 - v1.5 Web Application Foundation

- Added persistent background workflow runs to the shared application service.
- Added run create/list/status/events/result/artifacts/cancel/feedback/resume
  endpoints under `/api/v1`.
- Added validated run identifiers before filesystem-backed run-store access.
- Added a server-rendered Jinja2 interface with Dashboard, New Design, Runs,
  External Imports, Design Library, Design Detail, and Compare pages.
- Added low-density run progress and event views with local polling.
- Kept Streamlit available as the detailed research interface.
- API and HTML forms do not accept provider API keys; server environment
  variables remain the credential boundary.

## 2026-06-14 - v1.25 API Foundation

- Added shared application services for imports, designs, comparisons,
  benchmark evaluation, and exports.
- Added atomic local JSON repositories with validated record IDs.
- Added versioned FastAPI endpoints under `/api/v1` and OpenAPI documentation.
- Added persistent external-design drafts and confirmed `DesignIR` records.
- Updated the Streamlit external-import workflow to use the same application
  services as the API without changing the page layout.
- Added API contract, persistence, path traversal, comparison, evaluation, and
  export tests.
- Long-running LLM workflows remain outside the synchronous API until a
  persistent background-run contract is implemented.

## 2026-06-13

- Added external-design import v1 with guided literature entry, JSON draft
  upload/download, and basic GenBank feature parsing.
- Added field-level evidence records, import completeness, evidence quality,
  validation warnings, and applicable evaluation sections.
- Added review-before-import conversion from `ImportDraft` to `DesignIR`.
- Added comparison between confirmed external designs and workflow-generated
  candidates through the existing `DesignDiff` model.
- GenBank import preserves reported sequence annotations but does not infer
  Boolean logic, inputs, outputs, or experimental validation.

## 2026-06-07

- Added persisted MCP run events, stage progress, cursor-based event queries, and progress summaries.
- Added human feedback submission and auditable parent-to-child run resume.
- Added MCP DesignIR materialization, compatible-part discovery, replacement validation,
  immutable part replacement, revision diff, and BOM/GenBank/SBOL3 export tools.
- Hardened concurrent run metadata writes with re-entrant locking and unique atomic temp files.
# 變更紀錄

## 2026-06-16

- 新增序列品質分析器（`tools/sequence_analyzer.py`），可報告 IUPAC 有效性、CDS 框架、限制酶切位點、Type IIS 位點、同聚物、重複序列、註釋與校驗和。
- 新增針對大腸桿菌（E. coli）宿主的同義 CDS 密碼子優化（`tools/sequence_optimization.py`），並保留翻譯之蛋白質序列。
- 新增宿主優化候選方案排序（`tools/host_optimization.py`），支援高表達、低負載與平衡等策略。
- 新增使用者提供之實驗校準數據記錄與摘要報告。
- 新增 v2 優化工作流 API 進入點（`POST /api/v2/designs/{design_id}/optimization-workflow`），整合序列分析、CDS 優化版本、宿主候選排序與整備度報告。
- 新增大腸桿菌宿主設定檔註冊，以及針對引物、序列優化、宿主優化與實驗校準的整備度評估子分數。
- 新增生物學合理性與物理真實性優化功能（第一與第二階段）：
  - 使用 Biopython 計算 Gibson/Seamless 組裝 overlap 的熔解溫度 $T_m$，並在 $T_m$ 超出範圍時提供設計警告。
  - 實作 Golden Gate 組裝產物限制酶位點再切除（Re-cutting）檢查，確保最終產物不包含未被切割的 Type IIS 位點。
  - 新增內部 Shine-Dalgarno (SD) 樣基序之滑動窗口掃描與警告。
  - 偵測 CDS C端的活性降解標籤（LVA/LAV/ASV），並在 ODE 模擬中動態調整該訊號蛋白質的降解速率。
  - 支援解析 Cello UCF (User Constraint File) 門控實驗表徵參數（$y_{\text{min}}, y_{\text{max}}, K_d, n$），並動態映射至 ODE 模擬器之特定訊號 Hill 參數。
  - 針對 Monte Carlo 魯棒性評估，實作質體拷貝數（copy_number）的對數常態（Log-normal）隨機微擾，保留算術平均值之一致性。

## 2026-06-14 - v2.0 生物學合理性升級

- 升級資源感知 ODE 模擬器，以三狀態系統 ($mRNA_i$、未成熟蛋白質 $P_{\text{immature}, i}$ 與成熟蛋白質 $P_{\text{mature}, i}$) 來建模蛋白質成熟和折疊延遲。
- 將宿主細胞生長產生的稀釋率動態耦合至游離核糖體比例 ($\mu(t) = \mu_{\text{max}} \cdot R_{\text{free}}/R_{\text{total}}$)，為電路蛋白質積累引入負反饋。
- 整合質體複製數縮放，以靜態方式調節質體所攜帶之啟動子資源需求與轉錄速率。
- 為大腸桿菌 (*Escherichia coli*) 與釀酒酵母 (*Saccharomyces cerevisiae*) 配置宿主特異性生物動力學預設值，自動根據所選宿主調整模擬。
- 增強 `BuilderProposal` schema、提示詞與 `CelloWrapper` 映射路徑，以支援並傳遞可選的 `copy_number` 與 `chassis` 規格。
- 針對延遲誘導震盪、成熟衰變、複製數縮放以及宿主特異性行為新增廣泛的測試覆蓋，並置於回歸控制下。

## 2026-06-06 - Design Representation and Exchange Formats
## 2026-06-06 - 設計表示與交換格式

### Added / 新增

- Added `DesignIR` for biological parts, regulatory interactions, transcriptional units, validation status, provenance, part assignments, and immutable revisions.
- 新增 `DesignIR`，表示生物元件、調控關係、transcriptional units、驗證狀態、來源、元件映射與不可變版本。

- Added Logic, Regulatory, DNA Construct, Parts, Compare, and Export views to the Streamlit interface.
- 在 Streamlit 介面加入 Logic、Regulatory、DNA Construct、Parts、Compare 與 Export 視圖。

- External Cello execution now preserves input Verilog, output files, stdout/stderr, and an artifact manifest with SHA-256 hashes. Successful, failed, and timed-out runs are retained.
- 外部 Cello 執行現在會保存輸入 Verilog、輸出檔案、stdout/stderr，以及含 SHA-256 的 artifact manifest；成功、失敗與逾時執行都會被保留。

- Added a parser for supported Cello v2 JSON circuit and assignment artifacts.
- 新增支援 Cello v2 JSON circuit 與 assignment artifacts 的解析器。

- Added fixed demonstration library `demo-cello-library@1.0.0`.
- 新增固定版本示範元件庫 `demo-cello-library@1.0.0`。

- Added part replacement validation for type, host, gate role, sequence availability, and evidence level.
- 新增元件替換驗證，涵蓋類型、宿主、gate role、序列可用性與證據等級。

- Added immutable part replacement. Replacement creates a new `DesignRevision` without mutating the original design.
- 新增不可變元件替換；替換會建立新的 `DesignRevision`，不修改原始設計。

- Added `DesignDiff` for part, construct, maturity, and metric comparison.
- 新增 `DesignDiff`，比較元件、construct、成熟度與評分指標。

- Added BOM CSV, GenBank, and SBOL3 Turtle exporters.
- 新增 BOM CSV、GenBank 與 SBOL3 Turtle 匯出器。

### Export Rules / 匯出規則

- BOM may describe incomplete or conceptual designs.
- BOM 可以描述不完整或概念性設計。

- GenBank export is blocked when construct sequences are missing or contain non-IUPAC DNA characters.
- construct 序列缺失或含非 IUPAC DNA 字元時，GenBank 匯出會被阻擋。

- SBOL3 can represent sequence-less conceptual Components, but warnings are emitted and sequences are never invented.
- SBOL3 可表示沒有序列的概念性 Component，但會發出警告，且不會自行補入序列。

- Demonstration-library sequences are marked `illustrative` and the library evidence level is `demo_only`.
- 示範元件庫序列標示為 `illustrative`，元件庫證據等級為 `demo_only`。

- Export availability does not establish plasmid completeness, assembly readiness, biosafety, or experimental validation.
- 可匯出不代表質體完整、可組裝、生物安全或已通過實驗驗證。

### Validation / 驗證

- Added focused tests for DesignIR, Cello artifact persistence and parsing, part libraries, immutable replacement, DesignDiff, BOM, GenBank, and SBOL3.
- 新增 DesignIR、Cello artifact 保存與解析、元件庫、不可變替換、DesignDiff、BOM、GenBank 與 SBOL3 的測試。
# v2.0.0

- Added `/api/v2` research-run, result, artifact, cancellation, and comparison
  endpoints.
- Added asynchronous simulation plus multidimensional evaluation using the
  persistent `RunStore`.
- Added JSON, CSV, Markdown, and run-manifest research outputs.
- Added a paginated Jinja research workspace and expanded DesignIR v2 detail
  views for constructs, plasmids, evidence, assumptions, and simulation.
- Added version-aware research comparison.
- Added optional PostgreSQL DesignIR and revision repository support through
  `GENETIC_CIRCUIT_DATABASE_URL`; SQLite remains the default.
