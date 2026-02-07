from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_chat import parse_chat_block
from namel3ss.parser.decl.page_chart import parse_chart_block, parse_chart_header
from namel3ss.parser.decl.page_common import (
    _is_param_ref,
    _parse_debug_only_clause,
    _match_ident_value,
    _parse_boolean_value,
    _parse_param_ref,
    _parse_reference_name_value,
    _parse_state_path_value,
    _parse_state_path_value_relaxed,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _parse_visibility_rule_line,
    _is_visibility_rule_start,
    _validate_visibility_combo,
)
from namel3ss.parser.decl.page_form import parse_form_block
from namel3ss.parser.decl.page_list import parse_list_block
from namel3ss.parser.decl.page_table import parse_table_block
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic

from .tabs import parse_tabs_item
from .use import parse_use_item


def parse_view_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ViewItem:
    parser._advance()
    of_tok = parser._expect("IDENT", "Expected 'of' after view")
    if of_tok.value != "of":
        raise Namel3ssError("Expected 'of' after view", line=of_tok.line, column=of_tok.column)
    record_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="record")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ViewItem(
        record_name=record_name,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_title_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.TitleItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'title'")
    value = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="title")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.TitleItem(
        value=value,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_text_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.TextItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'text'")
    value = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="text")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.TextItem(
        value=value,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_upload_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.UploadItem:
    parser._advance()
    if allow_pattern_params and _is_param_ref(parser):
        name = _parse_param_ref(parser)
    else:
        name_tok = parser._expect("IDENT", "Expected upload name")
        if is_keyword(name_tok.value) and not getattr(name_tok, "escaped", False):
            guidance, details = reserved_identifier_diagnostic(name_tok.value)
            raise Namel3ssError(guidance, line=name_tok.line, column=name_tok.column, details=details)
        name = name_tok.value
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = None
    accept = None
    multiple = None
    if parser._match("COLON"):
        parser._expect("NEWLINE", "Expected newline after upload header")
        parser._expect("INDENT", "Expected indented upload block")
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            entry_tok = parser._current()
            if _is_visibility_rule_start(parser):
                if visibility_rule is not None:
                    raise Namel3ssError("Visibility blocks may only declare one only-when rule.", line=entry_tok.line, column=entry_tok.column)
                visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
                parser._match("NEWLINE")
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "accept":
                if accept is not None:
                    raise Namel3ssError("Accept is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after accept")
                accept = _parse_upload_accept_list(parser)
                if parser._match("NEWLINE"):
                    continue
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "multiple":
                if multiple is not None:
                    raise Namel3ssError("Multiple is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after multiple")
                try:
                    multiple = _parse_boolean_value(parser, allow_pattern_params=allow_pattern_params)
                except Namel3ssError as err:
                    raise Namel3ssError(
                        "Multiple must be true or false",
                        line=err.line,
                        column=err.column,
                    ) from err
                if parser._match("NEWLINE"):
                    continue
                continue
            raise Namel3ssError(
                f"Unknown upload setting '{entry_tok.value}'",
                line=entry_tok.line,
                column=entry_tok.column,
            )
        parser._expect("DEDENT", "Expected end of upload block")
    else:
        visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.UploadItem(
        name=name,
        accept=accept,
        multiple=multiple,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_upload_accept_list(parser) -> list[str]:
    values: list[str] = []
    while True:
        tok = parser._current()
        if tok.type not in {"STRING", "IDENT"}:
            raise Namel3ssError("Accept must be a list of non-empty strings", line=tok.line, column=tok.column)
        parser._advance()
        value = str(tok.value).strip()
        if not value:
            raise Namel3ssError("Accept entries cannot be empty", line=tok.line, column=tok.column)
        values.append(value)
        if not parser._match("COMMA"):
            break
    if not values:
        tok = parser._current()
        raise Namel3ssError("Accept must be a list of non-empty strings", line=tok.line, column=tok.column)
    return values


def parse_form_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.FormItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'form'")
    record_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="record")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    if parser._match("COLON"):
        groups, fields, visibility_rule = parse_form_block(parser, allow_pattern_params=allow_pattern_params)
        _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
        return ast.FormItem(
            record_name=record_name,
            groups=groups,
            fields=fields,
            visibility=visibility,
            visibility_rule=visibility_rule,
            debug_only=debug_only,
            line=tok.line,
            column=tok.column,
        )
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.FormItem(
        record_name=record_name,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_table_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.TableItem:
    parser._advance()
    record_name, source = _parse_table_list_source(parser, allow_pattern_params=allow_pattern_params, label="table")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    if parser._match("COLON"):
        columns, empty_text, sort, pagination, selection, row_actions, visibility_rule = parse_table_block(
            parser,
            allow_pattern_params=allow_pattern_params,
        )
        _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
        return ast.TableItem(
            record_name=record_name,
            source=source,
            columns=columns,
            empty_text=empty_text,
            sort=sort,
            pagination=pagination,
            selection=selection,
            row_actions=row_actions,
            visibility=visibility,
            visibility_rule=visibility_rule,
            debug_only=debug_only,
            line=tok.line,
            column=tok.column,
        )
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.TableItem(
        record_name=record_name,
        source=source,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_list_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ListItem:
    parser._advance()
    record_name, source = _parse_table_list_source(parser, allow_pattern_params=allow_pattern_params, label="list")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    if parser._match("COLON"):
        variant, item, empty_text, selection, actions, visibility_rule = parse_list_block(
            parser,
            allow_pattern_params=allow_pattern_params,
        )
        _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
        return ast.ListItem(
            record_name=record_name,
            source=source,
            variant=variant,
            item=item,
            empty_text=empty_text,
            selection=selection,
            actions=actions,
            visibility=visibility,
            visibility_rule=visibility_rule,
            debug_only=debug_only,
            line=tok.line,
            column=tok.column,
        )
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ListItem(
        record_name=record_name,
        source=source,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_show_items(parser, tok, *, allow_pattern_params: bool = False) -> list[ast.PageItem]:
    parser._advance()
    items: list[ast.PageItem] = []
    last_item = _parse_show_entry(parser, allow_pattern_params=allow_pattern_params)
    items.append(last_item)
    if parser._match("NEWLINE"):
        if parser._match("INDENT"):
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                if _is_visibility_rule_start(parser):
                    if last_item is None:
                        tok_rule = parser._current()
                        raise Namel3ssError(
                            "Visibility rules must follow a show entry.",
                            line=tok_rule.line,
                            column=tok_rule.column,
                        )
                    if getattr(last_item, "visibility_rule", None) is not None:
                        tok_rule = parser._current()
                        raise Namel3ssError(
                            "Visibility blocks may only declare one only-when rule.",
                            line=tok_rule.line,
                            column=tok_rule.column,
                        )
                    rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
                    _validate_visibility_combo(getattr(last_item, "visibility", None), rule, line=rule.line, column=rule.column)
                    last_item.visibility_rule = rule
                    parser._match("NEWLINE")
                    continue
                last_item = _parse_show_entry(parser, allow_pattern_params=allow_pattern_params)
                items.append(last_item)
            parser._expect("DEDENT", "Expected end of show block")
    return items


def _parse_show_entry(parser, *, allow_pattern_params: bool) -> ast.PageItem:
    tok = parser._current()
    if tok.type == "TABLE":
        return parse_table_item(parser, tok, allow_pattern_params=allow_pattern_params)
    if tok.type == "IDENT" and tok.value == "list":
        return parse_list_item(parser, tok, allow_pattern_params=allow_pattern_params)
    raise Namel3ssError("Show only supports tables and lists", line=tok.line, column=tok.column)


def _parse_table_list_source(
    parser,
    *,
    allow_pattern_params: bool,
    label: str,
) -> tuple[str | None, ast.StatePath | ast.PatternParamRef | None]:
    if parser._match("IS"):
        record_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="record")
        return record_name, None
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == "from":
        parser._advance()
        parser._match("IS")
        if _match_ident_value(parser, "records") or _match_ident_value(parser, "record"):
            record_name = _parse_reference_name_value(
                parser,
                allow_pattern_params=allow_pattern_params,
                context="record",
            )
            return record_name, None
        source = _parse_state_path_value_relaxed(parser, allow_pattern_params=allow_pattern_params)
        return None, source
    raise Namel3ssError(
        f"{label.capitalize()} must use is <record> or from state.<path>",
        line=tok.line,
        column=tok.column,
    )


def parse_chart_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ChartItem:
    parser._advance()
    record_name, source = parse_chart_header(parser, allow_pattern_params=allow_pattern_params)
    chart_type = None
    x = None
    y = None
    explain = None
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    if parser._match("COLON"):
        chart_type, x, y, explain, visibility_rule = parse_chart_block(parser, allow_pattern_params=allow_pattern_params)
        _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    else:
        visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
        _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ChartItem(
        record_name=record_name,
        source=source,
        chart_type=chart_type,
        x=x,
        y=y,
        explain=explain,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_chat_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ChatItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after chat")
    children, visibility_rule = parse_chat_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ChatItem(
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


__all__ = [
    "parse_chart_item",
    "parse_chat_item",
    "parse_form_item",
    "parse_list_item",
    "parse_table_item",
    "parse_tabs_item",
    "parse_text_item",
    "parse_title_item",
    "parse_upload_item",
    "parse_use_item",
    "parse_view_item",
]
