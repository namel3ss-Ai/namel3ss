from __future__ import annotations

from namel3ss.ui.theme_tokens import (
    UI_THEME_DEFAULTS,
    UI_THEME_TOKEN_ORDER,
    normalize_ui_theme_token_value_optional,
)


def theme_settings_from_state(state: dict | None) -> dict[str, str]:
    if not isinstance(state, dict):
        return {}
    ui = state.get("ui")
    if not isinstance(ui, dict):
        return {}
    settings = ui.get("settings")
    if not isinstance(settings, dict):
        return {}
    normalized: dict[str, str] = {}
    for key in UI_THEME_TOKEN_ORDER:
        value = normalize_ui_theme_token_value_optional(key, settings.get(key))
        if value is not None:
            normalized[key] = value
    return normalized


def merge_theme_tokens(*overrides: dict[str, str]) -> dict[str, str]:
    merged = {key: UI_THEME_DEFAULTS[key] for key in UI_THEME_TOKEN_ORDER}
    for override in overrides:
        for key in UI_THEME_TOKEN_ORDER:
            value = override.get(key)
            if value is not None:
                merged[key] = value
    return merged


__all__ = ["merge_theme_tokens", "theme_settings_from_state"]
