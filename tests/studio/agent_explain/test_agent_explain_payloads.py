import hashlib
import json

from namel3ss.studio.agent_explain.payloads import build_agent_explain_payload


def _hash_value(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_agent_explain_single_summary_is_stable():
    traces = [
        {
            "type": "ai_call",
            "agent_name": "support",
            "ai_profile_name": "assistant",
            "input": "hello",
            "output": "ok",
            "canonical_events": [
                {"type": "ai_call_started", "input_summary": "hello", "tools_declared_count": 1},
                {
                    "type": "memory_recall",
                    "recalled": [{"text": "fact"}],
                    "recall_counts": {"session": 1},
                    "spaces_consulted": ["session"],
                },
                {"type": "memory_border_check", "reason": "policy:read"},
                {
                    "type": "tool_call_requested",
                    "tool_call_id": "1",
                    "tool_name": "echo",
                    "arguments_summary": "{\"value\":1}",
                },
                {
                    "type": "tool_call_completed",
                    "tool_call_id": "1",
                    "tool_name": "echo",
                    "result_summary": "{\"echo\":1}",
                },
            ],
        }
    ]
    payload = build_agent_explain_payload(traces, parallel=False)
    summary = payload["agent_run_summary"]
    assert summary["agent_id"] == "support"
    assert summary["agent_name"] == "support"
    assert summary["ai_profile"] == "assistant"
    assert summary["input_summary"] == "hello"
    assert summary["memory"]["recalled_count"] == 1
    assert summary["memory"]["spaces"] == ["session"]
    assert summary["memory"]["reasons"] == ["policy:read"]
    assert summary["tools"][0]["tool"] == "echo"
    assert summary["tools"][0]["status"] == "completed"
    assert summary["output_hash"] == _hash_value("ok")
    assert summary["memory_facts"]["counts"]["total"] == 0
    assert summary["memory_facts"]["keys"] == []
    assert summary["memory_facts"]["last_updated_step"] is None
    assert payload["memory_facts"][0]["agent_id"] == "support"


def test_agent_explain_parallel_summary_order_is_stable():
    traces = [
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
        }
    ]
    payload = build_agent_explain_payload(traces, parallel=True)
    parallel = payload["agent_parallel_summary"]
    assert parallel["merge_policy"] == "preserve_order"
    assert [entry["agent_id"] for entry in parallel["agents"]] == ["alpha", "beta"]


def test_agent_explain_parallel_merge_summary_is_used():
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
    payload = build_agent_explain_payload(traces, parallel=True)
    parallel = payload["agent_parallel_summary"]
    assert parallel["merge_policy"] == "ranked"
    assert parallel["merge_selected"] == ["beta"]
    assert parallel["merge_rejected"] == ["alpha"]
    assert "beta: Selected by merge policy." in parallel["merge_explanation"]
