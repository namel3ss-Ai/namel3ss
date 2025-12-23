from __future__ import annotations

from typing import Iterable

from namel3ss.secrets import redact_text


_ACTOR_FIELDS = {
    "id",
    "user_id",
    "email",
    "name",
    "role",
    "trust_level",
    "organization_id",
    "org_id",
    "tenant_id",
    "tenant",
}


def actor_summary(identity: dict | None) -> dict:
    if not identity:
        return {}
    return {key: identity[key] for key in _ACTOR_FIELDS if key in identity}


def summarize_value(
    value: object,
    *,
    preview_limit: int = 80,
    secret_values: Iterable[str] | None = None,
) -> dict:
    if isinstance(value, dict):
        keys = sorted(list(value.keys()))
        return {"type": "object", "keys": keys[:10], "count": len(keys)}
    if isinstance(value, list):
        return {"type": "list", "count": len(value)}
    if isinstance(value, str):
        redacted = redact_text(value, secret_values or [])
        preview = redacted[:preview_limit]
        if len(redacted) > preview_limit:
            preview += "..."
        return {"type": "text", "chars": len(redacted), "preview": preview}
    if isinstance(value, (int, float, bool)) or value is None:
        return {"type": type(value).__name__, "value": value}
    text = str(value)
    if secret_values:
        text = redact_text(text, secret_values)
    return {"type": type(value).__name__, "value": text}


__all__ = ["actor_summary", "summarize_value"]
