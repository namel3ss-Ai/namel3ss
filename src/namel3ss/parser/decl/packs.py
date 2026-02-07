from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.decl.grouping import parse_bracketed_items


def parse_packs(parser) -> list[str]:
    header_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after packs")
    items: list[str] = []
    seen: set[str] = set()
    if parser._current().type == "LBRACKET":
        pack_tokens = parse_bracketed_items(
            parser,
            context="packs",
            parse_item=lambda: parser._expect("STRING", "Pack id must be a string."),
            allow_empty=True,
        )
        for token in pack_tokens:
            _append_pack(items, seen, token.value, line=token.line, column=token.column)
        parser._match("NEWLINE")
    else:
        parser._expect("NEWLINE", "Expected newline after packs")
        parser._expect("INDENT", "Expected indented packs block")
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            name_tok = parser._expect("STRING", "Pack id must be a string.")
            _append_pack(items, seen, name_tok.value, line=name_tok.line, column=name_tok.column)
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


def _append_pack(
    items: list[str],
    seen: set[str],
    pack_id: str,
    *,
    line: int | None = None,
    column: int | None = None,
) -> None:
    if not isinstance(pack_id, str) or not pack_id.strip():
        raise Namel3ssError(
            build_guidance_message(
                what="Pack id is empty.",
                why="Every pack entry must be a non-empty string.",
                fix="Provide a pack id.",
                example='packs:\\n  "builtin.text"',
            ),
            line=line,
            column=column,
        )
    if pack_id in seen:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Duplicate pack "{pack_id}".',
                why="Each pack can be listed only once.",
                fix="Remove the duplicate entry.",
                example='packs:\\n  "builtin.text"',
            ),
            line=line,
            column=column,
        )
    seen.add(pack_id)
    items.append(pack_id)


__all__ = ["parse_packs"]
