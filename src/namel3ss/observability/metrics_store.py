from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from namel3ss.determinism import canonical_json_dump
from namel3ss.runtime.persistence_paths import resolve_persistence_root


METRICS_DIRNAME = "metrics"
METRICS_FILENAME = "metrics.json"


def metrics_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=True)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / METRICS_DIRNAME / METRICS_FILENAME


def _legacy_metrics_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / METRICS_FILENAME


class MetricsStore:
    def __init__(
        self,
        *,
        project_root: str | Path | None,
        app_path: str | Path | None,
        scrubber: Callable[[object], object],
    ) -> None:
        self._project_root = project_root
        self._app_path = app_path
        self._scrub = scrubber
        self._counters: dict[tuple, dict] = {}
        self._timings: dict[tuple, dict] = {}

    def reset(self) -> None:
        self._counters = {}
        self._timings = {}

    def increment(self, name: str, *, labels: dict | None = None, value: int | float = 1) -> None:
        self.add(name, value=value, labels=labels)

    def add(self, name: str, *, value: int | float, labels: dict | None = None) -> None:
        entry = self._counter_entry(name, labels)
        entry["value"] = _coerce_number(entry.get("value", 0)) + _coerce_number(value)

    def set(self, name: str, *, value: int | float, labels: dict | None = None) -> None:
        entry = self._counter_entry(name, labels)
        entry["value"] = _coerce_number(value)

    def record_timing(self, name: str, *, duration: int, labels: dict | None = None) -> None:
        entry = self._timing_entry(name, labels)
        entry["count"] = int(entry.get("count", 0)) + 1
        entry["total_steps"] = int(entry.get("total_steps", 0)) + int(duration)
        entry["last_steps"] = int(duration)
        entry["min_steps"] = _min_or(entry.get("min_steps"), duration)
        entry["max_steps"] = _max_or(entry.get("max_steps"), duration)

    def snapshot(self) -> dict:
        counters = sorted(self._counters.values(), key=_metric_sort_key)
        timings = sorted(self._timings.values(), key=_metric_sort_key)
        return {"counters": counters, "timings": timings}

    def flush(self) -> None:
        path = metrics_path(self._project_root, self._app_path)
        if path is None:
            return
        canonical_json_dump(path, self.snapshot(), pretty=True)

    def _counter_entry(self, name: str, labels: dict | None) -> dict:
        entry = self._entry(name, labels)
        entry.setdefault("value", 0)
        return entry

    def _timing_entry(self, name: str, labels: dict | None) -> dict:
        entry = self._entry(name, labels, timing=True)
        entry.setdefault("count", 0)
        entry.setdefault("total_steps", 0)
        entry.setdefault("min_steps", None)
        entry.setdefault("max_steps", None)
        entry.setdefault("last_steps", 0)
        return entry

    def _entry(self, name: str, labels: dict | None, *, timing: bool = False) -> dict:
        clean = self._scrub({"name": name, "labels": labels or {}})
        if not isinstance(clean, dict):
            clean = {"name": str(name), "labels": labels or {}}
        metric_name = str(clean.get("name", name))
        labels_value = clean.get("labels", {}) if isinstance(clean.get("labels"), dict) else {}
        label_key = _label_key(labels_value)
        entry_key = (metric_name, label_key)
        target = self._timings if timing else self._counters
        if entry_key not in target:
            target[entry_key] = {
                "name": metric_name,
                "labels": labels_value,
            }
            if timing:
                target[entry_key]["unit"] = "steps"
        return target[entry_key]


def read_metrics(project_root: str | Path | None, app_path: str | Path | None) -> dict:
    path = metrics_path(project_root, app_path)
    if path is None:
        return {"counters": [], "timings": []}
    if not path.exists():
        legacy = _legacy_metrics_path(project_root, app_path)
        if legacy is None or not legacy.exists():
            return {"counters": [], "timings": []}
        path = legacy
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"counters": [], "timings": []}
    if not isinstance(raw, dict):
        return {"counters": [], "timings": []}
    counters = raw.get("counters")
    timings = raw.get("timings")
    return {
        "counters": counters if isinstance(counters, list) else [],
        "timings": timings if isinstance(timings, list) else [],
    }


def _label_key(labels: dict) -> tuple:
    return tuple((str(key), str(labels.get(key))) for key in sorted(labels.keys(), key=lambda item: str(item)))


def _metric_sort_key(entry: dict) -> tuple:
    name = str(entry.get("name", ""))
    labels = entry.get("labels", {})
    label_key = _label_key(labels if isinstance(labels, dict) else {})
    return (name, label_key)


def _coerce_number(value: object) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return 0.0


def _min_or(current: object, value: int) -> int:
    if current is None:
        return int(value)
    try:
        return min(int(current), int(value))
    except Exception:
        return int(value)


def _max_or(current: object, value: int) -> int:
    if current is None:
        return int(value)
    try:
        return max(int(current), int(value))
    except Exception:
        return int(value)


__all__ = ["MetricsStore", "read_metrics", "metrics_path"]
