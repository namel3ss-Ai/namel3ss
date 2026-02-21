from __future__ import annotations

import math

from namel3ss.errors.base import Namel3ssError

_ALLOWED_ROLES = {"user", "assistant", "system", "tool"}
_SNIPPET_MAX_LENGTH = 220


def require_list(value: object, label: str, line: int | None, column: int | None) -> list:
    if not isinstance(value, list):
        raise Namel3ssError(f"{label} must be a list", line=line, column=column)
    return value


def normalize_messages(messages: list, line: int | None, column: int | None) -> list[dict]:
    normalized: list[dict] = []
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
        message_id = entry.get("id")
        if message_id is not None and not isinstance(message_id, str):
            raise Namel3ssError(f"Message {idx} id must be text", line=line, column=column)
        created = entry.get("created")
        if created is not None and not isinstance(created, (str, int, float)):
            raise Namel3ssError(f"Message {idx} created must be text or number", line=line, column=column)
        meta = entry.get("meta")
        if meta is not None and not isinstance(meta, dict):
            raise Namel3ssError(f"Message {idx} meta must be an object", line=line, column=column)
        message_payload = {"role": role, "content": content}
        if isinstance(message_id, str) and message_id.strip():
            message_payload["id"] = message_id.strip()
        if created is not None:
            message_payload["created"] = created
        if meta is not None:
            message_payload["meta"] = meta
        citations = entry.get("citations")
        if citations is not None:
            if not isinstance(citations, list):
                raise Namel3ssError(f"Message {idx} citations must be a list", line=line, column=column)
            validate_citations(citations, line, column)
            message_payload["citations"] = _index_citations(citations)
        trust = entry.get("trust")
        if trust is not None:
            message_payload["trust"] = _normalize_trust_value(trust, idx=idx, line=line, column=column)
        attachments = entry.get("attachments")
        if attachments is not None:
            if not isinstance(attachments, list):
                raise Namel3ssError(f"Message {idx} attachments must be a list", line=line, column=column)
            message_payload["attachments"] = [dict(item) for item in attachments if isinstance(item, dict)]
        actions = entry.get("actions")
        if actions is not None:
            if isinstance(actions, str):
                message_payload["actions"] = [actions]
            elif isinstance(actions, list):
                values: list[object] = []
                for action in actions:
                    if isinstance(action, str):
                        values.append(action)
                        continue
                    if isinstance(action, dict):
                        action_id = action.get("id")
                        if not isinstance(action_id, str) or not action_id.strip():
                            raise Namel3ssError(f"Message {idx} action id must be text", line=line, column=column)
                        action_payload: dict[str, object] = {"id": action_id.strip()}
                        label = action.get("label")
                        if label is not None and not isinstance(label, str):
                            raise Namel3ssError(f"Message {idx} action label must be text", line=line, column=column)
                        if isinstance(label, str) and label.strip():
                            action_payload["label"] = label.strip()
                        icon = action.get("icon")
                        if icon is not None and not isinstance(icon, str):
                            raise Namel3ssError(f"Message {idx} action icon must be text", line=line, column=column)
                        if isinstance(icon, str) and icon.strip():
                            action_payload["icon"] = icon.strip()
                        style = action.get("style")
                        if style is not None and not isinstance(style, str):
                            raise Namel3ssError(f"Message {idx} action style must be text", line=line, column=column)
                        if isinstance(style, str) and style.strip():
                            action_payload["style"] = style.strip()
                        action_target_id = action.get("action_id")
                        if action_target_id is not None and not isinstance(action_target_id, str):
                            raise Namel3ssError(f"Message {idx} action action_id must be text", line=line, column=column)
                        if isinstance(action_target_id, str) and action_target_id.strip():
                            action_payload["action_id"] = action_target_id.strip()
                        action_type = action.get("action_type")
                        if action_type is not None and not isinstance(action_type, str):
                            raise Namel3ssError(f"Message {idx} action action_type must be text", line=line, column=column)
                        if isinstance(action_type, str) and action_type.strip():
                            action_payload["action_type"] = action_type.strip()
                        flow = action.get("flow")
                        if flow is not None and not isinstance(flow, str):
                            raise Namel3ssError(f"Message {idx} action flow must be text", line=line, column=column)
                        if isinstance(flow, str) and flow.strip():
                            action_payload["flow"] = flow.strip()
                        target = action.get("target")
                        if target is not None and not isinstance(target, str):
                            raise Namel3ssError(f"Message {idx} action target must be text", line=line, column=column)
                        if isinstance(target, str) and target.strip():
                            action_payload["target"] = target.strip()
                        payload = action.get("payload")
                        if payload is not None:
                            if not isinstance(payload, dict):
                                raise Namel3ssError(f"Message {idx} action payload must be an object", line=line, column=column)
                            action_payload["payload"] = dict(payload)
                        values.append(action_payload)
                        continue
                    raise Namel3ssError(f"Message {idx} actions must be text", line=line, column=column)
                message_payload["actions"] = values
            else:
                raise Namel3ssError(f"Message {idx} actions must be text or list", line=line, column=column)
        streaming = entry.get("streaming")
        if streaming is not None:
            if not isinstance(streaming, bool):
                raise Namel3ssError(f"Message {idx} streaming must be true or false", line=line, column=column)
            message_payload["streaming"] = streaming
        tokens = entry.get("tokens")
        if tokens is not None:
            if not isinstance(tokens, list) or any(not isinstance(token, str) for token in tokens):
                raise Namel3ssError(f"Message {idx} tokens must be a list of text", line=line, column=column)
            message_payload["tokens"] = list(tokens)
        normalized.append(message_payload)
    return normalized


def validate_citations(citations: list, line: int | None, column: int | None) -> None:
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


def validate_memory(items: list, line: int | None, column: int | None) -> None:
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


def _normalize_trust_value(value: object, *, idx: int, line: int | None, column: int | None) -> bool | float:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if not math.isfinite(number) or number < 0 or number > 1:
            raise Namel3ssError(f"Message {idx} trust must be between 0 and 1", line=line, column=column)
        return round(number, 4)
    raise Namel3ssError(f"Message {idx} trust must be boolean or number", line=line, column=column)


def _index_citations(citations: list[dict]) -> list[dict]:
    indexed: list[dict] = []
    for idx, entry in enumerate(citations):
        payload = dict(entry)
        payload["citation_id"] = _normalize_citation_id(entry, idx=idx)
        snippet = payload.get("snippet")
        if isinstance(snippet, str) and snippet.strip():
            payload["snippet"] = _normalize_snippet(snippet)
        payload["index"] = idx + 1
        indexed.append(payload)
    return indexed


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


__all__ = ["normalize_messages", "require_list", "validate_citations", "validate_memory"]
