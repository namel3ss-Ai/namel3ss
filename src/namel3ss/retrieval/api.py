from __future__ import annotations

from decimal import Decimal

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


def run_retrieval(
    *,
    query: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    limit: int | None = None,
    tier: str | None = None,
    secret_values: list[str] | None = None,
    identity: dict | None = None,
    policy_decision: PolicyDecision | None = None,
    policy_decl: object | None = None,
) -> dict:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    query_text = _normalize_query(query)
    query_keywords = extract_keywords(query_text)
    tier_request = _normalize_tier(tier)
    entries = _read_index_entries(state)
    status_map = _read_ingestion_status(state)
    pass_entries: list[tuple[dict, int]] = []
    warn_entries: list[tuple[dict, int]] = []
    blocked = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        text = entry.get("text")
        text_value = text if isinstance(text, str) else ""
        upload_id = str(entry.get("upload_id") or "")
        quality = _quality_for_upload(status_map, upload_id)
        if quality == "block":
            blocked += 1
            continue
        chunk_id = entry.get("chunk_id")
        chunk_index = _require_chunk_index(entry)
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
                if overlap == 0 and query_text not in text_value.lower():
                    continue
            elif query_text not in text_value.lower():
                continue
        result = {
            "upload_id": upload_id,
            "chunk_id": str(chunk_id or f"{upload_id}:{chunk_index}"),
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
    pass_selected, pass_selection = _select_tier(pass_entries, tier_request)
    warn_selected, warn_selection = _select_tier(warn_entries, tier_request)
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
    elif warn_allowed:
        results = warn_selected
        included_warn = bool(warn_selected)
        preferred = "warn" if warn_selected else "pass"
        tier_selection = warn_selection
    else:
        results = []
        included_warn = False
        preferred = "pass"
        excluded_warn = len(warn_selected)
        tier_selection = pass_selection if pass_entries else warn_selection
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise Namel3ssError(_limit_message())
        results = results[:limit]
    return {
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
    value = _coerce_int(entry.get("page_number"))
    if value is not None and value > 0:
        return value
    raise Namel3ssError(_missing_field_message("page_number"))


def _require_chunk_index(entry: dict) -> int:
    value = _coerce_int(entry.get("chunk_index"))
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


def _select_tier(
    entries: list[tuple[dict, int]],
    tier_request: str,
) -> tuple[list[dict], dict]:
    available = _phase_counts(entries)
    phases = [phase for phase in ("deep", "quick") if available.get(phase)]
    ordered = _order_entries(entries)
    selection: dict = {"available": phases, "counts": available}
    if tier_request == "quick-only":
        selection.update({"selected": "quick", "reason": "tier_requested"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "quick"], selection
    if tier_request == "deep-only":
        selection.update({"selected": "deep", "reason": "tier_requested"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "deep"], selection
    if available.get("deep") and available.get("quick"):
        selection.update({"selected": "deep_then_quick", "reason": "deep_and_quick_available"})
        return ordered, selection
    if available.get("deep"):
        selection.update({"selected": "deep", "reason": "deep_available"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "deep"], selection
    if available.get("quick"):
        selection.update({"selected": "quick", "reason": "quick_only_available"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "quick"], selection
    selection.update({"selected": "none", "reason": "no_chunks"})
    return [], selection


def _order_entries(entries: list[tuple[dict, int]]) -> list[dict]:
    ordered = sorted(entries, key=_entry_sort_key)
    return [entry for entry, _ in ordered]


def _entry_sort_key(item: tuple[dict, int]) -> tuple[int, int, int, int, int]:
    entry, order = item
    phase = entry.get("ingestion_phase")
    phase_rank = 0 if phase == "deep" else 1
    overlap = int(entry.get("keyword_overlap") or 0)
    page_number = _coerce_int(entry.get("page_number")) or 0
    chunk_index = _coerce_int(entry.get("chunk_index")) or 0
    return (phase_rank, -overlap, page_number, chunk_index, order)


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
    return None


def _phase_counts(entries: list[tuple[dict, int]]) -> dict:
    counts = {"deep": 0, "quick": 0}
    for entry, _ in entries:
        phase = entry.get("ingestion_phase")
        if phase in counts:
            counts[phase] += 1
    return counts


__all__ = ["run_retrieval"]
