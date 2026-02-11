from __future__ import annotations

from typing import Any

from namel3ss.retrieval.tuning import (
    DEFAULT_SEMANTIC_WEIGHT,
    RETRIEVAL_TUNING_FLOW_TO_FIELD,
    RETRIEVAL_TUNING_FLOWS,
)
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
    controls = _build_retrieval_controls(manifest, normalized.get("retrieval_tuning"))
    normalized["retrieval_controls"] = controls
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
        "retrieval_tuning": payload["retrieval_tuning"],
        "retrieval_controls": payload["retrieval_controls"],
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
    tuning = _normalize_tuning(value.get("retrieval_tuning"))
    return {
        "query": query,
        "retrieval_plan": plan,
        "retrieval_trace": trace,
        "trust_score_details": trust,
        "retrieval_tuning": tuning,
    }


def _normalize_tuning(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "semantic_k": None,
            "lexical_k": None,
            "final_top_k": None,
            "semantic_weight": DEFAULT_SEMANTIC_WEIGHT,
            "explicit": False,
        }
    payload = _sanitize(value) if isinstance(value, dict) else {}
    return {
        "semantic_k": _as_nullable_int(payload.get("semantic_k")),
        "lexical_k": _as_nullable_int(payload.get("lexical_k")),
        "final_top_k": _as_nullable_int(payload.get("final_top_k")),
        "semantic_weight": _as_score(payload.get("semantic_weight")),
        "explicit": bool(payload.get("explicit")),
    }


def _build_retrieval_controls(manifest: dict, tuning: object) -> dict[str, Any]:
    actions = manifest.get("actions") if isinstance(manifest, dict) else None
    action_map = actions if isinstance(actions, dict) else {}
    tuning_map = tuning if isinstance(tuning, dict) else {}
    controls: list[dict[str, Any]] = []
    enabled_count = 0
    for flow_name in RETRIEVAL_TUNING_FLOWS:
        action = _find_flow_action(action_map, flow_name)
        field = RETRIEVAL_TUNING_FLOW_TO_FIELD.get(flow_name)
        value = tuning_map.get(field) if isinstance(field, str) else None
        if action is None:
            controls.append(
                {
                    "flow": flow_name,
                    "action_id": "",
                    "input_field": _default_input_field(field),
                    "enabled": False,
                    "disabled_reason": f'Flow "{flow_name}" is not available in this app.',
                    "value": value if value is not None else _default_value(field),
                }
            )
            continue
        action_id = str(action.get("id") or "")
        input_field = str(action.get("input_field") or _default_input_field(field))
        action_enabled = action.get("enabled") is not False
        if action_enabled:
            enabled_count += 1
        controls.append(
            {
                "flow": flow_name,
                "action_id": action_id,
                "input_field": input_field,
                "enabled": action_enabled,
                "disabled_reason": "" if action_enabled else f'Flow "{flow_name}" is currently disabled.',
                "value": value if value is not None else _default_value(field),
            }
        )
    return {
        "enabled": enabled_count > 0,
        "disabled_reason": "" if enabled_count > 0 else "Retrieval tuning flows are not available.",
        "items": controls,
    }


def _find_flow_action(actions: dict[str, Any], flow_name: str) -> dict[str, Any] | None:
    for action_id in sorted(actions.keys()):
        action = actions.get(action_id)
        if not isinstance(action, dict):
            continue
        if action.get("type") != "call_flow":
            continue
        if action.get("flow") != flow_name:
            continue
        if not isinstance(action.get("id"), str) or not action.get("id"):
            action = dict(action)
            action["id"] = action_id
        return action
    return None


def _default_input_field(field: object) -> str:
    if field == "semantic_weight":
        return "weight"
    return "k"


def _default_value(field: object) -> object:
    if field == "semantic_weight":
        return DEFAULT_SEMANTIC_WEIGHT
    return None


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


def _as_nullable_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    rank = _as_rank(value)
    if rank < 0:
        return None
    if rank == 0 and value not in {0, 0.0}:
        return None
    return rank


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
