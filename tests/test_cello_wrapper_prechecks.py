from pathlib import Path
import json
from schemas.state import DesignState
from tools.cello_wrapper import CelloWrapper


def test_cello_wrapper_sequential_logic_intercept() -> None:
    state = DesignState()
    # Verilog code with always @posedge clk
    code = """
    module seq_logic(input clk, input d, output reg q);
        always @(posedge clk) begin
            q <= d;
        end
    endmodule
    """
    state.verilog_codes = [code]
    
    # Run in mock mode (no cello_command)
    wrapper = CelloWrapper()
    result = wrapper.run(state)
    
    topology = result.candidate_topologies[0]
    assert topology["mapping_status"] == "SEQUENTIAL_LOGIC_BLOCKED"
    assert topology["error_type"] == "LOGIC_ERROR"
    assert topology["cello_buildable"] is False
    assert "always @" in topology["mapping_error_summary"] or "clk" in topology["mapping_error_summary"]


def test_cello_wrapper_ucf_capacity_intercept(tmp_path: Path) -> None:
    # 1. Create a UCF file with only 1 gate
    ucf_content = [
        {
            "collection": "gates",
            "name": "P1_PhlF",
            "gate_type": "NOR"
        }
    ]
    ucf_file = tmp_path / "test_ucf.json"
    ucf_file.write_text(json.dumps(ucf_content), encoding="utf-8")
    
    # 2. Verilog code with 2 gates (e.g. two nor gates)
    code = """
    module double_nor(input A, input B, input C, output Y);
        wire w1;
        nor g1(w1, A, B);
        nor g2(Y, w1, C);
    endmodule
    """
    state = DesignState()
    state.verilog_codes = [code]
    
    wrapper = CelloWrapper(ucf_path=str(ucf_file))
    result = wrapper.run(state)
    
    topology = result.candidate_topologies[0]
    assert topology["mapping_status"] == "UCF_CAPACITY_EXCEEDED"
    assert topology["error_type"] == "LOGIC_ERROR"
    assert topology["cello_buildable"] is False
    assert "exceeds" in topology["mapping_error_summary"]
    assert "2" in topology["mapping_error_summary"]
    assert "1" in topology["mapping_error_summary"]
