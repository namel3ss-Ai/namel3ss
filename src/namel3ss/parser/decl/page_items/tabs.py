from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _is_visibility_rule_start,
    _parse_visibility_clause,
    _parse_show_when_clause,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)


def parse_tabs_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.TabsItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after tabs")
    tabs, default_label, visibility_rule = _parse_tabs_block(parser, parse_block, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.TabsItem(
        tabs=tabs,
        default=default_label,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_tabs_block(parser, parse_block, *, allow_pattern_params: bool) -> tuple[List[ast.TabItem], str | None, ast.VisibilityRule | None]:
    parser._expect("NEWLINE", "Expected newline after tabs")
    parser._expect("INDENT", "Expected indented tabs body")
    tabs: List[ast.TabItem] = []
    seen_labels: set[str] = set()
    default_label: str | None = None
    default_line: int | None = None
    default_column: int | None = None
    visibility_rule: ast.VisibilityRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                raise Namel3ssError("Visibility blocks may only declare one only-when rule.", line=tok.line, column=tok.column)
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
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
            visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
            show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
            parser._expect("COLON", "Expected ':' after tab label")
            children, tab_visibility_rule = parse_block(
                parser,
                columns_only=False,
                allow_tabs=False,
                allow_pattern_params=allow_pattern_params,
            )
            _validate_visibility_combo(visibility, tab_visibility_rule, line=tok.line, column=tok.column)
            tabs.append(
                ast.TabItem(
                    label=label_tok.value,
                    children=children,
                    visibility=visibility,
                    visibility_rule=tab_visibility_rule,
                    show_when=show_when,
                    line=tok.line,
                    column=tok.column,
                )
            )
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
    return tabs, default_label, visibility_rule


__all__ = ["parse_tabs_item"]
