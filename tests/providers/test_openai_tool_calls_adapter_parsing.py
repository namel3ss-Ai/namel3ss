import pytest

from namel3ss.runtime.providers.openai.tool_calls_adapter import OpenAIChatCompletionsAdapter
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
from namel3ss.runtime.tool_calls.provider_iface import AssistantError, AssistantText, AssistantToolCall


def _make_adapter(monkeypatch, response):
    adapter = OpenAIChatCompletionsAdapter(api_key="test", base_url="https://api.openai.com", model="gpt-4.1")
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("namel3ss.runtime.providers.openai.tool_calls_adapter.post_json", lambda **kwargs: response)
    return adapter


def test_openai_adapter_parses_text_response(monkeypatch):
    response = {"choices": [{"message": {"content": "hello world"}}]}
    adapter = _make_adapter(monkeypatch, response)
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[], policy=ToolCallPolicy())
    assert isinstance(result, AssistantText)
    assert result.text == "hello world"


def test_openai_adapter_parses_tool_call(monkeypatch):
    response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {"id": "call_1", "type": "function", "function": {"name": "echo", "arguments": '{"x":1}'}}
                    ],
                }
            }
        ]
    }
    adapter = _make_adapter(monkeypatch, response)
    tool = ToolDeclaration(name="echo", input_schema={"type": "object"})
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[tool], policy=ToolCallPolicy())
    assert isinstance(result, AssistantToolCall)
    assert result.tool_call_id == "call_1"
    assert result.tool_name == "echo"
    assert result.arguments_json_text == '{"x":1}'


def test_openai_adapter_handles_malformed_tool_call(monkeypatch):
    response = {"choices": [{"message": {"role": "assistant", "tool_calls": [{"id": "call_2", "function": {}}]}}]}
    adapter = _make_adapter(monkeypatch, response)
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[], policy=ToolCallPolicy())
    assert isinstance(result, AssistantError)
    assert "Malformed" in result.error_message


def test_openai_adapter_normalizes_base_url(monkeypatch):
    captured = {}

    def fake_post_json(**kwargs):
        captured["url"] = kwargs["url"]
        return {"choices": [{"message": {"content": "ok"}}]}

    adapter = OpenAIChatCompletionsAdapter(
        api_key="test",
        base_url="https://api.openai.com/v1/",
        model="gpt-4.1",
    )
    monkeypatch.setattr("namel3ss.runtime.providers.openai.tool_calls_adapter.post_json", fake_post_json)
    result = adapter.run_model(messages=[{"role": "user", "content": "hi"}], tools=[], policy=ToolCallPolicy())
    assert isinstance(result, AssistantText)
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
