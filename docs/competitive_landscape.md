# Positioning and Comparison Landscape

Last reviewed: 2026-07-14

## Purpose and Comparison Boundary

This document explains the project's positioning relative to Cello and CELLM.
It compares public emphasis and reviewable artifacts; it is not a complete
feature audit, performance benchmark, or claim that another system lacks a
capability that its reviewed public materials do not discuss.

Cello is also an upstream design-automation system used by this project, not
merely a competitor. CELLM is the closer adjacent comparison because it adds
natural-language and LLM-based interaction around Cello.

## Public Positioning Comparison

| System | Publicly emphasized role | Relationship to this project | Safe interpretation |
| --- | --- | --- | --- |
| Cello | Converts a high-level Verilog logic specification into an abstract Boolean network, assigns characterized biological gates, constructs DNA sequences, and predicts circuit performance. | Upstream CAD and mapping foundation. | Cello is the stronger reference point for circuit synthesis and experimentally grounded gate libraries; this prototype does not claim to outperform it. |
| CELLM | Combines Cello with LLMs and LangChain so users can create, analyze, and optimize genetic circuits from natural-language instructions. | Closest adjacent natural-language comparison. | Natural-language access and LLM-assisted orchestration are not sufficient differentiation by themselves. |
| This prototype | Translates regulatory intent into candidates and evaluates them across deterministic, heuristic, and simplified-model paths. It additionally attaches an E-BOM and deterministic claim/license decisions to public evidence. | Evidence-governance and review layer around candidate generation and evaluation. | The defensible claim is improved inspectability of what may be said about an output—not superior biological performance or experimental validation. |

## Differentiation Dimensions

| Dimension | Cello | CELLM | This prototype |
| --- | --- | --- | --- |
| Natural-language entry | Not the primary interface described in the reviewed Cello sources. | Core public contribution. | Implemented as an entry layer, but not claimed as unique. |
| Circuit synthesis | Core capability using logic synthesis, characterized gates, constraints, and performance prediction. | Uses Cello as the synthesis basis. | Delegates real mapping to external Cello or records mock/failed/not-run status explicitly. |
| Claim-to-evidence manifest | Not established by the reviewed public sources. | Not established by the reviewed abstract and supporting-information description. | Machine-readable `evidence-bom@1.0.0` manifest in the public Case 01 snapshot. |
| Deterministic claim states | Not established by the reviewed public sources. | Not established by the reviewed public sources. | `supported`, `limited`, `unsupported`, or `blocked`, with reason codes. |
| License-aware evidence decision | Cello code and external biological resources retain their own licenses and terms. | Not established as a claim-decision mechanism by the reviewed public sources. | Evidence rights metadata participates in a deterministic gate; unresolved or restricted rights can limit or block a claim. |
| Biological validation boundary | Published Cello work includes experimentally characterized gates and reported constructed circuits. | Must be interpreted within the evidence reported by the CELLM paper. | Current repository evidence supports computational-workflow and screening claims only; no wet-lab validation is claimed. |

“Not established” means only that the reviewed source did not provide enough
evidence for this comparison. It must not be rewritten as “does not exist.”

## Recommended Project Description

> An evidence-governed AI workflow for genetic-circuit design: every
> reportable claim can be linked to named evidence, biological context,
> provenance, and license status, then deterministically classified as
> supported, limited, unsupported, or blocked.

Short form:

> Evidence-governed candidate generation and evaluation for genetic-circuit
> design.

The licensing component should be described as **license-aware evidence
provenance**, not “evidence licensing.” It records rights and controls claim
eligibility; it does not relicense third-party material or guarantee legal
compliance.

## Claims to Avoid

- “More trustworthy than Cello or CELLM” without a comparative user study or
  benchmark.
- “Produces biologically valid” or “ready-to-build” circuits.
- “Solves hallucination.” The implemented checks expose selected inconsistency
  and evidence gaps; they do not eliminate model error.
- “License compliant” as an unconditional guarantee. Prefer “records rights
  metadata and gates unresolved or restricted evidence uses.”
- “First” or “unique” without a systematic and current literature review.
- Treating multi-agent orchestration as the central differentiator.

## Project Evidence

- [Evidence Governance and E-BOM Specification](evidence_governance_spec.md)
- [Case 01 public evidence](evidence/case_01/README.md)
- [Case 01 machine-readable E-BOM](evidence/case_01/evidence_manifest.json)
- [Project limitations](limitations.md)
- [Third-party notices and license boundaries](../THIRD_PARTY_NOTICES.md)

## External Sources Reviewed

- Jones et al., [Genetic circuit design automation with Cello 2.0](https://doi.org/10.1038/s41596-021-00675-2), *Nature Protocols* (2022).
- CIDAR Lab, [Cello source repository](https://github.com/CIDARLAB/cello).
- Abello Castillo and Gutiérrez Pescarmona, [CELLM: Bridging Natural Language Processing and Synthetic Genetic Circuit Design with AI](https://doi.org/10.1021/acssynbio.5c00391), *ACS Synthetic Biology* (2025).

Because software and research claims can change, recheck these sources before
using this comparison in outreach, a paper, or a release announcement.
