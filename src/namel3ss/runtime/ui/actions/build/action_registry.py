from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.build.dispatch_contract import ActionHandler, merge_action_handlers
from namel3ss.runtime.ui.actions.chat.dispatch import ACTION_HANDLERS as CHAT_ACTION_HANDLERS
from namel3ss.runtime.ui.actions.ingestion.dispatch import ACTION_HANDLERS as INGESTION_ACTION_HANDLERS
from namel3ss.runtime.ui.actions.retrieval.dispatch import ACTION_HANDLERS as RETRIEVAL_ACTION_HANDLERS
from namel3ss.runtime.ui.actions.settings.dispatch import ACTION_HANDLERS as SETTINGS_ACTION_HANDLERS
from namel3ss.runtime.ui.actions.upload.dispatch import ACTION_HANDLERS as UPLOAD_ACTION_HANDLERS
from namel3ss.runtime.ui.state.dispatch import ACTION_HANDLERS as STATE_ACTION_HANDLERS

ACTION_HANDLERS: dict[str, ActionHandler] = merge_action_handlers(
    (
        CHAT_ACTION_HANDLERS,
        INGESTION_ACTION_HANDLERS,
        RETRIEVAL_ACTION_HANDLERS,
        SETTINGS_ACTION_HANDLERS,
        UPLOAD_ACTION_HANDLERS,
        STATE_ACTION_HANDLERS,
    )
)


def dispatch_action(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    handler = ACTION_HANDLERS.get(ctx.action_type)
    if handler is None:
        raise Namel3ssError(f"Unsupported action type '{ctx.action_type}'")
    return handler(ctx)


__all__ = ["ACTION_HANDLERS", "dispatch_action"]
