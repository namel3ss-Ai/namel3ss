from namel3ss.runtime.ui.actions import handle_action
from tests.conftest import lower_ir_program


SOURCE = '''flow "create_user":
  set state.result is "ok"
  return "done"

page "home":
  button "Create user":
    calls flow "create_user"
'''


def test_button_click_executes_flow():
    program = lower_ir_program(SOURCE)
    response = handle_action(program, action_id="page.home.button.create_user")
    assert response["state"]["result"] == "ok"
    assert response["result"] == "done"
    assert "page.home.button.create_user" in response["ui"]["actions"]
