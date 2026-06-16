import json
from unittest.mock import MagicMock, patch

from schemas.state import DesignState
from agents.pm_agent import call_pm_agent, _get_next_missing_field



def test_get_next_missing_field() -> None:
    # 測試定位缺失欄位的邏輯
    spec = {}
    assert _get_next_missing_field(spec) == "chassis"

    spec = {"chassis": "Escherichia coli"}
    assert _get_next_missing_field(spec) == "inputs"

    spec = {"chassis": "Escherichia coli", "inputs": [{"name": "IPTG"}]}
    assert _get_next_missing_field(spec) == "outputs"

    spec = {"chassis": "Escherichia coli", "inputs": [{"name": "IPTG"}], "outputs": ["sfGFP"]}
    assert _get_next_missing_field(spec) == "logic_relation"

    spec = {
        "chassis": "Escherichia coli",
        "inputs": [{"name": "IPTG"}],
        "outputs": ["sfGFP"],
        "logic_relation": "sfGFP = IPTG",
    }
    assert _get_next_missing_field(spec) == "copy_number"

    spec = {
        "chassis": "Escherichia coli",
        "inputs": [{"name": "IPTG"}],
        "outputs": ["sfGFP"],
        "logic_relation": "sfGFP = IPTG",
        "copy_number": 15,
    }
    assert _get_next_missing_field(spec) is None


@patch("litellm.completion")
def test_pm_elicitation_mode(mock_completion) -> None:
    # 建立一個模擬的 LLM 回應
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message={
                "content": json.dumps(
                    {
                        "missing_field": "inputs",
                        "proposed_value": [{"name": "Arsenic", "sensor_promoter": "pArsR"}],
                        "proposal_reason": "ArsR is a highly stable sensor system in E. coli.",
                        "ui_message": "建議使用大腸桿菌中穩定的 ArsR 來偵測砷。同意嗎？",
                    }
                )
            }
        )
    ]
    mock_completion.return_value = mock_response

    # 1. 初始 state，此時 spec 缺少 chassis
    state = DesignState()
    state.pm_stage = "elicitation"
    state.user_intent = "做個重金屬檢測器"
    state.structured_spec = {"chassis": "Escherichia coli"}  # 已有 chassis，下一個缺失是 inputs

    # 執行 PM Agent
    state = call_pm_agent(state, api_key="dummy_key", model_name="gpt-4o-mini")

    # 驗證
    assert state.pending_proposal["missing_field"] == "inputs"
    assert state.pending_proposal["schema_version"] == "pm-proposal-v1"
    assert state.pending_proposal["source"] == "llm"
    assert state.pending_proposal["field_label"] == "Input sensors"
    assert len(state.pending_proposal["proposed_value"]) == 1
    assert state.pending_proposal["proposed_value"][0]["name"] == "Arsenic"
    assert "ArsR" in state.pending_proposal["ui_message"]
    assert state.pending_proposal["field_status"][0]["status"] == "confirmed"
    assert state.pending_proposal["field_status"][1]["status"] == "current"
    assert state.pm_stage == "elicitation"


@patch("litellm.completion")
def test_pm_elicitation_completed(mock_completion) -> None:
    # 當所有 spec 都補滿時，PM Agent 應該轉為 completed
    state = DesignState()
    state.pm_stage = "elicitation"
    state.structured_spec = {
        "chassis": "Escherichia coli",
        "inputs": [{"name": "IPTG"}],
        "outputs": ["sfGFP"],
        "logic_relation": "sfGFP = IPTG",
        "copy_number": 15,
    }

    state = call_pm_agent(state, api_key="dummy_key", model_name="gpt-4o-mini")

    assert state.pm_stage == "completed"
    assert state.pending_proposal == {}
    assert "規格確認完畢" in state.pm_chat_history[-1]["content"]


@patch("litellm.completion")
def test_pm_hitl_translator_mode(mock_completion) -> None:
    # 模擬 HITL 轉譯的 LLM 回應
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message={
                "content": json.dumps(
                    {
                        "error_summary_cn": "模擬電路時發現細胞代謝負擔過高",
                        "options": [
                            {
                                "option_id": "A",
                                "label": "方案 A：使用低拷貝質體降低負擔",
                                "constraints": ["Use low-copy plasmid"],
                                "action": "Repair",
                                "extra_budget": 2,
                            },
                            {
                                "option_id": "B",
                                "label": "方案 B：接受目前結果",
                                "constraints": [],
                                "action": "Accept_Fallback",
                                "extra_budget": 0,
                            },
                        ],
                        "ui_message": "電路發生了細胞負擔過高問題，我們有以下建議：",
                    }
                )
            }
        )
    ]
    mock_completion.return_value = mock_response

    state = DesignState()
    state.requires_human_input = True
    state.last_error = "Simulation failed due to high metabolic burden"
    state.critic_feedbacks = ["The metabolic burden score 0.42 is below the threshold 0.6."]

    state = call_pm_agent(state, api_key="dummy_key", model_name="gpt-4o-mini")

    assert state.pm_stage == "hitl_dialogue"
    assert state.pending_proposal["error_summary_cn"] == "模擬電路時發現細胞代謝負擔過高"
    assert state.pending_proposal["schema_version"] == "pm-hitl-v1"
    assert state.pending_proposal["source"] == "llm"
    assert len(state.pending_proposal["options"]) == 3
    assert state.pending_proposal["options"][0]["option_id"] == "A"
    assert state.pending_proposal["options"][0]["action"] == "Repair"
    assert state.pending_proposal["options"][2]["option_id"] == "C"
    assert state.pending_proposal["options"][2]["action"] == "Accept_Fallback"


@patch("litellm.completion")
def test_pm_agent_fallback_on_exception(mock_completion) -> None:
    # 測試當 LLM 調用拋出例外時，PM Agent 不會崩潰且有 Fallback
    mock_completion.side_effect = Exception("API connection timed out")

    state = DesignState()
    state.pm_stage = "elicitation"
    state.structured_spec = {"chassis": "Escherichia coli"}  # 缺少 inputs

    state = call_pm_agent(state, api_key="dummy_key", model_name="gpt-4o-mini")

    # 驗證 fallback
    assert state.pending_proposal["missing_field"] == "inputs"
    assert state.pending_proposal["source"] == "fallback"
    assert "pLac" in state.pending_proposal["proposed_value"][0]["sensor_promoter"]
    assert state.pending_proposal["field_status"][1]["status"] == "current"


@patch("litellm.completion")
def test_pm_agent_fallback_on_invalid_json(mock_completion) -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message={"content": "not json"})]
    mock_completion.return_value = mock_response

    state = DesignState()
    state.pm_stage = "elicitation"
    state.structured_spec = {"chassis": "Escherichia coli"}

    state = call_pm_agent(state, api_key="dummy_key", model_name="gpt-4o-mini")

    assert state.pending_proposal["source"] == "fallback"
    assert state.pending_proposal["missing_field"] == "inputs"
    assert state.pending_proposal["schema_version"] == "pm-proposal-v1"


@patch("litellm.completion")
def test_pm_hitl_fallback_provides_three_options(mock_completion) -> None:
    mock_completion.side_effect = Exception("timeout")

    state = DesignState()
    state.requires_human_input = True
    state.last_error = "No valid topology found"

    state = call_pm_agent(state, api_key="dummy_key", model_name="gpt-4o-mini")

    assert state.pending_proposal["source"] == "fallback"
    assert [item["option_id"] for item in state.pending_proposal["options"]] == [
        "A",
        "B",
        "C",
    ]
    assert state.pending_proposal["options"][2]["action"] == "Accept_Fallback"


def test_builder_agent_with_structured_spec() -> None:
    from agents.builder_agent import _build_system_prompt

    # 1. 有 structured_spec 的情況
    state = DesignState()
    state.structured_spec = {
        "chassis": "Escherichia coli",
        "inputs": [{"name": "IPTG"}],
        "outputs": ["sfGFP"],
        "logic_relation": "sfGFP = IPTG",
        "copy_number": 15
    }
    
    prompt_with_spec = _build_system_prompt(state)
    assert "Structured Design Specification (Compiled by PM Agent)" in prompt_with_spec
    assert "Escherichia coli" in prompt_with_spec
    assert "sfGFP = IPTG" in prompt_with_spec

    # 2. 沒有 structured_spec (Fallback) 的情況
    state_no_spec = DesignState()
    state_no_spec.user_intent = "做一個光控開關"
    state_no_spec.host_organism = "Saccharomyces cerevisiae"
    
    prompt_no_spec = _build_system_prompt(state_no_spec)
    assert "Structured Design Specification (Compiled by PM Agent)" not in prompt_no_spec

    assert "Saccharomyces cerevisiae" in prompt_no_spec
    assert "做一個光控開關" in prompt_no_spec


def test_generate_mermaid_from_spec() -> None:
    from app import _generate_mermaid_from_spec
    spec = {
        "chassis": "Escherichia coli",
        "inputs": [{"name": "IPTG", "sensor_promoter": "pLac"}],
        "outputs": [{"name": "sfGFP"}],
        "logic_relation": "sfGFP = IPTG"
    }
    mermaid = _generate_mermaid_from_spec(spec)
    assert "graph LR" in mermaid
    assert "Escherichia coli" in mermaid
    assert "IPTG (感測器: pLac)" in mermaid
    assert "sfGFP (報告基因)" in mermaid


@patch("litellm.completion")
def test_pm_chat_history_truncation(mock_completion) -> None:
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message={
                "content": json.dumps({
                    "missing_field": "inputs",
                    "proposed_value": [{"name": "IPTG"}],
                    "proposal_reason": "test reason",
                    "ui_message": "test message"
                })
            }
        )
    ]
    mock_completion.return_value = mock_response

    state = DesignState()
    state.pm_stage = "elicitation"
    state.structured_spec = {"chassis": "Escherichia coli"}
    
    # 構建 15 條對話歷史，這超過了 12 條
    state.pm_chat_history = [{"role": "assistant", "content": "Intro message"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(14)
    ]
    
    state = call_pm_agent(state, api_key="dummy", model_name="dummy")
    
    # 驗證對話歷史被成功截斷至 1 + 10 = 11 條
    assert len(state.pm_chat_history) <= 11
    assert state.pm_chat_history[0]["content"] == "Intro message"  # 開場白依然在最前
