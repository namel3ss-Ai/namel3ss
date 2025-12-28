from __future__ import annotations

from typing import Callable, TypeVar

from namel3ss.runtime.memory_cache.store import MemoryCacheStore


T = TypeVar("T")


def use_cache(
    *,
    cache: MemoryCacheStore | None,
    cache_enabled: bool,
    cache_key: str,
    cache_version: object,
    compute: Callable[[], T],
) -> tuple[T, bool | None]:
    if not cache_enabled or cache is None:
        return compute(), None
    cached = cache.get(cache_key, version=cache_version)
    if cached is not None:
        return cached, True
    value = compute()
    cache.set(cache_key, value, version=cache_version)
    return value, False


__all__ = ["use_cache"]
