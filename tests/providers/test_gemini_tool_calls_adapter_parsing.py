import pytest

from namel3ss.runtime.providers.gemini.tool_calls_adapter import GeminiToolCallsAdapter
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
from namel3ss.runtime.tool_calls.provider_iface import AssistantError, AssistantText, AssistantToolCall


def _adapter(monkeypatch, response):
    monkeypatch.setenv("NAMEL3SS_GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("namel3ss.runtime.providers.gemini.tool_calls_adapter.post_json", lambda **kwargs: response)
    return GeminiToolCallsAdapter(api_key="test")


def test_gemini_adapter_parses_text(monkeypatch):
    response = {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]}
    adapter = _adapter(monkeypatch, response)
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[], policy=ToolCallPolicy())
    assert isinstance(result, AssistantText)
    assert result.text == "hello"


def test_gemini_adapter_parses_tool_call(monkeypatch):
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "echo",
                                "args": {"x": 1},
                            }
                        }
                    ]
                }
            }
        ]
    }
    adapter = _adapter(monkeypatch, response)
    tool = ToolDeclaration(name="echo", input_schema={"type": "object"})
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[tool], policy=ToolCallPolicy())
    assert isinstance(result, AssistantToolCall)
    assert result.tool_name == "echo"
    assert result.arguments_json_text == '{"x": 1}'


def test_gemini_adapter_handles_malformed_tool_call(monkeypatch):
    response = {"candidates": [{"content": {"parts": [{"functionCall": {"name": "echo"}}]}}]}
    adapter = _adapter(monkeypatch, response)
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[], policy=ToolCallPolicy())
    assert isinstance(result, AssistantError)
    assert "Malformed" in result.error_message or "No" in result.error_message
