from __future__ import annotations

from namel3ss.errors.guidance import build_guidance_message


def escaped_identifier(name: str) -> str:
    return f"`{name}`"


def reserved_identifier_message(name: str) -> str:
    escaped = escaped_identifier(name)
    return build_guidance_message(
        what=f"Identifier '{name}' is reserved.",
        why="Reserved words have fixed meaning in the grammar.",
        fix=f"Use the escaped form {escaped} or choose a different name.",
        example=f"let {escaped} is \"...\"",
    )


def reserved_identifier_details(name: str) -> dict[str, str]:
    return {"error_id": "parse.reserved_identifier", "keyword": name}


def reserved_identifier_diagnostic(name: str) -> tuple[str, dict[str, str]]:
    return reserved_identifier_message(name), reserved_identifier_details(name)


__all__ = [
    "escaped_identifier",
    "reserved_identifier_details",
    "reserved_identifier_diagnostic",
    "reserved_identifier_message",
]
