from __future__ import annotations

from namel3ss.ast.ui_theme import ThemeTokens
from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.theme_tokens import (
    UI_THEME_ALLOWED_VALUES,
    UI_THEME_TOKEN_ORDER,
    normalize_ui_theme_token_value,
)


def parse_page_theme_tokens_inline(parser) -> ThemeTokens:
    tokens, line, column = _parse_theme_tokens(parser, stop_on_non_token=True, allow_color_scheme=True)
    if not tokens:
        tok = parser._current()
        raise Namel3ssError("tokens block requires at least one token.", line=tok.line, column=tok.column)
    return _build_tokens(tokens, line, column)


def parse_page_theme_tokens_block(parser) -> ThemeTokens:
    parser._expect("IDENT", "Expected tokens block")
    parser._expect("COLON", "Expected ':' after tokens")
    parser._expect("NEWLINE", "Expected newline after tokens")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("tokens block has no entries", line=tok.line, column=tok.column)
    tokens, line, column = _parse_theme_tokens(parser, stop_on_non_token=False, allow_color_scheme=True)
    parser._expect("DEDENT", "Expected end of tokens block")
    if not tokens:
        raise Namel3ssError("tokens block requires at least one token.", line=line, column=column)
    return _build_tokens(tokens, line, column)


def _build_tokens(tokens: dict[str, str], line: int | None, column: int | None) -> ThemeTokens:
    return ThemeTokens(
        size=tokens.get("size"),
        radius=tokens.get("radius"),
        density=tokens.get("density"),
        font=tokens.get("font"),
        color_scheme=tokens.get("color_scheme"),
        line=line,
        column=column,
    )


def _parse_theme_tokens(
    parser,
    *,
    stop_on_non_token: bool,
    allow_color_scheme: bool,
) -> tuple[dict[str, str], int | None, int | None]:
    tokens: dict[str, str] = {}
    line: int | None = None
    column: int | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT" or tok.value not in UI_THEME_ALLOWED_VALUES:
            if stop_on_non_token:
                break
            raise Namel3ssError(
                f"Unknown token '{tok.value}'. Allowed tokens: {', '.join(UI_THEME_TOKEN_ORDER)}.",
                line=tok.line,
                column=tok.column,
            )
        name = str(tok.value)
        if name == "color_scheme" and not allow_color_scheme:
            raise Namel3ssError(
                "color_scheme is only supported at the page level.",
                line=tok.line,
                column=tok.column,
            )
        parser._advance()
        if parser._match("COLON"):
            pass
        else:
            parser._expect("IS", f"Expected 'is' after {name}")
        value = _parse_token_value(parser, name)
        if name in tokens:
            raise Namel3ssError(f"duplicate definition for {name}.", line=tok.line, column=tok.column)
        if line is None:
            line = tok.line
            column = tok.column
        tokens[name] = value
        parser._match("NEWLINE")
    return tokens, line, column


def _parse_token_value(parser, name: str) -> str:
    value_tok = parser._current()
    if value_tok.type in {"STRING", "IDENT"}:
        parser._advance()
        return normalize_ui_theme_token_value(
            name,
            str(value_tok.value),
            line=value_tok.line,
            column=value_tok.column,
        )
    raise Namel3ssError(
        f"Expected {name} token value.",
        line=value_tok.line,
        column=value_tok.column,
    )


__all__ = ["parse_page_theme_tokens_block", "parse_page_theme_tokens_inline"]
