from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_form_block(parser) -> tuple[List[ast.FormGroup] | None, List[ast.FormFieldConfig] | None]:
    parser._expect("NEWLINE", "Expected newline after form header")
    parser._expect("INDENT", "Expected indented form block")
    groups: List[ast.FormGroup] | None = None
    fields: List[ast.FormFieldConfig] | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "groups":
            if groups is not None:
                raise Namel3ssError("Groups block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            groups = _parse_form_groups_block(parser)
            continue
        if tok.type == "IDENT" and tok.value == "fields":
            if fields is not None:
                raise Namel3ssError("Fields block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            fields = _parse_form_fields_block(parser)
            continue
        raise Namel3ssError(
            f"Unknown form setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of form block")
    return groups, fields


def _parse_form_groups_block(parser) -> List[ast.FormGroup]:
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
        label_tok = parser._expect("STRING", "Expected group label string")
        parser._expect("COLON", "Expected ':' after group label")
        parser._expect("NEWLINE", "Expected newline after group header")
        if not parser._match("INDENT"):
            raise Namel3ssError("Group block has no fields", line=label_tok.line, column=label_tok.column)
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
            raise Namel3ssError("Group block has no fields", line=label_tok.line, column=label_tok.column)
        groups.append(ast.FormGroup(label=label_tok.value, fields=fields, line=tok.line, column=tok.column))
    parser._expect("DEDENT", "Expected end of groups block")
    if not groups:
        raise Namel3ssError("Groups block has no entries", line=parser._current().line, column=parser._current().column)
    return groups


def _parse_form_fields_block(parser) -> List[ast.FormFieldConfig]:
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
                value_tok = parser._expect("STRING", "Expected help text string")
                help_text = value_tok.value
                if parser._match("NEWLINE"):
                    continue
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "readonly":
                if readonly is not None:
                    raise Namel3ssError("Readonly is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after readonly")
                bool_tok = parser._expect("BOOLEAN", "Readonly must be true or false")
                readonly = bool(bool_tok.value)
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
    raise Namel3ssError("Expected field name", line=tok.line, column=tok.column)


__all__ = ["parse_form_block"]
