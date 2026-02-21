from __future__ import annotations

from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.build.dispatch_contract import ActionHandler
from namel3ss.runtime.ui.actions.upload.clear import handle_upload_clear_action
from namel3ss.runtime.ui.actions.upload.replace import handle_upload_replace_action
from namel3ss.runtime.ui.actions.upload.select import handle_upload_select_action


def _run_upload_select(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_upload_select_action(
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
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


def _run_upload_clear(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_upload_clear_action(
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
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


def _run_upload_replace(ctx: ActionDispatchContext) -> tuple[dict, Exception | None]:
    response = handle_upload_replace_action(
        ctx.program_ir,
        action_id=ctx.action_id,
        payload=ctx.payload,
        state=ctx.state,
        store=ctx.store,
        runtime_theme=ctx.runtime_theme,
        config=ctx.config,
        identity=ctx.identity,
        auth_context=ctx.auth_context,
        secret_values=ctx.secret_values,
        ui_mode=ctx.ui_mode,
        diagnostics_enabled=ctx.diagnostics_enabled,
    )
    return response, None


ACTION_HANDLERS: dict[str, ActionHandler] = {
    "upload_clear": _run_upload_clear,
    "upload_replace": _run_upload_replace,
    "upload_select": _run_upload_select,
}


__all__ = ["ACTION_HANDLERS"]
