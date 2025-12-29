from __future__ import annotations


def ensure_object(value: object, *, key: str = "result") -> dict:
    if isinstance(value, dict):
        return value
    return {key: value}


def unwrap_text(value: object) -> object:
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
    return value


__all__ = ["ensure_object", "unwrap_text"]
