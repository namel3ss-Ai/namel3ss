from __future__ import annotations

import difflib
from typing import Dict, Iterable, Tuple

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.icons.registry import icon_names


UI_FIELD_ORDER: tuple[str, ...] = ("theme", "accent_color", "density", "motion", "shape", "surface")

UI_DEFAULTS: dict[str, str] = {
    "theme": "light",
    "accent_color": "blue",
    "density": "comfortable",
    "motion": "subtle",
    "shape": "rounded",
    "surface": "flat",
}

UI_ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "theme": ("light", "dark", "white", "black", "midnight", "paper", "terminal", "enterprise"),
    "accent_color": ("blue", "indigo", "purple", "pink", "red", "orange", "yellow", "green", "teal", "cyan", "neutral"),
    "density": ("compact", "comfortable", "spacious"),
    "motion": ("none", "subtle"),
    "shape": ("rounded", "soft", "sharp", "square"),
    "surface": ("flat", "outlined", "raised"),
}

STORY_TONES: tuple[str, ...] = ("informative", "success", "caution", "critical", "neutral")
STORY_ICONS: tuple[str, ...] = icon_names()

_KEY_ALIASES: dict[str, str] = {
    "accent color": "accent_color",
    "accent_color": "accent_color",
    "accent": "accent_color",
}


def default_ui_settings_with_meta() -> dict[str, tuple[str, int | None, int | None]]:
    return {key: (value, None, None) for key, value in UI_DEFAULTS.items()}


def normalize_ui_settings(raw: dict[str, tuple[str, int | None, int | None]] | dict[str, str] | None) -> dict[str, str]:
    values = dict(UI_DEFAULTS)
    if raw:
        for key, meta_val in raw.items():
            if key not in values:
                continue
            if isinstance(meta_val, tuple) and len(meta_val) >= 1:
                values[key] = meta_val[0]
            else:
                values[key] = meta_val
    return {key: values[key] for key in UI_FIELD_ORDER}


def validate_ui_field(name: str, *, line: int | None, column: int | None) -> str:
    key = _KEY_ALIASES.get(name, name)
    if key in UI_DEFAULTS:
        return key
    suggestion = _closest(name, list(UI_DEFAULTS.keys()) + list(_KEY_ALIASES.keys()))
    suggestion_display = suggestion.replace("_", " ") if suggestion else None
    fix = f'Did you mean \"{suggestion_display}\"?' if suggestion_display else "Use a supported ui field."
    allowed_fields = ", ".join(field.replace("_", " ") for field in UI_FIELD_ORDER)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown ui field '{name}'.",
            why=f"Allowed fields: {allowed_fields}.",
            fix=fix,
            example='ui:\n  theme is "light"\n  accent color is "blue"',
        ),
        line=line,
        column=column,
    )


def validate_ui_value(key: str, value: str, *, line: int | None, column: int | None) -> None:
    allowed = UI_ALLOWED_VALUES.get(key, ())
    if value in allowed:
        return
    suggestion = _closest(value, allowed)
    fix = f'Did you mean "{suggestion}"?' if suggestion else f"Use one of: {', '.join(allowed)}."
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown {key.replace('_', ' ')} '{value}'.",
            why=f"Allowed values: {', '.join(allowed)}.",
            fix=fix,
            example=f'ui:\n  {key.replace("_", " ")} is "{allowed[0]}"',
        ),
        line=line,
        column=column,
    )


def _closest(value: str, choices: Iterable[str]) -> str | None:
    matches = difflib.get_close_matches(value, list(choices), n=1, cutoff=0.6)
    return matches[0] if matches else None


def closest_value(value: str, choices: Iterable[str]) -> str | None:
    return _closest(value, choices)


__all__ = [
    "UI_ALLOWED_VALUES",
    "UI_DEFAULTS",
    "UI_FIELD_ORDER",
    "STORY_TONES",
    "closest_value",
    "default_ui_settings_with_meta",
    "normalize_ui_settings",
    "validate_ui_field",
    "validate_ui_value",
]
