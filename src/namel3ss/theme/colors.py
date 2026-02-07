from __future__ import annotations

import colorsys
import re
from typing import Iterable

from namel3ss.errors.base import Namel3ssError


RGB = tuple[int, int, int]
TONAL_STEPS: tuple[int, ...] = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)

_HEX_SHORT = re.compile(r"^#([0-9a-fA-F]{3})$")
_HEX_LONG = re.compile(r"^#([0-9a-fA-F]{6})$")
_TOKEN_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*$")

_CSS_COLORS: dict[str, str] = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "orange": "#ffa500",
    "purple": "#800080",
    "pink": "#ffc0cb",
    "teal": "#008080",
    "cyan": "#00ffff",
    "gray": "#808080",
    "grey": "#808080",
    "brown": "#a52a2a",
    "indigo": "#4b0082",
    "lime": "#00ff00",
    "navy": "#000080",
    "maroon": "#800000",
    "olive": "#808000",
    "silver": "#c0c0c0",
}


def is_token_name(value: str) -> bool:
    return bool(_TOKEN_NAME.match(value))


def parse_color(value: str, *, line: int | None = None, column: int | None = None) -> RGB:
    text = value.strip()
    if text.lower().startswith("hex:"):
        text = text[4:].strip()
    short = _HEX_SHORT.match(text)
    if short:
        chunk = short.group(1)
        return tuple(int(ch * 2, 16) for ch in chunk)  # type: ignore[return-value]
    long = _HEX_LONG.match(text)
    if long:
        chunk = long.group(1)
        return int(chunk[0:2], 16), int(chunk[2:4], 16), int(chunk[4:6], 16)
    css = _CSS_COLORS.get(text.lower())
    if css:
        return parse_color(css, line=line, column=column)
    raise Namel3ssError("Invalid color value. Use #RRGGBB, #RGB, or a supported CSS color name.", line=line, column=column)


def rgb_to_hex(rgb: RGB) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def derive_tonal_scale(base: RGB) -> dict[int, str]:
    derived: dict[int, str] = {}
    for step in TONAL_STEPS:
        if step == 500:
            color = base
        elif step < 500:
            ratio = (500 - step) / 500.0
            color = _blend(base, (255, 255, 255), ratio)
        else:
            ratio = (step - 500) / 500.0
            color = _blend(base, (0, 0, 0), ratio)
        derived[step] = rgb_to_hex(color)
    return derived


def harmonize_color(color: RGB, target: RGB) -> RGB:
    r, g, b = [chan / 255.0 for chan in color]
    tr, tg, tb = [chan / 255.0 for chan in target]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    th, tl, ts = colorsys.rgb_to_hls(tr, tg, tb)
    # Deterministic 80/20 blend toward target hue/saturation.
    blended_h = (h * 0.8 + th * 0.2) % 1.0
    blended_s = _clamp((s * 0.8 + ts * 0.2), 0.0, 1.0)
    out_r, out_g, out_b = colorsys.hls_to_rgb(blended_h, l, blended_s)
    return int(round(out_r * 255)), int(round(out_g * 255)), int(round(out_b * 255))


def ensure_contrast_pairs(
    token_colors: dict[str, str],
    *,
    allow_low_contrast: bool,
    line: int | None = None,
    column: int | None = None,
) -> None:
    if allow_low_contrast:
        return
    for left, right in _CONTRAST_PAIRS:
        left_color = token_colors.get(left)
        right_color = token_colors.get(right)
        if not left_color or not right_color:
            continue
        ratio = contrast_ratio(parse_color(left_color, line=line, column=column), parse_color(right_color, line=line, column=column))
        if ratio < 4.5:
            raise Namel3ssError(
                f'Theme contrast check failed for "{left}" vs "{right}" (ratio {ratio:.2f}, required 4.50).',
                line=line,
                column=column,
            )


def contrast_ratio(left: RGB, right: RGB) -> float:
    l1 = _relative_luminance(left)
    l2 = _relative_luminance(right)
    bright = max(l1, l2)
    dark = min(l1, l2)
    return (bright + 0.05) / (dark + 0.05)


def best_on_color(background: str) -> str:
    bg = parse_color(background)
    white = contrast_ratio(bg, (255, 255, 255))
    black = contrast_ratio(bg, (0, 0, 0))
    return "#FFFFFF" if white >= black else "#000000"


def sorted_token_items(items: dict[str, str]) -> dict[str, str]:
    return {key: items[key] for key in sorted(items)}


def normalize_token_reference(value: str) -> str:
    return value.strip()


def validate_token_name(name: str, *, line: int | None = None, column: int | None = None) -> None:
    if is_token_name(name):
        return
    raise Namel3ssError(
        f'Invalid token name "{name}". Use dot-separated identifiers like color.primary.500.',
        line=line,
        column=column,
    )


def validate_palette_name(name: str, *, line: int | None = None, column: int | None = None) -> None:
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        return
    raise Namel3ssError(
        f'Invalid brand palette key "{name}". Use letters, numbers, and underscores only.',
        line=line,
        column=column,
    )


def resolve_token_value(
    value: str,
    *,
    known: dict[str, str],
    line: int | None = None,
    column: int | None = None,
) -> str:
    normalized = normalize_token_reference(value)
    if normalized in known:
        return known[normalized]
    try:
        color = parse_color(normalized, line=line, column=column)
        return rgb_to_hex(color)
    except Namel3ssError:
        pass
    raise Namel3ssError(
        f'Unknown token or color reference "{value}".',
        line=line,
        column=column,
    )


def dedupe_names(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return tuple(ordered)


_CONTRAST_PAIRS: tuple[tuple[str, str], ...] = (
    ("color.primary", "color.on_primary"),
    ("color.secondary", "color.on_secondary"),
    ("color.error", "color.on_error"),
    ("color.success", "color.on_success"),
    ("color.warning", "color.on_warning"),
    ("color.surface", "color.on_surface"),
    ("color.background", "color.on_background"),
)


def _blend(base: RGB, overlay: RGB, ratio: float) -> RGB:
    ratio = _clamp(ratio, 0.0, 1.0)
    return (
        int(round(base[0] * (1.0 - ratio) + overlay[0] * ratio)),
        int(round(base[1] * (1.0 - ratio) + overlay[1] * ratio)),
        int(round(base[2] * (1.0 - ratio) + overlay[2] * ratio)),
    )


def _relative_luminance(rgb: RGB) -> float:
    r, g, b = [_linearize(channel / 255.0) for channel in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _linearize(value: float) -> float:
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


__all__ = [
    "TONAL_STEPS",
    "best_on_color",
    "contrast_ratio",
    "dedupe_names",
    "derive_tonal_scale",
    "ensure_contrast_pairs",
    "harmonize_color",
    "is_token_name",
    "normalize_token_reference",
    "parse_color",
    "resolve_token_value",
    "rgb_to_hex",
    "sorted_token_items",
    "validate_palette_name",
    "validate_token_name",
]

