from __future__ import annotations

from dataclasses import dataclass

from namel3ss.theme.ui_theme_tokens import compile_ui_theme
from namel3ss.ui.theme.theme_config import ThemeConfig, theme_config_from_program
from namel3ss.ui.theme.theme_tokens import resolve_theme_tokens, token_schema


@dataclass(frozen=True)
class LoadedThemeBundle:
    base_theme: str
    tokens: dict[str, str | int | float]
    css: str
    css_hash: str
    font_url: str | None
    token_schema: dict[str, dict[str, str]]
    config: dict[str, object]


def load_theme_bundle(config: ThemeConfig) -> LoadedThemeBundle:
    resolved = resolve_theme_tokens(config.base_theme, config.overrides)
    compiled = compile_ui_theme("default", resolved.tokens)
    return LoadedThemeBundle(
        base_theme=resolved.base_theme,
        tokens=dict(compiled.tokens),
        css=compiled.css,
        css_hash=compiled.css_hash,
        font_url=compiled.font_url,
        token_schema=token_schema(),
        config={
            "base_theme": resolved.base_theme,
            "overrides": dict(config.overrides),
        },
    )


def load_theme_bundle_from_program(program: object) -> LoadedThemeBundle:
    config = theme_config_from_program(program)
    return load_theme_bundle(config)


__all__ = [
    "LoadedThemeBundle",
    "load_theme_bundle",
    "load_theme_bundle_from_program",
]
