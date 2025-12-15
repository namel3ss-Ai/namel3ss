from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  kind is "mock"

ai "assistant":
  model is "gpt-4.1"
  tools:
    expose "echo"

agent "planner":
  ai is "assistant"
  system_prompt is "You are a planner. Return a short plan."

agent "builder":
  ai is "assistant"
  system_prompt is "You are a builder. Execute the plan."

flow "demo":
  run agent "planner" with input: "Build a CRM" as plan
  run agent "builder" with input: plan as result
  return result
'''


def test_agents_parse_and_lower():
    program = lower_ir_program(SOURCE)
    assert "planner" in program.agents and "builder" in program.agents
    flow = program.flows[0]
    assert isinstance(flow.body[0], ir.RunAgentStmt)
    assert flow.body[0].agent_name == "planner"
