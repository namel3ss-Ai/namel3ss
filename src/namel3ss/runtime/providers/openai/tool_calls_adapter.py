from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.config.model import OpenAIConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
from namel3ss.runtime.tool_calls.provider_iface import AssistantError, AssistantText, AssistantToolCall, ModelResponse, ProviderAdapter


def _build_tool_payload(tools: List[ToolDeclaration]) -> list:
    payload = []
    for tool in tools:
        parameters = tool.input_schema or {"type": "object", "properties": {}}
        payload.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": parameters,
                },
            }
        )
    return payload


def _map_messages(messages: List[dict]) -> list:
    mapped = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        name = message.get("name")
        tool_call_id = message.get("tool_call_id")
        msg: dict = {"role": role, "content": content}
        if name:
            msg["name"] = name
        if role == "tool" and tool_call_id:
            msg["tool_call_id"] = tool_call_id
        mapped.append(msg)
    return mapped


@dataclass
class OpenAIChatCompletionsAdapter(ProviderAdapter):
    api_key: str | None
    base_url: str
    model: str

    @classmethod
    def from_provider(cls, provider, *, model: str) -> "OpenAIChatCompletionsAdapter":
        key = getattr(provider, "api_key", None)
        base_url = getattr(provider, "base_url", "https://api.openai.com").rstrip("/")
        return cls(api_key=key, base_url=base_url, model=model)

    def run_model(self, messages: List[dict], tools: List[ToolDeclaration], policy: ToolCallPolicy) -> ModelResponse:
        api_key = None
        try:
            api_key = require_env("openai", "NAMEL3SS_OPENAI_API_KEY", self.api_key)
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))

        payload: dict = {"model": self.model, "messages": _map_messages(messages), "tool_choice": "auto"}
        tool_payload = _build_tool_payload(tools)
        if tool_payload:
            payload["tools"] = tool_payload
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            result = post_json(
                url=f"{self.base_url}/v1/chat/completions",
                headers=headers,
                payload=payload,
                timeout_seconds=30,
                provider_name="openai",
            )
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        except Exception as err:  # pragma: no cover - defensive
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        return _parse_response(result)


def _parse_response(result: dict) -> ModelResponse:
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        return AssistantError(error_type="ProviderError", error_message="No choices returned")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return AssistantError(error_type="ProviderError", error_message="Invalid message payload")
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        if isinstance(first, dict):
            fn = first.get("function") if isinstance(first.get("function"), dict) else None
            name = fn.get("name") if fn else None
            arguments = fn.get("arguments") if fn else None
            tool_call_id = first.get("id")
            if name and arguments is not None and tool_call_id:
                return AssistantToolCall(
                    tool_call_id=str(tool_call_id),
                    tool_name=str(name),
                    arguments_json_text=str(arguments),
                )
            return AssistantError(error_type="ProviderError", error_message="Malformed tool call")
    content = message.get("content")
    if isinstance(content, str):
        return AssistantText(text=content)
    return AssistantError(error_type="ProviderError", error_message="No assistant content")


__all__ = ["OpenAIChatCompletionsAdapter"]
