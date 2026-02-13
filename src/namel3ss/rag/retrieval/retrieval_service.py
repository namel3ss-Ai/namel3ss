from __future__ import annotations

from namel3ss.config.model import AppConfig
from namel3ss.rag.contracts.retrieval_config_model import (
    build_retrieval_config_model,
    normalize_retrieval_config_model,
)
from namel3ss.rag.observability.explain_service import build_retrieval_explain_payload
from namel3ss.rag.observability.trace_logger import (
    build_answer_stream_events,
    build_observability_trace_model,
)
from namel3ss.rag.retrieval.citation_mapper import map_answer_citations
from namel3ss.rag.retrieval.pdf_preview_mapper import build_pdf_preview_routes
from namel3ss.rag.retrieval.rerank_service import build_ranked_retrieval_results
from namel3ss.rag.retrieval.scope_service import apply_retrieval_scope
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.answer.api import run_answer


def run_retrieval_service(
    *,
    query: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    retrieval_config: dict[str, object] | None = None,
    tier: str | None = None,
) -> dict[str, object]:
    config_model = _resolved_retrieval_config(retrieval_config)
    scoped_state, scope_summary = apply_retrieval_scope(
        state=state,
        scope=config_model.get("scope"),
    )
    limit = int(config_model.get("top_k") or 8)
    filter_tags = _filter_tags(config_model)
    raw = run_retrieval(
        query=query,
        state=scoped_state,
        project_root=project_root,
        app_path=app_path,
        limit=limit,
        tier=tier,
        filter_tags=filter_tags,
    )
    trace_rows = list(raw.get("retrieval_trace") or [])
    contract_rows = build_ranked_retrieval_results(
        results=raw.get("results"),
        retrieval_trace=trace_rows,
    )
    retrieval_plan = dict(raw.get("retrieval_plan") or {})
    retrieval_tuning = dict(raw.get("retrieval_tuning") or {})
    trust_score_details = dict(raw.get("trust_score_details") or {})
    retrieval_explain = build_retrieval_explain_payload(
        query=_text(query),
        retrieval_results=contract_rows,
        retrieval_trace=trace_rows,
        retrieval_plan=retrieval_plan,
        retrieval_tuning=retrieval_tuning,
        trust_score_details=trust_score_details,
        retrieval_scope=scope_summary,
    )
    observability_trace = build_observability_trace_model(
        query=_text(query),
        retrieval_config=config_model,
        retrieval_results=contract_rows,
        retrieval_scope=scope_summary,
        retrieval_plan=retrieval_plan,
        stream_events=[
            {
                "event_type": "trace_event",
                "payload": {
                    "result_count": len(contract_rows),
                    "stage": "retrieval",
                },
                "sequence": 1,
            },
            {
                "event_type": "final",
                "payload": {
                    "result_count": len(contract_rows),
                    "stage": "retrieval",
                },
                "sequence": 2,
            },
        ],
    )
    return {
        "retrieval_config": config_model,
        "retrieval_scope": scope_summary,
        "retrieval_results": contract_rows,
        "retrieval_plan": retrieval_plan,
        "retrieval_tuning": retrieval_tuning,
        "trust_score_details": trust_score_details,
        "retrieval_explain": retrieval_explain,
        "observability_trace": observability_trace,
        "retrieval_preview": list(raw.get("retrieval_preview") or []),
        "raw": raw,
    }


def run_chat_answer_service(
    *,
    query: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    provider: AIProvider,
    provider_name: str,
    config: AppConfig | None = None,
    model: str | None = None,
    retrieval_config: dict[str, object] | None = None,
    tier: str | None = None,
) -> dict[str, object]:
    config_model = _resolved_retrieval_config(retrieval_config)
    scoped_state, scope_summary = apply_retrieval_scope(
        state=state,
        scope=config_model.get("scope"),
    )
    limit = int(config_model.get("top_k") or 8)
    report, meta = run_answer(
        query=query,
        state=scoped_state,
        project_root=project_root,
        app_path=app_path,
        limit=limit,
        tier=tier,
        config=config or AppConfig(),
        provider=provider,
        provider_name=provider_name,
        model=model,
    )
    retrieval_trace = list(report.get("retrieval_trace") or [])
    retrieval_results = build_ranked_retrieval_results(
        results=retrieval_trace,
        retrieval_trace=retrieval_trace,
    )
    index_chunks = list((scoped_state.get("index") or {}).get("chunks") or []) if isinstance(scoped_state, dict) else []
    citations = map_answer_citations(
        answer_text=str(report.get("answer_text") or ""),
        citation_chunk_ids=list(report.get("citations") or []),
        retrieval_trace=retrieval_trace,
        index_chunks=index_chunks,
    )
    snippet_by_chunk = _snippet_map(index_chunks)
    pdf_preview_routes = build_pdf_preview_routes(citations=citations, snippet_by_chunk=snippet_by_chunk)
    retrieval_plan = dict(report.get("retrieval_plan") or {})
    trust_score_details = dict(report.get("trust_score_details") or {})
    retrieval_tuning = dict(report.get("retrieval_tuning") or {})
    retrieval_explain = build_retrieval_explain_payload(
        query=_text(query),
        retrieval_results=retrieval_results,
        retrieval_trace=retrieval_trace,
        retrieval_plan=retrieval_plan,
        retrieval_tuning=retrieval_tuning,
        trust_score_details=trust_score_details,
        retrieval_scope=scope_summary,
    )
    stream_events = build_answer_stream_events(
        answer_text=str(report.get("answer_text") or ""),
        citations=citations,
        retrieval_trace=retrieval_trace,
    )
    observability_trace = build_observability_trace_model(
        query=_text(query),
        retrieval_config=config_model,
        retrieval_results=retrieval_results,
        retrieval_scope=scope_summary,
        retrieval_plan=retrieval_plan,
        stream_events=stream_events,
    )
    return {
        "answer_text": str(report.get("answer_text") or ""),
        "citations": citations,
        "confidence": float(report.get("confidence") or 0),
        "retrieval_plan": retrieval_plan,
        "retrieval_trace": retrieval_trace,
        "retrieval_results": retrieval_results,
        "retrieval_config": config_model,
        "retrieval_scope": scope_summary,
        "retrieval_tuning": retrieval_tuning,
        "trust_score_details": trust_score_details,
        "retrieval_explain": retrieval_explain,
        "observability_trace": observability_trace,
        "pdf_preview_routes": pdf_preview_routes,
        "meta": meta,
    }


def _resolved_retrieval_config(value: dict[str, object] | None) -> dict[str, object]:
    if isinstance(value, dict):
        return normalize_retrieval_config_model(value)
    return build_retrieval_config_model()


def _filter_tags(config_model: dict[str, object]) -> list[str] | None:
    filters = config_model.get("filters")
    if not isinstance(filters, dict):
        return None
    tags = filters.get("tags")
    if not isinstance(tags, list):
        return None
    normalized: list[str] = []
    for item in tags:
        if not isinstance(item, str):
            continue
        token = item.strip()
        if not token:
            continue
        normalized.append(token)
    return normalized or None


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _snippet_map(rows: list[object]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        chunk_id = _text(row.get("chunk_id"))
        text = _text(row.get("text"))
        if not chunk_id or not text:
            continue
        mapped[chunk_id] = text
    return mapped


__all__ = [
    "run_chat_answer_service",
    "run_retrieval_service",
]
