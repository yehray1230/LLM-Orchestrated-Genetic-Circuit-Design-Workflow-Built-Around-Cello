# Demo Cases

This folder turns the phase-two goal into a repeatable demo and reporting
workflow. Each case should be run with the same evidence structure so the
project can be explained as a coherent research prototype rather than a set of
separate features.

## Phase-Two Goal

Produce a small story package that shows what the system does:

```text
natural-language intent
structured spec
truth table or logic matrix
Verilog
Cello or mock Cello result
ODE simulation summary
benchmark score
readiness report
export artifacts or export blockers
limitations and next checks
```

## Fixed Cases

| Case | Logic | Output | Purpose | Report |
| --- | --- | --- | --- | --- |
| 01 | `A AND NOT B` | `GFP` | Main two-input demo with activation and repression. | [case_01_a_and_not_b_gfp.md](case_01_a_and_not_b_gfp.md) |
| 02 | `A OR B` | `reporter` | Simple two-input permissive logic baseline. | [case_02_a_or_b_reporter.md](case_02_a_or_b_reporter.md) |
| 03 | `NOT A` | `GFP` | Minimal single-input inverter/control case. | [case_03_not_a_gfp.md](case_03_not_a_gfp.md) |

## Recommended Order

1. Run Case 01 first and make it complete.
2. Use Case 01 as the example for the report style.
3. Run Cases 02 and 03 with the same evidence fields.
4. Update [DEMO_SUMMARY.md](DEMO_SUMMARY.md) after each run.
5. Keep mock Cello and real Cello claims visibly separated in every report.

## Evidence Standard

Every case report should answer:

- What did the user ask for?
- What explicit assumptions or defaults did the system use?
- What logic was produced?
- What Verilog was produced?
- Was Cello real or mock?
- What simulation and benchmark evidence exists?
- What readiness stage or blockers are present?
- What can be exported?
- What should not be claimed yet?

## Demo Boundary

Use this safe claim unless real construction and measurement evidence is added:

```text
This project generates and evaluates computational candidate designs for
regulatory logic circuits. It does not yet produce complete, buildable,
experimentally validated genetic circuits.
```

