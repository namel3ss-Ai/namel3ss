from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ui.presets import validate_ui_preset
from namel3ss.ast import nodes as ast
from namel3ss.ui.settings import default_ui_settings_with_meta, validate_ui_field, validate_ui_value


_PAGES_GRAMMAR = "Pages must declare: active page: with one or more rules."
_ACTIVE_PAGE_GRAMMAR = 'Active page must use: is "<page>" only when state.<path> is <value>.'


def parse_ui_decl(parser):
    tok = parser._advance()
    parser._expect("COLON", "Expected ':' after ui")
    parser._expect("NEWLINE", "Expected newline after ui header")
    parser._expect("INDENT", "Expected indented ui block")
    settings = default_ui_settings_with_meta()
    seen: set[str] = set()
    active_page_rules: list[ast.ActivePageRule] | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if parser._current().type == "IDENT" and parser._current().value == "pages":
            if active_page_rules is not None:
                tok_pages = parser._current()
                raise Namel3ssError(
                    "UI pages are already declared.",
                    line=tok_pages.line,
                    column=tok_pages.column,
                )
            active_page_rules = _parse_pages_block(parser)
            continue
        if parser._current().type in {"IDENT", "THEME"}:
            name_tok = parser._advance()
        else:
            name_tok = parser._expect("IDENT", "Expected ui field name")
        key_name = name_tok.value
        if parser._current().type == "IDENT":
            next_tok = parser._advance()
            key_name = f"{key_name} {next_tok.value}"
        key = validate_ui_field(key_name, line=name_tok.line, column=name_tok.column)
        if key in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate ui field '{key}'.",
                    why="Each ui field can only be declared once.",
                    fix="Remove the duplicate field.",
                    example='ui:\n  theme is "light"\n  accent color is "blue"',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._expect("IS", "Expected 'is' after ui field name")
        value_tok = parser._expect("STRING", "Expected ui field value")
        if key == "preset":
            validate_ui_preset(value_tok.value, line=value_tok.line, column=value_tok.column)
        else:
            validate_ui_value(key, value_tok.value, line=value_tok.line, column=value_tok.column)
        settings[key] = (value_tok.value, value_tok.line, value_tok.column)
        seen.add(key)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of ui block")
    while parser._match("NEWLINE"):
        continue
    return settings, active_page_rules, tok.line, tok.column


def _parse_pages_block(parser) -> list[ast.ActivePageRule]:
    pages_tok = parser._expect("IDENT", "Expected 'pages'")
    if pages_tok.value != "pages":
        raise Namel3ssError(_PAGES_GRAMMAR, line=pages_tok.line, column=pages_tok.column)
    parser._expect("COLON", "Expected ':' after pages")
    parser._expect("NEWLINE", "Expected newline after pages header")
    parser._expect("INDENT", "Expected indented pages block")
    active_page_rules: list[ast.ActivePageRule] | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if active_page_rules is not None:
            extra = parser._current()
            raise Namel3ssError("Active page is already declared.", line=extra.line, column=extra.column)
        active_page_rules = _parse_active_page_block(parser)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of pages block")
    if not active_page_rules:
        raise Namel3ssError(_PAGES_GRAMMAR, line=pages_tok.line, column=pages_tok.column)
    return active_page_rules


def _parse_active_page_block(parser) -> list[ast.ActivePageRule]:
    active_tok = parser._expect("IDENT", "Expected 'active page'")
    if active_tok.value != "active":
        raise Namel3ssError(_PAGES_GRAMMAR, line=active_tok.line, column=active_tok.column)
    parser._expect("PAGE", "Expected 'page' after active")
    parser._expect("COLON", "Expected ':' after active page")
    parser._expect("NEWLINE", "Expected newline after active page")
    parser._expect("INDENT", "Expected indented active page block")
    rules: list[ast.ActivePageRule] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        rules.append(_parse_active_page_rule(parser))
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of active page block")
    if not rules:
        raise Namel3ssError(_ACTIVE_PAGE_GRAMMAR, line=active_tok.line, column=active_tok.column)
    return rules


def _parse_active_page_rule(parser) -> ast.ActivePageRule:
    is_tok = parser._expect("IS", "Expected 'is' in active page rule")
    page_name = parser._expect("STRING", "Expected page name string")
    only_tok = parser._expect("IDENT", "Expected 'only' after page name")
    if only_tok.value != "only":
        raise Namel3ssError(_ACTIVE_PAGE_GRAMMAR, line=only_tok.line, column=only_tok.column)
    parser._expect("WHEN", "Expected 'when' after only")
    path = parser._parse_state_path()
    parser._expect("IS", "Expected 'is' after state path")
    value = _parse_active_page_literal(parser)
    if parser._current().type not in {"NEWLINE", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(_ACTIVE_PAGE_GRAMMAR, line=extra.line, column=extra.column)
    return ast.ActivePageRule(
        page_name=page_name.value,
        path=path,
        value=value,
        line=is_tok.line,
        column=is_tok.column,
    )


def _parse_active_page_literal(parser) -> ast.Literal:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    if tok.type == "NUMBER":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    if tok.type == "BOOLEAN":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    raise Namel3ssError(_ACTIVE_PAGE_GRAMMAR, line=tok.line, column=tok.column)


__all__ = ["parse_ui_decl"]
