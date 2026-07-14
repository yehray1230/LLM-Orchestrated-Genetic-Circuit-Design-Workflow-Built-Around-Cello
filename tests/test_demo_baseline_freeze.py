from __future__ import annotations

import json
from pathlib import Path

from application.demo_baseline import (
    DEMO_BASELINE_INTENT,
    run_demo_baseline_freeze,
)
from application.services import create_application_services
from schemas.evidence_governance import validate_evidence_manifest


def test_demo_baseline_freeze_generates_reproducible_packet(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")

    packet = run_demo_baseline_freeze(
        services,
        output_dir=tmp_path / "demo_baseline",
        timeout_seconds=30.0,
    )

    assert packet["intent"] == DEMO_BASELINE_INTENT
    assert packet["packet_hash"]
    assert packet["fixed_demo"]["truth_table"][2] == {"A": 1, "B": 0, "GFP": 1}
    assert packet["fixed_demo"]["task_set_license"] == "Apache-2.0"
    assert packet["research_run"]["status"] == "completed"
    assert packet["research_run"]["configuration_hash"]
    assert packet["research_run"]["result_hash"]
    assert packet["benchmark_run"]["dataset_id"] == "research_smoke_v1"
    assert packet["benchmark_run"]["dataset_license"] == "Apache-2.0"
    assert packet["benchmark_run"]["pass_rate"] == 1.0
    assert packet["sequence_analysis"]["summary"]["part_count"] > 0
    assert packet["sequence_analysis"]["summary"]["blocked_count"] == 0
    assert packet["sequence_evidence_report"]["readiness_status"] == "sequence_complete"
    assert packet["assembly_plan"]["status"] == "ready"
    assert packet["assembly_plan"]["method"] == "abstract_non_experimental_ordering"
    assert len(packet["assembly_plan"]["fragments"]) > 0
    assert len(packet["assembly_plan"]["junctions"]) > 0
    assert packet["primer_readiness"]["status"] == "ready"
    assert (
        packet["primer_readiness"]["checks"]["actual_primer_sequences_generated"]
        is False
    )
    assert "primer sequences" in packet["primer_readiness"]["claim_boundary"]
    assert packet["readiness"]["readiness_status"] == "primer_ready"
    assert packet["readiness"]["next_required_stage"] == "sequence_optimized"
    assert packet["readiness"]["domain_scores"]["logic_score"] is not None
    assert packet["readiness"]["domain_scores"]["dynamic_score"] is not None
    assert packet["readiness"]["domain_scores"]["sequence_quality_score"] is not None
    assert packet["readiness"]["domain_scores"]["assembly_plan_score"] is not None
    assert packet["readiness"]["domain_scores"]["primer_readiness_score"] == 1.0
    assert packet["readiness"]["domain_scores"]["experimental_readiness_score"] is None
    assert packet["run_manifest"]["simulation"]["configuration_hash"]
    assert any(
        tool["capability"] == "ode_simulation"
        for tool in packet["tool_capabilities"]["tools"]
    )

    packet_path = Path(packet["artifacts"]["packet_json"])
    markdown_path = Path(packet["artifacts"]["packet_markdown"])
    assert packet_path.is_file()
    assert markdown_path.is_file()
    assert Path(packet["artifacts"]["sequence_analysis_json"]).is_file()
    assert Path(packet["artifacts"]["sequence_evidence_json"]).is_file()
    assert Path(packet["artifacts"]["assembly_plan_json"]).is_file()
    assert Path(packet["artifacts"]["primer_readiness_json"]).is_file()
    evidence_manifest_path = Path(packet["artifacts"]["evidence_manifest_json"])
    assert evidence_manifest_path.is_file()
    assert validate_evidence_manifest(packet["evidence_manifest"]) == []
    decisions = {
        item["claim_id"]: item["status"]
        for item in packet["evidence_manifest"]["claim_decisions"]
    }
    assert decisions["computationally_consistent"] == "supported"
    assert decisions["externally_mapped"] == "unsupported"
    assert decisions["sequence_supported"] == "limited"
    assert decisions["experimentally_supported"] == "unsupported"


    persisted = json.loads(packet_path.read_text(encoding="utf-8"))
    assert persisted["packet_hash"] == packet["packet_hash"]
    assert "computational screening evidence" in persisted["claim_boundary"]
    assert persisted["readiness"]["readiness_status"] == "primer_ready"
    assert "Demo / Research Baseline Freeze" in markdown_path.read_text(
        encoding="utf-8"
    )


def test_run_canonical_task_baseline_all_cases(tmp_path: Path) -> None:
    from application.demo_baseline import run_canonical_task_baseline

    services = create_application_services(tmp_path / "api_data")

    # Run for a temporal task (toggle switch)
    packet_toggle = run_canonical_task_baseline(
        services,
        task_id="toggle_set_reset_v1",
        output_dir=tmp_path / "toggle",
        timeout_seconds=30.0,
    )
    assert packet_toggle["packet_hash"]
    assert packet_toggle["fixed_demo"]["task_id"] == "toggle_set_reset_v1"
    assert packet_toggle["evaluation"]["passed"] is True
    assert packet_toggle["readiness"]["readiness_status"] == "primer_ready"

    # Run for the ambiguous task
    packet_ambiguous = run_canonical_task_baseline(
        services,
        task_id="ambiguous_stress_output_v1",
        output_dir=tmp_path / "ambiguous",
        timeout_seconds=30.0,
    )
    assert packet_ambiguous["packet_hash"]
    assert packet_ambiguous["fixed_demo"]["task_id"] == "ambiguous_stress_output_v1"
    assert len(packet_ambiguous["response"]["questions"]) == 3
    assert packet_ambiguous["readiness"]["readiness_status"] == "conceptual"


def test_baseline_packet_hashes_are_reproducible_across_runs(tmp_path: Path) -> None:
    import time
    from application.demo_baseline import run_canonical_task_baseline

    services = create_application_services(tmp_path / "api_data")

    packet1 = run_canonical_task_baseline(
        services,
        task_id="toggle_set_reset_v1",
        output_dir=tmp_path / "run1",
        timeout_seconds=30.0,
    )

    time.sleep(0.1)

    packet2 = run_canonical_task_baseline(
        services,
        task_id="toggle_set_reset_v1",
        output_dir=tmp_path / "run2",
        timeout_seconds=30.0,
    )

    assert packet1["packet_hash"] == packet2["packet_hash"]
