from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.expr.common import read_attr_name


def parse_visibility_expression(parser, *, allow_pattern_params: bool = False) -> ast.Expression | ast.PatternParamRef:
    return _parse_or(parser, allow_pattern_params=allow_pattern_params)


def _parse_or(parser, *, allow_pattern_params: bool) -> ast.Expression | ast.PatternParamRef:
    expr = _parse_and(parser, allow_pattern_params=allow_pattern_params)
    while parser._match("OR"):
        op_tok = parser.tokens[parser.position - 1]
        right = _parse_and(parser, allow_pattern_params=allow_pattern_params)
        expr = ast.BinaryOp(op="or", left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def _parse_and(parser, *, allow_pattern_params: bool) -> ast.Expression | ast.PatternParamRef:
    expr = _parse_not(parser, allow_pattern_params=allow_pattern_params)
    while parser._match("AND"):
        op_tok = parser.tokens[parser.position - 1]
        right = _parse_not(parser, allow_pattern_params=allow_pattern_params)
        expr = ast.BinaryOp(op="and", left=expr, right=right, line=op_tok.line, column=op_tok.column)
    return expr


def _parse_not(parser, *, allow_pattern_params: bool) -> ast.Expression | ast.PatternParamRef:
    if parser._match("NOT"):
        tok = parser.tokens[parser.position - 1]
        operand = _parse_not(parser, allow_pattern_params=allow_pattern_params)
        return ast.UnaryOp(op="not", operand=operand, line=tok.line, column=tok.column)
    return _parse_comparison(parser, allow_pattern_params=allow_pattern_params)


def _parse_comparison(parser, *, allow_pattern_params: bool) -> ast.Expression | ast.PatternParamRef:
    left = _parse_factor(parser, allow_pattern_params=allow_pattern_params)

    if _match_symbol_pair(parser, "EQUALS", "EQUALS"):
        tok = parser.tokens[parser.position - 2]
        right = _parse_factor(parser, allow_pattern_params=allow_pattern_params)
        return ast.Comparison(kind="eq", left=left, right=right, line=tok.line, column=tok.column)

    if parser._match("BANG"):
        tok = parser.tokens[parser.position - 1]
        parser._expect("EQUALS", "Expected '=' after '!' in visibility expression")
        right = _parse_factor(parser, allow_pattern_params=allow_pattern_params)
        return ast.Comparison(kind="ne", left=left, right=right, line=tok.line, column=tok.column)

    if parser._match("GT"):
        tok = parser.tokens[parser.position - 1]
        kind = "gte" if parser._match("EQUALS") else "gt"
        right = _parse_factor(parser, allow_pattern_params=allow_pattern_params)
        return ast.Comparison(kind=kind, left=left, right=right, line=tok.line, column=tok.column)

    if parser._match("LT"):
        tok = parser.tokens[parser.position - 1]
        kind = "lte" if parser._match("EQUALS") else "lt"
        right = _parse_factor(parser, allow_pattern_params=allow_pattern_params)
        return ast.Comparison(kind=kind, left=left, right=right, line=tok.line, column=tok.column)

    if parser._match("IN"):
        tok = parser.tokens[parser.position - 1]
        right = _parse_factor(parser, allow_pattern_params=allow_pattern_params)
        return ast.Comparison(kind="in", left=left, right=right, line=tok.line, column=tok.column)

    if parser._match("NOT"):
        tok = parser.tokens[parser.position - 1]
        parser._expect("IN", "Expected 'in' after 'not' in visibility expression")
        right = _parse_factor(parser, allow_pattern_params=allow_pattern_params)
        return ast.Comparison(kind="nin", left=left, right=right, line=tok.line, column=tok.column)

    return left


def _parse_factor(parser, *, allow_pattern_params: bool) -> ast.Expression | ast.PatternParamRef:
    tok = parser._current()

    if allow_pattern_params and tok.type == "PARAM":
        return _parse_param_ref(parser)

    if tok.type == "BOOLEAN":
        parser._advance()
        return ast.Literal(value=bool(tok.value), line=tok.line, column=tok.column)

    if tok.type == "NUMBER":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)

    if tok.type == "STRING":
        parser._advance()
        return ast.Literal(value=str(tok.value), line=tok.line, column=tok.column)

    if tok.type == "STATE":
        return _parse_state_path(parser)

    if tok.type == "LBRACKET":
        return _parse_list_literal(parser, allow_pattern_params=allow_pattern_params)

    if tok.type == "LPAREN":
        parser._advance()
        expr = _parse_or(parser, allow_pattern_params=allow_pattern_params)
        parser._expect("RPAREN", "Expected ')' to close visibility expression")
        return expr

    raise Namel3ssError(
        "Visibility expressions only support literals, state paths, lists, and boolean operators.",
        line=tok.line,
        column=tok.column,
    )


def _parse_state_path(parser) -> ast.StatePath:
    state_tok = parser._expect("STATE", "Expected state.<path>")
    path: list[str] = []
    if parser._match("DOT"):
        path.append(read_attr_name(parser, context="identifier after '.'"))
    else:
        path.append(read_attr_name(parser, context="state path"))
    while parser._match("DOT"):
        path.append(read_attr_name(parser, context="identifier after '.'"))
    return ast.StatePath(path=path, line=state_tok.line, column=state_tok.column)


def _parse_list_literal(parser, *, allow_pattern_params: bool) -> ast.ListExpr:
    list_tok = parser._expect("LBRACKET", "Expected '[' to start list literal")
    items: list[ast.Expression | ast.PatternParamRef] = []
    if parser._match("RBRACKET"):
        return ast.ListExpr(items=[], line=list_tok.line, column=list_tok.column)
    while True:
        items.append(_parse_or(parser, allow_pattern_params=allow_pattern_params))
        if parser._match("COMMA"):
            if parser._current().type == "RBRACKET":
                break
            continue
        break
    parser._expect("RBRACKET", "Expected ']' to end list literal")
    return ast.ListExpr(items=items, line=list_tok.line, column=list_tok.column)


def _parse_param_ref(parser) -> ast.PatternParamRef:
    tok = parser._expect("PARAM", "Expected param.<name>")
    parser._expect("DOT", "Expected '.' after param")
    name_tok = parser._expect("IDENT", "Expected parameter name")
    return ast.PatternParamRef(name=name_tok.value, line=tok.line, column=tok.column)


def _match_symbol_pair(parser, first: str, second: str) -> bool:
    if not parser._match(first):
        return False
    if parser._match(second):
        return True
    parser.position -= 1
    return False


__all__ = ["parse_visibility_expression"]
