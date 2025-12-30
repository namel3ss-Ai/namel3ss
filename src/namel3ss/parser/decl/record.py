from __future__ import annotations

from typing import List, Tuple

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lexer.tokens import Token
from namel3ss.lang.types import canonicalize_type_name
from namel3ss.parser.decl.constraints import parse_field_constraint


def parse_record(parser) -> ast.RecordDecl:
    rec_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected record name string")
    parser._expect("COLON", "Expected ':' after record name")
    fields, tenant_key, ttl_hours = parse_record_body(parser)
    return ast.RecordDecl(
        name=name_tok.value,
        fields=fields,
        tenant_key=tenant_key,
        ttl_hours=ttl_hours,
        line=rec_tok.line,
        column=rec_tok.column,
    )


def parse_record_fields(parser) -> List[ast.FieldDecl]:
    fields, _, _ = parse_record_body(parser)
    return fields


def parse_record_body(
    parser,
) -> Tuple[List[ast.FieldDecl], ast.Expression | None, ast.Expression | None]:
    parser._expect("NEWLINE", "Expected newline after record header")
    parser._expect("INDENT", "Expected indented record body")
    fields: List[ast.FieldDecl] = []
    tenant_key_expr: ast.Expression | None = None
    ttl_hours_expr: ast.Expression | None = None
    seen_persisted = False
    seen_fields: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._current()
        if name_tok.type == "IDENT" and name_tok.value == "tenant_key":
            if tenant_key_expr is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Record declares tenant_key more than once.",
                        why="Each record may only define a single tenant_key.",
                        fix="Keep a single tenant_key declaration.",
                        example='tenant_key is identity.organization_id',
                    ),
                    line=name_tok.line,
                    column=name_tok.column,
                )
            parser._advance()
            parser._expect("IS", "Expected 'is' after tenant_key")
            tenant_key_expr = parser._parse_expression()
            if parser._match("NEWLINE"):
                continue
            continue
        if name_tok.type == "IDENT" and name_tok.value == "persisted":
            if seen_persisted:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Record declares persisted block more than once.",
                        why="Each record may only define a single persisted block.",
                        fix="Keep a single persisted block.",
                        example="persisted:\n  ttl_hours is 24",
                    ),
                    line=name_tok.line,
                    column=name_tok.column,
                )
            seen_persisted = True
            parser._advance()
            parser._expect("COLON", "Expected ':' after persisted")
            parser._expect("NEWLINE", "Expected newline after persisted")
            parser._expect("INDENT", "Expected indented persisted block")
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                setting_tok = parser._current()
                if setting_tok.type == "IDENT" and setting_tok.value == "ttl_hours":
                    if ttl_hours_expr is not None:
                        raise Namel3ssError(
                            build_guidance_message(
                                what="ttl_hours is declared more than once.",
                                why="Only one ttl_hours setting is allowed.",
                                fix="Keep a single ttl_hours line.",
                                example="ttl_hours is 24",
                            ),
                            line=setting_tok.line,
                            column=setting_tok.column,
                        )
                    parser._advance()
                    parser._expect("IS", "Expected 'is' after ttl_hours")
                    ttl_hours_expr = parser._parse_expression()
                    if parser._match("NEWLINE"):
                        continue
                    continue
                raise Namel3ssError(
                    build_guidance_message(
                        what=f"Unknown persisted setting '{setting_tok.value}'.",
                        why="Only ttl_hours is supported in persisted blocks.",
                        fix="Use ttl_hours or remove the line.",
                        example="persisted:\n  ttl_hours is 24",
                    ),
                    line=setting_tok.line,
                    column=setting_tok.column,
                )
            parser._expect("DEDENT", "Expected end of persisted block")
            while parser._match("NEWLINE"):
                pass
            continue
        if name_tok.type == "IDENT" and name_tok.value == "fields" and _peek_token(parser, 1).type == "COLON":
            fields.extend(_parse_fields_block(parser, seen_fields))
            continue
        field = _parse_record_field(parser, allow_field_keyword=True, require_is=False, use_guidance=False)
        _register_field(field, seen_fields)
        fields.append(field)
        if parser._match("NEWLINE"):
            continue
    parser._expect("DEDENT", "Expected end of record body")
    while parser._match("NEWLINE"):
        pass
    return fields, tenant_key_expr, ttl_hours_expr


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


_FIELD_NAME_TOKENS = {"IDENT", "TITLE", "TEXT", "FORM", "TABLE", "BUTTON", "PAGE"}


def _parse_fields_block(parser, seen_fields: set[str]) -> list[ast.FieldDecl]:
    fields_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after fields")
    parser._expect("NEWLINE", "Expected newline after fields")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Fields block has no fields.",
                why="Fields blocks require at least one field declaration.",
                fix="Add one or more fields under fields:.",
                example='record "Order":\n  fields:\n    order_id is text',
            ),
            line=tok.line,
            column=tok.column,
        )
    fields: list[ast.FieldDecl] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        field = _parse_record_field(parser, allow_field_keyword=False, require_is=True, use_guidance=True)
        _register_field(field, seen_fields)
        fields.append(field)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of fields block")
    while parser._match("NEWLINE"):
        pass
    if not fields:
        raise Namel3ssError(
            build_guidance_message(
                what="Fields block has no fields.",
                why="Fields blocks require at least one field declaration.",
                fix="Add one or more fields under fields:.",
                example='record "Order":\n  fields:\n    order_id is text',
            ),
            line=fields_tok.line,
            column=fields_tok.column,
        )
    return fields


def _parse_record_field(
    parser,
    *,
    allow_field_keyword: bool,
    require_is: bool,
    use_guidance: bool,
) -> ast.FieldDecl:
    name_tok = parser._current()
    if name_tok.type not in _FIELD_NAME_TOKENS:
        if use_guidance:
            raise Namel3ssError(
                build_guidance_message(
                    what="Fields block entries must start with a field name.",
                    why="Fields blocks use unquoted identifiers followed by `is` and a type.",
                    fix="Use a simple name like order_id.",
                    example='fields:\n  order_id is text',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        raise Namel3ssError("Expected field name", line=name_tok.line, column=name_tok.column)
    if name_tok.value == "field":
        if not allow_field_keyword:
            raise Namel3ssError(
                build_guidance_message(
                    what="Fields block entries must use unquoted names.",
                    why="Fields blocks replace the `field \"name\"` syntax.",
                    fix="Remove the field keyword and quotes.",
                    example='fields:\n  order_id is text',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._advance()
        field_name_tok = parser._expect("STRING", "Expected field name string after 'field'")
    else:
        parser._advance()
        field_name_tok = name_tok
    if require_is:
        parser._expect("IS", "Expected 'is' after field name")
    else:
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


def _register_field(field: ast.FieldDecl, seen_fields: set[str]) -> None:
    if field.name in seen_fields:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Record declares field '{field.name}' more than once.",
                why="Each record field name must be unique.",
                fix="Rename or remove the duplicate field.",
                example='record "Order":\n  fields:\n    order_id is text\n    customer is text',
            ),
            line=field.line,
            column=field.column,
        )
    seen_fields.add(field.name)


def _peek_token(parser, offset: int = 1) -> Token:
    pos = parser.position + offset
    if pos >= len(parser.tokens):
        return parser.tokens[-1]
    return parser.tokens[pos]


__all__ = ["parse_record", "parse_record_fields", "parse_record_body", "type_from_token"]
