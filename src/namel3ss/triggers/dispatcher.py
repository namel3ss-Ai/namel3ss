from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.persistence_paths import resolve_persistence_root


TRIGGER_QUEUE_FILENAME = "trigger_queue.jsonl"


@dataclass(frozen=True)
class TriggerEvent:
    trigger_type: str
    trigger_name: str
    pattern: str
    flow_name: str
    payload: dict[str, object]
    step_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "trigger_type": self.trigger_type,
            "trigger_name": self.trigger_name,
            "pattern": self.pattern,
            "flow_name": self.flow_name,
            "payload": self.payload,
            "step_count": int(self.step_count),
        }


def queue_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / TRIGGER_QUEUE_FILENAME


def load_trigger_events(project_root: str | Path | None, app_path: str | Path | None) -> list[TriggerEvent]:
    path = queue_path(project_root, app_path, allow_create=False)
    if path is None or not path.exists():
        return []
    events: list[TriggerEvent] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as err:
            raise Namel3ssError(_invalid_queue_message(path, err.msg)) from err
        event = _event_from_payload(payload, path=path)
        if event is not None:
            events.append(event)
    return _sorted_events(events)


def enqueue_trigger_event(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    trigger_type: str,
    trigger_name: str,
    pattern: str,
    flow_name: str,
    payload: dict[str, object] | None = None,
    step_count: int | None = None,
) -> TriggerEvent:
    path = queue_path(project_root, app_path, allow_create=True)
    if path is None:
        raise Namel3ssError(_missing_queue_path_message())
    existing = load_trigger_events(project_root, app_path)
    resolved_step = _resolve_step_count(existing, step_count)
    event = TriggerEvent(
        trigger_type=str(trigger_type or "").strip().lower(),
        trigger_name=_require_text(trigger_name, "trigger_name"),
        pattern=_require_text(pattern, "pattern"),
        flow_name=_require_text(flow_name, "flow_name"),
        payload=_normalize_payload(payload),
        step_count=resolved_step,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(event.to_dict(), pretty=False, drop_run_keys=False) + "\n")
    return event


def drain_trigger_events(project_root: str | Path | None, app_path: str | Path | None) -> list[TriggerEvent]:
    events = load_trigger_events(project_root, app_path)
    path = queue_path(project_root, app_path, allow_create=True)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return events


def dispatch_trigger_events(
    *,
    program,
    project_root: str | Path | None,
    app_path: str | Path | None,
    store=None,
    identity: dict | None = None,
    auth_context: object | None = None,
) -> dict[str, object]:
    events = drain_trigger_events(project_root, app_path)
    results: list[dict[str, object]] = []
    ok = True
    for event in events:
        try:
            run = execute_program_flow(
                program,
                event.flow_name,
                input=dict(event.payload),
                store=store,
                identity=identity,
                auth_context=auth_context,
                route_name=f"trigger:{event.trigger_name}",
            )
            results.append(
                {
                    "trigger_name": event.trigger_name,
                    "flow_name": event.flow_name,
                    "step_count": event.step_count,
                    "ok": True,
                    "result": run.last_value,
                }
            )
        except Exception as err:  # pragma: no cover - defensive
            ok = False
            results.append(
                {
                    "trigger_name": event.trigger_name,
                    "flow_name": event.flow_name,
                    "step_count": event.step_count,
                    "ok": False,
                    "error": str(err),
                }
            )
    return {
        "ok": ok,
        "count": len(events),
        "results": results,
    }


def _event_from_payload(payload: object, *, path: Path) -> TriggerEvent | None:
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_queue_message(path, "entry is not an object"))
    trigger_type = _require_text(payload.get("trigger_type"), "trigger_type")
    trigger_name = _require_text(payload.get("trigger_name"), "trigger_name")
    pattern = _require_text(payload.get("pattern"), "pattern")
    flow_name = _require_text(payload.get("flow_name"), "flow_name")
    step_count = _parse_step_count(payload.get("step_count"))
    if step_count is None:
        raise Namel3ssError(_invalid_queue_message(path, "step_count is invalid"))
    raw_payload = payload.get("payload")
    normalized_payload = _normalize_payload(raw_payload if isinstance(raw_payload, dict) else {})
    return TriggerEvent(
        trigger_type=trigger_type,
        trigger_name=trigger_name,
        pattern=pattern,
        flow_name=flow_name,
        payload=normalized_payload,
        step_count=step_count,
    )


def _sorted_events(events: list[TriggerEvent]) -> list[TriggerEvent]:
    return sorted(
        events,
        key=lambda item: (
            item.step_count,
            item.trigger_name,
            item.trigger_type,
            item.pattern,
            canonical_json_dumps(item.payload, pretty=False, drop_run_keys=False),
        ),
    )


def _resolve_step_count(existing: list[TriggerEvent], value: int | None) -> int:
    if value is not None:
        parsed = _parse_step_count(value)
        if parsed is None:
            raise Namel3ssError(_invalid_step_message())
        return parsed
    if not existing:
        return 1
    return max(item.step_count for item in existing) + 1


def _parse_step_count(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    if parsed < 0:
        return None
    return parsed


def _normalize_payload(payload: dict[str, object] | None) -> dict[str, object]:
    if not payload:
        return {}
    normalized: dict[str, object] = {}
    for key in sorted(payload.keys(), key=lambda item: str(item)):
        normalized[str(key)] = payload[key]
    return normalized


def _require_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(_missing_field_message(label))


def _missing_field_message(label: str) -> str:
    return build_guidance_message(
        what=f"{label} is required.",
        why=f"Trigger event entries need '{label}'.",
        fix=f"Provide '{label}' and retry.",
        example='{"trigger_name":"nightly_cleanup","flow_name":"cleanup"}',
    )


def _invalid_queue_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Trigger queue file is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Clean invalid rows in the queue file.",
        example='{"trigger_type":"timer","trigger_name":"nightly","pattern":"0 0 * * *","flow_name":"cleanup","step_count":1}',
    )


def _missing_queue_path_message() -> str:
    return build_guidance_message(
        what="Trigger queue path could not be resolved.",
        why="The project root is missing.",
        fix="Run this command in a project with app.ai.",
        example="n3 trigger list",
    )


def _invalid_step_message() -> str:
    return build_guidance_message(
        what="step_count is invalid.",
        why="step_count must be a non-negative integer.",
        fix="Use a valid integer value.",
        example='{"step_count": 3}',
    )


__all__ = [
    "TRIGGER_QUEUE_FILENAME",
    "TriggerEvent",
    "dispatch_trigger_events",
    "drain_trigger_events",
    "enqueue_trigger_event",
    "load_trigger_events",
    "queue_path",
]
