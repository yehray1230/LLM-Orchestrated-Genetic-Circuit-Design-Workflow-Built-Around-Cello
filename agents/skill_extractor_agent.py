
from __future__ import annotations

from schemas.state import DesignState
from agents.base import AgentProtocol


class SkillExtractorAgent(AgentProtocol):
    def run(self, state: DesignState) -> DesignState:
        return state

    def extract_skill(self, state: DesignState) -> dict:
        node = state.tree_nodes.get(state.current_node_id) if state.current_node_id else None
        score = node.score if node else 0.0
        return {
            "title": state.user_intent[:80] or "Untitled design skill",
            "summary": node.critic_feedbacks[-1] if node and node.critic_feedbacks else "",
            "confidence_score": max(0.0, min(1.0, float(score) if score != -float("inf") else 0.0)),
            "source_node": state.current_node_id,
        }
