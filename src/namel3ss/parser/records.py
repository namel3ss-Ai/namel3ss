from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lexer.tokens import Token
from namel3ss.parser.constraints import parse_field_constraint
from namel3ss.types import normalize_type_name


def parse_record(parser) -> ast.RecordDecl:
    rec_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected record name string")
    parser._expect("COLON", "Expected ':' after record name")
    fields = parse_record_fields(parser)
    return ast.RecordDecl(name=name_tok.value, fields=fields, line=rec_tok.line, column=rec_tok.column)


def parse_record_fields(parser) -> List[ast.FieldDecl]:
    parser._expect("NEWLINE", "Expected newline after record header")
    parser._expect("INDENT", "Expected indented record body")
    fields: List[ast.FieldDecl] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._current()
        if name_tok.type not in {"IDENT", "TITLE", "TEXT", "FORM", "TABLE", "BUTTON", "PAGE"}:
            raise Namel3ssError("Expected field name", line=name_tok.line, column=name_tok.column)
        # Support canonical "field \"name\" is type" while keeping legacy "name type".
        if name_tok.value == "field":
            parser._advance()
            field_name_tok = parser._expect("STRING", "Expected field name string after 'field'")
        else:
            parser._advance()
            field_name_tok = name_tok
        parser._match("IS")
        type_tok = parser._current()
        raw_type = None
        type_was_alias = False
        if type_tok.type == "TEXT":
            raw_type = "text"
            parser._advance()
        elif type_tok.type.startswith("TYPE_"):
            parser._advance()
            raw_type = type_from_token(type_tok)
        else:
            raise Namel3ssError("Expected field type", line=type_tok.line, column=type_tok.column)
        canonical_type, type_was_alias = normalize_type_name(raw_type)
        if type_was_alias and not getattr(parser, "allow_legacy_type_aliases", True):
            raise Namel3ssError(
                f"N3PARSER_TYPE_ALIAS_DISALLOWED: Type alias '{raw_type}' is not allowed. Use '{canonical_type}'. "
                "Fix: run `n3 app.ai format` to rewrite aliases.",
                line=type_tok.line,
                column=type_tok.column,
            )
        constraint = None
        if parser._match("MUST"):
            constraint = parse_field_constraint(parser)
        fields.append(
            ast.FieldDecl(
                name=field_name_tok.value,
                type_name=canonical_type,
                constraint=constraint,
                type_was_alias=type_was_alias,
                raw_type_name=raw_type if type_was_alias else None,
                type_line=type_tok.line,
                type_column=type_tok.column,
                line=field_name_tok.line,
                column=field_name_tok.column,
            )
        )
        if parser._match("NEWLINE"):
            continue
    parser._expect("DEDENT", "Expected end of record body")
    while parser._match("NEWLINE"):
        pass
    return fields


def type_from_token(tok: Token) -> str:
    raw = tok.value.lower() if isinstance(tok.value, str) else None
    if tok.type == "TYPE_STRING":
        return raw or "string"
    if tok.type == "TYPE_INT":
        return raw or "int"
    if tok.type == "TYPE_NUMBER":
        return raw or "number"
    if tok.type == "TYPE_BOOLEAN":
        return raw or "boolean"
    if tok.type == "TYPE_JSON":
        return raw or "json"
    raise Namel3ssError("Invalid type", line=tok.line, column=tok.column)
