from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir

_ALLOWED_MESSAGE_ACTIONS = {"copy", "expand", "view_sources"}
_ALLOWED_ATTACHMENT_TYPES = {"citation", "file", "image"}
_ALLOWED_COMPOSER_SEND_STYLES = {"icon", "text"}
_DEFAULT_COMPOSER_PLACEHOLDER = "Ask about your documents... use #project or @document"
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
    chat_element["composer_placeholder"] = _normalize_composer_placeholder(
        getattr(item, "composer_placeholder", _DEFAULT_COMPOSER_PLACEHOLDER),
    )
    chat_element["composer_send_style"] = _normalize_composer_send_style(
        getattr(item, "composer_send_style", "icon"),
        line=item.line,
        column=item.column,
    )
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


def _normalize_composer_placeholder(raw: object) -> str:
    if not isinstance(raw, str):
        return _DEFAULT_COMPOSER_PLACEHOLDER
    value = raw.strip()
    if not value:
        return _DEFAULT_COMPOSER_PLACEHOLDER
    return value


def _normalize_composer_send_style(raw: object, *, line: int | None, column: int | None) -> str:
    value = str(raw or "icon").strip().lower()
    if value not in _ALLOWED_COMPOSER_SEND_STYLES:
        raise Namel3ssError(
            "composer_send_style must be icon or text.",
            line=line,
            column=column,
        )
    return value


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
        chunk_id = entry.get("chunk_id")
        if isinstance(chunk_id, str) and chunk_id.strip():
            citation["chunk_id"] = chunk_id.strip()
        document_id = entry.get("document_id")
        if isinstance(document_id, str) and document_id.strip():
            citation["document_id"] = document_id.strip()
        deep_link_query = entry.get("deep_link_query")
        if isinstance(deep_link_query, str) and deep_link_query.strip():
            citation["deep_link_query"] = deep_link_query.strip()
        preview_url = entry.get("preview_url")
        if isinstance(preview_url, str) and preview_url.strip():
            citation["preview_url"] = preview_url.strip()
        explain = entry.get("explain")
        if isinstance(explain, str) and explain.strip():
            citation["explain"] = explain.strip()
        highlight_color = entry.get("highlight_color")
        if isinstance(highlight_color, str) and highlight_color.strip():
            citation["highlight_color"] = highlight_color.strip()
        color = entry.get("color")
        if isinstance(color, str) and color.strip():
            citation["color"] = color.strip()
        color_hex = entry.get("color_hex")
        if isinstance(color_hex, str) and color_hex.strip():
            citation["color_hex"] = color_hex.strip()
        page_number = _positive_int(entry.get("page_number"))
        if page_number is not None:
            citation["page_number"] = page_number
        page_value = entry.get("page")
        page_number_from_page = _positive_int(page_value)
        if page_number_from_page is not None:
            citation["page"] = page_number_from_page
        elif isinstance(page_value, str) and page_value.strip():
            citation["page"] = page_value.strip()
        color_index = entry.get("color_index")
        if isinstance(color_index, int):
            citation["color_index"] = abs(color_index) % 8
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


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            parsed = int(text)
            return parsed if parsed > 0 else None
    return None


__all__ = ["apply_chat_configuration"]
