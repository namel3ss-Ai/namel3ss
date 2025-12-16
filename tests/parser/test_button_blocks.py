import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


VALID = '''page "Home":
  button "Run":
    calls flow "demo"
'''


def test_button_block_parses():
    parse(VALID)


def test_one_line_button_rejected():
    src = '''page "Home":
  button "Run" calls flow "demo"
'''
    with pytest.raises(Namel3ssError) as excinfo:
        parse(src)
    assert "Buttons must use a block" in str(excinfo.value)


def test_button_missing_calls():
    src = '''page "Home":
  button "Run":
    title is "bad"
'''
    with pytest.raises(Namel3ssError):
        parse(src)
