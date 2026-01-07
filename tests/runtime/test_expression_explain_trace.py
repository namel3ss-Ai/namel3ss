from __future__ import annotations

from pathlib import Path

from namel3ss.determinism import canonical_trace_json
from namel3ss.module_loader import load_project
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.execution.explain import EXPLAIN_SAMPLE_LIMIT


SOURCE = '''spec is "1.0"

flow "demo":
  let numbers is list:
    1
    2
    3
  calc:
    doubled = map numbers with item as n:
      n * 2
    total = sum(doubled)
  return total
'''


TRUNCATION_SOURCE = '''spec is "1.0"

flow "demo":
  let numbers is list:
    1
    2
    3
    4
    5
    6
    7
    8
    9
    10
    11
    12
    13
    14
    15
    16
    17
    18
    19
    20
    21
    22
    23
    24
    25
  calc:
    doubled = map numbers with item as n:
      n * 2
  return doubled
'''


def _run_source(tmp_path: Path, source: str):
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    project = load_project(app_file)
    return execute_program_flow(project.program, "demo")


def _expression_traces(result) -> list[dict]:
    return [trace for trace in result.traces if isinstance(trace, dict) and trace.get("type") == "expression_explain"]


def test_expression_explain_trace_for_calc(tmp_path: Path) -> None:
    result = _run_source(tmp_path, SOURCE)
    traces = _expression_traces(result)
    targets = {trace.get("target") for trace in traces}
    assert "doubled" in targets
    assert "total" in targets

    total_trace = next(trace for trace in traces if trace.get("target") == "total")
    steps = total_trace.get("steps") or []
    agg_steps = [step for step in steps if step.get("kind") == "aggregation" and step.get("op") == "sum"]
    assert agg_steps
    assert agg_steps[0].get("input_count") == 3


def test_expression_explain_trace_truncates_samples(tmp_path: Path) -> None:
    result = _run_source(tmp_path, TRUNCATION_SOURCE)
    traces = _expression_traces(result)
    doubled = next(trace for trace in traces if trace.get("target") == "doubled")
    assert doubled.get("truncated") is True
    steps = doubled.get("steps") or []
    map_steps = [step for step in steps if step.get("kind") == "map"]
    assert map_steps
    assert len(map_steps[0].get("items", [])) == EXPLAIN_SAMPLE_LIMIT


def test_expression_explain_trace_deterministic(tmp_path: Path) -> None:
    result = _run_source(tmp_path, SOURCE)
    traces = _expression_traces(result)
    actual = canonical_trace_json(traces)
    expected = Path("tests/fixtures/expression_explain_trace_golden.json").read_text(encoding="utf-8")
    assert actual == expected
