from __future__ import annotations

import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.observability.trace_runs import read_trace_entries, trace_runs_root
from namel3ss.determinism import canonical_json_dump


DEBUG_STATE_FILENAME = "debug_state.json"


class Debugger:
    def __init__(self, *, project_root: str | Path | None, app_path: str | Path | None) -> None:
        self.project_root = project_root
        self.app_path = app_path
        self._root = trace_runs_root(project_root, app_path, allow_create=True)
        if self._root is None:
            raise Namel3ssError(
                build_guidance_message(
                    what="Debugger root path could not be resolved.",
                    why="The project root is missing.",
                    fix="Run this command from a project with app.ai.",
                    example="n3 debug replay demo-000001",
                )
            )
        self._root.mkdir(parents=True, exist_ok=True)

    def pause(self, run_id: str) -> dict[str, object]:
        entries = self._entries(run_id)
        state = self._load_state()
        sessions = _sessions_map(state)
        session = sessions.get(run_id, {"current_step": 0, "paused": False})
        session["paused"] = True
        sessions[run_id] = session
        self._save_state(state)
        return self._payload(run_id, entries, sessions[run_id])

    def step(self, run_id: str) -> dict[str, object]:
        entries = self._entries(run_id)
        state = self._load_state()
        sessions = _sessions_map(state)
        session = sessions.get(run_id)
        if not isinstance(session, dict) or not bool(session.get("paused")):
            raise Namel3ssError(_not_paused_message(run_id))
        current = _to_int(session.get("current_step"), 0)
        session["current_step"] = min(len(entries), current + 1)
        sessions[run_id] = session
        self._save_state(state)
        return self._payload(run_id, entries, sessions[run_id])

    def back(self, run_id: str) -> dict[str, object]:
        entries = self._entries(run_id)
        state = self._load_state()
        sessions = _sessions_map(state)
        session = sessions.get(run_id)
        if not isinstance(session, dict) or not bool(session.get("paused")):
            raise Namel3ssError(_not_paused_message(run_id))
        current = _to_int(session.get("current_step"), 0)
        session["current_step"] = max(0, current - 1)
        sessions[run_id] = session
        self._save_state(state)
        return self._payload(run_id, entries, sessions[run_id])

    def replay(self, run_id: str) -> dict[str, object]:
        entries = self._entries(run_id)
        session = {"current_step": len(entries), "paused": False}
        return self._payload(run_id, entries, session)

    def show(self, run_id: str) -> dict[str, object]:
        entries = self._entries(run_id)
        state = self._load_state()
        sessions = _sessions_map(state)
        session = sessions.get(run_id, {"current_step": 0, "paused": False})
        return self._payload(run_id, entries, session)

    def _payload(self, run_id: str, entries: list[dict[str, object]], session: dict[str, object]) -> dict[str, object]:
        current_step = _to_int(session.get("current_step"), 0)
        bounded_step = max(0, min(len(entries), current_step))
        paused = bool(session.get("paused"))
        state = _state_at_step(entries, bounded_step)
        current_entry = entries[bounded_step - 1] if bounded_step > 0 and bounded_step <= len(entries) else None
        return {
            "ok": True,
            "run_id": run_id,
            "paused": paused,
            "current_step": bounded_step,
            "total_steps": len(entries),
            "current_entry": current_entry,
            "state": state,
        }

    def _entries(self, run_id: str) -> list[dict[str, object]]:
        entries = read_trace_entries(self.project_root, self.app_path, run_id)
        if entries:
            return entries
        raise Namel3ssError(_missing_trace_run_message(run_id))

    def _state_path(self) -> Path:
        return self._root / DEBUG_STATE_FILENAME

    def _load_state(self) -> dict[str, object]:
        path = self._state_path()
        if not path.exists():
            return {"schema_version": 1, "sessions": {}}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"schema_version": 1, "sessions": {}}
        if not isinstance(payload, dict):
            return {"schema_version": 1, "sessions": {}}
        payload.setdefault("schema_version", 1)
        payload.setdefault("sessions", {})
        return payload

    def _save_state(self, payload: dict[str, object]) -> None:
        path = self._state_path()
        canonical_json_dump(path, payload, pretty=True, drop_run_keys=False)


def _sessions_map(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    raw = payload.get("sessions")
    if not isinstance(raw, dict):
        payload["sessions"] = {}
        raw = payload["sessions"]
    sessions: dict[str, dict[str, object]] = {}
    for key in sorted(raw.keys(), key=lambda item: str(item)):
        value = raw.get(key)
        if isinstance(value, dict):
            sessions[str(key)] = dict(value)
    payload["sessions"] = sessions
    return sessions


def _state_at_step(entries: list[dict[str, object]], step_index: int) -> dict[str, object]:
    locals_map: dict[str, object] = {}
    last_output: object = None
    max_index = max(0, min(step_index, len(entries)))
    for entry in entries[:max_index]:
        output = entry.get("output")
        if isinstance(output, dict):
            for key in sorted(output.keys(), key=lambda item: str(item)):
                locals_map[str(key)] = output[key]
        last_output = output
    return {
        "flow_name": str(entries[0].get("flow_name", "") if entries else ""),
        "locals": locals_map,
        "last_output": last_output,
        "history_steps": max_index,
    }


def _to_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except Exception:
        return default


def _not_paused_message(run_id: str) -> str:
    return build_guidance_message(
        what=f'Run "{run_id}" is not paused.',
        why="Step and back commands only work for paused runs.",
        fix="Pause the run first, then step or back.",
        example=f"n3 debug pause {run_id}",
    )


def _missing_trace_run_message(run_id: str) -> str:
    return build_guidance_message(
        what=f'Trace run "{run_id}" was not found.',
        why="No trace file exists for that run id.",
        fix="Use n3 trace list to find available run ids.",
        example="n3 trace list",
    )


__all__ = ["DEBUG_STATE_FILENAME", "Debugger"]
