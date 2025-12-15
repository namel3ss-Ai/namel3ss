from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def test_form_action_id_and_registry():
    source = '''record "User":
  email string must be unique
  name string must be present

page "home":
  form is "User"
  table is "User"
'''
    program = lower_ir_program(source)
    manifest = build_manifest(program)
    form = manifest["pages"][0]["elements"][0]
    assert form["action_id"] == "page.home.form.user"
    action = manifest["actions"]["page.home.form.user"]
    assert action["type"] == "submit_form"
    assert action["record"] == "User"
