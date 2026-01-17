from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_packs(parser) -> list[str]:
    header_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after packs")
    parser._expect("NEWLINE", "Expected newline after packs")
    parser._expect("INDENT", "Expected indented packs block")
    items: list[str] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._current()
        if name_tok.type != "STRING":
            raise Namel3ssError(
                build_guidance_message(
                    what="Pack id must be a string.",
                    why="Pack ids include dots and must be quoted.",
                    fix='Use a quoted pack id in the packs block.',
                    example='packs:\\n  "builtin.text"',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._advance()
        pack_id = name_tok.value
        if not isinstance(pack_id, str) or not pack_id.strip():
            raise Namel3ssError(
                build_guidance_message(
                    what="Pack id is empty.",
                    why="Every pack entry must be a non-empty string.",
                    fix="Provide a pack id.",
                    example='packs:\\n  "builtin.text"',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        if pack_id in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Duplicate pack "{pack_id}".',
                    why="Each pack can be listed only once.",
                    fix="Remove the duplicate entry.",
                    example='packs:\\n  "builtin.text"',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        seen.add(pack_id)
        items.append(pack_id)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of packs block")
    while parser._match("NEWLINE"):
        pass
    if not items:
        raise Namel3ssError(
            build_guidance_message(
                what="Packs block is empty.",
                why="Every packs block must list at least one pack id.",
                fix="Add one or more pack ids.",
                example='packs:\\n  "builtin.text"',
            ),
            line=header_tok.line,
            column=header_tok.column,
        )
    return items


__all__ = ["parse_packs"]
