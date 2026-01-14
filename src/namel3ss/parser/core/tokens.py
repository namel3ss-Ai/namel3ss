from __future__ import annotations

from typing import Optional

from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.keywords import is_keyword
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
        if token_type == "IDENT" and isinstance(tok.value, str) and is_keyword(tok.value):
            guidance = build_guidance_message(
                what=f"Reserved keyword '{tok.value}' cannot be used as an identifier.",
                why="Keywords have fixed meaning in the grammar and cannot be reused for variable names.",
                fix=f"Rename the identifier (for example, 'ticket_{tok.value}' or '{tok.value}_value').",
                example=f"let ticket_{tok.value} is \"...\"",
            )
            raise_parse_error(
                tok,
                guidance,
                details={"error_id": "parse.reserved_identifier", "keyword": tok.value},
            )
        raise_parse_error(tok, message or f"Expected {token_type}, got {tok.type}")
    advance(stream)
    return tok


__all__ = ["advance", "current", "expect", "match"]
