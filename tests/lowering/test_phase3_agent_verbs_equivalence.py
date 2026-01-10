from __future__ import annotations

from tests.conftest import lower_ir_program
from tests.spec_freeze.helpers.ir_dump import dump_ir


def _strip_positions(value):
    if isinstance(value, list):
        return [_strip_positions(item) for item in value]
    if isinstance(value, dict):
        return {key: _strip_positions(val) for key, val in value.items() if key not in {"line", "column"}}
    return value


def test_verb_agent_call_ir_equivalence() -> None:
    sugar = '''
ai "mock":
  model is "mock"

agent "planner":
  ai is "mock"

flow "demo":
  planner drafts goal as plan
'''
    core = '''
ai "mock":
  model is "mock"

agent "planner":
  ai is "mock"

flow "demo":
  run agent "planner" with input: goal as plan
'''
    sugar_dump = _strip_positions(dump_ir(lower_ir_program(sugar)))
    core_dump = _strip_positions(dump_ir(lower_ir_program(core)))
    assert sugar_dump == core_dump


def test_in_parallel_ir_equivalence() -> None:
    sugar = '''
ai "mock":
  model is "mock"

agent "critic":
  ai is "mock"

agent "researcher":
  ai is "mock"

flow "demo":
  in parallel:
    critic reviews plan as critic_text
    researcher enriches plan as researcher_text
  merge policy is "all" as feedback
'''
    core = '''
ai "mock":
  model is "mock"

agent "critic":
  ai is "mock"

agent "researcher":
  ai is "mock"

flow "demo":
  run agents in parallel:
    agent "critic" with input: plan
    agent "researcher" with input: plan
  merge:
    policy is "all"
  as feedback
'''
    sugar_dump = _strip_positions(dump_ir(lower_ir_program(sugar)))
    core_dump = _strip_positions(dump_ir(lower_ir_program(core)))
    assert sugar_dump == core_dump


def test_phase3_ir_is_deterministic() -> None:
    source = '''
ai "mock":
  model is "mock"

agent "planner":
  ai is "mock"

flow "demo":
  planner drafts "goal" as plan
'''
    first = dump_ir(lower_ir_program(source))
    second = dump_ir(lower_ir_program(source))
    assert first == second
