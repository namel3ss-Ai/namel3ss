from __future__ import annotations

import json
from pathlib import Path

from namel3ss.studio.agent_explain.payloads import build_agent_explain_payload

FIXTURE_DIR = Path("tests/fixtures")


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _single_payload() -> dict:
    traces = [
        {
            "type": "ai_call",
            "agent_name": "planner",
            "ai_profile_name": "assistant",
            "input": "Plan the task",
            "output": "Draft plan",
            "canonical_events": [
                {
                    "type": "ai_call_started",
                    "input_summary": "Plan the task",
                    "tools_declared_count": 1,
                },
                {
                    "type": "memory_recall",
                    "recalled": [{"text": "fact"}],
                    "recall_counts": {"session": 1},
                    "spaces_consulted": ["session"],
                },
                {"type": "memory_border_check", "reason": "policy:read"},
                {
                    "type": "tool_call_requested",
                    "tool_call_id": "tool-1",
                    "tool_name": "echo",
                    "arguments_summary": "{\"value\":1}",
                },
                {
                    "type": "tool_call_completed",
                    "tool_call_id": "tool-1",
                    "tool_name": "echo",
                    "result_summary": "{\"echo\":1}",
                },
            ],
        },
        {
            "type": "memory_handoff_created",
            "packet_id": "handoff-1",
            "from_agent_id": "planner",
            "to_agent_id": "reviewer",
            "title": "Memory handoff created",
            "lines": ["Packet id is handoff-1."],
        },
    ]
    return build_agent_explain_payload(traces, parallel=False)


def _parallel_payload() -> dict:
    traces = [
        {
            "type": "agent_merge_summary",
            "policy": "ranked",
            "selected_agents": ["beta"],
            "rejected_agents": ["alpha"],
            "lines": ["Merge policy is ranked."],
        },
        {
            "type": "agent_merge_selected",
            "policy": "ranked",
            "agent_name": "beta",
            "lines": ["Selected by merge policy."],
        },
        {
            "type": "agent_merge_rejected",
            "policy": "ranked",
            "agent_name": "alpha",
            "lines": ["Not selected by merge policy."],
        },
        {
            "type": "parallel_agents",
            "agents": [
                {
                    "type": "ai_call",
                    "agent_name": "alpha",
                    "ai_profile_name": "assistant",
                    "input": "task",
                    "output": "first",
                    "canonical_events": [{"type": "ai_call_started", "input_summary": "task"}],
                },
                {
                    "type": "ai_call",
                    "agent_name": "beta",
                    "ai_profile_name": "assistant",
                    "input": "task",
                    "output": "second",
                    "canonical_events": [{"type": "ai_call_started", "input_summary": "task"}],
                },
            ],
        },
    ]
    return build_agent_explain_payload(traces, parallel=True)


def test_agent_explain_single_payload_golden():
    payload = _single_payload()
    expected = _load_fixture("agent_explain_payload_single.json")
    assert payload == expected


def test_agent_explain_parallel_payload_golden():
    payload = _parallel_payload()
    expected = _load_fixture("agent_explain_payload_parallel.json")
    assert payload == expected
