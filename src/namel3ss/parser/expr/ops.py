from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.grammar_table import select_expression_rule
from namel3ss.parser.expr.comparisons import parse_comparison
from namel3ss.parser.sugar.grammar import parse_postfix_access


def parse_expression(parser) -> ast.Expression:
    return parse_or(parser)


def parse_or(parser) -> ast.Expression:
    expr = parse_and(parser)
    while parser._match("OR"):
        op_tok = parser.tokens[parser.position - 1]
        right = parse_and(parser)
        expr = ast.BinaryOp(op="or", left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def parse_and(parser) -> ast.Expression:
    expr = parse_not(parser)
    while parser._match("AND"):
        op_tok = parser.tokens[parser.position - 1]
        right = parse_not(parser)
        expr = ast.BinaryOp(op="and", left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def parse_not(parser) -> ast.Expression:
    if parser._match("NOT"):
        tok = parser.tokens[parser.position - 1]
        operand = parse_not(parser)
        return ast.UnaryOp(op="not", operand=operand, line=tok.line, column=tok.column)
    return parse_comparison(parser)


def parse_additive(parser) -> ast.Expression:
    expr = parse_multiplicative(parser)
    while parser._match("PLUS", "MINUS"):
        op_tok = parser.tokens[parser.position - 1]
        right = parse_multiplicative(parser)
        op = "+" if op_tok.type == "PLUS" else "-"
        expr = ast.BinaryOp(op=op, left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def parse_multiplicative(parser) -> ast.Expression:
    expr = parse_unary(parser)
    while parser._match("STAR", "SLASH", "PERCENT"):
        op_tok = parser.tokens[parser.position - 1]
        right = parse_unary(parser)
        if op_tok.type == "STAR":
            op = "*"
        elif op_tok.type == "SLASH":
            op = "/"
        else:
            op = "%"
        expr = ast.BinaryOp(op=op, left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def parse_unary(parser) -> ast.Expression:
    if parser._match("PLUS", "MINUS"):
        tok = parser.tokens[parser.position - 1]
        op = "+" if tok.type == "PLUS" else "-"
        operand = parse_unary(parser)
        return ast.UnaryOp(op=op, operand=operand, line=tok.line, column=tok.column)
    return parse_exponent(parser)


def parse_exponent(parser) -> ast.Expression:
    expr = parse_primary(parser)
    if parser._match("POWER"):
        op_tok = parser.tokens[parser.position - 1]
        right = parse_unary(parser)
        expr = ast.BinaryOp(op="**", left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def parse_primary(parser) -> ast.Expression:
    rule = select_expression_rule(parser)
    if rule is None:
        tok = parser._current()
        raise Namel3ssError("Unexpected expression", line=tok.line, column=tok.column)
    expr = rule.parse(parser)
    return parse_postfix_access(parser, expr)


def parse_grouped_expression(parser) -> ast.Expression:
    parser._advance()
    expr = parser._parse_expression()
    parser._expect("RPAREN", "Expected ')'")
    return expr


__all__ = [
    "parse_additive",
    "parse_and",
    "parse_expression",
    "parse_exponent",
    "parse_grouped_expression",
    "parse_multiplicative",
    "parse_not",
    "parse_or",
    "parse_primary",
    "parse_unary",
]
