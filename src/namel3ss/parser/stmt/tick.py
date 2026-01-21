from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_tick(parser) -> ast.AdvanceTime:
    tick_tok = parser._advance()
    if parser._current().type in {"NEWLINE", "DEDENT", "EOF"}:
        raise Namel3ssError("Expected duration after tick", line=tick_tok.line, column=tick_tok.column)
    amount = parser._parse_expression()
    return ast.AdvanceTime(amount=amount, line=tick_tok.line, column=tick_tok.column)


__all__ = ["parse_tick"]
