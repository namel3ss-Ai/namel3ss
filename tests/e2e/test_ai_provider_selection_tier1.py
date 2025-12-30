from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.executor import Executor


class StubProvider(AIProvider):
    def __init__(self):
        self.calls = []

    def ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        self.calls.append((model, system_prompt, user_input))
        return AIResponse(output=f"{model}|{system_prompt}|{user_input}")


def _run_with_provider(monkeypatch, provider_name: str):
    stub = StubProvider()

    def fake_get_provider(name, config):
        assert name == provider_name
        return stub

    monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", fake_get_provider)
    source = f'''spec is "1.0"

ai "assistant":
  provider is "{provider_name}"
  model is "{provider_name}-model"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''
    program = lower_program(parse(source))
    flow = program.flows[0]
    result = Executor(flow, ai_profiles=program.ais, agents=program.agents).run()
    return result, stub


def test_openai_provider_selected(monkeypatch):
    result, stub = _run_with_provider(monkeypatch, "openai")
    assert result.last_value["text"] == "openai-model|None|hi"
    assert stub.calls[0][0] == "openai-model"


def test_anthropic_provider_selected(monkeypatch):
    result, stub = _run_with_provider(monkeypatch, "anthropic")
    assert result.last_value["text"] == "anthropic-model|None|hi"


def test_gemini_provider_selected(monkeypatch):
    result, stub = _run_with_provider(monkeypatch, "gemini")
    assert result.last_value["text"] == "gemini-model|None|hi"


def test_mistral_provider_selected(monkeypatch):
    result, stub = _run_with_provider(monkeypatch, "mistral")
    assert result.last_value["text"] == "mistral-model|None|hi"
