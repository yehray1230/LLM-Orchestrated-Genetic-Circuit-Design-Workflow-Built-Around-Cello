from __future__ import annotations

import re
from typing import Any

from agents.base import AgentProtocol
from schemas.state import DesignState
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


class DataMinerAgent(AgentProtocol):
    def __init__(self, vector_retriever: Any | None = None, defaults: dict[str, dict[str, Any]] | None = None):
        self.vector_retriever = vector_retriever
        self.defaults = defaults or DEFAULT_BIOKINETIC_PARAMETERS

    def run(self, state: DesignState) -> DesignState:
        node = state.tree_nodes.get(state.current_node_id) if state.current_node_id else None
        topologies = node.candidate_topologies if node else state.candidate_topologies
        context = self._build_context(state)

        for topology in topologies:
            parameters = self._default_parameters()
            parameters.update(self._parameters_from_records(context))
            gene_count = self._infer_gene_count(topology)
            source_summary = _parameter_source_summary(parameters)
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
                    "source_summary": source_summary,
                    "all_parameters_have_external_source": source_summary.get("conservative_default", 0) == 0,
                    "unit_system": "nM and seconds",
                },
            }

        state.biokinetic_context = {
            "host": state.host_organism,
            "unit_system": "nM and seconds",
            "parameter_keys": sorted(self.defaults.keys()),
            "data_miner_enabled": True,
        }
        if node:
            node.candidate_topologies = topologies
        state.candidate_topologies = topologies
        state.last_error = None
        return state

    def _default_parameters(self) -> dict[str, dict[str, Any]]:
        return {key: value.copy() for key, value in self.defaults.items()}

    def _build_context(self, state: DesignState) -> str:
        pieces = [state.user_intent, state.host_organism]
        pieces.extend(state.logic_proposals)
        pieces.extend(state.verilog_codes)
        return " ".join(piece for piece in pieces if piece)

    def _parameters_from_records(self, context: str) -> dict[str, dict[str, Any]]:
        if not self.vector_retriever:
            return {}
        overrides: dict[str, dict[str, Any]] = {}
        for record in self.vector_retriever.search(context, k=8):
            normalized = self._normalize_record(record)
            if normalized:
                overrides[normalized[0]] = normalized[1]
        return overrides

    def _normalize_record(self, record: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
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
        return key, {
            "value": normalized.value,
            "unit": normalized.unit,
            "raw_value": value,
            "raw_unit": unit,
            "source": str(record.get("source") or "local_vector_record"),
            "confidence": float(record.get("confidence", record.get("confidence_score", 0.65))),
        }

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
