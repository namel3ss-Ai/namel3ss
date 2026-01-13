from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.capabilities.gates.base import (
    CapabilityViolation,
    REASON_GUARANTEE_ALLOWED,
    REASON_GUARANTEE_BLOCKED,
    build_block_message,
)
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext
from namel3ss.utils.path_display import display_path


def check_filesystem(ctx: CapabilityContext, record, *, path: Path | str, mode: str) -> None:
    operation = "filesystem_read"
    deny = ctx.guarantees.no_filesystem_read
    if _is_write_mode(mode):
        operation = "filesystem_write"
        deny = ctx.guarantees.no_filesystem_write
    source = ctx.guarantees.source_for_capability(operation) or "pack"
    if not deny:
        record(
            CapabilityCheck(
                capability=operation,
                allowed=True,
                guarantee_source=source,
                reason=REASON_GUARANTEE_ALLOWED,
            )
        )
        return
    check = CapabilityCheck(
        capability=operation,
        allowed=False,
        guarantee_source=source,
        reason=REASON_GUARANTEE_BLOCKED,
    )
    record(check)
    target = _path_label(path)
    action = "cannot write to the filesystem" if operation == "filesystem_write" else "cannot read from the filesystem"
    message = build_block_message(
        tool_name=ctx.tool_name,
        action=action,
        why=f"Effective guarantees forbid filesystem access ({target}).",
        example=f'[capability_overrides]\\n"{ctx.tool_name}" = {{ no_filesystem_write = true }}',
    )
    raise CapabilityViolation(message, check)


def _is_write_mode(mode: str) -> bool:
    return any(flag in mode for flag in ("w", "a", "x", "+"))


def _path_label(path: Path | str) -> str:
    try:
        return display_path(path)
    except Exception:
        return display_path(str(path))


__all__ = ["check_filesystem"]
