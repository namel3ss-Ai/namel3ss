from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
from namel3ss.runtime.tool_calls.provider_iface import AssistantError, AssistantText, AssistantToolCall, ModelResponse, ProviderAdapter
from namel3ss.security import read_env


def _build_tools(tools: List[ToolDeclaration]) -> list:
    tool_list = []
    for tool in tools:
        tool_list.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema or {"type": "object", "properties": {}},
                },
            }
        )
    return tool_list


def _map_messages(messages: List[dict]) -> list:
    mapped: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            mapped.append({"role": "system", "content": content})
            continue
        if role == "user":
            mapped.append({"role": "user", "content": content})
            continue
        if role == "assistant":
            mapped.append({"role": "assistant", "content": content})
            continue
        if role == "tool":
            mapped.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id") or "unknown_tool_call",
                    "content": content,
                }
            )
            continue
    return mapped


@dataclass
class MistralChatAdapter(ProviderAdapter):
    api_key: str | None

    @classmethod
    def from_provider(cls, provider) -> "MistralChatAdapter":
        key = getattr(provider, "api_key", None)
        return cls(api_key=key)

    def run_model(self, messages: List[dict], tools: List[ToolDeclaration], policy: ToolCallPolicy) -> ModelResponse:
        try:
            api_key = _resolve_api_key(self.api_key)
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        payload: dict = {
            "model": messages[-1].get("model_override") or "mistral-large-latest",
            "messages": _map_messages(messages),
        }
        tool_payload = _build_tools(tools)
        if policy.allow_tools and tool_payload:
            payload["tools"] = tool_payload
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            result = post_json(
                url="https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                payload=payload,
                timeout_seconds=30,
                provider_name="mistral",
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
        first = tool_calls[0] if isinstance(tool_calls[0], dict) else {}
        fn = first.get("function") if isinstance(first.get("function"), dict) else None
        name = fn.get("name") if fn else None
        args = fn.get("arguments") if fn else None
        tool_call_id = first.get("id") or (fn.get("id") if fn else None)
        if name and args is not None and tool_call_id:
            try:
                args_text = args if isinstance(args, str) else json.dumps(args)
            except Exception:
                args_text = str(args)
            return AssistantToolCall(
                tool_call_id=str(tool_call_id),
                tool_name=str(name),
                arguments_json_text=args_text,
            )
        return AssistantError(error_type="ProviderError", error_message="Malformed tool call from Mistral")
    content = message.get("content")
    if isinstance(content, str):
        return AssistantText(text=content)
    return AssistantError(error_type="ProviderError", error_message="No assistant content")


def _resolve_api_key(api_key: str | None) -> str:
    if api_key is not None and str(api_key).strip() != "":
        return api_key
    preferred = read_env("NAMEL3SS_MISTRAL_API_KEY")
    if preferred is not None and str(preferred).strip() != "":
        return require_env("mistral", "NAMEL3SS_MISTRAL_API_KEY", preferred)
    fallback = read_env("MISTRAL_API_KEY")
    if fallback is not None and str(fallback).strip() != "":
        return require_env("mistral", "MISTRAL_API_KEY", fallback)
    raise Namel3ssError(
        "Missing Mistral API key. Set NAMEL3SS_MISTRAL_API_KEY (preferred) or MISTRAL_API_KEY."
    )


__all__ = ["MistralChatAdapter"]
