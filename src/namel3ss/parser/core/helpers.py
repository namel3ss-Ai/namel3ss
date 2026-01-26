from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.core.tokens import parse_identifier_name


def parse_reference_name(parser, *, context: str) -> str:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return tok.value
    missing_context = build_guidance_message(
        what=f"Expected {context} name.",
        why="Names must be a string or a dot-qualified identifier.",
        fix="Use a quoted name or an alias-qualified name.",
        example='"inventory.Product"',
    )
    name_tok = parse_identifier_name(parser, missing_context)
    parts = [name_tok.value]
    while parser._match("DOT"):
        missing_part = build_guidance_message(
            what="Qualified name is incomplete.",
            why="Dot-qualified references must be identifiers.",
            fix="Add the symbol name after the dot.",
            example="inv.Product",
        )
        next_tok = parse_identifier_name(parser, missing_part)
        parts.append(next_tok.value)
    return ".".join(parts)


__all__ = ["parse_reference_name"]
