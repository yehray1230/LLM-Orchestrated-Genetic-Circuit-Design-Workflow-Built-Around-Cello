# Evaluation Metrics

## Readiness evaluation boundary

The existing `weighted_total_score` remains unchanged for historical
benchmark compatibility. New responses also expose the identical value as
`computational_design_score` to make its scope explicit.

Assembly and experimental readiness are evaluated separately by
`readiness-evaluator@1.0.0`. It reports:

- `logic_score`
- `dynamic_score`
- `part_evidence_score`
- `sequence_quality_score`
- `assembly_plan_score`
- `experimental_readiness_score`

Unavailable domains are `null`, not zero. Hard blockers are not converted
into score penalties. Any essential-feature disruption, checksum mismatch,
missing sequence, insufficient part evidence, internal Type IIS site,
non-unique Gibson overlap, or invalid Golden Gate overhang forces
`readiness_status = "blocked"` regardless of computational score.

The readiness stages are:

```text
conceptual
sequence_complete
assembly_planned
primer_ready
sequence_optimized
host_optimized
expert_review_required
```

This readiness result is not calibrated experimental evidence and does not
replace expert review.

## v1.8 Versioned Research Evaluation

The API evaluation default is `research-v1.8@1.8.0`. Existing workflow code
continues to use `legacy-weighted@1.0.0` unless it explicitly selects another
profile.

```text
0.20 logic_function
0.15 dynamic_behavior
0.15 robustness
0.10 resource_burden
0.15 buildability
0.15 evidence_quality
0.10 data_completeness
```

Each result includes `scoring_profile`, `scoring_version`, and
`scoring_configuration_hash`. Comparisons across versions carry a warning
because the scores are not assumed to be calibrated equivalents.

Benchmark dataset manifests are content-addressed and versioned. The bundled
`research_smoke_v1` dataset contains synthetic infrastructure fixtures, not
wet-lab validated circuits. JSON, CSV, and Markdown reports preserve dataset
and scoring hashes, case results, dimension summaries, and expectation checks.
# 評估指標

This document explains how the current benchmark system scores candidate genetic-circuit designs. The metrics are intended for computational triage: they rank and compare candidate designs inside the Reflexion loop so weak candidates can be repaired, rejected, or deprioritized.

本文件解釋了目前的基準（Benchmark）系統如何對候選基因電路設計進行評分。這些指標旨在用於計算篩選（Triage）：它們在 Reflexion 迴圈內對候選設計進行排序與比較，以便修復、拒絕較弱的候選方案，或降低其優先級。

These metrics do not validate biological function. A high score means that a candidate passed the implemented computational checks under the available assumptions and inputs. It does not mean that the design is a complete plasmid, that all biological parts are experimentally compatible, or that the circuit will work in vivo.

這些指標並不驗證生物學功能。高分代表候選方案在可用的假設和輸入下通過了已實現的計算檢查。這並不意味著該設計是一個完整的質體、所有生物元件在實驗上都相容，或者該電路將在活體內（in vivo）工作。

## 1. Score Summary
## 1. 分數摘要

Candidate evaluation is implemented in [benchmark_suite/benchmark_controller.py](benchmark_suite/benchmark_controller.py). The main entry point is:

候選方案的評估實作於 [benchmark_suite/benchmark_controller.py](benchmark_suite/benchmark_controller.py)。主要進入點為：

```python
evaluate_candidate(candidate)
```

It returns:

它返回：

- `weighted_total_score`: the final normalized score from 0.0 to 1.0.
  `weighted_total_score`：最終歸一化分數，範圍為 0.0 到 1.0。
- `grade`: `Excellent`, `Pass`, or `Fail`.
  `grade`：評級，分為 `Excellent`（優秀）、`Pass`（通過）或 `Fail`（不通過）。
- `component_scores`: the normalized scores used in the weighted sum.
  `component_scores`：用於加權求和的歸一化子項分數。
- `score_weights`: the component weights.
  `score_weights`：各子項的權重。
- `details`: per-evaluator diagnostic information.
  `details`：每個評估器的診斷資訊。

The weighted score is:

加權分數為：

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

All components are clamped to the range `[0.0, 1.0]` before scoring.

在評分之前，所有子項分數都會被限制在 `[0.0, 1.0]` 範圍內。

| Component / 評估子項 | Weight / 權重 | Interpretation / 解讀 |
| --- | ---: | --- |
| `functional` | 0.22 | Logic consistency and ON/OFF separation when data are available. <br> 邏輯一致性，以及當數據可用時的 ON/OFF 分離度。 |
| `kinetic` | 0.15 | Simulated expression dynamics and robustness under the ODE/noisy-response model. <br> 在 ODE/有雜訊響應模型下的模擬表達動力學與魯棒性。 |
| `static_plausibility` | 0.08 | Structural plausibility based on repeated parts and logic depth. <br> 基於重複元件和邏輯深度的結構合理性。 |
| `metabolic_burden` | 0.15 | Penalty for unnecessary gate complexity. <br> 對不必要的邏輯閘複雜度施加的懲罰。 |
| `robustness` | 0.15 | Explicit robustness score, usually from kinetic simulation or candidate metadata. <br> 明確的魯棒性分數，通常來自動力學模擬或候選方案元數據。 |
| `temporal` | 0.05 | Response-time or rise-time behavior. <br> 響應時間或上升時間行為。 |
| `orthogonality` | 0.10 | Cello/buildability and cross-talk-related constraint signal. <br> 與 Cello/可構建性和交叉干擾（Cross-talk）相關的約束訊號。 |
| `cello_assignment` | 0.10 | Cello assignment quality or score when available. <br> 可用時的 Cello 分配品質或分數。 |

Grades are assigned as:

評級分配如下：

| Grade / 評級 | Condition / 條件 |
| --- | --- |
| `Excellent` | `weighted_total_score >= 0.80` |
| `Pass` | `0.60 <= weighted_total_score < 0.80` |
| `Fail` | `weighted_total_score < 0.60` |

## 2. Functional Score
## 2. 功能性分數

Implemented in [benchmark_suite/functional_scorer.py](benchmark_suite/functional_scorer.py).

實作於 [benchmark_suite/functional_scorer.py](benchmark_suite/functional_scorer.py)。

The functional score checks whether the candidate appears to implement the intended Boolean behavior and whether available expression values show useful ON/OFF separation.

功能性分數檢查候選方案是否實現了預期的布林行為，以及可用的表達值是否顯示出有用的 ON/OFF 分離度。

Inputs may include:

輸入項可能包括：

- `truth_table`, `truth_table_or_logic_matrix`, or `logic_matrix`
- `verilog`, `verilog_code`, or `verilog_draft`
- `fold_change`
- `min_on` / `on_min`
- `max_off` / `off_max`
- fallback fields such as `functional_score` or `score`

When both a truth table and Verilog are available, the scorer simulates supported combinational Verilog constructs:

當真值表與 Verilog 皆可用時，評分器會模擬支持的組合邏輯 Verilog 結構：

- `assign`
- `and`, `or`, `not`, `nand`, `nor`, `xor`, `xnor`, `buf`

The logic-compliance score is:

邏輯符合性分數為：

```text
logic_compliance_score =
  correct_truth_table_rows / checked_truth_table_rows
```

If no checkable truth-table rows are found:

如果未找到可檢查的真值表行：

```text
logic_compliance_score = 0.0
```

If analog ON/OFF values are available, the scorer also computes:

如果模擬（Analog）的 ON/OFF 值可用，評分器還會計算：

```text
fold_change = min_on / max(max_off, 1e-9)
```

```text
fold_change_score =
  clamp01(log1p(max(0.0, fold_change)) / log1p(100.0))
```

```text
margin = min_on - max_off
scale = max(abs(min_on), abs(max_off), 1.0)
margin_score = clamp01(0.5 + 0.5 * margin / scale)
```

The final functional score is the mean of the available functional components:

最終的功能性分數是可用功能子項的平均值：

```text
functional_score = mean(
  logic_compliance_score,
  fold_change_score,
  margin_score
)
```

Only available components are included. If none are available, the scorer falls back to:

僅包含可用的子項。如果均不可用，評分器將回退至：

```text
candidate.functional_score or candidate.score or 0.0
```

Interpretation: this score is strongest when it is backed by both a truth-table check and expression-separation evidence. A fallback-only score should be treated as weak evidence.

解讀：當該分數同時有真值表檢查和表達分離度證據支援時，說服力最強。僅有回退（Fallback）的分數應被視為微弱的證據。

The UI and MCP adapter may also expose explanation artifacts such as score explanations, decision traces, Cello provenance warnings, and ODE trajectory readouts. These explanations help audit why a score was assigned, but they do not change the benchmark weights or convert heuristic scores into experimental validation.

UI 與 MCP adapter 也可能輸出分數解釋、決策紀錄、Cello 來源警示與 ODE 軌跡讀數等解釋性產物。這些解釋有助於審查分數為何如此，但不會改變基準權重，也不會將啟發式分數轉換為實驗驗證。

## 3. Kinetic and Robustness Scores
## 3. 動力學與魯棒性分數

Implemented in [benchmark_suite/kinetic_scorer.py](benchmark_suite/kinetic_scorer.py) and [tools/ode_simulator.py](tools/ode_simulator.py).

實作於 [benchmark_suite/kinetic_scorer.py](benchmark_suite/kinetic_scorer.py) 與 [tools/ode_simulator.py](tools/ode_simulator.py)。

The kinetic scorer uses a noisy ODE response simulation when the candidate has simulation-relevant inputs such as:

當候選方案具有與模擬相關的輸入時，動力學評分器將使用有雜訊的 ODE 響應模擬，例如：

- `verilog`
- `verilog_code`
- `gate_count`
- `biokinetic_parameters`

If these inputs are missing, it falls back to:

如果缺失這些輸入，它將回退至：

```text
candidate.kinetic_score or candidate.score or 0.0
```

When simulation inputs are available, the scorer runs multiple noisy response simulations. Defaults are:

當模擬輸入可用時，評分器會運行多次有雜訊響應模擬。預設值為：

```text
monte_carlo_runs = 20
noise_level = 0.10
```

For each successful simulation, the scorer records:

對於每次成功的模擬，評分器會記錄：

- `on_value`: terminal output value.
  `on_value`：終端輸出值。
- `off_value`: maximum output in the early OFF window.
  `off_value`：早期 OFF 窗口中的最大輸出值。

The scorer then checks whether the simulated signal collapses:

隨後評分器會檢查模擬訊號是否塌陷：

```text
min_signal = min(on_values)
max_noise = max(off_values)
collapsed = max_noise >= min_signal
```

The signal-to-noise ratio is:

訊噪比（SNR）為：

```text
snr =
  max(0.0, (mean_on - mean_off) / max(std_on + std_off, 1e-9))
```

SNR is normalized as:

SNR 歸一化為：

```text
snr_score = snr / (snr + 10.0)
```

If the signal collapses:

如果訊號塌陷：

```text
robustness_score = 0.0
```

Otherwise:

否則：

```text
success_rate = successful_runs / monte_carlo_runs
robustness_score = 0.5 * success_rate + 0.5 * snr_score
```

If some runs fail but the signal does not collapse, the score is further penalized:

如果某些運行失敗但訊號未塌陷，分數將被進一步扣分：

```text
robustness_score =
  robustness_score * (monte_carlo_runs - failed_runs) / monte_carlo_runs
```

The kinetic evaluator reports this robustness score as its score. The benchmark controller also places a `robustness` component into the weighted total. If the candidate already contains an explicit `robustness_score`, that value is used; otherwise, the kinetic result's robustness score is used.

動力學評估器將此魯棒性分數作為其分數報告。基準控制器還會將 `robustness`（魯棒性）子項放入加權總分中。如果候選方案已包含明確的 `robustness_score`，則使用該值；否則，使用動力學結果的魯棒性分數。

Interpretation: kinetic and robustness scores are useful for identifying obvious dynamic failures under the simplified model. They should not be interpreted as quantitative predictions of real cellular expression.

解讀：動力學和魯棒性分數有助於在簡化模型下識別明顯的動態失效。它們不應被解讀為對真實細胞表達的定量預測。

## 4. ODE Simulation Metrics
## 4. ODE 模擬指標

Implemented in [tools/ode_simulator.py](tools/ode_simulator.py).

實作於 [tools/ode_simulator.py](tools/ode_simulator.py)。

The ODE simulator uses a reduced resource-aware model. For a candidate topology, it tracks:

ODE 模擬器使用簡化的資源感知模型。對於候選拓撲，它追蹤：

- mRNA species
  mRNA 物種
- protein species
  蛋白質物種
- free/occupied RNAP
  游離/佔用的 RNAP
- free/occupied ribosome
  游離/佔用的核糖體
- aggregate burden proxy
  聚合負載代理指標

The simulator computes metrics such as:

模擬器計算以下指標：

```text
output_mean = mean(output_protein)
output_std = std(output_protein)
output_cv = output_std / max(output_mean, 1e-9)
signal_to_noise_ratio = output_mean / max(output_std, 1e-9)
```

It also tracks resource use:

它還追蹤資源使用情況：

```text
rnap_occupancy_max
ribosome_occupancy_max
rnap_free_min
ribosome_free_min
max_burden_nM
```

Dynamic margin is approximated as:

動態邊際近似為：

```text
dynamic_margin =
  output_mean / (1.0 + max(upstream_protein_values))
```

The ODE-derived kinetic score uses:

由 ODE 導出的動力學分數使用：

```text
stability = 1.0 / (1.0 + output_cv)
```

If Monte Carlo terminal-output variation is available:

如果蒙特卡羅終端輸出變異可用：

```text
stability =
  stability * 1.0 / (1.0 + monte_carlo_terminal_output_cv)
```

```text
margin = clamp01(dynamic_margin / 80.0)
```

```text
resource_penalty =
  1.0 - 0.5 * (rnap_occupancy_max + ribosome_occupancy_max)
```

The raw kinetic score is:

原始動力學分數為：

```text
raw_kinetic_score =
  0.25 * stability
+ 0.20 * margin
+ 0.25 * burden_penalty
+ 0.20 * toxicity_penalty
+ 0.10 * clamp01(resource_penalty)
```

The final ODE kinetic score is:

最終的 ODE 動力學分數為：

```text
kinetic_score =
  clamp01(
    raw_kinetic_score
    * failure_penalty
    * (0.35 + 0.65 * resource_capacity_factor)
  )
```

This ODE model is intentionally simplified. It is designed for early ranking and failure detection inside a search loop, not for complete biological prediction. It does not model full plasmid architecture, copy-number dynamics, host growth, DNA supercoiling, RNA folding, codon usage, protein maturation, or experimentally calibrated toxicity feedback.

此 ODE 模型被刻意簡化。它旨在用於搜尋迴圈內的早期排序和失效檢測，而非完整的生物學預測。它不模擬完整的質體架構、複製數動力學、宿主生長、DNA 超螺旋、RNA 折疊、密碼子使用偏好、蛋白質成熟或經實驗校準的毒性反饋。

## 5. Static Plausibility Score
## 5. 靜態合理性分數

Implemented in [benchmark_suite/static_plausibility_evaluator.py](benchmark_suite/static_plausibility_evaluator.py).

實作於 [benchmark_suite/static_plausibility_evaluator.py](benchmark_suite/static_plausibility_evaluator.py)。

This evaluator checks whether a candidate has simple structural warning signs:

此評估器檢查候選方案是否具有簡單的結構警告標誌：

- repeated part IDs
  重複的元件 ID
- excessive logic depth
  過深的邏輯深度

It may use:

它可能使用：

- `part_ids`
- `assigned_parts`
- `components`
- Verilog comments such as `// part: <id>`
- Verilog-like tokens such as `promoter_<id>`, `rbs_<id>`, `terminator_<id>`, or `repressor_<id>`
- explicit `logic_depth`, `depth`, or `gate_count`
- explicit `plausibility_score`

Repeated parts are counted as:

重複元件的計數方式為：

```text
repeated_part_count =
  sum(count(part_id) - 1 for each repeated part_id)
```

The evaluator applies:

評估器套用以下公式：

```text
repeat_penalty = 1.0 - exp(-0.18 * repeated_part_count)
```

```text
depth_excess = max(0, logic_depth - 4)
depth_penalty = 1.0 - exp(-0.22 * depth_excess)
```

```text
structural_score =
  clamp01((1.0 - repeat_penalty) * (1.0 - depth_penalty))
```

If an explicit `plausibility_score` is present together with structural inputs:

如果明確的 `plausibility_score` 與結構輸入項同時存在：

```text
static_plausibility =
  clamp01(0.5 * plausibility_score + 0.5 * structural_score)
```

If only `plausibility_score` is present, that value is used directly.

如果僅存在 `plausibility_score`，則直接使用該值。

Interpretation: this is a lightweight structural check. It can penalize obvious complexity or repetition, but it is not a substitute for detailed biological part compatibility analysis.

解讀：這是一個輕量級的結構檢查。它可以懲罰明顯的複雜度或重複性，但它不能替代詳細的生物元件相容性分析。

## 6. Metabolic Burden Score
## 6. 代謝負載分數

Implemented in [benchmark_suite/metabolic_scorer.py](benchmark_suite/metabolic_scorer.py).

實作於 [benchmark_suite/metabolic_scorer.py](benchmark_suite/metabolic_scorer.py)。

This evaluator currently uses logic-gate complexity as a proxy for burden. It counts Verilog primitive gates:

此評估器目前使用邏輯閘複雜度作為負載的代理指標。它統計 Verilog 原語邏輯閘：

- `and`
- `nand`
- `or`
- `nor`
- `xor`
- `xnor`
- `not`
- `buf`

If Verilog is unavailable but `gate_count` is provided, it uses that value. If neither is available, the evaluator skips the check and returns:

如果 Verilog 不可用但提供了 `gate_count`，它將使用該值。如果兩者皆不可用，評估器將跳過此檢查並返回：

```text
metabolic_burden_score = 1.0
gate_count = 0
complexity_penalty = 0.0
```

The burden proxy is:

負載代理指標為：

```text
excess_gates = max(0, gate_count - ideal_gate_limit)
```

where:

其中：

```text
ideal_gate_limit = 3
decay_rate = 0.35
```

```text
metabolic_burden_score = exp(-decay_rate * excess_gates)
```

```text
complexity_penalty = 1.0 - metabolic_burden_score
```

Interpretation: this is not a direct metabolic model. It is a design-complexity proxy that penalizes candidates with more logic gates than the current ideal limit.

解讀：這不是一個直接的代謝模型。它是一個設計複雜度代理指標，懲罰邏輯閘數量超過當前理想限制的候選方案。

## 7. Temporal Score
## 7. 時序分數

Implemented in [benchmark_suite/temporal_scorer.py](benchmark_suite/temporal_scorer.py).

實作於 [benchmark_suite/temporal_scorer.py](benchmark_suite/temporal_scorer.py)。

The temporal score estimates whether the candidate response is fast enough relative to a target rise time.

時序分數評估候選方案的響應相對於目標上升時間（Rise time）是否足夠快。

It looks for timing evidence in this order:

它按以下順序尋找時間證據：

1. Explicit `rise_time` or `response_time`.
   明確的 `rise_time`（上升時間）或 `response_time`（響應時間）。
2. A trace using `time` / `t` and `output` / `y` / `output_trace`.
   使用 `time` / `t` 與 `output` / `y` / `output_trace` 的軌跡。
3. An estimate from `logic_depth`, `depth`, or `gate_count`.
   從 `logic_depth`、`depth` 或 `gate_count` 進行估算。

If a trace is available:

如果軌跡可用：

```text
rise_time =
  first time where output >= threshold_on
```

where:

其中：

```text
threshold_on = candidate.threshold_on or 0.5
```

If only depth is available:

如果僅深度可用：

```text
rise_time = depth * gate_delay_seconds
```

where:

其中：

```text
gate_delay_seconds = candidate.gate_delay_seconds or 35.0
```

The default target is:

預設目標為：

```text
target_rise_time = 180.0
```

The score is:

分數為：

```text
temporal_score =
  clamp01(exp(-max(0.0, rise_time - target_rise_time) / target_rise_time))
```

If no timing evidence is available, the evaluator skips the check and returns:

如果沒有可用的時間證據，評估器將跳過此檢查並返回：

```text
temporal_score = 1.0
```

Interpretation: the temporal score is a weak signal unless it is backed by explicit timing data or simulation traces.

解讀：除非有明確的時間數據或模擬軌跡支援，否則時序分數是一個微弱的訊號。

## 8. Cello Constraint, Orthogonality, and Assignment Scores
## 8. Cello 約束、正交性與分配分數

Implemented in [benchmark_suite/cello_constraint_evaluator.py](benchmark_suite/cello_constraint_evaluator.py) and [tools/cello_wrapper.py](tools/cello_wrapper.py).

實作於 [benchmark_suite/cello_constraint_evaluator.py](benchmark_suite/cello_constraint_evaluator.py) 與 [tools/cello_wrapper.py](tools/cello_wrapper.py)。

The Cello constraint evaluator extracts signals from:

Cello 約束評估器從以下來源提取訊號：

- `cello_report`
- `cello_json_report`
- `assignment_report`
- Cello stdout/stderr logs
- mapping error summaries
- report files
- candidate fields such as `mapping_status`, `cello_buildable`, `orthogonality_score`, and `cello_assignment_score`

The evaluator sets:

評估器設定：

- `orthogonality_score`
- `cello_assignment_score`
- `cello_buildable`
- `toxicity`
- `toxicity_score`

Severe orthogonality or part-availability failures are detected from phrases such as:

嚴重的正交性或元件可用性失效是從以下短語中檢測到的：

- `not enough gates`
- `not enough orthogonal parts`
- `not enough repressors`
- `crosstalk`
- `cross talk`

If such a severe constraint error is found:

如果發現此類嚴重的約束錯誤：

```text
orthogonality_score = 0.05
cello_buildable = false
```

If the candidate is buildable:

如果候選方案是可構建的：

```text
orthogonality_score =
  candidate.orthogonality_score or 1.0
```

If the candidate is not buildable and no stronger evidence is available:

如果候選方案不可構建且沒有更強的證據：

```text
orthogonality_score =
  candidate.orthogonality_score or 0.25
```

Assignment scores may be extracted from report fields or text patterns. If a score is greater than 1.0, it is interpreted as a percentage and divided by 100:

分配分數可以從報告欄位或文本模式中提取。如果分數大於 1.0，它會被解讀為百分比並除以 100：

```text
cello_assignment_score =
  clamp01(assignment_score / 100.0) if assignment_score > 1.0
  else clamp01(assignment_score)
```

The combined Cello constraint score is:

組合後的 Cello 約束分數為：

```text
cello_constraint_score =
  0.5 * orthogonality_score
+ 0.5 * cello_assignment_score
```

If the candidate is not buildable:

如果候選方案不可構建：

```text
cello_constraint_score =
  cello_constraint_score * 0.5
```

The benchmark controller does not directly weight `cello_constraint_score`. Instead, it weights the extracted `orthogonality` and `cello_assignment` components separately.

基準控制器不直接對 `cello_constraint_score` 進行加權。相反，它分別對提取的 `orthogonality`（正交性）和 `cello_assignment`（Cello 分配）子項進行加權。

Important: when no external Cello command is configured, [tools/cello_wrapper.py](tools/cello_wrapper.py) returns mock topology data with:

重要提示：當未配置外部 Cello 指令時，[tools/cello_wrapper.py](tools/cello_wrapper.py) 將返回模擬的拓撲數據，其屬性為：

```text
mapping_status = "unmapped"
cello_buildable = false
cello_assignment_score = 0.0
```

Mock-mode results should not be described as successful Cello mapping.

模擬模式的結果不應被描述為成功的 Cello 映射。

## 9. Semantic Faithfulness
## 9. 語義忠實性

Implemented in [benchmark_suite/semantic_evaluator.py](benchmark_suite/semantic_evaluator.py), but not currently part of `SCORE_WEIGHTS`.

實作於 [benchmark_suite/semantic_evaluator.py](benchmark_suite/semantic_evaluator.py)，但目前不屬於 `SCORE_WEIGHTS`（分數權重）的一部分。

The semantic evaluator can use an LLM to compare the original natural-language request with generated Verilog and return:

語義評估器可以使用 LLM 將原始自然語言請求與生成的 Verilog 進行比較，並返回：

- `semantic_faithfulness_score`
- `missed_edge_cases`

The benchmark controller currently records semantic fields if they are present on the candidate:

基準控制器目前在候選方案中記錄語義欄位（如果存在）：

```text
semantic_faithfulness_score =
  candidate.semantic_faithfulness_score or 1.0
```

```text
missed_edge_cases =
  candidate.missed_edge_cases
  or candidate.missed_conditions
  or []
```

Because semantic faithfulness is not currently included in the weighted total, it should be treated as diagnostic metadata rather than a direct scoring component.

由於語義忠實性目前未包含在加權總分中，因此應將其視為診斷元數據（Diagnostic metadata），而非直接的評分組件。

## 10. Critic Thresholds
## 10. Critic 閾值

Implemented in [agents/critic_agent.py](agents/critic_agent.py).

實作於 [agents/critic_agent.py](agents/critic_agent.py)。

The Critic uses benchmark outputs to decide whether a candidate should be approved, repaired, or rejected. Current thresholds include:

Critic 使用基準輸出決定是批准、修復還是拒絕候選方案。目前的閾值包括：

| Threshold / 評估指標 | Value / 閾值 | Purpose / 目的 |
| --- | ---: | --- |
| `PASS_SCORE_THRESHOLD` | 0.80 | Strong candidate threshold. <br> 強候選方案閾值。 |
| `FAIL_SCORE_THRESHOLD` | 0.60 | Weak candidate threshold. <br> 弱候選方案閾值。 |
| `METABOLIC_BURDEN_THRESHOLD` | 0.70 | Reject or repair high-complexity candidates. <br> 拒絕或修復高複雜度的候選方案。 |
| `ROBUSTNESS_THRESHOLD` | 0.75 | Reject or repair fragile candidates. <br> 拒絕或修復脆弱的候選方案。 |
| `ORTHOGONALITY_THRESHOLD` | 0.20 | Detect likely Cello/UCF or part-compatibility failure. <br> 檢測可能的 Cello/UCF 或元件相容性失效。 |
| `SEMANTIC_FAITHFULNESS_THRESHOLD` | 0.90 | Detect request-to-design mismatch when missed edge cases exist. <br> 當存在遺漏的邊角情況（Edge cases）時，檢測請求與設計之間的不匹配。 |

The Critic can route failures to:

Critic 可以將失效路由至：

- `Builder`, for logic or design-strategy repair.
  `Builder`，用於邏輯或設計策略修復。
- `Translator`, for part/mapping/Verilog-oriented repair.
  `Translator`，用於元件/映射/Verilog 導向的修復。
- `Consolidator`, when the candidate is acceptable.
  `Consolidator`，當候選方案可接受時。

## 11. How to Read Scores
## 11. 如何解讀分數

Recommended interpretation:

推薦的解讀方式：

- Use `weighted_total_score` to compare candidates generated under similar assumptions.
  使用 `weighted_total_score`（加權總分）來比較在相似假設下生成的候選方案。
- Inspect `component_scores` before trusting the total score.
  在信任總分之前，請先檢查 `component_scores`（子項分數）。
- Treat fallback-only scores as weak evidence.
  將僅有回退（Fallback）的分數視為微弱的證據。
- Treat mock Cello output as workflow scaffolding, not biological mapping.
  將模擬的 Cello 輸出視為工作流支架，而非生物學映射。
- Treat ODE results as early screening signals, not calibrated in vivo predictions.
  將 ODE 結果視為早期篩選訊號，而非校準過的活體內預測。
- Prefer candidates with clear evidence across multiple components rather than one high aggregate score.
  優先選擇在多個子項中具有明確證據的候選方案，而非單一高總分的候選方案。

The most defensible way to describe the system is:

最合理的系統描述方式是：

> The benchmark ranks computational candidate designs and exposes failure modes for iterative repair.
> 基準測試對計算候選設計進行排序，並顯現失敗模式以進行迭代修復。

Avoid describing the score as:

避免將分數描述為：

> A proof that the generated construct is a complete, buildable, experimentally validated genetic circuit.
> 生成的構建體是完整、可構建且經過實驗驗證的基因電路的證明。
# Design Revision and Export Metrics Note (2026-06-06)
# 設計版本與匯出指標說明（2026-06-06）

The following new fields and operations are not additional benchmark components:

以下新增欄位與操作不是新的 benchmark component：

- sequence coverage (`missing`, `partial`, or `complete`);
- sequence coverage（`missing`、`partial` 或 `complete`）；
- replacement-validation pass/fail checks;
- 元件替換驗證的 pass/fail；
- DesignRevision number and lineage;
- DesignRevision 版本號與 lineage；
- DesignDiff part/construct changes;
- DesignDiff 的元件／construct 差異；
- BOM, GenBank, or SBOL3 export availability.
- BOM、GenBank 或 SBOL3 是否可匯出。

These fields describe design completeness, provenance, or representation. They do not change `weighted_total_score`.

這些欄位描述設計完整度、來源或表示方式，不會改變 `weighted_total_score`。

In particular:

- A complete sequence does not increase functional, kinetic, robustness, orthogonality, or Cello-assignment scores automatically.
- 完整序列不會自動提高 functional、kinetic、robustness、orthogonality 或 Cello-assignment 分數。
- A successful export is not a score and should not be used as a buildability label.
- 成功匯出不是分數，也不應作為 buildability 標籤。
- A replacement revision should be re-evaluated before metric differences are interpreted.
- 元件替換後的新版本應重新評估，才能解讀指標差異。
- `DesignDiff` reports the metrics supplied to it; it does not rerun ODE simulation or benchmark evaluation.
- `DesignDiff` 只回報傳入的指標，不會重新執行 ODE 或 benchmark。
