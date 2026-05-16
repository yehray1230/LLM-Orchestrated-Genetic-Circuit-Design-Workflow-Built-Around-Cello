from __future__ import annotations

from pathlib import Path
from typing import Any

from schemas.state import DesignState
from agents.base import AgentProtocol
from exporters.obsidian_writer import write_skill_card


class SkillExtractorAgent(AgentProtocol):
    def __init__(
        self,
        vault_dir: str | Path | None = None,
        vector_db: Any | None = None,
        auto_write: bool = True,
    ):
        self.vault_dir = Path(vault_dir) if vault_dir else None
        self.vector_db = vector_db
        self.auto_write = auto_write

    def run(self, state: DesignState) -> DesignState:
        skill = self.extract_skill(state)
        if self.auto_write and self.vault_dir:
            path = write_skill_card(skill, self.vault_dir)
            skill["obsidian_path"] = str(path)
        if self.vector_db and hasattr(self.vector_db, "add"):
            self.vector_db.add(skill)
        if not hasattr(state, "extracted_skills"):
            state.extracted_skills = []
        state.extracted_skills.append(skill)
        return state

    def extract_skill(self, state: DesignState) -> dict:
        node = state.tree_nodes.get(state.current_node_id) if state.current_node_id else None
        score = node.score if node else 0.0
        topology = node.best_topology if node and node.best_topology else state.best_topology or {}
        failed_attempts = node.failed_attempts if node and node.failed_attempts else state.failed_attempts
        error_types = sorted({str(attempt.get("error_type")) for attempt in failed_attempts if attempt.get("error_type")})
        tags = _skill_tags(state, node, topology, error_types)
        return {
            "title": state.user_intent[:80] or "Untitled design skill",
            "summary": _skill_summary(state, node, topology, failed_attempts),
            "confidence_score": max(0.0, min(1.0, float(score) if score != -float("inf") else 0.0)),
            "source_node": state.current_node_id,
            "source_nodes": list(state.tree_nodes.keys()),
            "backlinks": [f"[[{attempt.get('node_id')}]]" for attempt in failed_attempts if attempt.get("node_id")],
            "tags": tags,
            "search_text": " ".join(
                [
                    state.user_intent,
                    state.host_organism,
                    str(topology.get("verilog", "")),
                    " ".join(error_types),
                    " ".join(node.critic_feedbacks if node else state.critic_feedbacks),
                ]
            ),
            "best_topology": _compact_topology(topology),
            "failed_attempts": failed_attempts,
        }


def _skill_tags(
    state: DesignState,
    node,
    topology: dict[str, Any],
    error_types: list[str],
) -> list[str]:
    tags = {
        "skill/genetic-circuit",
        f"host/{_slug(state.host_organism)}",
    }
    if node:
        tags.add(f"mode/{node.search_mode.lower()}")
        tags.add(f"status/{node.status.lower()}")
    for error_type in error_types:
        tags.add(f"failure/{error_type.lower().replace('_', '-')}")
    gate_count = topology.get("gate_count")
    if gate_count is not None:
        tags.add(f"gate-count/{gate_count}")
    if topology.get("mapping_status"):
        tags.add(f"mapping/{_slug(str(topology['mapping_status']))}")
    if topology.get("ode_status"):
        tags.add(f"ode/{_slug(str(topology['ode_status']))}")
    return sorted(tags)


def _skill_summary(
    state: DesignState,
    node,
    topology: dict[str, Any],
    failed_attempts: list[dict[str, Any]],
) -> str:
    feedbacks = node.critic_feedbacks if node else state.critic_feedbacks
    lines = [
        f"Intent: {state.user_intent or 'N/A'}",
        f"Host: {state.host_organism}",
        f"Source node: {state.current_node_id or 'N/A'}",
        f"Score: {node.score if node else topology.get('score', 0.0)}",
    ]
    if topology:
        lines.append(f"Best topology: {_compact_topology(topology)}")
    if feedbacks:
        lines.append(f"Latest critic feedback: {feedbacks[-1]}")
    if failed_attempts:
        failures = ", ".join(
            f"{attempt.get('node_id')}:{attempt.get('error_type')}" for attempt in failed_attempts[-5:]
        )
        lines.append(f"Recent failed attempts: {failures}")
    return "\n".join(lines)


def _compact_topology(topology: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "score",
        "mapping_status",
        "ode_status",
        "gate_count",
        "dynamic_margin",
        "metrics_cv",
        "metrics_max_burden",
        "verilog",
    ]
    return {key: topology[key] for key in keys if key in topology}


def _slug(value: str) -> str:
    return "-".join(value.lower().replace("_", "-").split())
