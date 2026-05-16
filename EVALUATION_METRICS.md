# 基因電路科學驗證與評分系統 (Evaluation Metrics & Validation Framework)

本文件旨在闡述自動化基因電路設計代理 (Agentic Genetic Circuit Designer) 內部的科學評估與評分機制。本系統結合了非線性常微分方程 (Ordinary Differential Equations, ODEs) 以及多維度懲罰模型，確保 AI 產出的設計不僅在「布林邏輯」上正確，更能承受宿主細胞內真實的生化擾動。

---

## 1. 驗證系統理念 (Validation Philosophy)

在合成生物學中，純邏輯層面的正確性（如 Verilog 組合邏輯）往往不足以保證活體細胞內的運作可行性。這是因為生物系統本質上是「類比信號 (Analog)」且充滿雜訊的。
啟動子可能發生「漏電 (Leakage)」，過度表現外源蛋白會產生「代謝毒性 (Metabolic Burden)」，而細胞內的資源競爭亦會導致訊號失真。因此，我們引入了嚴謹的動力學模擬與多維度評分矩陣，作為系統中 **Critic Agent** 決定是否退回重做的客觀依據。

---

## 2. 動力學模擬引擎 (ODE Simulation Engine)

系統內建的動力學模擬引擎 (`tools/ode_simulator.py`) 優先使用 Python 的 `scipy.integrate.solve_ivp`，依序嘗試 BDF 與 Radau 演算法以處理剛性方程式；若 SciPy 不可用或積分失敗，會退回內建 RK4 fallback。

### 2.1 核心生化機制建模
對於基因網路上每個節點的目標物質，我們建立一組耦合常微分方程，分別模擬其 mRNA 與蛋白質的動態：
*   **轉錄 (Transcription):** 以 Hill Function 模擬多重抑制劑 (Repressors) 與活化劑 (Activators) 的啟動子競爭佔用。結合漏電係數 (Leakage) 決定有效轉錄速率 (Effective Transcription Rate)。
*   **轉譯 (Translation):** 考慮 mRNA 濃度與核糖體結合效率 (RBS strength)。
*   **降解 (Degradation):** 模擬 mRNA 與蛋白質的自然降解半衰期。
*   **誘導劑交互作用 (Inducer Binding):** 利用獨立的 Hill Function 模擬外部環境訊號 (如 IPTG, aTc) 與感測器蛋白結合後導致的去活化 (Deactivation) 效應。

### 2.2 蒙地卡羅壓力測試 (Monte Carlo Testing)
單一決定性 (Deterministic) 的模擬不足以反映生物雜訊。`BatchODESimulator` 因此提供可設定的 Monte Carlo 壓力測試：當 `monte_carlo_samples > 1` 時，系統會針對轉錄率、轉譯率、結合常數 $K_d$、Hill coefficient、漏電係數與降解率引入高斯分佈噪音，預設噪音比例為 15%。Monte Carlo 會輸出 `monte_carlo_terminal_output_cv` 與 `monte_carlo_failure_rate`，並納入 kinetic score 懲罰。

---

## 3. 評分指標矩陣 (Scoring Metrics)

為了將高維度的模擬曲線壓縮為決策演算法可判讀的量化指標，我們在 `benchmark_suite/` 目錄下實作了三個核心評估模組。

### 3.1 功能正確性評分 (Functional Scorer)
對應模組：`functional_scorer.py`
專注於理想（無雜訊）條件下的邏輯辨識度。
*   **Fold Change (FC) Score**: 
    提取目標產物在所有 ON 狀態中的最小濃度 (`Min ON`)，除以在所有 OFF 狀態中的最大濃度 (`Max OFF`)。
    $Fold Change = \frac{Min\_ON}{Max\_OFF}$
    並透過自訂的 Hill Equation 映射為 0~100 分。
*   **邏輯吻合度 (Logic Compliance)**: 
    使用 Sigmoid 函數設立嚴格閾值 (`thresh_on`, `thresh_off`)，只要有任何一個狀態未跨越安全閾值，分數將遭遇指數級乘數懲罰。
*   **漏電與裕度 (Margin Score)**: 
    利用 $e^{-k \times Max\_OFF}$ 評估 OFF 狀態的乾淨度，強烈懲罰背景漏電現象。

### 3.2 動力學與物理限制評分 (Kinetic Scorer)
對應模組：`kinetic_scorer.py`
專注於分析蒙地卡羅壓力測試的多組數據，確保物理層面可被實現。
*   **穩健度保留係數 ($R_{Kinetic}$)**:
    衡量引入雜訊後的 Fold Change 衰減程度，並計算變異係數 (Coefficient of Variation, $CV = \sigma / \mu$)。高 CV 值將觸發指數遞減懲罰，保障系統的抗噪能力。
*   **代謝毒性評估 ($P_{Burden}$)**:
    追蹤模擬過程中「所有非目標蛋白質（如邏輯閘中間產物）」的濃度總和。當其最大值 (`max_burden`) 逼近細胞的軟限制 (`limit_soft`，例如 45,000 nM) 時，觸發 Sigmoid 函數式崩潰：
    $P_{Burden} = \frac{1}{1 + e^{k_{burden} (max\_burden - limit\_soft)}}$
    此分數過低往往代表元件疊加過度，是觸發 Critic Agent 將問題歸類為 `PART_ERROR` 的重要指標。
*   **時序效率 ($Score_{Temporal}$)**:
    計算訊號從輸入層傳遞到輸出層，跨越啟動閾值所需的「平均上升時間 (Rise Time)」。層級過深會導致巨大的時間延遲並被扣分。

### 3.3 靜態合理性評估 (Static Plausibility)
對應模組：`static_plausibility_evaluator.py`
*   執行拓樸學層面的分析。當演算法發現選用了重複的元件序列時，將施加同源重組 (Homologous Recombination) 懲罰。
*   同時針對過高的電路層級深度的網路進行預先折扣。

---

## 4. Benchmark Controller 的匯總機制

所有模組最終在 `benchmark_controller.py` 進行統一收斂與加權。

**最終實驗潛力分數 (Total Viability Score)** 在 `benchmark_suite/benchmark_controller.py` 採用**連乘懲罰機制**：
$$Total\_Score = Score_{Functional} \times C_{Plausibility} \times R_{Kinetic} \times P_{Burden} \times Score_{Temporal}$$

連乘機制的科學用意在於「木桶理論」：只要任何一項指標（如毒性過高導致 $P_{Burden} \to 0$，或漏電導致 $Score_{Functional} \to 0$）崩潰，總分將直接歸零，防止 AI 通過彌補其他指標來蒙混過關。

最終會將分數分為三級：
*   **Excellent (≥80)**: 准予輸出（PASS）。
*   **Pass (60~79)**: 勉強及格，通常伴隨潛在的漏電或毒性警告。
*   **Fail (<60)**: 直接退回。此時產生的詳細扣分報表（包含具體的 `metrics_cv`, `metrics_max_burden`、Monte Carlo failure rate 等）將回傳給 **Critic Agent** 作為除錯依據，以判斷應走 `LOGIC_ERROR`、`PART_ERROR` 或 `BOTH` 的修復路徑。
