from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


def _parse_variant_line(parser) -> str:
    key_tok = parser._current()
    if key_tok.type != "IDENT" or key_tok.value != "variant":
        raise Namel3ssError("Expected variant metadata", line=key_tok.line, column=key_tok.column)
    parser._advance()
    if parser._match("COLON"):
        pass
    else:
        parser._expect("IS", "Expected ':' or 'is' after variant")
    value_tok = parser._current()
    if value_tok.type == "STRING":
        parser._advance()
        return str(value_tok.value)
    if value_tok.type == "IDENT":
        parser._advance()
        return str(value_tok.value)
    raise Namel3ssError("variant must be an identifier or string", line=value_tok.line, column=value_tok.column)


def _parse_style_hooks_block(parser) -> dict[str, str]:
    key_tok = parser._current()
    if key_tok.type != "IDENT" or key_tok.value != "style_hooks":
        raise Namel3ssError("Expected style_hooks block", line=key_tok.line, column=key_tok.column)
    parser._advance()
    parser._expect("COLON", "Expected ':' after style_hooks")
    parser._expect("NEWLINE", "Expected newline after style_hooks")
    parser._expect("INDENT", "Expected indented style_hooks block")
    hooks: dict[str, str] = {}
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        hook_tok = parser._current()
        if hook_tok.type == "STRING" or not isinstance(hook_tok.value, str):
            raise Namel3ssError("Expected style hook name", line=hook_tok.line, column=hook_tok.column)
        parser._advance()
        hook_name = str(hook_tok.value)
        if parser._match("COLON"):
            pass
        else:
            parser._expect("IS", "Expected ':' or 'is' after style hook name")
        hook_value = _parse_token_reference(parser, context="style hook token")
        if hook_name in hooks:
            raise Namel3ssError(
                f'Duplicate style hook "{hook_name}".',
                line=hook_tok.line,
                column=hook_tok.column,
            )
        hooks[hook_name] = hook_value
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of style_hooks block")
    return hooks


def _parse_token_reference(parser, *, context: str) -> str:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return str(tok.value)
    if tok.type != "IDENT":
        raise Namel3ssError(f"Expected {context}.", line=tok.line, column=tok.column)
    parts = [str(tok.value)]
    parser._advance()
    while parser._match("DOT"):
        segment_tok = parser._current()
        if segment_tok.type == "IDENT":
            parts.append(str(segment_tok.value))
            parser._advance()
            continue
        if segment_tok.type == "NUMBER":
            parts.append(str(segment_tok.value))
            parser._advance()
            continue
        raise Namel3ssError(
            f"Expected token segment in {context}.",
            line=segment_tok.line,
            column=segment_tok.column,
        )
    return ".".join(parts)


__all__ = ["_parse_style_hooks_block", "_parse_variant_line"]
