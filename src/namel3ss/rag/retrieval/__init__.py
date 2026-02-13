from __future__ import annotations

from namel3ss.rag.retrieval.preview_router import (
    BASIC_PREVIEW_SCHEMA_VERSION,
    build_preview_routes,
)
from namel3ss.rag.retrieval.citation_mapper import map_answer_citations
from namel3ss.rag.retrieval.highlight_resolver import resolve_highlight_for_chunk, resolve_highlight_target
from namel3ss.rag.retrieval.pdf_preview_mapper import (
    DEFAULT_COLOR_PALETTE_SIZE,
    PDF_PREVIEW_SCHEMA_VERSION,
    build_pdf_preview_routes,
    build_preview_page_url,
    citation_color_index,
)
from namel3ss.rag.retrieval.prompt_builder import build_chat_prompt
from namel3ss.rag.retrieval.rerank_service import (
    RERANK_SCHEMA_VERSION,
    build_ranked_retrieval_results,
)
from namel3ss.rag.retrieval.retrieval_service import (
    run_chat_answer_service,
    run_retrieval_service,
)
from namel3ss.rag.retrieval.scope_service import (
    SCOPE_STATE_SCHEMA_VERSION,
    apply_retrieval_scope,
    ensure_scope_state,
    resolve_scope_document_ids,
    upsert_collection_membership,
)

__all__ = [
    "BASIC_PREVIEW_SCHEMA_VERSION",
    "DEFAULT_COLOR_PALETTE_SIZE",
    "PDF_PREVIEW_SCHEMA_VERSION",
    "RERANK_SCHEMA_VERSION",
    "SCOPE_STATE_SCHEMA_VERSION",
    "apply_retrieval_scope",
    "build_chat_prompt",
    "build_pdf_preview_routes",
    "build_preview_page_url",
    "build_preview_routes",
    "build_ranked_retrieval_results",
    "citation_color_index",
    "ensure_scope_state",
    "map_answer_citations",
    "resolve_highlight_for_chunk",
    "resolve_highlight_target",
    "resolve_scope_document_ids",
    "run_chat_answer_service",
    "run_retrieval_service",
    "upsert_collection_membership",
]
