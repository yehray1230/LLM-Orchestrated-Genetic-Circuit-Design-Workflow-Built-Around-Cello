from __future__ import annotations

import importlib.util
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from schemas.state import DesignState
from tools.cello_wrapper import CelloWrapper
from tools.ode_simulator import BatchODESimulator


CAPABILITY_LOGIC_SYNTHESIS = "logic_synthesis"
CAPABILITY_ODE_SIMULATION = "ode_simulation"
CAPABILITY_STOCHASTIC_SIMULATION = "stochastic_simulation"
CAPABILITY_CRN_COMPILATION = "crn_compilation"
CAPABILITY_RNA_FOLDING = "rna_folding"
CAPABILITY_SEQUENCE_OPTIMIZATION = "sequence_optimization"
CAPABILITY_ASSEMBLY_SIMULATION = "assembly_simulation"
CAPABILITY_PRIMER_DESIGN = "primer_design"
CAPABILITY_OFF_TARGET_SCREENING = "off_target_screening"
CAPABILITY_HOMOLOGY_SCREENING = "homology_screening"
CAPABILITY_FORMAT_VALIDATION = "format_validation"
CAPABILITY_SEQUENCE_ANNOTATION = "sequence_annotation"


CAPABILITY_CATALOG: dict[str, dict[str, Any]] = {
    CAPABILITY_LOGIC_SYNTHESIS: {
        "description": "Map logic designs to genetic circuit assignments.",
        "preferred_tools": ["cello"],
        "fallback": "mock_cello_wrapper",
    },
    CAPABILITY_ODE_SIMULATION: {
        "description": "Run deterministic ODE simulation over candidate topologies.",
        "preferred_tools": ["scipy"],
        "fallback": "internal_rk4",
    },
    CAPABILITY_STOCHASTIC_SIMULATION: {
        "description": "Run stochastic verification for sequential or noisy designs.",
        "preferred_tools": ["bioscrape"],
        "fallback": None,
    },
    CAPABILITY_CRN_COMPILATION: {
        "description": "Compile biological designs into CRN/SBML-like models.",
        "preferred_tools": ["biocrnpyler"],
        "fallback": "local_ode_abstractions",
    },
    CAPABILITY_RNA_FOLDING: {
        "description": "Estimate RNA structure or accessibility.",
        "preferred_tools": ["viennarna", "nupack"],
        "fallback": "heuristic_warning",
    },
    CAPABILITY_SEQUENCE_OPTIMIZATION: {
        "description": "Repair sequence constraints and optimize host compatibility.",
        "preferred_tools": ["dna_chisel"],
        "fallback": "local_sequence_optimization",
    },
    CAPABILITY_ASSEMBLY_SIMULATION: {
        "description": "Simulate construct assembly and cloning plans.",
        "preferred_tools": ["dna_cauldron"],
        "fallback": "local_assembly_planner",
    },
    CAPABILITY_PRIMER_DESIGN: {
        "description": "Design assembly or PCR primers.",
        "preferred_tools": ["primer3"],
        "fallback": "local_primer_designer",
    },
    CAPABILITY_OFF_TARGET_SCREENING: {
        "description": "Screen guide-like sequences for potential off-targets.",
        "preferred_tools": ["cas-offinder"],
        "fallback": "deterministic_precheck",
        "license_sensitive": True,
    },
    CAPABILITY_HOMOLOGY_SCREENING: {
        "description": "Screen sequences against local homology databases.",
        "preferred_tools": ["blastn", "bowtie"],
        "fallback": "exact_match_scan",
    },
    CAPABILITY_FORMAT_VALIDATION: {
        "description": "Validate biological exchange formats such as SBOL.",
        "preferred_tools": ["sbol3"],
        "fallback": "export_with_warning",
    },
    CAPABILITY_SEQUENCE_ANNOTATION: {
        "description": "Parse and annotate GenBank or sequence features.",
        "preferred_tools": ["biopython"],
        "fallback": "local_importers_exporters",
    },
}


@dataclass
class ToolWarning:
    code: str
    message: str
    severity: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolAvailability:
    tool_name: str
    adapter_name: str
    capability: str
    status: str
    version: str | None = None
    fallback_available: bool = False
    fallback_used: bool = False
    license_sensitive: bool = False
    warnings: list[ToolWarning] = field(default_factory=list)
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = [warning.to_dict() for warning in self.warnings]
        return payload


@dataclass
class ToolAdapterResult:
    availability: ToolAvailability
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    warnings: list[ToolWarning] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "availability": self.availability.to_dict(),
            "status": self.status,
            "output": self.output,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


class ToolAdapter(Protocol):
    tool_name: str
    adapter_name: str
    capability: str

    def available(self) -> ToolAvailability:
        ...

    def validate_input(self, payload: dict[str, Any]) -> list[ToolWarning]:
        ...

    def run(self, payload: dict[str, Any]) -> ToolAdapterResult:
        ...


def normalize_tool_warning(
    code: str,
    message: str,
    severity: str = "warning",
) -> ToolWarning:
    return ToolWarning(
        code=str(code).strip().upper().replace(" ", "_") or "TOOL_WARNING",
        message=str(message).strip() or "Tool warning.",
        severity=str(severity or "warning"),
    )


def detect_python_module(
    module_name: str,
    *,
    tool_name: str,
    adapter_name: str,
    capability: str,
    fallback_available: bool = False,
    license_sensitive: bool = False,
) -> ToolAvailability:
    if importlib.util.find_spec(module_name) is None:
        warnings = [
            normalize_tool_warning(
                "TOOL_UNAVAILABLE",
                f"Optional Python module '{module_name}' is not installed.",
            )
        ]
        return ToolAvailability(
            tool_name=tool_name,
            adapter_name=adapter_name,
            capability=capability,
            status="unavailable",
            fallback_available=fallback_available,
            license_sensitive=license_sensitive,
            warnings=warnings,
        )
    return ToolAvailability(
        tool_name=tool_name,
        adapter_name=adapter_name,
        capability=capability,
        status="available",
        fallback_available=fallback_available,
        license_sensitive=license_sensitive,
    )


def detect_cli_tool(
    executable: str,
    *,
    tool_name: str,
    adapter_name: str,
    capability: str,
    fallback_available: bool = False,
    license_sensitive: bool = False,
) -> ToolAvailability:
    if shutil.which(executable) is None:
        return ToolAvailability(
            tool_name=tool_name,
            adapter_name=adapter_name,
            capability=capability,
            status="unavailable",
            fallback_available=fallback_available,
            license_sensitive=license_sensitive,
            warnings=[
                normalize_tool_warning(
                    "TOOL_UNAVAILABLE",
                    f"Optional executable '{executable}' was not found on PATH.",
                )
            ],
        )
    return ToolAvailability(
        tool_name=tool_name,
        adapter_name=adapter_name,
        capability=capability,
        status="available",
        fallback_available=fallback_available,
        license_sensitive=license_sensitive,
    )


class CelloLogicSynthesisAdapter:
    tool_name = "cello"
    adapter_name = "cello_wrapper"
    capability = CAPABILITY_LOGIC_SYNTHESIS

    def __init__(self, wrapper: CelloWrapper | None = None):
        self.wrapper = wrapper or CelloWrapper()

    def available(self) -> ToolAvailability:
        if self.wrapper.cello_command is None:
            return ToolAvailability(
                tool_name=self.tool_name,
                adapter_name=self.adapter_name,
                capability=self.capability,
                status="fallback",
                fallback_available=True,
                fallback_used=True,
                warnings=[
                    normalize_tool_warning(
                        "FALLBACK_USED",
                        "Cello command is not configured; using mock Cello fallback.",
                    )
                ],
            )
        executable = (
            self.wrapper.cello_command[0]
            if isinstance(self.wrapper.cello_command, list)
            else str(self.wrapper.cello_command).split()[0]
        )
        return detect_cli_tool(
            executable,
            tool_name=self.tool_name,
            adapter_name=self.adapter_name,
            capability=self.capability,
            fallback_available=True,
        )

    def validate_input(self, payload: dict[str, Any]) -> list[ToolWarning]:
        if not payload.get("state") and not payload.get("verilog"):
            return [
                normalize_tool_warning(
                    "MISSING_INPUT",
                    "Cello adapter needs a DesignState or a Verilog string.",
                    "error",
                )
            ]
        return []

    def run(self, payload: dict[str, Any]) -> ToolAdapterResult:
        validation_warnings = self.validate_input(payload)
        if any(warning.severity == "error" for warning in validation_warnings):
            availability = self.available()
            return ToolAdapterResult(
                availability=availability,
                status="failed",
                warnings=validation_warnings + availability.warnings,
            )

        state = payload.get("state")
        if not isinstance(state, DesignState):
            state = DesignState()
            state.verilog_codes = [str(payload.get("verilog") or "")]

        result_state = self.wrapper.run(state)
        topology = (
            result_state.candidate_topologies[0]
            if result_state.candidate_topologies
            else {}
        )
        availability = self.available()
        status = "ok" if topology.get("mapping_status") == "mapped" else availability.status
        warnings = list(validation_warnings)
        warnings.extend(availability.warnings)
        if topology.get("cello_warning"):
            warnings.append(
                normalize_tool_warning("TOOL_WARNING", str(topology["cello_warning"]))
            )

        return ToolAdapterResult(
            availability=availability,
            status=status,
            output={"topology": topology},
            metrics={
                key: topology.get(key)
                for key in (
                    "orthogonality_score",
                    "cello_assignment_score",
                    "cello_buildable",
                    "toxicity",
                    "toxicity_score",
                )
                if key in topology
            },
            artifacts={
                key: topology.get(key)
                for key in ("cello_artifact_dir", "cello_artifact_manifest_path")
                if topology.get(key)
            },
            warnings=warnings,
        )


class ODESimulationAdapter:
    tool_name = "internal_ode_simulator"
    adapter_name = "batch_ode_simulator"
    capability = CAPABILITY_ODE_SIMULATION

    def __init__(self, simulator: BatchODESimulator | None = None):
        self.simulator = simulator or BatchODESimulator()

    def available(self) -> ToolAvailability:
        availability = detect_python_module(
            "scipy",
            tool_name=self.tool_name,
            adapter_name=self.adapter_name,
            capability=self.capability,
            fallback_available=True,
        )
        if availability.status == "unavailable":
            availability.status = "fallback"
            availability.fallback_used = True
            availability.warnings.append(
                normalize_tool_warning(
                    "FALLBACK_USED",
                    "SciPy is unavailable; using internal RK4 ODE integration fallback.",
                )
            )
        return availability

    def validate_input(self, payload: dict[str, Any]) -> list[ToolWarning]:
        if not isinstance(payload.get("topology"), dict):
            return [
                normalize_tool_warning(
                    "MISSING_INPUT",
                    "ODE adapter needs a topology dictionary.",
                    "error",
                )
            ]
        return []

    def run(self, payload: dict[str, Any]) -> ToolAdapterResult:
        validation_warnings = self.validate_input(payload)
        availability = self.available()
        if any(warning.severity == "error" for warning in validation_warnings):
            return ToolAdapterResult(
                availability=availability,
                status="failed",
                warnings=validation_warnings + availability.warnings,
            )
        topology = self.simulator.simulate_topology(dict(payload["topology"]))
        status = "ok" if topology.get("ode_status") == "simulated" else "failed"
        warnings = validation_warnings + availability.warnings
        if topology.get("ode_error"):
            warnings.append(normalize_tool_warning("TOOL_FAILED", topology["ode_error"]))
        return ToolAdapterResult(
            availability=availability,
            status=status,
            output={"topology": topology},
            metrics={
                key: topology.get(key)
                for key in (
                    "dynamic_margin",
                    "signal_to_noise_ratio",
                    "kinetic_score",
                    "max_burden_nM",
                )
                if key in topology
            },
            warnings=warnings,
        )


def default_tool_adapters() -> list[ToolAdapter]:
    return [CelloLogicSynthesisAdapter(), ODESimulationAdapter()]


def inspect_capabilities(adapters: list[ToolAdapter] | None = None) -> dict[str, Any]:
    selected = adapters or default_tool_adapters()
    records = [adapter.available().to_dict() for adapter in selected]
    return {
        "catalog": CAPABILITY_CATALOG,
        "tools": records,
        "capabilities": sorted({record["capability"] for record in records}),
    }
