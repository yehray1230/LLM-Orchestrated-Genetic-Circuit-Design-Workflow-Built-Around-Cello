from __future__ import annotations

from fastapi.testclient import TestClient
from pathlib import Path

from api.dependencies import get_services
from api.main import app
from api.v2_schemas import HostProfileRegistrationRequest
from application.services import create_application_services
from schemas.host_profile import (
    default_ecoli_profile,
    default_yeast_profile,
    default_mammalian_profile,
    apply_host_profile_to_topology,
    host_profile_from_dict,
)


def test_host_profiles_have_biophysical_constants() -> None:
    ecoli = default_ecoli_profile()
    yeast = default_yeast_profile()
    mammalian = default_mammalian_profile()

    assert ecoli.host_organism == "Escherichia coli"
    assert ecoli.rnap_total == 5000.0
    assert ecoli.growth_rate_dilution == 0.0004

    assert yeast.host_organism == "Saccharomyces cerevisiae"
    assert yeast.rnap_total == 3000.0
    assert yeast.growth_rate_dilution == 0.0001

    assert mammalian.host_organism == "Homo sapiens"
    assert mammalian.rnap_total == 1500.0
    assert mammalian.growth_rate_dilution == 0.00001


def test_host_profile_registration_schema_accepts_biophysical_parameters() -> None:
    request = HostProfileRegistrationRequest(
        profile_id="custom_host",
        name="Custom host",
        host_organism="Example host",
        rnap_total=4200.0,
        ribosome_total=90000.0,
        transcription_rate=0.04,
        translation_rate=0.02,
        mrna_degradation_rate=0.001,
        protein_degradation_rate=0.0001,
        growth_rate_dilution=0.0002,
        km_rnap=60.0,
        km_ribosome=140.0,
        burden_soft_limit=100000.0,
        toxicity_threshold=150000.0,
    )

    profile = host_profile_from_dict(request.model_dump())

    assert profile.rnap_total == 4200.0
    assert profile.ribosome_total == 90000.0
    assert profile.toxicity_threshold == 150000.0


def test_apply_host_profile_to_topology() -> None:
    topology = {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [{"A": "0", "Y": "0"}, {"A": "1", "Y": "1"}],
    }
    yeast = default_yeast_profile()
    applied = apply_host_profile_to_topology(topology, yeast)

    biokinetic = applied["biokinetic_parameters"]
    assert biokinetic["host"] == "Saccharomyces cerevisiae"
    
    parameters = biokinetic["parameters"]
    assert parameters["rnap_total"]["value"] == 3000.0
    assert parameters["rnap_total"]["source"] == "host_profile:yeast_sc_default"
    assert parameters["rnap_total"]["parameter_origin"] == "default"
    assert parameters["rnap_total"]["confidence_category"] == "default"
    assert parameters["rnap_total"]["data_boundary"] == "public"
    assert parameters["rnap_total"]["measurement_context"]["host_profile_id"] == "yeast_sc_default"
    
    assert parameters["growth_rate_dilution"]["value"] == 0.0001
    assert biokinetic["mining_summary"]["origin_summary"]["default"] > 0


def test_simulation_service_applies_host_profile(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    topology = {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [{"A": "0", "Y": "0"}, {"A": "1", "Y": "1"}],
    }

    # Simulate with default (E. coli K-12)
    res_ecoli = services.simulations.simulate(
        topology,
        simulation_time=30,
        sample_count=8,
        host_profile_id="ecoli_k12_default",
    )
    cand_ecoli = res_ecoli["candidate"]
    assert cand_ecoli["biokinetic_parameters"]["host"] == "Escherichia coli"
    assert cand_ecoli["biokinetic_parameters"]["parameters"]["rnap_total"]["value"] == 5000.0

    # Simulate with Mammalian
    res_mammalian = services.simulations.simulate(
        topology,
        simulation_time=30,
        sample_count=8,
        host_profile_id="mammalian_cho_default",
    )
    cand_mammalian = res_mammalian["candidate"]
    assert cand_mammalian["biokinetic_parameters"]["host"] == "Homo sapiens"
    assert cand_mammalian["biokinetic_parameters"]["parameters"]["rnap_total"]["value"] == 1500.0


def test_api_route_applies_host_profile(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    topology = {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [{"A": "0", "Y": "0"}, {"A": "1", "Y": "1"}],
    }

    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/simulations",
                json={
                    "topology": topology,
                    "host_profile_id": "yeast_sc_default",
                    "simulation_time": 30,
                    "sample_count": 8,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    candidate = payload["data"]["candidate"]
    assert candidate["biokinetic_parameters"]["host"] == "Saccharomyces cerevisiae"
    assert candidate["biokinetic_parameters"]["parameters"]["rnap_total"]["value"] == 3000.0
