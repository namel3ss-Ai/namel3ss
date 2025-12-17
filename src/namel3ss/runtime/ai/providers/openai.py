from __future__ import annotations

from namel3ss.config.model import OpenAIConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.ai.providers._shared.parse import ensure_text_output


class OpenAIProvider(AIProvider):
    def __init__(self, *, api_key: str | None, base_url: str = "https://api.openai.com", timeout_seconds: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_config(cls, config: OpenAIConfig) -> "OpenAIProvider":
        return cls(api_key=config.api_key, base_url=config.base_url)

    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        key = require_env("openai", "NAMEL3SS_OPENAI_API_KEY", self.api_key)
        url = f"{self.base_url}/v1/responses"
        payload = {"model": model, "input": user_input}
        if system_prompt:
            payload["system"] = system_prompt
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            result = post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
                provider_name="openai",
            )
        except Namel3ssError:
            raise
        text = _extract_text(result)
        return AIResponse(output=ensure_text_output("openai", text))


def _extract_text(result: dict) -> str | None:
    if isinstance(result.get("output_text"), str):
        return result["output_text"]
    output = result.get("output")
    if isinstance(output, list) and output:
        content = output[0].get("content") if isinstance(output[0], dict) else None
        if isinstance(content, list) and content:
            text = content[0].get("text")
            if isinstance(text, str):
                return text
    message = result.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    return None
