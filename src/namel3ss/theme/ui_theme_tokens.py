from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.resources import package_root


UI_STYLE_THEME_DEFAULT = "default"
UI_STYLE_THEME_NAMES: tuple[str, ...] = (
    UI_STYLE_THEME_DEFAULT,
    "modern",
    "minimal",
    "corporate",
)
UI_THEME_TOKEN_ORDER: tuple[str, ...] = (
    "primary_color",
    "secondary_color",
    "background_color",
    "foreground_color",
    "font_family",
    "font_size_base",
    "font_weight",
    "spacing_scale",
    "border_radius",
    "shadow_level",
)
_COLOR_TOKENS = {
    "primary_color",
    "secondary_color",
    "background_color",
    "foreground_color",
}
_FONT_SYSTEM_NAMES = {
    "system-ui",
    "-apple-system",
    "segoe ui",
    "roboto",
    "helvetica",
    "arial",
    "sans-serif",
    "serif",
    "monospace",
}
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{6})$")
_SHADOW_BY_LEVEL = {
    0: "none",
    1: "0 2px 6px rgba(15, 23, 42, 0.08)",
    2: "0 8px 18px rgba(15, 23, 42, 0.14)",
    3: "0 14px 28px rgba(15, 23, 42, 0.20)",
}


@dataclass(frozen=True)
class CompiledUITheme:
    theme_name: str
    tokens: dict[str, str | int | float]
    css: str
    css_hash: str
    font_url: str | None


def compile_ui_theme(theme_name: str, overrides: dict[str, object] | None = None) -> CompiledUITheme:
    selected = _normalize_theme_name(theme_name)
    base_tokens = _load_theme_tokens(selected)
    merged: dict[str, str | int | float] = dict(base_tokens)
    for token_name, raw_value in sorted((overrides or {}).items()):
        merged[token_name] = normalize_ui_theme_token_value(token_name, raw_value)
    css = _build_theme_css(merged)
    hash_input = json.dumps(
        {"theme_name": selected, "tokens": _ordered_tokens(merged), "css": css},
        sort_keys=True,
        separators=(",", ":"),
    )
    css_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return CompiledUITheme(
        theme_name=selected,
        tokens=merged,
        css=css,
        css_hash=css_hash,
        font_url=build_font_url(str(merged["font_family"])),
    )


def normalize_ui_theme_token_value(
    token_name: str,
    value: object,
    *,
    line: int | None = None,
    column: int | None = None,
) -> str | int | float:
    if token_name not in UI_THEME_TOKEN_ORDER:
        _raise_unknown_token(token_name, line=line, column=column)
    if token_name in _COLOR_TOKENS:
        if isinstance(value, str) and _HEX_COLOR_RE.match(value):
            return value.upper()
        _raise_invalid_value(token_name, value, "hex color value like #007AFF", line=line, column=column)
    if token_name == "font_family":
        if isinstance(value, str) and value.strip():
            return value.strip()
        _raise_invalid_value(token_name, value, "non-empty font family string", line=line, column=column)
    if token_name == "font_size_base":
        number = _coerce_number(token_name, value, line=line, column=column)
        if number < 10 or number > 24:
            _raise_invalid_value(token_name, value, "number between 10 and 24", line=line, column=column)
        return int(number) if float(number).is_integer() else float(number)
    if token_name == "font_weight":
        number = _coerce_number(token_name, value, line=line, column=column)
        if number < 100 or number > 900:
            _raise_invalid_value(token_name, value, "number between 100 and 900", line=line, column=column)
        rounded = int(round(number / 100.0) * 100)
        return max(100, min(900, rounded))
    if token_name == "spacing_scale":
        number = _coerce_number(token_name, value, line=line, column=column)
        if number <= 0.0 or number > 3.0:
            _raise_invalid_value(token_name, value, "positive number between 0.1 and 3.0", line=line, column=column)
        return float(number)
    if token_name == "border_radius":
        number = _coerce_number(token_name, value, line=line, column=column)
        if number < 0 or number > 32:
            _raise_invalid_value(token_name, value, "number between 0 and 32", line=line, column=column)
        return int(number) if float(number).is_integer() else float(number)
    if token_name == "shadow_level":
        number = _coerce_number(token_name, value, line=line, column=column)
        if int(number) not in _SHADOW_BY_LEVEL:
            _raise_invalid_value(token_name, value, "integer 0, 1, 2, or 3", line=line, column=column)
        return int(number)
    return value if isinstance(value, (str, int, float)) else str(value)


def is_ui_style_theme_name(value: str) -> bool:
    return value in UI_STYLE_THEME_NAMES


def is_ui_theme_token_name(value: str) -> bool:
    return value in UI_THEME_TOKEN_ORDER


def build_font_url(font_family: str) -> str | None:
    first = _first_font_name(font_family)
    if not first:
        return None
    if first.lower() in _FONT_SYSTEM_NAMES:
        return None
    encoded = quote_plus(first)
    return f"https://fonts.googleapis.com/css2?family={encoded}:wght@400;500;600;700&display=swap"


def _first_font_name(font_family: str) -> str:
    first = (font_family or "").split(",", 1)[0].strip()
    return first.strip("\"'")


def _ordered_tokens(tokens: dict[str, str | int | float]) -> dict[str, str | int | float]:
    return {name: tokens[name] for name in UI_THEME_TOKEN_ORDER}


def _normalize_theme_name(theme_name: str) -> str:
    if theme_name in UI_STYLE_THEME_NAMES:
        return theme_name
    suggestion = _closest(theme_name, UI_STYLE_THEME_NAMES)
    fix = f'Did you mean "{suggestion}"?' if suggestion else "Use a supported built-in theme."
    allowed = ", ".join(UI_STYLE_THEME_NAMES)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown ui theme '{theme_name}'.",
            why=f"Allowed built-in themes: {allowed}.",
            fix=fix,
            example='ui:\n  theme is "modern"',
        )
    )


def _load_theme_tokens(theme_name: str) -> dict[str, str | int | float]:
    path = package_root() / "themes" / f"{theme_name}.json"
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Missing built-in theme file for '{theme_name}'.",
                why="Built-in themes must be packaged as deterministic JSON assets.",
                fix="Restore the missing theme JSON file.",
                example="src/namel3ss/themes/modern.json",
            )
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Theme file '{path.name}' is not valid JSON.",
                why="Theme files must be deterministic JSON objects.",
                fix="Fix JSON syntax in the theme file.",
                example='{"primary_color": "#007AFF"}',
            )
        ) from err
    if not isinstance(raw, dict):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Theme file '{path.name}' must contain a JSON object.",
                why="Built-in theme files map token names to values.",
                fix="Replace the file content with a token object.",
                example='{"primary_color": "#007AFF"}',
            )
        )
    tokens: dict[str, str | int | float] = {}
    for token_name in UI_THEME_TOKEN_ORDER:
        if token_name not in raw:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Theme '{theme_name}' is missing token '{token_name}'.",
                    why="All built-in themes must define the full token set.",
                    fix="Add the missing token to the theme JSON file.",
                    example=f'"{token_name}": "..."',
                )
            )
        tokens[token_name] = normalize_ui_theme_token_value(token_name, raw[token_name])
    return tokens


def _build_theme_css(tokens: dict[str, str | int | float]) -> str:
    lines = [
        ":root {",
        f"  --n3-primary-color: {tokens['primary_color']};",
        f"  --n3-secondary-color: {tokens['secondary_color']};",
        f"  --n3-background-color: {tokens['background_color']};",
        f"  --n3-foreground-color: {tokens['foreground_color']};",
        f"  --n3-font-family: {tokens['font_family']};",
        f"  --n3-font-size-base: {tokens['font_size_base']}px;",
        f"  --n3-font-weight: {tokens['font_weight']};",
        f"  --n3-spacing-scale: {tokens['spacing_scale']};",
        f"  --n3-border-radius: {tokens['border_radius']}px;",
        f"  --n3-shadow-elevation: {_SHADOW_BY_LEVEL[int(tokens['shadow_level'])]};",
        "}",
        "",
        "body.n3-runtime,",
        "body {",
        "  background: var(--n3-background-color);",
        "  color: var(--n3-foreground-color);",
        "  font-family: var(--n3-font-family);",
        "  font-size: var(--n3-font-size-base);",
        "  font-weight: var(--n3-font-weight);",
        "}",
        "",
        ".ui-body,",
        ".panel,",
        ".ui-element,",
        ".list-item,",
        ".trace-row,",
        ".n3-layout-header,",
        ".n3-layout-sidebar,",
        ".n3-layout-main,",
        ".n3-layout-drawer,",
        ".n3-layout-footer {",
        "  background: var(--n3-background-color);",
        "  color: var(--n3-foreground-color);",
        "  border-radius: var(--n3-border-radius);",
        "  box-shadow: var(--n3-shadow-elevation);",
        "}",
        "",
        ".btn.primary,",
        ".ui-chat-action,",
        ".ui-upload-label {",
        "  background: var(--n3-primary-color);",
        "  border-color: var(--n3-primary-color);",
        "  color: #FFFFFF;",
        "}",
        "",
        ".ui-link,",
        ".n3-chat-attachment-link,",
        ".n3-citation-chip {",
        "  color: var(--n3-primary-color);",
        "}",
        "",
        ".ui-card-title,",
        ".ui-section-title,",
        ".n3-chat-group-label {",
        "  color: var(--n3-secondary-color);",
        "}",
        "",
        ".ui-element,",
        ".panel,",
        ".n3-layout-header,",
        ".n3-layout-sidebar,",
        ".n3-layout-main,",
        ".n3-layout-drawer,",
        ".n3-layout-footer {",
        "  padding: calc(10px * var(--n3-spacing-scale));",
        "}",
        "",
        ".ui-row,",
        ".ui-column,",
        ".ui-card-group,",
        ".n3-layout-root,",
        ".n3-layout-body {",
        "  gap: calc(10px * var(--n3-spacing-scale));",
        "}",
    ]
    return "\n".join(lines).strip() + "\n"


def _coerce_number(
    token_name: str,
    value: object,
    *,
    line: int | None = None,
    column: int | None = None,
) -> float:
    if isinstance(value, bool):
        _raise_invalid_value(token_name, value, "numeric value", line=line, column=column)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            _raise_invalid_value(token_name, value, "numeric value", line=line, column=column)
    _raise_invalid_value(token_name, value, "numeric value", line=line, column=column)
    return 0.0


def _raise_unknown_token(token_name: str, *, line: int | None, column: int | None) -> None:
    suggestion = _closest(token_name, UI_THEME_TOKEN_ORDER)
    fix = f'Did you mean "{suggestion}"?' if suggestion else "Use a supported theme token."
    allowed = ", ".join(UI_THEME_TOKEN_ORDER)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown ui theme token '{token_name}'.",
            why=f"Allowed tokens: {allowed}.",
            fix=fix,
            example='ui:\n  primary_color is "#007AFF"',
        ),
        line=line,
        column=column,
    )


def _raise_invalid_value(
    token_name: str,
    value: object,
    expected: str,
    *,
    line: int | None,
    column: int | None,
) -> None:
    raise Namel3ssError(
        build_guidance_message(
            what=f"Invalid value '{value}' for ui token '{token_name}'.",
            why=f"{token_name} must be a valid {expected}.",
            fix="Use a valid token value.",
            example=f"ui:\n  {token_name} is \"...\"",
        ),
        line=line,
        column=column,
    )


def _closest(value: str, choices: tuple[str, ...]) -> str | None:
    matches = difflib.get_close_matches(value, list(choices), n=1, cutoff=0.6)
    return matches[0] if matches else None


__all__ = [
    "CompiledUITheme",
    "UI_STYLE_THEME_DEFAULT",
    "UI_STYLE_THEME_NAMES",
    "UI_THEME_TOKEN_ORDER",
    "build_font_url",
    "compile_ui_theme",
    "is_ui_style_theme_name",
    "is_ui_theme_token_name",
    "normalize_ui_theme_token_value",
]
