from __future__ import annotations

from benchmark_suite.parameter_fitting import (
    fit_hill_response,
    fitted_parameters_to_part_override,
    load_plate_reader_csv,
)
from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from fastapi.testclient import TestClient


def _csv_text() -> str:
    return """concentration,response,replicate,condition
0,10,r1,IPTG
0.1,13.8,r1,IPTG
0.3,30,r1,IPTG
1,60,r1,IPTG
3,86.2,r1,IPTG
10,98,r1,IPTG
"""


def test_plate_reader_csv_import_validates_required_columns() -> None:
    points = load_plate_reader_csv(_csv_text())

    assert len(points) == 6
    assert points[0].concentration == 0.0
    assert points[-1].metadata["condition"] == "IPTG"


def test_hill_fitting_returns_governed_local_override_parameters() -> None:
    points = load_plate_reader_csv(_csv_text())
    fit = fit_hill_response(
        points,
        measurement_context={
            "host": "Escherichia coli",
            "measurement_type": "fluorescence",
        },
    )

    assert fit.status == "completed"
    assert fit.metrics["r_squared"] > 0.95
    assert fit.parameters["kd"]["parameter_origin"] == "inferred"
    assert fit.parameters["kd"]["data_boundary"] == "local_private"
    assert fit.parameters["kd"]["is_override"] is True
    assert fit.parameters["hill_coefficient"]["value"] > 0.2
    assert fit.tool_record["tool_name"] == "scipy"


def test_fitted_parameters_create_part_override_snapshot() -> None:
    fit = fit_hill_response(load_plate_reader_csv(_csv_text()))

    override = fitted_parameters_to_part_override(
        part_id="pTet_response",
        fit=fit,
        snapshot_id="local_fit_snapshot_001",
    )

    assert override["part_id"] == "pTet_response"
    assert override["snapshot_id"] == "local_fit_snapshot_001"
    assert override["update_policy"] == "override_only_do_not_replace_source_defaults"
    assert override["parameters"]["kd"]["override_policy"] == "do_not_replace_defaults_silently"


def test_parameter_fit_snapshot_service_persists_local_private_override(tmp_path) -> None:
    services = create_application_services(tmp_path / "api_data")

    created = services.evaluations.create_parameter_fit_snapshot(
        {
            "part_id": "pTet_response",
            "snapshot_id": "fit_snapshot_001",
            "csv_content": _csv_text(),
            "measurement_context": {"host": "Escherichia coli"},
        }
    )
    fetched = services.evaluations.parameter_fit_snapshot("fit_snapshot_001")

    assert created["snapshot_id"] == "fit_snapshot_001"
    assert created["data_boundary"] == "local_private"
    assert fetched is not None
    assert fetched["override"]["parameters"]["kd"]["is_override"] is True


def test_parameter_fit_snapshot_api_contract(tmp_path) -> None:
    services = create_application_services(tmp_path / "api_data")
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/benchmarks/parameter-fits",
                json={
                    "part_id": "pTet_response",
                    "snapshot_id": "fit_api_snapshot_001",
                    "csv_content": _csv_text(),
                    "measurement_context": {"host": "Escherichia coli"},
                },
            )
            listed = client.get("/api/v1/benchmarks/parameter-fits")
            fetched = client.get(
                "/api/v1/benchmarks/parameter-fits/fit_api_snapshot_001"
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["data"]["override"]["part_id"] == "pTet_response"
    assert listed.json()["data"]["count"] == 1
    assert fetched.json()["data"]["snapshot_id"] == "fit_api_snapshot_001"


def test_simulation_api_applies_parameter_fit_snapshot_explicitly(tmp_path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.evaluations.create_parameter_fit_snapshot(
        {
            "part_id": "pTet_response",
            "snapshot_id": "fit_for_simulation",
            "csv_content": _csv_text(),
            "measurement_context": {"host": "Escherichia coli"},
        }
    )
    topology = {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "0", "Y": "0"},
            {"A": "1", "Y": "1"},
        ],
    }
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            simulated = client.post(
                "/api/v1/simulations",
                json={
                    "topology": topology,
                    "parameter_fit_snapshot_id": "fit_for_simulation",
                    "simulation_time": 30,
                    "sample_count": 8,
                    "random_seed": 7,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert simulated.status_code == 200
    candidate = simulated.json()["data"]["candidate"]
    assert candidate["applied_parameter_fit_snapshot"]["snapshot_id"] == "fit_for_simulation"
    assert candidate["biokinetic_parameters"]["parameters"]["kd"]["is_override"] is True
    assert candidate["parameter_provenance"]["local_private_parameter_count"] >= 4


def test_simulation_comparison_service_calculates_deltas(tmp_path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.evaluations.create_parameter_fit_snapshot(
        {
            "part_id": "pTet_response",
            "snapshot_id": "fit_for_comparison",
            "csv_content": _csv_text(),
            "measurement_context": {"host": "Escherichia coli"},
        }
    )
    topology = {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "0", "Y": "0"},
            {"A": "1", "Y": "1"},
        ],
    }

    report = services.simulations.compare_default_vs_fitted(
        topology,
        snapshot_id="fit_for_comparison",
        simulation_time=30,
        sample_count=8,
        random_seed=7,
    )

    assert report["topology_id"] == "unknown"
    assert report["report_type"] == "parameter_fit_snapshot_comparison"
    assert report["report_id"].startswith("snapshot_comparison_")
    assert report["report_hash"]
    assert report["simulation_config"]["simulation_model_id"]
    assert report["snapshot_id"] == "fit_for_comparison"
    assert report["part_id"] == "pTet_response"
    assert "default_run" in report
    assert "fitted_run" in report
    assert "comparison" in report

    comp = report["comparison"]
    assert comp["dynamic_margin_delta"] is not None
    assert comp["signal_to_noise_ratio_delta"] is not None
    assert comp["kinetic_score_delta"] is not None
    assert comp["provenance_changes"]["local_private_count_after"] >= 4
    deltas = {item["metric"]: item for item in report["metric_deltas"]}
    assert deltas["dynamic_margin"]["delta"] == comp["dynamic_margin_delta"]
    assert deltas["signal_to_noise_ratio"]["delta"] == comp["signal_to_noise_ratio_delta"]
    assert deltas["kinetic_score"]["delta"] == comp["kinetic_score_delta"]
    assert report["provenance_delta"]["counts"]["local_private_parameter_count"][
        "delta"
    ] >= 4
    assert report["interpretation"]["status"] == "complete"


def test_simulation_comparison_api_endpoint(tmp_path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.evaluations.create_parameter_fit_snapshot(
        {
            "part_id": "pTet_response",
            "snapshot_id": "fit_for_comparison_api",
            "csv_content": _csv_text(),
            "measurement_context": {"host": "Escherichia coli"},
        }
    )
    topology = {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "0", "Y": "0"},
            {"A": "1", "Y": "1"},
        ],
    }
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/simulations/compare-snapshot",
                json={
                    "topology": topology,
                    "parameter_fit_snapshot_id": "fit_for_comparison_api",
                    "simulation_time": 30,
                    "sample_count": 8,
                    "random_seed": 7,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["snapshot_id"] == "fit_for_comparison_api"
    assert data["report_type"] == "parameter_fit_snapshot_comparison"
    assert data["comparison"]["dynamic_margin_delta"] is not None
    assert {item["metric"] for item in data["metric_deltas"]} == {
        "dynamic_margin",
        "signal_to_noise_ratio",
        "kinetic_score",
    }


def test_parameter_fit_snapshot_comparison_report_endpoint(tmp_path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.evaluations.create_parameter_fit_snapshot(
        {
            "part_id": "pTet_response",
            "snapshot_id": "fit_for_report_api",
            "csv_content": _csv_text(),
            "measurement_context": {"host": "Escherichia coli"},
        }
    )
    topology = {
        "topology_id": "report_topology_001",
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "0", "Y": "0"},
            {"A": "1", "Y": "1"},
        ],
    }
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/benchmarks/parameter-fits/fit_for_report_api/comparison",
                json={
                    "topology": topology,
                    "simulation_time": 30,
                    "sample_count": 8,
                    "random_seed": 7,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["warnings"]
    data = payload["data"]
    assert data["topology_id"] == "report_topology_001"
    assert data["snapshot"]["snapshot_id"] == "fit_for_report_api"
    assert data["default_run"]["parameter_provenance"]
    assert data["fitted_run"]["parameter_provenance"]
    assert data["provenance_delta"]["counts"]["local_private_parameter_count"][
        "delta"
    ] >= 4
