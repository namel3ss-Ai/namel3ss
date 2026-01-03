from __future__ import annotations

from namel3ss.config.model import OpenAIConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.http.client import post_json
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.diagnostics import categorize_ai_error
from namel3ss.runtime.ai.providers._shared.errors import build_provider_diagnostic, require_env
from namel3ss.runtime.ai.providers._shared.parse import ensure_text_output, normalize_ai_text
from namel3ss.security import read_env
from namel3ss.secrets import collect_secret_values, redact_payload


class OpenAIProvider(AIProvider):
    def __init__(self, *, api_key: str | None, base_url: str = "https://api.openai.com", timeout_seconds: int = 30):
        self.api_key = api_key
        self.base_url = _normalize_base_url(base_url)
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_config(cls, config: OpenAIConfig) -> "OpenAIProvider":
        return cls(api_key=config.api_key, base_url=config.base_url)

    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        url = f"{self.base_url}/v1/responses"
        secret_values = _secret_values(None)
        try:
            key = _resolve_api_key(self.api_key)
            secret_values = _secret_values(key)
            payload = {"model": model, "input": user_input}
            if system_prompt:
                payload["instructions"] = system_prompt
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            result = post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
                provider_name="openai",
                secret_values=secret_values,
            )
            text = _extract_text(result)
            if text is not None:
                text = normalize_ai_text(text, provider_name="openai", secret_values=secret_values)
            return AIResponse(output=ensure_text_output("openai", text))
        except Namel3ssError as err:
            raise _wrap_openai_error(err, url=url, secret_values=secret_values) from err


def _resolve_api_key(api_key: str | None) -> str:
    if api_key is not None and str(api_key).strip() != "":
        return api_key
    preferred = read_env("NAMEL3SS_OPENAI_API_KEY")
    if preferred is not None and str(preferred).strip() != "":
        return require_env("openai", "NAMEL3SS_OPENAI_API_KEY", preferred)
    fallback = read_env("OPENAI_API_KEY")
    if fallback is not None and str(fallback).strip() != "":
        return require_env("openai", "OPENAI_API_KEY", fallback)
    raise Namel3ssError(
        "Missing OpenAI API key. Set NAMEL3SS_OPENAI_API_KEY (preferred) or OPENAI_API_KEY."
    )


def _extract_text(result: dict) -> str | None:
    if isinstance(result.get("output_text"), str):
        return result["output_text"]
    output = result.get("output")
    if isinstance(output, list) and output:
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    message = result.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
    return None


def _normalize_base_url(raw: str) -> str:
    url = (raw or "").strip()
    url = url.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3].rstrip("/")
    return url or "https://api.openai.com"


def _wrap_openai_error(err: Namel3ssError, *, url: str, secret_values: list[str]) -> Namel3ssError:
    details = dict(err.details or {})
    details["provider"] = "openai"
    details["url"] = url
    diagnostic = details.get("diagnostic")
    error = details.get("error")
    if not isinstance(diagnostic, dict):
        code = error.get("code") if isinstance(error, dict) else None
        err_type = error.get("type") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        diagnostic = build_provider_diagnostic(
            "openai",
            url=url,
            status=_coerce_int(details.get("status")),
            code=code,
            error_type=err_type,
            message=message or err.message,
            secret_values=secret_values,
        )
        details["diagnostic"] = diagnostic
    else:
        if diagnostic.get("provider") != "openai":
            diagnostic["provider"] = "openai"
        if not diagnostic.get("url"):
            diagnostic["url"] = url
        if diagnostic.get("status") is None and details.get("status") is not None:
            diagnostic["status"] = _coerce_int(details.get("status"))
    if isinstance(error, dict):
        error = redact_payload(error, secret_values)
        message = error.get("message")
        if isinstance(message, str):
            error["message"] = _truncate(_compact_text(message))
        details["error"] = error
        if not diagnostic.get("message"):
            diagnostic["message"] = error.get("message")
    if not diagnostic.get("message"):
        diagnostic["message"] = build_provider_diagnostic(
            "openai",
            url=url,
            status=_coerce_int(details.get("status")),
            message=err.message,
            secret_values=secret_values,
        ).get("message")
    diagnostic.update(categorize_ai_error(diagnostic))
    message = _format_openai_error_message(diagnostic)
    return Namel3ssError(message, details=details)


def _format_openai_error_message(diagnostic: dict) -> str:
    parts = [
        f"provider={diagnostic.get('provider')}",
        f"url={diagnostic.get('url')}",
    ]
    status = diagnostic.get("status")
    if status is not None:
        parts.append(f"status={status}")
    code = diagnostic.get("code")
    if code:
        parts.append(f"code={code}")
    err_type = diagnostic.get("type")
    if err_type:
        parts.append(f"type={err_type}")
    message = diagnostic.get("message")
    if message:
        parts.append(f"message={message}")
    return "OpenAI request failed (" + ", ".join(parts) + ")"


def _secret_values(api_key: str | None) -> list[str]:
    values = collect_secret_values()
    if api_key and api_key not in values:
        values.append(api_key)
    return values


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _truncate(value: str, limit: int = 240) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
