from __future__ import annotations

import json
import os

from namel3ss.config.model import AppConfig


_SECRET_ALIASES = {
    "NAMEL3SS_OPENAI_API_KEY": "OPENAI_API_KEY",
    "OPENAI_API_KEY": "OPENAI_API_KEY",
    "NAMEL3SS_ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY": "GEMINI_API_KEY",
    "GEMINI_API_KEY": "GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY": "MISTRAL_API_KEY",
    "MISTRAL_API_KEY": "MISTRAL_API_KEY",
    "N3_DATABASE_URL": "DATABASE_URL",
    "DATABASE_URL": "DATABASE_URL",
    "N3_EDGE_KV_URL": "EDGE_KV_URL",
    "EDGE_KV_URL": "EDGE_KV_URL",
}


def normalize_secret_name(name: str) -> str | None:
    return _SECRET_ALIASES.get(name.strip().upper())


def secret_names_in_payload(payload: object, config: AppConfig | None) -> set[str]:
    value_index = _secret_value_index(config)
    if not value_index:
        return set()
    text = _payload_text(payload)
    hits: set[str] = set()
    for value, names in value_index.items():
        if value and value in text:
            hits.update(names)
    return hits


def _secret_value_index(config: AppConfig | None) -> dict[str, set[str]]:
    values: dict[str, str] = {}
    if config:
        _assign(values, "OPENAI_API_KEY", config.openai.api_key)
        _assign(values, "ANTHROPIC_API_KEY", config.anthropic.api_key)
        _assign(values, "GEMINI_API_KEY", config.gemini.api_key)
        _assign(values, "MISTRAL_API_KEY", config.mistral.api_key)
        _assign(values, "DATABASE_URL", config.persistence.database_url)
        _assign(values, "EDGE_KV_URL", config.persistence.edge_kv_url)
    for env_key, canonical in _SECRET_ALIASES.items():
        value = os.getenv(env_key)
        if value and canonical not in values:
            values[canonical] = value
    index: dict[str, set[str]] = {}
    for name, value in values.items():
        if not value:
            continue
        index.setdefault(value, set()).add(name)
    return index


def _payload_text(payload: object) -> str:
    try:
        return json.dumps(payload, sort_keys=True, default=str)
    except Exception:
        return str(payload)


def _assign(target: dict[str, str], key: str, value: str | None) -> None:
    if value:
        target.setdefault(key, value)


__all__ = ["normalize_secret_name", "secret_names_in_payload"]
