import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_ui_state_requires_capability() -> None:
    source = """spec is "1.0"

ui_state:
  session:
    current_page is text

page "Home":
  text is "Ready"
"""
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "capability ui_state" in str(exc.value)


def test_ui_state_rejects_undeclared_read() -> None:
    source = """spec is "1.0"

capabilities:
  ui_state

ui_state:
  session:
    drawer_open is boolean

flow "demo":
  return state.ui.current_page
"""
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "not declared in ui_state" in str(exc.value)


def test_ui_state_rejects_undeclared_write() -> None:
    source = """spec is "1.0"

capabilities:
  ui_state

ui_state:
  session:
    current_page is text

flow "demo":
  set state.ui.drawer_open is true
  return "ok"
"""
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Write to undeclared ui_state key" in str(exc.value)


def test_ui_state_lowers_and_sets_defaults() -> None:
    source = """spec is "1.0"

capabilities:
  ui_state

ui_state:
  session:
    current_page is text
    drawer_open is boolean
  persistent:
    theme is text

flow "demo":
  set state.ui.current_page is "Settings"
  return state.ui.current_page

page "Home":
  text is "Ready"
"""
    program = lower_ir_program(source)
    ui_state = getattr(program, "ui_state", None)
    assert ui_state is not None
    assert [field.key for field in ui_state.session] == ["current_page", "drawer_open"]
    defaults = getattr(program, "state_defaults", None) or {}
    assert defaults == {"ui": {"current_page": "", "drawer_open": False, "theme": ""}}
