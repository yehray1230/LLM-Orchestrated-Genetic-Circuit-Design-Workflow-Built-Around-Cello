# Project Limitations
# 專案限制

This document states what the current project can and cannot claim. It is meant to reduce ambiguity when presenting the work to synthetic biologists, supervisors, collaborators, or potential research contacts.

本文件說明了目前專案可以與不可以做出的宣稱。其目的是在向合成生物學家、指導教授、合作夥伴或潛在的學術/產業聯繫對象展示工作成果時，減少模糊空間。

The short version is:

簡短版本為：

> This project generates and evaluates computational candidate designs for regulatory logic circuits. It does not yet produce complete, buildable, experimentally validated genetic circuits.
> 本專案生成並評估調節邏輯電路的計算候選設計。它目前尚無法產生完整、可構建且經過實驗驗證的基因電路。

## 1. What This Project Can Do
## 1. 本專案可以做的事情

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
- Surface failure modes such as logic mismatch, weak simulated robustness, excessive complexity, or likely Cello/part-assignment problems.
  顯現失敗模式，如邏輯不匹配、模擬的魯棒性微弱、過度複雜，或可能存在的 Cello/元件分配問題。
- Support optional external Cello execution when a real Cello command and compatible UCF/library are configured.
  在配置了真實的 Cello 指令與相容的 UCF/庫時，支援可選的外部 Cello 執行。

These capabilities are useful for research prototyping, workflow design, and early candidate triage.

這些能力對於研究原型開發、工作流設計以及早期候選方案篩選非常有用。

## 2. What This Project Cannot Yet Do
## 2. 本專案目前無法做的事情

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
- Account for all relevant biological mechanisms, such as host growth, copy number, burden-growth feedback, RNA folding, codon usage, protein maturation, and toxicity feedback.
  考量所有相關的生物學機制，例如宿主生長、複製數、負載-生長反饋、RNA 折疊、密碼子使用偏好、蛋白質成熟以及毒性反饋。

These limitations are expected for the current stage of the project. The system should be treated as a computational design-assistance prototype, not as an automated biological-design platform.

對於專案目前的階段，這些限制是符合預期的。該系統應被視為一個計算輔助設計的原型，而非自動化的生物設計平台。

## 3. Safe Claims
## 3. 安全的宣稱（合適的描述方式）

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

## 4. Claims to Avoid
## 4. 應避免的宣稱（誇大的描述方式）

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

> The project has validated a biological logic gate without construction and measurement.
> 該專案在沒有構建與測量的情況下驗證了生物邏輯閘。

## 5. Evidence Needed for Stronger Claims
## 5. 做出更強宣稱所需的證據

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

## 6. Relationship to Other Documents
## 6. 與其他文件的關係

- [README.md](README.md): high-level project overview and entry point.
  [README.md](README.md)：高階專案概述與進入點。
- [EVALUATION_METRICS.md](EVALUATION_METRICS.md): scoring formulas, fallback behavior, and interpretation of benchmark components.
  [EVALUATION_METRICS.md](EVALUATION_METRICS.md)：評分公式、回退行為以及基準組件的解讀。
- [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md): detailed assumptions behind the resource-aware ODE simulation model.
  [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)：資源感知 ODE 模擬模型背後的詳細假設。
- [ARCHITECTURE.md](ARCHITECTURE.md): current system architecture and agent responsibilities.
  [ARCHITECTURE.md](ARCHITECTURE.md)：當前系統架構與智能體職責。

## 7. Recommended One-Sentence Description
## 7. 推薦的一句話描述

For presentations, emails, or early research conversations, the safest concise description is:

對於簡報、電子郵件或早期研究對話，最安全且簡明的描述是：

> This is a multi-agent computational design-assistance prototype that translates natural-language regulatory logic intent into candidate genetic-circuit representations, then ranks and critiques those candidates using simplified simulation and heuristic evaluation.
> 這是一個多智能體計算輔助設計原型，可將自然語言調節邏輯意圖翻譯為候選基因電路表徵，然後使用簡化模擬和啟發式評估對這些候選方案進行排序與評論。
