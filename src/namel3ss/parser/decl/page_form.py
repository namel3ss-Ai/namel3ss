from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_common import _is_visibility_rule_start, _parse_boolean_value, _parse_string_value, _parse_visibility_rule_line
from namel3ss.parser.decl.page_items.size_radius import apply_theme_override, parse_theme_override_line
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def parse_form_block(
    parser,
    *,
    allow_pattern_params: bool = False,
) -> tuple[List[ast.FormGroup] | None, List[ast.FormFieldConfig] | None, ast.VisibilityRule | None]:
    parser._expect("NEWLINE", "Expected newline after form header")
    parser._expect("INDENT", "Expected indented form block")
    groups: List[ast.FormGroup] | None = None
    fields: List[ast.FormFieldConfig] | None = None
    visibility_rule: ast.VisibilityRule | None = None
    theme_overrides: ast.ThemeTokenOverrides | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        token_name, override = parse_theme_override_line(parser)
        if override is not None and token_name is not None:
            theme_overrides = apply_theme_override(
                theme_overrides,
                override,
                token_name=token_name,
                line=override.line,
                column=override.column,
            )
            parser._match("NEWLINE")
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                raise Namel3ssError("Visibility blocks may only declare one only-when rule.", line=tok.line, column=tok.column)
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "groups":
            if groups is not None:
                raise Namel3ssError("Groups block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            groups = _parse_form_groups_block(parser, allow_pattern_params=allow_pattern_params)
            continue
        if tok.type == "IDENT" and tok.value == "fields":
            if fields is not None:
                raise Namel3ssError("Fields block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            fields = _parse_form_fields_block(parser, allow_pattern_params=allow_pattern_params)
            continue
        raise Namel3ssError(
            f"Unknown form setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of form block")
    return groups, fields, visibility_rule, theme_overrides


def _parse_form_groups_block(parser, *, allow_pattern_params: bool) -> List[ast.FormGroup]:
    parser._expect("COLON", "Expected ':' after groups")
    parser._expect("NEWLINE", "Expected newline after groups")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Groups block has no entries", line=tok.line, column=tok.column)
    groups: List[ast.FormGroup] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT" or tok.value != "group":
            raise Namel3ssError("Groups may only contain group entries", line=tok.line, column=tok.column)
        parser._advance()
        label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="group label")
        parser._expect("COLON", "Expected ':' after group label")
        parser._expect("NEWLINE", "Expected newline after group header")
        if not parser._match("INDENT"):
            raise Namel3ssError("Group block has no fields", line=tok.line, column=tok.column)
        fields: List[ast.FormFieldRef] = []
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            field_tok = parser._current()
            if field_tok.type != "IDENT" or field_tok.value != "field":
                raise Namel3ssError("Groups may only contain field references", line=field_tok.line, column=field_tok.column)
            parser._advance()
            name = _parse_form_field_name(parser)
            fields.append(ast.FormFieldRef(name=name, line=field_tok.line, column=field_tok.column))
            if parser._match("NEWLINE"):
                continue
        parser._expect("DEDENT", "Expected end of group block")
        if not fields:
            raise Namel3ssError("Group block has no fields", line=tok.line, column=tok.column)
        groups.append(ast.FormGroup(label=label, fields=fields, line=tok.line, column=tok.column))
    parser._expect("DEDENT", "Expected end of groups block")
    if not groups:
        raise Namel3ssError("Groups block has no entries", line=parser._current().line, column=parser._current().column)
    return groups


def _parse_form_fields_block(parser, *, allow_pattern_params: bool) -> List[ast.FormFieldConfig]:
    parser._expect("COLON", "Expected ':' after fields")
    parser._expect("NEWLINE", "Expected newline after fields")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Fields block has no entries", line=tok.line, column=tok.column)
    fields: List[ast.FormFieldConfig] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT" or tok.value != "field":
            raise Namel3ssError("Fields may only contain field entries", line=tok.line, column=tok.column)
        parser._advance()
        name = _parse_form_field_name(parser)
        if name in seen:
            raise Namel3ssError(
                f"Field '{name}' is declared more than once",
                line=tok.line,
                column=tok.column,
            )
        seen.add(name)
        parser._expect("COLON", "Expected ':' after field name")
        parser._expect("NEWLINE", "Expected newline after field header")
        if not parser._match("INDENT"):
            raise Namel3ssError("Field block has no entries", line=tok.line, column=tok.column)
        help_text: str | None = None
        readonly: bool | None = None
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            entry_tok = parser._current()
            if entry_tok.type == "IDENT" and entry_tok.value == "help":
                if help_text is not None:
                    raise Namel3ssError("Help is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after help")
                help_text = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="help text")
                if parser._match("NEWLINE"):
                    continue
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "readonly":
                if readonly is not None:
                    raise Namel3ssError("Readonly is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after readonly")
                try:
                    readonly = _parse_boolean_value(parser, allow_pattern_params=allow_pattern_params)
                except Namel3ssError as err:
                    raise Namel3ssError(
                        "Readonly must be true or false",
                        line=err.line,
                        column=err.column,
                    ) from err
                if parser._match("NEWLINE"):
                    continue
                continue
            raise Namel3ssError(
                f"Unknown field setting '{entry_tok.value}'",
                line=entry_tok.line,
                column=entry_tok.column,
            )
        parser._expect("DEDENT", "Expected end of field block")
        if help_text is None and readonly is None:
            raise Namel3ssError("Field block requires help or readonly", line=tok.line, column=tok.column)
        fields.append(
            ast.FormFieldConfig(
                name=name,
                help=help_text,
                readonly=readonly,
                line=tok.line,
                column=tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of fields block")
    if not fields:
        raise Namel3ssError("Fields block has no entries", line=parser._current().line, column=parser._current().column)
    return fields


def _parse_form_field_name(parser) -> str:
    tok = parser._current()
    if tok.type in {"STRING", "IDENT"}:
        parser._advance()
        return str(tok.value)
    if isinstance(tok.value, str) and is_keyword(tok.value):
        guidance, details = reserved_identifier_diagnostic(tok.value)
        raise Namel3ssError(guidance, line=tok.line, column=tok.column, details=details)
    raise Namel3ssError("Expected field name", line=tok.line, column=tok.column)


__all__ = ["parse_form_block"]
