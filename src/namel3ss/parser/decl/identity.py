from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.keywords import is_keyword
from namel3ss.lang.types import canonicalize_type_name
from namel3ss.parser.decl.constraints import parse_field_constraint
from namel3ss.parser.decl.record import type_from_token
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def parse_identity(parser) -> ast.IdentityDecl:
    ident_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected identity name string")
    parser._expect("COLON", "Expected ':' after identity name")
    parser._expect("NEWLINE", "Expected newline after identity header")
    parser._expect("INDENT", "Expected indented identity body")
    fields: List[ast.FieldDecl] = []
    trust_levels: List[str] | None = None
    seen_fields: set[str] = set()
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
                        example='trust_level is one of "guest", "verified"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            parser._advance()
            parser._expect("IS", "Expected 'is' after trust_level")
            _expect_ident_value(parser, "one")
            _expect_ident_value(parser, "of")
            trust_levels = _parse_trust_level_list(parser, line=tok.line, column=tok.column)
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "fields" and _peek_token(parser, 1).type == "COLON":
            fields.extend(_parse_fields_block(parser, seen_fields, identity_name=name_tok.value))
            continue
        field = _parse_identity_field(
            parser,
            allow_field_keyword=True,
            require_is=False,
            use_guidance=False,
        )
        _register_field(field, seen_fields, identity_name=name_tok.value)
        fields.append(field)
        parser._match("NEWLINE")
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


_FIELD_NAME_TOKENS = {"IDENT", "TITLE", "TEXT", "FORM", "TABLE", "BUTTON", "PAGE"}


def _parse_fields_block(parser, seen_fields: set[str], *, identity_name: str) -> list[ast.FieldDecl]:
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
                example='identity "user":\n  fields:\n    subject is text',
            ),
            line=tok.line,
            column=tok.column,
        )
    fields: list[ast.FieldDecl] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        field = _parse_identity_field(
            parser,
            allow_field_keyword=False,
            require_is=True,
            use_guidance=True,
        )
        _register_field(field, seen_fields, identity_name=identity_name)
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
                example='identity "user":\n  fields:\n    subject is text',
            ),
            line=fields_tok.line,
            column=fields_tok.column,
        )
    return fields


def _parse_identity_field(
    parser,
    *,
    allow_field_keyword: bool,
    require_is: bool,
    use_guidance: bool,
) -> ast.FieldDecl:
    name_tok = parser._current()
    allow_quoted = not allow_field_keyword
    if name_tok.type not in _FIELD_NAME_TOKENS and not (allow_quoted and name_tok.type == "STRING"):
        if isinstance(name_tok.value, str) and is_keyword(name_tok.value):
            guidance, details = reserved_identifier_diagnostic(name_tok.value)
            raise Namel3ssError(guidance, line=name_tok.line, column=name_tok.column, details=details)
        if use_guidance:
            raise Namel3ssError(
                build_guidance_message(
                    what="Fields block entries must start with a field name.",
                    why="Fields blocks use identifiers followed by `is` and a type.",
                    fix="Use a simple name like subject.",
                    example='fields:\n  subject is text',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        raise Namel3ssError("Expected identity field name", line=name_tok.line, column=name_tok.column)
    if name_tok.type == "STRING":
        parser._advance()
        field_name_tok = name_tok
    elif name_tok.value == "field":
        if not allow_field_keyword:
            raise Namel3ssError(
                build_guidance_message(
                    what="Fields block entries must use names without the field keyword.",
                    why="Fields blocks replace the `field \"name\"` syntax.",
                    fix="Remove the field keyword and quotes.",
                    example='fields:\n  subject is text',
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
        parser._expect("IS", "Expected 'is' after identity field name")
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


def _parse_trust_level_list(parser, *, line: int, column: int) -> List[str]:
    if parser._match("LBRACKET"):
        values = _parse_trust_level_bracket_list(parser)
    elif parser._match("COLON"):
        values = _parse_trust_level_block_list(parser, line=line, column=column)
    else:
        values = _parse_trust_level_inline_list(parser, line=line, column=column)
    if not values:
        raise Namel3ssError(
            build_guidance_message(
                what="trust_level list cannot be empty.",
                why="The trust_level declaration needs at least one allowed value.",
                fix="Add one or more trust levels.",
                example='trust_level is one of "guest", "verified"',
            ),
            line=line,
            column=column,
        )
    return values


def _parse_trust_level_bracket_list(parser) -> List[str]:
    values: List[str] = []
    if parser._match("RBRACKET"):
        return values
    while True:
        tok = parser._expect("STRING", "Expected trust level string")
        values.append(tok.value)
        if parser._match("COMMA"):
            continue
        parser._expect("RBRACKET", "Expected ']' after list")
        break
    return values


def _parse_trust_level_block_list(parser, *, line: int, column: int) -> List[str]:
    parser._expect("NEWLINE", "Expected newline after trust_level list")
    if not parser._match("INDENT"):
        return []
    values: List[str] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._expect("STRING", "Expected trust level string")
        values.append(tok.value)
        if parser._match("COMMA"):
            if parser._current().type in {"NEWLINE", "DEDENT"}:
                continue
            continue
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of trust_level list")
    while parser._match("NEWLINE"):
        pass
    return values


def _parse_trust_level_inline_list(parser, *, line: int, column: int) -> List[str]:
    values: List[str] = []
    while True:
        tok = parser._current()
        if tok.type != "STRING":
            if not values:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Expected trust level string.",
                        why="trust_level lists use string values separated by commas.",
                        fix="Add a quoted trust level value.",
                        example='trust_level is one of "guest", "verified"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            break
        parser._advance()
        values.append(tok.value)
        if parser._match("COMMA"):
            if parser._current().type in {"NEWLINE", "DEDENT", "EOF"}:
                break
            continue
        break
    return values


def _expect_ident_value(parser, value: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Expected '{value}' in identity declaration.",
                why="trust_level must use `one of` followed by a comma list.",
                fix=f"Add '{value}' after trust_level is.",
                example='trust_level is one of "guest", "verified"',
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._advance()


def _register_field(field: ast.FieldDecl, seen_fields: set[str], *, identity_name: str | None) -> None:
    if field.name in seen_fields:
        label = identity_name or "identity"
        raise Namel3ssError(
            build_guidance_message(
                what=f"Identity declares field '{field.name}' more than once.",
                why="Each identity field name must be unique.",
                fix="Rename or remove the duplicate field.",
                example=f'identity "{label}":\n  fields:\n    subject is text\n    email is text',
            ),
            line=field.line,
            column=field.column,
        )
    seen_fields.add(field.name)


def _peek_token(parser, offset: int = 1):
    pos = parser.position + offset
    if pos >= len(parser.tokens):
        return parser.tokens[-1]
    return parser.tokens[pos]


__all__ = ["parse_identity"]
