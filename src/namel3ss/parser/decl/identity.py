from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.types import canonicalize_type_name
from namel3ss.parser.decl.constraints import parse_field_constraint
from namel3ss.parser.decl.record import type_from_token


def parse_identity(parser) -> ast.IdentityDecl:
    ident_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected identity name string")
    parser._expect("COLON", "Expected ':' after identity name")
    parser._expect("NEWLINE", "Expected newline after identity header")
    parser._expect("INDENT", "Expected indented identity body")
    fields: List[ast.FieldDecl] = []
    trust_levels: List[str] | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "trust_level":
            if trust_levels is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Identity trust_level is declared more than once.",
                        why="Only one trust_level list is allowed in an identity block.",
                        fix="Keep a single trust_level declaration.",
                        example='trust_level is one of ["guest", "verified"]',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            parser._advance()
            parser._expect("IS", "Expected 'is' after trust_level")
            _expect_ident_value(parser, "one")
            _expect_ident_value(parser, "of")
            trust_levels = _parse_string_list(parser)
            parser._expect("NEWLINE", "Expected newline after trust_level list")
            continue
        fields.append(_parse_identity_field(parser))
    parser._expect("DEDENT", "Expected end of identity body")
    while parser._match("NEWLINE"):
        pass
    return ast.IdentityDecl(
        name=name_tok.value,
        fields=fields,
        trust_levels=trust_levels,
        line=ident_tok.line,
        column=ident_tok.column,
    )


def _parse_identity_field(parser) -> ast.FieldDecl:
    name_tok = parser._current()
    if name_tok.type not in {"IDENT", "TITLE", "TEXT", "FORM", "TABLE", "BUTTON", "PAGE"}:
        raise Namel3ssError("Expected identity field name", line=name_tok.line, column=name_tok.column)
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
        raise Namel3ssError("Expected identity field type", line=type_tok.line, column=type_tok.column)
    canonical_type, type_was_alias = canonicalize_type_name(raw_type)
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
    if parser._match("NEWLINE"):
        pass
    return ast.FieldDecl(
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


def _parse_string_list(parser) -> List[str]:
    parser._expect("LBRACKET", "Expected '[' to start list")
    values: List[str] = []
    if parser._match("RBRACKET"):
        raise Namel3ssError(
            build_guidance_message(
                what="trust_level list cannot be empty.",
                why="The trust_level declaration needs at least one allowed value.",
                fix="Add one or more trust levels.",
                example='trust_level is one of ["guest", "verified"]',
            ),
            line=parser._current().line,
            column=parser._current().column,
        )
    while True:
        tok = parser._expect("STRING", "Expected trust level string")
        values.append(tok.value)
        if parser._match("COMMA"):
            continue
        parser._expect("RBRACKET", "Expected ']' after list")
        break
    return values


def _expect_ident_value(parser, value: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Expected '{value}' in identity declaration.",
                why="trust_level must use `one of [..]` to declare allowed values.",
                fix=f"Add '{value}' after trust_level is.",
                example='trust_level is one of ["guest", "verified"]',
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._advance()


__all__ = ["parse_identity"]
