from __future__ import annotations

from ..model import DecisionStep


_UPLOAD_TRACE_TYPES = {
    "upload_state",
    "upload_progress",
    "upload_preview",
    "upload_error",
    "upload_received",
    "upload_stored",
}


def upload_decisions(state: dict, upload_id: str | None) -> list[DecisionStep]:
    uploads = state.get("uploads")
    if not isinstance(uploads, dict):
        return []
    steps: list[DecisionStep] = []
    for upload_name in sorted(uploads.keys(), key=lambda item: str(item)):
        entries = uploads.get(upload_name)
        if isinstance(entries, dict):
            if _looks_like_upload_entry(entries):
                entries = [entries]
            else:
                entries = [value for value in entries.values() if isinstance(value, dict)]
        if not isinstance(entries, list):
            continue
        for entry in sorted(entries, key=_upload_sort_key):
            if not isinstance(entry, dict):
                continue
            checksum = _upload_checksum(entry)
            if upload_id and checksum and checksum != upload_id:
                continue
            step_id = f"upload:{upload_name}:{checksum or 'unknown'}"
            inputs = {
                "upload_name": upload_name,
                "name": entry.get("name"),
                "size": entry.get("size"),
                "type": entry.get("type"),
                "checksum": checksum,
            }
            preview = entry.get("preview")
            if isinstance(preview, dict):
                inputs["preview"] = preview
            progress = entry.get("progress")
            if isinstance(progress, dict):
                inputs["progress"] = progress
            state_value = entry.get("state")
            if isinstance(state_value, str):
                inputs["state"] = state_value
            error = entry.get("error")
            if isinstance(error, dict):
                inputs["error"] = error
            steps.append(
                DecisionStep(
                    id=step_id,
                    category="upload",
                    subject=checksum,
                    inputs=inputs,
                    rules=["metadata recorded"],
                    outcome={"selected": True},
                )
            )
    return steps


def upload_trace_decisions(traces: list[dict], upload_id: str | None) -> list[DecisionStep]:
    steps: list[DecisionStep] = []
    for idx, trace in enumerate(traces, start=1):
        event_type = trace.get("type")
        if event_type not in _UPLOAD_TRACE_TYPES:
            continue
        subject = _trace_upload_id(trace)
        if upload_id:
            if subject is None or subject != upload_id:
                continue
        step_id = f"upload:event:{idx}:{event_type}"
        inputs = _upload_trace_inputs(trace)
        outcome = _upload_trace_outcome(trace)
        steps.append(
            DecisionStep(
                id=step_id,
                category="upload",
                subject=subject,
                inputs=inputs,
                rules=[event_type],
                outcome=outcome,
            )
        )
    return steps


def _trace_upload_id(trace: dict) -> str | None:
    for key in ("upload_id", "checksum"):
        value = trace.get(key)
        if isinstance(value, str) and value:
            return value
    preview = trace.get("preview")
    if isinstance(preview, dict):
        value = preview.get("checksum")
        if isinstance(value, str) and value:
            return value
    return None


def _upload_trace_inputs(trace: dict) -> dict:
    inputs: dict[str, object] = {}
    for key in (
        "name",
        "content_type",
        "bytes",
        "checksum",
        "stored_path",
        "state",
        "bytes_received",
        "total_bytes",
        "percent_complete",
    ):
        if key in trace:
            inputs[key] = trace.get(key)
    preview = trace.get("preview")
    if isinstance(preview, dict):
        inputs["preview"] = preview
    error = trace.get("error")
    if isinstance(error, dict):
        inputs["error"] = error
    return inputs


def _upload_trace_outcome(trace: dict) -> dict:
    event_type = trace.get("type")
    if event_type == "upload_state":
        state = trace.get("state")
        return {"state": state} if state else {}
    if event_type == "upload_progress":
        progress = trace.get("percent_complete")
        return {"progress": progress} if progress is not None else {}
    if event_type == "upload_preview":
        return {"preview": True}
    if event_type == "upload_error":
        error = trace.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        return {"error": code} if isinstance(code, str) and code else {}
    if event_type == "upload_received":
        return {"received": True}
    if event_type == "upload_stored":
        return {"stored": True}
    return {}


def _upload_sort_key(entry: object) -> tuple[str, str]:
    if not isinstance(entry, dict):
        return ("", "")
    name = str(entry.get("name") or "")
    checksum = _upload_checksum(entry)
    return (name, checksum or "")


def _upload_checksum(entry: dict) -> str | None:
    value = entry.get("checksum") or entry.get("id")
    if isinstance(value, str) and value:
        return value
    return None


def _looks_like_upload_entry(entry: dict) -> bool:
    identifier = entry.get("id") if isinstance(entry.get("id"), str) and entry.get("id") else entry.get("checksum")
    name = entry.get("name")
    return isinstance(identifier, str) and bool(identifier) and isinstance(name, str) and bool(name)


__all__ = ["upload_decisions", "upload_trace_decisions"]
