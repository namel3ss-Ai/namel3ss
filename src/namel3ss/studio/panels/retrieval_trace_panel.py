from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath

from namel3ss.ir.validation.includes_validation import DIAGNOSTICS_TRACE_WARNING_MESSAGE
from namel3ss.runtime.retrieval.trace_contract import TRACE_TIE_BREAKER
from namel3ss.runtime.retrieval.what_if_simulator import simulate_ranking_from_trace


def build_retrieval_trace_panel_payload(
    *,
    trace_payload: Mapping[str, object] | None,
    capabilities: Sequence[str] | None,
    source_map: Sequence[Mapping[str, object]] | None,
) -> dict[str, object]:
    capability_set = {str(item).strip() for item in list(capabilities or ()) if str(item).strip()}
    enabled = "diagnostics.trace" in capability_set
    normalized_source_map = _normalize_source_map(source_map)
    if not enabled:
        return {
            "studio_only": True,
            "enabled": False,
            "available": False,
            "warning": DIAGNOSTICS_TRACE_WARNING_MESSAGE,
            "trace": {},
            "what_if": {"params": {}, "final": []},
            "source_map": normalized_source_map,
        }
    trace = _normalize_trace(trace_payload)
    if not trace:
        return {
            "studio_only": True,
            "enabled": True,
            "available": False,
            "warning": "",
            "trace": {},
            "what_if": {"params": {}, "final": []},
            "source_map": normalized_source_map,
        }
    simulated = simulate_ranking_from_trace(trace, params=None)
    return {
        "studio_only": True,
        "enabled": True,
        "available": True,
        "warning": "",
        "trace": trace,
        "what_if": simulated,
        "source_map": normalized_source_map,
    }


def _normalize_trace(value: Mapping[str, object] | None) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    query = _text(value.get("query"))
    params = _normalize_params(value.get("params"))
    filter_tags = _normalize_tags(value.get("filter_tags"))
    semantic = _normalize_rows(value.get("semantic"))
    lexical = _normalize_rows(value.get("lexical"))
    final = _normalize_rows(value.get("final"))
    if not semantic and not lexical and not final:
        return {}
    return {
        "query": query,
        "params": params,
        "filter_tags": filter_tags,
        "semantic": _sort_rows(semantic),
        "lexical": _sort_rows(lexical),
        "final": _sort_rows(final),
        "tie_breaker": TRACE_TIE_BREAKER,
    }


def _normalize_params(value: object) -> dict[str, object]:
    source = value if isinstance(value, Mapping) else {}
    return {
        "semantic_weight": _score(source.get("semantic_weight")),
        "semantic_k": _optional_int(source.get("semantic_k")),
        "lexical_k": _optional_int(source.get("lexical_k")),
        "final_top_k": _optional_int(source.get("final_top_k")),
    }


def _normalize_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for row in value:
        if not isinstance(row, Mapping):
            continue
        doc_id = _text(row.get("doc_id"))
        title = _text(row.get("title"))
        if not doc_id:
            continue
        rows.append(
            {
                "doc_id": doc_id,
                "title": title or doc_id,
                "semantic_score": _score(row.get("semantic_score")),
                "lexical_score": _score(row.get("lexical_score")),
                "final_score": _score(row.get("final_score")),
                "matched_tags": _normalize_tags(row.get("matched_tags")),
            }
        )
    return rows


def _sort_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    ordered = [dict(row) for row in rows if isinstance(row, Mapping)]
    ordered.sort(
        key=lambda row: (
            -_score(row.get("final_score")),
            -_score(row.get("semantic_score")),
            -_score(row.get("lexical_score")),
            _text(row.get("doc_id")),
        )
    )
    return ordered


def _normalize_source_map(value: Sequence[Mapping[str, object]] | None) -> list[dict[str, object]]:
    if not isinstance(value, Sequence):
        return []
    rows: list[dict[str, object]] = []
    for entry in value:
        if not isinstance(entry, Mapping):
            continue
        decl_id = _text(entry.get("decl_id"))
        file_value = _normalize_relative_path(entry.get("file"))
        if not decl_id or not file_value:
            continue
        rows.append(
            {
                "decl_id": decl_id,
                "file": file_value,
                "line": _line(entry.get("line")),
                "col": _line(entry.get("col")),
            }
        )
    rows.sort(key=lambda item: (str(item.get("decl_id") or ""), str(item.get("file") or "")))
    return rows


def _normalize_relative_path(value: object) -> str:
    text = _text(value).replace("\\", "/")
    if not text:
        return ""
    path = PurePosixPath(text)
    normalized = path.as_posix()
    if normalized.startswith("/"):
        return ""
    if ":" in normalized.split("/")[0]:
        return ""
    if ".." in path.parts:
        return ""
    return normalized


def _normalize_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    ordered: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return sorted(ordered)


def _line(value: object) -> int:
    if isinstance(value, bool):
        return 1
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        return int(value)
    return 1


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _score(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if not isinstance(value, (int, float)):
        return 0.0
    number = float(value)
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return round(number, 4)


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = ["build_retrieval_trace_panel_payload"]
