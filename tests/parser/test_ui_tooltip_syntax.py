from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_tooltip_item() -> None:
    source = '''
page "home":
  tooltip "Blend retrieval modes." for "Semantic weight"
'''.lstrip()
    program = parse_program(source)
    tooltip = next(item for item in program.pages[0].items if isinstance(item, ast.TooltipItem))
    assert tooltip.text == "Blend retrieval modes."
    assert tooltip.anchor_label == "Semantic weight"
    assert tooltip.collapsed_by_default is True


def test_tooltip_empty_text_is_parse_error() -> None:
    source = '''
page "home":
  tooltip "" for "Semantic weight"
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "tooltip text cannot be empty." in str(err.value)

