# Demo Case 02: A OR B -> reporter

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
Activate a reporter when input A or input B is present.
```

Short interpretation:

```text
This is a simple two-input permissive logic baseline. The desired output is ON
when either input is present.
```

## 2. Structured Spec

```json
{
  "chassis": "E. coli K-12 or project default",
  "inputs": ["A", "B"],
  "outputs": ["reporter"],
  "logic_relation": "A OR B",
  "copy_number": "project default",
  "assumptions": [
    "A and B are independent input conditions.",
    "Reporter identity may be resolved by project defaults unless specified.",
    "Mock Cello output is acceptable for workflow demonstration unless real Cello is configured."
  ]
}
```

## 3. Truth Table / Logic Matrix

| A | B | reporter |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 0 | 1 | 1 |
| 1 | 0 | 1 |
| 1 | 1 | 1 |

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

This case should demonstrate a baseline two-input logic request with less
structural complexity than Case 01. It is useful for comparing whether simpler
logic receives fewer repair suggestions or blockers.

It does not prove biological buildability unless external Cello mapping,
sequence-level evidence, and experimental validation are added.

## 11. Next Checks

- [ ] Run after Case 01 is complete.
- [ ] Fill in generated workflow evidence.
- [ ] Compare score and readiness against Case 01.
- [ ] Update [DEMO_SUMMARY.md](DEMO_SUMMARY.md).

