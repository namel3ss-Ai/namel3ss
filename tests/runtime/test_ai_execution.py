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
    assert response["state"]["reply"]["text"].startswith("[gpt-4.1]")
    assert response["result"]["text"].startswith("[gpt-4.1]")
    traces = response["traces"]
    assert len(traces) == 1
    trace = traces[0]
    assert trace["ai_name"] == "assistant"
    assert trace["model"] == "gpt-4.1"
