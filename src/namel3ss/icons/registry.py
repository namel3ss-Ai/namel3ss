from __future__ import annotations

import difflib
from functools import lru_cache
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.resources import icons_root


def normalize_icon_name(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower().replace(" ", "_").replace("-", "_")


@lru_cache(maxsize=1)
def icon_registry() -> dict[str, Path]:
    root = icons_root()
    if not root.exists():
        raise Namel3ssError("Icon registry is missing; icons are not available.")
    mapping: dict[str, Path] = {}
    paths = sorted(root.rglob("*.svg"), key=lambda p: (p.stem, p.as_posix()))
    for path in paths:
        name = path.stem
        if name in mapping:
            raise Namel3ssError(f"Duplicate icon id '{name}' in registry.")
        mapping[name] = path
    return mapping


def icon_names() -> tuple[str, ...]:
    return tuple(icon_registry().keys())


def closest_icon(name: str) -> str | None:
    choices = list(icon_registry().keys())
    matches = difflib.get_close_matches(name, choices, n=1, cutoff=0.6)
    return matches[0] if matches else None


def validate_icon_name(value: str | None, *, line: int | None = None, column: int | None = None) -> str | None:
    if value is None:
        return None
    normalized = normalize_icon_name(value)
    if not normalized:
        raise Namel3ssError("Icon name cannot be empty.", line=line, column=column, details={"error_id": "icon.invalid"})
    if normalized in icon_registry():
        return normalized
    suggestion = closest_icon(normalized)
    fix = f'Did you mean "{suggestion}"?' if suggestion else "Use a built-in icon from the registry."
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown icon '{value}'.",
            why="Icons must be chosen from the built-in registry.",
            fix=fix + " Run `n3 icons` to list options.",
            example="icon is add",
        ),
        line=line,
        column=column,
        details={"error_id": "icon.invalid", "keyword": normalized},
    )


__all__ = ["icon_registry", "icon_names", "validate_icon_name", "normalize_icon_name", "closest_icon"]
