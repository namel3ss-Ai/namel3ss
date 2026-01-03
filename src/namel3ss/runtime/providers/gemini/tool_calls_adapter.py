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
    payload = []
    for tool in tools:
        payload.append(
            {
                "functionDeclarations": [
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema or {"type": "object", "properties": {}},
                    }
                ]
            }
        )
    return payload


def _map_messages(messages: List[dict], system_prompt: str | None) -> list:
    parts = []
    if system_prompt:
        parts.append({"role": "user", "parts": [{"text": system_prompt}]})
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            parts.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            parts.append({"role": "model", "parts": [{"text": content}]})
        elif role == "tool":
            tool_name = msg.get("name")
            tool_call_id = msg.get("tool_call_id") or "unknown_tool_call"
            parts.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": tool_name,
                                "response": {"name": tool_name, "content": content},
                                "id": tool_call_id,
                            }
                        }
                    ],
                }
            )
    return parts


@dataclass
class GeminiToolCallsAdapter(ProviderAdapter):
    api_key: str | None

    @classmethod
    def from_provider(cls, provider) -> "GeminiToolCallsAdapter":
        key = getattr(provider, "api_key", None)
        return cls(api_key=key)

    def run_model(self, messages: List[dict], tools: List[ToolDeclaration], policy: ToolCallPolicy) -> ModelResponse:
        try:
            api_key = _resolve_api_key(self.api_key)
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        model = messages[-1].get("model_override") or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        system_prompt = None
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content")
                break
        contents = _map_messages(messages, system_prompt)
        payload: dict = {"contents": contents}
        tool_payload = _build_tools(tools)
        if policy.allow_tools and tool_payload:
            payload["tools"] = tool_payload
        headers = {"Content-Type": "application/json"}
        try:
            result = post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=30,
                provider_name="gemini",
            )
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        except Exception as err:  # pragma: no cover - defensive
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        return _parse_response(result)


def _parse_response(result: dict) -> ModelResponse:
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return AssistantError(error_type="ProviderError", error_message="No candidates returned")
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    if not isinstance(content, dict):
        return AssistantError(error_type="ProviderError", error_message="Invalid candidate content")
    parts = content.get("parts")
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict) and "functionCall" in part:
                fn = part.get("functionCall")
                name = fn.get("name") if isinstance(fn, dict) else None
                args = fn.get("args") if isinstance(fn, dict) else None
                if name and args is not None:
                    try:
                        args_text = json.dumps(args)
                    except Exception:
                        args_text = str(args)
                    return AssistantToolCall(
                        tool_call_id=f"{name}-call",
                        tool_name=str(name),
                        arguments_json_text=args_text,
                    )
                return AssistantError(error_type="ProviderError", error_message="Malformed tool call from Gemini")
        texts = [p.get("text") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
        if texts:
            return AssistantText(text="".join(texts))
    return AssistantError(error_type="ProviderError", error_message="No assistant content")


def _resolve_api_key(api_key: str | None) -> str:
    if api_key is not None and str(api_key).strip() != "":
        return api_key
    preferred = read_env("NAMEL3SS_GEMINI_API_KEY")
    if preferred is not None and str(preferred).strip() != "":
        return require_env("gemini", "NAMEL3SS_GEMINI_API_KEY", preferred)
    for alias in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        fallback = read_env(alias)
        if fallback is not None and str(fallback).strip() != "":
            return require_env("gemini", alias, fallback)
    raise Namel3ssError(
        "Missing Gemini API key. Set NAMEL3SS_GEMINI_API_KEY (preferred) or GEMINI_API_KEY/GOOGLE_API_KEY."
    )


__all__ = ["GeminiToolCallsAdapter"]
