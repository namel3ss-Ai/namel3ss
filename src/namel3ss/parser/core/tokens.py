from __future__ import annotations

from typing import Optional

from namel3ss.lexer.tokens import Token
from namel3ss.parser.core.errors import raise_parse_error


def current(stream) -> Token:
    return stream.tokens[stream.position]


def advance(stream) -> Token:
    tok = stream.tokens[stream.position]
    stream.position += 1
    return tok


def match(stream, *types: str) -> bool:
    if current(stream).type in types:
        advance(stream)
        return True
    return False


def expect(stream, token_type: str, message: Optional[str] = None) -> Token:
    tok = current(stream)
    if tok.type != token_type:
        raise_parse_error(tok, message or f"Expected {token_type}, got {tok.type}")
    advance(stream)
    return tok


__all__ = ["advance", "current", "expect", "match"]
