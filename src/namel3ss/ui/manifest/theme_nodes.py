from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.runtime.theme_state import merge_theme_tokens, theme_settings_from_state
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.elements.base import _base_element
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.theme_tokens import (
    UI_THEME_ALLOWED_VALUES,
    UI_THEME_COMPONENT_TOKENS,
    UI_THEME_DEFAULTS,
    UI_THEME_TOKEN_ORDER,
)


def resolve_runtime_theme_settings(state_ctx: StateContext) -> dict[str, str]:
    return theme_settings_from_state(state_ctx.state_snapshot())


def resolve_page_theme_tokens(page: ir.Page, runtime_settings: dict[str, str]) -> dict[str, str]:
    page_tokens: dict[str, str] = {}
    tokens = getattr(page, "theme_tokens", None)
    if tokens is not None:
        for key in UI_THEME_TOKEN_ORDER:
            value = getattr(tokens, key, None)
            if value is not None:
                page_tokens[key] = value
    merged = merge_theme_tokens(page_tokens, runtime_settings)
    overrides = getattr(page, "ui_theme_overrides", None)
    if overrides is not None:
        for key in UI_THEME_TOKEN_ORDER:
            value = getattr(overrides, key, None)
            if value is not None:
                merged[key] = value
    return merged


def apply_theme_overrides(element: dict, item: ir.PageItem, base_tokens: dict[str, str] | None) -> dict:
    if not isinstance(element, dict) or not isinstance(base_tokens, dict):
        return element
    overrides = getattr(item, "theme_overrides", None)
    for key in UI_THEME_COMPONENT_TOKENS:
        value = base_tokens.get(key)
        if overrides is not None:
            override_value = getattr(overrides, key, None)
            if override_value is not None:
                value = override_value
        if value is not None:
            element[key] = value
    return element


def build_theme_settings_page(
    item: ir.ThemeSettingsPageItem,
    *,
    page_name: str,
    page_slug: str,
    path: list[int],
    state_ctx: StateContext,
) -> tuple[dict, dict]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "theme_settings", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    current = getattr(state_ctx, "ui_theme", None)
    if not isinstance(current, dict):
        current = dict(UI_THEME_DEFAULTS)
    ordered_current = {key: current.get(key, UI_THEME_DEFAULTS[key]) for key in UI_THEME_TOKEN_ORDER}
    options = {key: list(UI_THEME_ALLOWED_VALUES[key]) for key in UI_THEME_TOKEN_ORDER}
    action_id = f"{element_id}.update"
    element = {
        "type": "theme.settings_page",
        "id": action_id,
        "action_id": action_id,
        "current": ordered_current,
        "options": options,
        **base,
    }
    action = {
        "id": action_id,
        "type": "theme_settings_update",
    }
    return _attach_origin(element, item), {action_id: action}


__all__ = [
    "apply_theme_overrides",
    "build_theme_settings_page",
    "resolve_page_theme_tokens",
    "resolve_runtime_theme_settings",
]
