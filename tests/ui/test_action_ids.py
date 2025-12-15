from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def test_button_action_id_is_slugified():
    source = '''page "home":
  button "Create user" calls flow "create_user"

flow "create_user":
  return "ok"
'''
    program = lower_ir_program(source)
    manifest = build_manifest(program)
    actions = manifest["actions"]
    assert "page.home.button.create_user" in actions
    button = manifest["pages"][0]["elements"][0]
    assert button["action_id"] == "page.home.button.create_user"
