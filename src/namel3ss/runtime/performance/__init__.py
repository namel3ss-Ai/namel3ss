from __future__ import annotations

from namel3ss.runtime.performance.batching import batched
from namel3ss.runtime.performance.config import PerformanceRuntimeConfig, normalize_performance_runtime_config
from namel3ss.runtime.performance.guard import (
    LEGACY_PERFORMANCE_CAPABILITY,
    PERFORMANCE_CAPABILITY,
    has_performance_capability,
    require_performance_capability,
)
from namel3ss.runtime.performance.state import build_or_get_performance_state, run_cached_ai_text_call

__all__ = [
    "LEGACY_PERFORMANCE_CAPABILITY",
    "PERFORMANCE_CAPABILITY",
    "PerformanceRuntimeConfig",
    "batched",
    "build_or_get_performance_state",
    "has_performance_capability",
    "normalize_performance_runtime_config",
    "require_performance_capability",
    "run_cached_ai_text_call",
]
