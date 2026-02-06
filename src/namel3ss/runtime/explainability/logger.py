from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
from typing import Any

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps

_LOGICAL_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_REDACTED = "(redacted)"
_REDACTABLE_KEYS = {
    "audio",
    "content",
    "description",
    "input",
    "output",
    "text",
    "token",
    "transcript",
    "user_input",
}


def explain_enabled(config: object | None) -> bool:
    determinism = getattr(config, "determinism", None)
    if determinism is None:
        return True
    return bool(getattr(determinism, "explain", True))


def redact_user_data_enabled(config: object | None) -> bool:
    determinism = getattr(config, "determinism", None)
    if determinism is None:
        return False
    return bool(getattr(determinism, "redact_user_data", False))


def append_explain_entry(
    ctx,
    *,
    stage: str,
    event_type: str,
    inputs: object | None = None,
    outputs: object | None = None,
    seed: int | str | None = None,
    provider: str | None = None,
    model: str | None = None,
    parameters: object | None = None,
    metadata: object | None = None,
) -> dict[str, object] | None:
    if not explain_enabled(getattr(ctx, "config", None)):
        return None
    sequence = int(getattr(ctx, "explain_sequence", 0)) + 1
    setattr(ctx, "explain_sequence", sequence)
    redaction = redact_user_data_enabled(getattr(ctx, "config", None))
    entry = {
        "event_index": sequence,
        "timestamp": logical_timestamp(sequence),
        "stage": str(stage or "unknown"),
        "event_type": str(event_type or "event"),
        "inputs": _redact(inputs, enabled=redaction),
        "seed": seed,
        "provider": str(provider or ""),
        "model": str(model or ""),
        "parameters": _redact(parameters, enabled=redaction),
        "outputs": _redact(outputs, enabled=redaction),
        "metadata": _redact(metadata, enabled=redaction),
    }
    explain_log = getattr(ctx, "explain_log", None)
    if not isinstance(explain_log, list):
        explain_log = []
        setattr(ctx, "explain_log", explain_log)
    explain_log.append(entry)
    return entry


def append_streaming_entry(
    ctx,
    *,
    stream_id: str,
    event_type: str,
    event_index: int,
    logical_time: str,
    output: object,
    data: dict[str, object] | None,
) -> dict[str, object] | None:
    metadata = {
        "stream_id": stream_id,
        "logical_timestamp": logical_time,
        "stream_channel": "ai",
    }
    if isinstance(data, dict):
        metadata["data"] = dict(data)
    return append_explain_entry(
        ctx,
        stage="streaming",
        event_type=event_type,
        inputs=None,
        outputs={"chunk": output},
        metadata={"streaming": metadata, "event_index": int(event_index)},
    )


def append_performance_entry(
    ctx,
    *,
    event_type: str,
    metadata: dict[str, object],
) -> dict[str, object] | None:
    return append_explain_entry(
        ctx,
        stage="performance",
        event_type=event_type,
        metadata=dict(metadata),
    )


def append_job_entry(
    ctx,
    *,
    event_type: str,
    job_name: str,
    metadata: dict[str, object] | None = None,
) -> dict[str, object] | None:
    details = {"job_name": str(job_name or "")}
    if isinstance(metadata, dict):
        details.update(metadata)
    return append_explain_entry(
        ctx,
        stage="job_queue",
        event_type=event_type,
        metadata=details,
    )


def build_explain_log_payload(*, flow_name: str, entries: list[dict[str, object]]) -> dict[str, object]:
    replay_hash = explain_replay_hash(entries)
    return {
        "schema_version": 1,
        "flow_name": flow_name,
        "entry_count": len(entries),
        "generated_at": logical_timestamp(len(entries)),
        "replay_hash": replay_hash,
        "entries": entries,
    }


def persist_explain_log(ctx) -> Path | None:
    if not explain_enabled(getattr(ctx, "config", None)):
        return None
    project_root = getattr(ctx, "project_root", None)
    if not isinstance(project_root, str) or not project_root:
        return None
    entries = getattr(ctx, "explain_log", None)
    if not isinstance(entries, list) or not entries:
        return None
    flow_name = str(getattr(getattr(ctx, "flow", None), "name", "") or "flow")
    payload = build_explain_log_payload(flow_name=flow_name, entries=list(entries))
    explain_root = Path(project_root) / ".namel3ss" / "explain"
    explain_root.mkdir(parents=True, exist_ok=True)
    stable_path = explain_root / "last_explain.json"
    flow_path = explain_root / f"{_safe_name(flow_name)}_last_explain.json"
    canonical_json_dump(stable_path, payload, pretty=True, drop_run_keys=False)
    canonical_json_dump(flow_path, payload, pretty=True, drop_run_keys=False)
    return stable_path


def load_explain_log(path: Path) -> dict[str, object]:
    value = _load_json_object(path)
    entries = value.get("entries")
    if not isinstance(entries, list):
        value["entries"] = []
    value["replay_hash"] = explain_replay_hash(value.get("entries") if isinstance(value.get("entries"), list) else [])
    return value


def explain_replay_hash(entries: list[dict[str, object]] | None) -> str:
    payload = canonical_json_dumps(entries or [], pretty=False, drop_run_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def logical_timestamp(index: int) -> str:
    logical = _LOGICAL_EPOCH + timedelta(milliseconds=max(0, int(index)))
    return logical.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _load_json_object(path: Path) -> dict[str, object]:
    import json

    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return raw
    return {}


def _redact(value: object, *, enabled: bool, key: str | None = None) -> object:
    if not enabled:
        return value
    if key and key.lower() in _REDACTABLE_KEYS:
        if value is None:
            return None
        return _REDACTED
    if isinstance(value, dict):
        return {str(k): _redact(v, enabled=enabled, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item, enabled=enabled) for item in value]
    if isinstance(value, tuple):
        return [_redact(item, enabled=enabled) for item in value]
    return value


def _safe_name(value: str) -> str:
    parts = []
    for char in str(value or ""):
        if char.isalnum() or char in {"-", "_", "."}:
            parts.append(char)
        else:
            parts.append("_")
    cleaned = "".join(parts).strip("._")
    return cleaned or "flow"


__all__ = [
    "append_explain_entry",
    "append_job_entry",
    "append_performance_entry",
    "append_streaming_entry",
    "build_explain_log_payload",
    "explain_enabled",
    "explain_replay_hash",
    "load_explain_log",
    "logical_timestamp",
    "persist_explain_log",
    "redact_user_data_enabled",
]
