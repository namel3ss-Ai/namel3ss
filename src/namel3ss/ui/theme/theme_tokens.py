from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.theme.ui_theme_tokens import (
    UI_THEME_TOKEN_ORDER,
    compile_ui_theme,
    normalize_ui_theme_token_value,
)


THEME_BASE_ORDER: tuple[str, ...] = ("default", "dark", "high_contrast")

_THEME_BASE_OVERRIDES: dict[str, dict[str, object]] = {
    "default": {},
    "dark": {
        "primary_color": "#60A5FA",
        "secondary_color": "#38BDF8",
        "background_color": "#0F172A",
        "foreground_color": "#F8FAFC",
        "shadow_level": 2,
    },
    "high_contrast": {
        "primary_color": "#FFD400",
        "secondary_color": "#00FFFF",
        "background_color": "#000000",
        "foreground_color": "#FFFFFF",
        "font_weight": 600,
        "spacing_scale": 1.1,
        "border_radius": 4,
        "shadow_level": 0,
    },
}

THEME_TOKEN_SCHEMA: dict[str, dict[str, str]] = {
    "primary_color": {
        "type": "color",
        "category": "color",
        "description": "Primary accent used for primary actions and links.",
    },
    "secondary_color": {
        "type": "color",
        "category": "color",
        "description": "Secondary accent for supporting emphasis.",
    },
    "background_color": {
        "type": "color",
        "category": "color",
        "description": "Application background color.",
    },
    "foreground_color": {
        "type": "color",
        "category": "color",
        "description": "Primary text color.",
    },
    "font_family": {
        "type": "string",
        "category": "typography",
        "description": "Font family stack.",
    },
    "font_size_base": {
        "type": "number",
        "category": "typography",
        "description": "Base font size in pixels.",
    },
    "font_weight": {
        "type": "number",
        "category": "typography",
        "description": "Default text weight.",
    },
    "spacing_scale": {
        "type": "number",
        "category": "spacing",
        "description": "Global spacing multiplier.",
    },
    "border_radius": {
        "type": "number",
        "category": "radius",
        "description": "Default corner radius in pixels.",
    },
    "shadow_level": {
        "type": "number",
        "category": "elevation",
        "description": "Shadow intensity level from 0 to 3.",
    },
}


@dataclass(frozen=True)
class ResolvedThemeTokens:
    base_theme: str
    tokens: dict[str, str | int | float]


def base_theme_names() -> tuple[str, ...]:
    return THEME_BASE_ORDER


def is_base_theme_name(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower().replace("-", "_") in THEME_BASE_ORDER


def normalize_base_theme_name(
    value: str | None,
    *,
    line: int | None = None,
    column: int | None = None,
) -> str:
    if not isinstance(value, str):
        _raise_invalid_base_theme(value, line=line, column=column)
    normalized = value.strip().lower().replace("-", "_")
    if normalized in THEME_BASE_ORDER:
        return normalized
    _raise_invalid_base_theme(value, line=line, column=column)
    return "default"


def default_theme_tokens() -> dict[str, str | int | float]:
    return resolve_base_theme_tokens("default")


def resolve_base_theme_tokens(base_theme: str) -> dict[str, str | int | float]:
    normalized = normalize_base_theme_name(base_theme)
    compiled = compile_ui_theme("default", _THEME_BASE_OVERRIDES[normalized])
    return _ordered_tokens(compiled.tokens)


def normalize_theme_overrides(
    overrides: Mapping[str, object] | None,
    *,
    line: int | None = None,
    column: int | None = None,
) -> dict[str, str | int | float]:
    if not isinstance(overrides, Mapping):
        return {}
    normalized: dict[str, str | int | float] = {}
    keyed = sorted(((str(key), key) for key in overrides.keys()), key=lambda item: item[0])
    for key_text, original_key in keyed:
        if key_text not in THEME_TOKEN_SCHEMA:
            raise Namel3ssError(
                f"Unknown theme token '{key_text}'.",
                line=line,
                column=column,
            )
        normalized[key_text] = normalize_ui_theme_token_value(
            key_text,
            overrides[original_key],
            line=line,
            column=column,
        )
    return normalized


def resolve_theme_tokens(
    base_theme: str,
    overrides: Mapping[str, object] | None = None,
    *,
    line: int | None = None,
    column: int | None = None,
) -> ResolvedThemeTokens:
    normalized_theme = normalize_base_theme_name(base_theme, line=line, column=column)
    base_tokens = resolve_base_theme_tokens(normalized_theme)
    normalized_overrides = normalize_theme_overrides(overrides, line=line, column=column)
    merged = dict(base_tokens)
    for key in UI_THEME_TOKEN_ORDER:
        value = normalized_overrides.get(key)
        if value is not None:
            merged[key] = value
    return ResolvedThemeTokens(
        base_theme=normalized_theme,
        tokens=_ordered_tokens(merged),
    )


def token_schema() -> dict[str, dict[str, str]]:
    return {name: dict(THEME_TOKEN_SCHEMA[name]) for name in UI_THEME_TOKEN_ORDER}


def _ordered_tokens(tokens: Mapping[str, str | int | float]) -> dict[str, str | int | float]:
    return {name: tokens[name] for name in UI_THEME_TOKEN_ORDER}


def _raise_invalid_base_theme(value: object, *, line: int | None, column: int | None) -> None:
    allowed = ", ".join(THEME_BASE_ORDER)
    raise Namel3ssError(
        f"Unknown base_theme '{value}'. Allowed values: {allowed}.",
        line=line,
        column=column,
    )


__all__ = [
    "THEME_BASE_ORDER",
    "THEME_TOKEN_SCHEMA",
    "ResolvedThemeTokens",
    "base_theme_names",
    "default_theme_tokens",
    "is_base_theme_name",
    "normalize_base_theme_name",
    "normalize_theme_overrides",
    "resolve_base_theme_tokens",
    "resolve_theme_tokens",
    "token_schema",
]
