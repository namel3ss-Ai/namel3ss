from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core.helpers import parse_reference_name
from namel3ss.parser.decl.page_chat import parse_chat_block
from namel3ss.parser.decl.page_chart import parse_chart_block, parse_chart_header
from namel3ss.parser.decl.page_form import parse_form_block
from namel3ss.parser.decl.page_list import parse_list_block
from namel3ss.parser.decl.page_table import parse_table_block


def parse_view_item(parser, tok) -> ast.ViewItem:
    parser._advance()
    of_tok = parser._expect("IDENT", "Expected 'of' after view")
    if of_tok.value != "of":
        raise Namel3ssError("Expected 'of' after view", line=of_tok.line, column=of_tok.column)
    record_name = parse_reference_name(parser, context="record")
    return ast.ViewItem(record_name=record_name, line=tok.line, column=tok.column)


def parse_title_item(parser, tok) -> ast.TitleItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'title'")
    value_tok = parser._expect("STRING", "Expected title string")
    return ast.TitleItem(value=value_tok.value, line=tok.line, column=tok.column)


def parse_text_item(parser, tok) -> ast.TextItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'text'")
    value_tok = parser._expect("STRING", "Expected text string")
    return ast.TextItem(value=value_tok.value, line=tok.line, column=tok.column)


def parse_form_item(parser, tok) -> ast.FormItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'form'")
    record_name = parse_reference_name(parser, context="record")
    if parser._match("COLON"):
        groups, fields = parse_form_block(parser)
        return ast.FormItem(
            record_name=record_name,
            groups=groups,
            fields=fields,
            line=tok.line,
            column=tok.column,
        )
    return ast.FormItem(record_name=record_name, line=tok.line, column=tok.column)


def parse_table_item(parser, tok) -> ast.TableItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'table'")
    record_name = parse_reference_name(parser, context="record")
    if parser._match("COLON"):
        columns, empty_text, sort, pagination, selection, row_actions = parse_table_block(parser)
        return ast.TableItem(
            record_name=record_name,
            columns=columns,
            empty_text=empty_text,
            sort=sort,
            pagination=pagination,
            selection=selection,
            row_actions=row_actions,
            line=tok.line,
            column=tok.column,
        )
    return ast.TableItem(record_name=record_name, line=tok.line, column=tok.column)


def parse_list_item(parser, tok) -> ast.ListItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'list'")
    record_name = parse_reference_name(parser, context="record")
    if parser._match("COLON"):
        variant, item, empty_text, selection, actions = parse_list_block(parser)
        return ast.ListItem(
            record_name=record_name,
            variant=variant,
            item=item,
            empty_text=empty_text,
            selection=selection,
            actions=actions,
            line=tok.line,
            column=tok.column,
        )
    return ast.ListItem(record_name=record_name, line=tok.line, column=tok.column)


def parse_chart_item(parser, tok) -> ast.ChartItem:
    parser._advance()
    record_name, source = parse_chart_header(parser)
    chart_type = None
    x = None
    y = None
    explain = None
    if parser._match("COLON"):
        chart_type, x, y, explain = parse_chart_block(parser)
    return ast.ChartItem(
        record_name=record_name,
        source=source,
        chart_type=chart_type,
        x=x,
        y=y,
        explain=explain,
        line=tok.line,
        column=tok.column,
    )


def parse_use_ui_pack_item(parser, tok) -> ast.UseUIPackItem:
    parser._advance()
    kind_tok = parser._current()
    if kind_tok.type != "IDENT" or kind_tok.value != "ui_pack":
        raise Namel3ssError("Pages only support 'use ui_pack'", line=kind_tok.line, column=kind_tok.column)
    parser._advance()
    pack_tok = parser._expect("STRING", "Expected ui_pack name string")
    frag_tok = parser._current()
    if frag_tok.type != "IDENT" or frag_tok.value != "fragment":
        raise Namel3ssError("Expected fragment name for ui_pack use", line=frag_tok.line, column=frag_tok.column)
    parser._advance()
    name_tok = parser._expect("STRING", "Expected fragment name string")
    return ast.UseUIPackItem(
        pack_name=pack_tok.value,
        fragment_name=name_tok.value,
        line=tok.line,
        column=tok.column,
    )


def parse_chat_item(parser, tok) -> ast.ChatItem:
    parser._advance()
    parser._expect("COLON", "Expected ':' after chat")
    children = parse_chat_block(parser)
    return ast.ChatItem(children=children, line=tok.line, column=tok.column)


def parse_tabs_item(parser, tok, parse_block) -> ast.TabsItem:
    parser._advance()
    parser._expect("COLON", "Expected ':' after tabs")
    tabs, default_label = _parse_tabs_block(parser, parse_block)
    return ast.TabsItem(tabs=tabs, default=default_label, line=tok.line, column=tok.column)


def _parse_tabs_block(parser, parse_block) -> tuple[List[ast.TabItem], str | None]:
    parser._expect("NEWLINE", "Expected newline after tabs")
    parser._expect("INDENT", "Expected indented tabs body")
    tabs: List[ast.TabItem] = []
    seen_labels: set[str] = set()
    default_label: str | None = None
    default_line: int | None = None
    default_column: int | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "default":
            if default_label is not None:
                raise Namel3ssError("Default tab is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after default")
            value_tok = parser._expect("STRING", "Expected default tab label string")
            default_label = value_tok.value
            default_line = value_tok.line
            default_column = value_tok.column
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "tab":
            parser._advance()
            label_tok = parser._expect("STRING", "Expected tab label string")
            if label_tok.value in seen_labels:
                raise Namel3ssError(
                    f"Tab label '{label_tok.value}' is duplicated",
                    line=label_tok.line,
                    column=label_tok.column,
                )
            seen_labels.add(label_tok.value)
            parser._expect("COLON", "Expected ':' after tab label")
            children = parse_block(parser, columns_only=False, allow_tabs=False)
            tabs.append(ast.TabItem(label=label_tok.value, children=children, line=tok.line, column=tok.column))
            continue
        raise Namel3ssError("Tabs may only contain tab entries", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of tabs body")
    if not tabs:
        tok = parser._current()
        raise Namel3ssError("Tabs block has no tabs", line=tok.line, column=tok.column)
    if default_label is not None and default_label not in seen_labels:
        raise Namel3ssError(
            f"Default tab '{default_label}' does not match any tab",
            line=default_line,
            column=default_column,
        )
    return tabs, default_label


__all__ = [
    "parse_chart_item",
    "parse_chat_item",
    "parse_form_item",
    "parse_list_item",
    "parse_table_item",
    "parse_tabs_item",
    "parse_text_item",
    "parse_title_item",
    "parse_use_ui_pack_item",
    "parse_view_item",
]
