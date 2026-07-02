from __future__ import annotations

import math

from tools.ode_simulator import (
    ResourceAwareSimulation,
    WarmStartResourceSolver,
    BatchODESimulator,
)


def test_analytical_single_target_solver() -> None:
    # Set up a simulation with a single target for regulator A
    # A -> B (A regulates B)
    signals = {"A": "input", "B": "output"}
    deps = {"B": ("not", ["A"])}
    params = {
        "kd": 10.0,
        "kd_B": 10.0,
        "copy_number": 20.0,
        "rnap_total": 5000.0,
        "ribosome_total": 20000.0,
        "km_rnap": 75.0,
        "km_ribosome": 120.0,
    }
    solver = WarmStartResourceSolver(rnap_free=5000.0, ribosome_free=20000.0)
    sim = ResourceAwareSimulation(signals, deps, params, solver)

    # Let's test the analytical solver directly
    # For m = 1 target: kd = 10, copy_number = 20, p_tot = 30
    # Equation: p_tot = p_free + copy_number * p_free / (kd + p_free)
    # 30 = p_free + 20 * p_free / (10 + p_free)
    # 30 * (10 + p_free) = p_free * (10 + p_free) + 20 * p_free
    # 300 + 30 * p_free = 10 * p_free + p_free^2 + 20 * p_free
    # p_free^2 - 300 = 0 => p_free = sqrt(300) ≈ 17.320508
    p_free = sim._solve_free_regulator("A", 30.0, 20.0, [("B", 10.0)])
    assert math.isclose(p_free, math.sqrt(300.0), rel_tol=1e-5)

    # Check that p_free <= p_tot always
    assert p_free <= 30.0


def test_multi_target_solver() -> None:
    # Set up a simulation with multiple targets for regulator A
    # A -> B, A -> C
    signals = {"A": "input", "B": "output", "C": "output"}
    deps = {"B": ("not", ["A"]), "C": ("not", ["A"])}
    params = {
        "kd": 10.0,
        "kd_B": 5.0,
        "kd_C": 15.0,
        "copy_number": 10.0,
        "rnap_total": 5000.0,
        "ribosome_total": 20000.0,
        "km_rnap": 75.0,
        "km_ribosome": 120.0,
    }
    solver = WarmStartResourceSolver(rnap_free=5000.0, ribosome_free=20000.0)
    sim = ResourceAwareSimulation(signals, deps, params, solver)

    # Solve for p_tot = 40.0, copy_number = 10.0
    # Targets: ("B", 5.0), ("C", 15.0)
    # f(x) = x + 10 * x / (5 + x) + 10 * x / (15 + x) - 40 = 0
    p_free = sim._solve_free_regulator("A", 40.0, 10.0, [("B", 5.0), ("C", 15.0)])

    # Verify conservation equation holds
    err = (
        p_free + 10.0 * p_free / (5.0 + p_free) + 10.0 * p_free / (15.0 + p_free) - 40.0
    )
    assert abs(err) < 1e-4
    assert p_free <= 40.0


def test_copy_number_zero_convergence() -> None:
    signals = {"A": "input", "B": "output"}
    deps = {"B": ("not", ["A"])}
    params = {
        "kd": 10.0,
        "copy_number": 0.0,
        "rnap_total": 5000.0,
        "ribosome_total": 20000.0,
        "km_rnap": 75.0,
        "km_ribosome": 120.0,
    }
    solver = WarmStartResourceSolver(rnap_free=5000.0, ribosome_free=20000.0)
    sim = ResourceAwareSimulation(signals, deps, params, solver)

    # Under copy_number = 0, p_free should equal p_tot exactly
    p_free = sim._solve_free_regulator("A", 25.0, 0.0, [("B", 10.0)])
    assert p_free == 25.0


def test_latch_bistability_shift_simulation() -> None:
    # Define a standard NOR-based SR latch
    latch_topology = {
        "verilog": """
        module sr_latch(input S, input R, output Q, output Qbar);
          nor g1(Q, R, Qbar);
          nor g2(Qbar, S, Q);
        endmodule
        """,
        "truth_table": [
            {"S": "0", "R": "0", "Q": "0"},
            {"S": "1", "R": "0", "Q": "1"},
            {"S": "0", "R": "0", "Q": "1"},  # Holds Q = 1
            {"S": "0", "R": "1", "Q": "0"},
            {"S": "0", "R": "0", "Q": "0"},  # Holds Q = 0
        ],
    }

    # Simulate with low copy number (copy_number = 1.0)
    # At low copy number, retroactivity / sequestration is minimal
    simulator_low = BatchODESimulator(
        simulation_time=200.0,
        sample_count=21,
        monte_carlo_samples=1,
    )
    topo_low = latch_topology.copy()
    topo_low["copy_number"] = 1.0
    res_low = simulator_low.simulate_topology(topo_low)

    assert res_low["ode_status"] == "simulated"
    # Ensure warnings are empty or not present for low retroactivity
    warnings_low = res_low.get("warnings", [])
    assert not any("Retroactivity warning" in w for w in warnings_low)

    # Simulate with high copy number (copy_number = 80.0)
    # At high copy number, high sequestration is expected, generating warnings
    simulator_high = BatchODESimulator(
        simulation_time=200.0,
        sample_count=21,
        monte_carlo_samples=1,
    )
    topo_high = latch_topology.copy()
    topo_high["copy_number"] = 80.0
    res_high = simulator_high.simulate_topology(topo_high)

    assert res_high["ode_status"] == "simulated"
    warnings_high = res_high.get("warnings", [])
    # Since copy number is high, retroactivity warnings should be raised for Q or Qbar
    assert any("Retroactivity warning" in w for w in warnings_high)
