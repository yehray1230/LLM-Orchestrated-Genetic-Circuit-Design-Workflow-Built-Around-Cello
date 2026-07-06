# LLM-Orchestrated Genetic Circuit Design Workflow

This repository is a research prototype for translating natural-language
regulatory-logic intent into computational genetic-circuit design candidates.
It combines LLM-based agents, Cello-compatible logic translation, simplified
ODE simulation, benchmark scoring, and explicit limitation reporting.

Short version:

> The system generates, evaluates, and critiques computational candidate
> designs for regulatory logic circuits. It is not a complete plasmid-design
> platform and does not claim wet-lab validation.

## Project Status

Current stage: `0.x research preview`.

The project is suitable for:

- demonstrating a natural-language-to-circuit-design workflow;
- exploring multi-agent design, critique, and repair loops;
- producing traceable computational design artifacts;
- comparing candidates with simplified simulation and heuristic evaluation;
- discussing how AI-assisted design tools should expose biological uncertainty.

It should not be read as:

- a finished synthetic-biology CAD tool;
- a validated biological design platform;
- a replacement for Cello setup, expert review, or wet-lab characterization;
- evidence that generated circuits will work experimentally.

## What The System Does

Given a request such as:

```text
Activate GFP only when input A is present and input B is absent.
```

the workflow can produce and inspect:

- a structured interpretation of the design intent;
- Boolean logic and truth-table expectations;
- Cello-compatible combinational Verilog;
- optional Cello mapping metadata when an external Cello setup is configured;
- mock Cello topology output for workflow testing when Cello is not configured;
- simplified resource-aware ODE simulation outputs;
- benchmark and readiness-style scores;
- critique messages that identify weak logic, mapping, simulation, or evidence;
- export-oriented artifacts such as BOM CSV, GenBank, and SBOL3 representations
  when enough sequence evidence is available.

## Implemented Preview Capabilities

The repository currently contains these reviewable computational paths:

| Area | Implemented preview capability | Evidence boundary |
| --- | --- | --- |
| Design intake | Natural-language elicitation, structured specifications, guided JSON/GenBank imports, DesignIR revisions, comparisons, and part-replacement checks | Imported or generated records still require expert review |
| Circuit execution | Synchronous evaluation plus persistent asynchronous runs, progress events, feedback/resume, artifacts, and HTML run monitoring | Run completion does not imply biological validity |
| Simulation | Resource-aware ODE screening, temporal inputs, parameter sweeps, simplified bifurcation reports, Monte Carlo perturbation, stochastic SSA, retroactivity, operon coupling/polarity, and heuristic RBS-blocking warnings | Models are simplified and mostly uncalibrated |
| Evaluation and repair | Versioned scoring profiles, benchmark datasets, readiness domains, Critic routing, validated best-candidate self-healing, and repair provenance | Scores rank implemented checks; they are not success probabilities |
| Sequence and host | Sequence QC, synonymous E. coli codon revisions, CAI/rare-codon reporting, host profiles, host ranking, calibration snapshots, and optimization workflow orchestration | Host compatibility and expression are not experimentally guaranteed |
| Assembly and exchange | Backbone registry, plasmid/assembly planning, conservative deliverable packages, BOM, GenBank, and SBOL3 representations | Outputs are planning artifacts, not executable wet-lab protocols |
| Interfaces | FastAPI/OpenAPI, server-rendered research workspace, MCP tools, and legacy Streamlit interface (maintenance-only) | Optional external tools may fall back or remain unavailable |

The detailed contracts and caveats live in
[`WORKFLOW.md`](WORKFLOW.md), [`EVALUATION_METRICS.md`](EVALUATION_METRICS.md),
[`MODEL_ASSUMPTIONS.md`](MODEL_ASSUMPTIONS.md), and
[`LIMITATION.md`](LIMITATION.md).

## Biological Claim Boundary

The project can support computational design assistance:

- translating regulatory-logic intent into candidate circuit representations;
- checking logic consistency and Cello-compatible syntax;
- ranking candidates under implemented scoring assumptions;
- exposing uncertainty, missing evidence, and likely failure modes;
- evaluating sequence-level constraints when sequence data is available;
- generating conservative assembly or optimization proposals in supported paths.

The project cannot currently claim:

- experimentally validated genetic logic gates;
- guaranteed biological buildability;
- complete plasmid design from user intent alone;
- calibrated in vivo expression prediction;
- reliable host compatibility, biosafety, or regulatory compliance;
- automatic selection of experimentally characterized parts without supplied
  evidence;
- automatic wet-lab protocol generation or expert-ready experimental approval.

The safest presentation wording is:

> This is an LLM-orchestrated computational design-assistance workflow built
> around Cello that translates natural-language regulatory logic intent into
> candidate genetic-circuit representations, then ranks and critiques those
> candidates using simplified simulation and heuristic evaluation.

## Workflow Snapshot

```text
Natural-language intent
  -> PM agent structured specification
  -> Builder agent logic proposal
  -> Translator agent Cello-compatible Verilog
  -> Cello wrapper real-or-mock mapping boundary
  -> Data and parameter attachment
  -> ODE simulation and benchmark evaluation
  -> Critic-driven repair or consolidation
  -> Reviewable design artifacts and reports
```

The main orchestration path is implemented in
[`workflows/reflexion_controller.py`](workflows/reflexion_controller.py).

## Repository Guide

Start here:

| File | Purpose |
| --- | --- |
| [`README_FOR_AI.md`](README_FOR_AI.md) | AI-agent reading guide for quickly judging project scope, architecture, and fit. |
| [`QUICKSTART.md`](QUICKSTART.md) | How to install, test, and run the local demo interfaces. |
| [`DEMO_CHECKLIST.md`](DEMO_CHECKLIST.md) | Checklist for a stable reproducible demo. |
| [`demo_cases/DEMO_SUMMARY.md`](demo_cases/DEMO_SUMMARY.md) | Presentation-facing index for fixed demo cases. |
| [`LIMITATION.md`](LIMITATION.md) | Detailed current capabilities, non-goals, and safe claims. |
| [`MODEL_ASSUMPTIONS.md`](MODEL_ASSUMPTIONS.md) | ODE model scope, assumptions, and missing biological mechanisms. |
| [`EVALUATION_METRICS.md`](EVALUATION_METRICS.md) | Benchmark dimensions, scoring behavior, and interpretation. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System components and agent responsibilities. |
| [`WORKFLOW.md`](WORKFLOW.md) | Reflexion workflow details and execution flow. |
| [`future_roadmap.md`](future_roadmap.md) | Longer-term research directions beyond the current preview. |

Code areas:

| Path | Role |
| --- | --- |
| [`agents/`](agents) | PM, Builder, Translator, Critic, DataMiner, Consolidator, and SkillExtractor agents. |
| [`workflows/`](workflows) | Multi-agent orchestration and repair loop. |
| [`tools/`](tools) | Cello wrapper, ODE simulator, part library, sequence analysis, and related utilities. |
| [`benchmark_suite/`](benchmark_suite) | Candidate scoring, benchmark profiles, and evaluation reports. |
| [`schemas/`](schemas) | Design, simulation, readiness, sequence, and API data models. |
| [`api/`](api) | FastAPI routes and service entry points. |
| [`web/`](web) | HTML research workspace. |
| [`app.py`](app.py) | Legacy Streamlit interface (maintenance-only). |
| [`exporters/`](exporters) | BOM, GenBank, SBOL3, assembly, and report exporters. |
| [`tests/`](tests) | Regression and workflow tests. |

## Demo Positioning

For a short research conversation or cold email, present the project as a
working research prototype with explicit boundaries:

- It demonstrates an end-to-end computational workflow.
- It separates mock Cello output from externally mapped Cello output.
- It treats ODE and benchmark results as screening evidence, not biological
  proof.
- It makes missing evidence and next checks visible.
- It is designed to invite feedback from synthetic-biology and computational
  biology researchers.

## Future Work

The current preview already includes conservative SBOL3/GenBank representations,
host-profile screening, layout checks, heuristic RNA-folding warnings, and
resource-aware deterministic/stochastic simulation paths. These remain
computational screening features rather than experimentally validated models.

Future work focuses on benchmark calibration, wet-lab data fitting, validated
host-specific parameter sets, external thermodynamic/CRN tool integration,
richer spatial and biophysical models, and CRISPRi/CRISPRa-oriented extensions.

Those are future research directions. They should not be interpreted as current
validated capabilities. See [`future_roadmap.md`](future_roadmap.md).
