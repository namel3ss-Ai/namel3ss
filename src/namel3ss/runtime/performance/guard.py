from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.performance.config import PerformanceRuntimeConfig


PERFORMANCE_CAPABILITY = "performance"
LEGACY_PERFORMANCE_CAPABILITY = "performance_scalability"


def has_performance_capability(capabilities: tuple[str, ...] | list[str] | None) -> bool:
    if not capabilities:
        return False
    declared = {str(item).strip().lower() for item in capabilities}
    if PERFORMANCE_CAPABILITY in declared:
        return True
    return LEGACY_PERFORMANCE_CAPABILITY in declared


def require_performance_capability(
    capabilities: tuple[str, ...] | list[str] | None,
    runtime_config: PerformanceRuntimeConfig,
    *,
    where: str,
) -> None:
    if not runtime_config.enabled:
        return
    if has_performance_capability(capabilities):
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Performance runtime settings are enabled without the required capability.",
            why="Projects must explicitly opt in to async runtime and scalability features.",
            fix=f"Add `{PERFORMANCE_CAPABILITY}` to the capabilities block or disable performance settings in {where}.",
            example='capabilities:\n  performance',
        )
    )


__all__ = [
    "LEGACY_PERFORMANCE_CAPABILITY",
    "PERFORMANCE_CAPABILITY",
    "has_performance_capability",
    "require_performance_capability",
]
