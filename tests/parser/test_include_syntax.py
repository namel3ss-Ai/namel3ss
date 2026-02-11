from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_include_parses_with_single_and_double_quotes() -> None:
    source = """
capabilities:
  composition.includes

include "modules/retrieval.ai"
include 'modules/flows.ai'

flow "demo":
  return "ok"
""".lstrip()
    program = parse_program(source)
    assert [entry.path_norm for entry in program.includes] == [
        "modules/retrieval.ai",
        "modules/flows.ai",
    ]


def test_include_rejects_parent_path_traversal() -> None:
    source = """
include "../shared.ai"
""".lstrip()
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "Parse error at line" in str(err.value)
    assert "include paths must be relative .ai files without '..'." in str(err.value)


def test_include_requires_top_level_position() -> None:
    source = """
flow "demo":
  return "ok"

include "modules/retrieval.ai"
""".lstrip()
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "Include directives must be declared before app declarations that use symbols." in str(err.value)
