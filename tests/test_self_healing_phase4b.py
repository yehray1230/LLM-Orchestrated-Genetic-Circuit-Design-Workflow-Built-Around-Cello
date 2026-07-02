from __future__ import annotations

import pytest
from tools.self_healing import (
    adjust_copy_number,
    mutate_intergenic_sequence,
    insert_insulator,
    swap_part_by_affinity,
    append_degradation_tag,
    run_self_healing_action,
    validate_self_healing_recommendation,
)
from schemas.state import DesignState, SearchNode
from workflows.reflexion_controller import (
    _apply_self_healing_to_best_topology,
    run_reflexion_workflow,
)


def test_programmatic_self_healing_actions() -> None:
    topology = {
        "copy_number": 10.0,
        "rbs_sequences": {"Y1": "AGGAGGGGGGGATG"},
        "biokinetic_parameters": {
            "translation_rate_Y1": 10.0,
            "protein_degradation_rate_Y1": 0.5,
        },
    }

    # 1. Adjust copy number
    res = adjust_copy_number(topology, 0.5)
    assert res["copy_number"] == 5.0

    # 2. Mutate spacer (break hairpin)
    res = mutate_intergenic_sequence(topology, "Y1")
    assert "AAAAATG" in res["rbs_sequences"]["Y1"]

    # 3. Insert insulator (prepend RiboJ)
    res = insert_insulator(topology, "Y1")
    assert res["rbs_sequences"]["Y1"].startswith(
        "AGCTGTCACCGGATGTGCTTTCCGGTCTGATGAGTCCGTG"
    )

    # 4. Swap part by affinity
    res = swap_part_by_affinity(topology, "Y1", "low")
    assert res["biokinetic_parameters"]["translation_rate_Y1"] == 2.0

    # 5. Append degradation tag
    res = append_degradation_tag(topology, "Y1", "LVA")
    assert res["biokinetic_parameters"]["protein_degradation_rate_Y1"] == 4.0


def test_self_healing_action_router() -> None:
    topology = {"copy_number": 10.0, "rbs_sequences": {"Y1": "AGGAGGGGGGGATG"}}

    recommendation = {
        "recommended_action": "adjust_copy_number",
        "target_node": "Y1",
        "parameters": {"scale": 0.2},
    }

    res = run_self_healing_action(topology, recommendation)
    assert res["copy_number"] == 2.0


def test_targeted_self_healing_rejects_missing_target() -> None:
    topology = {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
    }
    recommendation = {
        "recommended_action": "swap_part_by_affinity",
        "parameters": {"affinity": "low"},
    }

    errors = validate_self_healing_recommendation(topology, recommendation)

    assert any("target_node" in error for error in errors)
    with pytest.raises(ValueError, match="target_node"):
        run_self_healing_action(topology, recommendation)


def test_self_healing_only_replaces_evaluated_best_topology() -> None:
    best = {
        "verilog": "module best(input A, output Y); assign Y = A; endmodule",
        "copy_number": 10.0,
    }
    untouched = {
        "verilog": "module other(input A, output Z); assign Z = A; endmodule",
        "copy_number": 20.0,
    }
    node = SearchNode(
        node_id="root",
        search_mode="Exploration",
        candidate_topologies=[best, untouched],
        best_topology=best,
        last_recommendation={
            "recommended_action": "adjust_copy_number",
            "parameters": {"scale": 0.5},
        },
    )

    applied, _ = _apply_self_healing_to_best_topology(node)

    assert applied is True
    assert node.candidate_topologies[0]["copy_number"] == 5.0
    assert node.candidate_topologies[1] is untouched
    assert node.candidate_topologies[1]["copy_number"] == 20.0
    assert node.self_healing_history == [
        {
            "status": "applied",
            "candidate_index": 0,
            "recommendation": {
                "recommended_action": "adjust_copy_number",
                "parameters": {"scale": 0.5},
            },
            "changes": {
                "copy_number": {"before": 10.0, "after": 5.0},
            },
        }
    ]


class MockAgent:
    def __init__(self, run_fn):
        self.run_fn = run_fn
        self.kwargs = {}

    def run(self, state: DesignState) -> DesignState:
        return self.run_fn(state)


def test_reflexion_self_healing_controller_loop() -> None:
    # Set up basic state with a mock topology having high retroactivity
    state = DesignState(user_intent="test self healing")
    root_node = SearchNode(
        node_id="root",
        search_mode="Exploration",
        candidate_topologies=[
            {
                "verilog": "module c(input A, output Y); assign Y = A; endmodule",
                "copy_number": 10.0,
            }
        ],
    )
    state.tree_nodes["root"] = root_node
    state.active_frontier = ["root"]

    # Mock components
    builder = MockAgent(lambda s: s)
    translator = MockAgent(lambda s: s)

    # Mock Cello wrapper: adds default fields
    def cello_run(s):
        node = s.tree_nodes[s.current_node_id]
        for topo in node.candidate_topologies:
            topo["mapping_status"] = "assigned"
            topo["rbs_sequences"] = {"Y": "AGGAGG"}
        return s

    cello_wrapper = MockAgent(cello_run)

    # Mock simulator: simulates and updates copy number / load index
    def sim_run(s):
        node = s.tree_nodes[s.current_node_id]
        for topo in node.candidate_topologies:
            topo["ode_status"] = "simulated"
            # Add high retroactivity
            topo["retroactivity_max"] = 0.5
            topo["score"] = 0.5
            # Expose standard output fields
            topo["benchmark_report"] = {
                "score": 0.5,
                "metabolic_burden_score": 0.9,
                "robustness_score": 0.9,
                "orthogonality_score": 0.9,
                "cello_assignment_score": 0.9,
                "cello_buildable": True,
                "semantic_faithfulness_score": 1.0,
                "details": [],
            }
        return s

    batch_ode_simulator = MockAgent(sim_run)

    # Critic run:
    # First time: recommends copy number adjustment, sets is_approved = False
    # Second time: since copy number is adjusted, approves!
    run_count = 0

    def critic_run(s):
        nonlocal run_count
        run_count += 1
        node = s.tree_nodes[s.current_node_id]
        if run_count == 1:
            node.is_approved = False
            node.last_recommendation = {
                "recommended_action": "adjust_copy_number",
                "target_node": "Y",
                "parameters": {"scale": 0.5},
            }
        else:
            node.is_approved = True
            node.last_recommendation = None
        return s

    critic = MockAgent(critic_run)
    consolidator = MockAgent(lambda s: s)

    # Run workflow
    res_state = run_reflexion_workflow(
        state,
        builder,
        translator,
        cello_wrapper,
        batch_ode_simulator,
        critic,
        consolidator,
        None,
    )

    # Verify that self-healing loop was executed
    assert run_count == 2
    assert res_state.is_completed is True
    # The copy number should have been adjusted from 10.0 to 5.0
    assert res_state.best_topology["copy_number"] == 5.0
