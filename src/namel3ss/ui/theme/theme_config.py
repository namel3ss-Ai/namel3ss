from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.theme.ui_theme_tokens import UI_THEME_TOKEN_ORDER
from namel3ss.ui.theme.theme_tokens import (
    normalize_base_theme_name,
    normalize_theme_overrides,
    resolve_base_theme_tokens,
)


@dataclass(frozen=True)
class ThemeConfig:
    base_theme: str = "default"
    overrides: dict[str, str | int | float] = field(default_factory=dict)


def parse_theme_config(
    raw: Mapping[str, object] | None,
    *,
    line: int | None = None,
    column: int | None = None,
) -> ThemeConfig:
    if raw is None:
        return ThemeConfig()
    if not isinstance(raw, Mapping):
        raise Namel3ssError("Theme configuration must be a mapping.", line=line, column=column)

    base_theme = normalize_base_theme_name(raw.get("base_theme", "default"), line=line, column=column)
    overrides_raw = raw.get("overrides")
    if overrides_raw is None:
        overrides: dict[str, str | int | float] = {}
    elif isinstance(overrides_raw, Mapping):
        overrides = normalize_theme_overrides(overrides_raw, line=line, column=column)
    else:
        raise Namel3ssError("theme.overrides must be a mapping.", line=line, column=column)

    return ThemeConfig(base_theme=base_theme, overrides=overrides)


def theme_config_from_program(program: object) -> ThemeConfig:
    raw_config = getattr(program, "ui_theme_config", None)
    if isinstance(raw_config, Mapping):
        return parse_theme_config(raw_config)

    base_theme = _derive_base_theme_from_program(program)
    base_tokens = resolve_base_theme_tokens(base_theme)
    visual_tokens = getattr(program, "ui_visual_theme_tokens", None)
    overrides: dict[str, str | int | float] = {}
    if isinstance(visual_tokens, Mapping):
        for key in UI_THEME_TOKEN_ORDER:
            value = visual_tokens.get(key)
            if value is None:
                continue
            if base_tokens.get(key) != value:
                overrides[key] = value

    return ThemeConfig(base_theme=base_theme, overrides=overrides)


def serialize_theme_config(config: ThemeConfig) -> dict[str, object]:
    overrides = {key: config.overrides[key] for key in UI_THEME_TOKEN_ORDER if key in config.overrides}
    return {
        "base_theme": config.base_theme,
        "overrides": overrides,
    }


def _derive_base_theme_from_program(program: object) -> str:
    explicit = getattr(program, "ui_theme_base", None)
    if isinstance(explicit, str) and explicit:
        return normalize_base_theme_name(explicit)

    runtime_theme = str(getattr(program, "theme", "light") or "light").strip().lower()
    if runtime_theme in {"dark", "black", "midnight", "terminal"}:
        return "dark"
    if runtime_theme in {"white", "paper"}:
        return "high_contrast"
    return "default"


__all__ = [
    "ThemeConfig",
    "parse_theme_config",
    "serialize_theme_config",
    "theme_config_from_program",
]
