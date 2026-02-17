from __future__ import annotations

import re

from namel3ss.errors.base import Namel3ssError


COMPONENT_VARIANTS: dict[str, tuple[str, ...]] = {
    "button": ("primary", "secondary", "success", "danger", "plain"),
    "card": ("default", "elevated", "outlined"),
}

DEFAULT_VARIANTS: dict[str, str] = {
    "button": "primary",
    "card": "default",
}

COMPONENT_STYLE_HOOKS: dict[str, tuple[str, ...]] = {
    "button": ("background", "border", "text"),
    "card": ("background", "border", "text", "shadow", "radius"),
}

_TOKEN_REF = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*$")


def default_variant(component: str) -> str | None:
    return DEFAULT_VARIANTS.get(component)


def normalize_variant(
    component: str,
    value: str | None,
    *,
    line: int | None,
    column: int | None,
) -> str | None:
    if value is None:
        return None
    allowed = COMPONENT_VARIANTS.get(component)
    if not allowed:
        return None
    normalized = value.strip().lower()
    if normalized in allowed:
        return normalized
    raise Namel3ssError(
        f'Unknown variant "{value}" for {component}. Allowed: {", ".join(allowed)}.',
        line=line,
        column=column,
    )


def normalize_style_hooks(
    component: str,
    hooks: dict[str, str] | None,
    *,
    line: int | None,
    column: int | None,
) -> dict[str, str] | None:
    if not hooks:
        return None
    allowed = COMPONENT_STYLE_HOOKS.get(component)
    if not allowed:
        raise Namel3ssError(
            f"style_hooks are not supported for {component}.",
            line=line,
            column=column,
        )
    normalized: dict[str, str] = {}
    for key in hooks:
        name = key.strip().lower()
        if name not in allowed:
            raise Namel3ssError(
                f'Unknown style hook "{key}" for {component}. Allowed: {", ".join(allowed)}.',
                line=line,
                column=column,
            )
        token_ref = hooks[key].strip()
        if not _TOKEN_REF.match(token_ref):
            raise Namel3ssError(
                f'Style hook "{key}" must reference a token name (for example color.primary).',
                line=line,
                column=column,
            )
        normalized[name] = token_ref
    return {key: normalized[key] for key in sorted(normalized)}


def variant_token_defaults(component: str, variant: str | None) -> dict[str, str]:
    key = variant or default_variant(component) or ""
    if component == "button":
        mapping = {
            "primary": {"background": "color.primary", "text": "color.on_primary", "border": "color.primary.dark"},
            "secondary": {"background": "color.secondary", "text": "color.on_secondary", "border": "color.secondary.dark"},
            "success": {"background": "color.success", "text": "color.on_success", "border": "color.success"},
            "danger": {"background": "color.error", "text": "color.on_error", "border": "color.error"},
            "plain": {"background": "color.background", "text": "color.on_background", "border": "color.background"},
        }
        return dict(mapping.get(key, mapping["primary"]))
    if component == "card":
        mapping = {
            "default": {"background": "color.surface", "text": "color.on_surface", "border": "color.neutral"},
            "elevated": {"background": "color.surface", "text": "color.on_surface", "shadow": "color.neutral"},
            "outlined": {"background": "color.background", "text": "color.on_background", "border": "color.neutral"},
        }
        return dict(mapping.get(key, mapping["default"]))
    return {}


def resolve_component_style(
    component: str,
    *,
    variant: str | None,
    style_hooks: dict[str, str] | None,
    token_registry: dict[str, str],
) -> dict[str, object] | None:
    if component not in COMPONENT_VARIANTS:
        return None
    selected_variant = variant or default_variant(component)
    base = variant_token_defaults(component, selected_variant)
    if style_hooks:
        base.update(style_hooks)
    resolved_hooks: dict[str, str] = {}
    for hook_name, token_name in base.items():
        token_value = token_registry.get(token_name)
        if token_value is None:
            continue
        resolved_hooks[hook_name] = token_value
    payload: dict[str, object] = {"variant": selected_variant}
    if base:
        payload["tokens"] = base
    if resolved_hooks:
        payload["resolved"] = resolved_hooks
    return payload


__all__ = [
    "COMPONENT_STYLE_HOOKS",
    "COMPONENT_VARIANTS",
    "DEFAULT_VARIANTS",
    "default_variant",
    "normalize_style_hooks",
    "normalize_variant",
    "resolve_component_style",
    "variant_token_defaults",
]
