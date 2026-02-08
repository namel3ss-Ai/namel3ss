from __future__ import annotations

import difflib
from typing import Dict, Iterable, Tuple

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.icons.registry import icon_names
from namel3ss.theme.ui_theme_tokens import (
    UI_STYLE_THEME_DEFAULT,
    UI_STYLE_THEME_NAMES,
    UI_THEME_TOKEN_ORDER,
    is_ui_theme_token_name,
    normalize_ui_theme_token_value,
)
from namel3ss.ui.presets import resolve_ui_preset


UI_FIELD_ORDER: tuple[str, ...] = ("theme", "accent_color", "density", "motion", "shape", "surface")
UI_OPTIONAL_FIELDS: tuple[str, ...] = ("preset",)
UI_RUNTIME_THEME_VALUES: tuple[str, ...] = (
    "light",
    "dark",
    "white",
    "black",
    "midnight",
    "paper",
    "terminal",
    "enterprise",
)
UI_THEME_TOKEN_FIELDS: tuple[str, ...] = UI_THEME_TOKEN_ORDER

UI_DEFAULTS: dict[str, str] = {
    "theme": "light",
    "accent_color": "blue",
    "density": "comfortable",
    "motion": "subtle",
    "shape": "rounded",
    "surface": "flat",
}

UI_ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "theme": UI_RUNTIME_THEME_VALUES + UI_STYLE_THEME_NAMES,
    "accent_color": ("blue", "indigo", "purple", "pink", "red", "orange", "yellow", "green", "teal", "cyan", "neutral"),
    "density": ("compact", "comfortable", "spacious"),
    "motion": ("none", "subtle"),
    "shape": ("rounded", "soft", "sharp", "square"),
    "surface": ("flat", "outlined", "raised"),
}

STORY_TONES: tuple[str, ...] = ("informative", "success", "caution", "critical", "neutral")
STORY_ICONS: tuple[str, ...] = icon_names()

UI_CONTRAST_UNSAFE_PAIRS: set[tuple[str, str]] = {
    ("white", "yellow"),
}

_KEY_ALIASES: dict[str, str] = {
    "accent color": "accent_color",
    "accent_color": "accent_color",
    "accent": "accent_color",
    "primary color": "primary_color",
    "secondary color": "secondary_color",
    "background color": "background_color",
    "foreground color": "foreground_color",
    "font family": "font_family",
    "font size base": "font_size_base",
    "font weight": "font_weight",
    "spacing scale": "spacing_scale",
    "border radius": "border_radius",
    "shadow level": "shadow_level",
}


def default_ui_settings_with_meta() -> dict[str, tuple[object, int | None, int | None]]:
    return {key: (value, None, None) for key, value in UI_DEFAULTS.items()}


def normalize_ui_settings(raw: dict[str, tuple[object, int | None, int | None]] | dict[str, object] | None) -> dict[str, str]:
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
    if key in UI_DEFAULTS or key in UI_OPTIONAL_FIELDS or is_ui_theme_token_name(key):
        return key
    suggestion = _closest(
        name,
        list(UI_DEFAULTS.keys()) + list(UI_OPTIONAL_FIELDS) + list(UI_THEME_TOKEN_FIELDS) + list(_KEY_ALIASES.keys()),
    )
    suggestion_display = suggestion.replace("_", " ") if suggestion else None
    fix = f'Did you mean \"{suggestion_display}\"?' if suggestion_display else "Use a supported ui field."
    allowed_fields = ", ".join(field.replace("_", " ") for field in UI_FIELD_ORDER + UI_THEME_TOKEN_FIELDS + UI_OPTIONAL_FIELDS)
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


def validate_ui_value(key: str, value: object, *, line: int | None, column: int | None) -> None:
    if is_ui_theme_token_name(key):
        normalize_ui_theme_token_value(key, value, line=line, column=column)
        return
    allowed = UI_ALLOWED_VALUES.get(key, ())
    if value in allowed:
        return
    if not isinstance(value, str):
        readable = ", ".join(allowed)
        raise Namel3ssError(
            build_guidance_message(
                what=f"Invalid {key.replace('_', ' ')} value '{value}'.",
                why=f"Allowed values: {readable}.",
                fix="Use one of the allowed values.",
                example=f'ui:\n  {key.replace("_", " ")} is "{allowed[0]}"',
            ),
            line=line,
            column=column,
        )
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


def _extract_preset(raw: dict[str, tuple[object, int | None, int | None]] | dict[str, object]) -> str | None:
    preset = raw.get("preset")
    if isinstance(preset, tuple) and len(preset) >= 1:
        return preset[0] if isinstance(preset[0], str) else None
    if isinstance(preset, str):
        return preset
    return None


def _has_meta(raw: dict[str, tuple[object, int | None, int | None]] | dict[str, object]) -> bool:
    return any(isinstance(value, tuple) for value in raw.values())


def _explicit_overrides(raw: dict[str, tuple[object, int | None, int | None]] | dict[str, object]) -> dict[str, str]:
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


def explicit_ui_theme_tokens(raw: dict | None) -> dict[str, str | int | float]:
    if not isinstance(raw, dict):
        return {}
    tokens: dict[str, str | int | float] = {}
    for key in UI_THEME_TOKEN_FIELDS:
        value = raw.get(key)
        if not isinstance(value, tuple):
            continue
        candidate = value[0] if value else None
        line = value[1] if len(value) > 1 else None
        column = value[2] if len(value) > 2 else None
        if line is None and column is None:
            continue
        tokens[key] = normalize_ui_theme_token_value(key, candidate, line=line, column=column)
    return tokens


def explicit_ui_theme_name(raw: dict | None) -> str | None:
    if not isinstance(raw, dict):
        return None
    value = raw.get("theme")
    if not isinstance(value, tuple):
        return None
    candidate = value[0] if value else None
    line = value[1] if len(value) > 1 else None
    column = value[2] if len(value) > 2 else None
    if line is None and column is None:
        return None
    if not isinstance(candidate, str):
        return None
    if candidate in UI_STYLE_THEME_NAMES:
        return candidate
    if candidate in UI_RUNTIME_THEME_VALUES:
        return None
    # Keep deterministic error shape here so manifest/lowering cannot silently continue.
    validate_ui_value("theme", candidate, line=line, column=column)
    return None


def runtime_theme_setting_from_ui(raw: dict | None, fallback: str, normalized_theme: str | None = None) -> str:
    if not isinstance(raw, dict):
        return fallback
    value = raw.get("theme")
    if isinstance(value, tuple):
        candidate = value[0] if value else None
        if isinstance(candidate, str) and candidate in UI_RUNTIME_THEME_VALUES:
            line = value[1] if len(value) > 1 else None
            column = value[2] if len(value) > 2 else None
            if line is not None or column is not None:
                return candidate
    preset = raw.get("preset")
    if isinstance(preset, tuple):
        line = preset[1] if len(preset) > 1 else None
        column = preset[2] if len(preset) > 2 else None
        if (line is not None or column is not None) and isinstance(normalized_theme, str):
            if normalized_theme in UI_RUNTIME_THEME_VALUES:
                return normalized_theme
    return fallback


def validate_ui_contrast(theme: str, accent: str, raw: dict | None) -> None:
    allowed_themes = set(UI_ALLOWED_VALUES.get("theme", ()))
    allowed_accents = set(UI_ALLOWED_VALUES.get("accent_color", ()))
    if theme not in UI_RUNTIME_THEME_VALUES:
        return
    if theme not in allowed_themes or accent not in allowed_accents:
        return
    if (theme, accent) in _contrast_safe_pairs():
        return
    line, column = _ui_setting_location(raw, "accent_color")
    if line is None and column is None:
        line, column = _ui_setting_location(raw, "theme")
    if line is None and column is None:
        line, column = _ui_setting_location(raw, "preset")
    raise Namel3ssError(
        build_guidance_message(
            what=f'UI theme "{theme}" with accent "{accent}" does not meet contrast requirements.',
            why="Theme and accent combinations must meet the contrast contract.",
            fix="Choose a supported theme and accent color pairing.",
            example='ui:\n  theme is "light"\n  accent color is "blue"',
        ),
        line=line,
        column=column,
    )


def _contrast_safe_pairs() -> set[tuple[str, str]]:
    themes = UI_ALLOWED_VALUES.get("theme", ())
    accents = UI_ALLOWED_VALUES.get("accent_color", ())
    pairs = {(theme, accent) for theme in themes for accent in accents}
    for pair in UI_CONTRAST_UNSAFE_PAIRS:
        pairs.discard(pair)
    return pairs


def _ui_setting_location(raw: dict | None, key: str) -> tuple[int | None, int | None]:
    if not isinstance(raw, dict):
        return None, None
    value = raw.get(key)
    if isinstance(value, tuple):
        line = value[1] if len(value) > 1 else None
        column = value[2] if len(value) > 2 else None
        return line, column
    return None, None


__all__ = [
    "UI_ALLOWED_VALUES",
    "UI_CONTRAST_UNSAFE_PAIRS",
    "UI_DEFAULTS",
    "UI_FIELD_ORDER",
    "UI_RUNTIME_THEME_VALUES",
    "UI_STYLE_THEME_DEFAULT",
    "UI_STYLE_THEME_NAMES",
    "UI_THEME_TOKEN_FIELDS",
    "UI_OPTIONAL_FIELDS",
    "STORY_TONES",
    "closest_value",
    "default_ui_settings_with_meta",
    "explicit_ui_theme_name",
    "explicit_ui_theme_tokens",
    "normalize_ui_settings",
    "runtime_theme_setting_from_ui",
    "validate_ui_contrast",
    "validate_ui_field",
    "validate_ui_value",
]
