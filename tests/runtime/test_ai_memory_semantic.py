from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.memory.manager import MemoryManager
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    semantic is true

flow "demo":
  ask ai "assistant" with input: "We decided to use weekly releases." as first
  ask ai "assistant" with input: "weekly" as second
'''


def test_semantic_recall():
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]
    provider = MockProvider()
    memory = MemoryManager()
    executor = Executor(flow, schemas={}, ai_profiles=program.ais, ai_provider=provider, memory_manager=memory)
    result = executor.run()
    trace = result.traces[-1]
    assert trace.memory["semantic"]
