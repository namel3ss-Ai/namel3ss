from __future__ import annotations

import re


def slugify(payload: dict) -> dict:
    text = _require_text(payload, "text")
    separator = payload.get("separator", "-")
    if not isinstance(separator, str) or not separator:
        raise ValueError("payload.separator must be a non-empty string")
    slug = re.sub(r"[^a-zA-Z0-9]+", separator, text.strip().lower()).strip(separator)
    return {"text": slug}


def tokenize(payload: dict) -> dict:
    text = _require_text(payload, "text")
    delimiter = payload.get("delimiter")
    if delimiter is None:
        tokens = text.split()
    else:
        if not isinstance(delimiter, str):
            raise ValueError("payload.delimiter must be a string")
        tokens = [part for part in text.split(delimiter) if part]
    return {"tokens": tokens}


def trim(payload: dict) -> dict:
    text = _require_text(payload, "text")
    return {"text": text.strip()}


def lower(payload: dict) -> dict:
    text = _require_text(payload, "text")
    return {"text": text.lower()}


def upper(payload: dict) -> dict:
    text = _require_text(payload, "text")
    return {"text": text.upper()}


def _require_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"payload.{key} must be a string")
    return value


__all__ = ["lower", "slugify", "tokenize", "trim", "upper"]
