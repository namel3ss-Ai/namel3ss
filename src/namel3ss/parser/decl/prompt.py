from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_prompt_decl(parser) -> ast.PromptDefinition:
    prompt_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected prompt name string")
    parser._expect("COLON", "Expected ':' after prompt name")
    parser._expect("NEWLINE", "Expected newline after prompt header")
    parser._expect("INDENT", "Expected indented prompt block")

    version = None
    text = None
    description = None

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "TEXT":
            parser._advance()
            _ensure_unique("text", text, tok)
            parser._expect("IS", "Expected 'is' after text")
            value_tok = parser._expect("STRING", "Expected prompt text string")
            text = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "version"):
            _ensure_unique("version", version, tok)
            parser._expect("IS", "Expected 'is' after version")
            value_tok = parser._expect("STRING", "Expected version string")
            version = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "text"):
            _ensure_unique("text", text, tok)
            parser._expect("IS", "Expected 'is' after text")
            value_tok = parser._expect("STRING", "Expected prompt text string")
            text = value_tok.value
            parser._match("NEWLINE")
            continue
        if _match_ident(parser, "description"):
            _ensure_unique("description", description, tok)
            parser._expect("IS", "Expected 'is' after description")
            value_tok = parser._expect("STRING", "Expected description string")
            description = value_tok.value
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown prompt field '{tok.value}'.",
                why="Prompt blocks only allow version, text, and description.",
                fix="Remove the line or use a supported field.",
                example=(
                    'prompt "summary_prompt":\n'
                    '  version is "1.0.0"\n'
                    '  text is "Summarise the input."\n'
                    '  description is "Short summary."'
                ),
            ),
            line=tok.line,
            column=tok.column,
        )

    parser._expect("DEDENT", "Expected end of prompt block")
    while parser._match("NEWLINE"):
        pass

    if version is None:
        raise Namel3ssError("Prompt is missing a version", line=prompt_tok.line, column=prompt_tok.column)
    if text is None:
        raise Namel3ssError("Prompt is missing text", line=prompt_tok.line, column=prompt_tok.column)

    return ast.PromptDefinition(
        name=name_tok.value,
        version=version,
        text=text,
        description=description,
        line=prompt_tok.line,
        column=prompt_tok.column,
    )


def _ensure_unique(field: str, current: object | None, tok) -> None:
    if current is None:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"Prompt declares {field} more than once.",
            why="Each prompt field may only be declared once.",
            fix=f"Keep a single {field} entry.",
            example=f'{field} is "..."',
        ),
        line=tok.line,
        column=tok.column,
    )


def _match_ident(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


__all__ = ["parse_prompt_decl"]
