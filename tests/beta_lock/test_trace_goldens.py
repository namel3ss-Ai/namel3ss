from __future__ import annotations

import json
from pathlib import Path

from namel3ss.traces.builders import (
    build_agent_merge_candidate,
    build_agent_merge_rejected,
    build_agent_merge_selected,
    build_agent_merge_started,
    build_agent_merge_summary,
    build_merge_applied,
    build_tool_call_allowed,
    build_tool_call_blocked,
    build_tool_call_completed,
    build_tool_call_failed,
    build_tool_call_finished,
    build_tool_call_proposed,
    build_tool_call_requested,
    build_tool_call_started,
    build_tool_loop_finished,
)

FIXTURE_DIR = Path("tests/fixtures")
TIMESTAMP = "2024-01-01T00:00:00+00:00"


def _load_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _stamp(events: list[dict]) -> list[dict]:
    stamped = []
    for event in events:
        payload = dict(event)
        if "timestamp" in payload:
            payload["timestamp"] = TIMESTAMP
        stamped.append(payload)
    return stamped


def test_tool_call_trace_golden():
    events = _stamp(
        [
            build_tool_call_requested(
                call_id="call-1",
                tool_call_id="tool-1",
                provider="mock",
                model="demo",
                tool_name="echo",
                arguments={"value": "hi"},
            ),
            build_tool_call_completed(
                call_id="call-1",
                tool_call_id="tool-1",
                provider="mock",
                model="demo",
                tool_name="echo",
                result={"echo": "hi"},
                duration_ms=12,
            ),
            build_tool_call_failed(
                call_id="call-1",
                tool_call_id="tool-2",
                provider="mock",
                model="demo",
                tool_name="fail",
                error_type="Boom",
                error_message="boom",
                duration_ms=5,
            ),
            build_tool_call_proposed(
                call_id="call-2",
                tool_call_id="tool-3",
                provider="mock",
                model="demo",
                tool_name="echo",
                arguments={"value": "hi"},
            ),
            build_tool_call_allowed(
                call_id="call-2",
                tool_call_id="tool-3",
                provider="mock",
                model="demo",
                tool_name="echo",
                reason="policy_allowed",
                capability=None,
            ),
            build_tool_call_started(
                call_id="call-2",
                tool_call_id="tool-3",
                provider="mock",
                model="demo",
                tool_name="echo",
            ),
            build_tool_call_finished(
                call_id="call-2",
                tool_call_id="tool-3",
                provider="mock",
                model="demo",
                tool_name="echo",
                status="ok",
                result={"echo": "hi"},
                error_message=None,
                duration_ms=12,
            ),
            build_tool_loop_finished(
                call_id="call-2",
                provider="mock",
                model="demo",
                tool_call_count=1,
                stop_reason="assistant_text",
            ),
            build_tool_call_blocked(
                call_id="call-3",
                tool_call_id="tool-4",
                provider="mock",
                model="demo",
                tool_name="secret",
                reason="policy_denied",
                message="Policy denied \"secrets\" for tool \"secret\".",
                capability="secrets",
            ),
        ]
    )
    expected = _load_fixture("tool_call_trace_golden.json")
    assert events == expected


def test_agent_merge_trace_golden():
    events = [
        build_agent_merge_started(
            policy="ranked",
            candidate_count=2,
            title="Agent merge started",
            lines=["Merge policy is ranked.", "Candidate count is 2."],
        ),
        build_agent_merge_candidate(
            policy="ranked",
            agent_name="alpha",
            status="valid",
            score="2",
            title="Agent merge candidate",
            lines=["Score is 2."],
        ),
        build_agent_merge_selected(
            policy="ranked",
            agent_name="beta",
            score="3",
            title="Agent merge selected",
            lines=["Selected by merge policy."],
        ),
        build_agent_merge_rejected(
            policy="ranked",
            agent_name="alpha",
            score="2",
            title="Agent merge rejected",
            lines=["Not selected by merge policy."],
        ),
        build_agent_merge_summary(
            policy="ranked",
            selected_agents=["beta"],
            rejected_agents=["alpha"],
            title="Agent merge summary",
            lines=["Merge policy is ranked."],
        ),
        build_merge_applied(
            policy="ranked",
            selected_agents=["beta"],
            rejected_agents=["alpha"],
            title="Merge applied",
            lines=[
                "Merge applied.",
                "Merge policy is ranked.",
                "Selected agents: beta.",
                "Rejected agents count is 1.",
            ],
        ),
    ]
    expected = _load_fixture("agent_merge_trace_golden.json")
    assert events == expected
