from tests.conftest import run_flow


def test_if_at_least_branch():
    source = '''spec is "1.0"

flow "demo":
  let total is 10
  if total is at least 10:
    return "yes"
  else:
    return "no"
'''
    result = run_flow(source)
    assert result.last_value == "yes"


def test_if_at_most_branch():
    source = '''spec is "1.0"

flow "demo":
  let total is 5
  if total is at most 5:
    return "ok"
  else:
    return "no"
'''
    result = run_flow(source)
    assert result.last_value == "ok"


def test_if_not_equal_branch():
    source = '''spec is "1.0"

flow "demo":
  let total is 3
  if total is not 4:
    return "ne"
  else:
    return "eq"
'''
    result = run_flow(source)
    assert result.last_value == "ne"


def test_nested_if_executes_inner_branch():
    source = '''spec is "1.0"

flow "demo":
  let total is 12
  if total is greater than 10:
    if total is less than 20:
      return "mid"
    else:
      return "high"
  else:
    return "low"
'''
    result = run_flow(source)
    assert result.last_value == "mid"
