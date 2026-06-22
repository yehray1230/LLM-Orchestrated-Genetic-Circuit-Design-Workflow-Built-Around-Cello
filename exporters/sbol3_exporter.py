from __future__ import annotations

import re
from urllib.parse import quote

from exporters.export_result import ExportResult
from exporters.sequence_utils import is_valid_iupac_dna
from schemas.design_ir import DesignIR


SBOL = "http://sbols.org/v3#"
SO_ROLES = {
    "promoter": "https://identifiers.org/SO:0000167",
    "rbs": "https://identifiers.org/SO:0000139",
    "cds": "https://identifiers.org/SO:0000316",
    "terminator": "https://identifiers.org/SO:0000141",
}
INTERACTION_TYPES = {
    "activation": "https://identifiers.org/SBO:0000170",
    "repression": "https://identifiers.org/SBO:0000169",
    "expression": "https://identifiers.org/SBO:0000589",
}
SOURCE_ROLES = {
    "activation": "https://identifiers.org/SBO:0000459",
    "repression": "https://identifiers.org/SBO:0000020",
    "expression": "https://identifiers.org/SBO:0000645",
}
TARGET_ROLES = {
    "activation": "https://identifiers.org/SBO:0000643",
    "repression": "https://identifiers.org/SBO:0000642",
    "expression": "https://identifiers.org/SBO:0000011",
}


def export_sbol3_turtle(
    design: DesignIR,
    *,
    namespace: str = "https://example.org/genetic-circuit/",
) -> ExportResult:
    base = namespace.rstrip("/") + "/"
    lines = [
        "@prefix sbol: <http://sbols.org/v3#> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        f"@base <{base}> .",
        "",
    ]
    warnings: list[str] = []
    part_map = {part.id: part for part in design.parts}
    design_feature_uris: dict[str, str] = {}

    design_uri = _uri(base, "design", design.design_id)
    lines.extend(
        _statement(
            design_uri,
            [
                ("a", "sbol:Component"),
                ("sbol:type", "<https://identifiers.org/SBO:0000251>"),
                ("sbol:name", _literal(design.name)),
                ("dcterms:identifier", _literal(design.design_id)),
                ("sbol:description", _literal(design.logic_expression)),
            ],
        )
    )

    for part in design.parts:
        part_uri = _uri(base, "part", part.id)
        design_feature_uri = _uri(base, "feature", f"{design.design_id}_{part.id}")
        design_feature_uris[part.id] = design_feature_uri
        predicates = [
            ("a", "sbol:Component"),
            ("sbol:type", "<https://identifiers.org/SBO:0000251>"),
            ("sbol:name", _literal(part.name)),
            ("dcterms:identifier", _literal(part.id)),
            ("sbol:description", _literal(part.role)),
        ]
        role = SO_ROLES.get(part.part_type.lower())
        if role:
            predicates.append(("sbol:role", f"<{role}>"))
        if part.sequence and is_valid_iupac_dna(part.sequence):
            sequence_uri = _uri(base, "sequence", part.id)
            predicates.append(("sbol:hasSequence", sequence_uri))
            lines.extend(_statement(part_uri, predicates))
            lines.extend(
                _statement(
                    sequence_uri,
                    [
                        ("a", "sbol:Sequence"),
                        ("sbol:elements", _literal(part.sequence.upper())),
                        (
                            "sbol:encoding",
                            "<https://identifiers.org/edam:format_1207>",
                        ),
                    ],
                )
            )
        else:
            if part.sequence:
                warnings.append(
                    f"Part {part.id} has a non-IUPAC sequence; SBOL component is exported without a Sequence."
                )
            else:
                warnings.append(f"Part {part.id} has no sequence; SBOL component is sequence-less.")
            lines.extend(_statement(part_uri, predicates))
        lines.extend(
            _statement(
                design_feature_uri,
                [
                    ("a", "sbol:SubComponent"),
                    ("sbol:instanceOf", part_uri),
                    ("sbol:displayId", _literal(f"{design.design_id}_{part.id}")),
                ],
            )
        )
        lines.extend(
            _statement(
                design_uri,
                [("sbol:hasFeature", design_feature_uri)],
            )
        )

    for construct in design.constructs:
        construct_uri = _uri(base, "construct", construct.id)
        construct_parts = [
            part_map[part_id]
            for part_id in construct.parts
            if part_id in part_map
        ]
        construct_complete = (
            len(construct_parts) == len(construct.parts)
            and all(
                part.sequence and is_valid_iupac_dna(part.sequence)
                for part in construct_parts
            )
        )
        predicates = [
            ("a", "sbol:Component"),
            ("sbol:type", "<https://identifiers.org/SBO:0000251>"),
            ("sbol:name", _literal(construct.name)),
            ("dcterms:identifier", _literal(construct.id)),
        ]
        if construct_complete:
            construct_sequence_uri = _uri(base, "sequence", construct.id)
            predicates.append(("sbol:hasSequence", construct_sequence_uri))
        lines.extend(_statement(construct_uri, predicates))
        if construct_complete:
            lines.extend(
                _statement(
                    construct_sequence_uri,
                    [
                        ("a", "sbol:Sequence"),
                        (
                            "sbol:elements",
                            _literal(
                                "".join(part.sequence or "" for part in construct_parts)
                            ),
                        ),
                        (
                            "sbol:encoding",
                            "<https://identifiers.org/edam:format_1207>",
                        ),
                    ],
                )
            )
        previous_feature_uri = None
        offset = 1
        for position, part_id in enumerate(construct.parts, start=1):
            if part_id not in part_map:
                warnings.append(f"Construct {construct.id} references missing part {part_id}.")
                continue
            feature_uri = _uri(base, "feature", f"{construct.id}_{position}_{part_id}")
            feature_predicates = [
                ("a", "sbol:SubComponent"),
                ("sbol:instanceOf", _uri(base, "part", part_id)),
                ("sbol:displayId", _literal(f"{construct.id}_{position}")),
            ]
            part = part_map[part_id]
            if construct_complete and part.sequence:
                location_uri = _uri(
                    base, "location", f"{construct.id}_{position}_{part_id}"
                )
                end = offset + len(part.sequence) - 1
                feature_predicates.append(("sbol:hasLocation", location_uri))
                lines.extend(
                    _statement(
                        location_uri,
                        [
                            ("a", "sbol:Range"),
                            ("sbol:start", f'"{offset}"^^xsd:integer'),
                            ("sbol:end", f'"{end}"^^xsd:integer'),
                            ("sbol:orientation", "sbol:inline"),
                            ("sbol:sequence", construct_sequence_uri),
                        ],
                    )
                )
                offset = end + 1
            lines.extend(
                _statement(
                    feature_uri,
                    feature_predicates,
                )
            )
            lines.extend(
                _statement(
                    construct_uri,
                    [("sbol:hasFeature", feature_uri)],
                )
            )
            if previous_feature_uri:
                constraint_uri = _uri(base, "constraint", f"{construct.id}_{position - 1}_{position}")
                lines.extend(
                    _statement(
                        constraint_uri,
                        [
                            ("a", "sbol:Constraint"),
                            ("sbol:subject", previous_feature_uri),
                            ("sbol:object", feature_uri),
                            ("sbol:restriction", "sbol:precedes"),
                        ],
                    )
                )
                lines.extend(
                    _statement(
                        construct_uri,
                        [("sbol:hasConstraint", constraint_uri)],
                    )
                )
            previous_feature_uri = feature_uri

    for interaction_index, interaction in enumerate(design.interactions, start=1):
        interaction_uri = _uri(base, "interaction", f"{design.design_id}_{interaction_index}")
        source_part_uri = design_feature_uris.get(
            interaction.source,
            _uri(base, "feature", f"{design.design_id}_{interaction.source}"),
        )
        target_part_uri = design_feature_uris.get(
            interaction.target,
            _uri(base, "feature", f"{design.design_id}_{interaction.target}"),
        )
        source_participation_uri = _uri(
            base, "participation", f"{design.design_id}_{interaction_index}_source"
        )
        target_participation_uri = _uri(
            base, "participation", f"{design.design_id}_{interaction_index}_target"
        )
        interaction_type = INTERACTION_TYPES.get(
            interaction.interaction_type,
            "https://identifiers.org/SBO:0000231",
        )
        lines.extend(
            _statement(
                interaction_uri,
                [
                    ("a", "sbol:Interaction"),
                    ("sbol:type", f"<{interaction_type}>"),
                    ("sbol:name", _literal(interaction.label or interaction.interaction_type)),
                    ("sbol:description", _literal(interaction.interaction_type)),
                    ("sbol:hasParticipation", source_participation_uri),
                    ("sbol:hasParticipation", target_participation_uri),
                ],
            )
        )
        lines.extend(
            _statement(
                design_uri,
                [("sbol:hasInteraction", interaction_uri)],
            )
        )
        lines.extend(
            _statement(
                source_participation_uri,
                [
                    ("a", "sbol:Participation"),
                    ("sbol:participant", source_part_uri),
                    (
                        "sbol:role",
                        f"<{SOURCE_ROLES.get(interaction.interaction_type, 'https://identifiers.org/SBO:0000003')}>",
                    ),
                ],
            )
        )
        lines.extend(
            _statement(
                target_participation_uri,
                [
                    ("a", "sbol:Participation"),
                    ("sbol:participant", target_part_uri),
                    (
                        "sbol:role",
                        f"<{TARGET_ROLES.get(interaction.interaction_type, 'https://identifiers.org/SBO:0000003')}>",
                    ),
                ],
            )
        )

    for provenance in design.provenance:
        provenance_uri = _uri(base, "activity", provenance.id)
        predicates = [
            ("a", "prov:Activity"),
            ("dcterms:identifier", _literal(provenance.id)),
        ]
        if provenance.generated_at:
            predicates.append(
                (
                    "prov:endedAtTime",
                    f'{_literal(provenance.generated_at)}^^xsd:dateTime',
                )
            )
        lines.extend(_statement(provenance_uri, predicates))

    content = "\n".join(lines).rstrip() + "\n"
    return ExportResult(
        ok=True,
        format="SBOL3 Turtle",
        filename=f"{_token(design.design_id)}_{_token(design.revision.revision_id)}.ttl",
        media_type="text/turtle",
        content=content,
        status="ready" if not warnings else "ready_with_warnings",
        warnings=list(dict.fromkeys(warnings)),
    )


def _statement(subject: str, predicates: list[tuple[str, str]]) -> list[str]:
    if not predicates:
        return []
    lines = [subject]
    for index, (predicate, value) in enumerate(predicates):
        ending = " ." if index == len(predicates) - 1 else " ;"
        lines.append(f"    {predicate} {value}{ending}")
    lines.append("")
    return lines


def _uri(base: str, category: str, identifier: str) -> str:
    return f"<{base}{quote(category)}/{quote(_token(identifier))}>"


def _literal(value: str) -> str:
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def _token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]", "_", str(value))
    return token.strip("_") or "design"
