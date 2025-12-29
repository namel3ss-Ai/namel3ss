from namel3ss.schema.records import RecordSchema
from tests.conftest import lower_ir_program


def test_lowering_record_declares_schema():
    source = '''record "User":
  email string must be unique
  age int

spec is "1.0"

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


def test_lowering_record_tenant_key_and_ttl():
    source = '''identity "user":
  field "org_id" is text must be present

record "Session":
  field "token" is text
  tenant_key is identity.org_id
  persisted:
    ttl_hours is 24
'''
    program = lower_ir_program(source)
    schema = program.records[0]
    assert schema.tenant_key == ["org_id"]
    assert str(schema.ttl_hours) == "24"
