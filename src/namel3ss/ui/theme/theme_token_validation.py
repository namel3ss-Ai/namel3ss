from __future__ import annotations

from collections.abc import Mapping

from namel3ss.theme.ui_theme_tokens import UI_THEME_TOKEN_ORDER

_SPACING_KEYS = ("xs", "s", "m", "l", "xl")


def build_theme_token_contract(tokens: Mapping[str, object], *, mode: str) -> dict[str, object]:
    normalized = _normalize_tokens(tokens)
    spacing_scale = _positive_number(normalized.get("spacing_scale"), fallback=1.0)
    base_spacing = 8.0 * spacing_scale
    border_radius = _non_negative_number(normalized.get("border_radius"), fallback=10.0)
    contract = {
        "mode": _normalize_mode(mode),
        "colors": {
            "surface": str(normalized.get("background_color") or "#FFFFFF"),
            "text": str(normalized.get("foreground_color") or "#111827"),
            "muted": str(normalized.get("secondary_color") or "#6B7280"),
            "border": str(normalized.get("secondary_color") or "#D1D5DB"),
            "accent": str(normalized.get("primary_color") or "#2563EB"),
        },
        "spacing": {
            "xs": round(base_spacing * 0.5, 2),
            "s": round(base_spacing * 0.75, 2),
            "m": round(base_spacing, 2),
            "l": round(base_spacing * 1.5, 2),
            "xl": round(base_spacing * 2.0, 2),
        },
        "radii": {
            "s": round(max(0.0, border_radius * 0.5), 2),
            "m": round(max(0.0, border_radius), 2),
            "l": round(max(0.0, border_radius * 1.5), 2),
        },
        "typography": {
            "font_family": str(normalized.get("font_family") or "system-ui"),
            "font_size_base": round(_positive_number(normalized.get("font_size_base"), fallback=14.0), 2),
            "font_weight": int(_positive_number(normalized.get("font_weight"), fallback=500)),
        },
    }
    validate_theme_token_contract(contract)
    return contract


def validate_theme_token_contract(contract: Mapping[str, object]) -> None:
    if not isinstance(contract, Mapping):
        raise ValueError("Theme token contract must be an object.")
    if contract.get("mode") not in {"light", "dark"}:
        raise ValueError("Theme token contract mode must be 'light' or 'dark'.")
    colors = contract.get("colors")
    if not isinstance(colors, Mapping):
        raise ValueError("Theme token contract colors must be an object.")
    for key in ("surface", "text", "muted", "border", "accent"):
        if not isinstance(colors.get(key), str) or not str(colors.get(key)).strip():
            raise ValueError(f"Theme token contract colors.{key} must be non-empty text.")
    spacing = contract.get("spacing")
    if not isinstance(spacing, Mapping):
        raise ValueError("Theme token contract spacing must be an object.")
    for key in _SPACING_KEYS:
        value = spacing.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) <= 0:
            raise ValueError(f"Theme token contract spacing.{key} must be a positive number.")
    radii = contract.get("radii")
    if not isinstance(radii, Mapping):
        raise ValueError("Theme token contract radii must be an object.")
    for key in ("s", "m", "l"):
        value = radii.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) < 0:
            raise ValueError(f"Theme token contract radii.{key} must be a non-negative number.")
    typography = contract.get("typography")
    if not isinstance(typography, Mapping):
        raise ValueError("Theme token contract typography must be an object.")
    if not isinstance(typography.get("font_family"), str) or not str(typography.get("font_family")).strip():
        raise ValueError("Theme token contract typography.font_family must be non-empty text.")
    if not isinstance(typography.get("font_size_base"), (int, float)) or isinstance(typography.get("font_size_base"), bool):
        raise ValueError("Theme token contract typography.font_size_base must be numeric.")
    if not isinstance(typography.get("font_weight"), int) or isinstance(typography.get("font_weight"), bool):
        raise ValueError("Theme token contract typography.font_weight must be integer.")


def _normalize_tokens(tokens: Mapping[str, object]) -> dict[str, object]:
    return {
        key: tokens.get(key)
        for key in UI_THEME_TOKEN_ORDER
    }


def _normalize_mode(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"dark", "black", "midnight", "terminal"}:
        return "dark"
    return "light"


def _positive_number(value: object, *, fallback: float) -> float:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else fallback
    return fallback


def _non_negative_number(value: object, *, fallback: float) -> float:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number >= 0 else fallback
    return fallback


__all__ = ["build_theme_token_contract", "validate_theme_token_contract"]
