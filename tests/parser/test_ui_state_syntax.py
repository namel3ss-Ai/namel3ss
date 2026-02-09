import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_ui_state_parses_scoped_fields() -> None:
    source = """spec is "1.0"

ui_state:
  ephemeral:
    stream_phase is text
  session:
    current_page is text
    drawer_open is boolean
  persistent:
    theme is ThemeSettings

page "Home":
  text is "Ready"
"""
    program = parse_program(source)
    ui_state = getattr(program, "ui_state", None)
    assert isinstance(ui_state, ast.UIStateDecl)
    assert [field.key for field in ui_state.ephemeral] == ["stream_phase"]
    assert [field.key for field in ui_state.session] == ["current_page", "drawer_open"]
    assert [field.key for field in ui_state.persistent] == ["theme"]
    assert ui_state.session[1].type_name == "boolean"


def test_ui_state_rejects_duplicate_key_across_scopes() -> None:
    source = """spec is "1.0"

ui_state:
  session:
    current_page is text
  persistent:
    current_page is text

page "Home":
  text is "Ready"
"""
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "already declared in scope" in str(exc.value)


def test_ui_state_scope_requires_fields() -> None:
    source = """spec is "1.0"

ui_state:
  session:

page "Home":
  text is "Ready"
"""
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "must declare at least one state key" in str(exc.value)
