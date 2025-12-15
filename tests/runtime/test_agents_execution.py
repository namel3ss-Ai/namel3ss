from namel3ss.runtime.executor import Executor
from namel3ss.runtime.ai.mock_provider import MockProvider
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"

agent "planner":
  ai is "assistant"
  system_prompt is "You are a planner. Return a short plan."

agent "builder":
  ai is "assistant"
  system_prompt is "You are a builder. Execute the plan."

flow "demo":
  run agent "planner" with input: "Build a CRM" as plan
  run agent "builder" with input: plan as result
  set state.result is result
  return result
'''


def test_agent_execution_sets_locals_and_traces():
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]
    provider = MockProvider()
    executor = Executor(flow, schemas={}, ai_profiles=program.ais, agents=program.agents, ai_provider=provider)
    result = executor.run()
    assert result.state["result"].startswith("[gpt-4.1]")
    assert any(trace.agent_name == "planner" for trace in result.traces)
