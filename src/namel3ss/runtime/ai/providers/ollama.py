from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.provider import AIProvider, AIResponse


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
        data = json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except (HTTPError, URLError) as err:
            detail = getattr(err, "reason", None) or getattr(err, "code", "") or str(err)
            raise Namel3ssError(f"Ollama is not reachable at {self.host}. Is Ollama running? ({detail})") from err
        try:
            result = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as err:
            raise Namel3ssError("Invalid response from Ollama (could not decode JSON)") from err
        content = _extract_content(result)
        if content is None:
            raise Namel3ssError("Invalid response from Ollama (missing message content)")
        return AIResponse(output=content)


def _extract_content(payload: dict) -> str | None:
    if "message" in payload and isinstance(payload["message"], dict):
        content = payload["message"].get("content")
        if isinstance(content, str):
            return content
    if "response" in payload and isinstance(payload["response"], str):
        return payload["response"]
    return None
