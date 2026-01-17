from __future__ import annotations

from namel3ss.runtime.capabilities.gates import record_capability_check
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext, EffectiveGuarantees
from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION


PACK_PERMISSION_CAPABILITY = "pack_permission"


def record_pack_allowlist(
    ctx,
    *,
    tool_name: str,
    resolved_source: str,
    runner: str,
    allowed: bool,
) -> None:
    reason = "pack_declared" if allowed else "pack_not_declared"
    _record_pack_check(
        ctx,
        tool_name=tool_name,
        resolved_source=resolved_source,
        runner=runner,
        allowed=allowed,
        reason=reason,
        source="pack",
    )


def record_pack_policy(
    ctx,
    *,
    tool_name: str,
    resolved_source: str,
    runner: str,
    allowed: bool,
    policy_source: str | None,
) -> None:
    if not policy_source:
        return
    reason = "policy_denied" if not allowed else "policy_allowed"
    _record_pack_check(
        ctx,
        tool_name=tool_name,
        resolved_source=resolved_source,
        runner=runner,
        allowed=allowed,
        reason=reason,
        source="policy",
    )


def _record_pack_check(
    ctx,
    *,
    tool_name: str,
    resolved_source: str,
    runner: str,
    allowed: bool,
    reason: str,
    source: str,
) -> None:
    capability_ctx = CapabilityContext(
        tool_name=tool_name,
        resolved_source=resolved_source,
        runner=runner,
        protocol_version=PROTOCOL_VERSION,
        guarantees=EffectiveGuarantees(),
    )
    check = CapabilityCheck(
        capability=PACK_PERMISSION_CAPABILITY,
        allowed=allowed,
        guarantee_source=source,
        reason=reason,
    )
    record_capability_check(capability_ctx, check, _trace_target(ctx))


def _trace_target(ctx) -> list[dict]:
    return ctx.pending_tool_traces if getattr(ctx, "tool_call_source", None) == "ai" else ctx.traces


__all__ = ["PACK_PERMISSION_CAPABILITY", "record_pack_allowlist", "record_pack_policy"]
