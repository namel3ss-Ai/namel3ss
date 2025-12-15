from __future__ import annotations

from typing import Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.lexer.tokens import Token


def current(parser) -> Token:
    return parser.tokens[parser.position]


def advance(parser) -> Token:
    tok = parser.tokens[parser.position]
    parser.position += 1
    return tok


def match(parser, *types: str) -> bool:
    if current(parser).type in types:
        advance(parser)
        return True
    return False


def expect(parser, token_type: str, message: Optional[str] = None) -> Token:
    tok = current(parser)
    if tok.type != token_type:
        raise Namel3ssError(
            message or f"Expected {token_type}, got {tok.type}",
            line=tok.line,
            column=tok.column,
        )
    advance(parser)
    return tok
