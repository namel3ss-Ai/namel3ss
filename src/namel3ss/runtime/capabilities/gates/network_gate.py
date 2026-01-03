from __future__ import annotations

from namel3ss.runtime.capabilities.gates.base import (
    CapabilityViolation,
    REASON_GUARANTEE_ALLOWED,
    REASON_GUARANTEE_BLOCKED,
    build_block_message,
)
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext


def check_network(ctx: CapabilityContext, record, *, url: str, method: str) -> None:
    source = ctx.guarantees.source_for_capability("network") or "pack"
    if not ctx.guarantees.no_network:
        record(
            CapabilityCheck(
                capability="network",
                allowed=True,
                guarantee_source=source,
                reason=REASON_GUARANTEE_ALLOWED,
            )
        )
        return
    check = CapabilityCheck(
        capability="network",
        allowed=False,
        guarantee_source=source,
        reason=REASON_GUARANTEE_BLOCKED,
    )
    record(check)
    message = build_block_message(
        tool_name=ctx.tool_name,
        action="cannot use the network",
        why=f"Effective guarantees forbid network access ({method.upper()} {url}).",
        example=f'[capability_overrides]\\n"{ctx.tool_name}" = {{ no_network = true }}',
    )
    raise CapabilityViolation(message, check)


__all__ = ["check_network"]
