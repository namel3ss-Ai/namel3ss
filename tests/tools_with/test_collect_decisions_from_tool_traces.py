from namel3ss.tools_with.builder import build_tools_with_pack


def test_build_tools_with_pack_from_traces() -> None:
    traces = [
        {
            "type": "tool_call",
            "tool": "greet someone",
            "decision": "blocked",
            "capability": "network",
            "reason": "policy_denied",
            "result": "blocked",
        },
        {
            "type": "tool_call",
            "tool": "echo",
            "decision": "allowed",
            "capability": "none",
            "reason": "policy_allowed",
            "result": "ok",
        },
    ]
    pack = build_tools_with_pack(traces, project_root=None)
    assert pack.tools_called == 2
    assert len(pack.allowed) == 1
    assert len(pack.blocked) == 1
    assert len(pack.errors) == 0
