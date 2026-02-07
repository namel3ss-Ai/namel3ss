from __future__ import annotations

from collections import OrderedDict

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.theme.colors import (
    TONAL_STEPS,
    best_on_color,
    dedupe_names,
    derive_tonal_scale,
    ensure_contrast_pairs,
    harmonize_color,
    parse_color,
    resolve_token_value,
    rgb_to_hex,
    sorted_token_items,
)
from namel3ss.theme.model import ResolvedTheme, ThemeDefinition
from namel3ss.ui.presets import resolve_ui_preset


LEGACY_THEME_TOKEN_DEFAULTS: dict[str, str] = {
    "surface": "default",
    "text": "default",
    "muted": "muted",
    "border": "default",
    "accent": "primary",
}

_BASE_PALETTE: dict[str, str] = {
    "brand_primary": "#2563EB",
    "brand_secondary": "#475569",
    "brand_accent": "#0EA5E9",
    "brand_neutral": "#64748B",
    "functional_error": "#DC2626",
    "functional_success": "#16A34A",
    "functional_warning": "#D97706",
}

_PRESET_PALETTES: dict[str, dict[str, str]] = {
    "clarity": {
        "brand_primary": "#2563EB",
        "brand_secondary": "#0EA5E9",
        "brand_neutral": "#64748B",
    },
    "calm": {
        "brand_primary": "#0D9488",
        "brand_secondary": "#14B8A6",
        "brand_neutral": "#78716C",
    },
    "focus": {
        "brand_primary": "#4F46E5",
        "brand_secondary": "#312E81",
        "brand_neutral": "#334155",
    },
    "signal": {
        "brand_primary": "#22D3EE",
        "brand_secondary": "#0891B2",
        "brand_neutral": "#475569",
    },
}


def resolve_theme_definition(
    definition: ThemeDefinition | None,
    *,
    capabilities: tuple[str, ...],
) -> ResolvedTheme:
    if definition is None:
        return ResolvedTheme(definition=ThemeDefinition(), tokens={}, ui_overrides={}, responsive_tokens={})
    normalized = definition
    _validate_capability_gate(normalized, capabilities)
    if normalized.harmonize and not normalized.preset:
        raise Namel3ssError("harmonize requires a preset in theme block.", line=normalized.line, column=normalized.column)

    ui_overrides = _build_ui_overrides(normalized)
    has_token_system = bool(normalized.preset or normalized.brand_palette or normalized.tokens or normalized.harmonize)
    if not has_token_system:
        return ResolvedTheme(
            definition=normalized,
            tokens={},
            ui_overrides=ui_overrides,
            responsive_tokens=_sorted_responsive_tokens(normalized.responsive_tokens),
        )
    palette = _resolve_base_palette(normalized)
    tokens = _derive_tokens(palette)
    tokens = _apply_semantic_aliases(tokens, palette)
    tokens = _apply_token_overrides(tokens, normalized.tokens, line=normalized.line, column=normalized.column)
    ensure_contrast_pairs(tokens, allow_low_contrast=normalized.allow_low_contrast, line=normalized.line, column=normalized.column)
    for key, value in LEGACY_THEME_TOKEN_DEFAULTS.items():
        tokens.setdefault(key, value)
    return ResolvedTheme(
        definition=normalized,
        tokens=sorted_token_items(tokens),
        ui_overrides=ui_overrides,
        responsive_tokens=_sorted_responsive_tokens(normalized.responsive_tokens),
    )


def resolve_token_registry(
    theme_resolution: ResolvedTheme,
    *,
    legacy_tokens: dict[str, str] | None,
) -> dict[str, str]:
    merged = dict(theme_resolution.tokens)
    for name, value in (legacy_tokens or {}).items():
        merged[name] = value
    return sorted_token_items(merged)


def _build_ui_overrides(definition: ThemeDefinition) -> dict[str, str]:
    settings = OrderedDict()
    if definition.preset:
        preset_settings = resolve_ui_preset(definition.preset, line=definition.line, column=definition.column)
        for key, value in preset_settings.items():
            settings[key] = value
    if definition.density:
        settings["density"] = definition.density
    if definition.motion:
        settings["motion"] = definition.motion
    if definition.shape:
        settings["shape"] = definition.shape
    if definition.surface:
        settings["surface"] = definition.surface
    return dict(settings)


def _resolve_base_palette(definition: ThemeDefinition) -> dict[str, str]:
    palette: dict[str, str] = dict(_BASE_PALETTE)
    if definition.preset:
        palette.update(_PRESET_PALETTES.get(definition.preset, {}))
    palette.update(definition.brand_palette)
    if definition.harmonize and definition.preset:
        harmonize_target = _PRESET_PALETTES.get(definition.preset, {}).get("brand_primary")
        if harmonize_target:
            target_rgb = parse_color(harmonize_target, line=definition.line, column=definition.column)
            harmonized: dict[str, str] = {}
            for name, color in palette.items():
                rgb = parse_color(color, line=definition.line, column=definition.column)
                harmonized[name] = rgb_to_hex(harmonize_color(rgb, target_rgb))
            palette = harmonized
    return palette


def _derive_tokens(palette: dict[str, str]) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for name in dedupe_names(palette.keys()):
        base = palette[name]
        tones = derive_tonal_scale(parse_color(base))
        for step in TONAL_STEPS:
            tokens[f"color.{name}.{step}"] = tones[step]
        tokens[f"color.{name}"] = tones[500]
        tokens[f"color.{name}.light"] = tones[200]
        tokens[f"color.{name}.dark"] = tones[700]
    return tokens


def _apply_semantic_aliases(tokens: dict[str, str], palette: dict[str, str]) -> dict[str, str]:
    names = list(dedupe_names(palette.keys()))
    primary = "brand_primary" if "brand_primary" in palette else (names[0] if names else "brand_primary")
    secondary = "brand_secondary" if "brand_secondary" in palette else (names[1] if len(names) > 1 else primary)
    accent = "brand_accent" if "brand_accent" in palette else secondary
    neutral = "brand_neutral" if "brand_neutral" in palette else (names[2] if len(names) > 2 else primary)
    error = _pick_palette_name(palette, ("functional_error", "brand_error", "error"), fallback=primary)
    success = _pick_palette_name(palette, ("functional_success", "brand_success", "success"), fallback=primary)
    warning = _pick_palette_name(palette, ("functional_warning", "brand_warning", "warning"), fallback=primary)

    aliases = {
        "color.primary": f"color.{primary}.500",
        "color.secondary": f"color.{secondary}.500",
        "color.accent": f"color.{accent}.500",
        "color.neutral": f"color.{neutral}.500",
        "color.error": f"color.{error}.500",
        "color.success": f"color.{success}.500",
        "color.warning": f"color.{warning}.500",
        "color.background": f"color.{neutral}.50",
        "color.surface": f"color.{neutral}.100",
    }
    for alias, target in aliases.items():
        tokens[alias] = tokens.get(target, tokens.get(f"color.{primary}.500", "#2563EB"))
    tokens.setdefault("color.primary.light", tokens.get(f"color.{primary}.200", tokens["color.primary"]))
    tokens.setdefault("color.primary.dark", tokens.get(f"color.{primary}.700", tokens["color.primary"]))
    tokens.setdefault("color.secondary.light", tokens.get(f"color.{secondary}.200", tokens["color.secondary"]))
    tokens.setdefault("color.secondary.dark", tokens.get(f"color.{secondary}.700", tokens["color.secondary"]))
    tokens["color.on_primary"] = best_on_color(tokens["color.primary"])
    tokens["color.on_secondary"] = best_on_color(tokens["color.secondary"])
    tokens["color.on_error"] = best_on_color(tokens["color.error"])
    tokens["color.on_success"] = best_on_color(tokens["color.success"])
    tokens["color.on_warning"] = best_on_color(tokens["color.warning"])
    tokens["color.on_surface"] = best_on_color(tokens["color.surface"])
    tokens["color.on_background"] = best_on_color(tokens["color.background"])
    return tokens


def _apply_token_overrides(
    tokens: dict[str, str],
    overrides: dict[str, str],
    *,
    line: int | None,
    column: int | None,
) -> dict[str, str]:
    if not overrides:
        return tokens
    resolved = dict(tokens)
    for name in dedupe_names(overrides.keys()):
        resolved[name] = resolve_token_value(overrides[name], known=resolved, line=line, column=column)
    return resolved


def _pick_palette_name(palette: dict[str, str], candidates: tuple[str, ...], *, fallback: str) -> str:
    for name in candidates:
        if name in palette:
            return name
    for name in palette.keys():
        lower = name.lower()
        for candidate in candidates:
            if candidate in lower:
                return name
    return fallback


def _validate_capability_gate(definition: ThemeDefinition, capabilities: tuple[str, ...]) -> None:
    normalized_caps = {normalize_builtin_capability(item) for item in capabilities}
    has_custom_theme = (
        bool(definition.brand_palette)
        or bool(definition.tokens)
        or bool(definition.responsive_tokens)
        or bool(definition.harmonize)
    )
    if not has_custom_theme:
        return
    if "custom_theme" in normalized_caps:
        return
    raise Namel3ssError(
        "Missing capabilities: custom_theme. Add custom_theme to use brand_palette, tokens, responsive token scales, or harmonize.",
        line=definition.line,
        column=definition.column,
    )


def _sorted_responsive_tokens(tokens: dict[str, tuple[int, ...]]) -> dict[str, tuple[int, ...]]:
    if not tokens:
        return {}
    return {key: tuple(tokens[key]) for key in sorted(tokens)}


__all__ = [
    "LEGACY_THEME_TOKEN_DEFAULTS",
    "ResolvedTheme",
    "ThemeDefinition",
    "resolve_theme_definition",
    "resolve_token_registry",
]
