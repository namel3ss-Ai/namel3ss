import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_permissions_requires_capability() -> None:
    source = '''spec is "1.0"

permissions:
  ai:
    call: allowed

flow "demo":
  return "ok"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "capability app_permissions" in str(exc.value)


def test_permissions_denied_ai_call_fails_compile() -> None:
    source = '''spec is "1.0"

capabilities:
  app_permissions

permissions:
  ai:
    call: denied

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "ai.call" in str(exc.value)


def test_permissions_denied_navigation_fails_compile() -> None:
    source = '''spec is "1.0"

capabilities:
  ui_navigation
  app_permissions

permissions:
  navigation:
    change_page: denied

page "Chat":
  button "Open settings":
    navigate_to "Settings"

page "Settings":
  text is "Ready"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "navigation.change_page" in str(exc.value)


def test_permissions_denied_persistent_state_write_fails_compile() -> None:
    source = '''spec is "1.0"

capabilities:
  ui_state
  app_permissions

permissions:
  ui_state:
    persistent_write: denied

ui_state:
  persistent:
    theme is text

flow "demo":
  set state.ui.theme is "dark"
  return state.ui.theme
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "ui_state.persistent_write" in str(exc.value)


def test_permissions_allowed_lowers_and_exposes_manifest_matrix() -> None:
    source = '''spec is "1.0"

capabilities:
  ui_navigation
  ui_state
  app_permissions

permissions:
  navigation:
    change_page: allowed
  ui_state:
    persistent_write: allowed

ui_state:
  persistent:
    theme is text

flow "save_theme":
  set state.ui.theme is "dark"
  return state.ui.theme

page "Chat":
  button "Open settings":
    navigate_to "Settings"

page "Settings":
  text is "Ready"
'''
    program = lower_ir_program(source)
    assert getattr(program, "app_permissions_enabled", False) is True
    matrix = getattr(program, "app_permissions", {})
    assert matrix["navigation.change_page"] is True
    assert matrix["ui_state.persistent_write"] is True
    usage = getattr(program, "app_permissions_usage", [])
    permissions_used = {entry.get("permission") for entry in usage if isinstance(entry, dict)}
    assert "navigation.change_page" in permissions_used
    assert "ui_state.persistent_write" in permissions_used
