from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir

_ALLOWED_MESSAGE_ACTIONS = {"copy", "expand", "view_sources"}
_ALLOWED_ATTACHMENT_TYPES = {"citation", "file", "image"}
_SNIPPET_MAX_LENGTH = 220


def apply_chat_configuration(
    chat_element: dict,
    item: ir.ChatItem,
    *,
    citations_enhanced_enabled: bool = True,
) -> dict:
    if not isinstance(chat_element, dict):
        return chat_element
    chat_element["style"] = _normalize_style(getattr(item, "style", "bubbles"), line=item.line, column=item.column)
    chat_element["show_avatars"] = bool(getattr(item, "show_avatars", False))
    chat_element["group_messages"] = bool(getattr(item, "group_messages", True))
    chat_element["streaming"] = bool(getattr(item, "streaming", False))
    chat_element["attachments"] = bool(getattr(item, "attachments", False))
    chat_element["citations_enhanced"] = bool(citations_enhanced_enabled)
    chat_element["actions"] = _normalize_actions(getattr(item, "actions", []), line=item.line, column=item.column)

    children = chat_element.get("children")
    if not isinstance(children, list):
        return chat_element

    thinking_active = False
    for child in children:
        if not isinstance(child, dict):
            continue
        if child.get("type") != "thinking":
            continue
        if chat_element["streaming"]:
            child["debug_only"] = False
            child["user_visible"] = True
        thinking_active = thinking_active or bool(child.get("active"))

    for child in children:
        if not isinstance(child, dict):
            continue
        if child.get("type") != "messages":
            continue
        _apply_message_configuration(
            child,
            default_actions=chat_element["actions"],
            attachments_enabled=chat_element["attachments"],
            group_messages=chat_element["group_messages"],
            streaming_enabled=chat_element["streaming"],
            thinking_active=thinking_active,
            line=item.line,
            column=item.column,
        )
        break
    return chat_element


def _apply_message_configuration(
    messages_element: dict,
    *,
    default_actions: list[str],
    attachments_enabled: bool,
    group_messages: bool,
    streaming_enabled: bool,
    thinking_active: bool,
    line: int | None,
    column: int | None,
) -> None:
    values = messages_element.get("messages")
    if not isinstance(values, list):
        return
    last_assistant_index = _last_assistant_message(values)
    normalized: list[dict] = []
    previous_role: str | None = None
    for idx, entry in enumerate(values):
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role") or "user")
        message = dict(entry)
        message["group_start"] = not group_messages or role != previous_role
        previous_role = role

        message_actions = _normalize_actions(message.get("actions", default_actions), line=line, column=column)
        if message_actions:
            message["actions"] = message_actions
        else:
            message.pop("actions", None)

        citations = _normalize_citations(message.get("citations"), line=line, column=column)
        if citations:
            message["citations"] = citations

        attachments = _normalize_attachments(
            message.get("attachments"),
            citations=citations,
            attachments_enabled=attachments_enabled,
            line=line,
            column=column,
        )
        if attachments:
            message["attachments"] = attachments
        else:
            message.pop("attachments", None)

        if streaming_enabled and role == "assistant":
            in_progress = bool(message.get("streaming"))
            if thinking_active and idx == last_assistant_index:
                in_progress = True
            if in_progress:
                message["streaming"] = True
            else:
                message.pop("streaming", None)
        else:
            message.pop("streaming", None)

        normalized.append(message)
    messages_element["messages"] = normalized


def _normalize_style(value: object, *, line: int | None, column: int | None) -> str:
    style = str(value or "bubbles").strip().lower()
    if style not in {"bubbles", "plain"}:
        raise Namel3ssError("Chat style must be bubbles or plain.", line=line, column=column)
    return style


def _normalize_actions(raw: object, *, line: int | None, column: int | None) -> list[str]:
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in values:
        if not isinstance(entry, str):
            raise Namel3ssError("Chat actions must be text values.", line=line, column=column)
        value = entry.strip().lower()
        if value not in _ALLOWED_MESSAGE_ACTIONS:
            allowed = ", ".join(sorted(_ALLOWED_MESSAGE_ACTIONS))
            raise Namel3ssError(f"Unknown chat action '{value}'. Expected one of: {allowed}.", line=line, column=column)
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _normalize_citations(value: object, *, line: int | None, column: int | None) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise Namel3ssError("Message citations must be a list.", line=line, column=column)
    citations: list[dict] = []
    for idx, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise Namel3ssError(f"Message citation {idx} must be an object.", line=line, column=column)
        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            raise Namel3ssError(f"Message citation {idx} title must be text.", line=line, column=column)
        url = entry.get("url")
        source_id = entry.get("source_id")
        if url is None and source_id is None:
            raise Namel3ssError(f"Message citation {idx} must include url or source_id.", line=line, column=column)
        citation = {"type": "citation", "title": title.strip()}
        citation["citation_id"] = _normalize_citation_id(entry, idx=idx)
        if isinstance(url, str) and url.strip():
            citation["url"] = url.strip()
        if isinstance(source_id, str) and source_id.strip():
            citation["source_id"] = source_id.strip()
        snippet = entry.get("snippet")
        if isinstance(snippet, str) and snippet.strip():
            citation["snippet"] = _normalize_snippet(snippet)
        index = entry.get("index")
        if isinstance(index, int):
            citation["index"] = max(1, index)
        citations.append(citation)
    return citations


def _normalize_attachments(
    value: object,
    *,
    citations: list[dict],
    attachments_enabled: bool,
    line: int | None,
    column: int | None,
) -> list[dict]:
    if value is None and not attachments_enabled:
        return []
    attachments: list[dict] = []
    if isinstance(value, list):
        for idx, entry in enumerate(value):
            attachments.append(_normalize_attachment(entry, idx=idx, line=line, column=column))
    elif value is not None:
        raise Namel3ssError("Message attachments must be a list.", line=line, column=column)
    if citations:
        for citation in citations:
            attachments.append(dict(citation))
    if not attachments_enabled and value is None:
        return []
    return attachments


def _normalize_attachment(entry: object, *, idx: int, line: int | None, column: int | None) -> dict:
    if not isinstance(entry, dict):
        raise Namel3ssError(f"Message attachment {idx} must be an object.", line=line, column=column)
    attachment_type = entry.get("type")
    if not isinstance(attachment_type, str) or attachment_type.strip().lower() not in _ALLOWED_ATTACHMENT_TYPES:
        allowed = ", ".join(sorted(_ALLOWED_ATTACHMENT_TYPES))
        raise Namel3ssError(f"Message attachment {idx} type must be one of: {allowed}.", line=line, column=column)
    kind = attachment_type.strip().lower()
    payload = dict(entry)
    payload["type"] = kind
    if kind == "citation":
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            raise Namel3ssError(f"Message attachment {idx} citation title must be text.", line=line, column=column)
        if payload.get("url") is None and payload.get("source_id") is None:
            raise Namel3ssError(f"Message attachment {idx} citation needs url or source_id.", line=line, column=column)
    if kind == "file":
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise Namel3ssError(f"Message attachment {idx} file name must be text.", line=line, column=column)
        if payload.get("url") is None and payload.get("source_id") is None:
            raise Namel3ssError(f"Message attachment {idx} file needs url or source_id.", line=line, column=column)
    if kind == "image":
        url = payload.get("url")
        if not isinstance(url, str) or not url.strip():
            raise Namel3ssError(f"Message attachment {idx} image needs url.", line=line, column=column)
    return payload


def _last_assistant_message(messages: list[object]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        entry = messages[index]
        if isinstance(entry, dict) and str(entry.get("role") or "") == "assistant":
            return index
    return -1


def _normalize_citation_id(entry: dict, *, idx: int) -> str:
    value = entry.get("citation_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    fallback = entry.get("id")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    return f"citation.{idx + 1}"


def _normalize_snippet(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) <= _SNIPPET_MAX_LENGTH:
        return compact
    truncated = compact[:_SNIPPET_MAX_LENGTH].rstrip()
    return f"{truncated}..."


__all__ = ["apply_chat_configuration"]
