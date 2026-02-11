from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.ui.slider_decl import parse_slider_item
from namel3ss.parser.ui.tooltip_decl import parse_tooltip_item
from namel3ss.parser.decl.page_common import _is_visibility_rule_start, _parse_visibility_rule_line

from . import actions as actions_mod
from . import containers as containers_mod
from . import custom_component as custom_component_mod
from . import media as media_mod
from . import numbers as numbers_mod
from . import polish as polish_mod
from . import rag as rag_mod
from . import responsive as responsive_mod
from . import story as story_mod
from . import conditional_blocks as conditional_mod
from . import layout_blocks as layout_mod
from . import views as views_mod


def _parse_block(
    parser,
    *,
    columns_only: bool = False,
    allow_tabs: bool = False,
    allow_overlays: bool = False,
    allow_pattern_params: bool = False,
) -> tuple[List[ast.PageItem], ast.VisibilityRule | None]:
    parser._expect("NEWLINE", "Expected newline after header")
    parser._expect("INDENT", "Expected indented block")
    items: List[ast.PageItem] = []
    visibility_rule: ast.VisibilityRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                tok = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=tok.line,
                    column=tok.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        if columns_only and parser._current().type != "COLUMN":
            tok = parser._current()
            raise Namel3ssError("Rows may only contain columns", line=tok.line, column=tok.column)
        parsed = parse_page_item(
            parser,
            allow_tabs=allow_tabs,
            allow_overlays=allow_overlays,
            allow_pattern_params=allow_pattern_params,
        )
        if isinstance(parsed, list):
            items.extend(parsed)
        else:
            items.append(parsed)
    parser._expect("DEDENT", "Expected end of block")
    return items, visibility_rule


def parse_page_item(
    parser,
    *,
    allow_tabs: bool = False,
    allow_overlays: bool = False,
    allow_pattern_params: bool = False,
) -> ast.PageItem | list[ast.PageItem]:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == "purpose":
        raise Namel3ssError("Purpose must be declared at the page root", line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "nav_sidebar":
        raise Namel3ssError("nav_sidebar must be declared at the page root", line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "rag_ui":
        raise Namel3ssError("rag_ui must be declared at the page root", line=tok.line, column=tok.column)
    if tok.type == "IF":
        return conditional_mod.parse_if_block(parser, tok, parse_page_item, allow_pattern_params=allow_pattern_params)
    if tok.type == "ELSE":
        raise Namel3ssError("Else must follow an if block", line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "compose":
        return actions_mod.parse_compose_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "story":
        return story_mod.parse_story_item(parser, allow_pattern_params=allow_pattern_params)
    if tok.value == "number" and tok.type in {"IDENT", "TYPE_NUMBER"}:
        return numbers_mod.parse_number_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "view":
        return views_mod.parse_view_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "TITLE":
        return views_mod.parse_title_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "TEXT":
        return views_mod.parse_text_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "upload":
        return views_mod.parse_upload_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "loading":
        return polish_mod.parse_loading_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "snackbar":
        return polish_mod.parse_snackbar_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "icon":
        return polish_mod.parse_icon_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "lightbox":
        return polish_mod.parse_lightbox_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "FORM":
        return views_mod.parse_form_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "TABLE":
        return views_mod.parse_table_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "show":
        return views_mod.parse_show_items(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "list":
        return views_mod.parse_list_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "chart":
        return views_mod.parse_chart_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "use":
        return views_mod.parse_use_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "include":
        return views_mod.parse_include_item(parser, tok)
    if tok.type == "IDENT" and tok.value == "chat":
        return views_mod.parse_chat_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "citations":
        return rag_mod.parse_citation_chips_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "source_preview":
        return rag_mod.parse_source_preview_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "trust_indicator":
        return rag_mod.parse_trust_indicator_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "scope_selector":
        return rag_mod.parse_scope_selector_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value in {"messages", "composer", "thinking"}:
        raise Namel3ssError("Chat elements must be inside a chat block", line=tok.line, column=tok.column)
    if tok.type == "MEMORY":
        raise Namel3ssError("Chat elements must be inside a chat block", line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "tabs":
        if not allow_tabs:
            raise Namel3ssError("Tabs may only appear at the page root", line=tok.line, column=tok.column)
        return views_mod.parse_tabs_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "tab":
        raise Namel3ssError("Tab entries must be inside a tabs block", line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "modal":
        return actions_mod.parse_modal_item(
            parser,
            tok,
            _parse_block,
            allow_overlays=allow_overlays,
            allow_pattern_params=allow_pattern_params,
        )
    if tok.type == "IDENT" and tok.value == "drawer":
        if layout_mod.is_layout_drawer_header(parser):
            return layout_mod.parse_drawer_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
        return actions_mod.parse_drawer_item(
            parser,
            tok,
            _parse_block,
            allow_overlays=allow_overlays,
            allow_pattern_params=allow_pattern_params,
        )
    if tok.type == "BUTTON":
        return actions_mod.parse_button_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "slider":
        return parse_slider_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "tooltip":
        return parse_tooltip_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "INPUT":
        return actions_mod.parse_text_input_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "link":
        return actions_mod.parse_link_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "SECTION":
        return containers_mod.parse_section_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "card_group":
        return actions_mod.parse_card_group_item(parser, tok, parse_page_item, allow_pattern_params=allow_pattern_params)
    if tok.type == "CARD":
        return actions_mod.parse_card_item(parser, tok, parse_page_item, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "stack":
        return layout_mod.parse_stack_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "ROW":
        return layout_mod.parse_row_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "COLUMN":
        return containers_mod.parse_column_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "col":
        return layout_mod.parse_col_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "grid":
        if layout_mod.is_layout_grid_header(parser):
            return layout_mod.parse_grid_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
        return responsive_mod.parse_grid_item(parser, tok, parse_page_item, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "sidebar_layout":
        return layout_mod.parse_sidebar_layout_item(parser, tok, parse_page_item, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "sticky":
        return layout_mod.parse_sticky_item(parser, tok, _parse_block, allow_pattern_params=allow_pattern_params)
    if tok.type == "DIVIDER":
        return containers_mod.parse_divider_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IMAGE":
        return media_mod.parse_image_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if getattr(tok, "value", None) == "story":
        return story_mod.parse_story_item(parser, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT":
        return custom_component_mod.parse_custom_component_item(parser, tok, allow_pattern_params=allow_pattern_params)
    raise Namel3ssError(
        f"Pages are declarative; unexpected item '{tok.type.lower()}'",
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_page_item"]
