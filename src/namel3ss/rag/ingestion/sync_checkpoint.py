from __future__ import annotations

from copy import deepcopy


SYNC_CHECKPOINT_SCHEMA_VERSION = "rag.sync_checkpoint@1"
SYNC_STATE_SCHEMA_VERSION = "rag.sync_state@1"


def ensure_sync_state(state: dict) -> dict[str, object]:
    sync_state = state.get("rag_sync")
    if not isinstance(sync_state, dict):
        sync_state = {}
    checkpoints = sync_state.get("checkpoints")
    if not isinstance(checkpoints, dict):
        checkpoints = {}
    jobs = sync_state.get("jobs")
    if not isinstance(jobs, list):
        jobs = []
    sync_state = {
        "schema_version": _text(sync_state.get("schema_version")) or SYNC_STATE_SCHEMA_VERSION,
        "checkpoints": _normalize_checkpoint_map(checkpoints),
        "jobs": _normalize_jobs(jobs),
    }
    state["rag_sync"] = sync_state
    return sync_state


def build_sync_checkpoint(
    *,
    connector_id: str,
    cursor: str,
    doc_versions: dict[str, str] | None = None,
    schema_version: str = SYNC_CHECKPOINT_SCHEMA_VERSION,
) -> dict[str, object]:
    doc_versions_map = _normalize_doc_versions(doc_versions)
    return {
        "schema_version": _text(schema_version) or SYNC_CHECKPOINT_SCHEMA_VERSION,
        "connector_id": _text(connector_id),
        "cursor": _text(cursor),
        "doc_versions": doc_versions_map,
    }


def normalize_sync_checkpoint(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    return build_sync_checkpoint(
        connector_id=_text(data.get("connector_id")),
        cursor=_text(data.get("cursor")),
        doc_versions=_normalize_doc_versions(data.get("doc_versions") if isinstance(data.get("doc_versions"), dict) else {}),
        schema_version=_text(data.get("schema_version")) or SYNC_CHECKPOINT_SCHEMA_VERSION,
    )


def read_sync_checkpoint(state: dict, connector_id: str) -> dict[str, object]:
    sync_state = ensure_sync_state(state)
    checkpoints = sync_state.get("checkpoints")
    assert isinstance(checkpoints, dict)
    key = _text(connector_id)
    value = checkpoints.get(key)
    if not isinstance(value, dict):
        return build_sync_checkpoint(connector_id=key, cursor="", doc_versions={})
    return normalize_sync_checkpoint(value)


def write_sync_checkpoint(state: dict, checkpoint: dict[str, object]) -> dict[str, object]:
    normalized = normalize_sync_checkpoint(checkpoint)
    connector_id = _text(normalized.get("connector_id"))
    sync_state = ensure_sync_state(state)
    checkpoints = dict(sync_state.get("checkpoints") or {})
    checkpoints[connector_id] = normalized
    sync_state["checkpoints"] = _normalize_checkpoint_map(checkpoints)
    state["rag_sync"] = sync_state
    return deepcopy(normalized)


def merge_checkpoint_cursor(current_cursor: str, incoming_cursor: str) -> str:
    current = _text(current_cursor)
    incoming = _text(incoming_cursor)
    if not current:
        return incoming
    if not incoming:
        return current
    return incoming if incoming > current else current


def append_sync_job(state: dict, job: dict[str, object]) -> dict[str, object]:
    sync_state = ensure_sync_state(state)
    jobs = list(sync_state.get("jobs") or [])
    normalized = _normalize_job(job)
    normalized_job_id = _text(normalized.get("job_id"))
    jobs = [entry for entry in jobs if _text(entry.get("job_id")) != normalized_job_id]
    jobs.append(normalized)
    sync_state["jobs"] = _normalize_jobs(jobs)
    state["rag_sync"] = sync_state
    return deepcopy(normalized)


def list_sync_jobs(state: dict, *, connector_id: str | None = None) -> list[dict[str, object]]:
    sync_state = ensure_sync_state(state)
    jobs = list(sync_state.get("jobs") or [])
    normalized = _normalize_jobs(jobs)
    connector_filter = _text(connector_id)
    if connector_filter:
        normalized = [entry for entry in normalized if _text(entry.get("connector_id")) == connector_filter]
    return [deepcopy(entry) for entry in normalized]


def _normalize_checkpoint_map(value: dict[str, object]) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for key in sorted(value.keys(), key=lambda item: str(item)):
        connector_id = _text(key)
        if not connector_id:
            continue
        rows[connector_id] = normalize_sync_checkpoint(value[key])
    return rows


def _normalize_doc_versions(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    rows: dict[str, str] = {}
    for key in sorted(value.keys(), key=lambda item: str(item)):
        source_identity = _text(key)
        version = _text(value.get(key))
        if not source_identity or not version:
            continue
        rows[source_identity] = version
    return rows


def _normalize_jobs(value: list[object]) -> list[dict[str, object]]:
    rows = [_normalize_job(entry) for entry in value if isinstance(entry, dict)]
    rows.sort(
        key=lambda entry: (
            _text(entry.get("connector_id")),
            _text(entry.get("cursor")),
            _text(entry.get("job_id")),
        )
    )
    return rows


def _normalize_job(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    job_id = _text(data.get("job_id"))
    connector_id = _text(data.get("connector_id"))
    if not job_id:
        job_id = _text(data.get("cursor")) or f"sync.{connector_id}"
    return {
        "job_id": job_id,
        "connector_id": connector_id,
        "cursor": _text(data.get("cursor")),
        "status": _text(data.get("status")) or "completed",
        "upserted": _non_negative(data.get("upserted"), default=0),
        "deleted": _non_negative(data.get("deleted"), default=0),
        "skipped": _non_negative(data.get("skipped"), default=0),
    }


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _non_negative(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) >= 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if parsed >= 0:
            return parsed
    return default


__all__ = [
    "SYNC_CHECKPOINT_SCHEMA_VERSION",
    "SYNC_STATE_SCHEMA_VERSION",
    "append_sync_job",
    "build_sync_checkpoint",
    "ensure_sync_state",
    "list_sync_jobs",
    "merge_checkpoint_cursor",
    "normalize_sync_checkpoint",
    "read_sync_checkpoint",
    "write_sync_checkpoint",
]
