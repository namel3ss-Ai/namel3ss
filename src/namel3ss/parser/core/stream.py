from __future__ import annotations

from dataclasses import dataclass

from namel3ss.lexer.tokens import Token
from namel3ss.parser.core import tokens as token_ops


@dataclass
class TokenStream:
    tokens: list[Token]
    position: int = 0

    def current(self) -> Token:
        return token_ops.current(self)

    def advance(self) -> Token:
        return token_ops.advance(self)

    def match(self, *types: str) -> bool:
        return token_ops.match(self, *types)

    def expect(self, token_type: str, message: str | None = None) -> Token:
        return token_ops.expect(self, token_type, message)


__all__ = ["TokenStream"]
