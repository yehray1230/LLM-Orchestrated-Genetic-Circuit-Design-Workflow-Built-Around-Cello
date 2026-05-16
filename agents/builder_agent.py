from __future__ import annotations
import json
from schemas.state import DesignState
from agents.base import AgentProtocol
from utils.llm_utils import call_llm

def _build_system_prompt(state: DesignState) -> str:
    system_prompt = f"""You are Bio-Logic Architect, a synthetic biology design agent.

Goal:
- Convert the user's intent into three Cello-compatible genetic circuit design proposals.
- Keep designs combinational and suitable for Cello CAD technology mapping.
- Prefer designs that can later be translated to simple Verilog gates (`and`, `or`, `not`, `nand`, `nor`, `xor`, `xnor`, or `assign`).

Target host:
{state.host_organism}

User intent:
{state.user_intent}

Design constraints:
- Return exactly three proposals: `proposal_a`, `proposal_b`, and `proposal_c`.
- Proposal A should minimize biological part cost.
- Proposal B should minimize logic depth and delay.
- Proposal C should prioritize robustness or dynamic behavior while remaining Cello-compatible.
- Avoid sequential logic, delay syntax, clocks, memory elements, or Verilog constructs Cello cannot map.
- If you use motifs such as pulse-like behavior or feed-forward logic, describe them in a way the Translator can preserve as structural combinational logic.
- Include translator directives when a design requires structural instantiation rather than a simplified Boolean expression.

Output only valid JSON. No Markdown, no comments.

Required schema:
{{
  "proposal_a": {{
    "strategy_description": "short design rationale",
    "total_logic_depth": 2,
    "total_repressor_cost": 3,
    "logic_blueprint": "Y = A AND NOT B",
    "translator_directives": ["USE_STRUCTURAL_INSTANTIATION"]
  }},
  "proposal_b": {{
    "strategy_description": "short design rationale",
    "total_logic_depth": 1,
    "total_repressor_cost": 4,
    "logic_blueprint": "Y = A OR B",
    "translator_directives": []
  }},
  "proposal_c": {{
    "strategy_description": "short design rationale",
    "total_logic_depth": 3,
    "total_repressor_cost": 5,
    "logic_blueprint": "Y = ROBUST_COMBINATIONAL_MOTIF(A, B)",
    "translator_directives": ["PRESERVE_LOGIC"]
  }}
}}
"""
    try:
        try:
            with open("skill.json", "r", encoding="utf-8") as f:
                skill_library = f.read()
        except FileNotFoundError:
            with open("邏輯設計skill.json", "r", encoding="utf-8") as f:
                skill_library = f.read()
        system_prompt += f"\nReusable design skill library:\n{skill_library}\n"
    except Exception:
        if getattr(state, "skill_library_context", None):
            system_prompt += f"\nReusable design skill context:\n{state.skill_library_context}\n"
    if state.rag_context:
        system_prompt += (
            f"\n=== Historical Design Rules & Constraints ===\n"
            f"{state.rag_context}\n"
            "在構建真值表與邏輯閘時，必須嚴格遵守上述提取的生物學與物理定律，避開已知的失敗模式 (Avoid Patterns)。\n"
        )

    if getattr(state, "seed_debate_transcript", None):
        system_prompt += (
            "\nPrevious debate and design iterations (for context):\n"
            f"{state.seed_debate_transcript}\n"
        )

    if state.latest_critic_feedback:
        system_prompt += (
            "\nCritic feedback to address in this revision:\n"
            f"{state.latest_critic_feedback}\n"
        )
        
    node_id = state.current_node_id
    if node_id and node_id in state.tree_nodes:
        mode = state.tree_nodes[node_id].search_mode
        system_prompt += f"\nCurrent Search Mode: {mode}\n"
        if mode == "Repair":
            system_prompt += "You are in REPAIR mode. You must rethink the logic based on the critic feedback.\n"

    return system_prompt

def call_builder(
    state: DesignState,
    api_key: str | None,
    model_name: str,
    api_base: str | None = None,
    force_zero_shot: bool = False,
    temperature: float = 0.7,
    **kwargs,
) -> DesignState:
    system_prompt = _build_system_prompt(state)
    user_content = (
        "Generate three alternative Cello-compatible genetic circuit proposals "
        "for the target intent. Output only the JSON object described in the system prompt."
    )

    response = call_llm(
        api_key=api_key,
        model_name=model_name,
        system_prompt=system_prompt,
        user_content=user_content,
        api_base=api_base,
        temperature=temperature,
        **kwargs
    )

    if response.startswith("ERROR:"):
        state.last_error = response
        return state

    try:
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            json_str = response[start : end + 1]
            data = json.loads(json_str)
            proposals = [
                json.dumps(value, ensure_ascii=False)
                for value in data.values()
                if isinstance(value, dict)
            ]
            
            node_id = state.current_node_id
            if node_id and node_id in state.tree_nodes:
                node = state.tree_nodes[node_id]
                node.logic_proposals = proposals or [json_str]
                node.current_topology = node.logic_proposals[0] if node.logic_proposals else ""
                state.logic_proposals = node.logic_proposals
                state.current_topology = node.current_topology
            else:
                state.logic_proposals = proposals or [json_str]
                state.current_topology = state.logic_proposals[0] if state.logic_proposals else ""
        else:
            state.logic_proposals = [response]
            if state.current_node_id and state.current_node_id in state.tree_nodes:
                state.tree_nodes[state.current_node_id].logic_proposals = state.logic_proposals

        state.last_error = None

    except Exception as exc:
        state.last_error = (
            f"ERROR: Builder response could not be parsed as JSON: {exc}\n"
            f"Raw response:\n{response}"
        )

    return state

class BuilderAgent(AgentProtocol):
    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        api_base: str | None = None,
        force_zero_shot: bool = False,
        **kwargs
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.api_base = api_base
        self.force_zero_shot = force_zero_shot
        self.kwargs = kwargs

    def run(self, state: DesignState) -> DesignState:
        state.iteration_count += 1
        state = call_builder(
            state=state,
            api_key=self.api_key,
            model_name=self.model_name,
            api_base=self.api_base,
            force_zero_shot=self.force_zero_shot,
            **self.kwargs
        )
        if state.last_error:
            state.is_completed = True
        return state
