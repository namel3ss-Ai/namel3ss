import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tool_calls.provider_iface import AssistantText, AssistantToolCall
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  implemented using builtin

  input:
    value is json

  output:
    echo is json

ai "assistant":
  provider is "{provider}"
  model is "test-model"
  tools:
    expose "echo"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


class FakeAdapter:
    def __init__(self, *, tool_name: str = "echo"):
        self.calls = 0
        self.tool_name = tool_name

    def run_model(self, messages, tools, policy):
        if self.calls == 0:
            self.calls += 1
            return AssistantToolCall(
                tool_call_id="tool-1",
                tool_name=self.tool_name,
                arguments_json_text='{"value":"hi"}',
            )
        return AssistantText(text="[done]")


def _normalized_tool_events(events: list[dict]) -> list[dict]:
    keep = {
        "tool_call_proposed",
        "tool_call_allowed",
        "tool_call_blocked",
        "tool_call_started",
        "tool_call_finished",
        "tool_loop_finished",
    }
    cleaned = []
    for event in events:
        if not isinstance(event, dict) or event.get("type") not in keep:
            continue
        item = {
            key: value
            for key, value in event.items()
            if key not in {"call_id", "provider", "model", "timestamp"}
        }
        cleaned.append(item)
    return cleaned


def test_tool_call_events_are_provider_parity(monkeypatch):
    providers = ["openai", "anthropic", "gemini", "mistral"]
    baseline = None
    for name in providers:
        program = lower_ir_program(SOURCE.format(provider=name))
        adapter = FakeAdapter()
        monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", lambda *_args, **_kwargs: object())
        monkeypatch.setattr(
            "namel3ss.runtime.tool_calls.provider_iface.get_provider_adapter",
            lambda *_args, adapter=adapter, **_kwargs: adapter,
        )
        executor = Executor(
            program.flows[0],
            schemas={schema.name: schema for schema in program.records},
            ai_profiles=program.ais,
            tools=program.tools,
        )
        result = executor.run()
        events = result.traces[0].canonical_events
        normalized = _normalized_tool_events(events)
        assert normalized
        if baseline is None:
            baseline = normalized
        else:
            assert normalized == baseline
        types = [event.get("type") for event in normalized]
        assert types.index("tool_call_proposed") < types.index("tool_call_allowed")
        assert types.index("tool_call_allowed") < types.index("tool_call_started")
        assert types.index("tool_call_started") < types.index("tool_call_finished")
        assert types[-1] == "tool_loop_finished"


def test_tool_call_blocked_reason_is_stable(monkeypatch):
    program = lower_ir_program(SOURCE.format(provider="openai"))
    adapter = FakeAdapter(tool_name="missing_tool")
    monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "namel3ss.runtime.tool_calls.provider_iface.get_provider_adapter",
        lambda *_args, adapter=adapter, **_kwargs: adapter,
    )
    executor = Executor(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        ai_profiles=program.ais,
        tools=program.tools,
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    trace = executor.traces[0]
    events = trace.canonical_events
    blocked = next(event for event in events if event.get("type") == "tool_call_blocked")
    assert blocked["reason"] == "unknown_tool"
