from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.memory.manager import MemoryManager
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    profile is true

flow "demo":
  ask ai "assistant" with input: "Hello" as first
'''


def test_profile_recall():
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]
    memory = MemoryManager()
    memory.record_interaction(program.ais["assistant"], {}, "My name is Alice.", "ok", [])
    executor = Executor(flow, schemas={}, ai_profiles=program.ais, ai_provider=MockProvider(), memory_manager=memory)
    result = executor.run()
    trace = result.traces[-1]
    assert trace.memory["profile"]
