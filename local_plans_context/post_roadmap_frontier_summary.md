# Post-Roadmap Frontier Summary

This file is the `@`-friendly public summary for future ideas that should be discussed but not implemented until the current roadmap is stable.

Private details live in:

- `local_plans_private/post_roadmap_frontier/`

## Topics

| Topic | Private File | Purpose |
| :--- | :--- | :--- |
| CRISPR intent layer | `local_plans_private/post_roadmap_frontier/crispr_intent_layer.md` | Track CRISPRi/CRISPRa or related guide-mediated regulation as a future optional design-intent layer. |
| Multicellular consortia logic | `local_plans_private/post_roadmap_frontier/multicellular_consortia_logic.md` | Track future designs that distribute logic gates across multiple strains, cells, or compartments. |
| Dependency gate | `local_plans_private/post_roadmap_frontier/dependency_gate.md` | Define the roadmap foundations required before implementation can start. |

## Current Decision

These ideas are explicitly post-roadmap. They may be discussed, scoped, and refined now, but implementation should wait until the dependency gate is satisfied.

## First-Slice Direction

- CRISPR should first appear as non-sequence-level design intent, not guide generation.
- Consortia logic should first appear as abstract partitioning across cell contexts, not wet-lab assembly planning.
- Both directions require provenance, safety checks, tool-availability reporting, and fallback behavior before any deeper implementation.

## CRISPR Capability Staging

CRISPR support should grow in stages:

1. Level 0: no CRISPR-specific representation.
2. Level 1: CRISPR intent only, with no guide design.
3. Level 2: CRISPR feasibility checks for host, Cas system, target availability, tool availability, and safety boundary status.
4. Level 3: optional adapter integration for tools such as Cas-OFFinder, BLAST+, or Bowtie.
5. Level 4: controlled guide-level design only after safety, provenance, adapter, and validation foundations are stable.

Preferred upgrade path:

```text
intent -> feasibility -> validated candidate -> sequence-level design
```

## Multicellular Consortia Capability Staging

Consortia logic support should grow in stages:

1. Level 0: single-context logic.
2. Level 1: abstract `cell_context` partitioning.
3. Level 2: host and chassis assumptions.
4. Level 3: abstract inter-cell communication model.
5. Level 4: burden, population ratio, and dynamics evaluation.
6. Level 5: optional tool-backed validation.
7. Level 6: controlled strain-level planning only after safety, provenance, host, communication, burden, and validation foundations are stable.

Future PM Agent integration:

- PM Agent may detect when consortia partitioning is relevant.
- PM Agent may create subtasks for partitioning, host review, communication review, burden review, safety review, and Critic review.
- PM Agent must check the dependency gate before allowing implementation work.
- Early PM Agent output should remain planning and review coordination, not strain-level build instructions.

Preferred upgrade path:

```text
cell_context partition -> host assumptions -> communication model -> dynamics and burden checks -> tool-backed validation -> controlled strain-level planning
```
