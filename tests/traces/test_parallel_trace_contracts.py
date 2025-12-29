from tests.conftest import run_flow


def test_parallel_trace_lines_bracketless() -> None:
    code = """
flow "demo":
  parallel:
    run "beta":
      let beta is 2
      return beta
    run "alpha":
      let alpha is 1
      return alpha
"""
    result = run_flow(code)
    events = [
        event
        for event in result.traces
        if isinstance(event, dict)
        and event.get("type") in {"parallel_started", "parallel_task_finished", "parallel_merged"}
    ]
    bad_chars = {"(", ")", "[", "]", "{", "}"}
    for event in events:
        for line in event.get("lines") or []:
            assert not any(ch in line for ch in bad_chars)
