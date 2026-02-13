from __future__ import annotations

from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.build.dispatch_contract import ActionHandler
from namel3ss.runtime.ui.actions.settings.theme_update import handle_theme_settings_update_action


def _run_theme_settings_update(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_theme_settings_update_action(
        ctx.program_ir,
        action=ctx.action,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
    )
    return response, None


ACTION_HANDLERS: dict[str, ActionHandler] = {"theme_settings_update": _run_theme_settings_update}


__all__ = ["ACTION_HANDLERS"]
