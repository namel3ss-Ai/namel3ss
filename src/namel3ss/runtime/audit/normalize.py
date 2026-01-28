from __future__ import annotations


def stable_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(items)


def stable_bullets(lines: list[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines]


def stable_truncate(text: str, limit: int = 140) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


__all__ = ["stable_bullets", "stable_join", "stable_truncate"]
