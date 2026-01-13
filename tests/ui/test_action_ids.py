from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def test_button_action_id_is_slugified():
    source = '''page "home":
  button "Create user":
    calls flow "create_user"

flow "create_user":
  return "ok"
'''
    program = lower_ir_program(source)
    manifest = build_manifest(program)
    actions = manifest["actions"]
    assert "page.home.button.create_user" in actions
    button = manifest["pages"][0]["elements"][0]
    assert button["action_id"] == "page.home.button.create_user"


def test_duplicate_forms_receive_unique_ids():
    source = '''record "User":
  email string

page "home":
  form is "User"
  form is "User"

flow "create_user":
  return "ok"
'''
    program = lower_ir_program(source)
    manifest_one = build_manifest(program, state={})
    ids = sorted(manifest_one["actions"].keys())
    assert len(ids) == 2
    assert ids[0].startswith("page.home.form.user")
    manifest_two = build_manifest(program, state={})
    assert sorted(manifest_two["actions"].keys()) == ids
