from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.executor import Executor


PROGRAM_SOURCE = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''


class StubProvider(AIProvider):
    def __init__(self, output="stubbed"):
        self.output = output
        self.calls = 0

    def ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        self.calls += 1
        return AIResponse(output=self.output)


def _build_executor(source: str, ai_provider=None):
    program = lower_program(parse(source))
    flow = program.flows[0]
    return Executor(flow, ai_profiles=program.ais, ai_provider=ai_provider, schemas={}, agents=program.agents)


def test_mock_provider_used_by_default(monkeypatch):
    stub = StubProvider(output="mocked")

    def fail_get_provider(*args, **kwargs):
        raise AssertionError("registry should not be used for mock provider")

    monkeypatch.setattr("namel3ss.runtime.ai.providers.registry.get_provider", fail_get_provider)
    executor = _build_executor(PROGRAM_SOURCE, ai_provider=stub)
    result = executor.run()
    assert stub.calls == 1
    assert result.last_value["text"] == "mocked"


def test_ollama_provider_selected(monkeypatch):
    stub = StubProvider(output="ollama-output")

    def fake_get_provider(name, config):
        return stub

    monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", fake_get_provider)
    source = PROGRAM_SOURCE.replace('model is "gpt-4.1"', 'provider is "ollama"\n  model is "gpt-4.1"')
    executor = _build_executor(source)
    result = executor.run()
    assert stub.calls == 1
    assert result.last_value["text"] == "ollama-output"
