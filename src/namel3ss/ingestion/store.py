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
        document_id = _string_value(chunk.get("document_id"))
        source_name = _string_value(chunk.get("source_name"))
        page_number = _page_number_value(chunk.get("page_number"))
        chunk_index = _chunk_index_value(chunk.get("chunk_index"))
        phase = _phase_value(chunk.get("ingestion_phase"))
        if (
            document_id is None
            or source_name is None
            or page_number is None
            or chunk_index is None
            or phase is None
        ):
            raise Namel3ssError(_chunk_provenance_message())
        entry = {
            "upload_id": upload_id,
            "document_id": document_id,
            "source_name": source_name,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "chunk_id": f"{upload_id}:{chunk_index}",
            "order": chunk_index,
            "text": chunk.get("text"),
            "chars": chunk.get("chars"),
            "low_quality": bool(low_quality),
            "ingestion_phase": phase,
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


def _chunk_provenance_message() -> str:
    return build_guidance_message(
        what="Indexed chunks are missing page provenance.",
        why="Ingestion must include document_id, source_name, page_number, chunk_index, and ingestion_phase for every chunk.",
        fix="Re-run ingestion to rebuild chunks with provenance and phase metadata.",
        example='{"upload_id":"<checksum>"}',
    )


def _string_value(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return None


def _page_number_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _chunk_index_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _phase_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    phase = value.strip().lower()
    if phase in {"quick", "deep"}:
        return phase
    return None


__all__ = ["store_report", "update_index", "drop_index"]
