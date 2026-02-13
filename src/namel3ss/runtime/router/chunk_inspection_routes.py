from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.rag.indexing.chunk_inspector_service import build_chunk_inspection_payload
from namel3ss.runtime.conventions.errors import build_error_envelope


@dataclass(frozen=True)
class ChunkInspectionRoutePayload:
    response: dict
    status: int
    yield_messages: list[dict]


def dispatch_chunk_inspection_route(
    *,
    method: str,
    path: str,
    query_values: dict[str, str],
    store,
    program,
) -> ChunkInspectionRoutePayload | None:
    if _segments(path) != ("api", "chunks", "inspection"):
        return None
    if not _has_state_store(store):
        return _error_payload(program, "Chunk inspection route requires a stateful runtime store.", status=500)
    method_name = str(method or "").upper()
    if method_name != "GET":
        return _method_not_allowed(program, allowed=("GET",))
    state = _load_state(store)
    payload = build_chunk_inspection_payload(
        state=state,
        document_id=_query_document_id(query_values),
        limit=_query_int(query_values, "limit"),
        offset=_query_int(query_values, "offset"),
    )
    rows = payload.get("rows")
    returned_count = len(rows) if isinstance(rows, list) else 0
    response = {
        "chunk_inspection": payload,
        "ok": True,
    }
    return ChunkInspectionRoutePayload(
        response=response,
        status=200,
        yield_messages=[
            _event(
                "yield",
                output={
                    "document_id": str(payload.get("document_id") or ""),
                    "returned_count": returned_count,
                    "total_count": int(payload.get("total_count") or 0),
                },
            )
        ],
    )


def _query_document_id(query_values: dict[str, str]) -> str | None:
    for key in ("document_id", "doc_id", "doc"):
        value = query_values.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _query_int(query_values: dict[str, str], key: str) -> int | None:
    value = query_values.get(key)
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token or not token.isdigit():
        return None
    return int(token)


def _event(event_type: str, *, output: dict) -> dict:
    return {
        "event_type": event_type,
        "flow_name": "chunk.inspection",
        "output": output,
        "sequence": 1,
        "stream_channel": "chat",
        "stream_id": "chunk.inspection",
    }


def _error_payload(program, message: str, *, status: int) -> ChunkInspectionRoutePayload:
    error = Namel3ssError(message, details={"http_status": status, "category": "chunk_inspection_router"})
    return ChunkInspectionRoutePayload(
        response=build_error_envelope(error=error, project_root=getattr(program, "project_root", None)),
        status=status,
        yield_messages=[],
    )


def _method_not_allowed(program, *, allowed: tuple[str, ...]) -> ChunkInspectionRoutePayload:
    message = f"Method is not allowed for chunk inspection route. Allowed methods: {', '.join(allowed)}"
    payload = _error_payload(program, message, status=405)
    response = dict(payload.response)
    response["allowed_methods"] = list(allowed)
    return ChunkInspectionRoutePayload(response=response, status=payload.status, yield_messages=payload.yield_messages)


def _segments(path: str) -> tuple[str, ...]:
    return tuple(part for part in str(path or "").strip("/").split("/") if part)


def _has_state_store(store) -> bool:
    return bool(store and hasattr(store, "load_state") and hasattr(store, "save_state"))


def _load_state(store) -> dict:
    value = store.load_state()
    if isinstance(value, dict):
        return value
    return {}


__all__ = ["ChunkInspectionRoutePayload", "dispatch_chunk_inspection_route"]
