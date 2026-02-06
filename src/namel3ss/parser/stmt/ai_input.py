from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


TEXT_INPUT_MODE = "text"
STRUCTURED_INPUT_MODE = "structured"
IMAGE_INPUT_MODE = "image"
AUDIO_INPUT_MODE = "audio"


def parse_ai_input_clause(parser, *, context: str) -> tuple[object, str]:
    if _match_ident_value(parser, "structured") is not None:
        parser._expect("INPUT", f"Expected 'input' after 'structured' in {context}")
        _expect_ident_value(parser, "from", f"Expected 'from' after structured input in {context}")
        input_expr = parser._parse_expression()
        return input_expr, STRUCTURED_INPUT_MODE
    mode = _match_input_mode(parser)
    if mode is None:
        parser._expect("INPUT", f"Expected 'input' in {context}")
        mode = TEXT_INPUT_MODE
    else:
        parser._expect("INPUT", f"Expected 'input' after '{mode}' in {context}")
    parser._match("COLON")
    input_expr = parser._parse_expression()
    return input_expr, mode


def _match_input_mode(parser) -> str | None:
    tok = parser._current()
    if tok.type == "TEXT":
        parser._advance()
        return TEXT_INPUT_MODE
    if tok.type == "IMAGE":
        parser._advance()
        return IMAGE_INPUT_MODE
    if tok.type == "IDENT" and tok.value in {TEXT_INPUT_MODE, IMAGE_INPUT_MODE, AUDIO_INPUT_MODE}:
        parser._advance()
        return tok.value
    return None


def _match_ident_value(parser, value: str):
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return tok
    return None


def _expect_ident_value(parser, value: str, message: str):
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return tok
    raise Namel3ssError(message, line=tok.line, column=tok.column)


__all__ = ["parse_ai_input_clause"]
