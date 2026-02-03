from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import _parse_state_path_relaxed, _parse_visibility_rule_value
from namel3ss.parser.decl.page_items import parse_page_item


_ALLOWED_STATUS_NAMES = {"loading", "empty", "error"}


def parse_status_block(parser) -> ast.StatusBlock:
    status_tok = parser._current()
    parser._advance()
    parser._expect("COLON", "Expected ':' after status")
    parser._expect("NEWLINE", "Expected newline after status header")
    parser._expect("INDENT", "Expected indented status block")
    cases: list[ast.StatusCase] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._expect("IDENT", "Expected status name")
        name = name_tok.value
        if name not in _ALLOWED_STATUS_NAMES:
            raise Namel3ssError(
                "Status blocks only support loading, empty, or error.",
                line=name_tok.line,
                column=name_tok.column,
            )
        if name in seen:
            raise Namel3ssError(
                f"Status '{name}' is already declared.",
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._expect("WHEN", "Expected 'when' after status name")
        try:
            path = _parse_state_path_relaxed(parser)
        except Namel3ssError as err:
            raise Namel3ssError(
                "Status condition requires state.<path> is <value>.",
                line=err.line,
                column=err.column,
            ) from err
        parser._expect("IS", "Expected 'is' after state path")
        condition_tok = parser._current()
        if condition_tok.type == "IDENT" and condition_tok.value == "empty":
            parser._advance()
            condition = ast.StatusCondition(path=path, kind="empty", value=None, line=condition_tok.line, column=condition_tok.column)
        else:
            value = _parse_visibility_rule_value(parser, allow_pattern_params=False)
            condition = ast.StatusCondition(path=path, kind="equals", value=value, line=value.line, column=value.column)
        parser._expect("NEWLINE", "Expected newline after status condition")
        parser._expect("INDENT", "Expected indented status body")
        items: list[ast.PageItem] = []
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            parsed = parse_page_item(parser, allow_tabs=False, allow_overlays=False)
            if isinstance(parsed, list):
                items.extend(parsed)
            else:
                items.append(parsed)
        parser._expect("DEDENT", "Expected end of status body")
        if not items:
            raise Namel3ssError(
                f"Status '{name}' has no items.",
                line=name_tok.line,
                column=name_tok.column,
            )
        cases.append(
            ast.StatusCase(
                name=name,
                condition=condition,
                items=items,
                line=name_tok.line,
                column=name_tok.column,
            )
        )
        seen.add(name)
    parser._expect("DEDENT", "Expected end of status block")
    if not cases:
        raise Namel3ssError("Status block has no entries.", line=status_tok.line, column=status_tok.column)
    return ast.StatusBlock(cases=cases, line=status_tok.line, column=status_tok.column)


__all__ = ["parse_status_block"]
