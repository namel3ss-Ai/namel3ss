from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def looks_like_list_expression(parser) -> bool:
    next_tok = _peek(parser)
    if next_tok is None:
        return False
    if next_tok.type == "COLON":
        return True
    return isinstance(next_tok.value, str) and next_tok.value in {"length", "append", "get"}


def looks_like_map_expression(parser) -> bool:
    next_tok = _peek(parser)
    if next_tok is None:
        return False
    if next_tok.type == "COLON":
        return True
    return isinstance(next_tok.value, str) and next_tok.value in {"get", "set", "keys"}


def parse_list_expression(parser) -> ast.Expression:
    list_tok = parser._advance()
    if parser._match("COLON"):
        return _parse_list_literal(parser, list_tok.line, list_tok.column)
    if _match_word(parser, "length"):
        _expect_word(parser, "of")
        target = parser._parse_expression()
        return ast.ListOpExpr(kind="length", target=target, line=list_tok.line, column=list_tok.column)
    if _match_word(parser, "append"):
        target = parser._parse_expression()
        _expect_word(parser, "with")
        value = parser._parse_expression()
        return ast.ListOpExpr(
            kind="append",
            target=target,
            value=value,
            line=list_tok.line,
            column=list_tok.column,
        )
    if _match_word(parser, "get"):
        target = parser._parse_expression()
        _expect_word(parser, "at")
        index = parser._parse_expression()
        return ast.ListOpExpr(
            kind="get",
            target=target,
            index=index,
            line=list_tok.line,
            column=list_tok.column,
        )
    raise Namel3ssError("Expected list expression", line=list_tok.line, column=list_tok.column)


def parse_map_expression(parser) -> ast.Expression:
    map_tok = parser._advance()
    if parser._match("COLON"):
        return _parse_map_literal(parser, map_tok.line, map_tok.column)
    if _match_word(parser, "get"):
        target = parser._parse_expression()
        _expect_word(parser, "key")
        key = parser._parse_expression()
        return ast.MapOpExpr(
            kind="get",
            target=target,
            key=key,
            line=map_tok.line,
            column=map_tok.column,
        )
    if _match_word(parser, "set"):
        target = parser._parse_expression()
        _expect_word(parser, "key")
        key = parser._parse_expression()
        _expect_word(parser, "value")
        value = parser._parse_expression()
        return ast.MapOpExpr(
            kind="set",
            target=target,
            key=key,
            value=value,
            line=map_tok.line,
            column=map_tok.column,
        )
    if _match_word(parser, "keys"):
        target = parser._parse_expression()
        return ast.MapOpExpr(
            kind="keys",
            target=target,
            line=map_tok.line,
            column=map_tok.column,
        )
    raise Namel3ssError("Expected map expression", line=map_tok.line, column=map_tok.column)


def _parse_list_literal(parser, line: int, column: int) -> ast.ListExpr:
    parser._expect("NEWLINE", "Expected newline after list")
    parser._expect("INDENT", "Expected indented list items")
    items: list[ast.Expression] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        items.append(parser._parse_expression())
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of list")
    while parser._match("NEWLINE"):
        pass
    return ast.ListExpr(items=items, line=line, column=column)


def _parse_map_literal(parser, line: int, column: int) -> ast.MapExpr:
    parser._expect("NEWLINE", "Expected newline after map")
    parser._expect("INDENT", "Expected indented map entries")
    entries: list[ast.MapEntry] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._expect("STRING", "Expected map key string")
        parser._expect("IS", "Expected 'is' after map key")
        value_expr = parser._parse_expression()
        entries.append(
            ast.MapEntry(
                key=ast.Literal(value=key_tok.value, line=key_tok.line, column=key_tok.column),
                value=value_expr,
                line=key_tok.line,
                column=key_tok.column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of map")
    while parser._match("NEWLINE"):
        pass
    return ast.MapExpr(entries=entries, line=line, column=column)


def _peek(parser):
    pos = parser.position + 1
    if pos >= len(parser.tokens):
        return None
    return parser.tokens[pos]


def _match_word(parser, value: str) -> bool:
    tok = parser._current()
    if not isinstance(tok.value, str) or tok.value != value:
        return False
    parser._advance()
    return True


def _expect_word(parser, value: str) -> None:
    tok = parser._current()
    if not isinstance(tok.value, str) or tok.value != value:
        raise Namel3ssError(f"Expected '{value}'", line=tok.line, column=tok.column)
    parser._advance()


__all__ = [
    "looks_like_list_expression",
    "looks_like_map_expression",
    "parse_list_expression",
    "parse_map_expression",
]
