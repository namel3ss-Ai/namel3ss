from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


def parse_app(parser):
    tok = parser._advance()
    parser._expect("COLON", "Expected ':' after app")
    parser._expect("NEWLINE", "Expected newline after app header")
    parser._expect("INDENT", "Expected indented app body")
    theme = "system"
    theme_line = tok.line
    theme_column = tok.column
    theme_tokens = {}
    theme_preference = {
        "allow_override": (False, None, None),
        "persist": ("none", None, None),
    }
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if parser._current().type == "THEME":
            parser._advance()
            parser._expect("IS", "Expected 'is' after theme")
            value_tok = parser._expect("STRING", "Expected theme value")
            theme = value_tok.value
            theme_line = value_tok.line
            theme_column = value_tok.column
            parser._match("NEWLINE")
            continue
        if parser._current().type == "THEME_TOKENS":
            parser._advance()
            parser._expect("COLON", "Expected ':' after theme_tokens")
            parser._expect("NEWLINE", "Expected newline after theme_tokens")
            parser._expect("INDENT", "Expected indented theme_tokens block")
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                name_tok = parser._expect("IDENT", "Expected token name")
                parser._expect("IS", "Expected 'is' after token name")
                value_tok = parser._expect("STRING", "Expected token value")
                theme_tokens[name_tok.value] = (value_tok.value, value_tok.line, value_tok.column)
                parser._match("NEWLINE")
            parser._expect("DEDENT", "Expected end of theme_tokens block")
            continue
        if parser._current().type == "THEME_PREFERENCE":
            parser._advance()
            parser._expect("COLON", "Expected ':' after theme_preference")
            parser._expect("NEWLINE", "Expected newline after theme_preference")
            parser._expect("INDENT", "Expected indented theme_preference block")
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                key_tok = parser._expect("IDENT", "Expected preference field")
                if key_tok.value == "allow_override":
                    parser._expect("IS", "Expected 'is' after allow_override")
                    if parser._match("BOOLEAN"):
                        val_tok = parser.tokens[parser.position - 1]
                        theme_preference["allow_override"] = (bool(val_tok.value), val_tok.line, val_tok.column)
                    else:
                        current = parser._current()
                        raise Namel3ssError("Expected true or false", line=current.line, column=current.column)
                    parser._match("NEWLINE")
                    continue
                if key_tok.value == "persist":
                    parser._expect("IS", "Expected 'is' after persist")
                    val_tok = parser._expect("STRING", "Expected persist value")
                    theme_preference["persist"] = (val_tok.value, val_tok.line, val_tok.column)
                    parser._match("NEWLINE")
                    continue
                raise Namel3ssError("Unknown theme_preference field", line=key_tok.line, column=key_tok.column)
            parser._expect("DEDENT", "Expected end of theme_preference block")
            continue
        tok = parser._current()
        raise Namel3ssError("Unexpected token in app block", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of app block")
    while parser._match("NEWLINE"):
        continue
    return theme, theme_line, theme_column, theme_tokens, theme_preference


__all__ = ["parse_app"]
