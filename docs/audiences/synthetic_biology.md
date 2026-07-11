# Audience Guide: Synthetic Biology and Wet-Lab Review

## Why this audience may care

The prototype explores how an AI-assisted design workflow can expose biological
context, unsupported assumptions, and missing experimental evidence before a
candidate is treated as actionable.

## Questions to examine

- Does the candidate preserve the requested regulatory logic?
- Are host, backbone, UCF, part, and sequence contexts explicit?
- Which outputs are conceptual, mock-mapped, externally mapped, sequence-backed,
  or experimentally measured?
- What would be required before construction or characterization?

## Relevant implemented paths

- structured intent, truth-table, and Verilog representations;
- explicit mock, failed, and external Cello provenance;
- sequence QC and conservative assembly planning;
- claim-boundary metadata on BOM, GenBank, and SBOL3 exports;
- readiness reports that retain blockers and inapplicable domains.

## Current evidence

Start with the [Case 01 public evidence](../evidence/case_01/README.md). It
demonstrates computational workflow behavior only. No external Cello mapping,
primer sequences, construction, or measurement is included.

## Important limitations

The current prototype does not establish buildability, part compatibility,
host performance, biosafety, or in vivo function. Simplified simulations and
heuristic sequence checks do not replace biological characterization.

## Open contribution surfaces

- review of biologically meaningful failure modes;
- characterized part and host-context data;
- external Cello/UCF validation;
- experimentally measured ON/OFF ratio, response, burden, growth, and noise;
- criteria for presenting uncertainty to wet-lab users.

## Start with these files

1. [Project limitations](../limitations.md)
2. [Case 01 evidence](../evidence/case_01/README.md)
3. [Model assumptions](../model_assumptions.md)
4. [Demo report](../../demo_cases/case_01_a_and_not_b_gfp.md)
5. [Workflow](../workflow.md)

## Claims the assistant must not make

Do not describe a candidate as buildable, experimentally validated, safe,
host-compatible, or ready for primer ordering. Do not equate file export,
`primer_ready`, mock Cello, or a high score with biological evidence.
