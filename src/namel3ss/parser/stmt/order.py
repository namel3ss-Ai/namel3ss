from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.stmt.common import parse_target


_ORDER_EXAMPLE = "order state.items by score from highest to lowest"
_KEEP_EXAMPLE = "keep first 5 items"


def parse_order_list(parser) -> ast.OrderList:
    order_tok = parser._advance()
    target = parse_target(parser)
    _expect_word(parser, "by", _ORDER_EXAMPLE)
    field_tok = parser._expect("IDENT", "Expected field name after 'by'")
    _expect_word(parser, "from", _ORDER_EXAMPLE)
    start_tok = parser._expect("IDENT", "Expected 'highest' or 'lowest' after 'from'")
    if start_tok.value not in {"highest", "lowest"}:
        raise Namel3ssError(_order_direction_message(), line=start_tok.line, column=start_tok.column)
    parser._expect("TO", "Expected 'to' after order direction")
    end_tok = parser._expect("IDENT", "Expected 'highest' or 'lowest' after 'to'")
    if end_tok.value not in {"highest", "lowest"}:
        raise Namel3ssError(_order_direction_message(), line=end_tok.line, column=end_tok.column)
    if start_tok.value == end_tok.value:
        raise Namel3ssError(_order_direction_message(), line=end_tok.line, column=end_tok.column)
    direction = "desc" if start_tok.value == "highest" else "asc"
    return ast.OrderList(
        target=target,
        field=field_tok.value,
        direction=direction,
        line=order_tok.line,
        column=order_tok.column,
    )


def parse_keep_first(parser) -> ast.KeepFirst:
    keep_tok = parser._advance()
    _expect_word(parser, "first", _KEEP_EXAMPLE)
    count_expr = parser._parse_expression()
    _expect_word(parser, "items", _KEEP_EXAMPLE)
    return ast.KeepFirst(count=count_expr, line=keep_tok.line, column=keep_tok.column)


def _expect_word(parser, value: str, example: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Expected '{value}'.",
                why="This statement uses a fixed phrase.",
                fix=f"Use the full form: {example}",
                example=example,
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._advance()


def _order_direction_message() -> str:
    return build_guidance_message(
        what="Order direction must be highest to lowest or lowest to highest.",
        why="Ordering only supports those two fixed directions.",
        fix=f"Use one of: {_ORDER_EXAMPLE} or order state.items by score from lowest to highest",
        example=_ORDER_EXAMPLE,
    )


__all__ = ["parse_keep_first", "parse_order_list"]
