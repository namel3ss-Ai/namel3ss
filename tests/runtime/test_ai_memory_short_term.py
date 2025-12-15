from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.memory.manager import MemoryManager
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    short_term is 2

flow "demo":
  ask ai "assistant" with input: "Hello" as first
  ask ai "assistant" with input: "How are you" as second
'''


def test_short_term_recall_in_trace():
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]
    ai_provider = MockProvider()
    memory_manager = MemoryManager()
    executor = Executor(flow, schemas={}, ai_profiles=program.ais, ai_provider=ai_provider, memory_manager=memory_manager)
    result = executor.run()
    trace = result.traces[-1]
    assert len(trace.memory["short_term"]) >= 2
