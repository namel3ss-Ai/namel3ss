import pytest

from namel3ss.runtime.providers.anthropic.tool_calls_adapter import AnthropicMessagesAdapter
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
from namel3ss.runtime.tool_calls.provider_iface import AssistantError, AssistantText, AssistantToolCall


def _adapter(monkeypatch, response):
    monkeypatch.setenv("NAMEL3SS_ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr("namel3ss.runtime.providers.anthropic.tool_calls_adapter.post_json", lambda **kwargs: response)
    return AnthropicMessagesAdapter(api_key="test")


def test_anthropic_adapter_parses_text(monkeypatch):
    response = {"content": [{"type": "text", "text": "hello"}]}
    adapter = _adapter(monkeypatch, response)
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[], policy=ToolCallPolicy())
    assert isinstance(result, AssistantText)
    assert result.text == "hello"


def test_anthropic_adapter_parses_tool_call(monkeypatch):
    response = {
        "content": [
            {"type": "text", "text": "Using tool"},
            {"type": "tool_use", "id": "call_1", "name": "echo", "input": {"x": 1}},
        ]
    }
    adapter = _adapter(monkeypatch, response)
    tool = ToolDeclaration(name="echo", input_schema={"type": "object"})
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[tool], policy=ToolCallPolicy())
    assert isinstance(result, AssistantToolCall)
    assert result.tool_call_id == "call_1"
    assert result.tool_name == "echo"
    assert result.arguments_json_text == '{"x": 1}'


def test_anthropic_adapter_handles_malformed_tool_call(monkeypatch):
    response = {"content": [{"type": "tool_use", "id": "call_1", "name": "echo"}]}
    adapter = _adapter(monkeypatch, response)
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[], policy=ToolCallPolicy())
    assert isinstance(result, AssistantError)
    assert "Malformed" in result.error_message
