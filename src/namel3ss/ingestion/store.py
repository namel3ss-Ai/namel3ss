from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def store_report(state: dict, *, upload_id: str, report: dict) -> None:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    ingestion = state.get("ingestion")
    if ingestion is None:
        ingestion = {}
    if not isinstance(ingestion, dict):
        raise Namel3ssError(_ingestion_shape_message())
    ingestion[str(upload_id)] = dict(report)
    state["ingestion"] = ingestion


def update_index(
    state: dict,
    *,
    upload_id: str,
    chunks: list[dict],
    low_quality: bool,
) -> None:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    index = state.get("index")
    if index is None:
        index = {"chunks": []}
    if not isinstance(index, dict):
        raise Namel3ssError(_index_shape_message())
    entries = index.get("chunks")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise Namel3ssError(_index_chunks_shape_message())
    filtered = [entry for entry in entries if entry.get("upload_id") != upload_id]
    for chunk in chunks:
        entry = {
            "upload_id": upload_id,
            "chunk_id": f"{upload_id}:{chunk.get('index')}",
            "order": chunk.get("index"),
            "text": chunk.get("text"),
            "chars": chunk.get("chars"),
            "low_quality": bool(low_quality),
        }
        filtered.append(entry)
    index["chunks"] = filtered
    state["index"] = index


def drop_index(state: dict, *, upload_id: str) -> None:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    index = state.get("index")
    if not isinstance(index, dict):
        return
    entries = index.get("chunks")
    if not isinstance(entries, list):
        return
    index["chunks"] = [entry for entry in entries if entry.get("upload_id") != upload_id]


def _state_type_message() -> str:
    return build_guidance_message(
        what="State must be an object.",
        why="Ingestion writes reports and index entries into state.",
        fix="Ensure state is a JSON object.",
        example='{"ingestion":{}, "index":{"chunks":[]}}',
    )


def _ingestion_shape_message() -> str:
    return build_guidance_message(
        what="state.ingestion must be an object.",
        why="Ingestion reports are stored under state.ingestion.",
        fix="Replace state.ingestion with a map of upload ids.",
        example='{"ingestion":{"abc123":{}}}',
    )


def _index_shape_message() -> str:
    return build_guidance_message(
        what="state.index must be an object.",
        why="The ingestion index is stored under state.index.",
        fix="Replace state.index with an object containing chunks.",
        example='{"index":{"chunks":[]}}',
    )


def _index_chunks_shape_message() -> str:
    return build_guidance_message(
        what="state.index.chunks must be a list.",
        why="Index entries are stored as a list of chunks.",
        fix="Replace state.index.chunks with a list.",
        example='{"index":{"chunks":[]}}',
    )


__all__ = ["store_report", "update_index", "drop_index"]
