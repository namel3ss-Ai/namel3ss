from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


_SIDEBAR_GRAMMAR = 'nav_sidebar must declare one or more items: item "<label>" goes_to "<PageName>".'
_ITEM_GRAMMAR = 'Navigation items must use: item "<label>" goes_to "<PageName>".'


def parse_navigation_sidebar(parser) -> ast.NavigationSidebar:
    header = parser._expect("IDENT", "Expected 'nav_sidebar'")
    if header.value != "nav_sidebar":
        raise Namel3ssError(_SIDEBAR_GRAMMAR, line=header.line, column=header.column)
    parser._expect("COLON", "Expected ':' after nav_sidebar")
    parser._expect("NEWLINE", "Expected newline after nav_sidebar header")
    parser._expect("INDENT", "Expected indented nav_sidebar block")
    items: list[ast.NavigationItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        items.append(_parse_navigation_item(parser))
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of nav_sidebar block")
    if not items:
        raise Namel3ssError(_SIDEBAR_GRAMMAR, line=header.line, column=header.column)
    return ast.NavigationSidebar(items=items, line=header.line, column=header.column)


def _parse_navigation_item(parser) -> ast.NavigationItem:
    item_tok = parser._expect("IDENT", "Expected nav item")
    if item_tok.value != "item":
        raise Namel3ssError(_ITEM_GRAMMAR, line=item_tok.line, column=item_tok.column)
    label_tok = parser._expect("STRING", "Expected nav item label string")
    goes_to = parser._expect("IDENT", "Expected 'goes_to' after nav item label")
    if goes_to.value != "goes_to":
        raise Namel3ssError(_ITEM_GRAMMAR, line=goes_to.line, column=goes_to.column)
    page_tok = parser._expect("STRING", "Expected nav target page string")
    if parser._current().type not in {"NEWLINE", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(_ITEM_GRAMMAR, line=extra.line, column=extra.column)
    return ast.NavigationItem(
        label=label_tok.value,
        page_name=page_tok.value,
        line=item_tok.line,
        column=item_tok.column,
    )


__all__ = ["parse_navigation_sidebar"]
