from __future__ import annotations

from typing import Any

from schemas.design_ir_v2 import DesignIRV2, PlasmidV2
from exporters.plasmid_tools import AssemblyIssue
from exporters.sequence_utils import normalize_dna


LAYOUT_ISSUE_SCHEMA_VERSION = "1.0.0"


def layout_issue_to_dict(issue: AssemblyIssue) -> dict[str, Any]:
    return {
        "schema_version": LAYOUT_ISSUE_SCHEMA_VERSION,
        "code": issue.code,
        "severity": issue.severity,
        "subject_id": issue.subject_id,
        "message": issue.message,
    }


def layout_issues_report(
    design: DesignIRV2,
    plasmid: PlasmidV2,
) -> dict[str, Any]:
    issues = analyze_layout_issues(design, plasmid)
    return {
        "report_type": "layout_critic_report",
        "schema_version": LAYOUT_ISSUE_SCHEMA_VERSION,
        "design_id": design.design_id,
        "plasmid_id": plasmid.id,
        "issue_count": len(issues),
        "issues": [layout_issue_to_dict(issue) for issue in issues],
    }


def analyze_layout_issues(
    design: DesignIRV2,
    plasmid: PlasmidV2,
) -> list[AssemblyIssue]:
    issues: list[AssemblyIssue] = []
    
    part_map = {part.id: part for part in design.parts}
    construct_map = {c.id: c for c in design.constructs}
    
    for construct_id in plasmid.construct_ids:
        construct = construct_map.get(construct_id)
        if not construct:
            continue
            
        # Build ordered list of instances with sequence information
        ordered_instances = sorted(construct.part_instances, key=lambda x: x.order)
        parts_in_layout = []
        current_offset = 0
        
        for inst in ordered_instances:
            part = part_map.get(inst.part_id)
            if not part:
                continue
            seq = normalize_dna(part.sequence) or ""
            seq_len = len(seq)
            parts_in_layout.append({
                "instance": inst,
                "part": part,
                "start": current_offset,
                "end": current_offset + seq_len,
                "length": seq_len,
                "orientation": inst.orientation.lower(),
                "role": part.part_type.lower()
            })
            current_offset += seq_len
            
        n = len(parts_in_layout)
        
        # 1. Forward strand walk for active transcription units (TUs)
        in_forward_tu = False
        has_forward_cds = False
        promoter_id = None
        for i in range(n):
            p = parts_in_layout[i]
            if p["orientation"] == "forward":
                if p["role"] == "promoter":
                    if in_forward_tu and has_forward_cds:
                        issues.append(AssemblyIssue(
                            code="READ_THROUGH_RISK",
                            message=(
                                f"Read-through risk: Promoter '{p['part'].id}' is downstream "
                                f"of active transcription unit starting at '{promoter_id}' "
                                f"without an intervening terminator."
                            ),
                            subject_id=p["part"].id,
                            severity="warning"
                        ))
                    in_forward_tu = True
                    has_forward_cds = False
                    promoter_id = p["part"].id
                elif p["role"] == "cds" and in_forward_tu:
                    has_forward_cds = True
                elif p["role"] == "terminator" and in_forward_tu:
                    in_forward_tu = False
                    has_forward_cds = False
                    
        if in_forward_tu and has_forward_cds:
            issues.append(AssemblyIssue(
                code="MISSING_TERMINATOR",
                message=(
                    f"Missing terminator: active transcription unit starting at "
                    f"promoter '{promoter_id}' reaches the end of the construct without a terminator."
                ),
                subject_id=promoter_id,
                severity="warning"
            ))
            
        # 2. Reverse strand walk for active transcription units (TUs)
        in_reverse_tu = False
        has_reverse_cds = False
        promoter_id = None
        for i in range(n - 1, -1, -1):
            p = parts_in_layout[i]
            if p["orientation"] == "reverse":
                if p["role"] == "promoter":
                    if in_reverse_tu and has_reverse_cds:
                        issues.append(AssemblyIssue(
                            code="READ_THROUGH_RISK",
                            message=(
                                f"Read-through risk: Promoter '{p['part'].id}' is downstream "
                                f"(in reverse) of active transcription unit starting at '{promoter_id}' "
                                f"without an intervening terminator."
                            ),
                            subject_id=p["part"].id,
                            severity="warning"
                        ))
                    in_reverse_tu = True
                    has_reverse_cds = False
                    promoter_id = p["part"].id
                elif p["role"] == "cds" and in_reverse_tu:
                    has_reverse_cds = True
                elif p["role"] == "terminator" and in_reverse_tu:
                    in_reverse_tu = False
                    has_reverse_cds = False
                    
        if in_reverse_tu and has_reverse_cds:
            issues.append(AssemblyIssue(
                code="MISSING_TERMINATOR",
                message=(
                    f"Missing terminator: active transcription unit starting at reverse "
                    f"promoter '{promoter_id}' reaches the start of the construct without a terminator."
                ),
                subject_id=promoter_id,
                severity="warning"
            ))
            
        # 3. Promoter and RBS upstream check for CDS
        for i in range(n):
            p = parts_in_layout[i]
            if p["role"] == "cds":
                if p["orientation"] == "forward":
                    has_prom = False
                    has_rbs = False
                    for j in range(i - 1, -1, -1):
                        up = parts_in_layout[j]
                        if up["orientation"] == "forward":
                            if up["role"] == "rbs":
                                has_rbs = True
                            elif up["role"] == "promoter":
                                has_prom = True
                                break
                    if not has_prom:
                        issues.append(AssemblyIssue(
                            code="MISSING_PROMOTER",
                            message=f"CDS '{p['part'].id}' has no upstream forward promoter.",
                            subject_id=p["part"].id,
                            severity="warning"
                        ))
                    elif not has_rbs:
                        issues.append(AssemblyIssue(
                            code="MISSING_RBS",
                            message=f"CDS '{p['part'].id}' has no forward RBS between its promoter and coding sequence.",
                            subject_id=p["part"].id,
                            severity="warning"
                        ))
                elif p["orientation"] == "reverse":
                    has_prom = False
                    has_rbs = False
                    for j in range(i + 1, n):
                        down = parts_in_layout[j]
                        if down["orientation"] == "reverse":
                            if down["role"] == "rbs":
                                has_rbs = True
                            elif down["role"] == "promoter":
                                has_prom = True
                                break
                    if not has_prom:
                        issues.append(AssemblyIssue(
                            code="MISSING_PROMOTER",
                            message=f"CDS '{p['part'].id}' has no upstream reverse promoter.",
                            subject_id=p["part"].id,
                            severity="warning"
                        ))
                    elif not has_rbs:
                        issues.append(AssemblyIssue(
                            code="MISSING_RBS",
                            message=f"CDS '{p['part'].id}' has no reverse RBS between its promoter and coding sequence.",
                            subject_id=p["part"].id,
                            severity="warning"
                        ))
                        
        # 4. Spacing checks for divergent promoters
        for i in range(n - 1):
            p1 = parts_in_layout[i]
            p2 = parts_in_layout[i + 1]
            if p1["role"] == "promoter" and p2["role"] == "promoter":
                if p1["orientation"] == "reverse" and p2["orientation"] == "forward":
                    spacing = p2["start"] - p1["end"]
                    if spacing < 50:
                        issues.append(AssemblyIssue(
                            code="PROMOTER_INTERFERENCE",
                            message=(
                                f"Promoter interference: Divergent promoters '{p1['part'].id}' "
                                f"and '{p2['part'].id}' have spacing of only {spacing} bp "
                                f"(recommended >= 50 bp)."
                            ),
                            subject_id=p1["part"].id,
                            severity="warning"
                        ))
                        
        # 5. Convergent collision check (CDS without terminator between them)
        for i in range(n):
            p1 = parts_in_layout[i]
            if p1["role"] == "cds" and p1["orientation"] == "forward":
                for j in range(i + 1, n):
                    p2 = parts_in_layout[j]
                    if p2["role"] == "cds" and p2["orientation"] == "reverse":
                        has_term = False
                        for k in range(i + 1, j):
                            mid = parts_in_layout[k]
                            if mid["role"] == "terminator":
                                has_term = True
                                break
                        if not has_term:
                            issues.append(AssemblyIssue(
                                code="CONVERGENT_COLLISION_RISK",
                                message=(
                                    f"Convergent collision risk: Forward CDS '{p1['part'].id}' "
                                    f"and reverse CDS '{p2['part'].id}' transcribe towards each other "
                                    f"without a terminator in between."
                                ),
                                subject_id=p1["part"].id,
                                severity="warning"
                            ))
                        break

    return issues
