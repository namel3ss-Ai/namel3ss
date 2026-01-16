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
    root = _normalize_root(getattr(ctx, "filesystem_root", None))
    read_roots = _normalize_roots(getattr(ctx, "filesystem_read_roots", None))
    if _blocked_by_root(path, root, read_roots, mode):
        check = CapabilityCheck(
            capability=operation,
            allowed=False,
            guarantee_source="engine",
            reason=REASON_GUARANTEE_BLOCKED,
        )
        record(check)
        raise CapabilityViolation(
            _root_block_message(ctx.tool_name, path, root, read_roots, mode),
            check,
        )
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


def _blocked_by_root(
    path: Path | str,
    root: Path | None,
    read_roots: list[Path],
    mode: str,
) -> bool:
    if root is None and not read_roots:
        return False
    target = _resolve_target(path, root)
    if _is_write_mode(mode):
        if root is None:
            return False
        return not _is_within(root, target)
    allowed = list(read_roots)
    if root is not None:
        allowed.append(root)
    return not any(_is_within(allowed_root, target) for allowed_root in allowed)


def _resolve_target(path: Path | str, root: Path | None) -> Path:
    target = Path(path)
    if root is not None and not target.is_absolute():
        target = root / target
    try:
        return target.resolve()
    except Exception:
        return target


def _normalize_root(value: str | None) -> Path | None:
    if not value:
        return None
    try:
        return Path(value).expanduser().resolve()
    except Exception:
        return Path(value)


def _normalize_roots(values: list[str] | None) -> list[Path]:
    roots: list[Path] = []
    for value in values or []:
        if not value:
            continue
        roots.append(_normalize_root(str(value)))
    return [root for root in roots if root is not None]


def _is_within(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except Exception:
        return False


def _root_block_message(
    tool_name: str,
    path: Path | str,
    root: Path | None,
    read_roots: list[Path],
    mode: str,
) -> str:
    target = _path_label(path)
    roots = read_roots[:]
    if root is not None:
        roots.append(root)
    labels = sorted({_path_label(item) for item in roots})
    allowed = ", ".join(labels) if labels else "the allowed workspace"
    example_root = labels[0] if labels else "workspace"
    action = "cannot write outside its workspace" if _is_write_mode(mode) else "cannot read outside its workspace"
    return build_block_message(
        tool_name=tool_name,
        action=action,
        why=f"Filesystem access to {target} is outside {allowed}.",
        example=f"{example_root}/file.txt",
    )


__all__ = ["check_filesystem"]
