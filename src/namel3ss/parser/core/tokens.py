from __future__ import annotations

from typing import Optional

from namel3ss.lang.keywords import is_keyword
from namel3ss.lexer.tokens import ESCAPED_IDENTIFIER, Token
from namel3ss.parser.core.errors import raise_parse_error
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def _normalize_token(token: Token) -> Token:
    if token.type == ESCAPED_IDENTIFIER:
        return Token("IDENT", token.value, token.line, token.column, escaped=True)
    return token


def current(stream) -> Token:
    return _normalize_token(stream.tokens[stream.position])


def advance(stream) -> Token:
    tok = _normalize_token(stream.tokens[stream.position])
    stream.position += 1
    return tok


def match(stream, *types: str) -> bool:
    if current(stream).type in types:
        advance(stream)
        return True
    return False


def expect(stream, token_type: str, message: Optional[str] = None) -> Token:
    tok = current(stream)
    if token_type == "IDENT":
        return parse_identifier_name(stream, message)
    if tok.type != token_type:
        detail = message or _expected_token_message(stream, expected=token_type, actual=tok.type, token=tok)
        raise_parse_error(tok, detail)
    advance(stream)
    return tok


def parse_identifier_name(stream, message: Optional[str] = None) -> Token:
    tok = current(stream)
    if tok.type != "IDENT":
        if isinstance(tok.value, str) and is_keyword(tok.value):
            guidance, details = reserved_identifier_diagnostic(tok.value)
            raise_parse_error(
                tok,
                guidance,
                details=details,
            )
        raise_parse_error(tok, message or _expected_token_message(stream, expected="IDENT", actual=tok.type, token=tok))
    if isinstance(tok.value, str) and is_keyword(tok.value) and not getattr(tok, "escaped", False):
        guidance, details = reserved_identifier_diagnostic(tok.value)
        raise_parse_error(
            tok,
            guidance,
            details=details,
        )
    advance(stream)
    return tok


def _expected_token_message(stream, *, expected: str, actual: str, token: Token) -> str:
    base = f"Expected {expected}, got {actual}."
    snippet = _line_snippet(stream, token)
    if snippet:
        return f"{base}\nContext:\n{snippet}"
    return base


def _line_snippet(stream, token: Token) -> str:
    lines = getattr(stream, "source_lines", None)
    if not isinstance(lines, list):
        return ""
    index = int(token.line) - 1
    if index < 0 or index >= len(lines):
        return ""
    line_text = lines[index]
    marker = " " * max(0, int(token.column) - 1) + "^"
    return f"  {line_text}\n  {marker}"


__all__ = ["advance", "current", "expect", "match", "parse_identifier_name"]
