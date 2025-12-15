from namel3ss.runtime.executor import Executor
from namel3ss.runtime.ai.mock_provider import MockProvider
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"

agent "critic":
  ai is "assistant"

agent "researcher":
  ai is "assistant"

flow "analyze":
  run agents in parallel:
    agent "critic" with input: "Idea"
    agent "researcher" with input: "Idea"
  as results
  return results
'''


def test_parallel_agents_collect_results_and_trace():
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]
    executor = Executor(flow, schemas={}, ai_profiles=program.ais, agents=program.agents, ai_provider=MockProvider())
    result = executor.run()
    assert isinstance(result.last_value, list)
    assert len(result.last_value) == 2
    assert any(isinstance(t, dict) and t.get("type") == "parallel_agents" for t in result.traces)
