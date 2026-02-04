from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.keywords import normalize_keywords


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
        keywords = _keywords_value(chunk.get("keywords"))
        if (
            document_id is None
            or source_name is None
            or page_number is None
            or chunk_index is None
            or phase is None
            or keywords is None
        ):
            raise Namel3ssError(_chunk_provenance_message())
        chunk_id = f"{upload_id}:{chunk_index}"
        highlight = _highlight_value(
            chunk.get("highlight"),
            document_id=document_id,
            page_number=page_number,
            chunk_id=chunk_id,
        )
        entry = {
            "upload_id": upload_id,
            "document_id": document_id,
            "source_name": source_name,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "chunk_id": chunk_id,
            "order": chunk_index,
            "text": chunk.get("text"),
            "chars": chunk.get("chars"),
            "low_quality": bool(low_quality),
            "ingestion_phase": phase,
            "keywords": keywords,
            "highlight": highlight,
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
        why=(
            "Ingestion must include document_id, source_name, page_number, chunk_index, "
            "ingestion_phase, and keywords for every chunk."
        ),
        fix="Re-run ingestion to rebuild chunks with provenance and phase metadata.",
        example='{"upload_id":"<checksum>"}',
    )


def _highlight_status_message(value: str) -> str:
    return build_guidance_message(
        what=f"Highlight status '{value}' is invalid.",
        why="Highlight status must be exact or unavailable.",
        fix="Store highlight anchors with a valid status.",
        example='{"status":"exact","start_char":0,"end_char":42}',
    )


def _highlight_span_message() -> str:
    return build_guidance_message(
        what="Highlight span is invalid.",
        why="Highlight anchors must include start_char and end_char for exact matches.",
        fix="Re-run ingestion to rebuild highlight anchors.",
        example='{"status":"exact","start_char":0,"end_char":42}',
    )


def _highlight_identity_message() -> str:
    return build_guidance_message(
        what="Highlight anchor does not match chunk metadata.",
        why="Highlight anchors must reference the same document, page, and chunk.",
        fix="Re-run ingestion to rebuild highlight anchors.",
        example='{"status":"exact","chunk_id":"<checksum>:0"}',
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


def _highlight_value(value: object, *, document_id: str, page_number: int, chunk_id: str) -> dict:
    if not isinstance(value, dict):
        return _unavailable_highlight(document_id, page_number, chunk_id)
    status = value.get("status")
    if not isinstance(status, str):
        return _unavailable_highlight(document_id, page_number, chunk_id)
    status_value = status.strip().lower()
    if status_value not in {"exact", "unavailable"}:
        raise Namel3ssError(_highlight_status_message(status_value))
    if _string_value(value.get("document_id")) and value.get("document_id") != document_id:
        raise Namel3ssError(_highlight_identity_message())
    if _page_number_value(value.get("page_number")) and value.get("page_number") != page_number:
        raise Namel3ssError(_highlight_identity_message())
    if _string_value(value.get("chunk_id")) and value.get("chunk_id") != chunk_id:
        raise Namel3ssError(_highlight_identity_message())
    if status_value == "exact":
        start_char = _coerce_int(value.get("start_char"))
        end_char = _coerce_int(value.get("end_char"))
        if start_char is None or end_char is None or start_char < 0 or end_char <= start_char:
            raise Namel3ssError(_highlight_span_message())
        return {
            "document_id": document_id,
            "page_number": page_number,
            "chunk_id": chunk_id,
            "start_char": start_char,
            "end_char": end_char,
            "status": "exact",
        }
    return _unavailable_highlight(document_id, page_number, chunk_id)


def _keywords_value(value: object) -> list[str] | None:
    return normalize_keywords(value)


def _unavailable_highlight(document_id: str, page_number: int, chunk_id: str) -> dict:
    return {
        "document_id": document_id,
        "page_number": page_number,
        "chunk_id": chunk_id,
        "start_char": None,
        "end_char": None,
        "status": "unavailable",
    }


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


__all__ = ["store_report", "update_index", "drop_index"]
