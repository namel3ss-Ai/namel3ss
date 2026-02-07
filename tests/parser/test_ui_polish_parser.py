from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_icon_semantic_requires_label() -> None:
    source = '''
page "home":
  icon name: "info" role: "semantic"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "requires label" in str(exc.value)


def test_grid_requires_columns() -> None:
    source = '''
page "home":
  grid:
    text is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Grid block requires columns" in str(exc.value)
