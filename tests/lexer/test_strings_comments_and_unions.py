from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.lexer.lexer import Lexer


def test_lexer_supports_escape_sequences() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let message is "line one\\nline two\\t\\"ok\\"\\\\end"\n'
    tokens = Lexer(source).tokenize()
    values = [tok.value for tok in tokens if tok.type == "STRING"]
    assert values[0] == "1.0"
    assert values[1] == 'demo'
    assert values[2] == 'line one\nline two\t"ok"\\end'


def test_lexer_supports_triple_quoted_multiline_strings() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let note is """line one\nline two"""\n'
    tokens = Lexer(source).tokenize()
    values = [tok.value for tok in tokens if tok.type == "STRING"]
    assert values[-1] == "line one\nline two"


def test_lexer_ignores_inline_comments() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let total is 1 # keep this comment\n'
    tokens = Lexer(source).tokenize()
    token_types = [tok.type for tok in tokens]
    assert "NUMBER" in token_types
    assert all(tok.value != "#" for tok in tokens)


def test_lexer_reports_unknown_escape_sequences() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let bad is "nope\\q"\n'
    with pytest.raises(Namel3ssError) as excinfo:
        Lexer(source).tokenize()
    assert "Unsupported escape sequence" in str(excinfo.value)
