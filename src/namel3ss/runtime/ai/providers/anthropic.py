from __future__ import annotations

from namel3ss.config.model import AnthropicConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.ai.providers._shared.parse import ensure_text_output

ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    def __init__(self, *, api_key: str | None, timeout_seconds: int = 30):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_config(cls, config: AnthropicConfig) -> "AnthropicProvider":
        return cls(api_key=config.api_key)

    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        key = require_env("anthropic", "NAMEL3SS_ANTHROPIC_API_KEY", self.api_key)
        url = "https://api.anthropic.com/v1/messages"
        payload = {"model": model, "messages": [{"role": "user", "content": user_input}]}
        if system_prompt:
            payload["system"] = system_prompt
        headers = {
            "x-api-key": key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        try:
            result = post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
                provider_name="anthropic",
            )
        except Namel3ssError:
            raise
        text = _extract_text(result)
        return AIResponse(output=ensure_text_output("anthropic", text))


def _extract_text(result: dict) -> str | None:
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                return text
    return None
