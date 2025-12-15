from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lexer.tokens import Token
from namel3ss.parser.constraints import parse_field_constraint


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
        parser._advance()
        type_tok = parser._current()
        if not type_tok.type.startswith("TYPE_"):
            raise Namel3ssError("Expected field type", line=type_tok.line, column=type_tok.column)
        parser._advance()
        type_name = type_from_token(type_tok)
        constraint = None
        if parser._match("MUST"):
            constraint = parse_field_constraint(parser)
        fields.append(
            ast.FieldDecl(
                name=name_tok.value,
                type_name=type_name,
                constraint=constraint,
                line=name_tok.line,
                column=name_tok.column,
            )
        )
        if parser._match("NEWLINE"):
            continue
    parser._expect("DEDENT", "Expected end of record body")
    while parser._match("NEWLINE"):
        pass
    return fields


def type_from_token(tok: Token) -> str:
    if tok.type == "TYPE_STRING":
        return "string"
    if tok.type == "TYPE_INT":
        return "int"
    if tok.type == "TYPE_NUMBER":
        return "number"
    if tok.type == "TYPE_BOOLEAN":
        return "boolean"
    if tok.type == "TYPE_JSON":
        return "json"
    raise Namel3ssError("Invalid type", line=tok.line, column=tok.column)
