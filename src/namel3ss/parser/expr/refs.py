from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.parser.expr.common import read_attr_name
from namel3ss.parser.expr.collections import (
    looks_like_list_aggregate_expr,
    looks_like_list_reduce_expr,
    looks_like_list_transform_expr,
    looks_like_list_expression,
    looks_like_map_expression,
    parse_list_aggregate_expr,
    parse_list_reduce_expr,
    parse_list_transform_expr,
    parse_list_expression,
    parse_map_expression,
)


def parse_reference_expr(parser) -> ast.Expression:
    tok = parser._current()
    if tok.type == "IDENT" and looks_like_list_reduce_expr(parser):
        return parse_list_reduce_expr(parser)
    if tok.type == "IDENT" and looks_like_list_transform_expr(parser):
        return parse_list_transform_expr(parser)
    if tok.type == "IDENT" and looks_like_list_aggregate_expr(parser):
        return parse_list_aggregate_expr(parser)
    if tok.type == "IDENT" and tok.value == "list" and looks_like_list_expression(parser):
        return parse_list_expression(parser)
    if tok.type == "IDENT" and tok.value == "map" and looks_like_map_expression(parser):
        return parse_map_expression(parser)
    parser._advance()
    attrs: List[str] = []
    while parser._match("DOT"):
        attr_name = read_attr_name(parser, context="identifier after '.'")
        attrs.append(attr_name)
    if attrs:
        return ast.AttrAccess(base=tok.value, attrs=attrs, line=tok.line, column=tok.column)
    return ast.VarReference(name=tok.value, line=tok.line, column=tok.column)


__all__ = ["parse_reference_expr"]
