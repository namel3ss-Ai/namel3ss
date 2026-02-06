from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheEntry:
    key: str
    value: object
    created_at: int
    expires_at: int | None = None


class DeterministicLruCache:
    def __init__(self, *, max_entries: int) -> None:
        self._max_entries = max(0, int(max_entries))
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._clock = 0

    def get(self, key: str) -> object | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        # Promote deterministically on hit.
        self._entries.move_to_end(key, last=True)
        return entry.value

    def set(self, key: str, value: object) -> None:
        self._clock += 1
        entry = CacheEntry(key=key, value=value, created_at=self._clock, expires_at=None)
        self._entries[key] = entry
        self._entries.move_to_end(key, last=True)
        self._evict_if_needed()

    def clear(self) -> None:
        self._entries.clear()

    def size(self) -> int:
        return len(self._entries)

    def set_max_entries(self, max_entries: int) -> None:
        self._max_entries = max(0, int(max_entries))
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        if self._max_entries <= 0:
            self._entries.clear()
            return
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)


__all__ = ["CacheEntry", "DeterministicLruCache"]
