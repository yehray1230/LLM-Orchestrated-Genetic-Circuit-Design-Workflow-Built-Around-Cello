# Demo Case: <case name>

## Status

```text
Status: draft | run-complete | reviewed
Last updated:
Runner:
Environment:
```

## 1. Intent

Natural-language input:

```text
<paste exact user intent>
```

Short interpretation:

```text
<one or two sentences>
```

## 2. Structured Spec

```json
{
  "chassis": "",
  "inputs": [],
  "outputs": [],
  "logic_relation": "",
  "copy_number": "",
  "assumptions": []
}
```

## 3. Truth Table / Logic Matrix

| Input A | Input B | Output |
| ---: | ---: | ---: |
| 0 | 0 |  |
| 0 | 1 |  |
| 1 | 0 |  |
| 1 | 1 |  |

Notes:

```text
<logic notes>
```

## 4. Generated Verilog

```verilog
<paste generated Verilog>
```

## 5. Cello Result

| Field | Value |
| --- | --- |
| `cello_mode` |  |
| `cello_claim_level` |  |
| `mapping_status` |  |
| `cello_buildable` |  |
| `cello_assignment_score` |  |
| `orthogonality_score` |  |

Warning or provenance:

```text
<paste cello_warning, artifact path, or mapping failure summary>
```

## 6. ODE Summary

| Readout | Value |
| --- | --- |
| peak output protein |  |
| time to peak |  |
| final output protein |  |
| max total mRNA |  |
| max total protein |  |
| steady-state status |  |

Coverage warnings:

```text
<paste warnings or state "Not available">
```

## 7. Benchmark

| Metric | Value |
| --- | ---: |
| weighted total score |  |
| grade |  |
| functional |  |
| kinetic |  |
| metabolic burden |  |
| robustness |  |
| temporal |  |
| orthogonality |  |
| cello assignment |  |

Main limitations:

```text
<lowest scoring components and repair hints>
```

## 8. Readiness

| Field | Value |
| --- | --- |
| readiness stage |  |
| next required stage |  |
| hard blockers |  |
| sequence quality status |  |
| assembly-plan status |  |
| experimental-readiness status |  |

## 9. Export Artifacts

| Artifact | Path or status |
| --- | --- |
| BOM CSV |  |
| GenBank |  |
| SBOL3 Turtle |  |
| Cello artifacts |  |
| Benchmark report |  |

Export blockers:

```text
<missing sequence evidence, conceptual parts, or other blockers>
```

## 10. Interpretation

What this case demonstrates:

```text
<short demo explanation>
```

What this case does not prove:

```text
<claim boundary>
```

## 11. Next Checks

- [ ] Compare against another topology or run.
- [ ] Inspect low benchmark components.
- [ ] Confirm whether Cello output is mock or external.
- [ ] Add real UCF/library evidence if making Cello mapping claims.
- [ ] Add sequence-level evidence before claiming export/build readiness.

