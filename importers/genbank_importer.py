from __future__ import annotations

import re

from schemas.import_draft import DraftPart, FieldEvidence, ImportDraft


SUPPORTED_FEATURES = {
    "promoter": "promoter",
    "rbs": "RBS",
    "cds": "CDS",
    "terminator": "terminator",
    "regulatory": "regulator",
}


def genbank_to_import_draft(
    value: str | bytes,
    *,
    filename: str = "external_design.gb",
) -> ImportDraft:
    text = value.decode("utf-8-sig", errors="replace") if isinstance(value, bytes) else value
    if "LOCUS" not in text or "ORIGIN" not in text:
        raise ValueError("The file does not look like a GenBank flat file.")

    locus = _first_match(text, r"^LOCUS\s+(\S+)", re.MULTILINE) or filename
    organism = _first_match(text, r"^\s+ORGANISM\s+(.+)$", re.MULTILINE)
    source = _first_match(text, r"^SOURCE\s+(.+)$", re.MULTILINE)
    sequence = _extract_sequence(text)
    parts = _extract_parts(text, sequence)
    citation = _extract_reference(text)

    return ImportDraft(
        draft_id=f"genbank_{_slug(locus)}",
        name=locus,
        source_type="GenBank",
        citation=citation,
        host_organism=organism or source or "not_reported",
        inputs=[],
        outputs=[],
        logic_expression="",
        validation_status="not_reported",
        validation_notes=(
            "Imported from a GenBank flat file. Experimental validation and circuit "
            "logic require user confirmation."
        ),
        parts=parts,
        notes=f"Imported from {filename}.",
        evidence=[
            FieldEvidence(
                field_path="sequence_record",
                status="explicit",
                locator=f"GenBank record {locus}",
                note="Sequence and feature annotations were read from the uploaded file.",
            )
        ],
    )


def _extract_parts(text: str, sequence: str) -> list[DraftPart]:
    features_block = text.split("FEATURES", 1)[1].split("ORIGIN", 1)[0]
    feature_pattern = re.compile(
        r"^\s{5}(\S+)\s+([^\n]+)\n((?:\s{21}/[^\n]*(?:\n\s{21,}[^\n/]*)*\n?)*)",
        re.MULTILINE,
    )
    parts = []
    used_ids: set[str] = set()
    for index, match in enumerate(feature_pattern.finditer(features_block), start=1):
        raw_type, location, qualifier_block = match.groups()
        part_type = SUPPORTED_FEATURES.get(raw_type.lower())
        if part_type is None:
            continue
        qualifiers = _parse_qualifiers(qualifier_block)
        name = (
            qualifiers.get("label")
            or qualifiers.get("gene")
            or qualifiers.get("product")
            or f"{part_type}_{index}"
        )
        part_id = _unique_id(_slug(name) or f"part_{index}", used_ids)
        start, end = _location_bounds(location)
        part_sequence = (
            sequence[start - 1 : end]
            if sequence and start is not None and end is not None and end <= len(sequence)
            else None
        )
        parts.append(
            DraftPart(
                id=part_id,
                name=name,
                part_type=part_type,
                role=qualifiers.get("note") or qualifiers.get("product") or "",
                sequence=part_sequence,
                evidence=FieldEvidence(
                    field_path=f"parts.{part_id}",
                    status="explicit",
                    locator=f"FEATURES {raw_type} {location.strip()}",
                    note="Imported from a GenBank feature annotation.",
                ),
            )
        )
    return parts


def _parse_qualifiers(block: str) -> dict[str, str]:
    qualifiers: dict[str, str] = {}
    for key, quoted, plain in re.findall(
        r"/([A-Za-z0-9_]+)=(?:\"([^\"]*)\"|([^\s]+))",
        block,
    ):
        qualifiers[key.lower()] = (quoted or plain).strip()
    return qualifiers


def _extract_sequence(text: str) -> str:
    origin = text.split("ORIGIN", 1)[1].split("//", 1)[0]
    return "".join(re.findall(r"[A-Za-z]+", re.sub(r"^\s*\d+", "", origin, flags=re.MULTILINE))).upper()


def _location_bounds(location: str) -> tuple[int | None, int | None]:
    numbers = [int(value) for value in re.findall(r"\d+", location)]
    if not numbers:
        return None, None
    return min(numbers), max(numbers)


def _extract_reference(text: str) -> str:
    title = _first_match(text, r"^\s+TITLE\s+(.+)$", re.MULTILINE)
    journal = _first_match(text, r"^\s+JOURNAL\s+(.+)$", re.MULTILINE)
    return ". ".join(item for item in (title, journal) if item)


def _first_match(text: str, pattern: str, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _unique_id(base: str, used: set[str]) -> str:
    candidate = base
    index = 2
    while candidate in used:
        candidate = f"{base}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower()
