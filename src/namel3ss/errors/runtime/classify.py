from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


def classify_error(boundary: str, err: Exception) -> tuple[str, str]:
    boundary = boundary or "engine"
    message = _error_message(err).lower()
    action = getattr(err, "__namel3ss_boundary_action__", None)

    if boundary == "tools":
        if _mentions_blocking(message):
            return "tool_blocked", "runtime.tools.blocked"
        return "tool_failed", "runtime.tools.failed"
    if boundary == "ai":
        if "provider" in message:
            return "ai_provider_error", "runtime.ai.provider_error"
        return "ai_failed", "runtime.ai.failed"
    if boundary == "store":
        if action == "commit":
            return "store_commit_failed", "runtime.store.commit_failed"
        if action == "rollback":
            return "store_rollback_failed", "runtime.store.rollback_failed"
        return "store_failed", "runtime.store.failed"
    if boundary == "memory":
        if action == "persist":
            return "memory_persist_failed", "runtime.memory.persist_failed"
        return "memory_failed", "runtime.memory.failed"
    if boundary == "theme":
        return "theme_resolution_failed", "runtime.theme.failed"
    if boundary == "fs":
        return "filesystem_failed", "runtime.fs.failed"
    return "engine_error", "runtime.engine.error"


def _error_message(err: Exception) -> str:
    if isinstance(err, Namel3ssError):
        return err.message
    return str(err)


def _mentions_blocking(message: str) -> bool:
    return any(token in message for token in ("blocked", "permission", "capability"))


__all__ = ["classify_error"]
