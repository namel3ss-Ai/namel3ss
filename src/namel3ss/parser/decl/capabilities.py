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
            parse_item=lambda: parser._expect("IDENT", "Expected capability name"),
            allow_empty=True,
        )
        for token in raw_items:
            _append_capability(items, seen, token.value, line=token.line, column=token.column)
        parser._match("NEWLINE")
    else:
        parser._expect("NEWLINE", "Expected newline after capabilities")
        parser._expect("INDENT", "Expected indented capabilities block")
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            token = parser._expect("IDENT", "Expected capability name")
            _append_capability(items, seen, token.value, line=token.line, column=token.column)
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


__all__ = ["parse_capabilities"]
