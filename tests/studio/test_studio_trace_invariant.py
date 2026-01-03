from __future__ import annotations

from pathlib import Path

from namel3ss.studio.api import execute_action
from namel3ss.studio.session import SessionState


APP_SOURCE = '''
spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

record "User":
  name string must be present

flow "ask_ai":
  ask ai "assistant" with input: "hello" as reply
  return reply

page "home":
  button "Ask":
    calls flow "ask_ai"
  form is "User"
'''.lstrip()


def _assert_trace_invariant(trace: dict) -> None:
    assert isinstance(trace.get("type"), str)
    assert trace["type"]
    assert isinstance(trace.get("title"), str)
    assert trace["title"]
    assert isinstance(trace.get("canonical_events"), list)
    assert isinstance(trace.get("memory_events"), list)


def test_action_traces_have_type_and_title(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    session = SessionState()
    response = execute_action(
        APP_SOURCE,
        session,
        "page.home.button.ask",
        {},
        app_path=app_file.as_posix(),
    )
    traces = response.get("traces") or []
    assert traces
    for trace in traces:
        _assert_trace_invariant(trace)
    ai_traces = [trace for trace in traces if trace.get("type") == "ai_call"]
    assert ai_traces
    mem_events = [event for event in ai_traces[0]["memory_events"] if "memory" in event.get("type", "")]
    assert mem_events


def test_submit_form_traces_are_normalized(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    session = SessionState()
    response = execute_action(
        APP_SOURCE,
        session,
        "page.home.form.user",
        {"values": {"name": "Alice"}},
        app_path=app_file.as_posix(),
    )
    traces = response.get("traces") or []
    assert traces
    for trace in traces:
        _assert_trace_invariant(trace)
