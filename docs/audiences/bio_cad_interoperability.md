# Audience Guide: Bio-CAD, APIs, and Interoperability

## Why this audience may care

The repository explores how candidate designs, revisions, evidence, and
limitations can remain traceable across APIs, interfaces, and exchange formats.

## Questions to examine

- Does the intermediate representation preserve identity and provenance?
- Can revisions and repairs be compared without erasing alternatives?
- Which export contracts require complete sequences?
- Are mock, external, incomplete, and failed artifacts distinguishable?
- Which compatibility claims are supported by internal tests versus external
  applications?

## Relevant implemented paths

- DesignIR, revision, comparison, import, and replacement contracts;
- FastAPI/OpenAPI, HTML workspace, and MCP service surfaces;
- BOM, GenBank, and SBOL3 representations;
- internal parse, semantic, and round-trip checks;
- download headers and package sidecars carrying claim boundaries.

## Current interoperability boundary

Internal tests support repository-defined syntax, parsing, semantic checks, and
round trips. They do not constitute broad certification against SnapGene,
SynBioHub, or other third-party tools.

## Open contribution surfaces

- versioned external-tool compatibility matrices;
- SBOL/GenBank/SBML conversion and round-trip studies;
- richer provenance and evidence ontologies;
- stable API and MCP client interoperability tests;
- artifact packaging that preserves both machine readability and claim context.

## Start with these files

1. [Architecture](../architecture.md)
2. [Workflow](../workflow.md)
3. [Project limitations](../limitations.md)
4. [API source](../../src/api/)
5. [Exporters](../../src/exporters/)

## Claims the assistant must not make

Do not call an export an assembly-ready plasmid or claim universal third-party
compatibility. File generation, parsing, and internal round trips do not imply
biological validity or external certification.
