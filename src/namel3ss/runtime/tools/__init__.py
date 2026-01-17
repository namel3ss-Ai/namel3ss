from __future__ import annotations

__all__ = [
    "ToolCallOutcome",
    "ToolDecision",
    "ToolPolicy",
    "execute_tool_call",
    "gate_tool_call",
]


def __getattr__(name: str):
    if name in {"ToolCallOutcome", "ToolDecision"}:
        from namel3ss.runtime.tools.outcome import ToolCallOutcome, ToolDecision

        return {"ToolCallOutcome": ToolCallOutcome, "ToolDecision": ToolDecision}[name]
    if name == "ToolPolicy":
        from namel3ss.runtime.tools.policy import ToolPolicy

        return ToolPolicy
    if name == "execute_tool_call":
        from namel3ss.runtime.tools.executor import execute_tool_call

        return execute_tool_call
    if name == "gate_tool_call":
        from namel3ss.runtime.tools.gate import gate_tool_call

        return gate_tool_call
    raise AttributeError(f"module 'namel3ss.runtime.tools' has no attribute {name!r}")
