from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lexer.lexer import Lexer


def test_empty_escaped_identifier_has_exact_error() -> None:
    source = "``"
    with pytest.raises(Namel3ssError) as excinfo:
        Lexer(source).tokenize()
    err = excinfo.value
    assert err.message == "Escaped identifier cannot be empty"
    assert err.line == 1
    assert err.column == 1


def test_unterminated_escaped_identifier_has_exact_error() -> None:
    source = "`name"
    with pytest.raises(Namel3ssError) as excinfo:
        Lexer(source).tokenize()
    err = excinfo.value
    assert err.message == "Unterminated escaped identifier"
    assert err.line == 1
    assert err.column == 1


def test_invalid_escaped_identifier_characters_have_exact_error() -> None:
    source = "`bad-name`"
    with pytest.raises(Namel3ssError) as excinfo:
        Lexer(source).tokenize()
    err = excinfo.value
    expected = build_guidance_message(
        what="Escaped identifier contains invalid characters.",
        why="Escaped identifiers use the same characters as normal identifiers.",
        fix="Use letters, numbers, or underscores inside the backticks.",
        example='let `title` is "..."',
    )
    assert err.message == expected
    assert err.line == 1
    assert err.column == 1
