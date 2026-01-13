from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Tuple


def _deepcopy(value: object) -> object:
    try:
        return deepcopy(value)
    except Exception:
        return value


def _merge_override(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_override(merged[key], value)  # type: ignore[arg-type]
            continue
        merged[key] = _deepcopy(value)
    return merged


def _merge_missing(target: dict, defaults: dict) -> dict:
    for key, value in defaults.items():
        if isinstance(value, dict):
            current = target.get(key)
            if isinstance(current, dict):
                _merge_missing(current, value)
                continue
            if key not in target:
                target[key] = _merge_missing({}, value)
            continue
        if key not in target:
            target[key] = _deepcopy(value)
    return target


def _has_path(data: dict, path: List[str]) -> bool:
    cursor: object = data
    for segment in path:
        if not isinstance(cursor, dict) or segment not in cursor:
            return False
        cursor = cursor[segment]
    return True


def _read_path(data: dict, path: List[str]) -> object:
    cursor: object = data
    for segment in path:
        if not isinstance(cursor, dict) or segment not in cursor:
            raise KeyError("missing path")
        cursor = cursor[segment]
    return cursor


def _set_path(target: dict, path: List[str], value: object, *, overwrite: bool) -> None:
    cursor = target
    for segment in path[:-1]:
        next_cursor = cursor.get(segment)
        if not isinstance(next_cursor, dict):
            next_cursor = {}
            cursor[segment] = next_cursor
        cursor = next_cursor
    leaf = path[-1]
    if overwrite or leaf not in cursor:
        cursor[leaf] = _deepcopy(value)


def _collect_paths(data: dict, prefix: Tuple[str, ...] | None = None, paths: set[Tuple[str, ...]] | None = None) -> set[Tuple[str, ...]]:
    prefix = prefix or tuple()
    collected = paths or set()
    for key, value in data.items():
        next_prefix = (*prefix, str(key))
        collected.add(next_prefix)
        if isinstance(value, dict):
            _collect_paths(value, next_prefix, collected)
    return collected


class StateDefaults:
    def __init__(self, app_defaults: dict | None = None, page_defaults: dict | None = None) -> None:
        base = deepcopy(app_defaults) if isinstance(app_defaults, dict) else {}
        override = deepcopy(page_defaults) if isinstance(page_defaults, dict) else {}
        self.defaults: Dict[str, object] = _merge_override(base, override) if override else base
        self.declared_paths: set[Tuple[str, ...]] = _collect_paths(self.defaults)
        self._warned_paths: set[Tuple[str, ...]] = set()

    def declared(self, path: Iterable[str]) -> bool:
        return tuple(path) in self.declared_paths

    def warn_once(self, path: Iterable[str]) -> bool:
        key = tuple(path)
        if key in self._warned_paths:
            return False
        self._warned_paths.add(key)
        return True

    def register_default(self, path: List[str], value: object) -> None:
        _set_path(self.defaults, path, value, overwrite=False)
        self.declared_paths.add(tuple(path))

    def snapshot(self) -> dict:
        return deepcopy(self.defaults)


class StateContext:
    def __init__(self, state: dict | None, defaults: StateDefaults) -> None:
        self.defaults = defaults
        self.state = _merge_missing(deepcopy(state) if isinstance(state, dict) else {}, self.defaults.defaults)

    def has_value(self, path: List[str]) -> bool:
        return _has_path(self.state, path)

    def value(self, path: List[str], *, default: object | None = None, register_default: bool = False) -> tuple[object, bool]:
        if _has_path(self.state, path):
            return _read_path(self.state, path), False
        if default is not None:
            if register_default:
                self.defaults.register_default(path, default)
            _set_path(self.state, path, default, overwrite=False)
            return _read_path(self.state, path), True
        raise KeyError("missing path")

    def ensure_path(self, path: List[str], value: object, *, register_default: bool) -> None:
        self.value(path, default=value, register_default=register_default)

    def declared(self, path: Iterable[str]) -> bool:
        return self.defaults.declared(path)

    def defaults_snapshot(self) -> dict:
        return self.defaults.snapshot()

    def state_snapshot(self) -> dict:
        return deepcopy(self.state)


__all__ = ["StateDefaults", "StateContext", "_merge_missing", "_set_path"]
