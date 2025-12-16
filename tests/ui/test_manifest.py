from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''record "User":
  email string must be unique
  name string must be present

flow "create_user":
  return "ok"

page "home":
  title is "Welcome"
  text is "Hello"
  form is "User"
  table is "User"
  button "Create user":
    calls flow "create_user"
'''


def test_manifest_expands_records_and_actions():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program)
    assert manifest["pages"][0]["name"] == "home"
    elements = manifest["pages"][0]["elements"]
    form = next(e for e in elements if e["type"] == "form")
    assert form["record"] == "User"
    assert any(f["name"] == "email" for f in form["fields"])
    table = next(e for e in elements if e["type"] == "table")
    assert table["columns"][0]["name"] == "email"
    button = next(e for e in elements if e["type"] == "button")
    assert button["action"] == {"type": "call_flow", "flow": "create_user"}
