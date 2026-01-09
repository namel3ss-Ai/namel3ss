from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PerfBaseline:
    baseline_id: str
    traces_path: str
    max_trace_events: int
    max_ai_calls: int
    max_tool_calls: int


def load_perf_baseline(path: Path) -> tuple[PerfBaseline, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("perf baseline payload must be an object")
    raw_baselines = payload.get("baselines")
    if not isinstance(raw_baselines, list):
        raise ValueError("perf baseline payload missing baselines list")
    baselines: list[PerfBaseline] = []
    seen: set[str] = set()
    for entry in raw_baselines:
        if not isinstance(entry, dict):
            raise ValueError("perf baseline entry must be an object")
        baseline_id = entry.get("id")
        if not isinstance(baseline_id, str) or not baseline_id:
            raise ValueError("perf baseline entry missing id")
        if baseline_id in seen:
            raise ValueError(f"perf baseline duplicate id '{baseline_id}'")
        seen.add(baseline_id)
        traces_path = entry.get("traces")
        if not isinstance(traces_path, str) or not traces_path:
            raise ValueError(f"perf baseline '{baseline_id}' missing traces path")
        baselines.append(
            PerfBaseline(
                baseline_id=baseline_id,
                traces_path=traces_path,
                max_trace_events=_require_int(entry, "max_trace_events", baseline_id),
                max_ai_calls=_require_int(entry, "max_ai_calls", baseline_id),
                max_tool_calls=_require_int(entry, "max_tool_calls", baseline_id),
            )
        )
    return tuple(baselines)


def trace_counters(traces: list[dict]) -> dict[str, int]:
    events = list(_iter_canonical_events(traces))
    return {
        "trace_events": len(events),
        "ai_calls": sum(1 for event in events if event.get("type") == "ai_call_started"),
        "tool_calls": sum(1 for event in events if event.get("type") == "tool_call_started"),
    }


def _iter_canonical_events(traces: Iterable[dict]) -> Iterable[dict]:
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        events = trace.get("canonical_events")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    yield event
        agents = trace.get("agents")
        if isinstance(agents, list):
            for agent in agents:
                if not isinstance(agent, dict):
                    continue
                events = agent.get("canonical_events")
                if not isinstance(events, list):
                    continue
                for event in events:
                    if isinstance(event, dict):
                        yield event


def _require_int(entry: dict, name: str, baseline_id: str) -> int:
    value = entry.get(name)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"perf baseline '{baseline_id}' missing {name}")
    return value


__all__ = ["PerfBaseline", "load_perf_baseline", "trace_counters"]
