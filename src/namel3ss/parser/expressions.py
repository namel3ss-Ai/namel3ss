from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


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


def parse_comparison(parser) -> ast.Expression:
    left = parse_additive(parser)
    if not parser._match("IS"):
        return left
    is_tok = parser.tokens[parser.position - 1]
    if parser._match("NOT"):
        if parser._match("EQUAL"):
            if parser._match("TO"):
                pass
        right = parse_additive(parser)
        return ast.Comparison(kind="ne", left=left, right=right, line=is_tok.line, column=is_tok.column)
    if _match_ident_value(parser, "one"):
        _expect_ident_value(parser, "of")
        values = _parse_literal_list(parser)
        return _one_of_expression(left, values, is_tok.line, is_tok.column)
    if parser._match("GREATER"):
        parser._expect("THAN", "Expected 'than' after 'is greater'")
        right = parse_additive(parser)
        return ast.Comparison(kind="gt", left=left, right=right, line=is_tok.line, column=is_tok.column)
    if parser._match("LESS"):
        parser._expect("THAN", "Expected 'than' after 'is less'")
        right = parse_additive(parser)
        return ast.Comparison(kind="lt", left=left, right=right, line=is_tok.line, column=is_tok.column)
    if parser._match("AT"):
        if parser._match("LEAST"):
            right = parse_additive(parser)
            return ast.Comparison(kind="gte", left=left, right=right, line=is_tok.line, column=is_tok.column)
        if parser._match("MOST"):
            right = parse_additive(parser)
            return ast.Comparison(kind="lte", left=left, right=right, line=is_tok.line, column=is_tok.column)
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Incomplete comparison after 'is at'.",
                why="`is at` must be followed by `least` or `most` to form a comparison.",
                fix="Use `is at least` or `is at most` with a number.",
                example="if total is at least 10:",
            ),
            line=tok.line,
            column=tok.column,
        )
    if parser._match("EQUAL"):
        if parser._match("TO"):
            pass
        right = parse_additive(parser)
        return ast.Comparison(kind="eq", left=left, right=right, line=is_tok.line, column=is_tok.column)
    right = parse_additive(parser)
    return ast.Comparison(kind="eq", left=left, right=right, line=is_tok.line, column=is_tok.column)


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
    while parser._match("STAR", "SLASH"):
        op_tok = parser.tokens[parser.position - 1]
        right = parse_unary(parser)
        op = "*" if op_tok.type == "STAR" else "/"
        expr = ast.BinaryOp(op=op, left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def parse_unary(parser) -> ast.Expression:
    if parser._match("PLUS", "MINUS"):
        tok = parser.tokens[parser.position - 1]
        op = "+" if tok.type == "PLUS" else "-"
        operand = parse_unary(parser)
        return ast.UnaryOp(op=op, operand=operand, line=tok.line, column=tok.column)
    return parse_primary(parser)


def parse_primary(parser) -> ast.Expression:
    tok = parser._current()
    if tok.type == "NUMBER":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    if tok.type == "STRING":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    if tok.type == "BOOLEAN":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    if tok.type in {"IDENT", "INPUT"}:
        parser._advance()
        attrs: List[str] = []
        while parser._match("DOT"):
            attr_tok = parser._expect("IDENT", "Expected identifier after '.'")
            attrs.append(attr_tok.value)
        if attrs:
            return ast.AttrAccess(base=tok.value, attrs=attrs, line=tok.line, column=tok.column)
        return ast.VarReference(name=tok.value, line=tok.line, column=tok.column)
    if tok.type == "STATE":
        return parse_state_path(parser)
    if tok.type == "LPAREN":
        parser._advance()
        expr = parse_expression(parser)
        parser._expect("RPAREN", "Expected ')'")
        return expr
    if tok.type == "ASK":
        raise Namel3ssError(
            'AI calls are statements. Use: ask ai "name" with input: <expr> as <target>.',
            line=tok.line,
            column=tok.column,
        )
    raise Namel3ssError("Unexpected expression", line=tok.line, column=tok.column)


def parse_state_path(parser) -> ast.StatePath:
    state_tok = parser._expect("STATE", "Expected 'state'")
    path: List[str] = []
    while parser._match("DOT"):
        ident_tok = parser._expect("IDENT", "Expected identifier after '.'")
        path.append(ident_tok.value)
    if not path:
        raise Namel3ssError("Expected state path after 'state'", line=state_tok.line, column=state_tok.column)
    return ast.StatePath(path=path, line=state_tok.line, column=state_tok.column)


def _parse_literal_list(parser) -> List[ast.Expression]:
    parser._expect("LBRACKET", "Expected '[' to start list")
    items: List[ast.Expression] = []
    if parser._match("RBRACKET"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="One-of list cannot be empty.",
                why="Membership checks need at least one literal value.",
                fix="Add one or more literal values.",
                example='requires identity.role is one of ["admin", "staff"]',
            ),
            line=tok.line,
            column=tok.column,
        )
    while True:
        tok = parser._current()
        if tok.type == "STRING":
            parser._advance()
            items.append(ast.Literal(value=tok.value, line=tok.line, column=tok.column))
        elif tok.type == "NUMBER":
            parser._advance()
            items.append(ast.Literal(value=tok.value, line=tok.line, column=tok.column))
        elif tok.type == "BOOLEAN":
            parser._advance()
            items.append(ast.Literal(value=tok.value, line=tok.line, column=tok.column))
        else:
            raise Namel3ssError(
                build_guidance_message(
                    what="One-of list contains a non-literal value.",
                    why="Only string, number, or boolean literals are allowed in one-of lists.",
                    fix="Replace the value with a literal.",
                    example='requires identity.role is one of ["admin", "staff"]',
                ),
                line=tok.line,
                column=tok.column,
            )
        if parser._match("COMMA"):
            continue
        parser._expect("RBRACKET", "Expected ']' after list")
        break
    return items


def _one_of_expression(
    left: ast.Expression,
    values: List[ast.Expression],
    line: int,
    column: int,
) -> ast.Expression:
    expr: ast.Expression | None = None
    for value in values:
        comparison = ast.Comparison(kind="eq", left=left, right=value, line=line, column=column)
        if expr is None:
            expr = comparison
        else:
            expr = ast.BinaryOp(op="or", left=expr, right=comparison, line=line, column=column)
    if expr is None:
        raise Namel3ssError("One-of list must contain at least one value", line=line, column=column)
    return expr


def _match_ident_value(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


def _expect_ident_value(parser, value: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Expected '{value}' after 'is'.",
                why="Membership checks use `is one of [..]` with the word sequence.",
                fix=f"Add '{value}' in the membership clause.",
                example='requires identity.role is one of ["admin", "staff"]',
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._advance()
