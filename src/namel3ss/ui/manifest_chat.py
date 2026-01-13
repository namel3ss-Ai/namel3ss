from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

_ALLOWED_ROLES = {"user", "assistant", "system", "tool"}


def _build_chat_messages(
    item: ir.ChatMessagesItem,
    *,
    element_id: str,
    page_name: str,
    page_slug: str,
    index: int,
    state_ctx: StateContext,
    mode: ValidationMode,
) -> dict:
    source = _state_path_label(item.source)
    value = _resolve_state_path(item.source, state_ctx, default=[], register_default=True)
    messages = _require_list(value, "messages", item.line, item.column)
    _validate_messages(messages, item.line, item.column)
    return {
        "type": "messages",
        "source": source,
        "messages": messages,
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }


def _build_chat_composer(
    item: ir.ChatComposerItem,
    *,
    element_id: str,
    page_name: str,
    page_slug: str,
    index: int,
) -> tuple[dict, dict]:
    action_id = f"{element_id}.composer"
    element = {
        "type": "composer",
        "flow": item.flow_name,
        "id": action_id,
        "action_id": action_id,
        "action": {"type": "call_flow", "flow": item.flow_name},
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }
    return element, {action_id: {"id": action_id, "type": "call_flow", "flow": item.flow_name}}


def _build_chat_thinking(
    item: ir.ChatThinkingItem,
    *,
    element_id: str,
    page_name: str,
    page_slug: str,
    index: int,
    state_ctx: StateContext,
) -> dict:
    when = _state_path_label(item.when)
    value = _resolve_state_path(item.when, state_ctx, default=False, register_default=True)
    if not isinstance(value, bool):
        raise Namel3ssError("Thinking expects a boolean state value", line=item.line, column=item.column)
    return {
        "type": "thinking",
        "when": when,
        "active": value,
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }


def _build_chat_citations(
    item: ir.ChatCitationsItem,
    *,
    element_id: str,
    page_name: str,
    page_slug: str,
    index: int,
    state_ctx: StateContext,
) -> dict:
    source = _state_path_label(item.source)
    value = _resolve_state_path(item.source, state_ctx, default=[], register_default=True)
    citations = _require_list(value, "citations", item.line, item.column)
    _validate_citations(citations, item.line, item.column)
    return {
        "type": "citations",
        "source": source,
        "citations": citations,
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }


def _build_chat_memory(
    item: ir.ChatMemoryItem,
    *,
    element_id: str,
    page_name: str,
    page_slug: str,
    index: int,
    state_ctx: StateContext,
) -> dict:
    source = _state_path_label(item.source)
    value = _resolve_state_path(item.source, state_ctx, default=[], register_default=True)
    items = _require_list(value, "memory", item.line, item.column)
    _validate_memory(items, item.line, item.column)
    element = {
        "type": "memory",
        "source": source,
        "items": items,
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }
    if item.lane:
        element["lane"] = item.lane
    return element


def _chat_item_kind(item: ir.PageItem) -> str | None:
    if isinstance(item, ir.ChatMessagesItem):
        return "messages"
    if isinstance(item, ir.ChatComposerItem):
        return "composer"
    if isinstance(item, ir.ChatThinkingItem):
        return "thinking"
    if isinstance(item, ir.ChatCitationsItem):
        return "citations"
    if isinstance(item, ir.ChatMemoryItem):
        return "memory"
    return None


def _chat_item_to_manifest(
    item: ir.PageItem,
    *,
    element_id: str,
    page_name: str,
    page_slug: str,
    index: int,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None = None,
) -> tuple[dict, dict] | None:
    if isinstance(item, ir.ChatMessagesItem):
        return (
            _build_chat_messages(
                item,
                element_id=element_id,
                page_name=page_name,
                page_slug=page_slug,
                index=index,
                state_ctx=state_ctx,
                mode=mode,
            ),
            {},
        )
    if isinstance(item, ir.ChatComposerItem):
        return _build_chat_composer(
            item,
            element_id=element_id,
            page_name=page_name,
            page_slug=page_slug,
            index=index,
        )
    if isinstance(item, ir.ChatThinkingItem):
        return (
            _build_chat_thinking(
                item,
                element_id=element_id,
                page_name=page_name,
                page_slug=page_slug,
                index=index,
                state_ctx=state_ctx,
            ),
            {},
        )
    if isinstance(item, ir.ChatCitationsItem):
        return (
            _build_chat_citations(
                item,
                element_id=element_id,
                page_name=page_name,
                page_slug=page_slug,
                index=index,
                state_ctx=state_ctx,
            ),
            {},
        )
    if isinstance(item, ir.ChatMemoryItem):
        return (
            _build_chat_memory(
                item,
                element_id=element_id,
                page_name=page_name,
                page_slug=page_slug,
                index=index,
                state_ctx=state_ctx,
            ),
            {},
        )
    return None


def _resolve_state_path(path: ir.StatePath, state_ctx: StateContext, *, default: object, register_default: bool) -> object:
    value, _ = state_ctx.value(path.path, default=default, register_default=register_default)
    return value


def _state_path_label(path: ir.StatePath) -> str:
    return f"state.{'.'.join(path.path)}"


def _require_list(value: object, label: str, line: int | None, column: int | None) -> list:
    if not isinstance(value, list):
        raise Namel3ssError(f"{label} must be a list", line=line, column=column)
    return value


def _validate_messages(messages: list, line: int | None, column: int | None) -> None:
    for idx, entry in enumerate(messages):
        if not isinstance(entry, dict):
            raise Namel3ssError(f"Message {idx} must be an object", line=line, column=column)
        role = entry.get("role")
        if not isinstance(role, str):
            raise Namel3ssError(f"Message {idx} role must be text", line=line, column=column)
        if role not in _ALLOWED_ROLES:
            raise Namel3ssError(f"Message {idx} has invalid role '{role}'", line=line, column=column)
        content = entry.get("content")
        if not isinstance(content, str):
            raise Namel3ssError(f"Message {idx} content must be text", line=line, column=column)
        created = entry.get("created")
        if created is not None and not isinstance(created, (str, int, float)):
            raise Namel3ssError(f"Message {idx} created must be text or number", line=line, column=column)
        meta = entry.get("meta")
        if meta is not None and not isinstance(meta, dict):
            raise Namel3ssError(f"Message {idx} meta must be an object", line=line, column=column)


def _validate_citations(citations: list, line: int | None, column: int | None) -> None:
    for idx, entry in enumerate(citations):
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


def _validate_memory(items: list, line: int | None, column: int | None) -> None:
    for idx, entry in enumerate(items):
        if not isinstance(entry, dict):
            raise Namel3ssError(f"Memory item {idx} must be an object", line=line, column=column)
        kind = entry.get("kind")
        if not isinstance(kind, str):
            raise Namel3ssError(f"Memory item {idx} kind must be text", line=line, column=column)
        text = entry.get("text")
        if not isinstance(text, str):
            raise Namel3ssError(f"Memory item {idx} text must be text", line=line, column=column)
        meta = entry.get("meta")
        if meta is not None and not isinstance(meta, dict):
            raise Namel3ssError(f"Memory item {idx} meta must be an object", line=line, column=column)


__all__ = [
    "_build_chat_messages",
    "_build_chat_composer",
    "_build_chat_thinking",
    "_build_chat_citations",
    "_build_chat_memory",
    "_chat_item_kind",
    "_chat_item_to_manifest",
    "_state_path_label",
]
