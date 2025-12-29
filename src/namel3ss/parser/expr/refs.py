from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.parser.expr.common import read_attr_name


def parse_reference_expr(parser) -> ast.Expression:
    tok = parser._current()
    parser._advance()
    attrs: List[str] = []
    while parser._match("DOT"):
        attr_name = read_attr_name(parser, context="identifier after '.'")
        attrs.append(attr_name)
    if attrs:
        return ast.AttrAccess(base=tok.value, attrs=attrs, line=tok.line, column=tok.column)
    return ast.VarReference(name=tok.value, line=tok.line, column=tok.column)


__all__ = ["parse_reference_expr"]
