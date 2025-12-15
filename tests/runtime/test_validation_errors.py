import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_setting_constant_raises_error():
    source = '''flow "const":
  let x is 1 constant
  set x is 2
'''
    with pytest.raises(Namel3ssError) as exc:
        run_flow(source, flow_name="const")
    assert "constant" in str(exc.value).lower()


def test_unknown_variable_in_condition_errors():
    source = '''flow "unknown":
  if missing is equal to 1:
    set state.result is "bad"
'''
    with pytest.raises(Namel3ssError) as exc:
        run_flow(source, flow_name="unknown")
    assert "unknown variable" in str(exc.value).lower()


def test_invalid_comparison_type_errors():
    source = '''flow "badcmp":
  if "hi" is greater than 3:
    set state.result is "bad"
'''
    with pytest.raises(Namel3ssError) as exc:
        run_flow(source, flow_name="badcmp")
    assert "require numbers" in str(exc.value).lower()

