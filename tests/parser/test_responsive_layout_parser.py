from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_responsive_breakpoints() -> None:
    source = '''
responsive:
  breakpoints:
    mobile: 0
    tablet: 640
    desktop: 1024

page "home":
  title is "Hello"
'''
    program = parse_program(source)
    responsive = getattr(program, "responsive_definition", None)
    assert responsive is not None
    names = [entry.name for entry in responsive.breakpoints]
    values = [entry.width for entry in responsive.breakpoints]
    assert names == ["mobile", "tablet", "desktop"]
    assert values == [0, 640, 1024]


def test_parse_responsive_rejects_unsorted_breakpoints() -> None:
    source = '''
capabilities:
  responsive_design

responsive:
  breakpoints:
    tablet: 640
    mobile: 0

page "home":
  title is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        from tests.conftest import lower_ir_program

        lower_ir_program(source)
    assert "smallest to largest" in str(exc.value)
