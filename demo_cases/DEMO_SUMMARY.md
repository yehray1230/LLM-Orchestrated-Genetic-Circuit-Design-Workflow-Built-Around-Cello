# Demo Summary

Use this file as the presentation-facing index for phase-two demo results.
Update it after each case is run.

## Current Status

| Case | Intent | Status | Cello mode | Score | Readiness | Main blocker | Report |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| 01 | `A AND NOT B -> GFP` | baseline captured | not_run / not_mapped | 0.85 | primer_ready | no external Cello or wet-lab validation | [case_01_a_and_not_b_gfp.md](case_01_a_and_not_b_gfp.md) |
| 02 | `A OR B -> reporter` | draft | pending |  | pending | pending | [case_02_a_or_b_reporter.md](case_02_a_or_b_reporter.md) |
| 03 | `NOT A -> GFP` | draft | pending |  | pending | pending | [case_03_not_a_gfp.md](case_03_not_a_gfp.md) |

## Cold Outreach Readiness

For first-wave cold outreach, Case 01 is the flagship demo. The current baseline
packet is:

```text
outputs/demo_baseline/demo_baseline_cc928f18c446/demo_baseline_summary.md
```

This baseline supports research-preview outreach, but not biological claims.
It uses direct topology simulation and explicitly does not claim external Cello
mapping or wet-lab validation.

## Storyline

The demo set is designed to show three levels of circuit-logic complexity:

1. Case 01 tests the main activation-plus-repression story.
2. Case 02 tests a simpler two-input permissive logic baseline.
3. Case 03 tests a minimal single-input inverter/control case.

Together, the cases should demonstrate whether the workflow can preserve user
intent across structured specification, logic, Verilog, Cello provenance,
simulation, scoring, readiness, and export boundaries.

## Presentation Notes

Use these points when presenting the result:

- Start with the fixed natural-language intent.
- Show the structured spec and truth table before the generated Verilog.
- Call out `cello_mode` and `cello_claim_level` before discussing mapping.
- Treat ODE and benchmark results as computational screening evidence.
- Treat readiness blockers as stronger than a high aggregate score.
- End with limitations and next checks rather than biological guarantees.

## Phase-Two Done Criteria

- [ ] Case 01 has a complete report.
- [ ] Cases 02 and 03 have reports in the same format.
- [ ] Every report clearly separates mock Cello from external Cello.
- [ ] Every report includes benchmark and readiness evidence or explains why it is missing.
- [ ] Every report includes limitations and next checks.
- [ ] This summary can be used as a short briefing for a supervisor or collaborator.

