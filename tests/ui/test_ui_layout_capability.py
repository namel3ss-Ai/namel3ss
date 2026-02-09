import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_ui_layout_requires_capability() -> None:
    source = '''spec is "1.0"

page "Demo":
  stack:
    text is "Hi"
'''
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "UI layout requires capability ui_layout" in str(err.value)


def test_legacy_row_column_does_not_require_capability() -> None:
    source = '''spec is "1.0"

page "Legacy":
  row:
    column:
      text is "One"
'''
    program = lower_ir_program(source)
    assert program.pages

