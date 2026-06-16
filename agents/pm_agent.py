from __future__ import annotations

import json
import logging
import re
from types import ModuleType
from typing import Any
from uuid import uuid4

from schemas.state import DesignState

logger = logging.getLogger(__name__)

COMMON_BIOPARTS_KNOWLEDGE = """
=== Synthetic Biology Reference Knowledge ===
Common Host Organisms (Chassis):
- Escherichia coli (Standard prokaryotic host, fast growth, best gate compatibility)
- Saccharomyces cerevisiae (Yeast, standard eukaryotic host)

Common Biosensors (Inputs):
- Arsenic (Sensor: ArsR protein, Promoter: pArsR)
- IPTG (Sensor: LacI repressor, Promoter: pLac)
- aTc (Sensor: TetR repressor, Promoter: pTet)
- L-arabinose (Sensor: AraC regulator, Promoter: pBad)
- Salicylate (Sensor: NahR regulator, Promoter: psal)
- Temperature (Sensor: TlpA39 repressor, Promoter: pTlpA)
- Light (Sensor: PhyB/PIF or EL222, Promoter: pEL222)
- Herbicide / Glufosinate (Sensor: Glufosinate response system, Promoter: pBar)

Common Reporters (Outputs):
- sfGFP (Superfolder Green Fluorescent Protein, green fluorescence)
- mCherry / RFP (Red Fluorescent Protein, red fluorescence)
- LacZ (Beta-galactosidase, enzyme for visual assays)
- AmilCP (Blue chromoprotein, visible to naked eye without excitation)
"""

REQUIRED_FIELDS = ["chassis", "inputs", "outputs", "logic_relation", "copy_number"]

FIELD_LABELS = {
    "chassis": "Host chassis",
    "inputs": "Input sensors",
    "outputs": "Output reporters",
    "logic_relation": "Logic relation",
    "copy_number": "Copy number",
}

FIELD_FALLBACKS: dict[str, dict[str, Any]] = {
    "chassis": {
        "proposed_value": "Escherichia coli",
        "proposal_reason": (
            "E. coli is the safest default for this workflow because the current "
            "gate libraries and scoring assumptions are best aligned with it."
        ),
        "ui_message": "建議先使用 Escherichia coli 作為預設底盤，方便後續元件匹配與模擬。您同意嗎？",
    },
    "inputs": {
        "proposed_value": [
            {"name": "IPTG", "sensor_promoter": "pLac", "type": "input_sensor"}
        ],
        "proposal_reason": (
            "IPTG/pLac is a stable, familiar input sensor pair and is a good "
            "baseline when the user intent does not specify an inducer."
        ),
        "ui_message": "建議先用 IPTG/pLac 作為輸入感測器，建立可驗證的基準電路。您同意嗎？",
    },
    "outputs": {
        "proposed_value": [{"name": "sfGFP", "type": "reporter_gene"}],
        "proposal_reason": (
            "sfGFP is a robust reporter for early screening because it folds well "
            "and gives a clear fluorescence signal."
        ),
        "ui_message": "建議使用 sfGFP 作為預設輸出 reporter，方便後續評分與實驗檢查。您同意嗎？",
    },
    "logic_relation": {
        "proposed_value": "sfGFP = IPTG",
        "proposal_reason": (
            "A direct input-to-output relation is the simplest safe default when "
            "the desired Boolean relation has not been specified yet."
        ),
        "ui_message": "目前尚未指定邏輯關係，建議先用 sfGFP = IPTG 作為最小可行邏輯。您同意嗎？",
    },
    "copy_number": {
        "proposed_value": 15,
        "proposal_reason": (
            "A medium copy number balances expression strength against metabolic "
            "burden in early design screening."
        ),
        "ui_message": "建議先使用中等 copy number 15，在表現量與細胞負擔之間取得平衡。您同意嗎？",
    },
}


def _load_litellm() -> ModuleType:
    """Load LiteLLM only when the PM agent needs an LLM call."""
    try:
        import litellm
    except Exception as exc:  # pragma: no cover - depends on optional dependency state
        raise RuntimeError(
            "LiteLLM is unavailable or misconfigured; falling back to PM defaults."
        ) from exc
    return litellm


def _clean_json_response(raw_text: str) -> str:
    """Extract and clean JSON substring from LLM response."""
    raw_text = raw_text.strip()
    # Find matching {...} block
    match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_text


def _get_next_missing_field(spec: dict[str, Any]) -> str | None:
    """Identify the next required field that is missing or empty."""
    for field in REQUIRED_FIELDS:
        val = spec.get(field)
        if val is None or val == "" or (isinstance(val, list) and len(val) == 0):
            return field
    return None


def _field_status(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a UI-ready checklist for PM requirement elicitation."""
    next_missing = _get_next_missing_field(spec)
    items = []
    for field in REQUIRED_FIELDS:
        value = spec.get(field)
        confirmed = not (
            value is None
            or value == ""
            or (isinstance(value, list) and len(value) == 0)
        )
        items.append(
            {
                "field": field,
                "label": FIELD_LABELS[field],
                "status": (
                    "confirmed"
                    if confirmed
                    else "current"
                    if field == next_missing
                    else "pending"
                ),
                "value": value,
            }
        )
    return items


def _fallback_elicitation_proposal(
    missing_field: str,
    *,
    source: str = "fallback",
) -> dict[str, Any]:
    fallback = FIELD_FALLBACKS.get(missing_field, FIELD_FALLBACKS["chassis"])
    return {
        "proposal_id": f"pm_{missing_field}_{uuid4().hex[:8]}",
        "schema_version": "pm-proposal-v1",
        "source": source,
        "confidence": "medium" if source == "fallback" else "low",
        "missing_field": missing_field,
        "field_label": FIELD_LABELS.get(missing_field, missing_field),
        "proposed_value": fallback["proposed_value"],
        "proposal_reason": fallback["proposal_reason"],
        "ui_message": fallback["ui_message"],
        "field_status": [],
    }


def _normalize_elicitation_proposal(
    proposal: dict[str, Any],
    missing_field: str,
    spec: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    normalized = _fallback_elicitation_proposal(missing_field, source=source)
    if isinstance(proposal, dict):
        normalized["proposed_value"] = proposal.get(
            "proposed_value",
            normalized["proposed_value"],
        )
        normalized["proposal_reason"] = str(
            proposal.get("proposal_reason") or normalized["proposal_reason"]
        )
        normalized["ui_message"] = str(
            proposal.get("ui_message") or normalized["ui_message"]
        )
        if proposal.get("missing_field") == missing_field:
            normalized["missing_field"] = missing_field
    normalized["field_status"] = _field_status(spec)
    return normalized


def _fallback_hitl_proposal(*, source: str = "fallback") -> dict[str, Any]:
    return {
        "proposal_id": f"pm_hitl_{uuid4().hex[:8]}",
        "schema_version": "pm-hitl-v1",
        "source": source,
        "confidence": "medium" if source == "fallback" else "low",
        "error_summary_cn": "系統在搜尋最優電路時達到上限，或偵測到元件相容性與模型可信度風險。",
        "options": [
            {
                "option_id": "A",
                "label": "放寬元件正交性與代謝限制，追加 2 輪預算繼續搜尋",
                "constraints": [
                    "Relax orthogonality and metabolic constraints",
                    "Prioritize gate assignment success",
                ],
                "action": "Repair",
                "extra_budget": 2,
            },
            {
                "option_id": "B",
                "label": "改用較保守的設計策略，降低表現量或改變 promoter/gate 配置",
                "constraints": [
                    "Prefer lower burden parts",
                    "Allow promoter reassignment or lower copy number",
                ],
                "action": "Repair",
                "extra_budget": 2,
            },
            {
                "option_id": "C",
                "label": "接受目前最佳候選作為 fallback，並標記需要人工審查",
                "constraints": [],
                "action": "Accept_Fallback",
                "extra_budget": 0,
            },
        ],
        "ui_message": "系統目前遇到設計瓶頸，請選擇要修復、調整策略，或接受目前最佳候選。",
    }


def _normalize_hitl_proposal(
    proposal: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    normalized = _fallback_hitl_proposal(source=source)
    if isinstance(proposal, dict):
        normalized["error_summary_cn"] = str(
            proposal.get("error_summary_cn") or normalized["error_summary_cn"]
        )
        normalized["ui_message"] = str(
            proposal.get("ui_message") or normalized["ui_message"]
        )
        by_id = {
            str(option.get("option_id")): option
            for option in proposal.get("options", [])
            if isinstance(option, dict) and option.get("option_id")
        }
        merged = []
        for fallback in normalized["options"]:
            option = by_id.get(fallback["option_id"], {})
            merged.append(
                {
                    **fallback,
                    "label": str(option.get("label") or fallback["label"]),
                    "constraints": option.get("constraints")
                    if isinstance(option.get("constraints"), list)
                    else fallback["constraints"],
                    "action": str(option.get("action") or fallback["action"]),
                    "extra_budget": int(
                        option.get("extra_budget", fallback["extra_budget"]) or 0
                    ),
                }
            )
        normalized["options"] = merged
    return normalized


def call_pm_agent(
    state: DesignState,
    api_key: str | None,
    model_name: str,
    api_base: str | None = None,
    temperature: float = 0.2,
) -> DesignState:
    """
    Main entry point for PM Agent. Modifies DesignState in place or returns a new one.
    """
    # 1. Check if we are in HITL Dialogue mode (due to system pauses)
    if state.requires_human_input or state.pm_stage == "hitl_dialogue":
        state.pm_stage = "hitl_dialogue"
        return _run_hitl_translator(state, api_key, model_name, api_base, temperature)

    # 2. Check if we are in Requirement Elicitation mode
    if state.pm_stage == "elicitation":
        next_missing = _get_next_missing_field(state.structured_spec)
        if next_missing is None:
            # All specs gathered, transition to completed
            state.pm_stage = "completed"
            state.pending_proposal = {}
            if not any(msg.get("content", "").startswith("規格確認完畢") for msg in state.pm_chat_history):
                state.pm_chat_history.append({
                    "role": "assistant",
                    "content": "規格確認完畢，現在交由設計引擎開始建構與優化電路。"
                })
            return state
        
        return _run_requirement_elicitation(state, next_missing, api_key, model_name, api_base, temperature)

    return state


def _run_requirement_elicitation(
    state: DesignState,
    missing_field: str,
    api_key: str | None,
    model_name: str,
    api_base: str | None,
    temperature: float,
) -> DesignState:
    """
    Generate a default autocomplete proposal for the missing field.
    """
    system_prompt = f"""You are Bio-Design PM Agent, a synthetic biology product manager.
Your goal is to help a user complete their genetic circuit design specification.

Currently, we are missing the field: '{missing_field}'.
You must analyze the user's initial intent and the chat history, then consult the reference knowledge below to formulate ONE recommended default option.

{COMMON_BIOPARTS_KNOWLEDGE}

Rules:
1. Propose exactly ONE logical default value or configuration for '{missing_field}' that fits the context.
2. Provide a short, non-technical reason (under 3 sentences) explaining why this is chosen (e.g. to avoid cell toxicity, ensure parts compatibility, or keep scoring high).
3. Draft a friendly, concise message to the user asking for their confirmation.
4. DO NOT generate Verilog code or detailed gate connections.
5. Output ONLY a valid JSON object with the following schema:
{{
  "missing_field": "{missing_field}",
  "proposed_value": <any value or list appropriate for the field type>,
  "proposal_reason": "Explanation of the recommendation",
  "ui_message": "Friendly prompt asking user to confirm"
}}
"""
    # Truncate chat history to avoid token bloat while keeping the intro message
    if len(state.pm_chat_history) > 12:
        state.pm_chat_history = [state.pm_chat_history[0]] + state.pm_chat_history[-10:]

    chat_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state.pm_chat_history])
    user_content = f"""User Intent: {state.user_intent}
Current Structured Spec: {json.dumps(state.structured_spec)}
Dialogue History:
{chat_context}

    Please propose the default value for '{missing_field}' in JSON format."""

    try:
        litellm = _load_litellm()
        response = litellm.completion(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            api_key=api_key.strip() if api_key and api_key.strip() else None,
            api_base=api_base.strip() if api_base and api_base.strip() else None,
        )
        raw_output = response.choices[0].message["content"]
        cleaned_json = _clean_json_response(raw_output)
        proposal_dict = json.loads(cleaned_json)
        state.pending_proposal = _normalize_elicitation_proposal(
            proposal_dict,
            missing_field,
            state.structured_spec,
            source="llm",
        )
    except Exception as e:
        logger.error(f"Error in PM elicitation LLM call: {e}")
        state.pending_proposal = _normalize_elicitation_proposal(
            {},
            missing_field,
            state.structured_spec,
            source="fallback",
        )

    return state


def _run_hitl_translator(
    state: DesignState,
    api_key: str | None,
    model_name: str,
    api_base: str | None,
    temperature: float,
) -> DesignState:
    """
    Translate lower-level simulation or criticism errors into high-level user choices.
    """
    system_prompt = """You are Bio-Design PM Agent. The genetic circuit engine has encountered a technical issue or search bottleneck.
Your task is to analyze the technical feedback (Critic messages or error log), translate it into plain language, and propose exactly three high-level trade-off options for the user.

Your options must fit these categories:
- Option A: Trade-off option (e.g., reduce performance to decrease burden, accept lower expression levels).
- Option B: Alternative strategy (e.g., change promoter assignments, change cell copy number).
- Option C: Accept best fallback (Accept current best scored topology even with minor flaws).

Rules:
1. Explain the error simply in traditional Chinese (Traditional Chinese - Taiwan) without using heavy technical jargon (e.g., talk about 'cell burden' as '細胞生長負擔', 'leakage' as '漏電或背景干擾').
2. Offer 3 options with clear labels, target action ('Repair' or 'Accept_Fallback'), and constraints (technical instruction strings for the Builder/Critic to follow).
3. Output ONLY a valid JSON object with the following schema:
{
  "error_summary_cn": "白話的中文錯誤原因說明",
  "options": [
    {
      "option_id": "A",
      "label": "Option description in Traditional Chinese",
      "constraints": ["instruction_1", "instruction_2"],
      "action": "Repair",
      "extra_budget": 2
    },
    {
      "option_id": "B",
      "label": "Option description in Traditional Chinese",
      "constraints": ["instruction_1"],
      "action": "Repair",
      "extra_budget": 2
    },
    {
      "option_id": "C",
      "label": "Option description in Traditional Chinese",
      "constraints": [],
      "action": "Accept_Fallback",
      "extra_budget": 0
    }
  ],
  "ui_message": "Friendly summary explaining the issue and prompt to make a choice."
}
"""
    error_context = f"""Last Error: {state.last_error}
Latest Critic Feedback: {state.latest_critic_feedback}
Pause Reason: {state.pause_reason}
Failed Attempts Count: {len(state.failed_attempts)}
"""
    try:
        litellm = _load_litellm()
        response = litellm.completion(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": error_context},
            ],
            temperature=temperature,
            api_key=api_key.strip() if api_key and api_key.strip() else None,
            api_base=api_base.strip() if api_base and api_base.strip() else None,
        )
        raw_output = response.choices[0].message["content"]
        cleaned_json = _clean_json_response(raw_output)
        proposal_dict = json.loads(cleaned_json)
        state.pending_proposal = _normalize_hitl_proposal(
            proposal_dict,
            source="llm",
        )
    except Exception as e:
        logger.error(f"Error in PM HITL LLM call: {e}")
        state.pending_proposal = _normalize_hitl_proposal({}, source="fallback")

    return state
