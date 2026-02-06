from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.runtime.performance.batching import batched
from namel3ss.runtime.performance.cache import DeterministicLruCache
from namel3ss.runtime.performance.config import PerformanceRuntimeConfig
from namel3ss.runtime.performance.scheduler import DeterministicTaskScheduler
from namel3ss.runtime.performance.state import PerformanceRuntimeState, run_cached_ai_text_call


def test_deterministic_lru_cache_eviction() -> None:
    cache = DeterministicLruCache(max_entries=2)
    cache.set("one", "1")
    cache.set("two", "2")
    cache.set("three", "3")
    assert cache.get("one") is None
    assert cache.get("two") == "2"
    assert cache.get("three") == "3"


def test_batched_preserves_order() -> None:
    values = [1, 2, 3, 4, 5]
    groups = list(batched(values, 2))
    assert groups == [[1, 2], [3, 4], [5]]


def test_scheduler_reports_wait_metrics() -> None:
    scheduler = DeterministicTaskScheduler(max_concurrency=4)
    result, wait_ms = scheduler.run_interactive(lambda: "ok")
    assert result == "ok"
    assert wait_ms >= 0
    stats = scheduler.stats()
    assert stats.interactive_slots >= 1
    assert stats.heavy_slots >= 1


def test_run_cached_ai_text_call_uses_cache() -> None:
    runtime = PerformanceRuntimeState(
        config=PerformanceRuntimeConfig(
            enabled=True,
            async_runtime=True,
            max_concurrency=4,
            cache_size=2,
            enable_batching=False,
            metrics_endpoint="/api/metrics",
        ),
        scheduler=DeterministicTaskScheduler(max_concurrency=4),
        ai_cache=DeterministicLruCache(max_entries=2),
    )
    ctx = _Ctx(performance_state=runtime)
    calls = {"count": 0}

    def _compute() -> str:
        calls["count"] += 1
        return "alpha"

    first, first_hit = run_cached_ai_text_call(
        ctx,
        provider="mock",
        model="mock-model",
        system_prompt="be brief",
        user_input="hello",
        tools=[],
        memory={},
        compute=_compute,
    )
    second, second_hit = run_cached_ai_text_call(
        ctx,
        provider="mock",
        model="mock-model",
        system_prompt="be brief",
        user_input="hello",
        tools=[],
        memory={},
        compute=_compute,
    )
    assert first == "alpha"
    assert second == "alpha"
    assert first_hit is False
    assert second_hit is True
    assert calls["count"] == 1


@dataclass
class _Flow:
    name: str = "demo"


@dataclass
class _Ctx:
    performance_state: object
    flow: _Flow = field(default_factory=_Flow)
    observability: object | None = None
