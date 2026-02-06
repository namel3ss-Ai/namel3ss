from __future__ import annotations

import os
from typing import Iterable

from namel3ss.config.model import AppConfig


_KNOWN_ENV_VARS = {
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "OPENAI_API_KEY",
    "HUGGINGFACE_API_KEY",
    "HUGGINGFACEHUB_API_TOKEN",
    "SPEECH_API_KEY",
    "THIRD_PARTY_APIS_KEY",
    "NAMEL3SS_OPENAI_API_KEY",
    "NAMEL3SS_ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY",
    "NAMEL3SS_HUGGINGFACE_API_KEY",
    "NAMEL3SS_SPEECH_API_KEY",
    "NAMEL3SS_THIRD_PARTY_APIS_KEY",
    "N3_DATABASE_URL",
    "N3_EDGE_KV_URL",
    "N3_AUTH_SIGNING_KEY",
    "N3_AUTH_PASSWORD",
}

_SAFE_LITERAL_KEYS = {
    "event_type",
    "stream_channel",
}


def collect_secret_values(config: AppConfig | None = None) -> list[str]:
    values: list[str] = []
    for key in _KNOWN_ENV_VARS:
        env_value = os.getenv(key)
        if env_value:
            values.append(env_value)
    if config:
        candidates = [
            getattr(config.openai, "api_key", None),
            getattr(config.anthropic, "api_key", None),
            getattr(config.gemini, "api_key", None),
            getattr(config.mistral, "api_key", None),
            getattr(config.persistence, "database_url", None),
            getattr(config.persistence, "edge_kv_url", None),
            getattr(config.authentication, "signing_key", None),
            getattr(config.authentication, "password", None),
        ]
        values.extend([val for val in candidates if isinstance(val, str) and val])
    return _unique(values)


def redact_text(text: str, secret_values: Iterable[str]) -> str:
    if not text:
        return text
    redacted = text
    for secret in _sorted_secrets(secret_values):
        if secret in redacted:
            redacted = redacted.replace(secret, "***REDACTED***")
    return redacted


def redact_payload(
    value: object,
    secret_values: Iterable[str],
    *,
    _parent_key: str | None = None,
) -> object:
    if isinstance(value, dict):
        return {
            key: redact_payload(val, secret_values, _parent_key=str(key))
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [
            redact_payload(item, secret_values, _parent_key=_parent_key)
            for item in value
        ]
    if isinstance(value, str):
        if _parent_key in _SAFE_LITERAL_KEYS:
            return value
        return redact_text(value, secret_values)
    return value


def _sorted_secrets(secret_values: Iterable[str]) -> list[str]:
    filtered = [val for val in _unique(secret_values) if isinstance(val, str) and len(val) >= 4]
    return sorted(filtered, key=len, reverse=True)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


__all__ = ["collect_secret_values", "redact_text", "redact_payload"]
