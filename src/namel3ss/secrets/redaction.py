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
    "NAMEL3SS_OPENAI_API_KEY",
    "NAMEL3SS_ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY",
    "N3_DATABASE_URL",
    "N3_EDGE_KV_URL",
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


def redact_payload(value: object, secret_values: Iterable[str]) -> object:
    if isinstance(value, dict):
        return {key: redact_payload(val, secret_values) for key, val in value.items()}
    if isinstance(value, list):
        return [redact_payload(item, secret_values) for item in value]
    if isinstance(value, str):
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
