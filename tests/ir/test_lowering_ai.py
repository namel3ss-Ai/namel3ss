from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
'''


def test_lowering_ai_decl_and_ask():
    program = lower_ir_program(SOURCE)
    assert "assistant" in program.ais
    ai_ir = program.ais["assistant"]
    assert ai_ir.model == "gpt-4.1"
    flow = program.flows[0]
    ask_stmt = flow.body[0]
    assert isinstance(ask_stmt, ir.AskAIStmt)
    assert ask_stmt.ai_name == "assistant"
