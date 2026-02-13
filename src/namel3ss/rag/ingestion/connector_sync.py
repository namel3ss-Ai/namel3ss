from __future__ import annotations

from copy import deepcopy

from namel3ss.rag.determinism.json_policy import canonical_contract_hash
from namel3ss.rag.determinism.id_policy import build_doc_id
from namel3ss.rag.ingestion.connector_registry import ensure_connector_registry, list_connector_specs
from namel3ss.rag.ingestion.ingestion_pipeline import run_ingestion_pipeline
from namel3ss.rag.ingestion.sync_checkpoint import (
    append_sync_job,
    build_sync_checkpoint,
    merge_checkpoint_cursor,
    read_sync_checkpoint,
    write_sync_checkpoint,
)
from namel3ss.rag.retrieval.scope_service import remove_document_membership, upsert_collection_membership


CONNECTOR_SYNC_RUN_SCHEMA_VERSION = "rag.connector_sync_run@1"


def run_connector_sync(
    *,
    state: dict,
    connector_id: str,
    records: list[object],
    schema_version: str = CONNECTOR_SYNC_RUN_SCHEMA_VERSION,
) -> dict[str, object]:
    connector_spec = _connector_spec(state, connector_id=connector_id)
    checkpoint = read_sync_checkpoint(state, connector_spec["connector_id"])
    collapsed = _collapse_records(records)
    prior_versions = dict(checkpoint.get("doc_versions") or {})

    upserted = 0
    deleted = 0
    skipped = 0
    next_versions = dict(prior_versions)
    cursor = _text(checkpoint.get("cursor"))

    for record in collapsed:
        cursor = merge_checkpoint_cursor(cursor, _text(record.get("cursor")))
        source_identity = _text(record.get("source_identity"))
        if not source_identity:
            skipped += 1
            continue
        doc_id = build_doc_id(source_type=connector_spec["source_type"], source_identity=source_identity)
        if bool(record.get("deleted")):
            _delete_document(state, doc_id=doc_id)
            next_versions.pop(source_identity, None)
            deleted += 1
            continue

        content = _content_bytes(record.get("content"))
        source_uri = _text(record.get("source_uri")) or f"{connector_spec['source_type']}://{source_identity}"
        title = _text(record.get("title")) or source_identity
        mime_type = _text(record.get("mime_type")) or "text/plain"

        run_payload = run_ingestion_pipeline(
            state=state,
            content=content,
            source_name=title,
            source_identity=source_identity,
            source_type=connector_spec["source_type"],
            source_uri=source_uri,
            mime_type=mime_type,
        )
        document = run_payload.get("document") if isinstance(run_payload.get("document"), dict) else {}
        doc_version_id = _text(document.get("doc_version_id"))
        previous_doc_version = _text(prior_versions.get(source_identity))
        if doc_version_id and previous_doc_version and doc_version_id == previous_doc_version:
            skipped += 1
        else:
            upserted += 1
        if doc_version_id:
            next_versions[source_identity] = doc_version_id

        collection_ids = _normalize_text_list(record.get("collection_ids"))
        for collection_id in collection_ids:
            upsert_collection_membership(
                state,
                collection_id=collection_id,
                document_id=doc_id,
                name=collection_id,
            )

    normalized_checkpoint = build_sync_checkpoint(
        connector_id=connector_spec["connector_id"],
        cursor=cursor,
        doc_versions=next_versions,
    )
    write_sync_checkpoint(state, normalized_checkpoint)

    job_id = _sync_job_id(
        connector_id=connector_spec["connector_id"],
        cursor=cursor,
        upserted=upserted,
        deleted=deleted,
        skipped=skipped,
    )
    append_sync_job(
        state,
        {
            "job_id": job_id,
            "connector_id": connector_spec["connector_id"],
            "cursor": cursor,
            "status": "completed",
            "upserted": upserted,
            "deleted": deleted,
            "skipped": skipped,
        },
    )

    return {
        "schema_version": _text(schema_version) or CONNECTOR_SYNC_RUN_SCHEMA_VERSION,
        "connector": deepcopy(connector_spec),
        "checkpoint": normalized_checkpoint,
        "job": {
            "job_id": job_id,
            "connector_id": connector_spec["connector_id"],
            "cursor": cursor,
            "status": "completed",
            "upserted": upserted,
            "deleted": deleted,
            "skipped": skipped,
        },
        "record_count": len(collapsed),
    }


def list_sync_jobs_for_connector(state: dict, connector_id: str) -> list[dict[str, object]]:
    from namel3ss.rag.ingestion.sync_checkpoint import list_sync_jobs

    return list_sync_jobs(state, connector_id=connector_id)


def _connector_spec(state: dict, *, connector_id: str) -> dict[str, object]:
    ensure_connector_registry(state)
    connector_key = _text(connector_id)
    specs = list_connector_specs(state, include_disabled=True)
    for entry in specs:
        if _text(entry.get("connector_id")) == connector_key:
            return dict(entry)
    return {
        "connector_id": connector_key,
        "cursor_field": "cursor",
        "enabled": True,
        "name": connector_key,
        "source_type": connector_key,
        "sync_mode": "incremental",
    }


def _collapse_records(records: list[object]) -> list[dict[str, object]]:
    rows = [_normalize_record(entry) for entry in records if isinstance(entry, dict)]
    rows.sort(
        key=lambda entry: (
            _text(entry.get("source_identity")),
            _text(entry.get("cursor")),
            1 if bool(entry.get("deleted")) else 0,
            _text(entry.get("title")),
        )
    )
    collapsed: dict[str, dict[str, object]] = {}
    for row in rows:
        source_identity = _text(row.get("source_identity"))
        if not source_identity:
            continue
        current = collapsed.get(source_identity)
        if current is None:
            collapsed[source_identity] = row
            continue
        merged = _merge_record(current, row)
        collapsed[source_identity] = merged
    return [collapsed[key] for key in sorted(collapsed.keys())]


def _merge_record(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    left_cursor = _text(left.get("cursor"))
    right_cursor = _text(right.get("cursor"))
    if right_cursor > left_cursor:
        return right
    if right_cursor < left_cursor:
        return left
    if bool(right.get("deleted")) and not bool(left.get("deleted")):
        return right
    if bool(left.get("deleted")) and not bool(right.get("deleted")):
        return left
    left_key = canonical_contract_hash(left)
    right_key = canonical_contract_hash(right)
    return right if right_key > left_key else left


def _normalize_record(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    return {
        "source_identity": _text(data.get("source_identity")),
        "cursor": _text(data.get("cursor")),
        "deleted": bool(data.get("deleted")),
        "title": _text(data.get("title")),
        "source_uri": _text(data.get("source_uri")),
        "mime_type": _text(data.get("mime_type")) or "text/plain",
        "content": data.get("content"),
        "collection_ids": _normalize_text_list(data.get("collection_ids")),
    }


def _delete_document(state: dict, *, doc_id: str) -> None:
    ingestion = state.get("ingestion")
    if isinstance(ingestion, dict):
        ingestion.pop(doc_id, None)
    index = state.get("index")
    if isinstance(index, dict) and isinstance(index.get("chunks"), list):
        index["chunks"] = [entry for entry in index["chunks"] if _text(entry.get("upload_id")) != doc_id]
    remove_document_membership(state, document_id=doc_id)


def _content_bytes(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return b""


def _sync_job_id(*, connector_id: str, cursor: str, upserted: int, deleted: int, skipped: int) -> str:
    payload = {
        "connector_id": _text(connector_id),
        "cursor": _text(cursor),
        "upserted": int(upserted),
        "deleted": int(deleted),
        "skipped": int(skipped),
    }
    digest = canonical_contract_hash(payload)
    return f"sync.{_text(connector_id)}.{digest[:12]}"


def _normalize_text_list(value: object) -> list[str]:
    values = value if isinstance(value, list) else []
    rows: list[str] = []
    seen: set[str] = set()
    for entry in values:
        text = _text(entry)
        if not text or text in seen:
            continue
        seen.add(text)
        rows.append(text)
    rows.sort()
    return rows


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = [
    "CONNECTOR_SYNC_RUN_SCHEMA_VERSION",
    "list_sync_jobs_for_connector",
    "run_connector_sync",
]
