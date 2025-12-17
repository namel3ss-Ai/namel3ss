from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.errors import map_http_error
from namel3ss.runtime.ai.providers._shared.parse import ensure_text_output


class OllamaProvider(AIProvider):
    def __init__(self, *, host: str, timeout_seconds: int = 30):
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        url = f"{self.host}/api/chat"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})
        payload = {"model": model, "messages": messages}
        try:
            result = post_json(url=url, headers={"Content-Type": "application/json"}, payload=payload, timeout_seconds=self.timeout_seconds, provider_name="ollama")
        except Namel3ssError:
            raise
        except Exception as err:
            raise map_http_error("ollama", err) from err
        content = _extract_content(result)
        return AIResponse(output=ensure_text_output("ollama", content))


def _extract_content(payload: dict) -> str | None:
    if "message" in payload and isinstance(payload["message"], dict):
        content = payload["message"].get("content")
        if isinstance(content, str):
            return content
    if "response" in payload and isinstance(payload["response"], str):
        return payload["response"]
    return None
