from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _is_debug_only_start,
    _is_diagnostics_start,
    _match_ident_value,
    _parse_debug_only_line,
    _parse_diagnostics_line,
    _parse_visibility_clause,
    _reject_list_transforms,
)
from namel3ss.parser.decl.page_layout import flatten_page_layout, parse_page_layout_block
from namel3ss.parser.decl.page_items import parse_page_item
from namel3ss.parser.decl.page_status import parse_status_block


def parse_page(parser) -> ast.PageDecl:
    page_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected page name string")
    parser._expect("COLON", "Expected ':' after page name")
    requires_expr = None
    visibility = None
    if _match_ident_value(parser, "requires"):
        requires_expr = parser._parse_expression()
        _reject_list_transforms(requires_expr)
    visibility = _parse_visibility_clause(parser)
    parser._expect("NEWLINE", "Expected newline after page header")
    parser._expect("INDENT", "Expected indented page body")
    items: List[ast.PageItem] = []
    layout: ast.PageLayout | None = None
    purpose: str | None = None
    status_block: ast.StatusBlock | None = None
    debug_only: bool | str | None = None
    diagnostics: bool | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _is_debug_only_start(parser):
            if debug_only is not None:
                raise Namel3ssError("debug_only is already declared for this page", line=tok.line, column=tok.column)
            debug_only = _parse_debug_only_line(parser)
            parser._match("NEWLINE")
            continue
        if _is_diagnostics_start(parser):
            if diagnostics is not None:
                raise Namel3ssError("diagnostics is already declared for this page", line=tok.line, column=tok.column)
            diagnostics = _parse_diagnostics_line(parser)
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "purpose":
            if purpose is not None:
                raise Namel3ssError("Purpose is already declared for this page", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after purpose")
            value_tok = parser._expect("STRING", "Expected purpose string")
            purpose = value_tok.value
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "status":
            if status_block is not None:
                raise Namel3ssError("Status is already declared for this page", line=tok.line, column=tok.column)
            status_block = parse_status_block(parser)
            continue
        if tok.type == "IDENT" and tok.value == "layout":
            if layout is not None:
                raise Namel3ssError("Layout is already declared for this page", line=tok.line, column=tok.column)
            if items:
                raise Namel3ssError(
                    "Pages with layout cannot declare top-level items outside layout.",
                    line=tok.line,
                    column=tok.column,
                )
            layout = parse_page_layout_block(parser)
            continue
        if layout is not None:
            raise Namel3ssError(
                "Pages with layout cannot declare top-level items outside layout.",
                line=tok.line,
                column=tok.column,
            )
        parsed = parse_page_item(parser, allow_tabs=True, allow_overlays=True)
        if isinstance(parsed, list):
            items.extend(parsed)
        else:
            items.append(parsed)
    parser._expect("DEDENT", "Expected end of page body")
    page_items = flatten_page_layout(layout) if layout is not None else items
    return ast.PageDecl(
        name=name_tok.value,
        items=page_items,
        layout=layout,
        requires=requires_expr,
        visibility=visibility,
        purpose=purpose,
        status=status_block,
        debug_only=debug_only,
        diagnostics=diagnostics,
        line=page_tok.line,
        column=page_tok.column,
    )


__all__ = ["parse_page"]
