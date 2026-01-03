from __future__ import annotations

from namel3ss.config.model import MistralConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.ai.providers._shared.parse import ensure_text_output
from namel3ss.security import read_env


class MistralProvider(AIProvider):
    def __init__(self, *, api_key: str | None, timeout_seconds: int = 30):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_config(cls, config: MistralConfig) -> "MistralProvider":
        return cls(api_key=config.api_key)

    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        key = _resolve_api_key(self.api_key)
        url = "https://api.mistral.ai/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})
        payload = {"model": model, "messages": messages}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            result = post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
                provider_name="mistral",
            )
        except Namel3ssError:
            raise
        text = _extract_text(result)
        return AIResponse(output=ensure_text_output("mistral", text))


def _extract_text(result: dict) -> str | None:
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
    return None


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
