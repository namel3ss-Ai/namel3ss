from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.diagnostics import reserved_identifier_message
from tests.conftest import parse_program


def test_unescaped_reserved_identifier_in_map_literal_has_exact_message() -> None:
    source = '''flow "demo":
  let payload is map:
    title is "Hello"
'''
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    err = excinfo.value
    assert err.message == reserved_identifier_message("title")
    assert err.details == {"error_id": "parse.reserved_identifier", "keyword": "title"}
