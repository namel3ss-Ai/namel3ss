from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import threading
from typing import Callable

from namel3ss.config.model import AppConfig
from namel3ss.runtime.explainability.logger import append_performance_entry
from namel3ss.runtime.performance.cache import DeterministicLruCache
from namel3ss.runtime.performance.config import PerformanceRuntimeConfig, normalize_performance_runtime_config
from namel3ss.runtime.performance.guard import require_performance_capability
from namel3ss.runtime.performance.scheduler import DeterministicTaskScheduler


@dataclass
class PerformanceRuntimeState:
    config: PerformanceRuntimeConfig
    scheduler: DeterministicTaskScheduler
    ai_cache: DeterministicLruCache

    def refresh(self, runtime_config: PerformanceRuntimeConfig) -> None:
        if runtime_config.max_concurrency != self.config.max_concurrency:
            self.scheduler = DeterministicTaskScheduler(max_concurrency=runtime_config.max_concurrency)
        if runtime_config.cache_size != self.config.cache_size:
            self.ai_cache.set_max_entries(runtime_config.cache_size)
        self.config = runtime_config


_STATE_LOCK = threading.Lock()
_STATE_BY_SCOPE: dict[str, PerformanceRuntimeState] = {}


def build_or_get_performance_state(
    *,
    config: AppConfig | None,
    capabilities: tuple[str, ...] | list[str] | None,
    project_root: str | None,
    app_path: str | None,
) -> PerformanceRuntimeState | None:
    runtime_config = normalize_performance_runtime_config(config)
    require_performance_capability(
        capabilities,
        runtime_config,
        where="namel3ss.toml [performance], environment overrides, or CLI flags",
    )
    if not runtime_config.enabled:
        return None
    scope = _scope_key(project_root=project_root, app_path=app_path)
    with _STATE_LOCK:
        state = _STATE_BY_SCOPE.get(scope)
        if state is None:
            state = PerformanceRuntimeState(
                config=runtime_config,
                scheduler=DeterministicTaskScheduler(max_concurrency=runtime_config.max_concurrency),
                ai_cache=DeterministicLruCache(max_entries=runtime_config.cache_size),
            )
            _STATE_BY_SCOPE[scope] = state
            return state
        state.refresh(runtime_config)
        return state


def run_cached_ai_text_call(
    ctx,
    *,
    provider: str,
    model: str,
    system_prompt: str,
    user_input: str,
    tools: list[str],
    memory: dict,
    compute: Callable[[], str],
) -> tuple[str, bool | None]:
    state = _state_from_ctx(ctx)
    if state is None:
        return compute(), None
    cache_key = _ai_cache_key(
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        user_input=user_input,
        tools=tools,
        memory=memory,
    )
    if state.config.cache_size > 0:
        cached = state.ai_cache.get(cache_key)
        if isinstance(cached, str):
            _record_counter(ctx, "performance_ai_cache_hit", 1)
            append_performance_entry(
                ctx,
                event_type="cache_hit",
                metadata={
                    "cache_key": cache_key,
                    "provider": provider,
                    "model": model,
                },
            )
            return cached, True
    def _invoke() -> str:
        return compute()

    if state.config.async_runtime:
        output, wait_ms = state.scheduler.run_interactive(_invoke)
        _record_counter(ctx, "performance_scheduler_wait_ms", wait_ms)
        append_performance_entry(
            ctx,
            event_type="scheduler_wait",
            metadata={
                "lane": "interactive",
                "provider": provider,
                "model": model,
            },
        )
    else:
        output = _invoke()
    if state.config.cache_size > 0:
        state.ai_cache.set(cache_key, output)
        _record_counter(ctx, "performance_ai_cache_miss", 1)
        append_performance_entry(
            ctx,
            event_type="cache_miss",
            metadata={
                "cache_key": cache_key,
                "provider": provider,
                "model": model,
            },
        )
        return output, False
    return output, None


def _state_from_ctx(ctx) -> PerformanceRuntimeState | None:
    state = getattr(ctx, "performance_state", None)
    if isinstance(state, PerformanceRuntimeState):
        return state
    return None


def _record_counter(ctx, name: str, value: int) -> None:
    observability = getattr(ctx, "observability", None)
    metrics = getattr(observability, "metrics", None) if observability is not None else None
    if metrics is None:
        return
    try:
        metrics.add(name, value=int(value), labels={"flow": getattr(getattr(ctx, "flow", None), "name", "")})
    except Exception:
        return


def _scope_key(*, project_root: str | None, app_path: str | None) -> str:
    raw = f"{project_root or ''}|{app_path or ''}"
    return sha256(raw.encode("utf-8")).hexdigest()[:20]


def _ai_cache_key(
    *,
    provider: str,
    model: str,
    system_prompt: str,
    user_input: str,
    tools: list[str],
    memory: dict,
) -> str:
    payload = {
        "provider": provider,
        "model": model,
        "system_prompt": system_prompt,
        "user_input": user_input,
        "tools": sorted(str(item) for item in tools),
        "memory": memory or {},
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_fallback,
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_fallback(value: object) -> str:
    return str(value)


__all__ = ["PerformanceRuntimeState", "build_or_get_performance_state", "run_cached_ai_text_call"]
