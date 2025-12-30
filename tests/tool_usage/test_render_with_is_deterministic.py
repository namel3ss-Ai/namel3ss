from namel3ss.tools_with.builder import build_tools_with_pack
from namel3ss.tools_with.render_plain import render_with


def test_render_with_is_deterministic() -> None:
    traces = [
        {
            "type": "tool_call",
            "tool": "alpha",
            "decision": "allowed",
            "capability": "none",
            "reason": "policy_allowed",
            "result": "ok",
        },
        {
            "type": "tool_call",
            "tool": "beta",
            "decision": "blocked",
            "capability": "network",
            "reason": "policy_denied",
            "result": "blocked",
        },
    ]
    pack = build_tools_with_pack(traces, project_root=None)
    text_one = render_with(pack)
    text_two = render_with(pack)
    assert text_one == text_two
