from __future__ import annotations

from copy import deepcopy


SCOPE_STATE_SCHEMA_VERSION = "rag.scope_state@1"


def ensure_scope_state(state: dict) -> dict[str, object]:
    scope_state = state.get("rag_scope")
    if not isinstance(scope_state, dict):
        scope_state = {}
    collections = scope_state.get("collections")
    if not isinstance(collections, list):
        collections = []
    normalized = {
        "schema_version": _text(scope_state.get("schema_version")) or SCOPE_STATE_SCHEMA_VERSION,
        "collections": _normalize_collections(collections),
    }
    state["rag_scope"] = normalized
    return deepcopy(normalized)


def upsert_collection_membership(
    state: dict,
    *,
    collection_id: str,
    document_id: str,
    name: str = "",
    connector_id: str = "",
    source_type: str = "",
) -> dict[str, object]:
    scope_state = ensure_scope_state(state)
    collection_key = _text(collection_id)
    document_key = _text(document_id)
    if not collection_key or not document_key:
        return {
            "collection_id": collection_key,
            "documents": [],
            "name": _text(name),
            "connector_id": _text(connector_id),
            "source_type": _text(source_type),
        }

    rows = list(scope_state.get("collections") or [])
    mapped: dict[str, dict[str, object]] = {}
    for row in rows:
        normalized = _normalize_collection(row)
        mapped[normalized["collection_id"]] = normalized

    current = mapped.get(collection_key)
    if current is None:
        current = _normalize_collection(
            {
                "collection_id": collection_key,
                "documents": [document_key],
                "name": _text(name) or collection_key,
                "connector_id": _text(connector_id),
                "source_type": _text(source_type),
            }
        )
    else:
        docs = sorted({*_normalize_text_list(current.get("documents")), document_key})
        current["documents"] = docs
        if _text(name):
            current["name"] = _text(name)
        if _text(connector_id):
            current["connector_id"] = _text(connector_id)
        if _text(source_type):
            current["source_type"] = _text(source_type)

    mapped[collection_key] = _normalize_collection(current)
    state["rag_scope"] = {
        "schema_version": _text(scope_state.get("schema_version")) or SCOPE_STATE_SCHEMA_VERSION,
        "collections": [mapped[key] for key in sorted(mapped.keys())],
    }
    return deepcopy(mapped[collection_key])


def remove_document_membership(state: dict, *, document_id: str) -> None:
    scope_state = ensure_scope_state(state)
    document_key = _text(document_id)
    rows = list(scope_state.get("collections") or [])
    next_rows: list[dict[str, object]] = []
    for row in rows:
        normalized = _normalize_collection(row)
        docs = [doc for doc in _normalize_text_list(normalized.get("documents")) if doc != document_key]
        normalized["documents"] = docs
        if docs:
            next_rows.append(normalized)
    state["rag_scope"] = {
        "schema_version": _text(scope_state.get("schema_version")) or SCOPE_STATE_SCHEMA_VERSION,
        "collections": next_rows,
    }


def resolve_scope_document_ids(state: dict, *, scope: object) -> list[str]:
    scope_payload = _normalize_scope(scope)
    explicit = set(scope_payload["documents"])
    collection_ids = scope_payload["collections"]
    if not collection_ids and explicit:
        return sorted(explicit)

    collection_docs: set[str] = set()
    if collection_ids:
        scope_state = ensure_scope_state(state)
        rows = list(scope_state.get("collections") or [])
        mapped = {_text(row.get("collection_id")): _normalize_collection(row) for row in rows if isinstance(row, dict)}
        for collection_id in collection_ids:
            row = mapped.get(collection_id)
            if row is None:
                continue
            collection_docs.update(_normalize_text_list(row.get("documents")))

    resolved = collection_docs | explicit
    return sorted(resolved)


def apply_retrieval_scope(
    *,
    state: dict,
    scope: object,
) -> tuple[dict, dict[str, object]]:
    scope_payload = _normalize_scope(scope)
    has_scope = bool(scope_payload["collections"] or scope_payload["documents"])
    resolved_documents = resolve_scope_document_ids(state, scope=scope_payload)

    summary = {
        "active": has_scope,
        "requested": scope_payload,
        "resolved_documents": resolved_documents,
    }
    if not has_scope:
        return state, summary

    allowed = set(resolved_documents)
    scoped_state = dict(state)

    ingestion = state.get("ingestion")
    if isinstance(ingestion, dict):
        scoped_state["ingestion"] = {
            key: value
            for key, value in ingestion.items()
            if _text(key) in allowed
        }

    index = state.get("index")
    if isinstance(index, dict):
        chunks = index.get("chunks")
        filtered_chunks = []
        if isinstance(chunks, list):
            for entry in chunks:
                if not isinstance(entry, dict):
                    continue
                if _doc_id(entry) in allowed:
                    filtered_chunks.append(entry)
        scoped_index = dict(index)
        scoped_index["chunks"] = filtered_chunks
        scoped_state["index"] = scoped_index

    return scoped_state, summary


def _normalize_scope(value: object) -> dict[str, list[str]]:
    data = value if isinstance(value, dict) else {}
    return {
        "collections": _normalize_text_list(data.get("collections")),
        "documents": _normalize_text_list(data.get("documents")),
    }


def _normalize_collections(value: list[object]) -> list[dict[str, object]]:
    rows = [_normalize_collection(row) for row in value if isinstance(row, dict)]
    rows.sort(key=lambda row: _text(row.get("collection_id")))
    return rows


def _normalize_collection(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    collection_id = _text(data.get("collection_id"))
    return {
        "collection_id": collection_id,
        "name": _text(data.get("name")) or collection_id,
        "connector_id": _text(data.get("connector_id")),
        "source_type": _text(data.get("source_type")),
        "documents": _normalize_text_list(data.get("documents")),
    }


def _normalize_text_list(value: object) -> list[str]:
    rows = value if isinstance(value, list) else []
    seen: set[str] = set()
    values: list[str] = []
    for row in rows:
        text = _text(row)
        if not text or text in seen:
            continue
        seen.add(text)
        values.append(text)
    values.sort()
    return values


def _doc_id(entry: dict[str, object]) -> str:
    return _text(entry.get("document_id") or entry.get("upload_id"))


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = [
    "SCOPE_STATE_SCHEMA_VERSION",
    "apply_retrieval_scope",
    "ensure_scope_state",
    "remove_document_membership",
    "resolve_scope_document_ids",
    "upsert_collection_membership",
]
