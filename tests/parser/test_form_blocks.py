import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_form_groups_and_fields():
    source = '''record "User":
  name text
  email text

page "home":
  form is "User":
    groups:
      group "Main":
        field name
        field email
    fields:
      field name:
        help is "Your full name"
        readonly is true
      field email:
        help is "Work email"
'''
    program = parse_program(source)
    form = next(item for item in program.pages[0].items if isinstance(item, ast.FormItem))
    assert form.groups is not None
    assert form.groups[0].label == "Main"
    assert [ref.name for ref in form.groups[0].fields] == ["name", "email"]
    assert form.fields is not None
    assert form.fields[0].name == "name"
    assert form.fields[0].help == "Your full name"
    assert form.fields[0].readonly is True


def test_form_groups_require_field_entries():
    source = '''record "User":
  name text

page "home":
  form is "User":
    groups:
      group "Main":
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "group block has no fields" in str(exc.value).lower()


def test_form_fields_require_boolean_readonly():
    source = '''record "User":
  name text

page "home":
  form is "User":
    fields:
      field name:
        readonly is "yes"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "readonly must be true or false" in str(exc.value).lower()
