from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_comparison(parser) -> ast.Expression:
    from namel3ss.parser.expr.ops import parse_additive

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
    if _looks_like_strictly_between(parser):
        parser._advance()
        parser._advance()
        return _parse_between_expression(parser, left, is_tok, strict=True)
    if _match_ident_value(parser, "between"):
        return _parse_between_expression(parser, left, is_tok, strict=False)
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


_BETWEEN_START_TOKENS = {
    "NUMBER",
    "STRING",
    "BOOLEAN",
    "NULL",
    "IDENT",
    "INPUT",
    "STATE",
    "LPAREN",
    "CALL",
    "ASK",
    "PLUS",
    "MINUS",
}


def _parse_between_expression(
    parser,
    left: ast.Expression,
    is_tok,
    *,
    strict: bool,
) -> ast.Expression:
    _expect_between_bound(parser, kind="lower")
    lower = parser._parse_additive()
    and_tok = parser._expect("AND", "Expected 'and' after between lower bound")
    _expect_between_bound(parser, kind="upper")
    upper = parser._parse_additive()
    if strict:
        lower_cmp = ast.Comparison(kind="gt", left=left, right=lower, line=is_tok.line, column=is_tok.column)
        upper_cmp = ast.Comparison(kind="lt", left=left, right=upper, line=is_tok.line, column=is_tok.column)
    else:
        lower_cmp = ast.Comparison(kind="gte", left=left, right=lower, line=is_tok.line, column=is_tok.column)
        upper_cmp = ast.Comparison(kind="lte", left=left, right=upper, line=is_tok.line, column=is_tok.column)
    return ast.BinaryOp(op="and", left=lower_cmp, right=upper_cmp, line=and_tok.line, column=and_tok.column)


def _expect_between_bound(parser, *, kind: str) -> None:
    tok = parser._current()
    if tok.type in _BETWEEN_START_TOKENS:
        return
    bound = "lower" if kind == "lower" else "upper"
    raise Namel3ssError(
        build_guidance_message(
            what=f"Between comparison is missing the {bound} bound.",
            why="`is between` requires two bounds separated by `and`.",
            fix=f"Add the {bound} bound to the between comparison.",
            example="if value is between 1 and 10:",
        ),
        line=tok.line,
        column=tok.column,
    )


def _looks_like_strictly_between(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "strictly":
        return False
    next_tok = parser.tokens[parser.position + 1] if parser.position + 1 < len(parser.tokens) else None
    return bool(next_tok and next_tok.type == "IDENT" and next_tok.value == "between")


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


__all__ = ["parse_comparison"]
