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
    if tok.type == "IDENT" and _looks_like_builtin_call(parser):
        return parse_builtin_call_expr(parser)
    parser._advance()
    attrs: List[str] = []
    while parser._match("DOT"):
        attr_name = read_attr_name(parser, context="identifier after '.'")
        attrs.append(attr_name)
    if attrs:
        return ast.AttrAccess(base=tok.value, attrs=attrs, line=tok.line, column=tok.column)
    return ast.VarReference(name=tok.value, line=tok.line, column=tok.column)


def parse_builtin_call_expr(parser) -> ast.BuiltinCallExpr:
    name_tok = parser._advance()
    parser._expect("LPAREN", "Expected '(' after builtin name")
    args: List[ast.Expression] = []
    if not parser._match("RPAREN"):
        while True:
            args.append(parser._parse_expression())
            if parser._match("COMMA"):
                continue
            parser._expect("RPAREN", "Expected ')' after builtin arguments")
            break
    return ast.BuiltinCallExpr(name=name_tok.value, arguments=args, line=name_tok.line, column=name_tok.column)


def _looks_like_builtin_call(parser) -> bool:
    pos = parser.position + 1
    if pos >= len(parser.tokens):
        return False
    return parser.tokens[pos].type == "LPAREN"


__all__ = ["parse_reference_expr"]
