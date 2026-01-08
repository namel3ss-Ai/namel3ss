from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''record "User":
  name text must be present
  email text
  status text

page "home":
  form is "User":
    groups:
      group "Main":
        field name
        field email
    fields:
      field email:
        help is "Work email"
      field status:
        readonly is true
'''


def test_form_manifest_groups_help_readonly():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={})
    form = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "form")
    assert form["groups"] == [{"label": "Main", "fields": ["name", "email"]}]
    fields = {field["name"]: field for field in form["fields"]}
    assert fields["email"]["help"] == "Work email"
    assert fields["status"]["readonly"] is True
    assert "help" not in fields["name"]
    assert "readonly" not in fields["name"]
    assert any(constraint["kind"] == "present" for constraint in fields["name"]["constraints"])
