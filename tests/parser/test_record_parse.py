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

