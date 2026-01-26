from __future__ import annotations

from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.lexer.lexer import Lexer


def test_lexer_emits_escaped_identifier_token() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let `row` is 1\n'
    tokens = Lexer(source).tokenize()
    escaped = [tok for tok in tokens if tok.type == "IDENT_ESCAPED"]
    assert len(escaped) == 1
    assert escaped[0].value == "row"
    assert escaped[0].escaped is True


def test_lexer_rejects_empty_escaped_identifier() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let `` is 1\n'
    with pytest.raises(Namel3ssError) as excinfo:
        Lexer(source).tokenize()
    assert "Escaped identifier cannot be empty" in str(excinfo.value)


def test_lexer_rejects_newline_inside_escape() -> None:
    source = "`row\nname`"
    with pytest.raises(Namel3ssError) as excinfo:
        Lexer(source).tokenize()
    assert "Unterminated escaped identifier" in str(excinfo.value)
    assert excinfo.value.line == 1


def test_lexer_regression_tokens_unchanged() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let total is 1\n'
    tokens = Lexer(source).tokenize()
    filtered = [
        (tok.type, tok.value)
        for tok in tokens
        if tok.type not in {"NEWLINE", "INDENT", "DEDENT", "EOF"}
    ]
    assert filtered == [
        ("SPEC", "spec"),
        ("IS", "is"),
        ("STRING", "1.0"),
        ("FLOW", "flow"),
        ("STRING", "demo"),
        ("COLON", ":"),
        ("LET", "let"),
        ("IDENT", "total"),
        ("IS", "is"),
        ("NUMBER", Decimal("1")),
    ]
    assert not any(tok.type == "IDENT_ESCAPED" for tok in tokens)
