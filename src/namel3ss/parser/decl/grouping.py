from __future__ import annotations

from typing import Callable, TypeVar

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message

T = TypeVar("T")


_LAYOUT_TOKENS = {"NEWLINE", "INDENT", "DEDENT"}


def parse_bracketed_items(
    parser,
    *,
    context: str,
    parse_item: Callable[[], T],
    allow_empty: bool = True,
) -> list[T]:
    open_tok = parser._expect("LBRACKET", f"Expected '[' to start {context}")
    items: list[T] = []
    _reject_multiline_grouping(parser, context=context, group_name="Bracketed lists")
    if parser._match("RBRACKET"):
        if allow_empty:
            return items
        raise Namel3ssError(
            build_guidance_message(
                what=f"{context.title()} list is empty.",
                why=f"{context.title()} requires at least one entry.",
                fix="Add one or more entries.",
                example=f"{context}: [example]",
            ),
            line=open_tok.line,
            column=open_tok.column,
        )

    while True:
        tok = parser._current()
        _reject_multiline_grouping(parser, context=context, group_name="Bracketed lists")
        if tok.type in {"LBRACKET", "LBRACE"}:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Nested grouping is not allowed inside {context}.",
                    why="Bracketed lists only allow flat comma-separated entries.",
                    fix="Use simple values without nested [] or {}.",
                    example=f"{context}: [a, b, c]",
                ),
                line=tok.line,
                column=tok.column,
            )
        items.append(parse_item())
        if parser._match("COMMA"):
            _reject_multiline_grouping(parser, context=context, group_name="Bracketed lists")
            if parser._match("RBRACKET"):
                break
            continue
        tok = parser._current()
        if tok.type == "RBRACKET":
            parser._advance()
            break
        raise Namel3ssError(
            build_guidance_message(
                what=f"{context.title()} entries must be comma-separated.",
                why="Bracketed lists require commas between entries.",
                fix="Insert a comma between adjacent entries.",
                example=f"{context}: [first, second]",
            ),
            line=tok.line,
            column=tok.column,
        )
    return items


def parse_braced_items(
    parser,
    *,
    context: str,
    parse_item: Callable[[], T],
    allow_empty: bool = True,
) -> list[T]:
    open_tok = parser._expect("LBRACE", f"Expected '{{' to start {context}")
    items: list[T] = []
    _reject_multiline_grouping(parser, context=context, group_name="Braced blocks")
    if parser._match("RBRACE"):
        if allow_empty:
            return items
        raise Namel3ssError(
            build_guidance_message(
                what=f"{context.title()} block is empty.",
                why=f"{context.title()} requires at least one entry.",
                fix="Add one or more entries.",
                example=f"{context}: {{ entry }}",
            ),
            line=open_tok.line,
            column=open_tok.column,
        )

    while True:
        tok = parser._current()
        _reject_multiline_grouping(parser, context=context, group_name="Braced blocks")
        if tok.type in {"LBRACKET", "LBRACE"}:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Nested grouping is not allowed inside {context}.",
                    why="Braced blocks only allow flat comma-separated entries.",
                    fix="Remove nested [] or {} from this block.",
                    example=f"{context}: {{ item_one, item_two }}",
                ),
                line=tok.line,
                column=tok.column,
            )
        items.append(parse_item())
        if parser._match("COMMA"):
            _reject_multiline_grouping(parser, context=context, group_name="Braced blocks")
            if _at_closing_brace(parser):
                parser._advance()
                break
            continue
        if _at_closing_brace(parser):
            parser._advance()
            break
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what=f"{context.title()} entries must be comma-separated.",
                why="Braced blocks require commas between entries.",
                fix="Insert a comma between adjacent entries.",
                example=f"{context}: {{ first, second }}",
            ),
            line=tok.line,
            column=tok.column,
        )
    return items


def parse_named_value_block(parser, *, label: str, allow_strings: bool) -> list[str]:
    header_tok = parser._current()
    parser._expect("COLON", f"Expected ':' after {label}")
    if parser._current().type == "LBRACKET":
        entries = parse_bracketed_items(
            parser,
            context=label,
            parse_item=lambda: _parse_named_value_entry(
                parser,
                label=label,
                allow_strings=allow_strings,
            ),
            allow_empty=True,
        )
        parser._match("NEWLINE")
        values = _ensure_unique_entries(entries, label=label)
    else:
        parser._expect("NEWLINE", f"Expected newline after {label}")
        if not parser._match("INDENT"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"{label.title()} block has no entries.",
                    why=f"{label.title()} blocks require at least one entry.",
                    fix=f"Add one or more entries under {label}.",
                    example=f"{label}:\n  example",
                ),
                line=header_tok.line,
                column=header_tok.column,
            )
        entries = []
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            entries.append(_parse_named_value_entry(parser, label=label, allow_strings=allow_strings))
            parser._match("NEWLINE")
        parser._expect("DEDENT", f"Expected end of {label} block")
        while parser._match("NEWLINE"):
            pass
        values = _ensure_unique_entries(entries, label=label)
    return values


def _parse_named_value_entry(parser, *, label: str, allow_strings: bool) -> tuple[str, int | None, int | None]:
    tok = parser._current()
    if tok.type == "IDENT":
        parser._advance()
        value = str(tok.value)
    elif allow_strings and tok.type == "STRING":
        parser._advance()
        value = str(tok.value)
    else:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{label.title()} entries must be simple names.",
                why=f"{label.title()} lists allow identifiers (and quoted strings where documented).",
                fix="Use a single name entry.",
                example=f"{label}: [example]",
            ),
            line=tok.line,
            column=tok.column,
        )
    if not value.strip():
        raise Namel3ssError(
            build_guidance_message(
                what=f"{label.title()} entry is empty.",
                why=f"{label.title()} entries must contain non-empty text.",
                fix="Provide a non-empty entry.",
                example=f"{label}: [example]",
            ),
            line=tok.line,
            column=tok.column,
        )
    return value, tok.line, tok.column


def _ensure_unique_entries(values: list[tuple[str, int | None, int | None]], *, label: str) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value, line, column in values:
        if value in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate {label} entry '{value}'.",
                    why="Each entry may only appear once.",
                    fix="Remove the duplicate entry.",
                    example=f"{label}: [{value}]",
                ),
                line=line,
                column=column,
            )
        seen.add(value)
        normalized.append(value)
    return normalized


def _reject_multiline_grouping(parser, *, context: str, group_name: str) -> None:
    tok = parser._current()
    if tok.type not in _LAYOUT_TOKENS:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"{group_name} cannot span multiple lines in {context}.",
            why="Grouping delimiters are a compact single-line convenience form.",
            fix="Use indentation form for multi-line entries.",
            example=f"{context}:\n  first\n  second",
        ),
        line=tok.line,
        column=tok.column,
    )


def _at_closing_brace(parser) -> bool:
    return parser._current().type == "RBRACE"


__all__ = ["parse_bracketed_items", "parse_braced_items", "parse_named_value_block"]
