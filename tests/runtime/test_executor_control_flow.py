import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_return_exits_loop():
    source = '''flow "ret":
  repeat up to 5 times:
    return "done"
    set state.result is "unreachable"
'''
    result = run_flow(source, flow_name="ret")
    assert result.last_value == "done"
    assert "result" not in result.state


def test_try_catch_handles_error_and_sets_message():
    source = '''flow "trycatch":
  try:
    set state.result is missing_var
  with catch error:
    set state.result is error.message
'''
    result = run_flow(source, flow_name="trycatch")
    assert result.state["result"]
    assert "unknown variable" in result.state["result"].lower()


def test_for_each_invalid_iterable_errors():
    source = '''flow "badfor":
  for each item in 123:
    set state.result is item
'''
    with pytest.raises(Namel3ssError) as exc:
        run_flow(source, flow_name="badfor")
    assert "expects a list" in str(exc.value).lower()


def test_repeat_invalid_count_errors():
    source = '''flow "badrepeat":
  repeat up to "hi" times:
    set state.result is "no"
'''
    with pytest.raises(Namel3ssError) as exc:
        run_flow(source, flow_name="badrepeat")
    assert "must be an integer" in str(exc.value).lower()

