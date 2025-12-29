from __future__ import annotations

from namel3ss.ast import nodes as ast


def parse_return(parser) -> ast.Return:
    ret_tok = parser._advance()
    expr = parser._parse_expression()
    return ast.Return(expression=expr, line=ret_tok.line, column=ret_tok.column)


__all__ = ["parse_return"]
