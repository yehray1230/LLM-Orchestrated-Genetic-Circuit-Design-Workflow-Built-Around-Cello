from __future__ import annotations

import re
from typing import Any

from agents.base import AgentProtocol
from schemas.state import DesignState
from schemas.parameter_governance import (
    normalize_parameter_metadata,
    summarize_parameter_governance,
)
from utils.unit_conversion import normalize_biokinetic_value


DEFAULT_BIOKINETIC_PARAMETERS: dict[str, dict[str, Any]] = {
    "rnap_total": {"value": 5000.0, "unit": "nM", "source": "conservative_default", "confidence": 0.45},
    "ribosome_total": {"value": 25000.0, "unit": "nM", "source": "conservative_default", "confidence": 0.45},
    "km_rnap": {"value": 75.0, "unit": "nM", "source": "conservative_default", "confidence": 0.45},
    "km_ribosome": {"value": 120.0, "unit": "nM", "source": "conservative_default", "confidence": 0.45},
    "transcription_rate": {"value": 0.08, "unit": "nM/s", "source": "conservative_default", "confidence": 0.45},
    "translation_rate": {"value": 0.045, "unit": "1/s", "source": "conservative_default", "confidence": 0.45},
    "mrna_degradation_rate": {"value": 0.0038, "unit": "1/s", "source": "conservative_default", "confidence": 0.45},
    "protein_degradation_rate": {"value": 0.00058, "unit": "1/s", "source": "conservative_default", "confidence": 0.45},
    "kd": {"value": 50.0, "unit": "nM", "source": "conservative_default", "confidence": 0.45},
    "hill_coefficient": {"value": 2.0, "unit": "dimensionless", "source": "conservative_default", "confidence": 0.45},
    "leak_fraction": {"value": 0.02, "unit": "dimensionless", "source": "conservative_default", "confidence": 0.45},
    "burden_soft_limit": {"value": 45000.0, "unit": "nM", "source": "conservative_default", "confidence": 0.45},
    "toxicity_threshold": {"value": 65000.0, "unit": "nM", "source": "conservative_default", "confidence": 0.45},
    "growth_rate_dilution": {"value": 0.0004, "unit": "1/s", "source": "conservative_default", "confidence": 0.45},
}


PARAMETER_ALIASES = {
    "rnap": "rnap_total",
    "rnap_total": "rnap_total",
    "ribosome": "ribosome_total",
    "ribosome_total": "ribosome_total",
    "kd": "kd",
    "k_d": "kd",
    "transcription_rate": "transcription_rate",
    "translation_rate": "translation_rate",
    "mrna_degradation_rate": "mrna_degradation_rate",
    "protein_degradation_rate": "protein_degradation_rate",
    "km_rnap": "km_rnap",
    "km_ribosome": "km_ribosome",
}


CHASSIS_SPECIFIC_DEFAULTS = {
    "Escherichia coli": {
        "rnap_total": 5000.0,
        "ribosome_total": 25000.0,
        "translation_rate": 0.045,
        "growth_rate_dilution": 0.0004,
    },
    "Saccharomyces cerevisiae": {
        "rnap_total": 3000.0,
        "ribosome_total": 120000.0,
        "translation_rate": 0.012,
        "growth_rate_dilution": 0.0001,
    }
}

def _normalize_chassis(chassis: str) -> str:
    ch = str(chassis).lower().strip()
    if "yeast" in ch or "cerevisiae" in ch:
        return "Saccharomyces cerevisiae"
    if "coli" in ch:
        return "Escherichia coli"
    return "Escherichia coli"

class DataMinerAgent(AgentProtocol):
    def __init__(self, vector_retriever: Any | None = None, defaults: dict[str, dict[str, Any]] | None = None):
        self.vector_retriever = vector_retriever
        self.defaults = defaults or DEFAULT_BIOKINETIC_PARAMETERS

    def run(self, state: DesignState) -> DesignState:
        node = state.tree_nodes.get(state.current_node_id) if state.current_node_id else None
        topologies = node.candidate_topologies if node else state.candidate_topologies
        context = self._build_context(state)

        for topology in topologies:
            chassis_raw = topology.get("chassis") or state.host_organism
            parameters = self._default_parameters(host=str(chassis_raw))
            chassis_normalized = _normalize_chassis(chassis_raw)
            if chassis_normalized in CHASSIS_SPECIFIC_DEFAULTS:
                spec_vals = CHASSIS_SPECIFIC_DEFAULTS[chassis_normalized]
                for p_key, p_val in spec_vals.items():
                    if p_key in parameters:
                        parameters[p_key]["value"] = p_val
                        if chassis_normalized != "Escherichia coli":
                            parameters[p_key]["source"] = "chassis_specific_default"
                            parameters[p_key]["confidence"] = 0.65
                            parameters[p_key] = normalize_parameter_metadata(
                                parameters[p_key],
                                default_origin="default",
                                default_context=_measurement_context(str(chassis_raw)),
                            )
            parameters.update(self._parameters_from_records(context, host=str(chassis_raw)))
            gene_count = self._infer_gene_count(topology)
            governance_summary = summarize_parameter_governance(parameters)
            topology["biokinetic_parameters"] = {
                "host": state.host_organism,
                "gene_count": gene_count,
                "parameters": parameters,
                "mining_summary": {
                    "source": "DataMinerAgent",
                    "records_used": [
                        value["source"]
                        for value in parameters.values()
                        if value.get("source") != "conservative_default"
                    ],
                    **governance_summary,
                    "all_parameters_have_external_source": governance_summary["source_summary"].get("conservative_default", 0) == 0,
                    "unit_system": "nM and seconds",
                },
            }

        state.biokinetic_context = {
            "host": state.host_organism,
            "unit_system": "nM and seconds",
            "parameter_keys": sorted(self.defaults.keys()),
            "data_miner_enabled": True,
            "data_boundary": "public_defaults_with_optional_local_private_overrides",
        }
        if node:
            node.candidate_topologies = topologies
        state.candidate_topologies = topologies
        state.last_error = None
        return state

    def _default_parameters(self, *, host: str) -> dict[str, dict[str, Any]]:
        return {
            key: normalize_parameter_metadata(
                value,
                default_origin="default",
                default_context=_measurement_context(host),
            )
            for key, value in self.defaults.items()
        }

    def _build_context(self, state: DesignState) -> str:
        pieces = [state.user_intent, state.host_organism]
        pieces.extend(state.logic_proposals)
        pieces.extend(state.verilog_codes)
        return " ".join(piece for piece in pieces if piece)

    def _parameters_from_records(self, context: str, *, host: str) -> dict[str, dict[str, Any]]:
        if not self.vector_retriever:
            return {}
        overrides: dict[str, dict[str, Any]] = {}
        for record in self.vector_retriever.search(context, k=8):
            normalized = self._normalize_record(record, host=host)
            if normalized:
                overrides[normalized[0]] = normalized[1]
        return overrides

    def _normalize_record(self, record: dict[str, Any], *, host: str) -> tuple[str, dict[str, Any]] | None:
        raw_name = str(record.get("name") or record.get("parameter") or record.get("key") or "").lower()
        key = PARAMETER_ALIASES.get(raw_name)
        if not key:
            return None
        value = record.get("value", record.get("normalized_value"))
        unit = str(record.get("unit") or "").strip()
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        normalized = normalize_biokinetic_value(value, unit)
        return key, normalize_parameter_metadata({
            "value": normalized.value,
            "unit": normalized.unit,
            "raw_value": value,
            "raw_unit": unit,
            "source": str(record.get("source") or "local_vector_record"),
            "confidence": float(record.get("confidence", record.get("confidence_score", 0.65))),
            "parameter_origin": record.get("parameter_origin"),
            "confidence_category": record.get("confidence_category"),
            "measurement_context": record.get("measurement_context"),
            "data_boundary": record.get("data_boundary"),
        }, default_origin="inferred", default_context=_measurement_context(host), is_override=True)

    def _infer_gene_count(self, topology: dict[str, Any]) -> int:
        if topology.get("gate_count"):
            return max(1, int(topology["gate_count"]))
        verilog = str(topology.get("verilog") or "")
        primitive_count = len(re.findall(r"\b(and|or|not|nand|nor|xor|xnor)\s*\(", verilog))
        assign_count = len(re.findall(r"\bassign\b", verilog))
        return max(1, primitive_count + assign_count)


def _parameter_source_summary(parameters: dict[str, dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for parameter in parameters.values():
        source = str(parameter.get("source") or "unknown")
        summary[source] = summary.get(source, 0) + 1
    return summary


def _measurement_context(host: str) -> dict[str, Any]:
    return {
        "host": host or "unknown",
        "unit_system": "nM and seconds",
        "context_scope": "computational_screening",
    }
