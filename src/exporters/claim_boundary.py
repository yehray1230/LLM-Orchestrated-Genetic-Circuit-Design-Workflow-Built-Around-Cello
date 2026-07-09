from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


CLAIM_BOUNDARY_VERSION = "2026-07-09"
EXCHANGE_EXPORT_FORMATS = {"bom", "genbank", "sbol3"}
CLAIM_BOUNDARY_TEXT = (
    "Computational exchange artifact only. This file is not wet-lab validation, "
    "does not establish biological function, and is not an experimental protocol. "
    "Review sequence completeness, host assumptions, model limitations, and "
    "biophysical uncertainty before any laboratory planning."
)
BIOPHYSICAL_UNCERTAINTIES = [
    "Uncalibrated model parameters may not match the selected host or growth condition.",
    "ODE/SSA outputs are computational screening evidence, not measured expression.",
    "Sequence completeness and part annotations require independent review.",
    "Assembly or readiness outputs do not provide executable wet-lab protocol steps.",
]


def is_exchange_export_format(export_format: str) -> bool:
    return export_format.lower() in EXCHANGE_EXPORT_FORMATS


def claim_boundary_payload(
    *,
    design_id: str | None = None,
    revision_id: str | None = None,
    revision_number: int | None = None,
    formats: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "claim_boundary_version": CLAIM_BOUNDARY_VERSION,
        "claim_boundary": CLAIM_BOUNDARY_TEXT,
        "biophysical_uncertainties": BIOPHYSICAL_UNCERTAINTIES,
        "not_wet_lab_validation": True,
        "not_experimental_protocol": True,
        "applies_to_formats": formats or sorted(EXCHANGE_EXPORT_FORMATS),
        "design_id": design_id,
        "revision_id": revision_id,
        "revision_number": revision_number,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def claim_boundary_markdown(payload: dict[str, Any] | None = None) -> str:
    selected = payload or claim_boundary_payload()
    lines = [
        "# Claim Boundary",
        "",
        selected["claim_boundary"],
        "",
        "## Biophysical Uncertainties",
        "",
    ]
    lines.extend(f"- {item}" for item in selected["biophysical_uncertainties"])
    lines.extend(
        [
            "",
            "## Scope",
            "",
            f"- Applies to formats: `{', '.join(selected['applies_to_formats'])}`",
            f"- Not wet-lab validation: `{selected['not_wet_lab_validation']}`",
            f"- Not an experimental protocol: `{selected['not_experimental_protocol']}`",
        ]
    )
    if selected.get("design_id"):
        lines.append(f"- Design ID: `{selected['design_id']}`")
    if selected.get("revision_id"):
        lines.append(f"- Revision ID: `{selected['revision_id']}`")
    if selected.get("revision_number") is not None:
        lines.append(f"- Revision number: `{selected['revision_number']}`")
    return "\n".join(lines) + "\n"


def claim_boundary_json(payload: dict[str, Any] | None = None) -> str:
    return json.dumps(payload or claim_boundary_payload(), indent=2, ensure_ascii=False)


def claim_boundary_headers() -> dict[str, str]:
    return {
        "X-Claim-Boundary": "computational-exchange-artifact-only",
        "X-Not-Wet-Lab-Validation": "true",
        "X-Not-Experimental-Protocol": "true",
        "X-Biophysical-Uncertainty": "requires-review",
        "X-Claim-Boundary-Version": CLAIM_BOUNDARY_VERSION,
    }
