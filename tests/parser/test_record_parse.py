from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


RECORD_DECL = '''record "User":
  email string must be unique
  name string must be present
  age int must be greater than 18
'''


def test_parse_record_declaration_with_constraints():
    program = parse_program(RECORD_DECL)
    assert program.records
    user = program.records[0]
    assert user.name == "User"
    assert len(user.fields) == 3
    assert user.fields[0].constraint.kind == "unique"
    assert user.fields[1].constraint.kind == "present"
    assert user.fields[2].constraint.kind == "gt"


def test_parse_record_tenant_key_and_ttl():
    source = '''record "Session":
  field "token" is text
  tenant_key is identity.org_id
  persisted:
    ttl_hours is 24
'''
    program = parse_program(source)
    record = program.records[0]
    assert isinstance(record.tenant_key, ast.AttrAccess)
    assert record.tenant_key.base == "identity"
    assert record.tenant_key.attrs == ["org_id"]
    assert isinstance(record.ttl_hours, ast.Literal)
    assert str(record.ttl_hours.value) == "24"
