from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
from namel3ss.runtime.tool_calls.provider_iface import AssistantError, AssistantText, AssistantToolCall, ModelResponse, ProviderAdapter
from namel3ss.security import read_env

ANTHROPIC_VERSION = "2023-06-01"


def _build_tools(tools: List[ToolDeclaration]) -> list:
    tool_list = []
    for tool in tools:
        tool_list.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.input_schema or {"type": "object", "properties": {}},
            }
        )
    return tool_list


def _map_messages(messages: List[dict]) -> list:
    mapped: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        tool_call_id = msg.get("tool_call_id")
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
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call_id or "unknown_tool_call",
                            "content": content,
                        }
                    ],
                }
            )
            continue
    return mapped


@dataclass
class AnthropicMessagesAdapter(ProviderAdapter):
    api_key: str | None
    timeout_seconds: int = 30

    @classmethod
    def from_provider(cls, provider) -> "AnthropicMessagesAdapter":
        key = getattr(provider, "api_key", None)
        return cls(api_key=key)

    def run_model(self, messages: List[dict], tools: List[ToolDeclaration], policy: ToolCallPolicy) -> ModelResponse:
        try:
            api_key = _resolve_api_key(self.api_key)
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))

        payload: dict = {
            "model": messages[-1].get("model_override") or "claude-3-5-sonnet-latest",
            "messages": _map_messages(messages),
            "max_tokens": 1024,
        }
        tool_payload = _build_tools(tools)
        if policy.allow_tools and tool_payload:
            payload["tools"] = tool_payload
        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        try:
            result = post_json(
                url="https://api.anthropic.com/v1/messages",
                headers=headers,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
                provider_name="anthropic",
            )
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        except Exception as err:  # pragma: no cover - defensive
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        return _parse_response(result)


def _parse_response(result: dict) -> ModelResponse:
    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_call_id = block.get("id")
                name = block.get("name")
                arguments = block.get("input")
                if tool_call_id and name is not None and arguments is not None:
                    try:
                        arguments_text = json.dumps(arguments)
                    except Exception:
                        arguments_text = str(arguments)
                    return AssistantToolCall(
                        tool_call_id=str(tool_call_id),
                        tool_name=str(name),
                        arguments_json_text=arguments_text,
                    )
                return AssistantError(error_type="ProviderError", error_message="Malformed tool call from Anthropic")
        texts = [b.get("text") for b in content if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
        if texts:
            return AssistantText(text="".join(texts))
    return AssistantError(error_type="ProviderError", error_message="No assistant content")


def _resolve_api_key(api_key: str | None) -> str:
    if api_key is not None and str(api_key).strip() != "":
        return api_key
    preferred = read_env("NAMEL3SS_ANTHROPIC_API_KEY")
    if preferred is not None and str(preferred).strip() != "":
        return require_env("anthropic", "NAMEL3SS_ANTHROPIC_API_KEY", preferred)
    fallback = read_env("ANTHROPIC_API_KEY")
    if fallback is not None and str(fallback).strip() != "":
        return require_env("anthropic", "ANTHROPIC_API_KEY", fallback)
    raise Namel3ssError(
        "Missing Anthropic API key. Set NAMEL3SS_ANTHROPIC_API_KEY (preferred) or ANTHROPIC_API_KEY."
    )


__all__ = ["AnthropicMessagesAdapter"]
