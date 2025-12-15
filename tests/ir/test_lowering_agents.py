from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"

agent "planner":
  ai is "assistant"

flow "demo":
  run agent "planner" with input: "Hi" as reply
'''


def test_agents_lowering():
    program = lower_ir_program(SOURCE)
    assert "planner" in program.agents
    flow = program.flows[0]
    stmt = flow.body[0]
    assert isinstance(stmt, ir.RunAgentStmt)
    assert stmt.agent_name == "planner"
