from __future__ import annotations

import math

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.elements.base import _base_element
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode, add_warning


def build_citation_chips_item(
    item: ir.CitationChipsItem,
    *,
    page_name: str,
    page_slug: str,
    path: list[int],
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> tuple[dict, dict]:
    del mode
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "citation_chips", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    source = _state_path_label(item.source)
    value = _resolve_state_path(item.source, state_ctx, default=[], register_default=True)
    citations = _normalize_citations(value, line=item.line, column=item.column)
    if not citations:
        add_warning(
            warnings,
            code="rag.empty_citations_component",
            message="Citations component has no entries to render.",
            fix="Bind citations to a non-empty list or remove the component.",
            path=f"page.{page_slug}.element.{index}",
            line=item.line,
            column=item.column,
            category="rag",
        )
    element = {
        "type": "citation_chips",
        "source": source,
        "citations": citations,
        **base,
    }
    return _attach_origin(element, item), {}


def build_source_preview_item(
    item: ir.SourcePreviewItem,
    *,
    page_name: str,
    page_slug: str,
    path: list[int],
    state_ctx: StateContext,
) -> tuple[dict, dict]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "source_preview", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    resolved = _resolve_source_reference(item.source, state_ctx, line=item.line, column=item.column)
    element = {
        "type": "source_preview",
        **resolved,
        **base,
    }
    return _attach_origin(element, item), {}


def build_trust_indicator_item(
    item: ir.TrustIndicatorItem,
    *,
    page_name: str,
    page_slug: str,
    path: list[int],
    state_ctx: StateContext,
) -> tuple[dict, dict]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "trust_indicator", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    source = _state_path_label(item.source)
    value = _resolve_state_path(item.source, state_ctx, default=False, register_default=True)
    normalized_value = _normalize_trust_value(value, line=item.line, column=item.column)
    element = {
        "type": "trust_indicator",
        "source": source,
        "value": normalized_value,
        **base,
    }
    return _attach_origin(element, item), {}


def build_scope_selector_item(
    item: ir.ScopeSelectorItem,
    *,
    page_name: str,
    page_slug: str,
    path: list[int],
    state_ctx: StateContext,
) -> tuple[dict, dict]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "scope_selector", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    options_source = _state_path_label(item.options_source)
    active_source = _state_path_label(item.active)
    options_value = _resolve_state_path(item.options_source, state_ctx, default=[], register_default=True)
    active_value = _resolve_state_path(item.active, state_ctx, default=[], register_default=True)
    options = _normalize_scope_options(options_value, line=item.line, column=item.column)
    active = _normalize_active_scope_values(active_value, line=item.line, column=item.column)
    action_id = f"{element_id}.select"
    element = {
        "type": "scope_selector",
        "id": action_id,
        "action_id": action_id,
        "options_source": options_source,
        "active_source": active_source,
        "options": options,
        "active": active,
        **base,
    }
    action = {
        "id": action_id,
        "type": "scope_select",
        "target_state": active_source,
    }
    return _attach_origin(element, item), {action_id: action}


def _resolve_source_reference(
    source: ir.StatePath | ir.Literal,
    state_ctx: StateContext,
    *,
    line: int | None,
    column: int | None,
) -> dict:
    if isinstance(source, ir.StatePath):
        source_path = _state_path_label(source)
        value = _resolve_state_path(source, state_ctx, default=None, register_default=True)
        resolved = _normalize_source_payload(value, line=line, column=column)
        resolved["source"] = source_path
        return resolved
    if isinstance(source, ir.Literal):
        if not isinstance(source.value, str):
            raise Namel3ssError("Source previews require a text source id or url.", line=line, column=column)
        return _normalize_source_payload(source.value, line=line, column=column)
    raise Namel3ssError("Source previews require state.<path> or a text source id.", line=line, column=column)


def _normalize_source_payload(value: object, *, line: int | None, column: int | None) -> dict:
    if value is None:
        return {"error": "Source preview is unavailable."}
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {"error": "Source preview is unavailable."}
        if text.startswith("http://") or text.startswith("https://"):
            return {"url": text}
        return {"source_id": text}
    if not isinstance(value, dict):
        raise Namel3ssError("Source preview values must be objects or text.", line=line, column=column)
    normalized = _normalize_citation_entry(value, idx=0, line=line, column=column, include_index=False)
    payload = {key: val for key, val in normalized.items() if key != "index"}
    if "source_id" not in payload and "url" not in payload:
        payload["error"] = "Source preview is unavailable."
    return payload


def _normalize_citations(value: object, *, line: int | None, column: int | None) -> list[dict]:
    if not isinstance(value, list):
        raise Namel3ssError("Citations must be a list", line=line, column=column)
    return [
        _normalize_citation_entry(entry, idx=idx, line=line, column=column, include_index=True)
        for idx, entry in enumerate(value)
    ]


def _normalize_citation_entry(
    entry: object,
    *,
    idx: int,
    line: int | None,
    column: int | None,
    include_index: bool,
) -> dict:
    if not isinstance(entry, dict):
        raise Namel3ssError(f"Citation {idx} must be an object", line=line, column=column)
    title = entry.get("title")
    if not isinstance(title, str):
        raise Namel3ssError(f"Citation {idx} title must be text", line=line, column=column)
    url = entry.get("url")
    source_id = entry.get("source_id")
    if url is None and source_id is None:
        raise Namel3ssError(f"Citation {idx} must include url or source_id", line=line, column=column)
    if url is not None and not isinstance(url, str):
        raise Namel3ssError(f"Citation {idx} url must be text", line=line, column=column)
    if source_id is not None and not isinstance(source_id, str):
        raise Namel3ssError(f"Citation {idx} source_id must be text", line=line, column=column)
    snippet = entry.get("snippet")
    if snippet is not None and not isinstance(snippet, str):
        raise Namel3ssError(f"Citation {idx} snippet must be text", line=line, column=column)
    result = {"title": title}
    if include_index:
        result["index"] = idx + 1
    if url:
        result["url"] = url
    if source_id:
        result["source_id"] = source_id
    if snippet:
        result["snippet"] = snippet
    for passthrough in ("chunk_id", "document_id", "page", "page_number"):
        value = entry.get(passthrough)
        if isinstance(value, (str, int, float)):
            result[passthrough] = value
    return result


def _normalize_trust_value(value: object, *, line: int | None, column: int | None) -> bool | float:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if not math.isfinite(number) or number < 0 or number > 1:
            raise Namel3ssError("Trust indicators expect a score between 0 and 1.", line=line, column=column)
        return round(number, 4)
    raise Namel3ssError("Trust indicators expect a boolean or score between 0 and 1.", line=line, column=column)


def _normalize_scope_options(value: object, *, line: int | None, column: int | None) -> list[dict]:
    if not isinstance(value, list):
        raise Namel3ssError("Scope selector options must be a list.", line=line, column=column)
    options: list[dict] = []
    for idx, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise Namel3ssError(f"Scope selector option {idx} must be an object.", line=line, column=column)
        option_id = entry.get("id")
        name = entry.get("name")
        if not isinstance(option_id, str) or not option_id.strip():
            raise Namel3ssError(f"Scope selector option {idx} id must be text.", line=line, column=column)
        if not isinstance(name, str) or not name.strip():
            raise Namel3ssError(f"Scope selector option {idx} name must be text.", line=line, column=column)
        options.append({"id": option_id, "name": name})
    return options


def _normalize_active_scope_values(value: object, *, line: int | None, column: int | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, list):
        raise Namel3ssError("Scope selector active value must be text or a list of text ids.", line=line, column=column)
    normalized: list[str] = []
    seen: set[str] = set()
    for idx, entry in enumerate(value):
        if not isinstance(entry, str):
            raise Namel3ssError(f"Scope selector active value {idx} must be text.", line=line, column=column)
        if entry in seen:
            continue
        seen.add(entry)
        normalized.append(entry)
    return normalized


def _resolve_state_path(path: ir.StatePath, state_ctx: StateContext, *, default: object, register_default: bool) -> object:
    value, _ = state_ctx.value(path.path, default=default, register_default=register_default)
    return value


def _state_path_label(path: ir.StatePath) -> str:
    return f"state.{'.'.join(path.path)}"


__all__ = [
    "build_citation_chips_item",
    "build_scope_selector_item",
    "build_source_preview_item",
    "build_trust_indicator_item",
]
