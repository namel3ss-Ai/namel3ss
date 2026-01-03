from __future__ import annotations

from namel3ss.runtime.capabilities.gates.base import (
    CapabilityViolation,
    REASON_GUARANTEE_ALLOWED,
    REASON_SECRETS_ALLOWED,
    REASON_SECRETS_BLOCKED,
    build_block_message,
)
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext


def check_secret_allowed(ctx: CapabilityContext, record, *, secret_name: str) -> None:
    allowed = ctx.guarantees.secrets_allowed
    if allowed is None:
        check = CapabilityCheck(
            capability="secrets",
            allowed=True,
            guarantee_source=_source(ctx),
            reason=REASON_GUARANTEE_ALLOWED,
        )
        record(check)
        return
    if secret_name in allowed:
        check = CapabilityCheck(
            capability="secrets",
            allowed=True,
            guarantee_source=_source(ctx),
            reason=REASON_SECRETS_ALLOWED,
        )
        record(check)
        return
    check = CapabilityCheck(
        capability="secrets",
        allowed=False,
        guarantee_source=_source(ctx),
        reason=REASON_SECRETS_BLOCKED,
    )
    record(check)
    message = build_block_message(
        tool_name=ctx.tool_name,
        action="cannot access secrets",
        why=f"Effective guarantees only allow secrets {sorted(allowed)} (requested: {secret_name}).",
        example=f'[capability_overrides]\\n"{ctx.tool_name}" = {{ secrets_allowed = ["{secret_name}"] }}',
    )
    raise CapabilityViolation(message, check)


def _source(ctx: CapabilityContext) -> str:
    return ctx.guarantees.source_for_capability("secrets") or "pack"


__all__ = ["check_secret_allowed"]
