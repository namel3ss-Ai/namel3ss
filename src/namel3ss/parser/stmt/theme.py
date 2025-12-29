from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_set_theme(parser) -> ast.ThemeChange:
    set_tok = parser._advance()
    theme_tok = parser._expect("THEME", "Expected 'theme' after set")
    if parser._match("IS"):
        pass
    else:
        parser._expect("TO", "Expected 'to' after theme")
    value_tok = parser._expect("STRING", "Expected theme value")
    allowed = {"light", "dark", "system"}
    if value_tok.value not in allowed:
        raise Namel3ssError("Theme must be one of: light, dark, system.", line=value_tok.line, column=value_tok.column)
    return ast.ThemeChange(value=value_tok.value, line=theme_tok.line, column=theme_tok.column)


__all__ = ["parse_set_theme"]
