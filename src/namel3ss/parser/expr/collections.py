from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.keywords import is_keyword


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


_AGGREGATE_NAMES = {"sum", "min", "max", "mean", "median"}
_TRANSFORM_NAMES = {"map", "filter"}
_REDUCE_NAME = "reduce"


def looks_like_list_aggregate_expr(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value not in _AGGREGATE_NAMES:
        return False
    next_tok = _peek(parser)
    return bool(next_tok and next_tok.type == "LPAREN")


def parse_list_aggregate_expr(parser) -> ast.Expression:
    name_tok = parser._advance()
    parser._expect("LPAREN", f"Expected '(' after '{name_tok.value}'")
    if parser._current().type == "RPAREN":
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what=f"{name_tok.value} requires a list expression.",
                why="Aggregations must receive a list value.",
                fix="Pass a list variable or list literal.",
                example=f"let total is {name_tok.value}(numbers)",
            ),
            line=tok.line,
            column=tok.column,
        )
    target = parser._parse_expression()
    if parser._match("COMMA"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what=f"{name_tok.value} accepts a single list expression.",
                why="Aggregations only take one list input.",
                fix="Remove the extra argument.",
                example=f"let total is {name_tok.value}(numbers)",
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._expect("RPAREN", "Expected ')' after list expression")
    return ast.ListOpExpr(kind=name_tok.value, target=target, line=name_tok.line, column=name_tok.column)


def looks_like_list_transform_expr(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value not in _TRANSFORM_NAMES:
        return False
    pos = parser.position + 1
    depth = 0
    tokens = parser.tokens
    while pos < len(tokens):
        current = tokens[pos]
        if current.type in {"NEWLINE", "DEDENT", "EOF"}:
            return False
        if current.type in {"LPAREN", "LBRACKET"}:
            depth += 1
        elif current.type in {"RPAREN", "RBRACKET"} and depth > 0:
            depth -= 1
        elif depth == 0 and current.type == "WITH":
            return True
        pos += 1
    return True


def looks_like_list_reduce_expr(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != _REDUCE_NAME:
        return False
    pos = parser.position + 1
    depth = 0
    tokens = parser.tokens
    while pos < len(tokens):
        current = tokens[pos]
        if current.type in {"NEWLINE", "DEDENT", "EOF"}:
            return False
        if current.type in {"LPAREN", "LBRACKET"}:
            depth += 1
        elif current.type in {"RPAREN", "RBRACKET"} and depth > 0:
            depth -= 1
        elif depth == 0 and current.type == "WITH":
            return True
        pos += 1
    return False


def parse_list_transform_expr(parser) -> ast.Expression:
    op_tok = parser._advance()
    target = parser._parse_expression()
    parser._expect("WITH", f"Expected 'with' after {op_tok.value} input list")
    item_tok = parser._current()
    if item_tok.type != "IDENT" or item_tok.value != "item":
        raise Namel3ssError(
            build_guidance_message(
                what=f"Expected 'item' after 'with' in {op_tok.value} expression.",
                why="List transforms use `with item as <name>` to bind each element.",
                fix="Add `item` after `with`.",
                example=f"let result is {op_tok.value} numbers with item as n:\\n  n",
            ),
            line=item_tok.line,
            column=item_tok.column,
        )
    parser._advance()
    parser._expect("AS", "Expected 'as' after 'item'")
    name = _read_binding_name(parser, op_name=op_tok.value)
    parser._expect("COLON", f"Expected ':' after {op_tok.value} header")
    parser._expect("NEWLINE", f"Expected newline after {op_tok.value} header")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what=f"{op_tok.value} expression needs an indented body.",
                why="List transforms require a block expression after the header.",
                fix="Indent the expression under the header.",
                example=f"let result is {op_tok.value} numbers with item as n:\\n  n",
            ),
            line=tok.line,
            column=tok.column,
        )
    while parser._match("NEWLINE"):
        pass
    if parser._current().type == "DEDENT":
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what=f"{op_tok.value} expression body is missing.",
                why="List transforms require a single expression in the indented block.",
                fix="Add an expression inside the block.",
                example=f"let result is {op_tok.value} numbers with item as n:\\n  n * 2",
            ),
            line=tok.line,
            column=tok.column,
        )
    body_expr = parser._parse_expression()
    while parser._match("NEWLINE"):
        pass
    parser._expect("DEDENT", f"Expected end of {op_tok.value} block")
    if op_tok.value == "map":
        return ast.ListMapExpr(
            target=target,
            var_name=name,
            body=body_expr,
            line=op_tok.line,
            column=op_tok.column,
        )
    return ast.ListFilterExpr(
        target=target,
        var_name=name,
        predicate=body_expr,
        line=op_tok.line,
        column=op_tok.column,
    )


def parse_list_reduce_expr(parser) -> ast.Expression:
    reduce_tok = parser._advance()
    target = parser._parse_expression()
    parser._expect("WITH", "Expected 'with' after reduce input list")
    _expect_ident_value(parser, "acc")
    parser._expect("AS", "Expected 'as' after 'acc'")
    acc_name = _read_binding_name(parser, op_name="reduce")
    parser._expect("AND", "Expected 'and' after accumulator binding")
    _expect_ident_value(parser, "item")
    parser._expect("AS", "Expected 'as' after 'item'")
    item_name = _read_binding_name(parser, op_name="reduce")
    _expect_ident_value(parser, "starting")
    start_expr = parser._parse_expression()
    parser._expect("COLON", "Expected ':' after reduce header")
    parser._expect("NEWLINE", "Expected newline after reduce header")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Reduce expression needs an indented body.",
                why="Reduce requires a block expression after the header.",
                fix="Indent the expression under the header.",
                example="let total is reduce numbers with acc as s and item as n starting 0:\\n  s + n",
            ),
            line=tok.line,
            column=tok.column,
        )
    while parser._match("NEWLINE"):
        pass
    if parser._current().type == "DEDENT":
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Reduce expression body is missing.",
                why="Reduce requires a single expression in the indented block.",
                fix="Add an expression inside the block.",
                example="let total is reduce numbers with acc as s and item as n starting 0:\\n  s + n",
            ),
            line=tok.line,
            column=tok.column,
        )
    body_expr = parser._parse_expression()
    while parser._match("NEWLINE"):
        pass
    parser._expect("DEDENT", "Expected end of reduce block")
    return ast.ListReduceExpr(
        target=target,
        acc_name=acc_name,
        item_name=item_name,
        start=start_expr,
        body=body_expr,
        line=reduce_tok.line,
        column=reduce_tok.column,
    )


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


def _read_binding_name(parser, *, op_name: str) -> str:
    name_tok = parser._current()
    if name_tok.type != "IDENT":
        if isinstance(name_tok.value, str) and is_keyword(name_tok.value):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"'{name_tok.value}' is a reserved keyword.",
                    why="List transform item names must be identifiers that are not keywords.",
                    fix="Choose a different name.",
                    example=f"let result is {op_name} numbers with item as value:\\n  value",
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        raise Namel3ssError("Expected identifier after 'as'", line=name_tok.line, column=name_tok.column)
    parser._advance()
    if is_keyword(name_tok.value):
        raise Namel3ssError(
            build_guidance_message(
                what=f"'{name_tok.value}' is a reserved keyword.",
                why="List transform item names must be identifiers that are not keywords.",
                fix="Choose a different name.",
                example=f"let result is {op_name} numbers with item as value:\\n  value",
            ),
            line=name_tok.line,
            column=name_tok.column,
        )
    return name_tok.value


def _expect_ident_value(parser, value: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        raise Namel3ssError(f"Expected '{value}'", line=tok.line, column=tok.column)
    parser._advance()


__all__ = [
    "looks_like_list_aggregate_expr",
    "looks_like_list_reduce_expr",
    "looks_like_list_transform_expr",
    "looks_like_list_expression",
    "looks_like_map_expression",
    "parse_list_aggregate_expr",
    "parse_list_reduce_expr",
    "parse_list_transform_expr",
    "parse_list_expression",
    "parse_map_expression",
]
