from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.types import canonicalize_type_name
from namel3ss.parser.core.tokens import parse_identifier_name
from namel3ss.parser.decl.record import type_from_token


def parse_type_reference(parser) -> tuple[str, bool, str | None, int | None, int | None]:
    tok = parser._current()
    if tok.type == "TEXT":
        parser._advance()
        raw_type = "text"
        canonical_type, type_was_alias = canonicalize_type_name(raw_type)
        return _finalize_type(parser, canonical_type, raw_type, type_was_alias, tok.line, tok.column)
    if tok.type.startswith("TYPE_"):
        parser._advance()
        raw_type = type_from_token(tok)
        canonical_type, type_was_alias = canonicalize_type_name(raw_type)
        return _finalize_type(parser, canonical_type, raw_type, type_was_alias, tok.line, tok.column)
    if tok.type == "IDENT":
        if tok.value == "list" and not getattr(tok, "escaped", False):
            parser._advance()
            parser._expect("LT", "Expected '<' after list")
            inner_type, inner_alias, inner_raw, _, _ = parse_type_reference(parser)
            parser._expect("GT", "Expected '>' after list type")
            type_name = f"list<{inner_type}>"
            raw_type_name = f"list<{inner_raw or inner_type}>" if inner_alias else None
            return type_name, inner_alias, raw_type_name, tok.line, tok.column
        name_tok = parse_identifier_name(parser, "Expected type name")
        parts = [name_tok.value]
        while parser._match("DOT"):
            part_tok = parse_identifier_name(parser, "Expected type name after '.'")
            parts.append(part_tok.value)
        return ".".join(parts), False, None, tok.line, tok.column
    raise Namel3ssError("Expected field type", line=tok.line, column=tok.column)


def _finalize_type(
    parser,
    canonical_type: str,
    raw_type: str,
    type_was_alias: bool,
    line: int | None,
    column: int | None,
) -> tuple[str, bool, str | None, int | None, int | None]:
    if type_was_alias and not getattr(parser, "allow_legacy_type_aliases", True):
        raise Namel3ssError(
            f"N3PARSER_TYPE_ALIAS_DISALLOWED: Type alias '{raw_type}' is not allowed. Use '{canonical_type}'. "
            "Fix: run `n3 app.ai format` to rewrite aliases.",
            line=line,
            column=column,
        )
    return canonical_type, type_was_alias, raw_type if type_was_alias else None, line, column


__all__ = ["parse_type_reference"]
