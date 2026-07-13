# Evidence-Aware Genetic Circuit Design Research Prototype

AI systems can generate fluent genetic-circuit descriptions, but fluency is not
evidence of logical consistency, biological plausibility, buildability, or
experimental function.

This repository explores a working hypothesis:

> AI-assisted biological design should be treated as an evidence-aware
> evaluation process, not only as a generation task.

The current prototype translates regulatory-logic intent into computational
candidates, subjects them to deterministic checks and simplified models,
records missing evidence, and routes weak candidates toward critique or
revision. It is an exploratory, AI-assisted implementation of that idea—not a
virtual cell, a complete biological CAD platform, or an experimentally
validated circuit-design system.

## The Problem

Natural-language and LLM-generated biological designs can be persuasive while
silently crossing several abstraction boundaries:

- a coherent sentence is not a valid logic specification;
- valid Verilog is not a biological part assignment;
- a mapped or exported representation is not a buildable construct;
- a completed simulation is not calibrated in vivo prediction;
- a high heuristic score is not experimental evidence.

The project asks how a design workflow can preserve user intent while making
these boundaries, assumptions, failure modes, and next evidence requirements
visible.

## Working Hypothesis

A useful AI-assisted scientific workflow should combine generative components
with deterministic checks, explicit evidence classes, provenance, and honest
failure states. Its output should be a reviewable candidate and an account of
what supports it—not a confident-looking final answer.

This prototype therefore separates:

- LLM-dependent interpretation, proposal, translation, and critique;
- deterministic logic, schema, sequence, simulation, and export checks;
- mock, failed, and external Cello outcomes;
- computational scores from assembly and experimental readiness;
- available evidence from missing or inapplicable evidence.

## What the Prototype Tests

Given a request such as:

```text
Activate GFP only when input A is present and input B is absent.
```

the workflow can produce and inspect:

- a structured interpretation and truth-table expectation;
- Boolean logic and Cello-compatible combinational Verilog;
- explicit mock-versus-external Cello provenance;
- simplified resource-aware ODE, stochastic, temporal, and perturbation paths;
- versioned heuristic scoring and staged readiness reports;
- Critic feedback and repair provenance;
- sequence, host, assembly, BOM, GenBank, and SBOL3 planning artifacts when
  required evidence is available.

The implementation is a test bed for asking whether those layers can make
uncertainty and unsupported assumptions easier to inspect.

## Current Evidence

The repository includes deterministic regression coverage, versioned scoring
profiles, content-addressed benchmark metadata, explicit claim-boundary
policies, and a sanitized public snapshot for the fixed Case 01 demonstration.

- [Case 01 public evidence](docs/evidence/case_01/README.md)
- [Demo summary](demo_cases/DEMO_SUMMARY.md)
- [Evaluation metrics](docs/evaluation_metrics.md)
- [Model assumptions](docs/model_assumptions.md)
- [MVP verification plan and execution record](docs/developer/MVP_TEST_PLAN.md)

The bundled `research_smoke_v1` benchmark contains synthetic infrastructure
fixtures, not measured circuits. Current evidence supports software and
computational-screening claims only.

## Evidence and Biological Boundaries

The project can support:

- computational representation of regulatory-logic intent;
- logic and syntax consistency checks;
- comparisons under named computational assumptions;
- identification of missing evidence and likely failure modes;
- conservative sequence, host, assembly, and exchange-format review paths.

It cannot currently claim:

- experimentally validated genetic logic gates;
- guaranteed biological buildability or complete plasmid design;
- calibrated in vivo expression prediction;
- reliable host compatibility, biosafety, or regulatory compliance;
- automatic selection of characterized parts without supplied evidence;
- wet-lab-ready primers, protocols, or expert approval.

The detailed claim policy is in [Project Limitations](docs/limitations.md).

## Implemented Preview Surface

| Area | Reviewable computational path | Evidence boundary |
| --- | --- | --- |
| Design intake | Natural-language elicitation, structured specifications, imports, revisions, comparisons, replacement checks | Generated or imported records require review |
| Circuit execution | Synchronous and persistent runs, events, feedback/resume, artifacts, monitoring | Run completion does not imply biological validity |
| Simulation | Resource-aware ODE, temporal inputs, sweeps, simplified bifurcation reports, perturbation, bounded SSA, retroactivity, operon and RBS heuristics | Models are simplified and mostly uncalibrated |
| Evaluation and repair | Versioned profiles, datasets, readiness domains, Critic routing, constrained repair provenance | Scores rank implemented checks; they are not probabilities |
| Sequence and host | Sequence QC, synonymous revisions, CAI/rare-codon reporting, host profiles and ranking | Expression and compatibility are not guaranteed |
| Assembly and exchange | Backbone registry, planning, deliverable packages, BOM, GenBank, SBOL3 | Planning and exchange artifacts are not protocols |
| Interfaces | FastAPI/OpenAPI, HTML workspace, MCP tools, maintenance-only Streamlit UI | Optional external services may be unavailable |

## Research Direction: Multi-Layer Resource Accounting

One future direction is a layered mathematical representation across the
central-dogma information flow:

```text
DNA copy-number and promoter context
  -> transcriptional demand and RNAP allocation
  -> RNA production, accessibility, and degradation
  -> translational demand and ribosome allocation
  -> protein maturation and degradation
  -> circuit output, burden, and growth-dilution feedback
```

The goal is not to reproduce a real cell or construct a whole-cell digital
twin. The model would provide a diagnostic lens for identifying assumed
resource bottlenecks, comparing candidates under explicit assumptions,
exposing missing parameters, and recommending the next evidence needed for a
stronger interpretation.

See the [future roadmap](docs/future_roadmap.md) for this and other open research
questions.

## Workflow Snapshot

```text
Natural-language intent
  -> structured specification
  -> candidate logic and Verilog
  -> external-or-mock Cello boundary
  -> data and parameter attachment
  -> simplified simulation and evaluation
  -> critique, repair, or consolidation
  -> reviewable artifacts plus explicit limitations
```

The main orchestration path is
[`src/workflows/reflexion_controller.py`](src/workflows/reflexion_controller.py).

## Read This Repository by Interest

Different readers need different evidence first. The audience guides change
emphasis and reading order, but never change the underlying claim boundaries.

| Interest | Start here |
| --- | --- |
| Synthetic biology or wet lab | [Synthetic biology guide](docs/audiences/synthetic_biology.md) |
| Mathematical or systems modeling | [Mathematical modeling guide](docs/audiences/mathematical_modeling.md) |
| AI4Science or agent systems | [AI4Science and agents guide](docs/audiences/ai4science_agents.md) |
| Bio-CAD, APIs, or interoperability | [Bio-CAD and interoperability guide](docs/audiences/bio_cad_interoperability.md) |
| Potential collaborators or reviewers | [Collaboration and review guide](docs/audiences/potential_collaborators.md) |

AI assistants should begin with [`llms.txt`](llms.txt), which provides the same
audience-aware routing while preserving a universal project identity.

## Repository Guide

| File | Purpose |
| --- | --- |
| [Quickstart](QUICKSTART.md) | Install, test, and run the local interfaces |
| [Limitations](docs/limitations.md) | Safe claims, non-goals, evidence requirements |
| [Architecture](docs/architecture.md) | Components and responsibilities |
| [Workflow](docs/workflow.md) | Execution, repair, mock, and fallback behavior |
| [Model assumptions](docs/model_assumptions.md) | Equations, parameters, and missing mechanisms |
| [Evaluation metrics](docs/evaluation_metrics.md) | Scores, versions, and interpretation |
| [AI reviewer guide](docs/ai_reviewer_guide.md) | Repository review protocol |
| [Evidence capture guide (Traditional Chinese)](docs/evidence_capture_guide_zh-Hant.md) | Real-run screenshots, recording script, metadata, and claim boundaries |
| [Future roadmap](docs/future_roadmap.md) | Open research and engineering directions |

## Development Provenance

This repository should not be interpreted as a claim of solo implementation or
independent scientific validation. It is a concept-driven, AI-assisted research
prototype developed through iterative specification, generated and revised
code, deterministic tests, document review, and explicit claim-boundary work.

The appropriate basis for evaluating it is the clarity of the problem, the
inspectability of the implementation, the available evidence, and the honesty
of its unresolved questions—not an authorship narrative.
