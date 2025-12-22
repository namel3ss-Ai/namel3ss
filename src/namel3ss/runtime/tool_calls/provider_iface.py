from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List, Optional, Protocol

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.provider import AIResponse, AIToolCallResponse
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration


@dataclass(frozen=True)
class AssistantText:
    text: str


@dataclass(frozen=True)
class AssistantToolCall:
    tool_call_id: str
    tool_name: str
    arguments_json_text: str


@dataclass(frozen=True)
class AssistantError:
    error_type: str
    error_message: str


ModelResponse = AssistantText | AssistantToolCall | AssistantError


class ProviderAdapter(Protocol):
    def run_model(self, messages: List[dict], tools: List[ToolDeclaration], policy: ToolCallPolicy) -> ModelResponse:
        ...


class MockProviderAdapter:
    def __init__(self, provider, *, model: str, system_prompt: Optional[str]):
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt
        self.tool_call_counter = 0

    def run_model(self, messages: List[dict], tools: List[ToolDeclaration], policy: ToolCallPolicy) -> ModelResponse:
        user_messages = [m for m in messages if m.get("role") == "user"]
        user_input = user_messages[-1]["content"] if user_messages else ""
        tool_payload = [{"name": tool.name} for tool in tools]
        try:
            response = self.provider.ask(
                model=self.model,
                system_prompt=self.system_prompt,
                user_input=user_input,
                tools=tool_payload,
                memory=None,
                tool_results=[],
            )
        except Namel3ssError as err:
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        except Exception as err:  # pragma: no cover - defensive
            return AssistantError(error_type=err.__class__.__name__, error_message=str(err))
        if isinstance(response, AIResponse):
            return AssistantText(text=response.output)
        if isinstance(response, AIToolCallResponse):
            tool_call_id = f"tool-{self.tool_call_counter}"
            self.tool_call_counter += 1
            arguments_json_text = response.args
            if not isinstance(arguments_json_text, str):
                try:
                    arguments_json_text = json.dumps(arguments_json_text)
                except Exception:
                    arguments_json_text = str(arguments_json_text)
            return AssistantToolCall(
                tool_call_id=tool_call_id,
                tool_name=response.tool_name,
                arguments_json_text=arguments_json_text,
            )
        return AssistantError(error_type="ProviderError", error_message="Unexpected provider response")


def get_provider_adapter(provider_name: str, provider: Any, *, model: str, system_prompt: Optional[str]) -> Optional[ProviderAdapter]:
    if provider_name == "mock":
        return MockProviderAdapter(provider, model=model, system_prompt=system_prompt)
    if provider_name == "openai":
        from namel3ss.runtime.providers.openai.tool_calls_adapter import OpenAIChatCompletionsAdapter

        return OpenAIChatCompletionsAdapter.from_provider(provider, model=model)
    if provider_name == "anthropic":
        from namel3ss.runtime.providers.anthropic.tool_calls_adapter import AnthropicMessagesAdapter

        return AnthropicMessagesAdapter.from_provider(provider)
    if provider_name == "gemini":
        from namel3ss.runtime.providers.gemini.tool_calls_adapter import GeminiToolCallsAdapter

        return GeminiToolCallsAdapter.from_provider(provider)
    if provider_name == "mistral":
        from namel3ss.runtime.providers.mistral.tool_calls_adapter import MistralChatAdapter

        return MistralChatAdapter.from_provider(provider)
    return None


__all__ = [
    "AssistantError",
    "AssistantText",
    "AssistantToolCall",
    "ModelResponse",
    "ProviderAdapter",
    "MockProviderAdapter",
    "get_provider_adapter",
]
