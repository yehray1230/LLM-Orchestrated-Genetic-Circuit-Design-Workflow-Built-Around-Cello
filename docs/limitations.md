# Project Limitations/專案限制

This document states what the current project can and cannot claim. It is meant to reduce ambiguity when presenting the work to synthetic biologists, supervisors, collaborators, or potential research contacts.

本文件說明了目前專案可以與不可以做出的宣稱。其目的是在向合成生物學家、指導教授、合作夥伴或潛在的學術/產業聯繫對象展示工作成果時，減少模糊空間。

The short version is:

簡短版本為：

> This project generates and evaluates computational candidate designs for regulatory logic circuits. It does not yet produce complete, buildable, experimentally validated genetic circuits.
> 本專案生成並評估調節邏輯電路的計算候選設計。它目前尚無法產生完整、可構建且經過實驗驗證的基因電路。

## 1. What This Project Can Do/本專案可以做的事情

The current prototype can:

目前的原型可以：

- Convert a natural-language design intent into computational circuit-design candidates.
  將自然語言設計意圖轉化為計算電路設計的候選方案。
- Generate Boolean-logic proposals and Cello-compatible combinational Verilog.
  生成布林邏輯提案與和 Cello 相容的組合邏輯 Verilog。
- Run an iterative multi-agent Reflexion workflow for proposal, translation, evaluation, critique, and repair.
  運行包含提案、翻譯、評估、評論與修復的迭代多智能體 Reflexion 工作流。
- Use heuristic benchmark scores to compare candidates under the same implemented assumptions.
  在相同的實現假設下，使用啟發式基準分數來比較候選方案。
- Run a simplified resource-aware ODE simulation for early dynamic screening.
  運行簡化的資源感知 ODE 模擬以進行早期動態篩選。
- Estimate coarse signals such as dynamic margin, resource occupancy, robustness under perturbation, and gate-complexity burden.
  估算粗略的訊號，如動態邊際、資源佔用、微擾下的魯棒性以及邏輯閘複雜度造成的負載。
- Summarize selected ODE trajectory readouts, burden proxies, steady-state status, uncertainty metadata, coverage gaps, and suggested next checks when a stored trace is available.
  在保存的軌跡可用時，彙整選定的 ODE 軌跡讀數、負載代理指標、穩態狀態、不確定性後設資料、覆蓋缺口與建議的下一步檢查。
- Surface failure modes such as logic mismatch, weak simulated robustness, excessive complexity, or likely Cello/part-assignment problems.
  顯現失敗模式，如邏輯不匹配、模擬的魯棒性微弱、過度複雜，或可能存在的 Cello/元件分配問題。
- Support optional external Cello execution when a real Cello command and compatible UCF/library are configured, while explicitly labeling mock, failed, and externally mapped Cello outputs.
  在配置了真實的 Cello 指令與相容的 UCF/庫時，支援可選的外部 Cello 執行，同時明確標示 mock、失敗與外部映射完成的 Cello 輸出。
- Analyze sequence-level features for quality control, reporting restriction sites, Type IIS sites, homopolymers, repeats, and IUPAC validation.
  分析序列層級的特徵以進行品質控制，報告限制酶切位點、Type IIS 位點、同聚物、重複序列以及進行 IUPAC 驗證。
- Generate synonymous CDS codon-optimized revisions for E. coli host profiles while preserving protein sequences.
  針對大腸桿菌（E. coli）宿主設定檔生成同義的 CDS 密碼子優化版本，同時保留蛋白質序列。
- Rank host-optimization candidate designs using predefined strategies (high_expression, low_burden, balanced).
  使用預定義的策略（高表達、低負載、平衡）對宿主優化候選設計進行排序。
- Summarize user-provided experimental calibration measurements.
  彙整使用者提供的實驗校準測量數據。
- Calculate Gibson/Seamless assembly overlap $T_m$ and check Golden Gate circular product re-cutting using Biopython and pydna.
  使用 Biopython 與 pydna 計算 Gibson/Seamless 組裝 overlap 的 $T_m$ 以及檢查 Golden Gate 圓形產物的再切除位點。
- Detect C-terminal active degradation tags (LVA/LAV/ASV) and couple them to ODE simulation degradation rates.
  偵測 C-terminal 的活性降解標籤（LVA/LAV/ASV）並將其與 ODE 模擬中的降解速率進行耦合。
- Parse characterized gate parameters ($y_{\text{min}}, y_{\text{max}}, K_d, n$) from Cello UCF and map them to ODE Hill kinetics.
  從 Cello UCF 解析表徵門控參數（$y_{\text{min}}, y_{\text{max}}, K_d, n$）並將其映射至 ODE 希爾動力學。
- Perform log-normal perturbation of plasmid copy numbers preserving arithmetic mean during Monte Carlo robustness analysis.
  在 Monte Carlo 魯棒性分析中對質體複製數進行保留算術平均數的對數常態微擾。
- Run bounded Gillespie stochastic audits with explicit completed/truncated run metadata; truncated runs are rejected as complete verification evidence.
  執行具有完成／截斷狀態的 Gillespie 隨機稽核；截斷結果不會被視為完整驗證證據。
- Screen simplified retroactivity, operon translational coupling/polarity, and heuristic RBS accessibility within the implemented simulation assumptions.
  在既有模擬假設下篩選簡化的 retroactivity、operon 轉譯耦合／極性與啟發式 RBS 可及性。
- Apply validated programmatic self-healing only to the Critic-evaluated best candidate while preserving repair provenance and the other candidate alternatives.
  僅對 Critic 評估的最佳候選執行經驗證的程式化 self-healing，並保留修復 provenance 與其他候選方案。

These capabilities are useful for research prototyping, workflow design, and early candidate triage.

這些能力對於研究原型開發、工作流設計以及早期候選方案篩選非常有用。

## 2. What This Project Cannot Yet Do/本專案目前無法做的事情

The current prototype cannot:

目前的原型無法：

- Design a complete plasmid from end to end.
  從頭到尾設計一個完整的質體。
- Specify all sequence-level details needed for construction.
  指定構建所需的所有序列級細節。
- Guarantee biological buildability.
  保證生物學上的可構建性。
- Guarantee that a generated design is a true experimentally validated genetic logic gate.
  保證生成的設計是真實經過實驗驗證的基因邏輯閘。
- Replace expert synthetic-biology review.
  取代合成生物學專家的審查。
- Replace real Cello configuration, UCF selection, or part-library validation.
  取代真實的 Cello 配置、UCF 選擇或元件庫驗證。
- Predict in vivo expression quantitatively.
  定量預測活體內（in vivo）表達。
- Prove host compatibility, biosafety, or regulatory compliance.
  證明宿主相容性、生物安全或法規符合性。
- Select experimentally characterized parts reliably unless appropriate data are provided.
  除非提供適當的數據，否則無法可靠地選擇經實驗表徵的元件。
- Account for all relevant biological mechanisms, such as detailed/dynamic host growth, dynamic copy-number variation, experimentally calibrated toxicity/noise, full thermodynamic RNA folding, and codon-pair bias. Note: the preview includes heuristic RBS-folding warnings, E. coli synonymous codon optimization, simplified copy-number scaling, first-order protein maturation delay, ribosome-coupled growth dilution, Cello UCF characterized Hill parameters, degradation tag rates, and log-normal copy-number perturbation.
  考量所有相關的生物學機制，例如詳細／動態宿主生長、動態複製數變異、經實驗校準的毒性／雜訊、完整熱力學 RNA 折疊與密碼子對偏好。註：目前僅包含啟發式 RBS 折疊警告及其他簡化模型，並非完整生物物理預測。
- Optimize promoter/RBS strength, RNA folding, codon-pair bias, chromosomal context, or real expression balance during codon optimization.
  在密碼子優化過程中優化啟動子/RBS 強度、RNA 折疊、密碼子對偏好、染色體環境或真實的表達平衡。
- Fit a dynamic host-cell model or automatically recalibrate the ODE simulator using experimental measurements.
  利用實驗測量值擬合動態宿主細胞模型，或自動重新校準 ODE 模擬器。
- Account for context-dependency of Cello-derived parameters. Hill equations parsed from Cello UCFs are characterized in specific biological contexts (host, media, plasmid backbone). Directly mapping them to a general ODE model assumes context-independence, which is a major simplification.
  考慮從 Cello 衍生的元件參數之「上下文相依性（Context-Dependency）」。從 Cello UCF 解析出的希爾（Hill）方程式參數是在特定的生物上下文（如特定宿主、培養基、質體骨架）中測量得到的。直接將其映射至一般的 ODE 模擬器，是建立在「元件完全獨立」的簡化假設之上。
- Replace rigorous RNA secondary structure thermodynamic modeling. The RBS folding accessibility warning is a heuristic proxy based on sequence windows, not a substitute for complete thermodynamic folding packages like NUPACK or MFE calculations.
  取代嚴格的 RNA 二級結構熱力學建模。系統提供的 RBS 折疊可及性警告僅為基於序列窗口的啟發式指標，無法替代 NUPACK 或 MFE 計算等完整的熱力學折疊軟體。
- Replicate full Chemical Master Equation stochastic regimes. While bounded Gillespie stochastic audits are provided, they only detect extreme stochastic extinction or instability under low-molecule limits; they do not solve the full Chemical Master Equation (CME) or capture cell-to-cell heterogeneity comprehensively.
  複製完整的化學主方程式隨機動力學。雖然系統提供有限步數的 Gillespie 隨機稽核，但它僅用於檢測低分子量極限下的隨機絕滅或不穩定性，無法替代對化學主方程（CME）的完整求解，亦無法全面捕捉細胞間的異質性。
- Model dynamic host metabolic interactions. The metabolic burden calculation is a coarse aggregate proxy representing relative synthetic species concentration, rather than a dynamic coupling to endogenous host pathways, amino acid/tRNA pools, or cell growth feedback.
  模擬動態宿主代謝交互作用。系統的代謝負載計算僅為基於合成物種濃度的粗粒度代指標（Burden Proxy），而非動態耦合宿主內源代謝途徑、氨基酸/tRNA 庫或細胞生長反饋的精確模型。

These limitations are expected for the current stage of the project. The system should be treated as a computational design-assistance prototype, not as an automated biological-design platform.

對於專案目前的階段，這些限制是符合預期的。該系統應被視為一個計算輔助設計的原型，而非自動化的生物設計平台。

## 3. Safe Claims

These are appropriate ways to describe the project:

以下是描述該專案的合適方式：

> The system generates and evaluates computational candidate designs for regulatory logic circuits.
> 該系統生成並評估調節邏輯電路的計算候選設計。

> The workflow translates natural-language intent into Boolean logic, Cello-compatible Verilog, simulated dynamics, and heuristic benchmark scores.
> 該工作流將自然語言意圖翻譯為布林邏輯、與 Cello 相容的 Verilog、模擬的動力學以及啟發式基準分數。

> The benchmark ranks candidates under implemented computational checks and exposes failure modes for iterative repair.
> 基準測試在已實現的計算檢查下對候選方案進行排序，並顯現失敗模式以進行迭代修復。

> The ODE simulator provides simplified screening evidence, not calibrated in vivo prediction.
> ODE 模擬器提供簡化的篩選證據，而非校準過的活體內預測。

> External Cello mapping is only available when a real Cello command and compatible UCF/library are configured.
> 僅在配置了真實的 Cello 指令與相容的 UCF/庫時，外部 Cello 映射才可用。

> Mock Cello output may be used for workflow testing, but should be labeled as mock-only and not described as real part assignment.
> Mock Cello 輸出可用於工作流測試，但應標示為 mock-only，且不應描述為真實元件分配。

> The system evaluates sequence constraints and offers E. coli codon-optimization revisions for translated protein conservation.
> 該系統評估序列約束，並提供大腸桿菌密碼子優化版本以保留翻譯的蛋白質序列。

> The host-optimization ranking provides heuristic computational trade-offs, not calibrated biological guarantees.
> 宿主優化排序提供啟發式的計算權衡，而非生物學保證。

## 4. Claims to Avoid

These statements would overstate the current system:

以下陳述會誇大目前系統的能力：

> The system automatically designs complete plasmids.
> 系統會自動設計完整的質體。

> The generated circuit is guaranteed to be buildable.
> 生成的電路保證是可構建的。

> A high benchmark score proves that the circuit will function experimentally.
> 高基準分數證明該電路在實驗中將正常工作。

> Mock Cello output is equivalent to real Cello mapping.
> 模擬的 Cello 輸出等同於真實的 Cello 映射。

> The ODE simulation predicts real cellular expression quantitatively.
> ODE 模擬定量預測真實的細胞表達。

> ODE readouts such as peak output or time to peak are calibrated experimental measurements.
> ODE 讀數（例如最大輸出或達峰時間）是經校準的實驗量測。

> The project has validated a biological logic gate without construction and measurement.
> 該專案在沒有構建與測量的情況下驗證了生物邏輯閘。

> Synonymous codon optimization guarantees high expression, structural stability, or biological function.
> 同義密碼子優化能保證高表達、結構穩定性或生物學功能。

> Experimental calibration data automatically fits a validated dynamic host model.
> 實驗校準數據會自動擬合經過驗證的動態宿主模型。

## 5. Evidence Needed for Stronger Claims/做出更強宣稱所需的證據

Stronger biological claims would require additional evidence and implementation work, such as:

若要做出更強的生物學宣稱，將需要額外的證據與實現工作，例如：

- real Cello execution with appropriate UCF files and mapped biological parts;
  使用適當的 UCF 文件和映射的生物元件進行真實的 Cello 執行；
- sequence-level design of promoters, RBSs, coding regions, terminators, backbone, origin, marker, and cloning strategy;
  啟動子、RBS、編碼區、終止子、骨架、複製起點、標記與克隆策略的序列級設計；
- host-specific parameter calibration from literature or experiment;
  來自文獻或實驗的宿主特異性參數校準；
- explicit modeling of plasmid copy number, growth dilution, burden-growth coupling, and toxicity;
  對質體複製數、生長稀釋、負載-生長耦合以及毒性的明確建模；
- experimental measurement of ON/OFF ratios, response time, burden, growth effects, stability, and noise;
  對 ON/OFF 比率、響應時間、負載、生長效應、穩定性以及雜訊的實驗測量；
- comparison against known measured genetic circuits;
  與已知經測量的基因電路進行對比；
- validation of benchmark weights against empirical outcomes;
  根據經驗結果驗證基準權重；
- expert review for biosafety, host compatibility, and experimental feasibility.
  針對生物安全、宿主相容性與實驗可行性的專家審查。

## 6. Relationship to Other Documents/與其他文件的關係

- [README.md](../README.md): high-level project overview and entry point.
  [README.md](../README.md)：高階專案概述與進入點。
- [evaluation_metrics.md](evaluation_metrics.md): scoring formulas, fallback behavior, and interpretation of benchmark components.
  [evaluation_metrics.md](evaluation_metrics.md)：評分公式、回退行為以及基準組件的解讀。
- [model_assumptions.md](model_assumptions.md): detailed assumptions behind the resource-aware ODE simulation model.
  [model_assumptions.md](model_assumptions.md)：資源感知 ODE 模擬模型背後的詳細假設。
- [architecture.md](architecture.md): current system architecture and agent responsibilities.
  [architecture.md](architecture.md)：當前系統架構與智能體職責。

## 7. Recommended One-Sentence Description/推薦的一句話描述

For presentations, emails, or early research conversations, the safest concise description is:

對於簡報、電子郵件或早期研究對話，最安全且簡明的描述是：

> This is an LLM-orchestrated computational design-assistance workflow built around Cello that translates natural-language regulatory logic intent into candidate genetic-circuit representations, then ranks and critiques those candidates using simplified simulation and heuristic evaluation.
> 這是一個圍繞 Cello 構建且由 LLM 編排的計算輔助設計工作流，可將自然語言調節邏輯意圖翻譯為候選基因電路表徵，然後使用簡化模擬和啟發式評估對這些候選方案進行排序與評論。
# Current Design and Export Boundaries (2026-06-06)
# 目前設計與匯出邊界（2026-06-06）

The project now produces richer design artifacts, but the following distinctions remain mandatory:

專案目前可以產生更完整的設計 artifacts，但仍必須維持以下區分：

- A conceptual `DesignIR` part is not a characterized biological part.
- 概念性 `DesignIR` 元件不等同於經實驗表徵的生物元件。
- A parsed Cello assignment is evidence that a supported artifact associated a logic node with a part identifier; it is not independent experimental validation.
- 解析出的 Cello assignment 代表支援的 artifact 將 logic node 與 part identifier 關聯，不代表獨立實驗驗證。
- `demo-cello-library@1.0.0` is for demonstration and testing. Its sequences are illustrative.
- `demo-cello-library@1.0.0` 僅供展示與測試，其序列為 illustrative。
- Replacement validation checks target structural and type constraints. Detailed cloning junctions, restriction sites, and E. coli codon usage are checked in separate assembly planning and sequence analysis stages, but expression balance, toxicity, or biosafety are not biological guarantees.
- 元件替換驗證主要針對結構與類型限制。詳細的 cloning junctions、限制酶切位點與大腸桿菌密碼子使用偏好會在獨立的組裝計畫與序列分析階段進行檢查，但表現平衡、毒性或生物安全並非生物學上的保證。
- An immutable revision records a computational change history; it does not prove that the revision is better experimentally.
- 不可變版本記錄計算上的變更歷史，不證明新版本在實驗上更好。
- `DesignDiff` reports differences in available fields and scores. It is not an expert recommendation or causal analysis.
- `DesignDiff` 回報可用欄位與分數差異，不是專家建議或因果分析。
- BOM is an inventory artifact, not a purchase order, assembly protocol, or proof of availability.
- BOM 是清單 artifact，不是採購單、組裝 protocol 或可取得性證明。
- GenBank export represents the sequences currently stored in DesignIR. It does not add backbone, origin, marker, cloning scars, or missing host context.
- GenBank 匯出表示 DesignIR 目前保存的序列，不會補入 backbone、origin、marker、cloning scar 或缺失的宿主情境。
- SBOL3 export is a machine-readable representation. A syntactically structured SBOL document does not imply biological validity.
- SBOL3 匯出是機器可讀表示；具結構的 SBOL 文件不代表生物學有效。

Safe wording:

安全描述：

> The system can produce traceable computational design representations and standard exchange artifacts for review.
>
> 系統可以產生可追溯的計算設計表示與標準交換 artifacts，供後續審查。

Avoid:

應避免：

> The exported GenBank or SBOL file is an assembly-ready validated plasmid.
>
> 匯出的 GenBank 或 SBOL 檔案是可直接組裝且已驗證的質體。
