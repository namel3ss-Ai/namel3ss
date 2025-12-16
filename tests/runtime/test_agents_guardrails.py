import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.ai.mock_provider import MockProvider
from tests.conftest import lower_ir_program


def test_parallel_agent_limit():
    source = '''ai "assistant":
  model is "gpt-4.1"

agent "a1":
  ai is "assistant"

agent "a2":
  ai is "assistant"

agent "a3":
  ai is "assistant"

agent "a4":
  ai is "assistant"

flow "demo":
  run agents in parallel:
    agent "a1" with input: "x"
    agent "a2" with input: "x"
    agent "a3" with input: "x"
    agent "a4" with input: "x"
  as results
'''
    program = lower_ir_program(source)
    flow = program.flows[0]
    with pytest.raises(Namel3ssError):
        Executor(flow, schemas={}, ai_profiles=program.ais, agents=program.agents, ai_provider=MockProvider()).run()


def test_unknown_agent_errors():
    source = '''ai "assistant":
  model is "gpt-4.1"

agent "known":
  ai is "assistant"

flow "demo":
  run agent "missing" with input: "x" as out
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)
