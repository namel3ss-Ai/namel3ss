from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_field_constraint(parser) -> ast.FieldConstraint:
    tok = parser._current()
    if parser._match("BE"):
        if _match_ident_value(parser, "between"):
            low_expr = _parse_numeric_expression(parser)
            parser._expect("AND", "Expected 'and' after between lower bound")
            high_expr = _parse_numeric_expression(parser)
            return ast.FieldConstraint(
                kind="between",
                expression=low_expr,
                expression_high=high_expr,
                line=tok.line,
                column=tok.column,
            )
        if parser._match("AT"):
            if parser._match("LEAST"):
                expr = _parse_numeric_expression(parser)
                return ast.FieldConstraint(kind="gte", expression=expr, line=tok.line, column=tok.column)
            if parser._match("MOST"):
                expr = _parse_numeric_expression(parser)
                return ast.FieldConstraint(kind="lte", expression=expr, line=tok.line, column=tok.column)
            next_tok = parser._current()
            raise Namel3ssError("Expected 'least' or 'most' after 'at'", line=next_tok.line, column=next_tok.column)
        if parser._match("TYPE_INT"):
            return ast.FieldConstraint(kind="int", line=tok.line, column=tok.column)
        if _match_ident_value(parser, "an") or _match_ident_value(parser, "a"):
            if parser._match("TYPE_INT"):
                return ast.FieldConstraint(kind="int", line=tok.line, column=tok.column)
            next_tok = parser._current()
            raise Namel3ssError("Expected 'integer' after article", line=next_tok.line, column=next_tok.column)
        if parser._match("PRESENT"):
            return ast.FieldConstraint(kind="present", line=tok.line, column=tok.column)
        if parser._match("UNIQUE"):
            return ast.FieldConstraint(kind="unique", line=tok.line, column=tok.column)
        if parser._match("GREATER"):
            parser._expect("THAN", "Expected 'than' after 'greater'")
            expr = _parse_numeric_expression(parser)
            return ast.FieldConstraint(kind="gt", expression=expr, line=tok.line, column=tok.column)
        if parser._match("LESS"):
            parser._expect("THAN", "Expected 'than' after 'less'")
            expr = _parse_numeric_expression(parser)
            return ast.FieldConstraint(kind="lt", expression=expr, line=tok.line, column=tok.column)
    if parser._match("MATCH"):
        parser._expect("PATTERN", "Expected 'pattern'")
        pattern_tok = parser._expect("STRING", "Expected pattern string")
        return ast.FieldConstraint(kind="pattern", pattern=pattern_tok.value, line=tok.line, column=tok.column)
    if parser._match("HAVE"):
        parser._expect("LENGTH", "Expected 'length'")
        parser._expect("AT", "Expected 'at'")
        if parser._match("LEAST"):
            expr = parser._parse_expression()
            return ast.FieldConstraint(kind="len_min", expression=expr, line=tok.line, column=tok.column)
        if parser._match("MOST"):
            expr = parser._parse_expression()
            return ast.FieldConstraint(kind="len_max", expression=expr, line=tok.line, column=tok.column)
        tok = parser._current()
        raise Namel3ssError("Expected 'least' or 'most' after length", line=tok.line, column=tok.column)
    raise Namel3ssError("Unknown constraint", line=tok.line, column=tok.column)


def _match_ident_value(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


def _parse_numeric_expression(parser) -> ast.Expression:
    return parser._parse_additive()


__all__ = ["parse_field_constraint"]
