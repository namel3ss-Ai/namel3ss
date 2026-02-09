from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


UI_THEME_TOKEN_ORDER: tuple[str, ...] = ("size", "radius", "density", "font", "color_scheme")
UI_THEME_COMPONENT_TOKENS: tuple[str, ...] = ("size", "radius", "density", "font")

UI_THEME_ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "size": ("compact", "normal", "comfortable"),
    "radius": ("none", "sm", "md", "lg", "full"),
    "density": ("tight", "regular", "airy"),
    "font": ("sm", "md", "lg"),
    "color_scheme": ("light", "dark", "system"),
}

UI_THEME_DEFAULTS: dict[str, str] = {
    "size": "normal",
    "radius": "md",
    "density": "regular",
    "font": "md",
    "color_scheme": "light",
}


def is_ui_theme_token(name: str) -> bool:
    return name in UI_THEME_ALLOWED_VALUES


def normalize_ui_theme_token_value(
    name: str,
    value: object,
    *,
    line: int | None = None,
    column: int | None = None,
) -> str:
    if name not in UI_THEME_ALLOWED_VALUES:
        allowed = ", ".join(UI_THEME_TOKEN_ORDER)
        raise Namel3ssError(
            f"Unknown token '{name}'. Allowed tokens: {allowed}.",
            line=line,
            column=column,
        )
    if not isinstance(value, str):
        raise Namel3ssError(
            f"invalid token value '{value}' for {name}; allowed values: {', '.join(UI_THEME_ALLOWED_VALUES[name])}.",
            line=line,
            column=column,
        )
    if value not in UI_THEME_ALLOWED_VALUES[name]:
        raise Namel3ssError(
            f"invalid token value '{value}' for {name}; allowed values: {', '.join(UI_THEME_ALLOWED_VALUES[name])}.",
            line=line,
            column=column,
        )
    return value


def normalize_ui_theme_token_value_optional(name: str, value: object) -> str | None:
    if name not in UI_THEME_ALLOWED_VALUES:
        return None
    if not isinstance(value, str):
        return None
    if value not in UI_THEME_ALLOWED_VALUES[name]:
        return None
    return value


__all__ = [
    "UI_THEME_ALLOWED_VALUES",
    "UI_THEME_COMPONENT_TOKENS",
    "UI_THEME_DEFAULTS",
    "UI_THEME_TOKEN_ORDER",
    "is_ui_theme_token",
    "normalize_ui_theme_token_value",
    "normalize_ui_theme_token_value_optional",
]
