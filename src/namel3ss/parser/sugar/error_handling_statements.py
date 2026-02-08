from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.diagnostics import expected_phrase_error


@dataclass
class AttemptOtherwiseStmt(ast.Statement):
    try_body: List[ast.Statement]
    catch_body: List[ast.Statement]


def parse_attempt_otherwise(parser) -> AttemptOtherwiseStmt:
    attempt_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after attempt")
    try_body = parser._parse_block()
    if not parser._match("OTHERWISE"):
        tok = parser._current()
        raise expected_phrase_error(
            tok,
            phrase="otherwise:",
            example="attempt:\n  return \"ok\"\notherwise:\n  return \"fallback\"",
        )
    parser._expect("COLON", "Expected ':' after otherwise")
    catch_body = parser._parse_block()
    return AttemptOtherwiseStmt(try_body=try_body, catch_body=catch_body, line=attempt_tok.line, column=attempt_tok.column)


__all__ = ["AttemptOtherwiseStmt", "parse_attempt_otherwise"]
