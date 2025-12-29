from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse


def _field(program, name):
    record = program.records[0]
    return next(f for f in record.fields if f.name == name)


def test_canonical_types_remain_canonical():
    src = '''
spec is "1.0"

record "User":
  field "name" is text
  field "age" is number
  field "active" is boolean
'''
    program = parse(src)
    name_field = _field(program, "name")
    age_field = _field(program, "age")
    active_field = _field(program, "active")
    assert name_field.type_name == "text"
    assert age_field.type_name == "number"
    assert active_field.type_name == "boolean"
    assert not name_field.type_was_alias
    assert name_field.raw_type_name is None


def test_alias_types_normalize_in_ast_and_ir():
    src = '''
spec is "1.0"

record "User":
  field "name" is string
  field "age" is int
  field "active" is bool
'''
    program = parse(src)
    name_field = _field(program, "name")
    age_field = _field(program, "age")
    active_field = _field(program, "active")
    assert name_field.type_name == "text"
    assert age_field.type_name == "number"
    assert active_field.type_name == "boolean"
    assert name_field.type_was_alias and name_field.raw_type_name == "string"
    assert age_field.type_was_alias and age_field.raw_type_name == "int"
    assert active_field.type_was_alias and active_field.raw_type_name == "bool"
    ir_program = lower_program(parse(src))
    ir_field_types = {f.name: f.type_name for f in ir_program.records[0].fields}
    assert ir_field_types == {"name": "text", "age": "number", "active": "boolean"}
