from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from application.design_task_benchmark import (
    run_exp003_design_task_benchmark,
    stable_batch_hash,
)
from application.services import create_application_services


def test_exp003_batch_runs_all_tasks_with_default_v1_1(
    tmp_path: Path,
) -> None:
    services = create_application_services(tmp_path / "api_data")

    packet = run_exp003_design_task_benchmark(
        services,
        output_dir=tmp_path / "benchmark",
        timeout_seconds=30.0,
    )

    assert packet["summary"] == {
        "task_count": 5,
        "passed_count": 5,
        "failed_count": 0,
        "unsupported_count": 0,
        "provisional_count": 0,
        "pass_rate": 1.0,
        "all_tasks_executed": True,
        "all_tasks_supported": True,
    }
    by_id = {result["task_id"]: result for result in packet["results"]}
    reporter = by_id["reporter_a_or_b_v1"]
    cello = by_id["cello_a_and_not_b_gfp_v1"]
    ambiguous = by_id["ambiguous_stress_output_v1"]
    toggle = by_id["toggle_set_reset_v1"]
    oscillator = by_id["oscillator_repressilator_v1"]

    assert reporter["evaluation"]["truth_table_match"] is True
    assert cello["evaluation"]["functional_score"] == 1.0
    assert reporter["research_run"]["scoring_profile"] == "research-v2-preview"
    assert "research_smoke_v1" not in json.dumps(packet)
    assert ambiguous["passed"] is True
    assert ambiguous["candidate_generated"] is False
    assert len(ambiguous["response"]["questions"]) == 3
    assert toggle["passed"] is True
    assert oscillator["passed"] is True
    assert oscillator["status"] == "passed"
    assert toggle["evaluation"]["passed"] is True
    assert oscillator["evaluation"]["passed"] is True

    packet_json = Path(packet["artifacts"]["packet_json"])
    summary_markdown = Path(packet["artifacts"]["summary_markdown"])
    assert packet_json.is_file()
    assert summary_markdown.is_file()
    persisted = json.loads(packet_json.read_text(encoding="utf-8"))
    assert persisted["stable_result_hash"] == packet["stable_result_hash"]
    assert "Capability Gaps" in summary_markdown.read_text(encoding="utf-8")


def test_stable_batch_hash_ignores_volatile_metadata() -> None:
    batch = {
        "packet_type": "exp003_design_task_benchmark",
        "packet_version": "1.0",
        "created_at": "first",
        "runner": {"version": "1.0"},
        "task_set": {"content_hash": "task-hash"},
        "summary": {"task_count": 1},
        "results": [
            {
                "task_id": "case",
                "category": "reporter",
                "status": "passed",
                "passed": True,
                "execution_mode": "deterministic_fixture",
                "candidate_generated": True,
                "evaluation": {"passed": True},
                "research_run": {
                    "run_id": "volatile-run-1",
                    "run_manifest_path": "volatile-path-1",
                    "configuration_hash": "configuration",
                    "result_hash": "result",
                    "weighted_total_score": 1.0,
                },
            }
        ],
    }
    changed = deepcopy(batch)
    changed["created_at"] = "second"
    changed["results"][0]["research_run"]["run_id"] = "volatile-run-2"
    changed["results"][0]["research_run"]["run_manifest_path"] = "volatile-path-2"

    assert stable_batch_hash(batch) == stable_batch_hash(changed)


def test_stable_batch_hash_changes_directly_with_runner_evaluator_config() -> None:
    batch = {
        "packet_type": "exp003_design_task_benchmark",
        "packet_version": "1.0",
        "created_at": "now",
        "runner": {
            "version": "1.0",
            "temporal_evaluator_version": "1.0",
            "temporal_evaluator_config": {"some": "config"}
        },
        "task_set": {"content_hash": "hash"},
        "summary": {"task_count": 1},
        "results": [],
    }
    changed_version = deepcopy(batch)
    changed_version["runner"]["temporal_evaluator_version"] = "1.1"

    changed_config = deepcopy(batch)
    changed_config["runner"]["temporal_evaluator_config"] = {"different": "config"}

    hash_orig = stable_batch_hash(batch)
    assert hash_orig != stable_batch_hash(changed_version)
    assert hash_orig != stable_batch_hash(changed_config)


def test_exp003_benchmark_profiles_and_strict_peak_gate(tmp_path: Path) -> None:
    from schemas import (
        CONFIG_V1_0,
        CONFIG_V1_1,
        OscillatorProfile,
        TemporalEvaluatorConfig,
    )
    services = create_application_services(tmp_path / "api_data")

    # Run the legacy-compatible v1.0 profile explicitly.
    packet_v1_0 = run_exp003_design_task_benchmark(
        services,
        output_dir=tmp_path / "benchmark_v1_0",
        timeout_seconds=30.0,
        evaluator_config=CONFIG_V1_0,
    )

    # In v1.0, 4 tasks pass, and the oscillator is provisional (not counted in passed_count)
    assert packet_v1_0["summary"]["passed_count"] == 4
    by_id_v1_0 = {res["task_id"]: res for res in packet_v1_0["results"]}
    assert by_id_v1_0["oscillator_repressilator_v1"]["status"] == "provisional"
    assert by_id_v1_0["oscillator_repressilator_v1"]["passed"] is False

    # Run with v1.1 config (full conditions met and passed)
    packet_v1_1 = run_exp003_design_task_benchmark(
        services,
        output_dir=tmp_path / "benchmark_v1_1",
        timeout_seconds=30.0,
        evaluator_config=CONFIG_V1_1,
    )
    assert packet_v1_1["summary"]["passed_count"] == 5
    by_id_v1_1 = {res["task_id"]: res for res in packet_v1_1["results"]}
    assert by_id_v1_1["oscillator_repressilator_v1"]["status"] == "passed"
    assert by_id_v1_1["oscillator_repressilator_v1"]["passed"] is True

    # Run with a stricter config that requires 5 peaks (repressilator only has 3)
    strict_config = TemporalEvaluatorConfig(
        version="1.2-strict",
        toggle_profile=CONFIG_V1_1.toggle_profile,
        oscillator_profile=OscillatorProfile(
            transient_cutoff=500.0,
            minimum_peak_count=5,
            minimum_amplitude=10.0,
            maximum_period_cv=0.25,
            minimum_amplitude_retention=0.7,
        )
    )

    packet_strict = run_exp003_design_task_benchmark(
        services,
        output_dir=tmp_path / "benchmark_strict",
        timeout_seconds=30.0,
        evaluator_config=strict_config,
    )

    # Assert that the stable result hash is different
    assert packet_v1_0["stable_result_hash"] != packet_strict["stable_result_hash"]

    # In strict config, the oscillator task fails
    assert packet_strict["summary"]["passed_count"] == 4
    by_id_strict = {res["task_id"]: res for res in packet_strict["results"]}
    oscillator_res = by_id_strict["oscillator_repressilator_v1"]
    assert oscillator_res["passed"] is False
    assert oscillator_res["status"] == "failed"

    # Verify that rule details are recorded
    assert oscillator_res["evaluation"]["evaluator_version"] == "1.2-strict"
    assert oscillator_res["evaluation"]["evaluator_config"]["minimum_peak_count"] == 5


def test_default_temporal_config_and_cli_use_v1_1() -> None:
    from schemas import DEFAULT_TEMPORAL_CONFIG, get_temporal_evaluator_config
    from scripts.run_exp003_benchmark import build_parser

    assert DEFAULT_TEMPORAL_CONFIG.version == "1.1"
    assert build_parser().parse_args([]).temporal_evaluator_version == "1.1"
    assert (
        build_parser()
        .parse_args(["--temporal-evaluator-version", "1.0"])
        .temporal_evaluator_version
        == "1.0"
    )
    assert get_temporal_evaluator_config("1.1") is DEFAULT_TEMPORAL_CONFIG


def test_temporal_evaluator_config_rejects_invalid_values() -> None:
    from schemas import (
        CONFIG_V1_1,
        OscillatorProfile,
        PhaseWindow,
        TemporalEvaluatorConfig,
        ToggleProfile,
        get_temporal_evaluator_config,
    )

    with pytest.raises(ValueError, match="greater than start"):
        PhaseWindow(10.0, 5.0)
    with pytest.raises(ValueError, match="high threshold"):
        ToggleProfile(
            high_threshold=40.0,
            low_threshold=40.0,
            phase_windows=CONFIG_V1_1.toggle_profile.phase_windows,
            minimum_hold_margin=20.0,
        )
    with pytest.raises(ValueError, match="peak count"):
        OscillatorProfile(
            transient_cutoff=500.0,
            minimum_peak_count=1,
            minimum_amplitude=10.0,
        )
    with pytest.raises(ValueError, match="between zero and one"):
        OscillatorProfile(
            transient_cutoff=500.0,
            minimum_peak_count=3,
            minimum_amplitude=10.0,
            minimum_amplitude_retention=1.1,
        )
    with pytest.raises(ValueError, match="version is required"):
        TemporalEvaluatorConfig(
            version=" ",
            toggle_profile=CONFIG_V1_1.toggle_profile,
            oscillator_profile=CONFIG_V1_1.oscillator_profile,
        )
    with pytest.raises(ValueError, match="Unknown temporal evaluator version"):
        get_temporal_evaluator_config("9.9")




def test_toggle_evaluator_negative_scenarios() -> None:
    from application.design_task_benchmark import _evaluate_stateful_temporal_task
    from benchmark_suite.design_task_dataset import DesignTask

    # Create dummy design task
    task = DesignTask(
        task_id="dummy_toggle",
        category="toggle",
        name="Dummy Toggle",
        request="Design a toggle",
        expected={
            "evaluation_mode": "stateful_temporal",
            "inputs": ["SET", "RESET"],
            "outputs": ["GFP"],
        },
        constraints={},
        scoring_notes=[],
        tags=[],
        source={"type": "project_fixture"},
    )

    # Helper to create mock research result
    def make_mock_result(times: list[float], outputs: list[float]) -> dict:
        return {
            "candidate": {
                "ode_trace": {
                    "time": times,
                    "output_protein": outputs,
                }
            },
            "simulation_result": {
                "status": "simulated"
            }
        }

    # 1. Fake toggle (no feedback) - decays during HOLD_SET (1000 to 2000)
    # SET phase end (950-1000) is high (150.0). HOLD_SET (1100-2000) decays to 10.0
    times_fake = [950.0, 1000.0, 1100.0, 1500.0, 2000.0, 2950.0, 3000.0, 3100.0, 4000.0, 4900.0, 5000.0]
    outputs_fake = [150.0, 150.0, 10.0, 10.0, 10.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]
    res_fake = _evaluate_stateful_temporal_task(task, make_mock_result(times_fake, outputs_fake))
    assert res_fake["passed"] is False
    assert any(d["phase"] == "HOLD_SET" and d["passed"] is False for d in res_fake["details"])

    # 2. SET followed by rapid decay in HOLD_SET (same as above, specifically checking HOLD_SET failure)
    # We can test that SET passes (passed = True) but HOLD_SET fails
    set_metrics = next(d for d in res_fake["details"] if d["phase"] == "SET")
    hold_set_metrics = next(d for d in res_fake["details"] if d["phase"] == "HOLD_SET")
    assert set_metrics["passed"] is True
    assert hold_set_metrics["passed"] is False

    # 3. RESET followed by re-rising in HOLD_RESET (3100 to 4000)
    # SET (950-1000) high, HOLD_SET (1100-2000) high, RESET (2950-3000) low (5.0), but HOLD_RESET rises to 80.0
    times_rise = [950.0, 1000.0, 1100.0, 2000.0, 2950.0, 3000.0, 3100.0, 3500.0, 4000.0, 4900.0, 5000.0]
    outputs_rise = [150.0, 150.0, 150.0, 150.0, 5.0, 5.0, 80.0, 80.0, 80.0, 5.0, 5.0]
    res_rise = _evaluate_stateful_temporal_task(task, make_mock_result(times_rise, outputs_rise))
    assert res_rise["passed"] is False
    reset_metrics = next(d for d in res_rise["details"] if d["phase"] == "RESET")
    hold_reset_metrics = next(d for d in res_rise["details"] if d["phase"] == "HOLD_RESET")
    assert reset_metrics["passed"] is True
    assert hold_reset_metrics["passed"] is False

    # 4. Missing phase samples (e.g. no time points between 1100 and 2000)
    times_gap = [950.0, 1000.0, 2950.0, 3000.0, 3100.0, 4000.0, 4900.0, 5000.0]
    outputs_gap = [150.0, 150.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]
    res_gap = _evaluate_stateful_temporal_task(task, make_mock_result(times_gap, outputs_gap))
    assert res_gap["passed"] is False
    hold_set_gap_metrics = next(d for d in res_gap["details"] if d["phase"] == "HOLD_SET")
    assert hold_set_gap_metrics["sample_count"] == 0
    assert hold_set_gap_metrics["passed"] is False


def test_oscillator_evaluator_negative_scenarios() -> None:
    from application.design_task_benchmark import _evaluate_oscillatory_temporal_task
    from schemas import CONFIG_V1_1
    from benchmark_suite.design_task_dataset import DesignTask

    # Create dummy design task
    task = DesignTask(
        task_id="dummy_oscillator",
        category="oscillator",
        name="Dummy Oscillator",
        request="Design an oscillator",
        expected={
            "evaluation_mode": "oscillatory_temporal",
        },
        constraints={},
        scoring_notes=[],
        tags=[],
        source={"type": "project_fixture"},
    )

    # Helper to create mock research result
    def make_mock_result(times: list[float], outputs: list[float]) -> dict:
        return {
            "candidate": {
                "ode_trace": {
                    "time": times,
                    "output_protein": outputs,
                }
            },
            "simulation_result": {
                "status": "simulated"
            }
        }

    # 1. Single overshoot: only 1 peak at t=1000.0, transient cutoff=500.0
    times_single = [0.0, 500.0, 1000.0, 1500.0, 2000.0]
    outputs_single = [0.0, 50.0, 150.0, 50.0, 50.0]
    res_single = _evaluate_oscillatory_temporal_task(task, make_mock_result(times_single, outputs_single), config=CONFIG_V1_1)
    assert res_single["passed"] is False
    assert res_single["classification"] == "non-oscillatory"

    # 2. Two peaks: peaks at 1000.0 and 2000.0. Under V1.1 (requires 3 peaks) it fails
    times_two = [0.0, 500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0]
    outputs_two = [0.0, 50.0, 150.0, 50.0, 150.0, 50.0, 50.0]
    res_two = _evaluate_oscillatory_temporal_task(task, make_mock_result(times_two, outputs_two), config=CONFIG_V1_1)
    assert res_two["passed"] is False
    assert res_two["peak_count"] == 2

    # 3. Low amplitude: 3 peaks, but amplitudes are below 10.0 (e.g. peak value 105.0, valley value 100.0 -> amp 5.0)
    times_low = [0.0, 500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0]
    outputs_low = [100.0, 100.0, 105.0, 100.0, 105.0, 100.0, 105.0, 100.0, 100.0]
    res_low = _evaluate_oscillatory_temporal_task(task, make_mock_result(times_low, outputs_low), config=CONFIG_V1_1)
    assert res_low["passed"] is False
    assert res_low["classification"] == "non-oscillatory"

    # 4. Damped oscillation: 3 peaks, but amplitude decays (first amp 100.0, last amp 10.0 -> retention 0.1 < 0.7)
    times_damped = [0.0, 500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0]
    outputs_damped = [0.0, 0.0, 150.0, 50.0, 90.0, 60.0, 70.0, 60.0, 60.0]
    res_damped = _evaluate_oscillatory_temporal_task(task, make_mock_result(times_damped, outputs_damped), config=CONFIG_V1_1)
    assert res_damped["passed"] is False
    assert res_damped["classification"] == "damped"
    assert res_damped["amplitude_retention"] < 0.7

    # 5. Irregular oscillation: 3 peaks, but periods are highly irregular (CV > 0.25)
    times_irreg = [0.0, 500.0, 1000.0, 1100.0, 1200.0, 2100.0, 3000.0, 3500.0, 4000.0]
    outputs_irreg = [0.0, 0.0, 150.0, 50.0, 150.0, 50.0, 150.0, 50.0, 50.0]
    res_irreg = _evaluate_oscillatory_temporal_task(task, make_mock_result(times_irreg, outputs_irreg), config=CONFIG_V1_1)
    assert res_irreg["passed"] is False
    assert res_irreg["classification"] == "irregular"

    # 6. Insufficient simulation time: no peaks found
    times_insuf = [0.0, 100.0, 200.0, 300.0, 400.0]
    outputs_insuf = [10.0, 12.0, 14.0, 16.0, 18.0]
    res_insuf = _evaluate_oscillatory_temporal_task(task, make_mock_result(times_insuf, outputs_insuf), config=CONFIG_V1_1)
    assert res_insuf["passed"] is False
    assert res_insuf["peak_count"] == 0

    # 7. Malformed traces fail structurally instead of raising IndexError.
    res_malformed = _evaluate_oscillatory_temporal_task(
        task,
        make_mock_result(
            [500.0, 600.0, 700.0, 800.0, 900.0],
            [0.0, 1.0],
        ),
        config=CONFIG_V1_1,
    )
    assert res_malformed["passed"] is False
    assert res_malformed["classification"] == "invalid-trace"
    assert res_malformed["trace_valid"] is False
    assert res_malformed["trace_validation_errors"]


def test_stable_batch_hash_sanitization_and_status() -> None:
    from application.design_task_benchmark import stable_batch_hash
    from copy import deepcopy

    # Base batch
    batch_base = {
        "packet_type": "exp003_design_task_benchmark",
        "packet_version": "1.0",
        "runner": {
            "version": "1.0",
            "temporal_evaluator_version": "1.0",
            "temporal_evaluator_config": {"some": "config"}
        },
        "task_set": {"content_hash": "hash"},
        "summary": {"task_count": 1},
        "results": [
            {
                "task_id": "oscillator_repressilator_v1",
                "category": "oscillator",
                "status": "provisional",
                "passed": False,
                "execution_mode": "deterministic_fixture",
                "candidate_generated": True,
                "evaluation": {
                    "evaluation_mode": "oscillatory_temporal",
                    "passed": True,
                    "classification": "sustained",
                    "peak_count": 3,
                    "mean_period": 2675.0,
                    "amplitudes": [147.77, 160.53],
                },
                "response": {
                    "raw_output": "Sequence optimization log at C:\\Users\\yehra\\Desktop\\project\\logs\\opt.log Done.",
                }
            }
        ],
    }

    # 1. Changing volatile paths/timestamps should result in the EXACT same stable hash
    batch_changed_paths = deepcopy(batch_base)
    batch_changed_paths["results"][0]["response"]["raw_output"] = "Sequence optimization log at C:\\Users\\another_user\\Desktop\\side_project\\logs\\opt.log Done."

    hash_base = stable_batch_hash(batch_base)
    hash_changed_paths = stable_batch_hash(batch_changed_paths)
    assert hash_base == hash_changed_paths

    # 2. Changing quantified results (e.g. mean_period or amplitudes) must change the stable hash
    batch_changed_results = deepcopy(batch_base)
    batch_changed_results["results"][0]["evaluation"]["mean_period"] = 2680.0
    assert hash_base != stable_batch_hash(batch_changed_results)

    # 3. Changing threshold/evaluator version must change the stable hash
    batch_changed_eval_ver = deepcopy(batch_base)
    batch_changed_eval_ver["runner"]["temporal_evaluator_version"] = "1.1"
    assert hash_base != stable_batch_hash(batch_changed_eval_ver)

    # 4. Test status aggregate in _batch_summary
    from application.design_task_benchmark import _batch_summary
    results = [
        {"status": "passed"},
        {"status": "provisional"},
        {"status": "unsupported"},
        {"status": "failed"},
    ]
    summary = _batch_summary(results)
    assert summary["passed_count"] == 1
    assert summary["provisional_count"] == 1
    assert summary["unsupported_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["pass_rate"] == 0.25


