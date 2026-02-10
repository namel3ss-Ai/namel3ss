from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping


class CitationPanelError(RuntimeError):
    """Raised when citation panel data is invalid."""


def normalize_citation_state(state: Mapping[str, object] | None) -> dict[str, object]:
    source = dict(state or {})
    citations = _normalize_citations(source.get("citations"))
    selected_id = source.get("selected_id")
    return {
        "citations": citations,
        "selected_id": str(selected_id) if isinstance(selected_id, str) and selected_id else None,
    }


def select_citation(citation_state: Mapping[str, object] | None, citation_id: str) -> dict[str, object]:
    state = normalize_citation_state(citation_state)
    selected = citation_id.strip()
    if not selected:
        raise CitationPanelError("citation_id is required.")
    if selected not in {entry["id"] for entry in state["citations"]}:
        raise CitationPanelError(f'Unknown citation "{selected}".')
    state["selected_id"] = selected
    return state


def merge_citations(citation_state: Mapping[str, object] | None, updates: Iterable[Mapping[str, object]]) -> dict[str, object]:
    state = normalize_citation_state(citation_state)
    index: dict[str, dict[str, object]] = {entry["id"]: deepcopy(entry) for entry in state["citations"]}
    for update in updates:
        if not isinstance(update, Mapping):
            continue
        citation_id = str(update.get("id") or "").strip()
        if not citation_id:
            continue
        current = index.get(citation_id, {"id": citation_id, "title": citation_id, "snippet": "", "page": None, "source_id": None})
        title = update.get("title")
        snippet = update.get("snippet")
        page = update.get("page")
        source_id = update.get("source_id")
        if isinstance(title, str) and title.strip():
            current["title"] = title
        if isinstance(snippet, str):
            current["snippet"] = snippet
        current["page"] = int(page) if isinstance(page, int) else current.get("page")
        current["source_id"] = str(source_id) if isinstance(source_id, str) and source_id else current.get("source_id")
        index[citation_id] = current
    state["citations"] = _normalize_citations(list(index.values()))
    if state["selected_id"] and state["selected_id"] not in index:
        state["selected_id"] = None
    return state


def build_citation_panel_payload(
    citation_state: Mapping[str, object] | None,
    *,
    component_id: str,
    click_action_id: str | None = None,
) -> dict[str, object]:
    state = normalize_citation_state(citation_state)
    return {
        "type": "component.citation_panel",
        "id": component_id,
        "citations": deepcopy(state["citations"]),
        "selected_id": state["selected_id"],
        "bindings": {
            "on_click": click_action_id,
            "keyboard_shortcut": None,
            "selected_item": None,
        },
    }


def _normalize_citations(raw: object) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, Mapping):
                values.append(dict(entry))
    elif isinstance(raw, Mapping):
        for key, value in sorted(raw.items(), key=lambda item: str(item[0])):
            if isinstance(value, Mapping):
                values.append({"id": str(key), **dict(value)})

    normalized: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(values, start=1):
        citation_id = str(entry.get("id") or f"citation.{index}").strip()
        if not citation_id:
            citation_id = f"citation.{index}"
        if citation_id in seen_ids:
            raise CitationPanelError(f'Duplicate citation id "{citation_id}".')
        seen_ids.add(citation_id)
        title = str(entry.get("title") or citation_id)
        snippet = str(entry.get("snippet") or "")
        page = entry.get("page")
        source_id = entry.get("source_id")
        normalized.append(
            {
                "id": citation_id,
                "index": index,
                "title": title,
                "snippet": snippet,
                "page": int(page) if isinstance(page, int) else None,
                "source_id": str(source_id) if isinstance(source_id, str) and source_id else None,
            }
        )
    normalized.sort(key=lambda item: (item["index"], item["id"]))
    return normalized


__all__ = [
    "CitationPanelError",
    "build_citation_panel_payload",
    "merge_citations",
    "normalize_citation_state",
    "select_citation",
]
