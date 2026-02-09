from __future__ import annotations

from namel3ss.ast.ui_theme import ThemeTokenOverrides
from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.theme_tokens import (
    UI_THEME_COMPONENT_TOKENS,
    normalize_ui_theme_token_value,
)


def parse_theme_override_line(parser) -> tuple[str | None, ThemeTokenOverrides | None]:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value not in UI_THEME_COMPONENT_TOKENS:
        return None, None
    name = str(tok.value)
    parser._advance()
    if parser._match("COLON"):
        pass
    else:
        parser._expect("IS", f"Expected 'is' after {name}")
    value_tok = parser._current()
    if value_tok.type not in {"STRING", "IDENT"}:
        raise Namel3ssError(
            f"Expected {name} token value.",
            line=value_tok.line,
            column=value_tok.column,
        )
    parser._advance()
    value = normalize_ui_theme_token_value(name, str(value_tok.value), line=value_tok.line, column=value_tok.column)
    overrides = ThemeTokenOverrides(line=tok.line, column=tok.column)
    setattr(overrides, name, value)
    return name, overrides


def apply_theme_override(
    overrides: ThemeTokenOverrides | None,
    new_override: ThemeTokenOverrides,
    *,
    token_name: str,
    line: int | None,
    column: int | None,
) -> ThemeTokenOverrides:
    if overrides is None:
        return new_override
    current = getattr(overrides, token_name, None)
    if current is not None:
        raise Namel3ssError(f"duplicate definition for {token_name}.", line=line, column=column)
    setattr(overrides, token_name, getattr(new_override, token_name, None))
    return overrides


__all__ = ["apply_theme_override", "parse_theme_override_line"]
