from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER, PAGE_LAYOUT_SLOT_SET
from namel3ss.parser.decl.page_items import parse_page_item

_DIAGNOSTICS_BLOCK_NAME = "diagnostics"


def parse_page_layout_block(parser) -> ast.PageLayout:
    layout_tok = parser._current()
    parser._advance()
    parser._expect("COLON", "Expected ':' after layout")
    parser._expect("NEWLINE", "Expected newline after layout header")
    parser._expect("INDENT", "Expected indented layout block")
    slot_items: dict[str, list[ast.PageItem]] = {slot: [] for slot in PAGE_LAYOUT_SLOT_ORDER}
    diagnostics_items: list[ast.PageItem] = []
    seen: set[str] = set()

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        slot_tok = parser._expect("IDENT", "Expected layout slot name")
        slot_name = str(slot_tok.value)
        if slot_name == _DIAGNOSTICS_BLOCK_NAME:
            if slot_name in seen:
                raise Namel3ssError(
                    "Diagnostics block is already declared.",
                    line=slot_tok.line,
                    column=slot_tok.column,
                )
            parser._expect("COLON", "Expected ':' after diagnostics")
            diagnostics_items = _parse_layout_slot_items(parser, slot_name)
            seen.add(slot_name)
            continue
        if slot_name not in PAGE_LAYOUT_SLOT_SET:
            allowed = ", ".join(PAGE_LAYOUT_SLOT_ORDER)
            raise Namel3ssError(
                f'Unknown layout slot "{slot_name}". Allowed slots: {allowed}, diagnostics.',
                line=slot_tok.line,
                column=slot_tok.column,
            )
        if slot_name in seen:
            raise Namel3ssError(
                f'Layout slot "{slot_name}" is already declared.',
                line=slot_tok.line,
                column=slot_tok.column,
            )
        parser._expect("COLON", "Expected ':' after layout slot name")
        slot_items[slot_name] = _parse_layout_slot_items(parser, slot_name)
        seen.add(slot_name)

    parser._expect("DEDENT", "Expected end of layout block")
    if not seen:
        raise Namel3ssError("Layout block has no slots.", line=layout_tok.line, column=layout_tok.column)

    return ast.PageLayout(
        header=slot_items["header"],
        sidebar_left=slot_items["sidebar_left"],
        main=slot_items["main"],
        drawer_right=slot_items["drawer_right"],
        footer=slot_items["footer"],
        diagnostics=diagnostics_items,
        line=layout_tok.line,
        column=layout_tok.column,
    )


def flatten_page_layout(layout: ast.PageLayout | None) -> list[ast.PageItem]:
    if layout is None:
        return []
    items: list[ast.PageItem] = []
    for slot_name in PAGE_LAYOUT_SLOT_ORDER:
        values = getattr(layout, slot_name, None)
        if isinstance(values, list) and values:
            items.extend(values)
    return items


def _parse_layout_slot_items(parser, slot_name: str) -> list[ast.PageItem]:
    parser._expect("NEWLINE", f"Expected newline after {slot_name}")
    if not parser._match("INDENT"):
        # Empty slot declarations are explicit and deterministic.
        return []
    items: list[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        parsed = parse_page_item(parser, allow_tabs=True, allow_overlays=True)
        if isinstance(parsed, list):
            items.extend(parsed)
        else:
            items.append(parsed)
    parser._expect("DEDENT", f"Expected end of {slot_name} block")
    return items


__all__ = ["flatten_page_layout", "parse_page_layout_block"]
