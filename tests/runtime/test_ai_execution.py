from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIResponse
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.ui.actions import handle_action
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with input: "Hello" as reply
  set state.reply is reply
  return reply

page "home":
  button "Ask":
    calls flow "demo"
'''


def test_ai_call_uses_mock_and_traces():
    program = lower_ir_program(SOURCE)
    response = handle_action(program, action_id="page.home.button.ask")
    assert response["state"]["reply"].startswith("[gpt-4.1]")
    assert response["result"].startswith("[gpt-4.1]")
    traces = response["traces"]
    assert len(traces) == 1
    trace = traces[0]
    assert trace["ai_name"] == "assistant"
    assert trace["model"] == "gpt-4.1"


def test_ask_ai_returns_string_when_provider_returns_object(monkeypatch):
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  ask ai "assistant" with input: "hello" as reply
  return reply
'''

    def fake_ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        return AIResponse(output={"output": "hello"})

    monkeypatch.setattr(MockProvider, "ask", fake_ask)
    program = lower_ir_program(source)
    flow = program.flows[0]
    schemas = {schema.name: schema for schema in program.records}
    executor = Executor(
        flow,
        schemas=schemas,
        ai_profiles=program.ais,
        functions=program.functions,
        runtime_theme=getattr(program, "theme", None),
        identity_schema=getattr(program, "identity", None),
    )
    result = executor.run()
    assert isinstance(result.last_value, str)
    assert result.last_value == "hello"
