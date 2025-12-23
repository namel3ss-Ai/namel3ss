from decimal import Decimal

from namel3ss.format.formatter import format_source
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''record "Applicant":
  field "email" is string must be present
  field "name" is string must be unique
  field "bio" is string must have length at least 3
  field "summary" is string must have length at most 12
  field "code" is string must match pattern "^[A-Z]{3}-[0-9]{2}$"
  field "age" is number must be greater than 17
  field "score" is number must be less than 101

page "home":
  title is "Test"
  form is "Applicant"
'''


def test_record_fields_with_is_and_constraints_parse_and_lower():
    program = lower_ir_program(SOURCE)
    assert program.records
    record = program.records[0]
    fields = {f.name: f for f in record.fields}

    assert fields["email"].type_name == "text"
    assert fields["email"].constraint.kind == "present"

    assert fields["name"].type_name == "text"
    assert fields["name"].constraint.kind == "unique"

    assert fields["bio"].type_name == "text"
    assert fields["bio"].constraint.kind == "len_min"
    assert fields["bio"].constraint.expression.value == Decimal("3")

    assert fields["summary"].type_name == "text"
    assert fields["summary"].constraint.kind == "len_max"
    assert fields["summary"].constraint.expression.value == Decimal("12")

    assert fields["code"].type_name == "text"
    assert fields["code"].constraint.kind == "pattern"
    assert fields["code"].constraint.pattern == "^[A-Z]{3}-[0-9]{2}$"

    assert fields["age"].constraint.kind == "gt"
    assert fields["age"].constraint.expression.value == Decimal("17")

    assert fields["score"].constraint.kind == "lt"
    assert fields["score"].constraint.expression.value == Decimal("101")

    manifest = build_manifest(program, state={}, store=MemoryStore())
    assert any(el["type"] == "form" for el in manifest["pages"][0]["elements"])


def test_formatter_keeps_is_in_field_lines():
    formatted = format_source(SOURCE)
    for line in formatted.splitlines():
        if line.strip().startswith("field"):
            assert " is " in line
    assert 'field "email" string must be present' not in formatted
