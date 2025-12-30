from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import time
from datetime import datetime, timezone

from namel3ss_safeio import safe_env_get, safe_open


DEFAULT_CACHE_FILE = Path(".namel3ss") / "cache" / "api_cache.json"


@dataclass(frozen=True)
class CacheEntry:
    payload: Any
    updated_ts: float
    updated_at: str


@dataclass(frozen=True)
class CircuitState:
    failures: int
    open_until: float


def cache_path() -> Path:
    override = safe_env_get("N3_API_CACHE_PATH")
    if override:
        return Path(override)
    return DEFAULT_CACHE_FILE


def load_cache() -> dict[str, Any]:
    path = cache_path()
    if not path.exists():
        return {"responses": {}, "circuits": {}}
    try:
        with safe_open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {"responses": {}, "circuits": {}}
    if not isinstance(data, dict):
        return {"responses": {}, "circuits": {}}
    responses = data.get("responses")
    circuits = data.get("circuits")
    if not isinstance(responses, dict):
        responses = {}
    if not isinstance(circuits, dict):
        circuits = {}
    return {"responses": responses, "circuits": circuits}


def save_cache(data: dict[str, Any]) -> None:
    path = cache_path()
    payload = {
        "responses": data.get("responses", {}),
        "circuits": data.get("circuits", {}),
    }
    with safe_open(path, "w", encoding="utf-8", create_dirs=True) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def get_response(key: str) -> CacheEntry | None:
    data = load_cache()
    entry = data["responses"].get(key)
    if not isinstance(entry, dict):
        return None
    updated_ts = entry.get("updated_ts")
    updated_at = entry.get("updated_at")
    if not isinstance(updated_ts, (int, float)) or not isinstance(updated_at, str):
        return None
    return CacheEntry(payload=entry.get("payload"), updated_ts=float(updated_ts), updated_at=updated_at)


def set_response(key: str, payload: Any, *, updated_ts: float) -> CacheEntry:
    data = load_cache()
    updated_at = format_timestamp(updated_ts)
    data["responses"][key] = {
        "payload": payload,
        "updated_ts": float(updated_ts),
        "updated_at": updated_at,
    }
    save_cache(data)
    return CacheEntry(payload=payload, updated_ts=float(updated_ts), updated_at=updated_at)


def is_fresh(entry: CacheEntry, ttl_seconds: int, *, now: float) -> bool:
    return now - entry.updated_ts <= ttl_seconds


def get_circuit(key: str) -> CircuitState:
    data = load_cache()
    entry = data["circuits"].get(key)
    if not isinstance(entry, dict):
        return CircuitState(failures=0, open_until=0.0)
    failures = entry.get("failures")
    open_until = entry.get("open_until")
    if not isinstance(failures, int):
        failures = 0
    if not isinstance(open_until, (int, float)):
        open_until = 0.0
    return CircuitState(failures=failures, open_until=float(open_until))


def is_circuit_open(key: str, *, now: float) -> bool:
    state = get_circuit(key)
    return state.open_until > now


def record_success(key: str) -> None:
    data = load_cache()
    data["circuits"][key] = {"failures": 0, "open_until": 0.0}
    save_cache(data)


def record_failure(key: str, *, now: float, threshold: int, open_seconds: int) -> CircuitState:
    state = get_circuit(key)
    failures = state.failures + 1
    open_until = state.open_until
    if failures >= threshold:
        open_until = max(open_until, now + open_seconds)
    data = load_cache()
    data["circuits"][key] = {"failures": failures, "open_until": open_until}
    save_cache(data)
    return CircuitState(failures=failures, open_until=open_until)


def format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def now_timestamp() -> float:
    return time.time()


__all__ = [
    "CacheEntry",
    "CircuitState",
    "cache_path",
    "get_circuit",
    "get_response",
    "is_circuit_open",
    "is_fresh",
    "now_timestamp",
    "record_failure",
    "record_success",
    "set_response",
]
