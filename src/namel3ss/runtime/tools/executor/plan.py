from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.packs.permission_enforcer import evaluate_pack_permission
from namel3ss.runtime.packs.policy import policy_denied_message
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.packs.studio_pack_adapter import record_pack_allowlist, record_pack_policy
from namel3ss.runtime.tools.executor.result import _ensure_tool_trace
from namel3ss.runtime.tools.outcome import ToolDecision
from namel3ss.runtime.tools.policy import normalize_capabilities
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from namel3ss.runtime.tools.runners.registry import get_runner


@dataclass(frozen=True)
class _BindingCheck:
    ok: bool
    error: Namel3ssError | None
    reason: str | None
    status: str | None


def _resolve_required_capabilities(
    tool_kind: str | None,
    declared: tuple[str, ...] | list[str] | None,
    args: dict,
) -> tuple[str, ...]:
    required = set(normalize_capabilities(declared))
    if tool_kind == "http":
        required.add("network")
    elif tool_kind == "file":
        operation = None
        if isinstance(args, dict):
            operation = args.get("operation")
        if operation == "read":
            required.add("filesystem_read")
        elif operation == "write":
            required.add("filesystem_write")
        else:
            required.update({"filesystem_read", "filesystem_write"})
    return tuple(sorted(required))


def _capability_gate(
    ctx: ExecutionContext,
    tool_name: str,
    tool_kind: str | None,
    *,
    line: int | None,
    column: int | None,
) -> ToolDecision | None:
    capability = _builtin_capability_for_kind(tool_kind)
    if capability is None:
        return None
    allowed = set(getattr(ctx, "capabilities", ()) or ())
    if capability in allowed:
        return None
    message = build_guidance_message(
        what=f'Capability "{capability}" is required for tool "{tool_name}".',
        why="Built-in backend capabilities are deny-by-default.",
        fix="Add the capability to the app capabilities block.",
        example=f"capabilities:\n  {capability}",
    )
    return ToolDecision(
        status="blocked",
        capability=capability,
        reason="capability_missing",
        message=message,
    )


def _builtin_capability_for_kind(tool_kind: str | None) -> str | None:
    if tool_kind == "http":
        return "http"
    if tool_kind == "file":
        return "files"
    return None


def _check_binding(
    ctx: ExecutionContext,
    tool_name: str,
    tool_kind: str | None,
    *,
    line: int | None,
    column: int | None,
) -> _BindingCheck:
    if tool_kind is None:
        return _BindingCheck(ok=False, error=None, reason="unknown_tool", status="error")
    if tool_kind not in {"python", "node"}:
        return _BindingCheck(ok=True, error=None, reason=None, status=None)
    if not ctx.project_root:
        return _BindingCheck(ok=True, error=None, reason=None, status=None)
    pack_allowlist = getattr(ctx, "pack_allowlist", None)
    allowed_packs = pack_allowlist if pack_allowlist is not None else ()
    try:
        resolved = resolve_tool_binding(
            Path(ctx.project_root),
            tool_name,
            ctx.config,
            tool_kind=tool_kind,
            line=line,
            column=column,
            allowed_packs=allowed_packs,
        )
    except Namel3ssError as err:
        reason = _binding_reason(err)
        status = "blocked" if reason in {"pack_unavailable_or_unverified", "pack_not_declared"} else "error"
        if reason == "pack_not_declared":
            runner_name = "node" if tool_kind == "node" else "local"
            record_pack_allowlist(
                ctx,
                tool_name=tool_name,
                resolved_source="pack",
                runner=runner_name,
                allowed=False,
            )
        return _BindingCheck(ok=False, error=err, reason=reason, status=status)
    runner_name = resolved.binding.runner or ("node" if tool_kind == "node" else "local")
    try:
        get_runner(runner_name)
    except Namel3ssError as err:
        return _BindingCheck(ok=False, error=err, reason="unknown_runner", status="error")
    if resolved.source in {"builtin_pack", "installed_pack", "local_pack"} and resolved.pack_id:
        if not (resolved.source == "builtin_pack" and pack_allowlist is None):
            record_pack_allowlist(
                ctx,
                tool_name=tool_name,
                resolved_source=resolved.source,
                runner=runner_name,
                allowed=True,
            )
            registry = load_pack_registry(Path(ctx.project_root), ctx.config)
            pack = registry.packs.get(resolved.pack_id)
            if pack:
                decision = evaluate_pack_permission(pack, app_root=Path(ctx.project_root))
                record_pack_policy(
                    ctx,
                    tool_name=tool_name,
                    resolved_source=resolved.source,
                    runner=runner_name,
                    allowed=decision.allowed,
                    policy_source=decision.policy_source,
                )
                if not decision.allowed:
                    err = Namel3ssError(
                        policy_denied_message(pack.pack_id, "enable", decision.reasons),
                        line=line,
                        column=column,
                        details={"tool_reason": "pack_permission_denied"},
                    )
                    _ensure_tool_trace(
                        ctx,
                        tool_name,
                        tool_kind,
                        status="blocked",
                        reason="pack_permission_denied",
                    )
                    return _BindingCheck(
                        ok=False,
                        error=err,
                        reason="pack_permission_denied",
                        status="blocked",
                    )
    return _BindingCheck(ok=True, error=None, reason=None, status=None)


def _binding_reason(err: Namel3ssError) -> str:
    details = err.details if isinstance(err.details, dict) else {}
    reason = details.get("tool_reason")
    if isinstance(reason, str) and reason:
        return reason
    return "binding_error"


__all__ = [
    "_BindingCheck",
    "_builtin_capability_for_kind",
    "_capability_gate",
    "_check_binding",
    "_resolve_required_capabilities",
]
