# Audience Guide: Potential Collaborators and Reviewers

## Why this audience may care

This repository offers a concrete object for discussing what evidence-aware
AI-assisted biological design should require. It is intended to invite scrutiny
of the problem, assumptions, evidence architecture, and unresolved questions—not
endorsement of a finished platform.

## The central research question

How can an AI-assisted design workflow preserve intent, expose unsupported
assumptions, distinguish computational from experimental evidence, and identify
the next validation needed?

## What currently exists

- an inspectable multi-stage software prototype;
- deterministic and heuristic computational checks;
- explicit mock, external, missing, and blocked evidence states;
- versioned reports, provenance, and a fixed public evidence snapshot;
- documented biological and modeling limitations.

## What remains unresolved

- performance with real LLM providers across repeated tasks;
- external Cello mapping with compatible UCF/library data;
- calibration against measured reference circuits;
- whether the scoring and readiness language matches expert reasoning;
- whether multi-layer resource accounting improves diagnosis;
- how uncertainty should be presented to different users.

## Contribution surfaces by expertise

- synthetic biology: biological failure modes and experimental evidence;
- mathematical modeling: equations, calibration, sensitivity, identifiability;
- AI4Science: agent evaluation, abstention, and comparative baselines;
- Bio-CAD: provenance, standards, APIs, and interoperability;
- human-computer interaction: safe presentation of uncertainty and readiness.

## Start with these files

1. [README](../../README.md)
2. [Project limitations](../limitations.md)
3. [Public evidence](../evidence/case_01/README.md)
4. The audience guide closest to the reviewer's expertise
5. [Future roadmap](../future_roadmap.md)

## Claims the assistant must not make

Do not present the repository as independently validated, complete, or seeking
endorsement. Do not imply solo implementation. Describe it as a concept-driven,
AI-assisted prototype whose value should be judged from its problem framing,
inspectable evidence, and open research questions.
