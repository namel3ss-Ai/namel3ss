from __future__ import annotations

from namel3ss.errors.base import Namel3ssError

_ROLE_VALUES = {"assistant", "system", "tool", "user"}
_STREAM_PHASE_VALUES = {"complete", "error", "idle", "streaming", "thinking"}


def ensure_chat_shell_state(state: dict) -> dict:
    chat = state.get("chat")
    if not isinstance(chat, dict):
        chat = {}
        state["chat"] = chat
    threads = _normalize_named_rows(chat.get("threads"))
    models = _normalize_named_rows(chat.get("models"))
    active_thread_id = _normalize_active_thread_id(chat, threads)
    selected_model_ids = _normalize_selected_model_ids(chat, models)
    messages_graph = _normalize_messages_graph(chat.get("messages_graph"), chat.get("messages"))
    composer_state = _normalize_composer_state(chat.get("composer_state"))
    stream_state = _normalize_stream_state(chat.get("stream_state"), node_ids={row["id"] for row in messages_graph["nodes"]})
    chat["threads"] = threads
    chat["active_thread_id"] = active_thread_id
    chat["models"] = models
    chat["selected_model_ids"] = selected_model_ids
    chat["messages_graph"] = messages_graph
    chat["composer_state"] = composer_state
    chat["stream_state"] = stream_state
    chat["active_thread"] = active_thread_id
    chat["active_models"] = list(selected_model_ids)
    return chat


def select_chat_thread(state: dict, thread_id: str) -> None:
    thread_text = _normalized_text(thread_id)
    if thread_text is None:
        raise Namel3ssError("Chat thread id must be text.")
    chat = ensure_chat_shell_state(state)
    known_ids = {entry["id"] for entry in chat["threads"]}
    if known_ids and thread_text not in known_ids:
        raise Namel3ssError(f'Unknown thread id "{thread_text}" for chat thread selection.')
    chat["active_thread_id"] = thread_text
    chat["active_thread"] = thread_text


def select_chat_models(state: dict, model_ids: list[str]) -> list[str]:
    chat = ensure_chat_shell_state(state)
    requested = _normalize_text_list(model_ids)
    known_ids = {entry["id"] for entry in chat["models"]}
    if known_ids:
        unknown = [entry for entry in requested if entry not in known_ids]
        if unknown:
            raise Namel3ssError(f'Unknown model id "{unknown[0]}" for chat model selection.')
    selected = sorted(requested)
    chat["selected_model_ids"] = selected
    chat["active_models"] = list(selected)
    return selected


def create_chat_thread(state: dict, thread_name: str | None = None) -> dict:
    chat = ensure_chat_shell_state(state)
    normalized_name = _normalized_text(thread_name)
    thread_id = _next_thread_id(chat["threads"], name=normalized_name)
    display_name = _next_thread_name(chat["threads"], preferred=normalized_name)
    thread = {"id": thread_id, "name": display_name}
    chat["threads"] = [*chat["threads"], thread]
    chat["active_thread_id"] = thread_id
    chat["active_thread"] = thread_id
    _reset_chat_conversation(chat)
    return thread


def append_chat_user_message(state: dict, message: str) -> dict:
    text = _normalized_text(message)
    if text is None:
        raise Namel3ssError("Chat message payload requires non-empty message text.")
    chat = ensure_chat_shell_state(state)
    graph = dict(chat["messages_graph"])
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    message_id = _next_message_id(nodes)
    node = {"content": text, "id": message_id, "role": "user"}
    previous_id = nodes[-1]["id"] if nodes else None
    nodes.append(node)
    if isinstance(previous_id, str) and previous_id:
        edges.append({"from": previous_id, "to": message_id})
    graph["nodes"] = nodes
    graph["edges"] = _normalize_graph_edges(edges, node_ids={entry["id"] for entry in nodes})
    graph["active_message_id"] = message_id
    chat["messages_graph"] = graph
    _sync_legacy_messages(chat)
    stream_state = dict(chat["stream_state"])
    stream_state["active_message_id"] = message_id
    stream_state["cancel_requested"] = False
    stream_state["phase"] = "thinking"
    stream_state["tokens"] = []
    chat["stream_state"] = stream_state
    return node


def select_chat_branch(state: dict, message_id: str) -> str:
    selected_id = _normalized_text(message_id)
    if selected_id is None:
        raise Namel3ssError("Chat branch selection requires message_id text.")
    chat = ensure_chat_shell_state(state)
    known_ids = {entry["id"] for entry in chat["messages_graph"]["nodes"]}
    if selected_id not in known_ids:
        raise Namel3ssError(f'Unknown message id "{selected_id}" for chat branch selection.')
    chat["messages_graph"]["active_message_id"] = selected_id
    chat["stream_state"]["active_message_id"] = selected_id
    return selected_id


def begin_chat_message_regeneration(state: dict, message_id: str | None = None) -> str:
    chat = ensure_chat_shell_state(state)
    target = _resolve_regeneration_target(chat, explicit_message_id=message_id)
    chat["messages_graph"]["active_message_id"] = target
    stream_state = dict(chat["stream_state"])
    stream_state["active_message_id"] = target
    stream_state["cancel_requested"] = False
    stream_state["phase"] = "thinking"
    stream_state["tokens"] = []
    chat["stream_state"] = stream_state
    return target


def request_chat_stream_cancel(state: dict) -> dict:
    chat = ensure_chat_shell_state(state)
    stream_state = dict(chat["stream_state"])
    stream_state["cancel_requested"] = True
    if stream_state.get("phase") in {"streaming", "thinking"}:
        stream_state["phase"] = "idle"
    stream_state["tokens"] = []
    chat["stream_state"] = stream_state
    return dict(stream_state)


def _normalize_named_rows(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows: list[dict] = []
    seen_ids: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            continue
        entry_id = _normalized_text(entry.get("id"))
        if entry_id is None or entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        name = _normalized_text(entry.get("name")) or entry_id
        row = {"id": entry_id, "name": name}
        for key in sorted(entry.keys()):
            if key in {"id", "name"}:
                continue
            row[str(key)] = entry[key]
        rows.append(row)
    return rows


def _next_thread_id(threads: list[dict], *, name: str | None) -> str:
    known_ids = {entry["id"] for entry in threads if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
    base = _slug_text(name) or "new"
    candidate = f"thread.{base}"
    if candidate not in known_ids:
        return candidate
    suffix = 2
    while True:
        candidate = f"thread.{base}.{suffix}"
        if candidate not in known_ids:
            return candidate
        suffix += 1


def _next_thread_name(threads: list[dict], *, preferred: str | None) -> str:
    if preferred:
        known = {entry["name"] for entry in threads if isinstance(entry, dict) and isinstance(entry.get("name"), str)}
        if preferred not in known:
            return preferred
        suffix = 2
        while True:
            candidate = f"{preferred} {suffix}"
            if candidate not in known:
                return candidate
            suffix += 1
    count = len(threads) + 1
    return f"New chat {count}"


def _next_message_id(nodes: list[dict]) -> str:
    used_ids = {entry.get("id") for entry in nodes if isinstance(entry, dict)}
    index = len(nodes) + 1
    while True:
        candidate = f"message.{index}"
        if candidate not in used_ids:
            return candidate
        index += 1


def _resolve_regeneration_target(chat: dict, *, explicit_message_id: str | None) -> str:
    nodes = list((chat.get("messages_graph") or {}).get("nodes") or [])
    if not nodes:
        raise Namel3ssError("Cannot regenerate chat message without any messages.")
    explicit = _normalized_text(explicit_message_id)
    known_ids = {entry["id"] for entry in nodes if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
    if explicit is not None:
        if explicit not in known_ids:
            raise Namel3ssError(f'Unknown message id "{explicit}" for chat regeneration.')
        return explicit
    active = _normalized_text((chat.get("messages_graph") or {}).get("active_message_id"))
    if active in known_ids:
        return active
    for entry in reversed(nodes):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("role") or "") == "assistant":
            entry_id = _normalized_text(entry.get("id"))
            if entry_id is not None:
                return entry_id
    fallback = _normalized_text(nodes[-1].get("id")) if isinstance(nodes[-1], dict) else None
    if fallback is not None:
        return fallback
    raise Namel3ssError("Cannot resolve chat regeneration target.")


def _reset_chat_conversation(chat: dict) -> None:
    chat["messages"] = []
    chat["messages_graph"] = {"active_message_id": None, "edges": [], "nodes": []}
    chat["composer_state"] = {"attachments": [], "draft": "", "tools": [], "web_search": False}
    chat["stream_state"] = {"active_message_id": None, "cancel_requested": False, "phase": "idle", "tokens": []}


def _sync_legacy_messages(chat: dict) -> None:
    nodes = (chat.get("messages_graph") or {}).get("nodes")
    if not isinstance(nodes, list):
        chat["messages"] = []
        return
    messages: list[dict] = []
    for entry in nodes:
        if not isinstance(entry, dict):
            continue
        message_id = _normalized_text(entry.get("id"))
        role = _normalize_role(entry.get("role"))
        content = str(entry.get("content") or "")
        payload = {"content": content, "role": role}
        if message_id is not None:
            payload["id"] = message_id
        messages.append(payload)
    chat["messages"] = messages


def _normalize_active_thread_id(chat: dict, threads: list[dict]) -> str:
    candidate = _normalized_text(chat.get("active_thread_id"))
    if candidate is None:
        candidate = _normalized_text(_first_text_value(chat.get("active_thread")))
    known_ids = {entry["id"] for entry in threads}
    if known_ids and candidate not in known_ids:
        candidate = threads[0]["id"]
    return candidate or ""


def _normalize_selected_model_ids(chat: dict, models: list[dict]) -> list[str]:
    source = chat.get("selected_model_ids")
    if source is None:
        source = chat.get("active_models")
    selected = _normalize_text_list(source)
    known_ids = {entry["id"] for entry in models}
    if known_ids:
        selected = [entry for entry in selected if entry in known_ids]
        if not selected:
            selected = [models[0]["id"]]
    return sorted(selected)


def _normalize_messages_graph(raw_graph: object, raw_messages: object) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    active_message_id: str | None = None
    if isinstance(raw_graph, dict):
        nodes = _normalize_graph_nodes(raw_graph.get("nodes"))
        node_ids = {entry["id"] for entry in nodes}
        edges = _normalize_graph_edges(raw_graph.get("edges"), node_ids=node_ids)
        active_message_id = _normalized_text(raw_graph.get("active_message_id"))
        if active_message_id not in node_ids:
            active_message_id = None
    if not nodes:
        nodes = _messages_to_nodes(raw_messages)
        edges = _linear_edges(nodes)
        active_message_id = nodes[-1]["id"] if nodes else None
    return {"active_message_id": active_message_id, "edges": edges, "nodes": nodes}


def _normalize_graph_nodes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    nodes: list[dict] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(value, start=1):
        if not isinstance(entry, dict):
            continue
        message_id = _normalized_text(entry.get("id")) or f"message.{index}"
        if message_id in seen_ids:
            continue
        seen_ids.add(message_id)
        role = _normalize_role(entry.get("role"))
        content = str(entry.get("content") or "")
        nodes.append({"content": content, "id": message_id, "role": role})
    return nodes


def _messages_to_nodes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    nodes: list[dict] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(value, start=1):
        if not isinstance(entry, dict):
            continue
        message_id = _normalized_text(entry.get("id")) or f"message.{index}"
        if message_id in seen_ids:
            continue
        seen_ids.add(message_id)
        nodes.append(
            {
                "content": str(entry.get("content") or ""),
                "id": message_id,
                "role": _normalize_role(entry.get("role")),
            }
        )
    return nodes


def _normalize_graph_edges(value: object, *, node_ids: set[str]) -> list[dict]:
    if not isinstance(value, list):
        return []
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for entry in value:
        if not isinstance(entry, dict):
            continue
        parent = _normalized_text(entry.get("from"))
        child = _normalized_text(entry.get("to"))
        if parent is None or child is None:
            continue
        if parent not in node_ids or child not in node_ids:
            continue
        key = (parent, child)
        if key in seen:
            continue
        seen.add(key)
        edges.append({"from": parent, "to": child})
    return edges


def _linear_edges(nodes: list[dict]) -> list[dict]:
    if len(nodes) < 2:
        return []
    edges: list[dict] = []
    for index in range(1, len(nodes)):
        edges.append({"from": nodes[index - 1]["id"], "to": nodes[index]["id"]})
    return edges


def _normalize_composer_state(value: object) -> dict:
    if not isinstance(value, dict):
        return {"attachments": [], "draft": "", "tools": [], "web_search": False}
    return {
        "attachments": _normalize_text_list(value.get("attachments")),
        "draft": str(value.get("draft") or ""),
        "tools": _normalize_text_list(value.get("tools")),
        "web_search": bool(value.get("web_search")),
    }


def _normalize_stream_state(value: object, *, node_ids: set[str]) -> dict:
    if not isinstance(value, dict):
        return {"active_message_id": None, "cancel_requested": False, "phase": "idle", "tokens": []}
    phase_raw = _normalized_text(value.get("phase")) or "idle"
    phase = phase_raw if phase_raw in _STREAM_PHASE_VALUES else "idle"
    active_message_id = _normalized_text(value.get("active_message_id"))
    if active_message_id not in node_ids:
        active_message_id = None
    return {
        "active_message_id": active_message_id,
        "cancel_requested": bool(value.get("cancel_requested")),
        "phase": phase,
        "tokens": _normalize_text_list(value.get("tokens")),
    }


def _normalize_role(value: object) -> str:
    role = (_normalized_text(value) or "assistant").lower()
    if role in _ROLE_VALUES:
        return role
    return "assistant"


def _normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in values:
        text = _normalized_text(entry)
        if text is None or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _first_text_value(value: object) -> str | None:
    if isinstance(value, list):
        for entry in value:
            text = _normalized_text(entry)
            if text is not None:
                return text
        return None
    return _normalized_text(value)


def _normalized_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text


def _slug_text(value: str | None) -> str:
    if value is None:
        return ""
    allowed: list[str] = []
    last_dot = False
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
            last_dot = False
            continue
        if last_dot:
            continue
        allowed.append(".")
        last_dot = True
    slug = "".join(allowed).strip(".")
    return slug


__all__ = ["append_chat_user_message", "begin_chat_message_regeneration", "create_chat_thread", "ensure_chat_shell_state", "request_chat_stream_cancel", "select_chat_branch", "select_chat_models", "select_chat_thread"]
