from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import BUILTIN_CAPABILITIES, normalize_builtin_capability
from namel3ss.parser.decl.grouping import parse_bracketed_items


def parse_capabilities(parser) -> list[str]:
    parser._advance()
    parser._expect("COLON", "Expected ':' after capabilities")
    items: list[str] = []
    seen: set[str] = set()
    if parser._current().type == "LBRACKET":
        raw_items = parse_bracketed_items(
            parser,
            context="capabilities",
            parse_item=lambda: _parse_capability_entry(parser),
            allow_empty=True,
        )
        for value, line, column in raw_items:
            _append_capability(items, seen, value, line=line, column=column)
        parser._match("NEWLINE")
    else:
        parser._expect("NEWLINE", "Expected newline after capabilities")
        parser._expect("INDENT", "Expected indented capabilities block")
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            value, line, column = _parse_capability_entry(parser)
            _append_capability(items, seen, value, line=line, column=column)
            parser._match("NEWLINE")
        parser._expect("DEDENT", "Expected end of capabilities block")
    while parser._match("NEWLINE"):
        pass
    return items


def _append_capability(
    items: list[str],
    seen: set[str],
    raw: str,
    *,
    line: int | None = None,
    column: int | None = None,
) -> None:
    normalized = normalize_builtin_capability(raw)
    if normalized is None:
        allowed = ", ".join(BUILTIN_CAPABILITIES)
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown capability '{raw}'.",
                why=f"Capabilities must be one of: {allowed}.",
                fix="Use a supported capability name.",
                example="capabilities:\n  http\n  jobs\n  scheduling\n  uploads\n  secrets\n  files",
            ),
            line=line,
            column=column,
        )
    if normalized in seen:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Duplicate capability '{normalized}'.",
                why="Each capability can only be declared once.",
                fix="Remove the duplicate entry.",
                example="capabilities:\n  http\n  scheduling",
            ),
            line=line,
            column=column,
        )
    seen.add(normalized)
    items.append(normalized)


def _parse_capability_entry(parser) -> tuple[str, int | None, int | None]:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        value = str(tok.value or "").strip()
        if value:
            return value, tok.line, tok.column
        raise Namel3ssError("Expected capability name", line=tok.line, column=tok.column)

    start_line = tok.line
    start_column = tok.column
    parts: list[str] = []
    while True:
        current = parser._current()
        if current.type in {"NEWLINE", "DEDENT", "COMMA", "RBRACKET", "EOF"}:
            break
        if current.type == "DOT":
            parts.append(".")
            parser._advance()
            continue
        value = current.value if isinstance(current.value, str) else None
        if value is None:
            break
        parts.append(value)
        parser._advance()
    capability = "".join(parts).strip()
    if not capability:
        bad = parser._current()
        raise Namel3ssError("Expected capability name", line=bad.line, column=bad.column)
    return capability, start_line, start_column


__all__ = ["parse_capabilities"]
