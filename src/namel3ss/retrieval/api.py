from __future__ import annotations

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.keywords import extract_keywords, keyword_matches, normalize_keywords
from namel3ss.ingestion.normalize import sanitize_text
from namel3ss.ingestion.policy import (
    ACTION_RETRIEVAL_INCLUDE_WARN,
    PolicyDecision,
    evaluate_ingestion_policy,
    load_ingestion_policy,
)
from namel3ss.retrieval.embedding_plan import build_embedding_plan
from namel3ss.retrieval.explain import RetrievalExplainBuilder
from namel3ss.retrieval.ordering import coerce_int, ordering_label, rank_key, select_tier


def run_retrieval(
    *,
    query: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    limit: int | None = None,
    tier: str | None = None,
    explain: bool = False,
    secret_values: list[str] | None = None,
    identity: dict | None = None,
    policy_decision: PolicyDecision | None = None,
    policy_decl: object | None = None,
    config: AppConfig | None = None,
    capabilities: tuple[str, ...] | list[str] | None = None,
) -> dict:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    query_text = _normalize_query(query)
    query_keywords = extract_keywords(query_text)
    tier_request = _normalize_tier(tier)
    explain_query = (
        sanitize_text(query_text, project_root=project_root, app_path=app_path, secret_values=secret_values)
        if explain
        else query_text
    )
    explain_builder = RetrievalExplainBuilder(explain_query, tier_request, limit) if explain else None
    entries = _read_index_entries(state)
    status_map = _read_ingestion_status(state)
    embedding_plan = build_embedding_plan(
        entries,
        query_text=query_text,
        config=config,
        project_root=project_root,
        app_path=app_path,
        capabilities=capabilities,
    )
    ordering = ordering_label(embedding_plan.enabled)
    pass_entries: list[tuple[dict, int]] = []
    warn_entries: list[tuple[dict, int]] = []
    blocked = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        upload_id = str(entry.get("upload_id") or "")
        quality = _quality_for_upload(status_map, upload_id)
        text = entry.get("text")
        text_value = text if isinstance(text, str) else ""
        if quality == "block":
            blocked += 1
            if explain_builder is not None:
                overlap = _safe_keyword_overlap(
                    entry,
                    text_value,
                    query_keywords,
                    project_root=project_root,
                    app_path=app_path,
                    secret_values=secret_values,
                )
                candidate = _candidate_fields(entry, upload_id=upload_id, keyword_overlap=overlap)
                vector_score = embedding_plan.score_for(candidate["chunk_id"])
                explain_builder.add_blocked(
                    chunk_id=candidate["chunk_id"],
                    ingestion_phase=candidate["ingestion_phase"],
                    keyword_overlap=candidate["keyword_overlap"],
                    page_number=candidate["page_number"],
                    chunk_index=candidate["chunk_index"],
                    order_index=index,
                    vector_score=vector_score,
                )
            continue
        chunk_id = entry.get("chunk_id")
        chunk_index = _require_chunk_index(entry)
        chunk_id_value = str(chunk_id or f"{upload_id}:{chunk_index}")
        embedding_score = embedding_plan.score_for(chunk_id_value)
        embedding_candidate = embedding_plan.is_candidate(chunk_id_value)
        clean_text = sanitize_text(
            text_value,
            project_root=project_root,
            app_path=app_path,
            secret_values=secret_values,
        )
        document_id = _require_string_field(entry, "document_id")
        source_name = _require_string_field(entry, "source_name")
        page_number = _require_page_number(entry)
        ingestion_phase = _require_ingestion_phase(entry)
        keywords, keyword_source = _require_keywords(entry, clean_text)
        matches = keyword_matches(query_keywords, keywords)
        overlap = len(matches)
        if query_text:
            if query_keywords:
                if overlap == 0 and query_text not in text_value.lower() and not embedding_candidate:
                    if explain_builder is not None:
                        explain_builder.add_filtered(
                            chunk_id=chunk_id_value,
                            ingestion_phase=ingestion_phase,
                            keyword_overlap=overlap,
                            page_number=page_number,
                            chunk_index=chunk_index,
                            order_index=index,
                            quality=quality,
                            vector_score=embedding_score,
                        )
                    continue
            elif query_text not in text_value.lower() and not embedding_candidate:
                if explain_builder is not None:
                    explain_builder.add_filtered(
                        chunk_id=chunk_id_value,
                        ingestion_phase=ingestion_phase,
                        keyword_overlap=overlap,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        order_index=index,
                        quality=quality,
                        vector_score=embedding_score,
                    )
                continue
        result = {
            "upload_id": upload_id,
            "chunk_id": chunk_id_value,
            "quality": quality,
            "low_quality": quality == "warn",
            "text": clean_text,
            "document_id": document_id,
            "source_name": source_name,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "ingestion_phase": ingestion_phase,
            "keywords": keywords,
            "keyword_source": keyword_source,
            "keyword_matches": matches,
            "keyword_overlap": overlap,
        }
        if quality == "pass":
            pass_entries.append((result, index))
        else:
            warn_entries.append((result, index))
        if explain_builder is not None:
            candidate_rank_key = rank_key(result, index, tie_break_chunk_id=embedding_plan.enabled)
            explain_builder.add_candidate(
                chunk_id=result["chunk_id"],
                ingestion_phase=ingestion_phase,
                keyword_overlap=overlap,
                page_number=page_number,
                chunk_index=chunk_index,
                order_index=index,
                quality=quality,
                rank_key=candidate_rank_key,
                vector_score=embedding_score,
            )
    pass_selected, pass_selection = select_tier(pass_entries, tier_request, tie_break_chunk_id=embedding_plan.enabled)
    warn_selected, warn_selection = select_tier(warn_entries, tier_request, tie_break_chunk_id=embedding_plan.enabled)
    decision = policy_decision or _resolve_warn_policy(
        project_root=project_root,
        app_path=app_path,
        identity=identity,
        policy_decl=policy_decl,
    )
    warn_allowed = bool(decision.allowed)
    excluded_warn = 0
    if pass_selected:
        results = pass_selected
        included_warn = False
        preferred = "pass"
        tier_selection = pass_selection
        explain_quality = "pass"
        explain_selection = pass_selected
    elif warn_allowed:
        results = warn_selected
        included_warn = bool(warn_selected)
        preferred = "warn" if warn_selected else "pass"
        tier_selection = warn_selection
        explain_quality = "warn"
        explain_selection = warn_selected
    else:
        results = []
        included_warn = False
        preferred = "pass"
        excluded_warn = len(warn_selected)
        tier_selection = pass_selection if pass_entries else warn_selection
        explain_quality = "pass"
        explain_selection = pass_selected
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise Namel3ssError(_limit_message())
        results = results[:limit]
    response = {
        "query": query_text,
        "query_keywords": query_keywords,
        "preferred_quality": preferred,
        "included_warn": included_warn,
        "excluded_blocked": blocked,
        "excluded_warn": excluded_warn,
        "warn_allowed": warn_allowed,
        "warn_policy": _policy_summary(decision),
        "tier": _tier_summary(tier_request, tier_selection),
        "results": results,
    }
    if explain_builder is not None:
        response["explain"] = explain_builder.finalize(
            selected=results,
            selection_candidates=explain_selection,
            chosen_quality=explain_quality,
            warn_allowed=warn_allowed,
            embedding=embedding_plan.explain_payload(),
            ordering=ordering,
        )
    return response


def _normalize_query(query: str | None) -> str:
    if query is None:
        return ""
    if not isinstance(query, str):
        raise Namel3ssError(_query_message())
    return query.strip().lower()


def _normalize_tier(value: str | None) -> str:
    if value is None:
        return "auto"
    if not isinstance(value, str):
        raise Namel3ssError(_tier_message(str(value)))
    text = value.strip().lower()
    if not text:
        return "auto"
    if text in {"auto", "quick-only", "deep-only"}:
        return text
    raise Namel3ssError(_tier_message(text))


def _read_index_entries(state: dict) -> list[dict]:
    index = state.get("index")
    if not isinstance(index, dict):
        return []
    entries = index.get("chunks")
    if not isinstance(entries, list):
        return []
    return entries


def _read_ingestion_status(state: dict) -> dict:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return {}
    return ingestion


def _quality_for_upload(status_map: dict, upload_id: str) -> str:
    if not upload_id:
        return "block"
    report = status_map.get(upload_id)
    if not isinstance(report, dict):
        return "block"
    status = report.get("status")
    if status in {"pass", "warn", "block"}:
        return status
    return "block"


def _resolve_warn_policy(
    *,
    project_root: str | None,
    app_path: str | None,
    identity: dict | None,
    policy_decl: object | None,
) -> PolicyDecision:
    policy = load_ingestion_policy(project_root, app_path, policy_decl=policy_decl)
    return evaluate_ingestion_policy(policy, ACTION_RETRIEVAL_INCLUDE_WARN, identity)


def _policy_summary(decision: PolicyDecision) -> dict:
    return {
        "action": ACTION_RETRIEVAL_INCLUDE_WARN,
        "decision": "allowed" if decision.allowed else "denied",
        "reason": decision.reason,
    }


def _tier_summary(tier_request: str, selection: dict) -> dict:
    summary = {"requested": tier_request}
    if isinstance(selection, dict):
        summary.update(selection)
    return summary


def _state_type_message() -> str:
    return build_guidance_message(
        what="State must be an object.",
        why="Retrieval reads indexed chunks and ingestion reports from state.",
        fix="Ensure state is a JSON object.",
        example='{"index":{"chunks":[]},"ingestion":{}}',
    )


def _query_message() -> str:
    return build_guidance_message(
        what="Retrieval query must be text.",
        why="Retrieval expects a text query or an empty string.",
        fix="Provide a string query.",
        example='{"query":"invoice"}',
    )


def _limit_message() -> str:
    return build_guidance_message(
        what="Retrieval limit must be a non-negative integer.",
        why="Retrieval limits the number of returned chunks deterministically.",
        fix="Provide a number like 10.",
        example='{"limit":10}',
    )


def _tier_message(value: str) -> str:
    return build_guidance_message(
        what=f"Unsupported retrieval tier '{value}'.",
        why="Retrieval tiers must be auto, quick-only, or deep-only.",
        fix="Use auto, quick-only, or deep-only.",
        example='{"tier":"auto"}',
    )


def _missing_field_message(field: str) -> str:
    return build_guidance_message(
        what=f"Retrieval chunks are missing {field}.",
        why="Retrieval requires page-level provenance, phase metadata, and keywords for deterministic ranking.",
        fix="Re-run ingestion to rebuild the index with provenance.",
        example='{"query":"invoice"}',
    )


def _invalid_phase_message(value: str) -> str:
    return build_guidance_message(
        what=f"Retrieval chunk has invalid ingestion_phase '{value}'.",
        why="Ingestion phases must be quick or deep.",
        fix="Re-run ingestion to rebuild the index with phase metadata.",
        example='{"query":"invoice"}',
    )


def _invalid_keywords_message() -> str:
    return build_guidance_message(
        what="Retrieval chunk has invalid keywords.",
        why="Keywords must be a list of non-empty text values.",
        fix="Re-run ingestion to rebuild the index with keywords.",
        example='{"query":"invoice"}',
    )


def _require_string_field(entry: dict, field: str) -> str:
    value = entry.get(field)
    if isinstance(value, str) and value.strip():
        return value
    raise Namel3ssError(_missing_field_message(field))


def _require_page_number(entry: dict) -> int:
    value = coerce_int(entry.get("page_number"))
    if value is not None and value > 0:
        return value
    raise Namel3ssError(_missing_field_message("page_number"))


def _require_chunk_index(entry: dict) -> int:
    value = coerce_int(entry.get("chunk_index"))
    if value is not None and value >= 0:
        return value
    raise Namel3ssError(_missing_field_message("chunk_index"))


def _require_ingestion_phase(entry: dict) -> str:
    value = entry.get("ingestion_phase")
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(_missing_field_message("ingestion_phase"))
    phase = value.strip().lower()
    if phase in {"quick", "deep"}:
        return phase
    raise Namel3ssError(_invalid_phase_message(phase))


def _require_keywords(entry: dict, text_value: str) -> tuple[list[str], str]:
    if "keywords" not in entry:
        if isinstance(text_value, str) and text_value:
            return extract_keywords(text_value), "derived"
        raise Namel3ssError(_missing_field_message("keywords"))
    normalized = normalize_keywords(entry.get("keywords"))
    if normalized is None:
        raise Namel3ssError(_invalid_keywords_message())
    return normalized, "stored"


def _safe_keyword_overlap(
    entry: dict,
    text_value: str,
    query_keywords: list[str],
    *,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None,
) -> int:
    if not query_keywords:
        return 0
    keywords = normalize_keywords(entry.get("keywords"))
    if keywords is None:
        cleaned = sanitize_text(text_value, project_root=project_root, app_path=app_path, secret_values=secret_values)
        keywords = extract_keywords(cleaned) if cleaned else []
    matches = keyword_matches(query_keywords, keywords)
    return len(matches)


def _candidate_fields(entry: dict, *, upload_id: str, keyword_overlap: int) -> dict:
    chunk_index = coerce_int(entry.get("chunk_index")) or 0
    chunk_id = entry.get("chunk_id")
    return {
        "chunk_id": str(chunk_id or f"{upload_id}:{chunk_index}"),
        "ingestion_phase": str(entry.get("ingestion_phase") or ""),
        "keyword_overlap": int(keyword_overlap),
        "page_number": coerce_int(entry.get("page_number")) or 0,
        "chunk_index": chunk_index,
    }


__all__ = ["run_retrieval"]
