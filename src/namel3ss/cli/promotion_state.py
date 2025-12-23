from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from namel3ss.cli.targets_store import promotion_state_path, read_json, write_json


def default_state() -> Dict[str, Any]:
    return {
        "active": {"target": None, "build_id": None},
        "previous": {"target": None, "build_id": None},
        "last_promote": {"target": None, "build_id": None},
    }


def load_state(project_root: Path) -> Dict[str, Any]:
    path = promotion_state_path(project_root)
    if not path.exists():
        return default_state()
    data = read_json(path)
    return {
        "active": _coerce_slot(data.get("active")),
        "previous": _coerce_slot(data.get("previous")),
        "last_promote": _coerce_slot(data.get("last_promote")),
    }


def write_state(project_root: Path, state: Dict[str, Any]) -> None:
    path = promotion_state_path(project_root)
    write_json(path, state)


def record_promotion(project_root: Path, target: str, build_id: str) -> Dict[str, Any]:
    state = load_state(project_root)
    current_active = state.get("active") or {"target": None, "build_id": None}
    state["previous"] = {"target": current_active.get("target"), "build_id": current_active.get("build_id")}
    state["active"] = {"target": target, "build_id": build_id}
    state["last_promote"] = {"target": target, "build_id": build_id}
    write_state(project_root, state)
    return state


def record_rollback(project_root: Path) -> Dict[str, Any]:
    state = load_state(project_root)
    prev = state.get("previous") or {"target": None, "build_id": None}
    state["active"] = {"target": prev.get("target"), "build_id": prev.get("build_id")}
    state["previous"] = {"target": None, "build_id": None}
    if prev.get("target"):
        state["last_promote"] = {"target": prev.get("target"), "build_id": prev.get("build_id")}
    write_state(project_root, state)
    return state


def _coerce_slot(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return {"target": raw.get("target"), "build_id": raw.get("build_id")}
    return {"target": None, "build_id": None}


__all__ = [
    "default_state",
    "load_state",
    "record_promotion",
    "record_rollback",
    "write_state",
]
