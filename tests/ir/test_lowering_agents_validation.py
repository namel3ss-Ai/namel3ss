import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_agent_references_unknown_ai():
    source = '''agent "planner":
  ai is "missing"

flow "demo":
  run agent "planner" with input: "hi" as out
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)


def test_run_agent_unknown_agent():
    source = '''ai "assistant":
  model is "gpt-4.1"

flow "demo":
  run agent "ghost" with input: "hi" as out
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)


def test_parallel_agent_unknown_agent():
    source = '''ai "assistant":
  model is "gpt-4.1"

flow "demo":
  run agents in parallel:
    agent "ghost" with input: "hi"
  as results
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)


def test_duplicate_agent_declaration():
    source = '''ai "assistant":
  model is "gpt-4.1"

agent "dup":
  ai is "assistant"

agent "dup":
  ai is "assistant"
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)
