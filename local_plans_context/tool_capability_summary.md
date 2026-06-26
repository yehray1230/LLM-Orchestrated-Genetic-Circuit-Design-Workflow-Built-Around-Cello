# Tool Capability Summary

This is the short, context-safe version of `local_plans_private/tool_capability_matrix.md`.

## Adapter-First Capabilities

Use Phase 9 adapters for tool families that are useful but optional, heavyweight, platform-sensitive, or license-sensitive.

| Capability | Prefer Calling | Fallback |
| :--- | :--- | :--- |
| SBOL validation | `pySBOL3` | Export without full validation and warn. |
| GenBank parsing/export | `Biopython` | Existing project exporters/importers. |
| CRN compilation | `BioCRNpyler` | Existing deterministic ODE abstractions. |
| SBML simulation | `Tellurium`, `roadrunner` | Existing `tools/ode_simulator.py`. |
| CRN simulation fallback | `bioscrape` | Existing deterministic ODE simulator. |
| Sensitivity analysis | `SALib` | Local parameter sweeps. |
| RNA folding | `ViennaRNA` | Heuristic fallback. |
| RNA/DNA structure design | Optional `NUPACK` | `ViennaRNA` or heuristic fallback. |
| Sequence optimization | `DNA Chisel` | Existing sequence optimization helpers. |
| Assembly simulation | `DNA Cauldron` | Existing assembly planner. |
| Cloning workflows | `pydna` | Existing assembly deliverables. |
| Primer design | `primer3-py` | Existing primer designer. |
| Plasmid visualization | `dna-features-viewer` | Existing topology views. |
| CRISPR off-target screening | `Cas-OFFinder` | Deterministic local precheck. |
| Homology screening | `BLAST+`, `Bowtie` | Exact-match or simple local scan. |
| Logic synthesis baseline | Cello wrapper | Existing LLM/builder flow. |

## Manifest Requirements

Phase 6 run manifests should capture:

- Tool name and adapter name.
- Tool version.
- Capability requested.
- Availability status.
- Fallback status.
- License-sensitive status where relevant.
- Input artifact hash or stable identifier.
- Output artifact paths.
- Normalized warnings and errors.
