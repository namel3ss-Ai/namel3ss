from __future__ import annotations

from dataclasses import dataclass

from namel3ss.config.security_compliance import load_security_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import normalize_builtin_capability


@dataclass(frozen=True)
class ResourceLimits:
    max_steps: int
    max_memory_bytes: int


def load_resource_limits(
    *,
    project_root: str | None,
    app_path: str | None,
    capabilities: tuple[str, ...] | list[str] | None,
) -> ResourceLimits | None:
    if not _capability_enabled(capabilities, "security_compliance"):
        return None
    config = load_security_config(project_root, app_path, required=False)
    if config is None:
        return None
    return ResourceLimits(
        max_steps=max(1, int(config.max_cpu_ms)),
        max_memory_bytes=max(1, int(config.max_memory_mb) * 1024 * 1024),
    )


def enforce_resource_limits(
    ctx,
    *,
    stage: str,
    line: int | None = None,
    column: int | None = None,
) -> None:
    limits = getattr(ctx, "resource_limits", None)
    if not isinstance(limits, ResourceLimits):
        return
    steps = int(getattr(ctx, "execution_step_counter", 0))
    if steps > limits.max_steps:
        raise Namel3ssError(_cpu_limit_message(stage, steps, limits.max_steps), line=line, column=column)
    state_size = _estimate_size(getattr(ctx, "state", {}), seen=set())
    locals_size = _estimate_size(getattr(ctx, "locals", {}), seen=set())
    memory_bytes = state_size + locals_size
    if memory_bytes > limits.max_memory_bytes:
        raise Namel3ssError(
            _memory_limit_message(stage, memory_bytes, limits.max_memory_bytes),
            line=line,
            column=column,
        )


def _capability_enabled(values: tuple[str, ...] | list[str] | None, capability: str) -> bool:
    if not values:
        return False
    expected = normalize_builtin_capability(capability) or capability
    for value in values:
        token = normalize_builtin_capability(value if isinstance(value, str) else None)
        if token == expected:
            return True
    return False


def _estimate_size(value: object, *, seen: set[int]) -> int:
    marker = id(value)
    if marker in seen:
        return 0
    seen.add(marker)
    if isinstance(value, dict):
        total = 0
        for key in sorted(value.keys(), key=lambda item: str(item)):
            total += len(str(key))
            total += _estimate_size(value[key], seen=seen)
        return total
    if isinstance(value, (list, tuple)):
        return sum(_estimate_size(item, seen=seen) for item in value)
    if isinstance(value, set):
        return sum(_estimate_size(item, seen=seen) for item in sorted(value, key=lambda item: str(item)))
    if isinstance(value, str):
        return len(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return len(str(value))
    return len(str(value))


def _cpu_limit_message(stage: str, steps: int, limit: int) -> str:
    return build_guidance_message(
        what="CPU logical step limit exceeded.",
        why=f"{stage} consumed {steps} logical steps; limit is {limit}.",
        fix="Increase security.resource_limits.max_cpu_ms or simplify the flow.",
        example="security.yaml: resource_limits: { max_cpu_ms: 5000 }",
    )


def _memory_limit_message(stage: str, size_bytes: int, limit_bytes: int) -> str:
    return build_guidance_message(
        what="Memory limit exceeded.",
        why=f"{stage} used {size_bytes} bytes; limit is {limit_bytes} bytes.",
        fix="Reduce payload/state size or increase security.resource_limits.max_memory_mb.",
        example="security.yaml: resource_limits: { max_memory_mb: 256 }",
    )


__all__ = ["ResourceLimits", "enforce_resource_limits", "load_resource_limits"]
