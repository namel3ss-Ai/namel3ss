import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program, parse_program


def test_form_references_missing_record():
    source = '''flow "create_user":
  return "ok"

page "home":
  form is "User"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown record" in str(exc.value).lower()


def test_button_calls_missing_flow():
    source = '''page "home":
  button "Create user":
    calls flow "create_user"
    '''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown flow" in str(exc.value).lower()


def test_illegal_statement_in_page_block_errors():
    source = '''page "home":
  let x is 1
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "declarative" in str(exc.value).lower()
