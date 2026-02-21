import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


VALID = '''spec is "1.0"

page "Home":
  button "Run":
    calls flow "demo"
'''

VALID_WITH_ICON = '''spec is "1.0"

page "Home":
  button "Run":
    icon is add
    calls flow "demo"
'''


def test_button_block_parses():
    parse(VALID)


def test_button_icon_parses():
    parse(VALID_WITH_ICON)


def test_one_line_button_rejected():
    src = '''spec is "1.0"

page "Home":
  button "Run" calls flow "demo"
'''
    with pytest.raises(Namel3ssError) as excinfo:
        parse(src)
    assert "Buttons must use a block" in str(excinfo.value)


def test_button_missing_calls():
    src = '''spec is "1.0"

page "Home":
  button "Run":
    title is "bad"
'''
    with pytest.raises(Namel3ssError):
        parse(src)


def test_button_icon_unknown_rejected():
    src = '''spec is "1.0"

page "Home":
  button "Run":
    icon is not_a_real_icon_name
    calls flow "demo"
'''
    with pytest.raises(Namel3ssError) as excinfo:
        parse(src)
    assert "Unknown icon" in str(excinfo.value)
