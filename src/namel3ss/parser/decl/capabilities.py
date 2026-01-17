from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import BUILTIN_CAPABILITIES, normalize_builtin_capability


def parse_capabilities(parser) -> list[str]:
    tok = parser._advance()
    parser._expect("COLON", "Expected ':' after capabilities")
    parser._expect("NEWLINE", "Expected newline after capabilities")
    parser._expect("INDENT", "Expected indented capabilities block")
    items: list[str] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._expect("IDENT", "Expected capability name")
        normalized = normalize_builtin_capability(name_tok.value)
        if normalized is None:
            allowed = ", ".join(BUILTIN_CAPABILITIES)
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown capability '{name_tok.value}'.",
                    why=f"Capabilities must be one of: {allowed}.",
                    fix="Use a supported capability name.",
                    example="capabilities:\n  http\n  jobs\n  files",
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        if normalized in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate capability '{normalized}'.",
                    why="Each capability can only be declared once.",
                    fix="Remove the duplicate entry.",
                    example="capabilities:\n  http\n  jobs",
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        seen.add(normalized)
        items.append(normalized)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of capabilities block")
    while parser._match("NEWLINE"):
        pass
    return items


__all__ = ["parse_capabilities"]
