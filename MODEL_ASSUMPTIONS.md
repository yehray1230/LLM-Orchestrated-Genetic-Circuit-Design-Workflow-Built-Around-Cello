# Model Assumptions/模型假設

This document explains the assumptions behind the current resource-aware ODE simulation model. It is intended to make the model's scope clear for synthetic biologists, reviewers, and future contributors.

本文件解釋了目前資源感知 ODE 模擬模型背後的假設。其目的是向合成生物學家、審查者與未來的貢獻者明確說明該模型的範圍。

The simulator is designed for early computational triage. It helps compare candidate regulatory-circuit topologies, detect obvious dynamic failures, and provide signals for the Reflexion loop. It is not intended to be a full host-cell model or a quantitative prediction of in vivo expression.

模擬器旨在進行早期的計算篩選。它有助於比較候選調節電路的拓撲結構、檢測明顯的動態失效，並為 Reflexion 迴圈提供訊號。它並非旨在作為一個完整的宿主細胞模型，或對活體內（in vivo）表達進行定量預測。

## 1. Modeling Purpose/建模目的

The model is used to answer limited design-screening questions:

該模型用於回答有限的設計篩選問題：

- Does a candidate produce a stable output under the implemented dynamics?
  在實現的動力學下，候選方案是否能產生穩定的輸出？
- Does the simulated output show a useful dynamic margin?
  模擬的輸出是否顯示出有用的動態邊際？
- Does the candidate appear sensitive to kinetic-parameter perturbations?
  該候選方案是否對動力學參數的微擾敏感？
- Does the candidate impose high coarse-grained RNAP/ribosome demand?
  該候選方案是否施加了高粗粒度的 RNAP/核糖體需求？
- Should the Critic route the candidate toward repair, rejection, or consolidation?
  Critic 應該將候選方案引導至修復、拒絕還是鞏固？

The model should not be used to claim that a candidate will work experimentally. It provides relative evidence for ranking candidates generated under similar assumptions.

該模型不應被用來宣稱候選方案在實驗上一定可行。它僅為在相似假設下生成的候選方案提供用於排序的相對證據。

## 2. System Boundary/系統邊界

The current model represents a regulatory-circuit topology at a coarse level. It includes:

當前的模型在粗粒度水平上表徵調節電路拓撲。它包括：

- mRNA dynamics for inferred genes or gates;
  推導出的基因或邏輯閘之 mRNA 動力學；
- protein dynamics for inferred genes or gates;
  推導出的基因或邏輯閘之蛋白質動力學；
- shared RNAP availability;
  共享的 RNAP 可用性；
- shared ribosome availability;
  共享的核糖體可用性；
- aggregate burden proxy from total mRNA and protein;
  來自總 mRNA 和蛋白質的聚合負載代理指標；
- optional Monte Carlo perturbation of selected kinetic parameters.
  對選定動力學參數進行可選的蒙特卡羅微擾。

It does not represent a complete plasmid or full cellular physiology. In particular, it does not specify or simulate plasmid backbone, origin of replication, selectable marker, full DNA sequence, assembly strategy, host growth, or host-wide metabolism.

它並不代表完整的質體或完整的細胞生理學。特別是，它不指定或模擬質體骨架、複製起點、篩選標記、完整 DNA 序列、組裝策略、宿主生長或宿主全局代謝。

The current ODE explanation layer reports what can be read from the stored trajectory, such as peak output, time to peak, final output, coarse burden proxies, resource occupancy, and whether the final segment appears near steady state. These are derived readouts from the existing trace, not additional biological mechanisms.

目前的 ODE 解釋層會回報可從已保存軌跡讀出的內容，例如最大輸出、達峰時間、最終輸出、粗略負載代理指標、資源佔用率，以及最後一段軌跡是否看似接近穩態。這些是從既有軌跡衍生出的讀數，而不是額外的生物學機制。

## 3. State Variables/狀態變數

For `n` inferred genes or gates, the ODE state is:

對於 `n` 個推導出的基因或邏輯閘，ODE 狀態為：

```text
y = [mRNA_1 ... mRNA_n, protein_1 ... protein_n]
```

The simulator also records resource-related values over time:

模擬器還會記錄隨時間變化的資源相關數值：

```text
rnap_free
ribosome_free
rnap_occupancy
ribosome_occupancy
burden_nM
```

`burden_nM` is a coarse aggregate:

`burden_nM` 是一個粗略的聚合值：

```text
burden_nM = sum(mRNA) + sum(protein)
```

This is a proxy used for screening, not a measured cellular burden model.

這是一個用於篩選的代理指標，而非經測量的細胞負載模型。

## 4. Gene Count and Topology Approximation/基因數量與拓撲近似

The simulator infers `gene_count` from the topology. If `gate_count` is available, it uses that value. Otherwise, it estimates count from Verilog primitives and `assign` statements.

模擬器從拓撲結構中推導 `gene_count`。如果 `gate_count` 可用，它將使用該值。否則，它將從 Verilog 原語（Primitives）與 `assign` 語句中估算數量。

This means the ODE model treats a logic-level topology as a simplified chain of expression units. It does not infer a complete biological implementation from sequence or part-level design.

這意味著 ODE 模型將邏輯層級的拓撲結構視為表達單位的簡化鏈。它不從序列或元件層級設計中推導出完整的生物學實現。

## 5. Regulatory Assumptions/調節假設

The current regulation model is Hill-like repression. The first species is treated as unregulated, and downstream species can be repressed by upstream protein levels:

目前的調節模型是類希爾（Hill-like）抑制。第一個物種被視為不受調節的，下游物種可被上游蛋白質水平所抑制：

```text
regulation[0] = 1.0
regulation[i] =
  leak + (1.0 - leak) / (1.0 + (protein[i - 1] / kd) ^ hill)
```

This is a coarse topology-level approximation. It does not model promoter-specific binding kinetics, multiple operator sites, activator mechanisms, cooperative binding variants, inducer dynamics, or detailed transcription-factor biophysics.

這是一個粗略的拓撲級近似。它不模擬啟動子特異性結合動力學、多個算子位點、激活物機制、協同結合變體、誘導物動力學或詳細的轉錄因子生物物理學。

## 6. Resource Assumptions/資源假設

The model treats RNAP and ribosomes as shared resource pools. Transcription depends on available RNAP, and translation depends on available ribosomes:

該模型將 RNAP 和核糖體視為共享資源池。轉錄取決於可用的 RNAP，而翻譯取決於可用的核糖體：

```text
rnap_factor = rnap_free / (km_rnap + rnap_free)
ribosome_factor = ribosome_free / (km_ribosome + ribosome_free)
```

The ODE dynamics are:

ODE 動力學為：

```text
d_mRNA_i/dt =
  transcription_rate * regulation_i * rnap_factor
  - mrna_degradation_rate * mRNA_i
```

```text
d_protein_i/dt =
  translation_rate * mRNA_i * ribosome_factor
  - protein_degradation_rate * protein_i
```

Resource occupancy is used as a warning signal for coarse burden:

資源佔用率被用作粗略負載的警告訊號：

```text
rnap_occupancy = 1.0 - rnap_free / rnap_total
ribosome_occupancy = 1.0 - ribosome_free / ribosome_total
```

This resource model is useful for detecting candidates that may demand too much transcriptional or translational capacity. It does not model full cell growth, energy metabolism, amino-acid availability, stress responses, or burden-growth feedback.

此資源模型有助於檢測可能需求過多轉錄或翻譯能力的候選方案。它不模擬完整的細胞生長、能量代謝、胺基酸可用性、應激反應或負載-生長反饋。

## 7. Parameter Assumptions/參數假設

Biokinetic parameters are attached by `DataMinerAgent`. If a vector retriever provides relevant local records, those can override defaults. Otherwise, the system uses conservative default parameters.

生物動力學參數由 `DataMinerAgent` 附加。如果向量檢索器提供了相關的本地記錄，這些記錄可以覆蓋預設值。否則，系統將使用保守的預設參數。

Current default parameters include:

目前的預設參數包括：

- `rnap_total`
- `ribosome_total`
- `km_rnap`
- `km_ribosome`
- `transcription_rate`
- `translation_rate`
- `mrna_degradation_rate`
- `protein_degradation_rate`
- `kd`
- `hill_coefficient`
- `leak_fraction`
- `burden_soft_limit`
- `toxicity_threshold`

The current unit system is:

目前的單位系統為：

```text
nM and seconds
nM 和秒
```

Default parameters are useful for keeping the workflow executable, but they limit biological interpretation. Parameter provenance matters: a simulation based on host-specific, literature-supported, or experimentally calibrated parameters should be considered stronger than one based only on defaults.

預設參數對於保持工作流的可執行性非常有用，但它們限制了生物學上的解讀。參數來源（Provenance）至關重要：基於宿主特異性、文獻支持或實驗校準參數的模擬，應被視為比僅基於預設參數的模擬更具說服力。

## 8. Numerical Integration Assumptions/數值積分假設

The simulator first tries SciPy stiff ODE solvers:

模擬器首先嘗試 SciPy 的剛性（Stiff）ODE 求解器：

1. `BDF`
2. `Radau`

If SciPy is unavailable or the solver path fails in the current environment, the implementation can fall back to an internal RK4-style integration path.

若 SciPy 不可用或求解器路徑在當前環境下失敗，該實作可以回退到內部的 RK4 風格積分路徑。

A successful integration means the model equations were solved numerically under the provided assumptions. It does not mean the candidate is experimentally buildable or biologically valid.

成功的積分代表模型方程在提供的假設下得到了數值解。它並不意味著候選方案在實驗上是可構建的，或在生物學上是有效的。

## 9. Noise and Monte Carlo Assumptions/雜訊與蒙特卡羅假設

Monte Carlo perturbation is used as a sensitivity screen. It perturbs selected kinetic parameters by sampling around their current values:

蒙特卡羅微擾被用作敏感性篩選。它通過在其當前值周圍進行抽樣來對選定的動力學參數進行微擾：

```text
sampled_value = max(0.0, normal(original_value, abs(original_value) * noise_level))
```

Perturbable parameters include:

可微擾的參數包括：

- `transcription_rate`
- `translation_rate`
- `kd`
- `hill_coefficient`
- `leak_fraction`
- `mrna_degradation_rate`
- `protein_degradation_rate`
- `y_min`
- `ymax`
- `y_max`

The noisy-response scorer compares terminal output against an early output window:

有雜訊響應評分器將終端輸出與早期輸出窗口進行對比：

```text
on_value = terminal output
off_value = max(output in early window)
```

It treats a candidate as collapsed if:

若滿足以下條件，它會將候選方案視為塌陷（Collapsed）：

```text
max(off_values) >= min(on_values)
```

This is a simple robustness heuristic. It is not a measured noise model and does not represent experimentally observed cell-to-cell variability.

這是一個簡單的魯棒性啟發式指標。它不是一個測量得出的雜訊模型，也不代表實驗觀察到的細胞間變異性。

## 10. Output Interpretation/輸出結果的解讀

Important output fields should be interpreted conservatively:

重要的輸出欄位應進行保守解讀：

| Output / 輸出欄位 | Interpretation / 解讀 |
| --- | --- |
| `ode_status = "simulated"` | Numerical simulation completed under the model assumptions. <br> 數值模擬在模型假設下完成。 |
| `kinetic_score` | Relative ODE-derived screening score. <br> 相對的 ODE 導出篩選分數。 |
| `robustness_score` | Sensitivity score under implemented perturbations. <br> 在實現的微擾下的敏感性分數。 |
| `dynamic_margin` | Approximate output separation proxy. <br> 近似的輸出分離代理指標。 |
| `signal_to_noise_ratio` | Simulation-derived output variation proxy. <br> 模擬導出的輸出變異代理指標。 |
| `resource_occupancy` | Coarse RNAP/ribosome burden signal. <br> 粗略的 RNAP/核糖體負載訊號。 |
| `metrics_max_burden` | Aggregate mRNA/protein burden proxy. <br> 聚合 mRNA/蛋白質負載代理指標。 |
| `parameter_provenance` | Evidence quality for the parameter values used. <br> 所用參數值的證據品質。 |
| `ode_explanation.key_readouts` | Derived trajectory readouts such as peak output, time to peak, final output, fold-change proxy, and steady-state status. <br> 衍生的軌跡讀數，例如最大輸出、達峰時間、最終輸出、fold-change 代理指標與穩態狀態。 |
| `ode_explanation.burden_readouts` | Coarse mRNA/protein and RNAP/ribosome burden readouts. <br> 粗略的 mRNA/蛋白質與 RNAP/核糖體負載讀數。 |
| `ode_explanation.coverage_warnings` | Warnings about missing explicit input scenarios, OFF-state traces, ON/OFF ratios, or Monte Carlo perturbation. <br> 關於缺少明確輸入情境、OFF-state 軌跡、ON/OFF 比率或蒙特卡羅微擾的警示。 |

These fields are most useful for comparing candidates generated in the same workflow. They should not be treated as standalone experimental predictions.

這些欄位最有用於比較在相同工作流中生成的候選方案。它們不應被視為獨立的實驗預測。

## 11. Mechanisms Not Currently Modeled/目前未建模的機制

The current model does not include:

當前的模型不包括：

- complete plasmid sequence or backbone architecture;
  完整的質體序列或骨架架構；
- origin of replication, selectable marker, copy-number dynamics, or assembly scars;
  複製起點、篩選標記、複製數動力學或組裝疤痕；
- promoter-, RBS-, terminator-, or coding-sequence-level design constraints;
  啟動子、RBS、終止子或編碼序列級別的設計約束；
- host growth, dilution by growth, cell-cycle effects, or global metabolic regulation;
  宿主生長、生長產生的稀釋、細胞週期效應或全局代謝調節；
- burden-growth coupling or stress-response feedback;
  負載-生長耦合或應激反應反饋；
- DNA supercoiling or local sequence context;
  DNA 超螺旋或本地序列上下文；
- RNA folding, RNA stability motifs, or transcript processing;
  RNA 折疊、RNA 穩定性基序或轉錄本處理；
- codon usage, translation initiation context, or ribosome traffic;
  密碼子使用偏好、翻譯起始上下文或核糖體交通（Ribosome traffic）；
- protein folding, maturation, degradation tags, or active/inactive maturation states;
  蛋白質折疊、成熟、降解標籤或活性/非活性成熟狀態；
- inducer transport, ligand binding, or environmental dynamics;
  誘導物轉運、配體結合或環境動力學；
- experimentally calibrated toxicity and noise distributions.
  經實驗校準的毒性與雜訊分布。

These omissions are intentional for the current prototype. The model is kept small enough to run inside an iterative search loop.

對於目前的原型，這些省略是刻意為之的。模型保持足夠小的規模，以便在迭代搜尋迴圈中運行。

## 12. Evidence Needed for Stronger Biological Claims/做出更強生物學宣稱所需的證據

To move from computational candidate ranking toward stronger biological claims, future versions should add:

為了從計算候選方案排序邁向更強的生物學宣稱，未來的版本應增加：

- real Cello execution with appropriate UCF files and mapped part assignments;
  使用適當的 UCF 文件和映射的元件分配進行真實的 Cello 執行；
- sequence-level checks for promoters, RBSs, coding regions, terminators, and cloning constraints;
  針對啟動子、RBS、編碼區、終止子與克隆約束的序列級檢查；
- host-specific parameter calibration from literature or experiments;
  來自文獻或實驗的宿主特異性參數校準；
- plasmid copy-number and growth-dilution dynamics;
  質體複製數與生長稀釋動力學；
- burden-growth feedback and toxicity calibration;
  負載-生長反饋與毒性校準；
- experimentally measured ON/OFF ratios, response times, noise, burden, and growth effects;
  經實驗測量的 ON/OFF 比率、響應時間、雜訊、負載與生長效應；
- comparison against known measured genetic circuits;
  與已知經測量的基因電路進行對比；
- validation of score weights against empirical outcomes.
  根據經驗結果驗證評分權重。

Until those steps are added, the appropriate claim is:

在增加這些步驟之前，合適的宣稱為：

> The model provides simplified screening evidence for computational candidate designs.
> 該模型為計算候選設計提供簡化的篩選證據。

It should not be described as:

它不應被描述為：

> A quantitative predictor of complete, buildable, experimentally validated genetic circuits.
> 完整、可構建且經過實驗驗證 of 基因電路的定量預測器。
# Relationship Between DesignIR and the ODE Model (2026-06-06)
# DesignIR 與 ODE 模型的關係（2026-06-06）

The new part, revision, comparison, and export layers do not expand the biological scope of the ODE model.

新增的元件、版本、比較與匯出層不會擴張 ODE 模型的生物學範圍。

- `DesignIR` provides a richer representation of candidate parts and constructs.
- `DesignIR` 提供較完整的候選元件與 construct 表示。
- Part replacement changes stored assignment and sequence metadata, but the current ODE simulator does not automatically derive calibrated kinetic parameters from those sequences.
- 元件替換會改變保存的 assignment 與 sequence metadata，但目前 ODE simulator 不會自動從序列推導經校準的動力學參數。
- `DesignDiff` can display score differences, but those scores remain based on the existing benchmark and simulation assumptions.
- `DesignDiff` 可以顯示分數差異，但這些分數仍基於既有 benchmark 與模擬假設。
- BOM, GenBank, and SBOL3 are representations of current data; they do not add biological mechanisms or improve parameter calibration.
- BOM、GenBank 與 SBOL3 是目前資料的表示，不會增加生物機制或改善參數校準。

Therefore, a sequence-backed export should not be interpreted as a sequence-aware ODE prediction. Stronger coupling would require part-specific response functions, promoter/RBS models, degradation parameters, copy-number context, and calibrated host data.

因此，具有序列的匯出不應解讀為 sequence-aware ODE 預測。更強的耦合需要元件特定 response function、promoter/RBS 模型、降解參數、copy-number 情境與經校準的宿主資料。
