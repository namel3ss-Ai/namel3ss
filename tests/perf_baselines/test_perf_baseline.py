from __future__ import annotations

import json
from pathlib import Path

from namel3ss.beta_lock.perf import load_perf_baseline, trace_counters

BASELINE_PATH = Path("tests/perf_baselines/agent_stack.json")


def test_perf_baseline_schema_version():
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == "perf_baselines.v1"


def test_perf_baselines_are_within_limits():
    baselines = load_perf_baseline(BASELINE_PATH)
    root = Path(__file__).resolve().parents[2]
    for baseline in baselines:
        trace_path = root / baseline.traces_path
        traces = json.loads(trace_path.read_text(encoding="utf-8"))
        counters = trace_counters(traces)
        assert counters["trace_events"] <= baseline.max_trace_events
        assert counters["ai_calls"] <= baseline.max_ai_calls
        assert counters["tool_calls"] <= baseline.max_tool_calls
