from __future__ import annotations

from decimal import Decimal

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _parse_show_when_clause,
    _parse_string_value,
    _parse_visibility_clause,
    _validate_visibility_combo,
)
from namel3ss.parser.decl.visibility_expr import parse_visibility_expression


def is_layout_grid_header(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "grid":
        return False
    next_tok = _peek(parser, 1)
    if next_tok.type != "IDENT" or next_tok.value != "columns":
        return False
    next_next = _peek(parser, 2)
    return next_next.type == "IS"


def is_layout_drawer_header(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "drawer":
        return False
    next_tok = _peek(parser, 1)
    return next_tok.type == "TITLE"


def parse_stack_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.LayoutStack:
    return _parse_layout_container(
        parser,
        tok,
        parse_block,
        label="stack",
        build=lambda children, **kwargs: ast.LayoutStack(children=children, direction="vertical", **kwargs),
        allow_pattern_params=allow_pattern_params,
    )


def parse_row_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.PageItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after row")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    if all(isinstance(child, ast.ColumnItem) for child in children):
        return ast.RowItem(
            children=children,
            visibility=visibility,
            visibility_rule=visibility_rule,
            show_when=show_when,
            debug_only=debug_only,
            line=tok.line,
            column=tok.column,
        )
    return ast.LayoutRow(
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_col_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.LayoutColumn:
    return _parse_layout_container(
        parser,
        tok,
        parse_block,
        label="col",
        build=lambda children, **kwargs: ast.LayoutColumn(children=children, **kwargs),
        allow_pattern_params=allow_pattern_params,
    )


def parse_grid_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.LayoutGrid:
    parser._advance()
    columns_tok = parser._expect("IDENT", "Expected 'columns' after grid")
    if columns_tok.value != "columns":
        raise Namel3ssError("Grid must declare columns.", line=columns_tok.line, column=columns_tok.column)
    parser._expect("IS", "Expected 'is' after grid columns")
    number_tok = parser._expect("NUMBER", "Expected grid column count")
    raw_value = number_tok.value
    if isinstance(raw_value, Decimal):
        if raw_value != raw_value.to_integral_value():
            raise Namel3ssError("Grid columns must be a positive integer.", line=number_tok.line, column=number_tok.column)
        columns = int(raw_value)
    else:
        columns = int(raw_value)
        if columns != raw_value:
            raise Namel3ssError("Grid columns must be a positive integer.", line=number_tok.line, column=number_tok.column)
    if columns <= 0:
        raise Namel3ssError("Grid columns must be a positive integer.", line=number_tok.line, column=number_tok.column)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after grid columns")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.LayoutGrid(
        columns=columns,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_sidebar_layout_item(parser, tok, parse_page_item, *, allow_pattern_params: bool = False) -> ast.SidebarLayout:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after sidebar_layout")
    parser._expect("NEWLINE", "Expected newline after sidebar_layout")
    parser._expect("INDENT", "Expected indented sidebar_layout block")
    sidebar_items: list[ast.PageItem] | None = None
    main_items: list[ast.PageItem] | None = None
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        slot_tok = parser._expect("IDENT", "Expected sidebar or main block")
        slot_name = str(slot_tok.value)
        if slot_name not in {"sidebar", "main"}:
            raise Namel3ssError(
                "sidebar_layout only supports sidebar and main blocks.",
                line=slot_tok.line,
                column=slot_tok.column,
            )
        if slot_name in seen:
            raise Namel3ssError(
                f"{slot_name} is already declared.",
                line=slot_tok.line,
                column=slot_tok.column,
            )
        parser._expect("COLON", f"Expected ':' after {slot_name}")
        items = _parse_slot_items(parser, slot_name, parse_page_item, allow_pattern_params=allow_pattern_params)
        if slot_name == "sidebar":
            sidebar_items = items
        else:
            main_items = items
        seen.add(slot_name)
    parser._expect("DEDENT", "Expected end of sidebar_layout block")
    if sidebar_items is None or main_items is None:
        raise Namel3ssError(
            "sidebar_layout must declare both sidebar and main blocks.",
            line=tok.line,
            column=tok.column,
        )
    return ast.SidebarLayout(
        sidebar=sidebar_items,
        main=main_items,
        visibility=visibility,
        visibility_rule=None,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_drawer_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.LayoutDrawer:
    parser._advance()
    parser._expect("TITLE", "Expected 'title' after drawer")
    parser._expect("IS", "Expected 'is' after title")
    title = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="drawer title")
    parser._expect("WHEN", "Expected 'when' after drawer title")
    parser._match("IS")
    condition = parse_visibility_expression(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after drawer condition")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    return ast.LayoutDrawer(
        title=title,
        children=children,
        visibility_rule=visibility_rule,
        show_when=condition,
        line=tok.line,
        column=tok.column,
    )


def parse_sticky_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.LayoutSticky:
    parser._advance()
    pos_tok = parser._expect("IDENT", "Expected 'top' or 'bottom' after sticky")
    position = str(pos_tok.value)
    if position not in {"top", "bottom"}:
        raise Namel3ssError(
            "Sticky blocks must be 'top' or 'bottom'.",
            line=pos_tok.line,
            column=pos_tok.column,
        )
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", f"Expected ':' after sticky {position}")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.LayoutSticky(
        position=position,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_layout_container(
    parser,
    tok,
    parse_block,
    *,
    label: str,
    build,
    allow_pattern_params: bool,
):
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", f"Expected ':' after {label}")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return build(
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_slot_items(parser, slot_name: str, parse_page_item, *, allow_pattern_params: bool) -> list[ast.PageItem]:
    parser._expect("NEWLINE", f"Expected newline after {slot_name}")
    if not parser._match("INDENT"):
        return []
    items: list[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if parser._current().type == "IDENT" and parser._current().value == "only":
            tok = parser._current()
            raise Namel3ssError(
                "sidebar_layout slots do not support only-when rules.",
                line=tok.line,
                column=tok.column,
            )
        parsed = parse_page_item(
            parser,
            allow_tabs=False,
            allow_overlays=False,
            allow_pattern_params=allow_pattern_params,
        )
        if isinstance(parsed, list):
            items.extend(parsed)
        else:
            items.append(parsed)
    parser._expect("DEDENT", f"Expected end of {slot_name} block")
    return items


def _peek(parser, offset: int):
    index = parser.position + offset
    if index >= len(parser.tokens):
        return parser._current()
    return parser.tokens[index]


__all__ = [
    "is_layout_drawer_header",
    "is_layout_grid_header",
    "parse_col_item",
    "parse_drawer_item",
    "parse_grid_item",
    "parse_row_item",
    "parse_sidebar_layout_item",
    "parse_stack_item",
    "parse_sticky_item",
]
