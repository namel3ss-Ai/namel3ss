from __future__ import annotations

from namel3ss.runtime.ui.actions import handle_action
from tests.conftest import lower_ir_program


SOURCE_STREAM_TRUE = '''spec is "1.0"

capabilities:
  streaming

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  ask ai "assistant" with stream: true and input: "hello" as reply
  return reply

page "home":
  button "Run":
    calls flow "demo"
'''


SOURCE_STREAM_FALSE = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  ask ai "assistant" with stream: false and input: "hello" as reply
  return reply

page "home":
  button "Run":
    calls flow "demo"
'''


def test_streaming_emits_token_and_finish_events() -> None:
    program = lower_ir_program(SOURCE_STREAM_TRUE)
    response = handle_action(program, action_id="page.home.button.run")
    assert isinstance(response.get("result"), str)
    messages = list(response.get("yield_messages") or [])
    assert messages
    assert [item.get("sequence") for item in messages] == list(range(1, len(messages) + 1))
    assert messages[0].get("event_type") == "progress"
    assert messages[-1].get("event_type") == "finish"
    token_text = "".join(str(item.get("output") or "") for item in messages if item.get("event_type") == "token")
    assert token_text == response.get("result")
    assert messages[-1].get("output") == response.get("result")


def test_streaming_preserves_final_output_parity() -> None:
    streamed_program = lower_ir_program(SOURCE_STREAM_TRUE)
    streamed = handle_action(streamed_program, action_id="page.home.button.run")
    non_streamed_program = lower_ir_program(SOURCE_STREAM_FALSE)
    non_streamed = handle_action(non_streamed_program, action_id="page.home.button.run")
    assert streamed.get("result") == non_streamed.get("result")


def test_streaming_respects_global_disable(monkeypatch) -> None:
    monkeypatch.setenv("NAMEL3SS_STREAMING_ENABLED", "false")
    program = lower_ir_program(SOURCE_STREAM_TRUE)
    response = handle_action(program, action_id="page.home.button.run")
    assert isinstance(response.get("result"), str)
    assert response.get("yield_messages") in (None, [])
