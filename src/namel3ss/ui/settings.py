from __future__ import annotations

import difflib
from typing import Dict, Iterable, Tuple

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.icons.registry import icon_names
from namel3ss.ui.presets import resolve_ui_preset


UI_FIELD_ORDER: tuple[str, ...] = ("theme", "accent_color", "density", "motion", "shape", "surface")
UI_OPTIONAL_FIELDS: tuple[str, ...] = ("preset",)

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
    if not raw:
        return _ordered_settings(values, None)
    preset = _extract_preset(raw)
    if _has_meta(raw):
        if preset:
            values.update(_preset_values(preset))
        for key, value in _explicit_overrides(raw).items():
            values[key] = value
        return _ordered_settings(values, preset)
    for key, value in raw.items():
        if key not in values:
            continue
        values[key] = value
    return _ordered_settings(values, preset)


def validate_ui_field(name: str, *, line: int | None, column: int | None) -> str:
    key = _KEY_ALIASES.get(name, name)
    if key in UI_DEFAULTS or key in UI_OPTIONAL_FIELDS:
        return key
    suggestion = _closest(name, list(UI_DEFAULTS.keys()) + list(UI_OPTIONAL_FIELDS) + list(_KEY_ALIASES.keys()))
    suggestion_display = suggestion.replace("_", " ") if suggestion else None
    fix = f'Did you mean \"{suggestion_display}\"?' if suggestion_display else "Use a supported ui field."
    allowed_fields = ", ".join(field.replace("_", " ") for field in UI_FIELD_ORDER + UI_OPTIONAL_FIELDS)
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


def _ordered_settings(values: dict[str, str], preset: str | None) -> dict[str, str]:
    ordered = {key: values[key] for key in UI_FIELD_ORDER}
    if preset is not None:
        ordered["preset"] = preset
    return ordered


def _extract_preset(raw: dict[str, tuple[str, int | None, int | None]] | dict[str, str]) -> str | None:
    preset = raw.get("preset")
    if isinstance(preset, tuple) and len(preset) >= 1:
        return preset[0]
    if isinstance(preset, str):
        return preset
    return None


def _has_meta(raw: dict[str, tuple[str, int | None, int | None]] | dict[str, str]) -> bool:
    return any(isinstance(value, tuple) for value in raw.values())


def _explicit_overrides(raw: dict[str, tuple[str, int | None, int | None]] | dict[str, str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for key, meta_val in raw.items():
        if key not in UI_DEFAULTS:
            continue
        if isinstance(meta_val, tuple):
            value = meta_val[0] if meta_val else None
            line = meta_val[1] if len(meta_val) > 1 else None
            column = meta_val[2] if len(meta_val) > 2 else None
            if line is None and column is None:
                continue
            if isinstance(value, str):
                overrides[key] = value
        elif isinstance(meta_val, str):
            overrides[key] = meta_val
    return overrides


def _preset_values(preset: str) -> dict[str, str]:
    if not preset:
        return {}
    return resolve_ui_preset(preset)


__all__ = [
    "UI_ALLOWED_VALUES",
    "UI_DEFAULTS",
    "UI_FIELD_ORDER",
    "UI_OPTIONAL_FIELDS",
    "STORY_TONES",
    "closest_value",
    "default_ui_settings_with_meta",
    "normalize_ui_settings",
    "validate_ui_field",
    "validate_ui_value",
]
