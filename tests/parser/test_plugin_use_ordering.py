from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_use_plugin_must_appear_before_records_flows_and_pages() -> None:
    source = '''spec is "1.0"

flow "demo":
  return "ok"

use plugin "charts"

page "home":
  text is "hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Plugin declarations must appear before page, flow, and record definitions" in exc.value.message


def test_use_plugin_before_program_blocks_is_allowed() -> None:
    source = '''spec is "1.0"

use plugin "charts"
use plugin "maps"

record "Demo":
  field "value" is text

flow "demo":
  return "ok"

page "home":
  text is "hello"
'''
    program = parse_program(source)
    assert [item.name for item in program.plugin_uses] == ["charts", "maps"]
