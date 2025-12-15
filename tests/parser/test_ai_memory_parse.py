from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    short_term is 2
    semantic is true
    profile is true

flow "demo":
  ask ai "assistant" with input: "Hello" as reply
'''


def test_ai_memory_parses_and_lowers():
    program = lower_ir_program(SOURCE)
    ai = program.ais["assistant"]
    assert ai.memory.short_term == 2
    assert ai.memory.semantic is True
    assert ai.memory.profile is True
