from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.types import canonicalize_type_name, normalize_type_expression
from namel3ss.parser.core.tokens import parse_identifier_name


def parse_type_reference(parser) -> tuple[str, bool, str | None, int | None, int | None]:
    return _parse_union_type(parser)


def _parse_union_type(parser) -> tuple[str, bool, str | None, int | None, int | None]:
    first_name, first_alias, first_raw, line, column = _parse_type_atom(parser)
    names = [first_name]
    raws = [first_raw or first_name]
    any_alias = first_alias
    while parser._match("PIPE"):
        next_name, next_alias, next_raw, _, _ = _parse_type_atom(parser)
        names.append(next_name)
        raws.append(next_raw or next_name)
        any_alias = any_alias or next_alias
    type_name = " | ".join(names)
    raw_type_name = " | ".join(raws) if any_alias else None
    normalized_type, normalized_alias = normalize_type_expression(type_name)
    if normalized_alias:
        any_alias = True
        if raw_type_name is None:
            raw_type_name = type_name
    return normalized_type, any_alias, raw_type_name, line, column


def _parse_type_atom(parser) -> tuple[str, bool, str | None, int | None, int | None]:
    tok = parser._current()
    if tok.type == "TEXT":
        parser._advance()
        raw_type = "text"
        canonical_type, type_was_alias = canonicalize_type_name(raw_type)
        return _finalize_type(parser, canonical_type, raw_type, type_was_alias, tok.line, tok.column)
    if tok.type.startswith("TYPE_"):
        parser._advance()
        raw_type = _legacy_type_name(tok)
        canonical_type, type_was_alias = canonicalize_type_name(raw_type)
        return _finalize_type(parser, canonical_type, raw_type, type_was_alias, tok.line, tok.column)
    if tok.type == "NULL":
        parser._advance()
        return "null", False, None, tok.line, tok.column
    if tok.type == "IDENT":
        name_tok = parse_identifier_name(parser, "Expected type name")
        parts = [name_tok.value]
        while parser._match("DOT"):
            part_tok = parse_identifier_name(parser, "Expected type name after '.'")
            parts.append(part_tok.value)
        base_name = ".".join(parts)
        canonical_base, base_alias = canonicalize_type_name(base_name)
        if parser._match("LT"):
            args: list[str] = []
            raw_args: list[str] = []
            arg_alias = False
            while True:
                arg_name, nested_alias, nested_raw, _, _ = _parse_union_type(parser)
                args.append(arg_name)
                raw_args.append(nested_raw or arg_name)
                arg_alias = arg_alias or nested_alias
                if parser._match("COMMA"):
                    continue
                parser._expect("GT", "Expected '>' after generic type")
                break
            rendered = f"{canonical_base}<{', '.join(args)}>"
            has_alias = base_alias or arg_alias
            raw_rendered = None
            if has_alias:
                base_raw = base_name
                raw_rendered = f"{base_raw}<{', '.join(raw_args)}>"
            normalized, normalized_alias = normalize_type_expression(rendered)
            if normalized_alias:
                has_alias = True
                if raw_rendered is None:
                    raw_rendered = rendered
            return normalized, has_alias, raw_rendered, tok.line, tok.column
        return canonical_base, base_alias, base_name if base_alias else None, tok.line, tok.column
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
    normalized, normalized_alias = normalize_type_expression(canonical_type)
    alias = type_was_alias or normalized_alias
    raw_value = raw_type if alias else None
    return normalized, alias, raw_value, line, column


def _legacy_type_name(tok) -> str:
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


__all__ = ["parse_type_reference"]
