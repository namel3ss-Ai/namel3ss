from __future__ import annotations

import json
from pathlib import Path
import threading

from namel3ss.triggers import dispatch_trigger_events, enqueue_trigger_event, load_trigger_config


def run_service_trigger_loop(
    *,
    stop_event: threading.Event,
    program_state,
    flow_store,
) -> None:
    seen_timers: set[str] = set()
    seen_uploads: set[str] = set()
    queue_offsets: dict[str, int] = {}
    while not stop_event.wait(0.25):
        try:
            if program_state is None:
                continue
            if program_state.refresh_if_needed():
                seen_timers.clear()
                seen_uploads.clear()
                queue_offsets.clear()
            program = program_state.program
            if program is None:
                continue
            project_root = getattr(program, "project_root", None)
            app_path = getattr(program, "app_path", None)
            trigger_config = load_trigger_config(project_root, app_path)
            for trigger in trigger_config:
                fingerprint = f"{trigger.type}|{trigger.name}|{trigger.pattern}|{trigger.flow}"
                if trigger.type == "timer":
                    if fingerprint in seen_timers:
                        continue
                    enqueue_trigger_event(
                        project_root,
                        app_path,
                        trigger_type=trigger.type,
                        trigger_name=trigger.name,
                        pattern=trigger.pattern,
                        flow_name=trigger.flow,
                        payload={},
                    )
                    seen_timers.add(fingerprint)
                    continue
                if trigger.type == "upload":
                    _enqueue_upload_events(
                        project_root=project_root,
                        app_path=app_path,
                        trigger_name=trigger.name,
                        flow_name=trigger.flow,
                        pattern=trigger.pattern,
                        fingerprint=fingerprint,
                        seen_uploads=seen_uploads,
                    )
                    continue
                if trigger.type == "queue":
                    _enqueue_queue_events(
                        project_root=project_root,
                        app_path=app_path,
                        trigger_name=trigger.name,
                        flow_name=trigger.flow,
                        pattern=trigger.pattern,
                        fingerprint=fingerprint,
                        offsets=queue_offsets,
                    )
            dispatch_trigger_events(
                program=program,
                project_root=project_root,
                app_path=app_path,
                store=flow_store,
                identity={},
                auth_context=None,
            )
        except Exception:
            # Trigger loop should be resilient so transient parser/config errors
            # do not permanently disable dispatcher processing.
            continue


def _enqueue_upload_events(
    *,
    project_root,
    app_path,
    trigger_name: str,
    flow_name: str,
    pattern: str,
    fingerprint: str,
    seen_uploads: set[str],
) -> None:
    root = _resolve_path(project_root, pattern)
    if root is None or not root.exists() or not root.is_dir():
        return
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        stat = path.stat()
        marker = f"{fingerprint}|{path.as_posix()}|{int(stat.st_mtime)}|{int(stat.st_size)}"
        if marker in seen_uploads:
            continue
        enqueue_trigger_event(
            project_root,
            app_path,
            trigger_type="upload",
            trigger_name=trigger_name,
            pattern=pattern,
            flow_name=flow_name,
            payload={
                "name": path.name,
                "path": path.as_posix(),
                "size": int(stat.st_size),
            },
        )
        seen_uploads.add(marker)


def _enqueue_queue_events(
    *,
    project_root,
    app_path,
    trigger_name: str,
    flow_name: str,
    pattern: str,
    fingerprint: str,
    offsets: dict[str, int],
) -> None:
    source = _resolve_path(project_root, pattern)
    if source is None or not source.exists() or not source.is_file():
        return
    lines = [line for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    start = max(0, int(offsets.get(fingerprint, 0)))
    for line in lines[start:]:
        payload = _parse_queue_payload(line)
        enqueue_trigger_event(
            project_root,
            app_path,
            trigger_type="queue",
            trigger_name=trigger_name,
            pattern=pattern,
            flow_name=flow_name,
            payload=payload,
        )
    offsets[fingerprint] = len(lines)


def _parse_queue_payload(line: str) -> dict[str, object]:
    try:
        payload = json.loads(line)
    except Exception:
        payload = {"message": line}
    if not isinstance(payload, dict):
        return {"message": line}
    out: dict[str, object] = {}
    for key in sorted(payload.keys(), key=lambda item: str(item)):
        out[str(key)] = payload[key]
    return out


def _resolve_path(project_root, raw_path: str) -> Path | None:
    text = str(raw_path or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    root = Path(project_root) if project_root is not None else None
    if root is None:
        return None
    return root / path


__all__ = ["run_service_trigger_loop"]
