from __future__ import annotations

from dataclasses import dataclass

from namel3ss.config.model import AppConfig, PerformanceConfig


@dataclass(frozen=True)
class PerformanceRuntimeConfig:
    enabled: bool
    async_runtime: bool
    max_concurrency: int
    cache_size: int
    enable_batching: bool
    metrics_endpoint: str


def normalize_performance_runtime_config(config: AppConfig | None) -> PerformanceRuntimeConfig:
    cfg = config or AppConfig()
    perf = cfg.performance if isinstance(getattr(cfg, "performance", None), PerformanceConfig) else PerformanceConfig()
    defaults = PerformanceConfig()
    max_concurrency = _max_one(int(getattr(perf, "max_concurrency", defaults.max_concurrency)))
    cache_size = _max_zero(int(getattr(perf, "cache_size", defaults.cache_size)))
    async_runtime = bool(getattr(perf, "async_runtime", defaults.async_runtime))
    enable_batching = bool(getattr(perf, "enable_batching", defaults.enable_batching))
    metrics_endpoint = str(getattr(perf, "metrics_endpoint", defaults.metrics_endpoint) or defaults.metrics_endpoint)
    enabled = bool(
        async_runtime
        or enable_batching
        or max_concurrency != defaults.max_concurrency
        or cache_size != defaults.cache_size
    )
    return PerformanceRuntimeConfig(
        enabled=enabled,
        async_runtime=async_runtime,
        max_concurrency=max_concurrency,
        cache_size=cache_size,
        enable_batching=enable_batching,
        metrics_endpoint=metrics_endpoint,
    )


def _max_one(value: int) -> int:
    return max(1, int(value))


def _max_zero(value: int) -> int:
    return max(0, int(value))


__all__ = ["PerformanceRuntimeConfig", "normalize_performance_runtime_config"]
