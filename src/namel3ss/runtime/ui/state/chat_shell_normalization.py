from __future__ import annotations

_ROLE_VALUES = {"assistant", "system", "tool", "user"}


def normalize_role(value: object) -> str:
    role = (normalized_text(value) or "assistant").lower()
    if role in _ROLE_VALUES:
        return role
    return "assistant"


def normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in values:
        text = normalized_text(entry)
        if text is None or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def first_text_value(value: object) -> str | None:
    if isinstance(value, list):
        for entry in value:
            text = normalized_text(entry)
            if text is not None:
                return text
        return None
    return normalized_text(value)


def normalized_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text


def slug_text(value: str | None) -> str:
    if value is None:
        return ""
    allowed: list[str] = []
    last_dot = False
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
            last_dot = False
            continue
        if last_dot:
            continue
        allowed.append(".")
        last_dot = True
    return "".join(allowed).strip(".")

