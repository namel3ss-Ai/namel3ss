from namel3ss.schema.records import RecordSchema
from tests.conftest import lower_ir_program


def test_lowering_record_declares_schema():
    source = '''record "User":
  email string must be unique
  age int

flow "demo":
  save User
'''
    program = lower_ir_program(source)
    assert program.records
    schema = program.records[0]
    assert isinstance(schema, RecordSchema)
    assert schema.name == "User"
    assert any(f.name == "email" for f in schema.fields)
    assert "email" in schema.unique_fields
