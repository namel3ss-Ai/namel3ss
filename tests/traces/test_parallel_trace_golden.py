from pathlib import Path
import json

from tests.conftest import run_flow


def test_parallel_trace_goldens() -> None:
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
    events = [event for event in result.traces if isinstance(event, dict)]
    started = [event for event in events if event.get("type") == "parallel_started"]
    finished = [event for event in events if event.get("type") == "parallel_task_finished"]
    merged = [event for event in events if event.get("type") == "parallel_merged"]
    assert len(started) == 1
    assert len(merged) == 1

    golden_dir = Path("tests/golden/parallel_traces/traces")
    expected_started = json.loads((golden_dir / "parallel_started.json").read_text(encoding="utf-8"))
    expected_finished = json.loads((golden_dir / "parallel_task_finished.json").read_text(encoding="utf-8"))
    expected_merged = json.loads((golden_dir / "parallel_merged.json").read_text(encoding="utf-8"))

    assert started[0] == expected_started
    assert finished == expected_finished
    assert merged[0] == expected_merged
