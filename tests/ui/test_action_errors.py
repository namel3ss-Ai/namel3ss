import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.actions import handle_action
from tests.conftest import lower_ir_program


def test_unknown_action_id_errors():
    program = lower_ir_program('spec is "1.0"\n\nflow "demo":\n  return "ok"\n')
    with pytest.raises(Namel3ssError) as exc:
        handle_action(program, action_id="page.home.button.missing")
    assert "unknown action" in str(exc.value).lower()


def test_payload_mapping_into_flow():
    source = '''flow "echo":
  set state.last is input.message
  return input.message

page "home":
  button "Send":
    calls flow "echo"
'''
    program = lower_ir_program(source)
    response = handle_action(program, action_id="page.home.button.send", payload={"message": "hi"})
    assert response["state"]["last"] == "hi"
    assert response["result"] == "hi"
