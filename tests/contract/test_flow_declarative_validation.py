from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_declarative_flow_unknown_record_errors() -> None:
    source = '''
flow "demo"
  create "Missing"
    name is "Ada"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Unknown record 'Missing'" in str(exc.value)


def test_declarative_flow_unknown_field_errors() -> None:
    source = '''
record "User":
  name is text

flow "demo"
  create "User"
    age is 1
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Unknown field 'age' in record 'User'" in str(exc.value)


def test_declarative_flow_missing_input_binding_errors() -> None:
    source = '''
record "User":
  name is text

flow "demo"
  input
    name is text
  create "User"
    name is input.missing
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Input field 'missing' is not declared" in str(exc.value)


def test_duplicate_flow_names_error() -> None:
    source = '''
flow "demo":
  return "ok"

flow "demo":
  return "ok"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Duplicate flow name 'demo'" in str(exc.value)


def test_reserved_flow_name_error() -> None:
    source = '''
flow "if":
  return "ok"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Flow name 'if' is reserved" in str(exc.value)
