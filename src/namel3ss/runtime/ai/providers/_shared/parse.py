from __future__ import annotations

import json

from namel3ss.errors.base import Namel3ssError
from namel3ss.secrets.redaction import collect_secret_values, redact_payload, redact_text


def ensure_text_output(provider_name: str, text: object) -> str:
    if isinstance(text, str) and text.strip() != "":
        return text
    raise Namel3ssError(f"Provider '{provider_name}' returned an invalid response")


def json_loads_or_error(provider_name: str, raw: bytes) -> dict:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as err:  # json.JSONDecodeError or UnicodeError
        raise Namel3ssError(f"Provider '{provider_name}' returned an invalid response") from err


def normalize_ai_text(
    value: object,
    *,
    provider_name: str | None = None,
    secret_values: list[str] | None = None,
) -> str:
    merged_secrets = _merge_secret_values(secret_values)
    if isinstance(value, str):
        return _redact_text(value, merged_secrets)
    if isinstance(value, dict):
        for key in ("output", "output_text", "text", "content", "message"):
            if key in value:
                return normalize_ai_text(
                    value[key],
                    provider_name=provider_name,
                    secret_values=secret_values,
                )
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(_redact_text(item, merged_secrets))
                continue
            if isinstance(item, dict):
                for key in ("text", "content", "output", "output_text", "message"):
                    if key in item:
                        parts.append(
                            normalize_ai_text(
                                item[key],
                                provider_name=provider_name,
                                secret_values=secret_values,
                            )
                        )
                        break
        if parts:
            return "\n".join(parts)
    return _redacted_json(value, merged_secrets)


def _redacted_json(value: object, secret_values: list[str]) -> str:
    redacted = redact_payload(value, secret_values)
    try:
        return json.dumps(redacted, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return _redact_text(str(redacted), secret_values)


def _merge_secret_values(secret_values: list[str] | None) -> list[str]:
    merged = collect_secret_values()
    if secret_values:
        merged.extend(secret_values)
    return merged


def _redact_text(value: str, secret_values: list[str]) -> str:
    return redact_text(value, secret_values)


__all__ = ["ensure_text_output", "json_loads_or_error", "normalize_ai_text"]
