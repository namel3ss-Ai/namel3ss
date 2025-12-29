from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_reference_name(parser, *, context: str) -> str:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return tok.value
    if tok.type == "IDENT":
        parser._advance()
        parts = [tok.value]
        while parser._match("DOT"):
            next_tok = parser._current()
            if next_tok.type != "IDENT":
                raise Namel3ssError(
                    build_guidance_message(
                        what="Qualified name is incomplete.",
                        why="Dot-qualified references must be identifiers.",
                        fix="Add the symbol name after the dot.",
                        example="inv.Product",
                    ),
                    line=next_tok.line,
                    column=next_tok.column,
                )
            parser._advance()
            parts.append(next_tok.value)
        return ".".join(parts)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Expected {context} name.",
            why="Names must be a string or a dot-qualified identifier.",
            fix="Use a quoted name or an alias-qualified name.",
            example='"inventory.Product"',
        ),
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_reference_name"]
