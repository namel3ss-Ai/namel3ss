from __future__ import annotations


class MemoryManagerCacheMixin:
    def _cache_version_for(self, store_key: str, kinds: list[str]) -> tuple[int, ...]:
        return tuple(self._cache_versions.get((store_key, kind), 0) for kind in kinds)

    def _bump_cache_version(self, store_key: str, kind: str) -> None:
        key = (store_key, kind)
        self._cache_versions[key] = self._cache_versions.get(key, 0) + 1

    def _update_cache_versions(self, written: list[dict], events: list[dict]) -> None:
        for item in written:
            store_key, kind = _parse_memory_id(item.get("id"))
            if store_key and kind:
                self._bump_cache_version(store_key, kind)
        for event in events:
            if event.get("type") != "memory_deleted":
                continue
            store_key, kind = _parse_memory_id(event.get("memory_id"))
            if store_key and kind:
                self._bump_cache_version(store_key, kind)


def _parse_memory_id(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, None
    parts = value.split(":")
    if len(parts) < 3:
        return None, None
    store_key = ":".join(parts[:-2])
    kind = parts[-2]
    return store_key, kind


__all__ = ["MemoryManagerCacheMixin"]
