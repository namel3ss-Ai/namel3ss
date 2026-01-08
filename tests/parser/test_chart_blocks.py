from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


RECORD_SOURCE = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart is "Metric":
    type is bar
    x is name
    y is value
    explain is "Value by name"
'''


STATE_SOURCE = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart from is state.metric:
    type is summary
'''


def test_parse_chart_block():
    program = parse_program(RECORD_SOURCE)
    chart = next(item for item in program.pages[0].items if isinstance(item, ast.ChartItem))
    assert chart.record_name == "Metric"
    assert chart.chart_type == "bar"
    assert chart.x == "name"
    assert chart.y == "value"
    assert chart.explain == "Value by name"


def test_parse_chart_from_state():
    program = parse_program(STATE_SOURCE)
    chart = next(item for item in program.pages[0].items if isinstance(item, ast.ChartItem))
    assert chart.record_name is None
    assert chart.source is not None
    assert chart.source.path == ["metric"]
    assert chart.chart_type == "summary"
