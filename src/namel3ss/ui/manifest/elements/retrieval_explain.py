from __future__ import annotations

from typing import Any

from namel3ss.ui.manifest.canonical import _element_id


def inject_retrieval_explain_elements(manifest: dict, retrieval_report: dict[str, Any] | None) -> dict:
    if not isinstance(manifest, dict):
        return manifest
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        return manifest
    normalized = _normalize_retrieval_report(retrieval_report)
    if normalized is None:
        return manifest
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_slug = str(page.get("slug") or page.get("name") or "page")
        page_name = str(page.get("name") or page_slug)
        element = _retrieval_explain_element(page_name=page_name, page_slug=page_slug, payload=normalized)
        if isinstance(page.get("layout"), dict):
            layout = page["layout"]
            main_items = layout.get("main")
            if not isinstance(main_items, list):
                main_items = []
            layout["main"] = _inject_element(main_items, element)
            continue
        elements = page.get("elements")
        if not isinstance(elements, list):
            elements = []
            page["elements"] = elements
        page["elements"] = _inject_element(elements, element)
    manifest["retrieval_explain"] = normalized
    return manifest


def _inject_element(items: list[dict], element: dict[str, Any]) -> list[dict]:
    filtered = [entry for entry in items if not _is_retrieval_explain(entry)]
    if filtered and isinstance(filtered[0], dict) and filtered[0].get("type") == "runtime_error":
        return [filtered[0], element, *filtered[1:]]
    return [element, *filtered]


def _retrieval_explain_element(*, page_name: str, page_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "retrieval_explain",
        "element_id": _element_id(page_slug, "retrieval_explain", [0]),
        "page": page_name,
        "page_slug": page_slug,
        "index": 0,
        "line": 0,
        "column": 0,
        "source": "result.retrieval",
        "query": payload["query"],
        "retrieval_plan": payload["retrieval_plan"],
        "retrieval_trace": payload["retrieval_trace"],
        "trust_score_details": payload["trust_score_details"],
    }


def _normalize_retrieval_report(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    trace = _normalize_trace(value.get("retrieval_trace"))
    if not trace:
        return None
    query = str(value.get("query") or "")
    plan = _sanitize(value.get("retrieval_plan")) if isinstance(value.get("retrieval_plan"), dict) else {}
    trust = _sanitize(value.get("trust_score_details")) if isinstance(value.get("trust_score_details"), dict) else {}
    return {
        "query": query,
        "retrieval_plan": plan,
        "retrieval_trace": trace,
        "trust_score_details": trust,
    }


def _normalize_trace(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in value:
        item = _normalize_trace_entry(entry)
        if item is None:
            continue
        key = f"{item['rank']}::{item['chunk_id']}"
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized


def _normalize_trace_entry(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    chunk_id = _as_text(value.get("chunk_id"))
    document_id = _as_text(value.get("document_id"))
    reason = _as_text(value.get("reason"))
    rank = _as_rank(value.get("rank"))
    if not chunk_id or not reason or rank <= 0:
        return None
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "page_number": _as_page_number(value.get("page_number")),
        "score": _as_score(value.get("score")),
        "rank": rank,
        "reason": reason,
        "upload_id": _as_text(value.get("upload_id")),
        "ingestion_phase": _as_text(value.get("ingestion_phase")),
        "quality": _as_text(value.get("quality")),
    }


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _as_rank(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return 0


def _as_page_number(value: object) -> int:
    rank = _as_rank(value)
    if rank <= 0:
        return 0
    return rank


def _as_score(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
        if number < 0.0:
            return 0.0
        if number > 1.0:
            return 1.0
        return round(number, 4)
    return 0.0


def _is_retrieval_explain(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("type") == "retrieval_explain"


__all__ = ["inject_retrieval_explain_elements"]
