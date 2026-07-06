from __future__ import annotations

import csv
from io import StringIO

from exporters.export_result import ExportResult
from schemas.design_ir import DesignIR


BOM_COLUMNS = [
    "design_id",
    "revision_id",
    "construct_id",
    "construct_name",
    "position",
    "part_id",
    "assigned_part_id",
    "part_name",
    "part_type",
    "sequence_status",
    "sequence_length_bp",
    "source",
    "library_id",
    "confidence",
    "host_compatibility",
    "role",
    "evidence_source",
]


def export_bom_csv(design: DesignIR) -> ExportResult:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=BOM_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    part_map = {part.id: part for part in design.parts}
    warnings: list[str] = []

    for construct in design.constructs:
        for position, part_id in enumerate(construct.parts, start=1):
            part = part_map.get(part_id)
            if part is None:
                warnings.append(
                    f"Construct {construct.id} references missing part {part_id}."
                )
                writer.writerow(
                    {
                        "design_id": design.design_id,
                        "revision_id": design.revision.revision_id,
                        "construct_id": construct.id,
                        "construct_name": construct.name,
                        "position": position,
                        "part_id": part_id,
                        "sequence_status": "missing_part",
                    }
                )
                continue
            assignment = part.assignment
            writer.writerow(
                {
                    "design_id": design.design_id,
                    "revision_id": design.revision.revision_id,
                    "construct_id": construct.id,
                    "construct_name": construct.name,
                    "position": position,
                    "part_id": part.id,
                    "assigned_part_id": assignment.part_id if assignment else "",
                    "part_name": part.name,
                    "part_type": part.part_type,
                    "sequence_status": "available" if part.sequence else "missing",
                    "sequence_length_bp": len(part.sequence) if part.sequence else 0,
                    "source": part.source,
                    "library_id": assignment.library_id if assignment else "",
                    "confidence": part.confidence,
                    "host_compatibility": "|".join(part.host_compatibility),
                    "role": part.role,
                    "evidence_source": assignment.evidence_source if assignment else "",
                }
            )

    if not design.constructs:
        warnings.append("Design has no constructs; BOM contains only the header.")
    filename = f"{_filename_token(design.design_id)}_{_filename_token(design.revision.revision_id)}_bom.csv"
    return ExportResult(
        ok=True,
        format="BOM CSV",
        filename=filename,
        media_type="text/csv",
        content=output.getvalue(),
        status="ready" if not warnings else "ready_with_warnings",
        warnings=warnings,
    )


def _filename_token(value: str) -> str:
    token = "".join(character if character.isalnum() or character in "-_" else "_" for character in value)
    return token.strip("_") or "design"

