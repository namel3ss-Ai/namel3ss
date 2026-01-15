from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequiresGate:
    requires: str
    path: list[str] | None
    ready: bool | None
    issue: str | None = None


def evaluate_requires(requires: str, state: dict | None) -> RequiresGate:
    path = parse_state_requires(requires)
    if path is None:
        return RequiresGate(requires=requires, path=None, ready=None, issue="unsupported")
    if not path:
        return RequiresGate(requires=requires, path=[], ready=None, issue="invalid")
    state_value = state if isinstance(state, dict) else {}
    if not _has_path(state_value, path):
        return RequiresGate(requires=requires, path=path, ready=None, issue="missing")
    try:
        value = _read_path(state_value, path)
    except KeyError:
        return RequiresGate(requires=requires, path=path, ready=None, issue="missing")
    return RequiresGate(requires=requires, path=path, ready=bool(value), issue=None)


def parse_state_requires(requires: str) -> list[str] | None:
    if not requires.startswith("state."):
        return None
    parts = [segment for segment in requires.split(".")[1:] if segment]
    return parts


def _has_path(state: dict, path: list[str]) -> bool:
    cursor: object = state
    for segment in path:
        if not isinstance(cursor, dict) or segment not in cursor:
            return False
        cursor = cursor[segment]
    return True


def _read_path(state: dict, path: list[str]) -> object:
    cursor: object = state
    for segment in path:
        if not isinstance(cursor, dict) or segment not in cursor:
            raise KeyError("missing path")
        cursor = cursor[segment]
    return cursor


__all__ = ["RequiresGate", "evaluate_requires", "parse_state_requires"]
