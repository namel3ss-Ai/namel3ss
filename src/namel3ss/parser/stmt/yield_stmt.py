from __future__ import annotations

from namel3ss.ast import nodes as ast


def parse_yield_stmt(parser) -> ast.Yield:
    yield_tok = parser._advance()
    expr = parser._parse_expression()
    return ast.Yield(expression=expr, line=yield_tok.line, column=yield_tok.column)


__all__ = ["parse_yield_stmt"]
