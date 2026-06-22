# Demo Case 03: NOT A -> GFP

## Status

```text
Status: draft
Last updated:
Runner:
Environment:
```

## 1. Intent

Natural-language input:

```text
Activate GFP only when input A is absent.
```

Short interpretation:

```text
This is a minimal single-input inverter/control case. The desired output is ON
for A=0 and OFF for A=1.
```

## 2. Structured Spec

```json
{
  "chassis": "E. coli K-12 or project default",
  "inputs": ["A"],
  "outputs": ["GFP"],
  "logic_relation": "NOT A",
  "copy_number": "project default",
  "assumptions": [
    "Input A is treated as a repressing condition.",
    "Mock Cello output is acceptable for workflow demonstration unless real Cello is configured."
  ]
}
```

## 3. Truth Table / Logic Matrix

| A | GFP |
| ---: | ---: |
| 0 | 1 |
| 1 | 0 |

## 4. Generated Verilog

```verilog
// Fill from workflow output.
```

## 5. Cello Result

```text
Pending workflow run.
```

## 6. ODE Summary

```text
Pending workflow run.
```

## 7. Benchmark

```text
Pending workflow run.
```

## 8. Readiness

```text
Pending workflow run.
```

## 9. Export Artifacts

```text
Pending workflow run.
```

## 10. Interpretation

This case should demonstrate the simplest inverter-style behavior and can serve
as a control case for comparing complexity, burden, and readiness blockers.

It does not prove biological buildability unless external Cello mapping,
sequence-level evidence, and experimental validation are added.

## 11. Next Checks

- [ ] Run after Case 01 is complete.
- [ ] Fill in generated workflow evidence.
- [ ] Compare score and readiness against Cases 01 and 02.
- [ ] Update [DEMO_SUMMARY.md](DEMO_SUMMARY.md).

