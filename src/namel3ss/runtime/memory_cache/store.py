from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    inserted_at: int
    version: object


class MemoryCacheStore:
    def __init__(self, *, max_entries: int) -> None:
        self._max_entries = max(0, int(max_entries))
        self._entries: dict[str, CacheEntry] = {}
        self._counter = 0

    def get(self, key: str, *, version: object) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.version != version:
            return None
        return entry.value

    def set(self, key: str, value: Any, *, version: object) -> None:
        self._counter += 1
        self._entries[key] = CacheEntry(value=value, inserted_at=self._counter, version=version)
        self._evict_if_needed()

    def clear(self) -> None:
        self._entries = {}

    def set_max_entries(self, max_entries: int) -> None:
        self._max_entries = max(0, int(max_entries))
        self._evict_if_needed()

    def size(self) -> int:
        return len(self._entries)

    def _evict_if_needed(self) -> None:
        if self._max_entries <= 0:
            self._entries = {}
            return
        if len(self._entries) <= self._max_entries:
            return
        ordered = sorted(self._entries.items(), key=lambda item: (item[1].inserted_at, item[0]))
        excess = len(self._entries) - self._max_entries
        for idx in range(excess):
            key, _entry = ordered[idx]
            self._entries.pop(key, None)


__all__ = ["CacheEntry", "MemoryCacheStore"]
