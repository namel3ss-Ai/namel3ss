from __future__ import annotations

from decimal import Decimal
from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_actions import parse_ui_action_body
from namel3ss.parser.decl.page_common import _parse_number_value, _parse_string_value
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def parse_table_block(parser, *, allow_pattern_params: bool = False):
    parser._expect("NEWLINE", "Expected newline after table header")
    parser._expect("INDENT", "Expected indented table block")
    columns = None
    empty_text = None
    sort = None
    pagination = None
    selection = None
    row_actions = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "columns":
            if columns is not None:
                raise Namel3ssError("Columns block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            columns = _parse_table_columns(parser)
            continue
        if tok.type == "IDENT" and tok.value == "empty_state":
            if empty_text is not None:
                raise Namel3ssError("Empty state is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            empty_text = _parse_empty_state_block(parser, allow_pattern_params=allow_pattern_params)
            continue
        if tok.type == "IDENT" and tok.value == "empty_text":
            if empty_text is not None:
                raise Namel3ssError("Empty state is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after empty_text")
            empty_text = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="empty state")
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "sort":
            if sort is not None:
                raise Namel3ssError("Sort block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            sort = _parse_table_sort(parser, tok.line, tok.column)
            continue
        if tok.type == "IDENT" and tok.value == "pagination":
            if pagination is not None:
                raise Namel3ssError("Pagination block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            pagination = _parse_table_pagination(parser, tok.line, tok.column, allow_pattern_params=allow_pattern_params)
            continue
        if tok.type == "IDENT" and tok.value == "selection":
            if selection is not None:
                raise Namel3ssError("Selection is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after selection")
            value_tok = parser._current()
            if value_tok.type not in {"STRING", "IDENT"}:
                raise Namel3ssError(
                    "Selection must be 'none', 'single', or 'multi'",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            parser._advance()
            selection_value = str(value_tok.value).lower()
            if selection_value not in {"none", "single", "multi"}:
                raise Namel3ssError(
                    "Selection must be 'none', 'single', or 'multi'",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            selection = selection_value
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "row_actions":
            if row_actions is not None:
                raise Namel3ssError("Row actions block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            row_actions = _parse_row_actions_block(parser, allow_pattern_params=allow_pattern_params)
            continue
        raise Namel3ssError(
            f"Unknown table setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of table block")
    return columns, empty_text, sort, pagination, selection, row_actions


def _parse_table_columns(parser):
    parser._expect("COLON", "Expected ':' after columns")
    parser._expect("NEWLINE", "Expected newline after columns")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Columns block has no entries", line=tok.line, column=tok.column)
    directives: List[ast.TableColumnDirective] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "include":
            parser._advance()
            name = _parse_table_field_name(parser)
            directives.append(
                ast.TableColumnDirective(kind="include", name=name, label=None, line=tok.line, column=tok.column)
            )
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "exclude":
            parser._advance()
            name = _parse_table_field_name(parser)
            directives.append(
                ast.TableColumnDirective(kind="exclude", name=name, label=None, line=tok.line, column=tok.column)
            )
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "label":
            parser._advance()
            name = _parse_table_field_name(parser)
            parser._expect("IS", "Expected 'is' after label")
            label_tok = parser._expect("STRING", "Expected label string")
            directives.append(
                ast.TableColumnDirective(
                    kind="label",
                    name=name,
                    label=label_tok.value,
                    line=tok.line,
                    column=tok.column,
                )
            )
            if parser._match("NEWLINE"):
                continue
            continue
        raise Namel3ssError(
            f"Unknown columns setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of columns block")
    if not directives:
        raise Namel3ssError("Columns block has no entries", line=parser._current().line, column=parser._current().column)
    return directives


def _parse_empty_state_block(parser, *, allow_pattern_params: bool = False) -> str:
    parser._expect("COLON", "Expected ':' after empty_state")
    parser._expect("NEWLINE", "Expected newline after empty_state")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Empty state block has no entries", line=tok.line, column=tok.column)
    text_value: str | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "TEXT":
            raise Namel3ssError("Empty state only supports text", line=tok.line, column=tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'text'")
        value_tok = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="empty state")
        if text_value is not None:
            raise Namel3ssError("Empty state only supports one text entry", line=tok.line, column=tok.column)
        text_value = value_tok
        if parser._match("NEWLINE"):
            continue
    parser._expect("DEDENT", "Expected end of empty_state block")
    if text_value is None:
        tok = parser._current()
        raise Namel3ssError("Empty state block has no entries", line=tok.line, column=tok.column)
    return text_value


def _parse_table_sort(parser, line: int, column: int) -> ast.TableSort:
    parser._expect("COLON", "Expected ':' after sort")
    parser._expect("NEWLINE", "Expected newline after sort")
    parser._expect("INDENT", "Expected indented sort block")
    by = None
    order = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "by":
            parser._advance()
            parser._expect("IS", "Expected 'is' after by")
            by = _parse_table_field_name(parser)
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "order":
            parser._advance()
            parser._expect("IS", "Expected 'is' after order")
            value_tok = parser._current()
            if value_tok.type not in {"STRING", "IDENT"}:
                raise Namel3ssError("Sort order must be 'asc' or 'desc'", line=value_tok.line, column=value_tok.column)
            parser._advance()
            order_value = str(value_tok.value).lower()
            if order_value not in {"asc", "desc"}:
                raise Namel3ssError("Sort order must be 'asc' or 'desc'", line=value_tok.line, column=value_tok.column)
            order = order_value
            if parser._match("NEWLINE"):
                continue
            continue
        raise Namel3ssError(
            f"Unknown sort setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of sort block")
    if by is None:
        raise Namel3ssError("Sort block requires 'by is <field>'", line=line, column=column)
    if order is None:
        raise Namel3ssError("Sort block requires 'order is \"asc\"|\"desc\"'", line=line, column=column)
    return ast.TableSort(by=by, order=order, line=line, column=column)


def _parse_table_pagination(parser, line: int, column: int, *, allow_pattern_params: bool) -> ast.TablePagination:
    parser._expect("COLON", "Expected ':' after pagination")
    parser._expect("NEWLINE", "Expected newline after pagination")
    parser._expect("INDENT", "Expected indented pagination block")
    page_size = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "page_size":
            parser._advance()
            parser._expect("IS", "Expected 'is' after page_size")
            page_size = _parse_number_value(parser, allow_pattern_params=allow_pattern_params)
            if isinstance(page_size, (int, float, Decimal)):
                if page_size <= 0 or page_size != int(page_size):
                    raise Namel3ssError("page_size must be a positive integer", line=tok.line, column=tok.column)
                page_size = int(page_size)
            if parser._match("NEWLINE"):
                continue
            continue
        raise Namel3ssError(
            f"Unknown pagination setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of pagination block")
    if page_size is None:
        raise Namel3ssError("Pagination block requires page_size", line=line, column=column)
    return ast.TablePagination(page_size=page_size, line=line, column=column)


def _parse_row_actions_block(parser, *, allow_pattern_params: bool) -> List[ast.TableRowAction]:
    parser._expect("COLON", "Expected ':' after row_actions")
    parser._expect("NEWLINE", "Expected newline after row_actions")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Row actions block has no entries", line=tok.line, column=tok.column)
    actions: List[ast.TableRowAction] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT" or tok.value != "row_action":
            raise Namel3ssError("Row actions may only contain row_action entries", line=tok.line, column=tok.column)
        parser._advance()
        label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="row action label")
        if parser._match("CALLS"):
            raise Namel3ssError(
                'Row actions must use a block. Use: row_action "Label": NEWLINE indent calls flow "demo"',
                line=tok.line,
                column=tok.column,
            )
        parser._expect("COLON", "Expected ':' after row_action label")
        parser._expect("NEWLINE", "Expected newline after row_action header")
        parser._expect("INDENT", "Expected indented row_action body")
        kind = None
        flow_name = None
        target = None
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            kind, flow_name, target = parse_ui_action_body(
                parser,
                entry_label="Row action",
                allow_pattern_params=allow_pattern_params,
            )
            if parser._match("NEWLINE"):
                continue
            break
        parser._expect("DEDENT", "Expected end of row_action body")
        if kind is None:
            raise Namel3ssError("Row action body must include 'calls flow \"<name>\"'", line=tok.line, column=tok.column)
        if kind == "call_flow" and flow_name is None:
            raise Namel3ssError("Row action body must include 'calls flow \"<name>\"'", line=tok.line, column=tok.column)
        if kind != "call_flow" and target is None:
            raise Namel3ssError("Row action body must include a modal or drawer target", line=tok.line, column=tok.column)
        actions.append(
            ast.TableRowAction(
                label=label,
                flow_name=flow_name,
                kind=kind,
                target=target,
                line=tok.line,
                column=tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of row_actions block")
    if not actions:
        raise Namel3ssError("Row actions block has no entries", line=parser._current().line, column=parser._current().column)
    return actions


def _parse_table_field_name(parser) -> str:
    tok = parser._current()
    if tok.type in {"STRING", "IDENT"}:
        parser._advance()
        return str(tok.value)
    if isinstance(tok.value, str) and is_keyword(tok.value):
        guidance, details = reserved_identifier_diagnostic(tok.value)
        raise Namel3ssError(guidance, line=tok.line, column=tok.column, details=details)
    raise Namel3ssError("Expected field name", line=tok.line, column=tok.column)


__all__ = ["parse_table_block"]
