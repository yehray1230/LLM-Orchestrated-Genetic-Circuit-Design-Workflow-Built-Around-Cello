# Demo Case 01: A AND NOT B -> GFP

## Status

```text
Status: baseline captured
Last updated: 2026-07-11
Runner: src.scripts.generate_demo_baseline
Environment: local Windows venv
```

## 1. Intent

Natural-language input:

```text
Activate GFP only when input A is present and input B is absent.
```

Short interpretation:

```text
This is the main two-input demo. The desired output is ON only for A=1 and B=0.
```

## 2. Structured Spec

```json
{
  "chassis": "E. coli K-12 or project default",
  "inputs": ["A", "B"],
  "outputs": ["GFP"],
  "logic_relation": "A AND NOT B",
  "copy_number": "project default",
  "assumptions": [
    "Input A is an activating condition.",
    "Input B is a repressing condition.",
    "Mock Cello output is acceptable for workflow demonstration unless real Cello is configured."
  ]
}
```

## 3. Truth Table / Logic Matrix

| A | B | GFP |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 0 | 1 |
| 1 | 1 | 0 |

## 4. Generated Verilog

```verilog
module demo_a_and_not_b(input A, input B, output GFP); assign GFP = A & ~B; endmodule
```

## 5. Cello Result

| Field | Value |
| --- | --- |
| `cello_mode` | `not_run` |
| `cello_claim_level` | `not_mapped` |
| `mapping_status` | `not_mapped` |
| `cello_buildable` | not claimed |
| `cello_assignment_score` | not claimed |
| `orthogonality_score` | not claimed |

Warning or provenance:

```text
Deterministic task benchmark uses direct topology simulation; Cello mapping is
not claimed. The packet also records that the Cello command is not configured
and a mock Cello fallback would be used where applicable.
```

## 6. ODE Summary

```text
Simulation model: resource-aware-regulatory-ode@1.9.0
Run ID: generated per baseline run; see the current baseline summary
Configuration hash: 2fb665d9dd39fc1c06982e7052bd1438c8260e8d7537bdcbbf24b1251b5780ca
Result hash: 55cc49bb2a3398b5ffe909c9e561147ac2676b6859041ba6310742b8e2bc53b4
Score: 0.85
Grade: Excellent
```

## 7. Benchmark

```text
Dataset: research_smoke_v1@1.0.0
Cases: 4
Pass rate: 1.0
Mean score: 0.716625
```

## 8. Readiness

```text
Status: primer_ready
Next required stage: sequence_optimized
Experimental readiness: None
```

## 9. Export Artifacts

```text
Baseline packet:
outputs/demo_baseline/demo_baseline_cc928f18c446/demo_baseline_packet.json

Baseline summary:
outputs/demo_baseline/demo_baseline_cc928f18c446/demo_baseline_summary.md

Sequence evidence:
outputs/demo_baseline/demo_baseline_cc928f18c446/sequence_analysis.json

Assembly plan:
outputs/demo_baseline/demo_baseline_cc928f18c446/assembly_plan.json

Primer readiness:
outputs/demo_baseline/demo_baseline_cc928f18c446/primer_readiness.json
```

## 10. Interpretation

This case should demonstrate whether the system can preserve a user-specified
activation-plus-repression logic relation through structured spec, truth table,
Verilog, scoring, and readiness reporting.

It does not prove biological buildability unless external Cello mapping,
sequence-level evidence, and experimental validation are added.

## 11. Next Checks

- [x] Generate baseline evidence packet.
- [x] Fill in generated Verilog.
- [x] Fill in Cello metadata and warning.
- [x] Fill in ODE, benchmark, readiness, and export evidence.
- [x] Update [DEMO_SUMMARY.md](DEMO_SUMMARY.md).
- [ ] Run or inspect the same case through the FastAPI/web workspace if a live
      UI walkthrough is needed.
- [ ] Run external Cello with compatible UCF/library data before making any
      real Cello mapping claim.

