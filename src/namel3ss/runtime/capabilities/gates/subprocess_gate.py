from __future__ import annotations

from namel3ss.runtime.capabilities.gates.base import (
    CapabilityViolation,
    REASON_GUARANTEE_ALLOWED,
    REASON_GUARANTEE_BLOCKED,
    build_block_message,
)
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext


def check_subprocess(ctx: CapabilityContext, record, *, argv: list[str]) -> None:
    source = ctx.guarantees.source_for_capability("subprocess") or "pack"
    if not ctx.guarantees.no_subprocess:
        record(
            CapabilityCheck(
                capability="subprocess",
                allowed=True,
                guarantee_source=source,
                reason=REASON_GUARANTEE_ALLOWED,
            )
        )
        return
    check = CapabilityCheck(
        capability="subprocess",
        allowed=False,
        guarantee_source=source,
        reason=REASON_GUARANTEE_BLOCKED,
    )
    record(check)
    command = " ".join(argv)
    message = build_block_message(
        tool_name=ctx.tool_name,
        action="cannot spawn subprocesses",
        why=f"Effective guarantees forbid subprocess execution ({command}).",
        example=f'[capability_overrides]\\n"{ctx.tool_name}" = {{ no_subprocess = true }}',
    )
    raise CapabilityViolation(message, check)


__all__ = ["check_subprocess"]
