from __future__ import annotations

from namel3ss.config.model import GeminiConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.ai.providers._shared.parse import ensure_text_output


class GeminiProvider(AIProvider):
    def __init__(self, *, api_key: str | None, timeout_seconds: int = 30):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_config(cls, config: GeminiConfig) -> "GeminiProvider":
        return cls(api_key=config.api_key)

    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        key = require_env("gemini", "NAMEL3SS_GEMINI_API_KEY", self.api_key)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        text = user_input if not system_prompt else f"{system_prompt}\n{user_input}"
        payload = {"contents": [{"role": "user", "parts": [{"text": text}]}]}
        headers = {"Content-Type": "application/json"}
        try:
            result = post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
                provider_name="gemini",
            )
        except Namel3ssError:
            raise
        text_out = _extract_text(result)
        return AIResponse(output=ensure_text_output("gemini", text_out))


def _extract_text(result: dict) -> str | None:
    candidates = result.get("candidates")
    if isinstance(candidates, list) and candidates:
        content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
        if isinstance(content, dict):
            parts = content.get("parts")
            if isinstance(parts, list):
                texts = [part.get("text") for part in parts if isinstance(part, dict) and isinstance(part.get("text"), str)]
                if texts:
                    return "\n".join(texts)
    return None
