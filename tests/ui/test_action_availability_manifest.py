from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''flow "submit_flow":
  return "ok"

page "home":
  button "Submit":
    calls flow "submit_flow"
      only when state.status is "ready"
'''


def _build(state: dict) -> dict:
    program = lower_ir_program(SOURCE)
    program.state_defaults = {"status": "ready"}
    return build_manifest(program, state=state, store=None)


def test_action_availability_enabled_when_match():
    manifest = _build({"status": "ready"})
    action = manifest["actions"]["page.home.button.submit"]
    assert action["enabled"] is True
    assert action["availability"]["predicate"] == 'state.status is "ready"'
    button = next(el for el in manifest["pages"][0]["elements"] if el.get("type") == "button")
    assert button["enabled"] is True


def test_action_availability_disabled_when_mismatch():
    manifest = _build({"status": "loading"})
    action = manifest["actions"]["page.home.button.submit"]
    assert action["enabled"] is False
    button = next(el for el in manifest["pages"][0]["elements"] if el.get("type") == "button")
    assert button["enabled"] is False


def test_action_availability_missing_state_path_errors():
    program = lower_ir_program(SOURCE)
    program.state_defaults = {"other": "ready"}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"status": "ready"}, store=None)
    assert "requires declared state path 'state.status'" in str(exc.value)


def test_action_availability_type_mismatch_errors():
    program = lower_ir_program(SOURCE)
    program.state_defaults = {"status": True}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"status": True}, store=None)
    assert "expects text but state value is boolean" in str(exc.value)


def test_action_availability_is_deterministic():
    first = _build({"status": "ready"})
    second = _build({"status": "ready"})
    assert first == second
