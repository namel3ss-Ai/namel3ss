from __future__ import annotations

CHAT_BRANCH_SELECT = "chat.branch.select"
CHAT_MESSAGE_REGENERATE = "chat.message.regenerate"
CHAT_MESSAGE_SEND = "chat.message.send"
CHAT_MODEL_SELECT = "chat.model.select"
CHAT_STREAM_CANCEL = "chat.stream.cancel"
CHAT_THREAD_NEW = "chat.thread.new"
CHAT_THREAD_SELECT = "chat.thread.select"

_ACTION_KIND_ALIASES: dict[str, str] = {
    "chat_model_select": CHAT_MODEL_SELECT,
    "chat_thread_select": CHAT_THREAD_SELECT,
}


def canonical_action_kind(action_type: str) -> str:
    key = str(action_type or "")
    return _ACTION_KIND_ALIASES.get(key, key)


def action_kind_aliases(action_type: str) -> tuple[str, ...]:
    canonical = canonical_action_kind(action_type)
    aliases = [canonical]
    for alias, value in _ACTION_KIND_ALIASES.items():
        if value == canonical:
            aliases.append(alias)
    return tuple(aliases)


__all__ = [
    "CHAT_BRANCH_SELECT",
    "CHAT_MESSAGE_REGENERATE",
    "CHAT_MESSAGE_SEND",
    "CHAT_MODEL_SELECT",
    "CHAT_STREAM_CANCEL",
    "CHAT_THREAD_NEW",
    "CHAT_THREAD_SELECT",
    "action_kind_aliases",
    "canonical_action_kind",
]
