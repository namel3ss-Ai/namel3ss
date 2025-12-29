from namel3ss.tools_with.builder import build_tools_with_pack
from namel3ss.tools_with.render_plain import render_with


def test_blocked_tool_shows_reason_and_capability() -> None:
    traces = [
        {
            "type": "tool_call",
            "tool": "fetch data",
            "decision": "blocked",
            "capability": "network",
            "reason": "policy_denied",
            "result": "blocked",
        }
    ]
    pack = build_tools_with_pack(traces, project_root=None)
    text = render_with(pack)
    assert "reason: policy_denied" in text
    assert "capability: network" in text
