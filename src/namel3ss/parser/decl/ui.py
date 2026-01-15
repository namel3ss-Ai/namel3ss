from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ui.settings import default_ui_settings_with_meta, validate_ui_field, validate_ui_value


def parse_ui_decl(parser):
    tok = parser._advance()
    parser._expect("COLON", "Expected ':' after ui")
    parser._expect("NEWLINE", "Expected newline after ui header")
    parser._expect("INDENT", "Expected indented ui block")
    settings = default_ui_settings_with_meta()
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if parser._current().type in {"IDENT", "THEME"}:
            name_tok = parser._advance()
        else:
            name_tok = parser._expect("IDENT", "Expected ui field name")
        key_name = name_tok.value
        if parser._current().type == "IDENT":
            next_tok = parser._advance()
            key_name = f"{key_name} {next_tok.value}"
        key = validate_ui_field(key_name, line=name_tok.line, column=name_tok.column)
        if key in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate ui field '{key}'.",
                    why="Each ui field can only be declared once.",
                    fix="Remove the duplicate field.",
                    example='ui:\n  theme is "light"\n  accent color is "blue"',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._expect("IS", "Expected 'is' after ui field name")
        value_tok = parser._expect("STRING", "Expected ui field value")
        validate_ui_value(key, value_tok.value, line=value_tok.line, column=value_tok.column)
        settings[key] = (value_tok.value, value_tok.line, value_tok.column)
        seen.add(key)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of ui block")
    while parser._match("NEWLINE"):
        continue
    return settings, tok.line, tok.column


__all__ = ["parse_ui_decl"]
