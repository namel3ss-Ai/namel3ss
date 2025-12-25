from __future__ import annotations

from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext


def record_capability_check(
    ctx: CapabilityContext,
    check: CapabilityCheck,
    traces: list[dict[str, object]],
) -> None:
    if check.allowed and check.capability in ctx.allowed_emitted:
        return
    if check.allowed:
        ctx.allowed_emitted.add(check.capability)
    traces.append(_build_event(ctx, check))


def record_capability_checks(
    ctx: CapabilityContext,
    checks: list[object],
    traces: list[dict[str, object]],
) -> None:
    for item in checks:
        check = _coerce_check(item)
        if check is None:
            continue
        record_capability_check(ctx, check, traces)


def _build_event(ctx: CapabilityContext, check: CapabilityCheck) -> dict[str, object]:
    payload = {
        "type": "capability_check",
        "tool_name": ctx.tool_name,
        "runner": ctx.runner,
        "resolved_source": ctx.resolved_source,
        "capability": check.capability,
        "allowed": check.allowed,
        "guarantee_source": check.guarantee_source,
        "reason": check.reason,
        "protocol_version": ctx.protocol_version,
    }
    if check.duration_ms is not None:
        payload["duration_ms"] = check.duration_ms
    return payload


def _coerce_check(item: object) -> CapabilityCheck | None:
    if isinstance(item, CapabilityCheck):
        return item
    if isinstance(item, dict):
        capability = item.get("capability")
        allowed = item.get("allowed")
        guarantee_source = item.get("guarantee_source")
        reason = item.get("reason")
        if not isinstance(capability, str) or not isinstance(allowed, bool):
            return None
        if not isinstance(guarantee_source, str) or not isinstance(reason, str):
            return None
        duration_ms = item.get("duration_ms")
        duration_val = int(duration_ms) if isinstance(duration_ms, int) else None
        return CapabilityCheck(
            capability=capability,
            allowed=allowed,
            guarantee_source=guarantee_source,
            reason=reason,
            duration_ms=duration_val,
        )
    return None


__all__ = ["record_capability_check", "record_capability_checks"]
