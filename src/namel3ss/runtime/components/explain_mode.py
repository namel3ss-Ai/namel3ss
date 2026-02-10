from __future__ import annotations

from copy import deepcopy
from typing import Mapping


class ExplainModeError(RuntimeError):
    """Raised when explain mode payloads violate policy."""


def normalize_explain_mode_state(state: Mapping[str, object] | None) -> dict[str, object]:
    source = dict(state or {})
    entries = _normalize_entries(source.get("entries"))
    visible = bool(source.get("visible", True))
    studio_only = bool(source.get("studio_only", True))
    return {
        "entries": entries,
        "visible": visible,
        "studio_only": studio_only,
    }


def build_explain_mode_payload(
    explain_state: Mapping[str, object] | None,
    *,
    component_id: str,
    studio_mode: bool,
    allow_runtime: bool = False,
) -> dict[str, object]:
    state = normalize_explain_mode_state(explain_state)
    if state["studio_only"] and not studio_mode and not allow_runtime:
        raise ExplainModeError("explain_mode is Studio-only unless allow_runtime is enabled.")
    return {
        "type": "component.explain_mode",
        "id": component_id,
        "entries": deepcopy(state["entries"]),
        "visible": state["visible"],
        "studio_only": state["studio_only"],
        "bindings": {
            "on_click": None,
            "keyboard_shortcut": None,
            "selected_item": None,
        },
    }


def _normalize_entries(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    entries: list[dict[str, object]] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            continue
        chunk_id = str(entry.get("chunk_id") or "").strip()
        if not chunk_id:
            continue
        score = float(entry.get("score")) if isinstance(entry.get("score"), (int, float)) else 0.0
        rerank = float(entry.get("rerank_score")) if isinstance(entry.get("rerank_score"), (int, float)) else 0.0
        entries.append(
            {
                "chunk_id": chunk_id,
                "source_id": str(entry.get("source_id") or ""),
                "score": score,
                "rerank_score": rerank,
                "text": str(entry.get("text") or ""),
            }
        )
    entries.sort(key=lambda item: (-item["score"], -item["rerank_score"], item["chunk_id"], item["source_id"]))
    return entries


__all__ = [
    "ExplainModeError",
    "build_explain_mode_payload",
    "normalize_explain_mode_state",
]
