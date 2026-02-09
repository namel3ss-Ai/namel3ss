from __future__ import annotations

from namel3ss.ast.ui_theme import ThemeTokenOverrides as ASTThemeTokenOverrides
from namel3ss.ast.ui_theme import ThemeTokens as ASTThemeTokens
from namel3ss.ir.model.ui_theme import ThemeTokenOverrides, ThemeTokens


def lower_page_theme_tokens(tokens: ASTThemeTokens | None) -> ThemeTokens | None:
    if tokens is None:
        return None
    return ThemeTokens(
        size=tokens.size,
        radius=tokens.radius,
        density=tokens.density,
        font=tokens.font,
        color_scheme=tokens.color_scheme,
        line=tokens.line,
        column=tokens.column,
    )


def lower_theme_overrides(overrides: ASTThemeTokenOverrides | None) -> ThemeTokenOverrides | None:
    if overrides is None:
        return None
    return ThemeTokenOverrides(
        size=overrides.size,
        radius=overrides.radius,
        density=overrides.density,
        font=overrides.font,
        line=overrides.line,
        column=overrides.column,
    )


__all__ = ["lower_page_theme_tokens", "lower_theme_overrides"]
