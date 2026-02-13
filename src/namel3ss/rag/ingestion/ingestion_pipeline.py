from __future__ import annotations

from namel3ss.rag.contracts.document_model import build_document_model
from namel3ss.rag.indexing.chunk_builder import CHUNKING_VERSION, DEFAULT_MAX_CHARS, DEFAULT_OVERLAP, build_chunk_rows
from namel3ss.rag.indexing.index_service import INDEX_SCHEMA_VERSION, index_document_chunks
from namel3ss.rag.parsing.document_parser import PARSER_VERSION, parse_document_bytes


INGESTION_JOB_SCHEMA_VERSION = "rag.ingestion_job@1"


def run_ingestion_pipeline(
    *,
    state: dict,
    content: bytes,
    source_name: str,
    source_identity: str,
    source_type: str = "upload",
    source_uri: str = "",
    mime_type: str = "",
    mode: str | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
    schema_version: str = INGESTION_JOB_SCHEMA_VERSION,
) -> dict[str, object]:
    document = build_document_model(
        source_type=source_type,
        source_identity=source_identity,
        source_uri=source_uri,
        title=source_name,
        mime_type=mime_type,
        content=content.decode("utf-8", errors="replace"),
    )
    parser_payload = parse_document_bytes(
        content=content,
        metadata={
            "name": source_name,
            "content_type": mime_type,
        },
        mode=mode,
        parser_version=PARSER_VERSION,
    )
    chunk_rows = build_chunk_rows(
        document=document,
        pages=[str(page) for page in parser_payload.get("pages", []) if isinstance(page, str)],
        source_name=source_name,
        phase="deep",
        max_chars=max_chars,
        overlap=overlap,
        chunking_version=CHUNKING_VERSION,
    )
    index_summary = index_document_chunks(
        state=state,
        document=document,
        chunk_rows=chunk_rows,
        parser_payload=parser_payload,
        status="pass",
        schema_version=INDEX_SCHEMA_VERSION,
    )
    return {
        "schema_version": schema_version.strip() or INGESTION_JOB_SCHEMA_VERSION,
        "status": "pass",
        "document": document,
        "parser": {
            "schema_version": PARSER_VERSION,
            "detected": parser_payload.get("detected", {}),
            "method_used": parser_payload.get("method_used", "primary"),
            "fallback_used": parser_payload.get("fallback_used", False),
        },
        "chunking": {
            "schema_version": CHUNKING_VERSION,
            "chunk_count": len(chunk_rows),
            "max_chars": max_chars,
            "overlap": overlap,
        },
        "index": index_summary,
    }


__all__ = [
    "INGESTION_JOB_SCHEMA_VERSION",
    "run_ingestion_pipeline",
]
