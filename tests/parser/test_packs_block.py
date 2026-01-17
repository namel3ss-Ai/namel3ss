from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_packs_block_parses() -> None:
    source = """
packs:
  "builtin.text"
  "example.greeting"

flow "demo":
  return "ok"
"""
    program = parse_program(source)
    assert getattr(program, "pack_allowlist", None) == ["builtin.text", "example.greeting"]


def test_packs_block_rejects_duplicates() -> None:
    source = """
packs:
  "builtin.text"
  "builtin.text"

flow "demo":
  return "ok"
"""
    with pytest.raises(Namel3ssError):
        parse_program(source)
