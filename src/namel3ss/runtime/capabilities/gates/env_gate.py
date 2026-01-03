from __future__ import annotations

from namel3ss.runtime.capabilities.gates.base import (
    CapabilityViolation,
    REASON_GUARANTEE_ALLOWED,
    REASON_GUARANTEE_BLOCKED,
    build_block_message,
)
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext


def check_env_read(ctx: CapabilityContext, record, *, key: str) -> None:
    source = ctx.guarantees.source_for_capability("env_read") or "pack"
    if not ctx.guarantees.no_env_read:
        record(
            CapabilityCheck(
                capability="env_read",
                allowed=True,
                guarantee_source=source,
                reason=REASON_GUARANTEE_ALLOWED,
            )
        )
        return
    check = CapabilityCheck(
        capability="env_read",
        allowed=False,
        guarantee_source=source,
        reason=REASON_GUARANTEE_BLOCKED,
    )
    record(check)
    message = build_block_message(
        tool_name=ctx.tool_name,
        action="cannot read environment variables",
        why=f"Effective guarantees forbid env reads ({key}).",
        example=f'[capability_overrides]\\n"{ctx.tool_name}" = {{ no_env_read = true }}',
    )
    raise CapabilityViolation(message, check)


def check_env_write(ctx: CapabilityContext, record, *, key: str) -> None:
    source = ctx.guarantees.source_for_capability("env_write") or "pack"
    if not ctx.guarantees.no_env_write:
        record(
            CapabilityCheck(
                capability="env_write",
                allowed=True,
                guarantee_source=source,
                reason=REASON_GUARANTEE_ALLOWED,
            )
        )
        return
    check = CapabilityCheck(
        capability="env_write",
        allowed=False,
        guarantee_source=source,
        reason=REASON_GUARANTEE_BLOCKED,
    )
    record(check)
    message = build_block_message(
        tool_name=ctx.tool_name,
        action="cannot write environment variables",
        why=f"Effective guarantees forbid env writes ({key}).",
        example=f'[capability_overrides]\\n"{ctx.tool_name}" = {{ no_env_write = true }}',
    )
    raise CapabilityViolation(message, check)


__all__ = ["check_env_read", "check_env_write"]
