from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.chat.composer import build_chat_composer_manifest
from namel3ss.ui.manifest.chat.message_normalization import (
    normalize_messages as _normalize_messages,
    require_list as _require_list,
    validate_citations as _validate_citations,
    validate_memory as _validate_memory,
)
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode


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
    normalized_messages = _normalize_messages(messages, item.line, item.column)
    element = {
        "type": "messages",
        "source": source,
        "messages": normalized_messages,
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }
    controls = _chat_message_control_contract(item, element_id=element_id, state_ctx=state_ctx)
    if controls:
        element.update(controls)
    return element


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
        "debug_only": True,
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
        "debug_only": True,
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
        "debug_only": True,
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
        element = _build_chat_messages(
            item,
            element_id=element_id,
            page_name=page_name,
            page_slug=page_slug,
            index=index,
            state_ctx=state_ctx,
            mode=mode,
        )
        return (
            element,
            _chat_message_actions(item, element_id=element_id),
        )
    if isinstance(item, ir.ChatComposerItem):
        return build_chat_composer_manifest(
            item,
            element_id=element_id,
            page_name=page_name,
            page_slug=page_slug,
            index=index,
            state_ctx=state_ctx,
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


def _resolve_state_parts(path: list[str], state_ctx: StateContext, *, default: object, register_default: bool) -> object:
    try:
        value, _ = state_ctx.value(path, default=default, register_default=register_default)
        return value
    except KeyError:
        return default


def _state_path_label(path: ir.StatePath) -> str:
    return f"state.{'.'.join(path.path)}"


def _state_parts_label(path: list[str]) -> str:
    return f"state.{'.'.join(path)}"


def _chat_shell_prefix(path: list[str]) -> list[str] | None:
    values = [segment for segment in path if isinstance(segment, str) and segment]
    if not values:
        return None
    if values[-1] != "messages":
        return None
    return values[:-1]


def _chat_message_control_contract(
    item: ir.ChatMessagesItem,
    *,
    element_id: str,
    state_ctx: StateContext,
) -> dict:
    prefix = _chat_shell_prefix(item.source.path)
    if prefix is None:
        return {}
    active_message_value = _resolve_state_parts(
        [*prefix, "messages_graph", "active_message_id"],
        state_ctx,
        default=None,
        register_default=True,
    )
    stream_state = _resolve_state_parts(
        [*prefix, "stream_state"],
        state_ctx,
        default={},
        register_default=True,
    )
    active_message_id = active_message_value if isinstance(active_message_value, str) and active_message_value.strip() else None
    stream_phase = ""
    cancel_requested = False
    if isinstance(stream_state, dict):
        phase_value = stream_state.get("phase")
        if isinstance(phase_value, str):
            stream_phase = phase_value.strip().lower()
        cancel_requested = bool(stream_state.get("cancel_requested"))
    return {
        "active_message_id": active_message_id,
        "branch_action_id": f"{element_id}.branch_select",
        "regenerate_action_id": f"{element_id}.message_regenerate",
        "stream_cancel_action_id": f"{element_id}.stream_cancel",
        "stream_cancel_requested": cancel_requested,
        "stream_phase": stream_phase,
    }


def _chat_message_actions(item: ir.ChatMessagesItem, *, element_id: str) -> dict:
    prefix = _chat_shell_prefix(item.source.path)
    if prefix is None:
        return {}
    active_target_state = _state_parts_label([*prefix, "messages_graph", "active_message_id"])
    cancel_target_state = _state_parts_label([*prefix, "stream_state", "cancel_requested"])
    branch_action_id = f"{element_id}.branch_select"
    regenerate_action_id = f"{element_id}.message_regenerate"
    stream_cancel_action_id = f"{element_id}.stream_cancel"
    return {
        branch_action_id: {
            "id": branch_action_id,
            "target_state": active_target_state,
            "type": "chat.branch.select",
        },
        regenerate_action_id: {
            "id": regenerate_action_id,
            "target_state": active_target_state,
            "type": "chat.message.regenerate",
        },
        stream_cancel_action_id: {
            "id": stream_cancel_action_id,
            "target_state": cancel_target_state,
            "type": "chat.stream.cancel",
        },
    }


__all__ = [
    "_build_chat_messages",
    "_build_chat_thinking",
    "_build_chat_citations",
    "_build_chat_memory",
    "_chat_item_kind",
    "_chat_item_to_manifest",
    "_state_path_label",
]
