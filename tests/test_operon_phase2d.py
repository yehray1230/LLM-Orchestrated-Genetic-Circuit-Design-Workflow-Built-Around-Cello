from __future__ import annotations

from tools.tool_adapters import RNAFoldingAdapter, _heuristic_rna_folding_energy
from tools.ode_simulator import BatchODESimulator


def test_heuristic_rna_folding_energy() -> None:
    # A strong complementary hairpin stem-loop: GGGGCATCGCCCC
    # Stem: GGGG (4bp) vs CCCC (4bp), Loop: ATCG (4bp)
    # GC pair count: 4 => energy ~ 3 - 4*3 = -9.0 kcal/mol
    mfe_hairpin = _heuristic_rna_folding_energy("GGGGCATCGCCCC")
    assert mfe_hairpin <= -8.0

    # A sequence with no complementary matches: AAAAAAAAAAAA
    # This shouldn't form a strong hairpin of length >= 4 with a loop
    mfe_no_hairpin = _heuristic_rna_folding_energy("AAAAAAAAAAAA")
    assert mfe_no_hairpin == 0.0


def test_rna_folding_adapter_fallback() -> None:
    adapter = RNAFoldingAdapter()
    availability = adapter.available()
    
    # We should have status available or fallback
    assert availability.status in ("available", "fallback")
    
    res = adapter.run({"sequence": "GGGGCATCGCCCC"})
    assert res.status == "ok"
    assert "mfe" in res.output
    assert res.output["mfe"] <= -8.0


def test_polycistronic_operon_transcription() -> None:
    # Topology with operon Y1, Y2 grouped together
    topology = {
        "verilog": """
        module two_gene_operon(input A, output Y1, output Y2);
          nor g1(Y1, A);
          nor g2(Y2, A);
        endmodule
        """,
        "truth_table": [
            {"A": "0", "Y1": "1", "Y2": "1"},
        ],
        "operons": [["Y1", "Y2"]],
    }
    
    simulator = BatchODESimulator(
        simulation_time=200.0,
        sample_count=21,
    )
    result = simulator.simulate_topology(topology)
    
    assert result["ode_status"] == "simulated"
    # Number of states in result should be: num_op (1) + 2 * gene_count (4) = 5
    # Let's verify we got successful outputs
    assert "ode_trace" in result
    assert len(result["warnings"]) == 0
    assert result["stoichiometry_score"] > 0.0


def test_unknown_operon_gene_returns_structured_validation_failure() -> None:
    topology = {
        "verilog": "module invalid_operon(input A, output Y); assign Y = A; endmodule",
        "operons": [["NOT_A_GENE"]],
    }

    result = BatchODESimulator(
        simulation_time=20.0,
        sample_count=4,
    ).simulate_topology(topology)

    assert result["ode_status"] == "failed"
    assert result["score"] == 0.0
    assert result["simulation_result"]["status"] == "failed"
    assert "unknown gene 'NOT_A_GENE'" in result["simulation_result"]["error"]
    assert result["benchmark_report"]["details"][0]["status"] == "input_validation_failed"


def test_stochastic_adapter_rejects_unknown_operon_gene() -> None:
    topology = {
        "verilog": "module invalid_operon(input A, output Y); assign Y = A; endmodule",
        "operons": [["NOT_A_GENE"]],
    }

    from tools.tool_adapters import StochasticSimulationAdapter

    result = StochasticSimulationAdapter().run({"topology": topology})

    assert result.status == "failed"
    assert "INVALID_OPERON" in {warning.code for warning in result.warnings}


def test_translational_coupling_and_polarity() -> None:
    # Define an operon ["Y1", "Y2"] with overlapping spacing (coupling on)
    # We define Y1 as a wire and Y2 as the output so Y2 is the target output
    topology_coupled = {
        "verilog": """
        module coupled_op(input A, output Y2);
          wire Y1;
          nor g1(Y1, A);
          nor g2(Y2, A);
        endmodule
        """,
        "truth_table": [
            {"A": "0", "Y2": "1"}
        ],
        "operons": [["Y1", "Y2"]],
        "biokinetic_parameters": {
            "intergenic_spacing_Y2": {"value": -4.0, "unit": "bp"},
            "translation_rate_Y1": {"value": 5.0, "unit": "hr-1"},
            "translation_rate_Y2": {"value": 1.0, "unit": "hr-1"},  # low basal
        }
    }
    
    # Spacing large (coupling off)
    topology_uncoupled = {
        "verilog": """
        module uncoupled_op(input A, output Y2);
          wire Y1;
          nor g1(Y1, A);
          nor g2(Y2, A);
        endmodule
        """,
        "truth_table": [
            {"A": "0", "Y2": "1"}
        ],
        "operons": [["Y1", "Y2"]],
        "biokinetic_parameters": {
            "intergenic_spacing_Y2": {"value": 40.0, "unit": "bp"},
            "translation_rate_Y1": {"value": 5.0, "unit": "hr-1"},
            "translation_rate_Y2": {"value": 1.0, "unit": "hr-1"},
        }
    }

    simulator = BatchODESimulator(simulation_time=200.0, sample_count=21)
    
    res_coupled = simulator.simulate_topology(topology_coupled)
    res_uncoupled = simulator.simulate_topology(topology_uncoupled)
    
    # Trace values of Y2 should be higher in the coupled case due to upstream translation flux scaling Y2 RBS strength
    trace_coupled_Y2 = res_coupled["ode_trace"]["output_protein"]  # Y2 is output
    # Since target output defaults to Y2 (the last output)
    final_coupled_Y2 = trace_coupled_Y2[-1]
    
    # Verify uncoupled target output Y2
    trace_uncoupled_Y2 = res_uncoupled["ode_trace"]["output_protein"]
    final_uncoupled_Y2 = trace_uncoupled_Y2[-1]
    
    assert final_coupled_Y2 > final_uncoupled_Y2


def test_rbs_blocking_warning() -> None:
    # Set up a topology with an RBS sequence containing a strong hairpin
    # for a gene that has no upstream gene or low upstream translation flux
    topology = {
        "verilog": """
        module blocked_rbs(input A, output Y);
          nor g1(Y, A);
        endmodule
        """,
        "rbs_sequences": {
            "Y": "GGGGCATCGCCCC"  # forms -9.0 MFE hairpin loop
        }
    }
    
    simulator = BatchODESimulator(simulation_time=100.0, sample_count=11)
    result = simulator.simulate_topology(topology)
    
    assert result["ode_status"] == "simulated"
    # It should trigger RBS blocking warning because Y has a tight hairpin MFE < -8 and is at pos 0 of its operon
    warnings = result.get("warnings", [])
    assert any("RBS blocking warning" in w for w in warnings)
