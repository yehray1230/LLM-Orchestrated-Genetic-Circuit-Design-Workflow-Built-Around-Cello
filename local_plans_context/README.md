# Local Plans Context

This folder is the `@`-able context entry point for the local planning work.

The detailed execution notes live in `local_plans_private/`, which remains ignored by Git so private implementation details, tentative decisions, experiment notes, and unpublished data boundaries do not get uploaded accidentally.

Use this folder when you want to mention the planning context inside Codex. It contains stable, non-sensitive summaries of the private plan structure.

## Private Source Folder

- Private source: `local_plans_private/`
- Public/context-safe summary folder: `local_plans_context/`
- Keep detailed implementation notes, cost notes, tentative model choices, and experiment results in `local_plans_private/`.
- Promote only stable, non-sensitive summaries into this folder.

## Recommended Execution Order

1. Phase 0: project audit and baseline.
2. Phase 6-lite: minimal evaluation harness, fixed prompts, run manifest, local outputs, comparison shell.
3. Phase 7-lite: minimum provenance, confidence, parameter origin, and local/private data boundary fields.
4. Phase 1: benchmark calibration and wet-lab-like data fitting.
5. Phase 2 core: host profiles, layout, temporal inputs, burden, and sensitivity foundation.
6. Phase 9-lite: optional-tool capability detection, adapter status, normalized warnings, and fallbacks.
7. Phase 2c: retroactivity and free-vs-total regulator modeling.
8. Phase 2d: operon and translational-coupling modeling.
9. Phase 2b: optional deep stochastic SSA audit for sequential logic.
10. Phase 3: academic standards, SBOL, GenBank, import/export, and sequence validation.
11. Phase 4: explainable critic and agent reasoning.
12. Phase 4b: scoring reconstruction and programmatic self-healing actions.
13. Phase 5: hybrid model orchestration and routed model comparison.
14. Phase 8: full biosafety, misuse boundary, and safety logging.
15. Phase 9 full: generalized plugin and extension architecture.
16. Phase 10: publication and case-study package.

## Tooling Principle

Before implementing a biological algorithm from scratch, check whether a mature tool can be wrapped behind a Phase 9 adapter.

Prefer adapters for:

- SBOL and GenBank validation.
- CRN and SBML simulation.
- RNA folding and RBS accessibility.
- DNA sequence optimization and constraint repair.
- DNA assembly simulation.
- Primer design.
- Plasmid and feature visualization.
- CRISPR off-target or homology screening.

## Implementation Skill

When starting any implementation task from these plans, apply this lightweight skill:

1. Identify the phase and early-slice dependency first.
2. Check whether Phase 6-lite run capture exists before changing scoring, simulation, agents, or model routing.
3. Check whether Phase 7-lite provenance fields exist before adding fitted, inferred, or literature-derived parameters.
4. Check the tool capability summary before implementing biology logic from scratch.
5. Keep heavyweight tools optional behind Phase 9 adapters.
6. Preserve the existing deterministic fallback path.
7. Add tests around the smallest observable behavior, not only the happy path.
8. Record new experiments, failures, and follow-up decisions in the private backlog or decision log.

## Common Pitfalls To Avoid

- Do not let optional dependencies such as `NUPACK`, `ViennaRNA`, `Tellurium`, `roadrunner`, `BioCRNpyler`, `Cas-OFFinder`, `BLAST+`, or `Bowtie` become required for the core app.
- Do not silently replace public/default biological parameters with fitted local values.
- Do not compare hybrid-model behavior without fixed prompts, captured run manifests, and baseline outputs.
- Do not accept Critic diagnostics that cannot map to structured evidence, a design location, or a repair action.
- Do not treat missing external tools as biological failures; report them as unavailable, skipped, or fallback-used.
- Do not promote private experiment data, cost notes, or tentative model choices into public files without sanitizing them.

## Start-Of-Task Checklist

- Which phase file is the source of truth?
- Does this task depend on `Phase 6-lite`, `Phase 7-lite`, or `Phase 9-lite`?
- Which existing module should be extended instead of adding a new abstraction?
- Which open-source tool or adapter already covers part of this capability?
- What is the fallback when the tool is unavailable?
- What output, warning, or metric proves the change worked?

## Completion Checklist

- Tests or a small reproducible command were run, or the reason they were not run is documented.
- New tool use records availability, version, fallback status, and warnings.
- New biological parameters include source and confidence.
- New scoring or simulation behavior can be captured by the Phase 6 manifest.
- Safety-sensitive sequence-level or off-target behavior remains behind explicit checks.
- Public/context files contain only stable, non-sensitive summaries.

## Current Tool Families

| Capability | Candidate Tools |
| :--- | :--- |
| Benchmark import and fitting | `pandas`, `lmfit`, `scipy` |
| Sequence parsing and GenBank IO | `Biopython` |
| SBOL validation | `pySBOL3` |
| CRN compilation | `BioCRNpyler` |
| ODE/SBML/stochastic simulation | `Tellurium`, `roadrunner`, `bioscrape`, existing ODE simulator |
| Sensitivity analysis | `SALib`, local parameter sweeps |
| RNA folding | `ViennaRNA`, optional license-gated `NUPACK`, heuristic fallback |
| Sequence optimization | `DNA Chisel`, existing sequence optimization helpers |
| Assembly simulation | `DNA Cauldron`, existing assembly planner |
| Cloning and primer workflows | `pydna`, `primer3-py` |
| Plasmid visualization | `dna-features-viewer`, existing topology views |
| CRISPR/off-target screening | `Cas-OFFinder`, local deterministic prechecks |
| Local homology screening | `BLAST+`, `Bowtie`, exact-match fallback |
| Logic synthesis baseline | Cello through existing wrapper |

## Safety Notes

- Treat `NUPACK` as optional licensed academic software, not a required open-source dependency.
- Treat `Cas-OFFinder` as a CLI/OpenCL integration with explicit binary and device detection.
- Treat `BLAST+` and `Bowtie` as local-database integrations; reference database identity and provenance must be captured.
- Core workflow behavior should continue to work without heavyweight optional tools.
