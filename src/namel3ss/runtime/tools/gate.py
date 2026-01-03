from __future__ import annotations

from namel3ss.runtime.tools.outcome import ToolDecision
from namel3ss.runtime.tools.policy import ToolPolicy


def gate_tool_call(
    *,
    tool_name: str,
    required_capabilities: tuple[str, ...],
    policy: ToolPolicy,
) -> ToolDecision:
    if not policy.known_tool:
        return ToolDecision(
            status="error",
            capability=None,
            reason="unknown_tool",
            message=f'Unknown tool "{tool_name}".',
        )
    if not policy.binding_ok:
        return ToolDecision(
            status="error",
            capability=None,
            reason="missing_binding",
            message=f'Tool "{tool_name}" is not bound to a runner.',
        )
    for capability in sorted({cap for cap in required_capabilities if isinstance(cap, str)}):
        if capability in policy.denied_capabilities:
            return ToolDecision(
                status="blocked",
                capability=capability,
                reason="policy_denied",
                message=f'Policy denied "{capability}" for tool "{tool_name}".',
            )
    return ToolDecision(
        status="allowed",
        capability=None,
        reason="policy_allowed",
        message=f'Tool "{tool_name}" is allowed.',
    )


__all__ = ["gate_tool_call"]
