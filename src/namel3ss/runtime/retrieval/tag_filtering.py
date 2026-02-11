from __future__ import annotations

from collections.abc import Mapping


def resolve_filter_tags(
    filter_tags: object,
    *,
    state: Mapping[str, object] | None,
) -> list[str]:
    explicit = normalize_filter_tags(filter_tags)
    if explicit:
        return explicit
    if isinstance(state, Mapping):
        active_docs = normalize_filter_tags(state.get("active_docs"))
        if active_docs:
            return active_docs
        retrieval = state.get("retrieval")
        if isinstance(retrieval, Mapping):
            active_scope = normalize_filter_tags(retrieval.get("active_scope"))
            if active_scope:
                return active_scope
            fallback = normalize_filter_tags(retrieval.get("filter_tags"))
            if fallback:
                return fallback
    return []


def apply_filter_tags(results: list[dict], *, filter_tags: list[str]) -> tuple[list[dict], list[str]]:
    normalized = normalize_filter_tags(filter_tags)
    if not normalized:
        copied = [dict(entry) for entry in results if isinstance(entry, dict)]
        return copied, normalized
    allowed = set(normalized)
    selected: list[dict] = []
    for entry in results:
        if not isinstance(entry, dict):
            continue
        tags = _entry_tags(entry)
        matched = sorted(tag for tag in tags if tag in allowed)
        if not matched:
            continue
        copied = dict(entry)
        copied["matched_tags"] = matched
        selected.append(copied)
    return selected, normalized


def normalize_filter_tags(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            continue
        text = entry.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return sorted(normalized)


def _entry_tags(entry: Mapping[str, object]) -> list[str]:
    for key in ("tags", "matched_tags", "scope_tags"):
        value = entry.get(key)
        if isinstance(value, list):
            normalized = normalize_filter_tags(value)
            if normalized:
                return normalized
            continue
        if isinstance(value, str):
            single = normalize_filter_tags([value])
            if single:
                return single
    document_id = entry.get("document_id")
    if isinstance(document_id, str) and document_id.strip():
        return [document_id.strip()]
    upload_id = entry.get("upload_id")
    if isinstance(upload_id, str) and upload_id.strip():
        return [upload_id.strip()]
    return []


__all__ = ["apply_filter_tags", "normalize_filter_tags", "resolve_filter_tags"]
