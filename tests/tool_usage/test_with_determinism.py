import json

from namel3ss.tools_with.builder import build_tools_with_pack
from namel3ss.tools_with.render_plain import render_with


def test_with_determinism() -> None:
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
    pack_one = build_tools_with_pack(traces, project_root=None)
    pack_two = build_tools_with_pack(traces, project_root=None)
    assert json.dumps(pack_one.as_dict(), sort_keys=True) == json.dumps(pack_two.as_dict(), sort_keys=True)
    assert render_with(pack_one) == render_with(pack_two)
