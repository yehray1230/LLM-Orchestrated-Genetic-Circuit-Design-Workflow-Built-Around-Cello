from __future__ import annotations

import json
import sys
from pathlib import Path

from agents.builder_agent import call_builder
from agents.skill_extractor_agent import SkillExtractorAgent
from benchmark_suite.benchmark_controller import evaluate_candidate
from benchmark_suite.cello_constraint_evaluator import evaluate_cello_constraints
from benchmark_suite.functional_scorer import score_functional
from benchmark_suite.metabolic_scorer import MetabolicBurdenEvaluator, count_logic_gates
from benchmark_suite.semantic_evaluator import evaluate_semantic_faithfulness
from benchmark_suite.static_plausibility_evaluator import score_static_plausibility
from benchmark_suite.temporal_scorer import score_temporal
from oracle_evaluator import export_best_verilog
from schemas.state import DesignState, SearchNode
from tools.cello_wrapper import CelloWrapper, _split_command_string, _truncate_error_log
from tools.skill_retriever import SkillRetriever
from tools.topology_selection import select_best_topology
from vector_db import InMemoryVectorDB


def _builder_payload() -> str:
    proposal = {
        "strategy_name": "Gate-Count Optimization",
        "optimization_goal": "minimize gates",
        "truth_table_or_logic_matrix": [{"A": 1, "Y": 1}],
        "logic_blueprint": "Y = A",
        "verilog_draft": "module c(input A, output Y); assign Y = A; endmodule",
        "translator_directives": [],
    }
    return json.dumps(
        {
            "gate_count_optimization": proposal,
            "depth_optimization": {**proposal, "strategy_name": "Depth Optimization"},
            "robustness_strategy": {**proposal, "strategy_name": "Robustness Strategy"},
        }
    )


def test_oracle_exports_best_verilog_file(tmp_path: Path) -> None:
    topology = {"score": 0.9, "verilog": "module winner(input A, output Y); assign Y = A; endmodule"}
    state = DesignState(user_intent="A passthrough", best_topology=topology)

    result = export_best_verilog(state, output_dir=tmp_path)

    assert result["ok"] is True
    assert result["module_name"] == "winner"
    assert Path(result["path"]).read_text(encoding="utf-8") == topology["verilog"] + "\n"
    assert topology["verilog_export_path"] == result["path"]


def test_oracle_returns_error_without_verilog(tmp_path: Path) -> None:
    result = export_best_verilog(DesignState(user_intent="missing"), output_dir=tmp_path)

    assert result["ok"] is False
    assert result["error"]


def test_skill_retriever_loads_json_and_returns_motif_snippets() -> None:
    retriever = SkillRetriever.from_json_file("邏輯設計skill.json")
    raw_skills = json.loads(Path("邏輯設計skill.json").read_text(encoding="utf-8"))

    xor = retriever.retrieve_skills("xor boolean decomposition", k=2)
    nor = retriever.retrieve_skills("nor promoter gate", k=2)
    empty_query = retriever.retrieve_skills("", k=2)

    assert len(retriever.skills) == 16
    assert len(retriever.core_skills) == 16
    assert all(record.get("skill_name") for record in raw_skills)
    assert all(record.get("motif_name") for record in raw_skills)
    assert retriever.memory_skills == []
    assert "Canonical logic skill catalog" in xor
    assert "XOR_GATE" in xor
    assert "BAND_PASS_FILTER" in xor
    assert "CELLO_COMPATIBILITY_POLICY" in xor
    assert "DESIGN_REPAIR_PLAYBOOK" in xor
    assert "REQUIREMENT_ANALYSIS_PLAYBOOK" in xor
    assert "NOR_GATE" in nor
    assert "Boolean template" in xor
    assert "Canonical logic skill catalog" in empty_query


def test_skill_retriever_retrieves_extracted_memory_separately(tmp_path: Path) -> None:
    memory_path = tmp_path / "extracted.jsonl"
    memory_path.write_text(
        json.dumps(
            {
                "title": "Avoid unstable XOR mapping",
                "summary": "Use a simpler NOR decomposition after repeated mapping failures.",
                "memory_kind": "avoid",
                "confidence_score": 0.9,
                "tags": ["failure/part-error", "mapping/failed"],
                "search_text": "xor mapping failure recovery",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    retriever = SkillRetriever.from_json_file(
        "邏輯設計skill.json",
        include_extracted=True,
        extracted_path=memory_path,
    )

    result = retriever.retrieve_skills("xor mapping failure", mode="Repair", k=2)

    assert len(retriever.core_skills) == 16
    assert len(retriever.memory_skills) == 1
    assert "Canonical logic skill catalog" in result
    assert "Avoid unstable XOR mapping" in result


def test_skill_retriever_default_path_is_repo_relative(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    retriever = SkillRetriever.from_json_file()

    assert len(retriever.skills) == 16


def test_core_text_files_are_valid_utf8_without_replacement_characters() -> None:
    root = Path(__file__).resolve().parent.parent
    for path in [
        root / "README.md",
        root / "app.py",
        root / "src" / "agents" / "translator_agent.py",
        root / "src" / "agents" / "critic_agent.py",
        root / "src" / "tools" / "skill_retriever.py",
    ]:
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text


def test_skill_retriever_uses_graph_tags_and_mode_pruning() -> None:
    retriever = SkillRetriever(
        skills=[
            {
                "title": "Avoid weak mapping",
                "summary": "Dead-end part choice",
                "tags": ["failure/part-error", "mapping/failed"],
                "confidence_score": 0.9,
                "search_text": "avoid dead-end mapping",
            },
            {
                "title": "Physical tuning",
                "summary": "Use alternate gates for mapping recovery",
                "tags": ["mapping/failed", "mode/exploitation"],
                "confidence_score": 0.7,
                "search_text": "physical mapping recovery",
            },
        ]
    )

    result = retriever.retrieve_skills("alternate mapping", mode="Exploitation", k=1)

    assert "Physical tuning" in result
    assert "Patterns to avoid or repair" in result
    assert "Avoid weak mapping" in result


def test_skill_extractor_writes_obsidian_card_and_vector_record(tmp_path: Path) -> None:
    vector_db = InMemoryVectorDB()
    memory_path = tmp_path / "memory.jsonl"
    state = DesignState(user_intent="A and not B", host_organism="E coli")
    state.current_node_id = "root"
    state.tree_nodes["root"] = SearchNode(
        node_id="root",
        status="Pass",
        score=0.84,
        best_topology={"score": 0.84, "gate_count": 2, "ode_status": "simulated"},
        critic_feedbacks=["Design passed with good dynamic margin."],
    )

    result = SkillExtractorAgent(vault_dir=tmp_path, vector_db=vector_db, memory_path=memory_path).run(state)

    assert len(result.extracted_skills) == 1
    assert len(vector_db.all()) == 1
    assert memory_path.exists()
    assert "A and not B" in memory_path.read_text(encoding="utf-8")
    card_path = Path(result.extracted_skills[0]["obsidian_path"])
    assert card_path.exists()
    assert "confidence_score: 0.84" in card_path.read_text(encoding="utf-8")


def test_benchmark_controller_uses_weighted_total_score() -> None:
    result = evaluate_candidate(
        {
            "functional_score": 0.8,
            "kinetic_score": 0.5,
            "plausibility_score": 0.5,
            "robustness_score": 0.77,
            "snr": 4.2,
            "monte_carlo_runs": 6,
            "semantic_faithfulness_score": 0.9,
            "missed_edge_cases": ["B=unknown not specified"],
        }
    )

    assert result["score"] == 0.6315
    assert result["weighted_total_score"] == 0.6315
    assert result["scoring_model"] == "weighted_total_score"
    assert result["grade"] == "Pass"
    assert result["metabolic_burden_score"] == 1.0
    assert result["gate_count"] == 0
    assert result["robustness_score"] == 0.77
    assert result["signal_to_noise_ratio"] == 4.2
    assert result["monte_carlo_runs"] == 6
    assert result["orthogonality_score"] == 0.25
    assert result["cello_assignment_score"] == 0.0
    assert result["cello_buildable"] is False
    assert result["semantic_faithfulness_score"] == 0.9
    assert result["missed_edge_cases"] == ["B=unknown not specified"]
    assert result["score_weights"]["metabolic_burden"] == 0.15
    assert result["score_weights"]["robustness"] == 0.15
    assert result["score_weights"]["temporal"] == 0.05
    assert result["score_weights"]["orthogonality"] == 0.10
    assert result["score_weights"]["cello_assignment"] == 0.10
    assert result["component_scores"]["robustness"] == 0.77
    assert result["component_scores"]["temporal"] == 1.0
    assert result["component_scores"]["orthogonality"] == 0.25


def test_functional_scorer_checks_truth_table_against_verilog() -> None:
    result = score_functional(
        {
            "verilog": "module c(input A, input B, output Y); assign Y = A & ~B; endmodule",
            "truth_table": [
                {"A": 0, "B": 0, "Y": 0},
                {"A": 1, "B": 0, "Y": 1},
                {"A": 1, "B": 1, "Y": 0},
            ],
        }
    )

    assert result.score == 1.0
    assert result.details["logic_compliance_score"] == 1.0
    assert result.details["truth_table_rows_checked"] == 3


def test_functional_scorer_settles_gate_outputs_before_assigns() -> None:
    result = score_functional(
        {
            "verilog": "module c(input A, output Y); wire n; not(n, A); assign Y = n; endmodule",
            "truth_table": [
                {"A": 0, "Y": 1},
                {"A": 1, "Y": 0},
            ],
        }
    )

    assert result.score == 1.0
    assert result.details["logic_failures"] == []


def test_functional_scorer_penalizes_logic_mismatch() -> None:
    result = score_functional(
        {
            "verilog": "module c(input A, input B, output Y); assign Y = A | B; endmodule",
            "truth_table": [
                {"A": 0, "B": 0, "Y": 0},
                {"A": 1, "B": 0, "Y": 1},
                {"A": 0, "B": 1, "Y": 0},
            ],
        }
    )

    assert result.score == 2 / 3
    assert len(result.details["logic_failures"]) == 1


def test_static_plausibility_penalizes_repeated_parts_and_depth() -> None:
    result = score_static_plausibility(
        {
            "part_ids": ["pA", "pA", "pB", "pB"],
            "logic_depth": 7,
        }
    )

    assert 0.0 < result.score < 1.0
    assert result.details["repeated_part_count"] == 2
    assert result.details["logic_depth"] == 7


def test_temporal_scorer_uses_trace_rise_time() -> None:
    result = score_temporal(
        {
            "time": [0.0, 30.0, 60.0, 90.0],
            "output": [0.1, 0.3, 0.55, 0.8],
            "threshold_on": 0.5,
            "target_rise_time": 60.0,
        }
    )

    assert result.rise_time == 60.0
    assert result.temporal_score == 1.0


def test_semantic_evaluator_parses_llm_json(monkeypatch) -> None:
    captured = {}

    def fake_call_llm(**kwargs):
        captured["system_prompt"] = kwargs["system_prompt"]
        captured["user_content"] = kwargs["user_content"]
        return json.dumps(
            {
                "score": 0.72,
                "missed_conditions": ["Missing behavior for A=0, B=1"],
            }
        )

    monkeypatch.setattr("benchmark_suite.semantic_evaluator.call_llm", fake_call_llm)

    result = evaluate_semantic_faithfulness(
        {
            "user_intent": "Output Y only when A is high and B is low.",
            "verilog": "module c(input A, input B, output Y); assign Y = A; endmodule",
            "model_name": "mock",
        }
    )

    assert result["semantic_faithfulness_score"] == 0.72
    assert result["missed_edge_cases"] == ["Missing behavior for A=0, B=1"]
    assert "strict test engineer" in captured["system_prompt"]
    assert "Original natural-language prompt" in captured["user_content"]
    assert "Builder/Translator Verilog" in captured["user_content"]


def test_semantic_evaluator_handles_non_json_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "benchmark_suite.semantic_evaluator.call_llm",
        lambda **_: "not json",
    )

    result = evaluate_semantic_faithfulness(
        {
            "user_intent": "Output Y only when A is high.",
            "verilog": "module c(input A, output Y); assign Y = A; endmodule",
            "model_name": "mock",
        }
    )

    assert result["semantic_faithfulness_score"] == 0.0
    assert result["missed_edge_cases"]


def test_cello_constraint_evaluator_parses_json_report(tmp_path: Path) -> None:
    report_path = tmp_path / "cello_report.json"
    report_path.write_text(
        json.dumps({"Gate Assignment Score": 87.5, "Toxicity": 0.12}),
        encoding="utf-8",
    )

    result = evaluate_cello_constraints(
        {
            "mapping_status": "mapped",
            "cello_report_path": str(report_path),
            "cello_buildable": True,
        }
    )

    assert result["status"] == "ok"
    assert result["cello_buildable"] is True
    assert result["cello_assignment_score"] == 0.875
    assert result["orthogonality_score"] == 1.0
    assert result["toxicity"] == 0.12
    assert result["toxicity_score"] == 0.88


def test_cello_constraint_evaluator_penalizes_crosstalk_and_missing_gates() -> None:
    result = evaluate_cello_constraints(
        {
            "mapping_status": "MAPPING_FAILED",
            "raw_error_log": "ERROR: Not enough gates available; severe Crosstalk detected",
            "return_code": 2,
        }
    )

    assert result["status"] == "constraint_failed"
    assert result["cello_buildable"] is False
    assert result["orthogonality_score"] == 0.05
    assert result["cello_assignment_score"] == 0.0


def test_cello_constraint_evaluator_uses_final_simulated_annealing_score() -> None:
    result = evaluate_cello_constraints(
        {
            "mapping_status": "mapped",
            "cello_buildable": True,
            "cello_stdout": (
                "INFO SimulatedAnnealing - Score: 0.00\n"
                "INFO SimulatedAnnealing - Score: 164.90\n"
                "INFO SimulatedAnnealing - Score: 328.29\n"
            ),
        }
    )

    assert result["raw_assignment_score"] == 328.29
    assert result["cello_assignment_score"] == 1.0


def test_metabolic_scorer_counts_instantiated_logic_gates() -> None:
    verilog = """
    module c(input A, input B, output Y);
      wire n1, n2, n3;
      // and ignored_comment_gate(Y, A, B);
      not(n1, A);
      and g1(n2, A, B);
      NOR u2(n3, n1, n2);
      xor #(.delay(1)) u3(Y, n2, n3);
    endmodule
    """

    result = MetabolicBurdenEvaluator().evaluate({"verilog": verilog})

    assert count_logic_gates(verilog) == 4
    assert result.gate_count == 4
    assert 0.0 < result.metabolic_burden_score < 1.0
    assert result.complexity_penalty == 1.0 - result.metabolic_burden_score


def test_metabolic_scorer_reads_verilog_file(tmp_path: Path) -> None:
    verilog_path = tmp_path / "candidate.v"
    verilog_path.write_text(
        "module c(input A, input B, output Y); nor g1(Y, A, B); endmodule\n",
        encoding="utf-8",
    )

    result = MetabolicBurdenEvaluator().evaluate({"verilog_path": str(verilog_path)})

    assert result.details["status"] == "ok"
    assert result.details["source"] == str(verilog_path)
    assert result.gate_count == 1
    assert result.metabolic_burden_score == 1.0


def test_metabolic_scorer_handles_file_read_failure(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.v"

    result = MetabolicBurdenEvaluator().evaluate({"verilog_path": str(missing_path)})

    assert result.details["status"] == "error"
    assert result.metabolic_burden_score == 0.0
    assert result.gate_count == 0
    assert result.complexity_penalty == 1.0


def test_metabolic_scorer_dynamic_gate_limit() -> None:
    # 1. Without truth table: should fallback to DEFAULT_IDEAL_GATE_LIMIT = 3
    result_default = MetabolicBurdenEvaluator().evaluate({"gate_count": 4})
    assert result_default.details["ideal_gate_limit"] == 3
    # gate count 4 > limit 3 -> penalized
    assert result_default.metabolic_burden_score < 1.0

    # 2. With 2-input truth table: dynamic limit = max(3, 2*2 + 1) = 5
    candidate_2_inputs = {
        "gate_count": 4,
        "truth_table": [
            {"A": 0, "B": 0, "Y": 0},
            {"A": 1, "B": 1, "Y": 1}
        ]
    }
    result_2_inputs = MetabolicBurdenEvaluator().evaluate(candidate_2_inputs)
    assert result_2_inputs.details["ideal_gate_limit"] == 5
    # gate count 4 <= limit 5 -> no penalty
    assert result_2_inputs.metabolic_burden_score == 1.0

    # 3. With 3-input truth table: dynamic limit = max(3, 2*3 + 1) = 7
    candidate_3_inputs = {
        "gate_count": 6,
        "truth_table_or_logic_matrix": [
            {"In1": 0, "In2": 0, "In3": 0, "output": 0}
        ]
    }
    result_3_inputs = MetabolicBurdenEvaluator().evaluate(candidate_3_inputs)
    assert result_3_inputs.details["ideal_gate_limit"] == 7
    # gate count 6 <= limit 7 -> no penalty
    assert result_3_inputs.metabolic_burden_score == 1.0

    # 4. Verification that explicit override via candidate metadata is respected
    candidate_override = {
        "gate_count": 4,
        "ideal_gate_limit": 2,
        "truth_table": [
            {"A": 0, "B": 0, "Y": 0}
        ]
    }
    result_override = MetabolicBurdenEvaluator().evaluate(candidate_override)
    assert result_override.details["ideal_gate_limit"] == 2
    assert result_override.metabolic_burden_score < 1.0


def test_builder_prompt_includes_retrieved_skills_and_apply_instruction(monkeypatch) -> None:
    captured = {}

    class Retriever:
        def retrieve_skills(self, query: str, mode: str = "Exploration", k: int = 5) -> str:
            return "Motif: XOR_GATE\nBoolean template: A XOR B\nKnown risks: logic hazard"

    def fake_call_llm(**kwargs):
        captured["system_prompt"] = kwargs["system_prompt"]
        return _builder_payload()

    monkeypatch.setattr("agents.builder_agent.call_llm", fake_call_llm)

    state = DesignState(user_intent="build xor circuit")
    result = call_builder(state, api_key=None, model_name="mock", skill_retriever=Retriever())

    assert result.last_error is None
    assert "Logic Design Skill Context" in captured["system_prompt"]
    assert "Motif: XOR_GATE" in captured["system_prompt"]
    assert "Use these motif definitions as design constraints" in captured["system_prompt"]


def test_cello_wrapper_mock_mode_is_unchanged() -> None:
    state = DesignState()
    state.verilog_codes = ["module c(input A, output Y); assign Y = A; endmodule"]

    result = CelloWrapper().run(state)

    topology = result.candidate_topologies[0]
    assert topology["source"] == "mock_cello_wrapper"
    assert topology["cello_mode"] == "mock"
    assert topology["cello_claim_level"] == "mock_only"
    assert "workflow placeholder" in topology["cello_warning"]
    assert topology["mapping_status"] == "unmapped"
    assert topology["orthogonality_score"] == 1.0
    assert topology["cello_assignment_score"] == 0.0
    assert topology["cello_buildable"] is False


def test_cello_wrapper_external_failure_becomes_mapping_failed_topology() -> None:
    state = DesignState()
    state.verilog_codes = ["module c(input A, output Y); assign Y = A; endmodule"]
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('UCF constraint mismatch\\njava.lang.RuntimeException: no gate found\\n'); sys.exit(2)",
    ]

    result = CelloWrapper(cello_command=command, timeout_seconds=5).run(state)
    topology = result.candidate_topologies[0]

    assert result.last_error is None
    assert topology["mapping_status"] == "MAPPING_FAILED"
    assert topology["cello_mode"] == "external"
    assert topology["cello_claim_level"] == "external_mapping_failed"
    assert topology["error_type"] == "PART_ERROR"
    assert topology["cello_buildable"] is False
    assert topology["mapping_error_category"] == "UCF_INCOMPATIBLE"
    assert "RuntimeException" in topology["raw_error_log"]


def test_cello_wrapper_external_success_marks_topology_buildable() -> None:
    state = DesignState()
    state.verilog_codes = ["module c(input A, output Y); assign Y = A; endmodule"]
    command = [sys.executable, "-c", "print('Gate Assignment Score: 92\\nToxicity: 0.08')"]

    result = CelloWrapper(cello_command=command, timeout_seconds=5).run(state)
    topology = result.candidate_topologies[0]

    assert topology["mapping_status"] == "mapped"
    assert topology["cello_mode"] == "external"
    assert topology["cello_claim_level"] == "externally_mapped"
    assert topology["cello_buildable"] is True
    assert topology["cello_assignment_score"] == 0.92
    assert topology["orthogonality_score"] == 1.0
    assert topology["toxicity"] == 0.08


def test_cello_command_string_preserves_windows_paths_and_quoted_arguments() -> None:
    command = (
        r'C:\Users\tester\AppData\Local\Programs\Podman\podman.exe '
        r'run --name "cello mapping"'
    )

    assert _split_command_string(command, windows=True) == [
        r"C:\Users\tester\AppData\Local\Programs\Podman\podman.exe",
        "run",
        "--name",
        "cello mapping",
    ]


def test_cello_command_expands_candidate_filename_for_each_index(tmp_path: Path) -> None:
    wrapper = CelloWrapper(
        cello_command=["cello", "/root/input/{candidate_filename}", "{index}"],
    )
    temp_path = tmp_path / "input"
    output_dir = temp_path / "output"
    netlist_path = temp_path / "candidate_2.v"

    command = wrapper._build_command(2, temp_path, netlist_path, output_dir)

    assert command == ["cello", "/root/input/candidate_2.v", "2"]


def test_best_topology_prefers_verified_mapping_over_higher_failed_score() -> None:
    mapped = {
        "score": 0.55,
        "cello_mode": "external",
        "mapping_status": "mapped",
        "cello_claim_level": "externally_mapped",
        "cello_buildable": True,
    }
    mapping_failed = {
        "score": 0.95,
        "cello_mode": "external",
        "mapping_status": "MAPPING_FAILED",
        "cello_claim_level": "external_mapping_failed",
        "cello_buildable": False,
    }

    assert select_best_topology([mapping_failed, mapped]) is mapped


def test_best_topology_uses_score_between_verified_mappings() -> None:
    lower = {
        "score": 0.65,
        "cello_mode": "external",
        "mapping_status": "mapped",
        "cello_claim_level": "externally_mapped",
        "cello_buildable": True,
    }
    higher = {**lower, "score": 0.81}

    assert select_best_topology([lower, higher]) is higher


def test_cello_wrapper_persists_output_directory_manifest(tmp_path: Path) -> None:
    state = DesignState()
    state.verilog_codes = ["module c(input A, output Y); assign Y = A; endmodule"]
    command = [
        sys.executable,
        "-c",
        (
            "import json, pathlib, sys; "
            "out=pathlib.Path(sys.argv[1]); "
            "(out/'nested').mkdir(parents=True, exist_ok=True); "
            "(out/'nested'/'assignment.json').write_text("
            "json.dumps({'gate':'Y','part':'TetR'}), encoding='utf-8'); "
            "print('Gate Assignment Score: 90')"
        ),
        "{output_dir}",
    ]

    result = CelloWrapper(
        cello_command=command,
        artifact_dir=tmp_path / "cello_artifacts",
        timeout_seconds=5,
    ).run(state)
    topology = result.candidate_topologies[0]
    manifest_path = Path(topology["cello_artifact_manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest_path.exists()
    assert manifest["status"] == "mapped"
    assert manifest["return_code"] == 0
    assert {item["relative_path"] for item in manifest["files"]} >= {
        "output/nested/assignment.json",
        "stdout.log",
        "stderr.log",
        "candidate_0.v",
    }
    assignment_entry = next(
        item for item in manifest["files"]
        if item["relative_path"] == "output/nested/assignment.json"
    )
    assert assignment_entry["size_bytes"] > 0
    assert len(assignment_entry["sha256"]) == 64
    assert Path(assignment_entry["absolute_path"]).exists()


def test_cello_wrapper_timeout_becomes_mapping_failed_topology() -> None:
    state = DesignState()
    state.verilog_codes = ["module c(input A, output Y); assign Y = A; endmodule"]
    command = [sys.executable, "-c", "import time; time.sleep(2)"]

    result = CelloWrapper(cello_command=command, timeout_seconds=1).run(state)
    topology = result.candidate_topologies[0]

    assert topology["mapping_status"] == "MAPPING_FAILED"
    assert topology["mapping_error_category"] == "TIMEOUT"
    assert "timed out" in topology["mapping_error_summary"]


def test_search_node_syncs_cello_evaluation_metrics() -> None:
    node = SearchNode(node_id="root")

    node.sync_evaluation_metrics(
        {
            "benchmark_report": {
                "orthogonality_score": "0.82",
                "cello_assignment_score": "0.63",
                "cello_buildable": "true",
            }
        }
    )

    assert node.orthogonality_score == 0.82
    assert node.cello_assignment_score == 0.63
    assert node.cello_buildable is True


def test_cello_log_truncation_preserves_head_and_tail() -> None:
    long_log = "ERROR: initial declaration\n" + "\n".join(f"stack frame {i}" for i in range(500)) + "\nFinalException: concrete cause"

    truncated = _truncate_error_log(long_log, max_chars=1000)

    assert "ERROR: initial declaration" in truncated
    assert "FinalException: concrete cause" in truncated
    assert "truncated" in truncated
    assert len(truncated) < len(long_log)
