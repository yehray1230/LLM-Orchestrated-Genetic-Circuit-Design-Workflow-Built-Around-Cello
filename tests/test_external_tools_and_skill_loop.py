from __future__ import annotations

import json
import sys
import types
from pathlib import Path

litellm_stub = types.ModuleType("litellm")
litellm_stub.completion = lambda **_: None
litellm_exceptions_stub = types.ModuleType("litellm.exceptions")
for name in ["AuthenticationError", "RateLimitError", "BadRequestError", "APIError"]:
    setattr(litellm_exceptions_stub, name, type(name, (Exception,), {}))
litellm_caching_stub = types.ModuleType("litellm.caching")
litellm_caching_stub.Cache = lambda **_: object()
litellm_stub.exceptions = litellm_exceptions_stub
sys.modules.setdefault("litellm", litellm_stub)
sys.modules.setdefault("litellm.exceptions", litellm_exceptions_stub)
sys.modules.setdefault("litellm.caching", litellm_caching_stub)

from agents.builder_agent import call_builder
from agents.skill_extractor_agent import SkillExtractorAgent
from benchmark_suite.benchmark_controller import evaluate_candidate
from oracle_evaluator import export_best_verilog
from schemas.state import DesignState, SearchNode
from tools.cello_wrapper import CelloWrapper, _truncate_error_log
from tools.skill_retriever import SkillRetriever
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

    xor = retriever.retrieve_skills("xor boolean decomposition", k=2)
    nor = retriever.retrieve_skills("nor promoter gate", k=2)

    assert len(retriever.skills) == 13
    assert "XOR_GATE" in xor
    assert "NOR_GATE" in nor
    assert "Boolean template" in xor


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
    assert "Avoid weak mapping" not in result


def test_skill_extractor_writes_obsidian_card_and_vector_record(tmp_path: Path) -> None:
    vector_db = InMemoryVectorDB()
    state = DesignState(user_intent="A and not B", host_organism="E coli")
    state.current_node_id = "root"
    state.tree_nodes["root"] = SearchNode(
        node_id="root",
        status="Pass",
        score=0.84,
        best_topology={"score": 0.84, "gate_count": 2, "ode_status": "simulated"},
        critic_feedbacks=["Design passed with good dynamic margin."],
    )

    result = SkillExtractorAgent(vault_dir=tmp_path, vector_db=vector_db).run(state)

    assert len(result.extracted_skills) == 1
    assert len(vector_db.all()) == 1
    card_path = Path(result.extracted_skills[0]["obsidian_path"])
    assert card_path.exists()
    assert "confidence_score: 0.84" in card_path.read_text(encoding="utf-8")


def test_benchmark_controller_uses_multiplicative_penalty() -> None:
    result = evaluate_candidate(
        {
            "functional_score": 0.8,
            "kinetic_score": 0.5,
            "plausibility_score": 0.5,
        }
    )

    assert result["score"] == 0.2
    assert result["scoring_model"] == "multiplicative_penalty"
    assert result["grade"] == "Fail"


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
    assert "Retrieved Successful Design Skills" in captured["system_prompt"]
    assert "Motif: XOR_GATE" in captured["system_prompt"]
    assert "Please apply the successful skills above" in captured["system_prompt"]


def test_cello_wrapper_mock_mode_is_unchanged() -> None:
    state = DesignState()
    state.verilog_codes = ["module c(input A, output Y); assign Y = A; endmodule"]

    result = CelloWrapper().run(state)

    topology = result.candidate_topologies[0]
    assert topology["source"] == "mock_cello_wrapper"
    assert topology["mapping_status"] == "unmapped"


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
    assert topology["error_type"] == "PART_ERROR"
    assert topology["mapping_error_category"] == "UCF_INCOMPATIBLE"
    assert "RuntimeException" in topology["raw_error_log"]


def test_cello_wrapper_timeout_becomes_mapping_failed_topology() -> None:
    state = DesignState()
    state.verilog_codes = ["module c(input A, output Y); assign Y = A; endmodule"]
    command = [sys.executable, "-c", "import time; time.sleep(2)"]

    result = CelloWrapper(cello_command=command, timeout_seconds=1).run(state)
    topology = result.candidate_topologies[0]

    assert topology["mapping_status"] == "MAPPING_FAILED"
    assert topology["mapping_error_category"] == "TIMEOUT"
    assert "timed out" in topology["mapping_error_summary"]


def test_cello_log_truncation_preserves_head_and_tail() -> None:
    long_log = "ERROR: initial declaration\n" + "\n".join(f"stack frame {i}" for i in range(500)) + "\nFinalException: concrete cause"

    truncated = _truncate_error_log(long_log, max_chars=1000)

    assert "ERROR: initial declaration" in truncated
    assert "FinalException: concrete cause" in truncated
    assert "truncated" in truncated
    assert len(truncated) < len(long_log)
