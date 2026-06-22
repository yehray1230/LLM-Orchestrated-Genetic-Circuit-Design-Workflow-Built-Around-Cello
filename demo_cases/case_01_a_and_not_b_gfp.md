# Demo Case 01: A AND NOT B -> GFP

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
// Fill from workflow output.
```

## 5. Cello Result

| Field | Value |
| --- | --- |
| `cello_mode` | pending |
| `cello_claim_level` | pending |
| `mapping_status` | pending |
| `cello_buildable` | pending |
| `cello_assignment_score` | pending |
| `orthogonality_score` | pending |

Warning or provenance:

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

This case should demonstrate whether the system can preserve a user-specified
activation-plus-repression logic relation through structured spec, truth table,
Verilog, scoring, and readiness reporting.

It does not prove biological buildability unless external Cello mapping,
sequence-level evidence, and experimental validation are added.

## 11. Next Checks

- [ ] Run the case through the Streamlit research UI.
- [ ] Run or inspect the same case through the FastAPI/web workspace if possible.
- [ ] Fill in generated Verilog.
- [ ] Fill in Cello metadata and warning.
- [ ] Fill in ODE, benchmark, readiness, and export evidence.
- [ ] Update [DEMO_SUMMARY.md](DEMO_SUMMARY.md).

