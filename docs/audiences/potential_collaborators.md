# Audience Guide: Potential Collaborators and Reviewers

## Why this audience may care

This repository offers a concrete object for discussing what evidence-aware
AI-assisted biological design should require. It is intended to invite scrutiny
of the problem, assumptions, evidence architecture, rights metadata, and
unresolved questions—not endorsement of a finished platform.

## The central research question

How can an AI-assisted design workflow preserve intent while carrying an
auditable claim envelope across generation, evaluation, and export—linking each
reportable statement to evidence, biological context, provenance, rights
status, and the next validation needed?

## What currently exists

- an inspectable multi-stage software prototype;
- deterministic and heuristic computational checks;
- explicit mock, external, missing, and blocked evidence states;
- versioned reports, provenance, and a fixed public evidence snapshot;
- a machine-readable Evidence Bill of Materials (E-BOM);
- deterministic claim and license gates with reviewable reason codes;
- documented biological and modeling limitations.

## What remains unresolved

- performance with real LLM providers across repeated tasks;
- external Cello mapping with compatible UCF/library data;
- calibration against measured reference circuits;
- whether the scoring and readiness language matches expert reasoning;
- whether multi-layer resource accounting improves diagnosis;
- how uncertainty should be presented to different users.
- whether rights metadata is expressive enough for UCFs, part libraries,
  sequence records, and experimental evidence without implying legal review.

## Contribution surfaces by expertise

- synthetic biology: biological failure modes and evidence thresholds for
  specific claims;
- mathematical modeling: equations, calibration, sensitivity, identifiability;
- AI4Science: claim calibration, abstention, and comparative baselines;
- Bio-CAD: E-BOM provenance, standards, APIs, and interoperability;
- human-computer interaction: safe presentation of uncertainty and readiness.
- open-source and data governance: rights vocabulary, attribution boundaries,
  and review workflows for external software and biological data.

## Start with these files

1. [README](../../README.md)
2. [Project limitations](../limitations.md)
3. [Evidence Governance and E-BOM Specification](../evidence_governance_spec.md)
4. [Public evidence](../evidence/case_01/README.md)
5. [Positioning and comparison landscape](../competitive_landscape.md)
6. The audience guide closest to the reviewer's expertise
7. [Future roadmap](../future_roadmap.md)

## Claims the assistant must not make

Do not present the repository as independently validated, complete, or seeking
endorsement. Do not imply solo implementation. Describe it as a concept-driven,
AI-assisted prototype whose value should be judged from its problem framing,
inspectable evidence, and open research questions.
