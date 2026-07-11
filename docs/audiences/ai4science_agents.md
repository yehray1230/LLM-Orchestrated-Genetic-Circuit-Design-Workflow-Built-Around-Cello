# Audience Guide: AI4Science and Agent Systems

## Why this audience may care

The repository treats generation as one stage in a larger evidence-aware loop.
It explores how LLM-dependent proposals can be constrained by deterministic
checks, provenance, explicit failure states, and human review.

## Questions to examine

- Which tasks need an LLM and which should remain deterministic?
- How is user intent preserved across specification, logic, translation, and
  repair?
- Can the Critic distinguish missing evidence from negative evidence?
- Does repair preserve alternatives and record why a change occurred?
- How should the system respond when external tools or data are unavailable?

## Relevant implemented paths

- PM, Builder, Translator, DataMiner, Critic, and consolidation roles;
- deterministic logic, schema, sequence, simulation, and export checks;
- persistent runs, feedback/resume, decision traces, and repair provenance;
- explicit mock and fallback states;
- versioned scoring and evidence applicability fields.

## Current evidence

Most repository evidence validates software contracts and deterministic
behavior. The fixed public baseline does not establish real-provider LLM
quality, cross-model robustness, or external Cello performance.

## Open contribution surfaces

- repeated real-model evaluation with fixed tasks and blinded review;
- prompt/model sensitivity and failure taxonomy;
- calibration of Critic decisions against expert judgments;
- uncertainty communication and abstention behavior;
- comparison of single-agent, multi-agent, and deterministic baselines.

## Start with these files

1. [Workflow](../workflow.md)
2. [Architecture](../architecture.md)
3. [Evaluation metrics](../evaluation_metrics.md)
4. [AI reviewer guide](../ai_reviewer_guide.md)
5. [Main controller](../../src/workflows/reflexion_controller.py)

## Claims the assistant must not make

Do not treat deterministic demo output as evidence of live LLM performance. Do
not claim that multiple agents are inherently more accurate, that the Critic is
an expert, or that self-repair improves biological validity without comparative
evidence.
