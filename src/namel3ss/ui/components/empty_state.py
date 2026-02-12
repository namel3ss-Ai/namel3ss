from __future__ import annotations


def build_empty_state(*, title: str, text: str, hint: str | None = None) -> dict[str, object]:
    payload = {
        "hint": hint.strip() if isinstance(hint, str) else "",
        "text": text.strip() if isinstance(text, str) else "",
        "title": title.strip() if isinstance(title, str) else "",
    }
    return payload


__all__ = ["build_empty_state"]
