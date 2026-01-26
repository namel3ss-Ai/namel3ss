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
        raise_parse_error(tok, message or f"Expected {token_type}, got {tok.type}")
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
        raise_parse_error(tok, message or "Expected identifier")
    if isinstance(tok.value, str) and is_keyword(tok.value) and not getattr(tok, "escaped", False):
        guidance, details = reserved_identifier_diagnostic(tok.value)
        raise_parse_error(
            tok,
            guidance,
            details=details,
        )
    advance(stream)
    return tok


__all__ = ["advance", "current", "expect", "match", "parse_identifier_name"]
