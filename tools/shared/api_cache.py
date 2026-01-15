from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import time


@dataclass(frozen=True)
class CacheEntry:
    payload: dict[str, Any]
    updated_ts: float
    updated_at: str


@dataclass
class CircuitState:
    failures: int = 0
    open_until: float = 0.0


_cache: dict[str, CacheEntry] = {}
_circuits: dict[str, CircuitState] = {}


def now_timestamp() -> float:
    return time.time()


def set_response(key: str, payload: dict[str, Any], updated_ts: float) -> CacheEntry:
    entry = CacheEntry(payload=payload, updated_ts=updated_ts, updated_at=_format_timestamp(updated_ts))
    _cache[key] = entry
    return entry


def get_response(key: str) -> CacheEntry | None:
    return _cache.get(key)


def is_fresh(entry: CacheEntry, ttl_seconds: float, now: float) -> bool:
    return (now - entry.updated_ts) <= ttl_seconds


def record_failure(key: str, now: float, threshold: int, open_seconds: float) -> None:
    state = _circuits.setdefault(key, CircuitState())
    state.failures += 1
    if state.failures >= threshold:
        state.open_until = now + open_seconds


def record_success(key: str) -> None:
    state = _circuits.setdefault(key, CircuitState())
    state.failures = 0
    state.open_until = 0.0


def is_circuit_open(key: str, now: float) -> bool:
    state = _circuits.get(key)
    if not state:
        return False
    return now < state.open_until


def _format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
