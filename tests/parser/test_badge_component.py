from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_badge_item_binds_source_and_style() -> None:
    source = '''page "status":
  badge from state.status style is success
  badge from state.secondary
'''
    program = parse_program(source)
    items = program.pages[0].items
    badges = [item for item in items if isinstance(item, ast.BadgeItem)]
    assert len(badges) == 2
    assert badges[0].source.path == ["status"]
    assert badges[0].style == "success"
    assert badges[1].source.path == ["secondary"]
    assert badges[1].style == "neutral"


def test_badge_rejects_invalid_style_token() -> None:
    source = '''page "status":
  badge from state.status style is fancy
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    message = str(exc.value)
    assert "Badge style must be one of" in message
